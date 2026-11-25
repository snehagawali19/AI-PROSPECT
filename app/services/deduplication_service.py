"""Section 3: entity resolution with union-find. Merge ONLY on hard identity signals.
Name + location similarity alone never merges (prefer a false split over a false merge)."""
from collections import defaultdict
from rapidfuzz import fuzz
from app.models import Cluster, SourceRecord
from app.utils.normalizers import canonicalize

NAME_PRIORITY = ["LinkedIn", "Website", "YouTube", "Facebook", "Instagram", "X", "Threads"]

class UnionFind:
    def __init__(self, n): self.p = list(range(n))
    def find(self, x):
        while self.p[x] != x:
            self.p[x] = self.p[self.p[x]]; x = self.p[x]
        return x
    def union(self, a, b) -> bool:
        ra, rb = self.find(a), self.find(b)
        if ra == rb: return False
        self.p[rb] = ra; return True

def _names_match(a: str | None, b: str | None) -> bool:
    return bool(a and b) and fuzz.token_sort_ratio(a.lower(), b.lower()) >= 85

def resolve(records: list[SourceRecord]) -> list[Cluster]:
    # 1) Outbound profiles from a prospect's own page become records too (owned_site provenance)
    by_url = {r.url: r for r in records}
    for r in list(records):
        for u in r.outbound:
            if u not in by_url:
                c = canonicalize(u)
                if c:
                    new = SourceRecord(platform=c[0], url=c[1], name=None, handle=c[2], text="",
                                       found_via="owned_site", query=f"linked from {r.url}", is_business=r.is_business)
                    records.append(new); by_url[new.url] = new

    idx = {id(r): i for i, r in enumerate(records)}
    uf, reasons = UnionFind(len(records)), defaultdict(list)

    def link(a, b, why):
        if uf.union(idx[id(a)], idx[id(b)]):
            reasons[(idx[id(a)], idx[id(b)])].append(why)

    # 2) Same canonical URL (same profile found by two queries)
    seen = {}
    for r in records:
        if r.url in seen: link(seen[r.url], r, "same canonical URL")
        else: seen[r.url] = r
    # 3) Explicit cross-link published on the prospect's own page / channel description
    for r in records:
        for u in r.outbound:
            if u in by_url: link(r, by_url[u], f"cross-link from {r.platform}")
    # 4) Same handle on two different platforms AND matching display name (≥85)
    by_handle = defaultdict(list)
    for r in records:
        if r.handle and len(r.handle) >= 4 and not r.handle.isdigit():
            by_handle[r.handle].append(r)
    for group in by_handle.values():
        for i, a in enumerate(group):
            for b in group[i + 1:]:
                if a.platform != b.platform and _names_match(a.name, b.name):
                    link(a, b, f"same handle '{a.handle}' + matching name")
    # 5) Same validated email / phone published by both
    by_contact = {}
    for r in records:
        for _, v in r.contacts:
            if v in by_contact and by_contact[v] is not r: link(by_contact[v], r, "same published contact")
            else: by_contact.setdefault(v, r)

    groups = defaultdict(list)
    for r in records:
        groups[uf.find(idx[id(r)])].append(r)
    clusters = []
    for root, recs in groups.items():
        members = {idx[id(r)] for r in recs}
        why = sorted({w for (a, b), ws in reasons.items() if a in members for w in ws})
        named = sorted((r for r in recs if r.name), key=lambda r: NAME_PRIORITY.index(r.platform)
                       if r.platform in NAME_PRIORITY else 99)
        clusters.append(Cluster(records=recs, merge_reasons=why, name=named[0].name if named else None))
    return clusters
