from app.services.profile_extractor import extract_from_html

HTML = """<html><body>
<a href="mailto:hello@acme-bistro.ae">Email us</a> <a href="tel:+97122345678">Call</a>
<a href="https://wa.me/97122345678">WhatsApp</a>
<a href="https://www.instagram.com/acmebistro/">IG</a>
<a href="https://www.linkedin.com/in/staff-one">A</a> <a href="https://www.linkedin.com/in/staff-two">B</a>
<img src="logo@2x.png"></body></html>"""

def test_extracts_only_published_contacts_and_1to1_profiles():
    contacts, outbound = extract_from_html(HTML, "https://acme-bistro.ae/", "AE")
    assert ("Email", "mailto:hello@acme-bistro.ae") in contacts
    assert ("Phone", "tel:+97122345678") in contacts
    assert ("WhatsApp", "https://wa.me/97122345678") in contacts
    assert outbound == ["https://www.instagram.com/acmebistro"]   # 2 LinkedIn staff links = team page → ignored


import asyncio
import httpx
from app.utils import fetch as fetch_mod

def test_robots_txt_is_respected(monkeypatch):
    async def public(url): return None
    monkeypatch.setattr(fetch_mod, "assert_public_host", public)
    def handler(req):
        return httpx.Response(200, text="User-agent: *\nDisallow: /private\n")
    async def go():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as c:
            return (await fetch_mod.allowed_by_robots(c, "https://robots-test.example/"),
                    await fetch_mod.allowed_by_robots(c, "https://robots-test.example/private/page"))
    assert asyncio.run(go()) == (True, False)
