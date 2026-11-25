from typing import Literal
from pydantic import BaseModel, Field

# Spec platform names + "Phone" (spec rule 6 requires phones inside social_link; documented in README)
PlatformName = Literal["Google", "LinkedIn", "X", "YouTube", "Instagram", "WhatsApp",
                       "Facebook", "Email", "Threads", "Phone"]

# ---------- request ----------
class DiscoveryRequest(BaseModel):
    query: str = Field(..., min_length=3, max_length=200,
                       examples=["Football lovers in Washington DC in USA"])

# ---------- LLM: query understanding ----------
class Location(BaseModel):
    city: str | None
    state: str | None
    country: str | None
    country_code: str | None          # ISO-3166 alpha-2, e.g. "US", "GB", "IN", "AE"

class Intent(BaseModel):
    is_valid_query: bool              # false for gibberish / no audience
    interest: str | None
    audience: str
    target_type: Literal["individual", "business", "mixed"]
    location: Location
    location_aliases: list[str]       # e.g. ["Washington DC", "Washington, D.C.", "District of Columbia"]
    location_exclusions: list[str]    # e.g. ["Washington State", "Seattle"] — false-positive guards
    interest_keywords: list[str]      # synonyms, e.g. ["football", "soccer", "NFL", "DC United"]
    role_keywords: list[str]          # e.g. ["owner", "founder", "CEO"] (empty for hobby audiences)
    business_category: str | None     # e.g. "restaurant", "digital marketing agency"

# ---------- LLM: relevance ----------
class RelevanceVerdict(BaseModel):
    id: int
    entity_type: Literal["person", "business", "organization_page", "other"]
    interest_match: bool
    location_match: bool
    evidence_quote: str               # must be an exact substring of the candidate text

class RelevanceBatch(BaseModel):
    verdicts: list[RelevanceVerdict]

# ---------- API response (spec shape; extras only when include_evidence=true) ----------
class SocialLink(BaseModel):
    platform: PlatformName
    link: str

class SourceInfo(BaseModel):
    platform: str
    url: str
    found_via: str
    query: str

class ProspectEvidence(BaseModel):
    status: Literal["confirmed", "possible"]
    relevance_score: float
    matched_signals: list[str]
    evidence: list[str]
    merge_reasons: list[str]
    sources: list[SourceInfo]

class Prospect(BaseModel):
    name: str
    location: str | None = None
    social_link: list[SocialLink]
    evidence: ProspectEvidence | None = None

class DiscoveryResponse(BaseModel):
    success: Literal[True] = True
    query: str
    total_prospects: int
    prospects: list[Prospect]
    intent: Intent | None = None
    platform_status: dict[str, str] | None = None
    meta: dict | None = None

class ErrorBody(BaseModel):
    code: str
    message: str
    details: dict | None = None

class ErrorResponse(BaseModel):
    success: Literal[False] = False
    query: str | None = None
    error: ErrorBody
