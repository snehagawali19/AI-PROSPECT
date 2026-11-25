import pytest
from app.utils.normalizers import canonicalize, parse_name, site_root

@pytest.mark.parametrize("url,expected", [
    ("https://uk.linkedin.com/in/Jane-Doe-123?trk=x", ("LinkedIn", "https://www.linkedin.com/in/jane-doe-123", "jane-doe-123")),
    ("https://www.instagram.com/dc_soccer_fan/", ("Instagram", "https://www.instagram.com/dc_soccer_fan", "dc_soccer_fan")),
    ("https://twitter.com/JaneDoe", ("X", "https://x.com/janedoe", "janedoe")),
    ("https://www.youtube.com/@CricketGuru", ("YouTube", "https://www.youtube.com/@cricketguru", "cricketguru")),
    ("https://www.threads.net/@jane.doe", ("Threads", "https://www.threads.com/@jane.doe", "jane.doe")),
    ("https://m.facebook.com/profile.php?id=10001", ("Facebook", "https://www.facebook.com/profile.php?id=10001", "10001")),
])
def test_profiles_canonicalised(url, expected):
    assert canonicalize(url) == expected

@pytest.mark.parametrize("url", [
    "https://www.linkedin.com/posts/jane_activity-1", "https://www.linkedin.com/pulse/x",
    "https://www.instagram.com/p/Cxyz/", "https://www.instagram.com/reel/abc/",
    "https://x.com/jane/status/123", "https://x.com/search?q=a", "https://www.facebook.com/groups/dcfans",
    "https://www.youtube.com/watch?v=abc", "https://www.google.com/search?q=x", "ftp://x.com/a"])
def test_non_profiles_rejected(url):
    assert canonicalize(url) is None

def test_parse_names():
    assert parse_name("LinkedIn", "Jane Doe - Founder - Acme Ltd | LinkedIn") == "Jane Doe"
    assert parse_name("Instagram", "Jane Doe (@janedoe) • Instagram photos and videos") == "Jane Doe"
    assert parse_name("X", "Jane Doe (@janedoe) / X") == "Jane Doe"
    assert parse_name("Instagram", "Instagram") is None

def test_directories_are_not_own_sites():
    assert site_root("https://www.tripadvisor.com/Restaurant_Review-x") is None
    assert site_root("https://www.acme-bistro.ae/menu") == "https://acme-bistro.ae/"
