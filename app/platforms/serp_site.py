"""Generic site:-restricted discovery via an authorized SERP API. Never fetches the social site itself."""
from app.models import SourceRecord
from app.services import query_service as qs
from app.services.search_service import Ctx, serper
from app.utils.contacts import emails_in_text
from app.utils.normalizers import canonicalize, parse_linkedin_location, parse_name

class SiteSearchAdapter:
    method = "search_api_site_query"
    def __init__(self, name: str):
        self.name = name

    async def discover(self, ctx: Ctx) -> list[SourceRecord]:
        q = qs.build_site_query(ctx.intent, self.name)
        data = await serper(ctx, "search", q, qs.gl(ctx.intent), num=10)
        out = []
        for item in data.get("organic", []):
            c = canonicalize(item.get("link", ""))
            if not c or c[0] != self.name:          # drop posts, groups, wrong platform
                continue
            platform, url, handle = c
            title, snippet = item.get("title", ""), item.get("snippet", "")
            name = parse_name(platform, title)
            if not name:
                continue
            loc = parse_linkedin_location(snippet) if platform == "LinkedIn" else None
            rec = SourceRecord(platform=platform, url=url, name=name, handle=handle,
                               text=f"{title}\n{snippet}", found_via="serp", query=q, location_text=loc,
                               is_business=url.startswith("https://www.linkedin.com/company/"))
            rec.contacts += [("Email", f"mailto:{e}") for e in emails_in_text(snippet)]
            out.append(rec)
        return out
