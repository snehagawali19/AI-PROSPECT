"""Pipeline: intent → parallel discovery → enrichment → dedupe → relevance → spec-shaped response."""
import asyncio, logging, time
import httpx
import app.platforms  # noqa: F401  (registers adapters)
from app.config import get_settings
from app.errors import BudgetExceeded
from app.models import Cluster
from app.platforms.base import REGISTRY
from app.schemas import DiscoveryResponse, Intent, Prospect, ProspectEvidence, SocialLink, SourceInfo
from app.services import deduplication_service, profile_extractor, relevance_service
from app.services.query_service import parse_intent
from app.services.search_service import Ctx, NotConfigured, QuotaExhausted, RateLimited

log = logging.getLogger("prospects")
LINK_ORDER = ["LinkedIn", "Google", "Facebook", "Instagram", "X", "YouTube", "Threads", "Email", "Phone", "WhatsApp"]

async def _run_adapter(adapter, ctx: Ctx):
    try:
        recs = await asyncio.wait_for(adapter.discover(ctx), timeout=get_settings().platform_timeout_s)
        return adapter.name, recs, ("ok" if recs or adapter.method != "extracted_from_published_pages"
                                    else "extracted_from_pages_only")
    except asyncio.TimeoutError:
        return adapter.name, [], "timeout"
    except RateLimited:
        return adapter.name, [], "rate_limited"
    except QuotaExhausted:
        return adapter.name, [], "quota_exhausted"
    except NotConfigured:
        return adapter.name, [], "not_configured"
    except BudgetExceeded:
        return adapter.name, [], "budget_exceeded"
    except Exception as e:
        log.warning("adapter %s failed: %r", adapter.name, e)
        return adapter.name, [], "error"

def _location_label(c: Cluster, i: Intent) -> str | None:
    if "location" not in c.signals:
        return None
    for r in c.records:
        if r.location_text and r.found_via in ("places", "serp") and r.platform != "YouTube":
            return r.location_text
    parts = [i.location.city, i.location.country_code or i.location.country]
    return ", ".join(p for p in parts if p) or None

def _links(c: Cluster, i: Intent) -> list[SocialLink]:
    links: dict[str, str] = {}
    for r in c.records:
        if r.platform == "Website":
            if r.url.startswith("https://"):
                links.setdefault(r.url, "Google")        # business's own website, discovered via Google
        else:
            links.setdefault(r.url, r.platform)
        for platform, value in r.contacts:
            if platform in ("Phone", "WhatsApp") and i.target_type == "individual" and not r.is_business:
                continue                                   # data minimisation: no personal phone numbers
            links.setdefault(value, platform)
    items = [SocialLink(platform=p, link=l) for l, p in links.items()]
    return sorted(items, key=lambda s: LINK_ORDER.index(s.platform))

async def run(client: httpx.AsyncClient, query: str, include_evidence=False, include_possible=False) -> DiscoveryResponse:
    s, t0, usage, warnings = get_settings(), time.perf_counter(), {}, []
    intent = await parse_intent(query, usage)
    ctx = Ctx(client=client, intent=intent, usage=usage)

    results = await asyncio.gather(*(_run_adapter(a, ctx) for a in REGISTRY.values()))
    status = {name: st for name, _, st in results}
    records = [r for _, recs, _ in results for r in recs]

    await profile_extractor.enrich(ctx, records)
    clusters = deduplication_service.resolve(records)
    await relevance_service.evaluate(clusters, intent, usage, warnings)

    keep = {"confirmed", "possible"} if include_possible else {"confirmed"}
    chosen = sorted((c for c in clusters if c.name and c.status in keep), key=lambda c: -c.score)[: s.max_prospects]
    prospects = []
    for c in chosen:
        links = _links(c, intent)
        if not links:
            continue
        p = Prospect(name=c.name, location=_location_label(c, intent), social_link=links)
        if include_evidence:
            p.evidence = ProspectEvidence(
                status=c.status, relevance_score=c.score, matched_signals=c.signals, evidence=c.evidence,
                merge_reasons=c.merge_reasons,
                sources=[SourceInfo(platform=r.platform, url=r.url, found_via=r.found_via, query=r.query)
                         for r in c.records])
        prospects.append(p)

    for name in ("Email", "WhatsApp", "Phone"):
        n = sum(1 for p in prospects for l in p.social_link if l.platform == name)
        if name in status:
            status[name] = f"{status[name]} ({n} found)"
    resp = DiscoveryResponse(query=query, total_prospects=len(prospects), prospects=prospects)
    meta = {"latency_ms": int((time.perf_counter() - t0) * 1000), "serp_calls": ctx.serp_calls,
            "site_fetches": ctx.site_fetches, "candidates": len(records), "clusters": len(clusters),
            **usage, "warnings": warnings}
    log.info("discovery q=%r prospects=%d meta=%s status=%s", query, len(prospects), meta, status)
    if include_evidence:
        resp.intent, resp.platform_status, resp.meta = intent, status, meta
    return resp
