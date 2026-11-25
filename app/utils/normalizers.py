"""Per-platform URL canonicalisation (profiles only) and SERP title parsing."""
import re
from urllib.parse import urlsplit, parse_qs

_RESERVED = {
    "Instagram": {"p", "reel", "reels", "explore", "stories", "accounts", "tv", "direct", "about", "developer"},
    "X": {"i", "search", "hashtag", "home", "intent", "share", "explore", "settings", "login", "tos", "privacy"},
    "Facebook": {"groups", "events", "watch", "share", "sharer", "sharer.php", "photo", "photo.php", "photos",
                 "story.php", "permalink.php", "login", "marketplace", "hashtag", "help", "policies", "public"},
    "Threads": set(),
}

def _host(u) -> str:
    return (u.hostname or "").lower().removeprefix("www.").removeprefix("m.")

def canonicalize(url: str) -> tuple[str, str, str] | None:
    """Return (platform, canonical_url, handle) for a PROFILE url, else None (posts, groups, search...)."""
    try:
        u = urlsplit(url.strip())
    except ValueError:
        return None
    if u.scheme not in ("http", "https"):
        return None
    host, path = _host(u), re.sub(r"/+$", "", u.path) or "/"
    parts = [p for p in path.split("/") if p]

    if host.endswith("linkedin.com") and len(parts) == 2 and parts[0] in ("in", "company"):
        slug = parts[1].lower()
        return "LinkedIn", f"https://www.linkedin.com/{parts[0]}/{slug}", slug
    if host == "instagram.com" and len(parts) == 1 and re.fullmatch(r"[A-Za-z0-9._]{1,30}", parts[0]) \
            and parts[0].lower() not in _RESERVED["Instagram"]:
        h = parts[0].lower()
        return "Instagram", f"https://www.instagram.com/{h}", h
    if host in ("x.com", "twitter.com") and len(parts) == 1 and re.fullmatch(r"\w{1,15}", parts[0]) \
            and parts[0].lower() not in _RESERVED["X"]:
        h = parts[0].lower()
        return "X", f"https://x.com/{h}", h
    if host.endswith("facebook.com"):
        if parts == ["profile.php"]:
            pid = parse_qs(u.query).get("id", [None])[0]
            return ("Facebook", f"https://www.facebook.com/profile.php?id={pid}", pid) if pid and pid.isdigit() else None
        if len(parts) == 1 and re.fullmatch(r"[A-Za-z0-9.\-]{3,}", parts[0]) \
                and parts[0].lower() not in _RESERVED["Facebook"]:
            h = parts[0].lower()
            return "Facebook", f"https://www.facebook.com/{h}", h
        if len(parts) >= 2 and parts[0] == "people":          # /people/Name/123
            return "Facebook", f"https://www.facebook.com/{'/'.join(parts[:3])}", parts[-1]
        return None
    if host == "youtube.com" and len(parts) >= 1:
        if re.fullmatch(r"@[A-Za-z0-9._\-]+", parts[0]):
            h = parts[0].lower()
            return "YouTube", f"https://www.youtube.com/{h}", h[1:]
        if parts[0] == "channel" and len(parts) >= 2 and re.fullmatch(r"UC[\w\-]{22}", parts[1]):
            return "YouTube", f"https://www.youtube.com/channel/{parts[1]}", parts[1]
        return None
    if host in ("threads.net", "threads.com") and len(parts) == 1 and re.fullmatch(r"@[A-Za-z0-9._]+", parts[0]):
        h = parts[0].lower()
        return "Threads", f"https://www.threads.com/{h}", h[1:]
    return None

# Directory / aggregator / news domains are never a prospect's own website
DIRECTORY_DOMAINS = {
    "yelp.com", "tripadvisor.com", "zomato.com", "justdial.com", "clutch.co", "crunchbase.com",
    "wikipedia.org", "facebook.com", "instagram.com", "linkedin.com", "x.com", "twitter.com",
    "youtube.com", "threads.net", "threads.com", "tiktok.com", "pinterest.com", "reddit.com",
    "google.com", "maps.google.com", "glassdoor.com", "indeed.com", "medium.com", "eventbrite.com",
    "meetup.com", "talabat.com", "deliveroo.ae", "swiggy.com", "opentable.com", "timeout.com",
}

def site_root(url: str) -> str | None:
    """Canonical homepage for an own-website candidate, or None for directories/social/news."""
    try:
        u = urlsplit(url)
    except ValueError:
        return None
    host = (u.hostname or "").lower().removeprefix("www.")
    if not host or u.scheme not in ("http", "https"):
        return None
    if any(host == d or host.endswith("." + d) for d in DIRECTORY_DOMAINS):
        return None
    return f"https://{host}/"

_SUFFIX = re.compile(r"\s*(\||•|·|-|–|—)\s*(LinkedIn|Instagram.*|Facebook|X|Twitter|Threads.*|YouTube)\s*$", re.I)
_HANDLE_FORM = re.compile(r"^(.*?)\s*\(@[\w.]+\)")
_BAD_NAMES = {"instagram", "facebook", "linkedin", "log in", "login", "sign up", "x", "threads", "youtube"}

def parse_name(platform: str, title: str) -> str | None:
    t = (title or "").strip()
    m = _HANDLE_FORM.match(t)                       # "Name (@handle) • Instagram ..." / "/ X" / "• Threads"
    if m:
        name = m.group(1)
    else:
        name = _SUFFIX.sub("", t)
        name = re.split(r"\s+(?:-|–|—|\|)\s+", name)[0]   # "Name - Headline - Company"
    name = re.sub(r"\s+", " ", name).strip(" -|•·")
    if not name or name.lower() in _BAD_NAMES or len(name) > 80:
        return None
    return name

def parse_linkedin_location(snippet: str) -> str | None:
    m = re.search(r"Location:\s*([^·\n|]+)", snippet or "")
    return m.group(1).strip() if m else None
