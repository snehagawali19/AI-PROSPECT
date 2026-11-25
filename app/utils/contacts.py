"""Contact extraction + validation. Nothing is ever guessed or constructed from unpublished data."""
import re
from urllib.parse import urlsplit, parse_qs, unquote
import phonenumbers
from email_validator import validate_email, EmailNotValidError

EMAIL_RX = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
_IMG = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg")
_BLOCKED_DOMAINS = {"example.com", "domain.com", "email.com", "sentry.io", "wixpress.com"}

def clean_email(raw: str) -> str | None:
    e = unquote(raw).strip().strip(".,;:()<>").lower()
    if e.startswith("mailto:"):
        e = e[7:].split("?")[0]
    if not e or e.endswith(_IMG) or e.split("@")[-1] in _BLOCKED_DOMAINS:
        return None
    try:
        return validate_email(e, check_deliverability=False).normalized.lower()
    except EmailNotValidError:
        return None

def clean_phone(raw: str, region: str | None) -> str | None:
    """Return E.164 if valid. If a region is given, the number must belong to it."""
    try:
        n = phonenumbers.parse(unquote(raw).replace("tel:", "").strip(), (region or "").upper() or None)
    except phonenumbers.NumberParseException:
        return None
    if not phonenumbers.is_valid_number(n):
        return None
    if region and phonenumbers.region_code_for_number(n) != region.upper():
        return None
    return phonenumbers.format_number(n, phonenumbers.PhoneNumberFormat.E164)

def whatsapp_from_link(href: str, region: str | None) -> str | None:
    """Only literal wa.me / api.whatsapp.com links published on the page → https://wa.me/<digits>."""
    try:
        u = urlsplit(href)
    except ValueError:
        return None
    host = (u.hostname or "").lower().removeprefix("www.")
    num = None
    if host == "wa.me":
        num = u.path.strip("/").split("/")[0]
    elif host in ("api.whatsapp.com", "whatsapp.com") and u.path.startswith("/send"):
        num = parse_qs(u.query).get("phone", [None])[0]
    if not num or not re.fullmatch(r"\+?\d{7,15}", num):
        return None
    e164 = clean_phone("+" + num.lstrip("+"), None)
    if not e164 or (region and phonenumbers.region_code_for_number(phonenumbers.parse(e164)) != region.upper()):
        return None
    return "https://wa.me/" + e164.lstrip("+")

def emails_in_text(text: str) -> list[str]:
    out = []
    for m in EMAIL_RX.findall(text or ""):
        if (e := clean_email(m)) and e not in out:
            out.append(e)
    return out
