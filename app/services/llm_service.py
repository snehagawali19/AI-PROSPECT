"""Provider adapters (same as Test 1) + a generic structured() call with retry → cross-vendor fallback."""
import asyncio, json, logging
from dataclasses import dataclass
from pydantic import BaseModel, ValidationError
from app.config import cost_usd, get_settings, is_configured
from app.errors import LLMUnavailable

log = logging.getLogger("llm")

@dataclass
class LLMResult:
    data: dict
    input_tokens: int
    output_tokens: int
    model: str
    provider: str

class GeminiProvider:
    name = "gemini"
    def __init__(self, api_key: str, model: str):
        from google import genai
        self.client, self.model = genai.Client(api_key=api_key), model
    async def generate(self, system: str, user: str, schema) -> LLMResult:
        from google.genai import types
        resp = await self.client.aio.models.generate_content(
            model=self.model, contents=user,
            config=types.GenerateContentConfig(
                system_instruction=system, temperature=0, max_output_tokens=4096,
                response_mime_type="application/json", response_schema=schema))
        u = resp.usage_metadata
        out = (u.candidates_token_count or 0) + (getattr(u, "thoughts_token_count", 0) or 0)
        return LLMResult(json.loads(resp.text), u.prompt_token_count or 0, out, self.model, self.name)

class AnthropicProvider:
    name = "anthropic"
    def __init__(self, api_key: str, model: str):
        from anthropic import AsyncAnthropic
        self.client, self.model = AsyncAnthropic(api_key=api_key), model
    async def generate(self, system: str, user: str, schema) -> LLMResult:
        tool = {"name": "submit", "description": "Submit the structured result.",
                "input_schema": schema.model_json_schema()}
        msg = await self.client.messages.create(
            model=self.model, max_tokens=4096, temperature=0, system=system,
            messages=[{"role": "user", "content": user}],
            tools=[tool], tool_choice={"type": "tool", "name": "submit"})
        block = next(b for b in msg.content if b.type == "tool_use")
        return LLMResult(block.input, msg.usage.input_tokens, msg.usage.output_tokens, self.model, self.name)

class LLMNotConfigured(Exception):
    """Raised when a provider's API key or model ID is still a placeholder."""

def make_provider(provider: str, model: str):
    s = get_settings()
    if not is_configured(model):
        raise LLMNotConfigured(f"Model ID for provider '{provider}' is not set")
    if provider == "gemini":
        if not is_configured(s.gemini_api_key):
            raise LLMNotConfigured("GEMINI_API_KEY is not set")
        return GeminiProvider(s.gemini_api_key, model)
    if provider == "anthropic":
        if not is_configured(s.anthropic_api_key):
            raise LLMNotConfigured("ANTHROPIC_API_KEY is not set")
        return AnthropicProvider(s.anthropic_api_key, model)
    raise LLMNotConfigured(f"Unknown LLM provider '{provider}'")

async def structured(system: str, user: str, schema: type[BaseModel], usage: dict) -> BaseModel:
    """primary → primary (repair retry) → fallback vendor. Accumulates tokens/cost into `usage`."""
    s = get_settings()
    plan = [(s.primary_provider, s.primary_model), (s.primary_provider, s.primary_model),
            (s.fallback_provider, s.fallback_model)]
    feedback, last = "", None
    for i, (prov, model) in enumerate(plan, 1):
        try:
            r = await asyncio.wait_for(make_provider(prov, model).generate(system, user + feedback, schema),
                                       timeout=s.llm_timeout_s)
            usage["input_tokens"] = usage.get("input_tokens", 0) + r.input_tokens
            usage["output_tokens"] = usage.get("output_tokens", 0) + r.output_tokens
            usage["llm_cost_usd"] = round(usage.get("llm_cost_usd", 0) + cost_usd(model, r.input_tokens, r.output_tokens), 6)
            usage.setdefault("models", []).append(model)
            return schema.model_validate(r.data)
        except ValidationError as e:
            last = e.errors()[:5]
            feedback = f"\n\nYour previous output failed validation: {json.dumps(last, default=str)[:1200]}. Fix it."
        except Exception as e:  # timeout, 429, 5xx, auth
            last = repr(e)
            log.warning("LLM attempt %s %s/%s failed: %s", i, prov, model, last)
    raise LLMUnavailable("Query understanding is temporarily unavailable.", {"last_error": str(last)[:300]})
