"""Google = discovery source. Business audiences: Places (name, address, website, phone) + open-web search
for businesses' OWN websites. Result-page/article/directory URLs are never emitted as prospects."""
from app.models import SourceRecord
from app.platforms.base import register
from app.services import query_service as qs
from app.services.search_service import Ctx, serper
from app.utils.contacts import clean_phone
from app.utils.normalizers import parse_name, site_root

class GoogleAdapter:
    name, method = "Google", "search_api_places_and_web"
    async def discover(self, ctx: Ctx) -> list[SourceRecord]:
        i, out = ctx.intent, []
        if (pq := qs.build_places_query(i)):
            data = await serper(ctx, "places", pq, qs.gl(i))
            for p in data.get("places", []):
                root = site_root(p.get("website") or "")
                rec = SourceRecord(platform="Website", url=root or f"place:{p.get('cid') or p.get('title')}",
                                   name=p.get("title"), handle=None, found_via="places", query=pq,
                                   text=f"{p.get('title', '')}\n{p.get('category', '')}\n{p.get('address', '')}",
                                   location_text=p.get("address"), is_business=True)
                if (ph := clean_phone(p.get("phoneNumber") or "", i.location.country_code)):
                    rec.contacts.append(("Phone", f"tel:{ph}"))
                out.append(rec)
        if (wq := qs.build_web_query(i)):
            data = await serper(ctx, "search", wq, qs.gl(i), num=10)
            for item in data.get("organic", []):
                root = site_root(item.get("link", ""))
                if not root or item.get("link", "").rstrip("/").count("/") > 3:   # homepages / shallow pages only
                    continue
                name = parse_name("Google", item.get("title", ""))
                if name:
                    out.append(SourceRecord(platform="Website", url=root, name=name, handle=None,
                                            text=f"{item.get('title', '')}\n{item.get('snippet', '')}",
                                            found_via="serp", query=wq, is_business=True))
        return out

adapter = register(GoogleAdapter())
