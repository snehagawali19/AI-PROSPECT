"""Enrich prospects' OWN websites: published emails, phones, WhatsApp links and outbound social profiles.
SSRF-guarded fetch; social platforms themselves are never fetched."""
import asyncio, json, logging
from collections import defaultdict
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from app.config import get_settings
from app.models import SourceRecord
from app.services.search_service import Ctx
from app.utils.contacts import clean_email, clean_phone, emails_in_text, whatsapp_from_link
from app.utils.fetch import allowed_by_robots, safe_fetch
from app.utils.normalizers import canonicalize

log = logging.getLogger("enrich")

def extract_from_html(html: str, base_url: str, region: str | None) -> tuple[list[tuple[str, str]], list[str]]:
    soup = BeautifulSoup(html, "lxml")
    contacts: list[tuple[str, str]] = []
    social: dict[str, set[str]] = defaultdict(set)
    for a in soup.find_all("a", href=True):
        href = urljoin(base_url, a["href"].strip())
        low = href.lower()
        if low.startswith("mailto:"):
            if (e := clean_email(href)):
                contacts.append(("Email", f"mailto:{e}"))
        elif low.startswith("tel:"):
            if (p := clean_phone(href, region)):
                contacts.append(("Phone", f"tel:{p}"))
        elif (w := whatsapp_from_link(href, region)):
            contacts.append(("WhatsApp", w))
        elif (c := canonicalize(href)):
            social[c[0]].add(c[1])
    for s in soup.find_all("script", type="application/ld+json"):     # schema.org email/telephone
        try:
            data = json.loads(s.string or "")
        except (ValueError, TypeError):
            continue
        for d in (data if isinstance(data, list) else [data]):
            if isinstance(d, dict):
                if isinstance(d.get("email"), str) and (e := clean_email(d["email"])):
                    contacts.append(("Email", f"mailto:{e}"))
                if isinstance(d.get("telephone"), str) and (p := clean_phone(d["telephone"], region)):
                    contacts.append(("Phone", f"tel:{p}"))
    for e in emails_in_text(soup.get_text(" ")[:20000]):
        contacts.append(("Email", f"mailto:{e}"))
    # A page linking SEVERAL profiles on one platform (team page, directory) is not a 1:1 identity signal.
    outbound = [next(iter(urls)) for urls in social.values() if len(urls) == 1]
    return list(dict.fromkeys(contacts)), outbound

async def enrich(ctx: Ctx, records: list[SourceRecord]) -> None:
    s = get_settings()
    sites = [r for r in records if r.platform == "Website" and r.url.startswith("https://")][: s.max_site_fetches]
    region = ctx.intent.location.country_code

    async def one(r: SourceRecord):
        try:
            if s.respect_robots_txt and not await allowed_by_robots(ctx.client, r.url):
                log.info("enrich skip %s: disallowed by robots.txt", r.url)
                return
            html, final = await safe_fetch(ctx.client, r.url, s.max_page_bytes)
            ctx.site_fetches += 1
            contacts, outbound = extract_from_html(html, final, region)
            r.contacts = list(dict.fromkeys(r.contacts + contacts))
            r.outbound += outbound
        except Exception as e:                      # one site failing never fails the request
            log.info("enrich skip %s: %s", r.url, type(e).__name__)

    await asyncio.gather(*(one(r) for r in sites))
