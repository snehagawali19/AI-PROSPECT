"""Section 5: relevance. Deterministic evidence first; one batched LLM call (IDs only, no URLs) refines it.
An LLM 'match' is accepted only if its evidence_quote is an exact substring of that candidate's text."""
import logging, re
from pathlib import Path
from app.config import get_settings
from app.models import Cluster
from app.schemas import Intent, RelevanceBatch
from app.services.llm_service import structured

log = logging.getLogger("relevance")
SYSTEM = (Path(__file__).resolve().parent.parent / "prompts" / "relevance_system.txt").read_text(encoding="utf-8")

def _find(text: str, terms: list[str]) -> str | None:
    for t in terms:
        if t and (m := re.search(rf"(?<!\w){re.escape(t)}(?!\w)", text, re.I)):
            s = max(0, m.start() - 40)
            return text[s:m.end() + 40].replace("\n", " ").strip()
    return None

def score_deterministic(c: Cluster, i: Intent) -> None:
    text = c.text
    loc_terms = i.location_aliases + [x for x in [i.location.city] if x]
    excluded = _find(text, i.location_exclusions)
    interest = _find(text, i.interest_keywords + [x for x in [i.interest, i.business_category] if x])
    role = _find(text, i.role_keywords) if i.role_keywords else None
    location = None if excluded else _find(text, loc_terms)
    if not location and any(r.found_via == "places" for r in c.records):   # Places is location-scoped
        location = next(r.location_text for r in c.records if r.found_via == "places")
    c.signals, c.evidence = [], []
    for label, q in (("interest", interest), ("audience_role", role), ("location", location)):
        if q:
            c.signals.append(label); c.evidence.append(f"{label}: “{q}”")
    if excluded:
        c.signals.append("location_excluded"); c.evidence.append(f"conflicting location: “{excluded}”")
    c.score = round(0.4 * bool(interest) + 0.2 * bool(role) + 0.3 * bool(location)
                    + 0.1 * (len(c.platforms) > 1), 2)

def _status(c: Cluster, i: Intent) -> str:
    has_topic = "interest" in c.signals or "audience_role" in c.signals
    if "location_excluded" in c.signals:
        return "rejected"
    return "confirmed" if has_topic and "location" in c.signals else "possible"

async def evaluate(clusters: list[Cluster], i: Intent, usage: dict, warnings: list[str]) -> None:
    for c in clusters:
        score_deterministic(c, i)
    pool = sorted([c for c in clusters if c.name and "location_excluded" not in c.signals],
                  key=lambda c: -c.score)[: get_settings().llm_batch_size]
    if pool:
        target = f"Audience: {i.audience}. Interest/category: {i.interest or i.business_category}. " \
                 f"Location: {i.location.city}, {i.location.state}, {i.location.country}. Target type: {i.target_type}."
        body = "\n".join(f"<candidate id={n}>\n{c.name}\n{c.text[:500]}\n</candidate>" for n, c in enumerate(pool))
        try:
            batch = await structured(SYSTEM, f"{target}\n\n{body}", RelevanceBatch, usage)
            for v in batch.verdicts:
                if not 0 <= v.id < len(pool):
                    continue
                c = pool[v.id]
                quote_ok = bool(v.evidence_quote.strip()) and v.evidence_quote.lower() in (c.name + "\n" + c.text).lower()
                if i.target_type == "individual" and v.entity_type in ("organization_page", "other"):
                    c.signals.append("not_an_individual")
                if quote_ok and v.interest_match and "interest" not in c.signals:
                    c.signals.append("interest"); c.evidence.append(f"interest (LLM, verified quote): “{v.evidence_quote}”")
                if quote_ok and v.location_match and "location" not in c.signals:
                    c.signals.append("location"); c.evidence.append(f"location (LLM, verified quote): “{v.evidence_quote}”")
                c.score = round(min(1.0, c.score + (0.1 if quote_ok and (v.interest_match or v.location_match) else 0)), 2)
        except Exception as e:
            warnings.append(f"LLM relevance unavailable; deterministic scoring only ({type(e).__name__}).")
    for c in clusters:
        c.status = "rejected" if "not_an_individual" in c.signals else _status(c, i)
