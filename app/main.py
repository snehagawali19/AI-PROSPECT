import logging, time
from contextlib import asynccontextmanager
import httpx
from fastapi import FastAPI, Query, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from app.config import get_settings, is_configured
from app.errors import AppError
from app.schemas import DiscoveryRequest, DiscoveryResponse, ErrorBody, ErrorResponse
from app.services import prospect_service
from app.utils.fetch import UA

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("api")
limiter = Limiter(key_func=get_remote_address)

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.http = httpx.AsyncClient(follow_redirects=False, timeout=httpx.Timeout(8, connect=4),
                                       headers={"User-Agent": UA}, limits=httpx.Limits(max_connections=30))
    yield
    await app.state.http.aclose()

app = FastAPI(title="AI Multi-Platform Prospect Discovery API", version="1.0.0", lifespan=lifespan,
              description="Natural-language query → real public prospects from authorized sources. "
                          "No fabricated names, links or contacts.")
app.state.limiter = limiter

def error_json(status, code, message, details=None, query=None):
    body = ErrorResponse(query=query, error=ErrorBody(code=code, message=message, details=details))
    return JSONResponse(status_code=status, content=jsonable_encoder(body, exclude_none=True))

@app.exception_handler(AppError)
async def _app_err(_: Request, e: AppError):
    return error_json(e.status, e.code, e.message, e.details)

@app.exception_handler(RequestValidationError)
async def _val_err(_: Request, e: RequestValidationError):
    return error_json(422, "VALIDATION_ERROR", 'Expected {"query": "<audience> in <city> <country>"} (3–200 chars).',
                      {"errors": jsonable_encoder(e.errors())})

@app.exception_handler(RateLimitExceeded)
async def _rate(_: Request, e: RateLimitExceeded):
    return error_json(429, "RATE_LIMITED", "Too many requests. Please slow down.")

@app.exception_handler(Exception)
async def _unhandled(_: Request, e: Exception):
    log.exception("Unhandled error")
    return error_json(500, "INTERNAL_ERROR", "Unexpected server error.")

@app.get("/health", tags=["ops"])
async def health():
    """Liveness + which integrations are configured (booleans only — secrets are never echoed)."""
    s = get_settings()
    return {"status": "ok",
            "configured": {"serper": is_configured(s.serper_api_key),
                           "youtube": is_configured(s.youtube_api_key),
                           "anthropic": is_configured(s.anthropic_api_key),
                           "gemini": is_configured(s.gemini_api_key),
                           "primary_model": is_configured(s.primary_model),
                           "fallback_model": is_configured(s.fallback_model)},
            "llm": {"primary": f"{s.primary_provider}/{s.primary_model}",
                    "fallback": f"{s.fallback_provider}/{s.fallback_model}"}}

ERR = {c: {"model": ErrorResponse} for c in (422, 429, 500, 503)}

@app.post("/prospect-discovery", response_model=DiscoveryResponse, response_model_exclude_none=True,
          responses=ERR, tags=["discovery"])
@limiter.limit(lambda: get_settings().rate_limit)
async def prospect_discovery(request: Request, body: DiscoveryRequest,
                             include_evidence: bool = Query(False, description="Add evidence, sources, intent, platform_status, meta"),
                             include_possible: bool = Query(False, description="Also return 'possible' (partially evidenced) prospects")):
    t0 = time.perf_counter()
    try:
        return await prospect_service.run(request.app.state.http, body.query.strip(), include_evidence, include_possible)
    finally:
        log.info("request q=%r ms=%d", body.query, (time.perf_counter() - t0) * 1000)
