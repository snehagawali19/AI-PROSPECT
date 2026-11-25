"""End-to-end with all external calls mocked: no network, no keys."""
from fastapi.testclient import TestClient
from app.main import app
from app.schemas import Intent, Location, RelevanceBatch, RelevanceVerdict
from app.services import query_service, search_service, relevance_service

INTENT = Intent(is_valid_query=True, interest="Restaurants", audience="Restaurant owners", target_type="business",
                location=Location(city="Dubai", state="Dubai", country="United Arab Emirates", country_code="AE"),
                location_aliases=["Dubai"], location_exclusions=["Abu Dhabi"], interest_keywords=["restaurant"],
                role_keywords=["owner", "founder", "restaurateur"], business_category="restaurant")

SERP = {
  "places": {"places": [{"title": "Acme Bistro", "address": "Jumeirah, Dubai, UAE", "category": "Restaurant",
                         "website": "https://acme-bistro.ae/", "phoneNumber": "+971 2 234 5678"}]},
  "search": {"organic": [
      {"title": "Sara Ali - Founder & Owner - Acme Bistro | LinkedIn", "link": "https://ae.linkedin.com/in/sara-ali-1",
       "snippet": "Restaurant owner. Location: Dubai, United Arab Emirates · 500+ connections"},
      {"title": "Some post", "link": "https://www.linkedin.com/posts/x_activity-1", "snippet": "Dubai restaurant"},
      {"title": "Abu Dhabi Eats (@ad_eats) • Instagram photos and videos", "link": "https://www.instagram.com/ad_eats/",
       "snippet": "Restaurant owner in Abu Dhabi"}]},
}

def install_fakes(monkeypatch):
    async def fake_intent(q, usage): return INTENT
    async def fake_serper(ctx, endpoint, q, gl, num=None): return SERP[endpoint]
    async def fake_youtube(ctx, method, params): raise search_service.NotConfigured()
    async def fake_structured(system, user, schema, usage):
        return RelevanceBatch(verdicts=[])
    monkeypatch.setattr("app.services.prospect_service.parse_intent", fake_intent)
    for mod in ("app.platforms.serp_site", "app.platforms.google"):
        monkeypatch.setattr(f"{mod}.serper", fake_serper)
    monkeypatch.setattr("app.platforms.youtube.youtube", fake_youtube)
    monkeypatch.setattr(relevance_service, "structured", fake_structured)
    async def no_enrich(ctx, records): pass
    monkeypatch.setattr("app.services.prospect_service.profile_extractor.enrich", no_enrich)

def test_spec_shape_and_no_junk(monkeypatch):
    install_fakes(monkeypatch)
    with TestClient(app) as c:
        r = c.post("/prospect-discovery", json={"query": "Restaurant owners in Dubai UAE"})
    body = r.json()
    assert r.status_code == 200 and set(body) == {"success", "query", "total_prospects", "prospects"}
    names = {p["name"] for p in body["prospects"]}
    assert "Sara Ali" in names and "Acme Bistro" in names
    assert "Abu Dhabi Eats" not in names                                  # excluded location
    links = [l["link"] for p in body["prospects"] for l in p["social_link"]]
    assert all("/posts/" not in l for l in links)
    acme = next(p for p in body["prospects"] if p["name"] == "Acme Bistro")
    assert {"platform": "Phone", "link": "tel:+97122345678"} in acme["social_link"]
    assert body["total_prospects"] == len(body["prospects"])

def test_evidence_mode(monkeypatch):
    install_fakes(monkeypatch)
    with TestClient(app) as c:
        r = c.post("/prospect-discovery?include_evidence=true", json={"query": "Restaurant owners in Dubai UAE"})
    b = r.json()
    assert b["platform_status"]["YouTube"] == "not_configured"
    assert all(p["evidence"]["status"] == "confirmed" for p in b["prospects"])

def test_validation_error():
    with TestClient(app) as c:
        r = c.post("/prospect-discovery", json={"query": "a"})
    assert r.status_code == 422 and r.json()["error"]["code"] == "VALIDATION_ERROR"

def test_health_reports_config_without_secrets():
    with TestClient(app) as c:
        r = c.get("/health")
    body = r.json()
    assert r.status_code == 200 and body["status"] == "ok"
    assert set(body["configured"]) == {"serper", "youtube", "anthropic", "gemini", "primary_model", "fallback_model"}
    assert all(isinstance(v, bool) for v in body["configured"].values())

def test_placeholder_keys_count_as_unconfigured():
    from app.config import is_configured
    assert not is_configured("YOUR_SERPER_API_KEY_HERE")
    assert not is_configured("REPLACE_WITH_PRIMARY_MODEL_ID")
    assert not is_configured("")
    assert is_configured("sk-real-looking-value")
