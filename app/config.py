"""Central configuration. Every secret / environment-specific value is read from environment variables
(or a local .env file) — swap values in ONE place: the .env file."""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

_PLACEHOLDER_PREFIXES = ("YOUR_", "REPLACE_", "CHANGE_ME")

def is_configured(value: str | None) -> bool:
    """True only for a real value — empty strings and dummy placeholders count as 'not configured'."""
    return bool(value) and not value.strip().upper().startswith(_PLACEHOLDER_PREFIXES)

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # ---- API keys (secrets) ----
    serper_api_key: str = ""
    youtube_api_key: str = ""
    anthropic_api_key: str = ""
    gemini_api_key: str = ""

    # ---- LLM selection (final pick should come from your own measurements; see README §LLM research) ----
    primary_provider: str = "anthropic"            # "anthropic" | "gemini"
    primary_model: str = "REPLACE_WITH_PRIMARY_MODEL_ID"
    fallback_provider: str = "gemini"
    fallback_model: str = "REPLACE_WITH_FALLBACK_MODEL_ID"
    llm_timeout_s: float = 30

    # ---- LLM pricing, USD per 1M tokens (from the providers' OFFICIAL pricing pages) ----
    primary_price_in_per_m: float = 0.0
    primary_price_out_per_m: float = 0.0
    fallback_price_in_per_m: float = 0.0
    fallback_price_out_per_m: float = 0.0

    # ---- discovery budgets (per request) ----
    max_serp_calls: int = 12
    max_site_fetches: int = 8
    results_per_query: int = 10
    platform_timeout_s: float = 12
    max_prospects: int = 25
    llm_batch_size: int = 40

    # ---- caching / abuse protection ----
    cache_ttl_s: int = 6 * 3600
    rate_limit: str = "10/minute"
    max_page_bytes: int = 1_000_000
    respect_robots_txt: bool = True

def cost_usd(model: str, tin: int, tout: int) -> float:
    s = get_settings()
    prices = {s.primary_model: (s.primary_price_in_per_m, s.primary_price_out_per_m),
              s.fallback_model: (s.fallback_price_in_per_m, s.fallback_price_out_per_m)}
    pi, po = prices.get(model, (0.0, 0.0))
    return round(tin / 1e6 * pi + tout / 1e6 * po, 6)

@lru_cache
def get_settings() -> Settings:
    return Settings()
