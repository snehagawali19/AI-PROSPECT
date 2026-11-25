"""Internal models — never returned directly. Every datum keeps its provenance."""
from dataclasses import dataclass, field

@dataclass
class SourceRecord:
    platform: str                      # spec platform name, or "Website" (own site found via Google)
    url: str                           # canonical URL
    name: str | None
    handle: str | None
    text: str                          # title + snippet/bio/address — the ONLY evidence text
    found_via: str                     # serp | official_api | places | owned_site
    query: str
    location_text: str | None = None
    is_business: bool = False
    outbound: list[str] = field(default_factory=list)              # canonical profile URLs on its own page
    contacts: list[tuple[str, str]] = field(default_factory=list)  # ("Email","mailto:..") ("Phone","tel:+..")

@dataclass
class Cluster:
    records: list[SourceRecord]
    merge_reasons: list[str] = field(default_factory=list)
    name: str | None = None
    score: float = 0.0
    status: str = "possible"
    signals: list[str] = field(default_factory=list)
    evidence: list[str] = field(default_factory=list)
    location: str | None = None

    @property
    def text(self) -> str:
        return "\n".join(r.text for r in self.records if r.text)

    @property
    def platforms(self) -> set[str]:
        return {r.platform for r in self.records}
