import asyncio, ipaddress, re, socket
from urllib.parse import urlsplit, urlunsplit
from app.errors import InvalidURL, BlockedURL, SiteUnreachable

ALLOWED_SCHEMES = {"http", "https"}
ALLOWED_PORTS = {80, 443}

def normalize_url(raw: str) -> str:
    raw = (raw or "").strip()
    if not raw:
        raise InvalidURL("URL is required.")
    if "://" not in raw:
        if re.match(r"^[a-z][a-z0-9+.\-]*:(?!\d)", raw, re.I):   # javascript:, mailto:, data: …
            raise InvalidURL("Only http and https URLs are allowed.")
        raw = "https://" + raw                       # be forgiving: "example.com"
    p = urlsplit(raw)
    try:
        p.port                                        # raises on a malformed port
    except ValueError:
        raise InvalidURL("URL has an invalid port.")
    if p.scheme.lower() not in ALLOWED_SCHEMES:
        raise InvalidURL("Only http and https URLs are allowed.")
    if not p.hostname or not re.fullmatch(r"[a-z0-9.\-:]+", p.hostname):
        raise InvalidURL("URL must contain a valid hostname.")
    if p.username or p.password:
        raise InvalidURL("Credentials in URLs are not allowed.")
    return urlunsplit((p.scheme.lower(), p.netloc.lower(), p.path or "/", p.query, ""))

async def assert_public_host(url: str) -> None:
    p = urlsplit(url)
    port = p.port or (443 if p.scheme == "https" else 80)
    if port not in ALLOWED_PORTS:
        raise BlockedURL(f"Port {port} is not allowed.")
    try:
        infos = await asyncio.get_running_loop().getaddrinfo(p.hostname, port, proto=socket.IPPROTO_TCP)
    except socket.gaierror:
        raise SiteUnreachable("Domain could not be resolved (DNS failure).")
    for *_, sockaddr in infos:
        ip = ipaddress.ip_address(sockaddr[0].split("%")[0])
        if ip.version == 6 and ip.ipv4_mapped:       # ::ffff:127.0.0.1
            ip = ip.ipv4_mapped
        # is_global is False for private, loopback, link-local (169.254/fe80), CGNAT, ULA, 0.0.0.0, reserved
        if not ip.is_global or ip.is_multicast:
            raise BlockedURL("URL resolves to a private or internal network address.")
