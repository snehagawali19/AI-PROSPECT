"""YouTube Data API v3 — official API: search.list(type=channel) + one batched channels.list."""
from app.models import SourceRecord
from app.platforms.base import register
from app.services import query_service as qs
from app.services.search_service import Ctx, youtube
from app.utils.contacts import emails_in_text
from app.utils.normalizers import canonicalize

class YouTubeAdapter:
    name, method = "YouTube", "official_api"
    async def discover(self, ctx: Ctx) -> list[SourceRecord]:
        q = qs.build_youtube_query(ctx.intent)
        params = {"part": "snippet", "type": "channel", "q": q, "maxResults": 15}
        if ctx.intent.location.country_code:
            params["regionCode"] = ctx.intent.location.country_code.upper()
        found = await youtube(ctx, "search", params)
        ids = [it["snippet"]["channelId"] for it in found.get("items", []) if it.get("snippet", {}).get("channelId")]
        if not ids:
            return []
        ch = await youtube(ctx, "channels", {"part": "snippet", "id": ",".join(ids[:50])})
        out = []
        for c in ch.get("items", []):
            sn = c.get("snippet", {})
            handle = (sn.get("customUrl") or "").lower()
            url = f"https://www.youtube.com/{handle}" if handle.startswith("@") else f"https://www.youtube.com/channel/{c['id']}"
            desc = sn.get("description", "")
            rec = SourceRecord(platform="YouTube", url=url, name=sn.get("title"), handle=handle.lstrip("@") or c["id"],
                               text=f"{sn.get('title', '')}\n{desc}\nCountry: {sn.get('country', '')}",
                               found_via="official_api", query=q, location_text=sn.get("country"))
            rec.contacts += [("Email", f"mailto:{e}") for e in emails_in_text(desc)]
            for token in desc.split():                       # profile links published in the description
                if token.startswith("http") and (cc := canonicalize(token.strip(".,)("))) and cc[0] != "YouTube":
                    rec.outbound.append(cc[1])
            out.append(rec)
        return out

adapter = register(YouTubeAdapter())
