from app.models import SourceRecord
from app.services.deduplication_service import resolve

def rec(platform, url, name, handle=None, **kw):
    return SourceRecord(platform=platform, url=url, name=name, handle=handle, text=name or "",
                        found_via="serp", query="q", **kw)

def test_same_handle_and_name_merges():
    cl = resolve([rec("Instagram", "https://www.instagram.com/janedoe_dc", "Jane Doe", "janedoe_dc"),
                  rec("X", "https://x.com/janedoe_dc", "Jane Doe", "janedoe_dc")])
    assert len(cl) == 1 and "matching name" in cl[0].merge_reasons[0]

def test_same_name_different_people_not_merged():
    cl = resolve([rec("LinkedIn", "https://www.linkedin.com/in/john-smith-1", "John Smith", "john-smith-1"),
                  rec("Instagram", "https://www.instagram.com/jsmith_dc", "John Smith", "jsmith_dc")])
    assert len(cl) == 2

def test_same_handle_different_names_not_merged():
    cl = resolve([rec("Instagram", "https://www.instagram.com/thechef", "Ali Khan", "thechef"),
                  rec("X", "https://x.com/thechef", "Maria Lopez", "thechef")])
    assert len(cl) == 2

def test_cross_link_from_own_site_merges_and_adds_profile():
    site = rec("Website", "https://acme-bistro.ae/", "Acme Bistro", is_business=True,
               outbound=["https://www.instagram.com/acmebistro"])
    cl = resolve([site])
    assert len(cl) == 1 and {r.platform for r in cl[0].records} == {"Website", "Instagram"}
