# AI-Powered Multi-Platform Prospect Discovery API

This is a FastAPI service. You send it a natural-language request such as *"Restaurant owners in Dubai UAE"* and it returns **real, public prospects** with their profile links and any contact details they have **published**. Results are pulled together from Google, LinkedIn, X, YouTube, Instagram, Facebook, Threads, Email and WhatsApp, using authorized sources only. Names, links and contacts are never invented.

- **Endpoint:** `POST /prospect-discovery`, port **4000**
- **Docs:** `http://localhost:4000/docs`
- **Health:** `http://localhost:4000/health`

> **Status of this package:** the code is complete and the test suite passes (**32/32**, with every external call mocked). Live discovery has **not** been run yet. It needs real API keys, so do it on the target device by following §2–§4 below.

---

## Contents

1. [Project architecture overview](#1-project-architecture-overview)
2. [Configuration step (.env)](#2-configuration-step-env)
3. [One-command run](#3-one-command-run)
4. [Verification / smoke test](#4-verification--smoke-test)
5. [API contract](#5-api-contract)
6. [How discovery works](#6-how-discovery-works)
7. [Platform coverage and what is not integrated](#7-platform-coverage-and-what-is-not-integrated)
8. [Test queries and results](#8-test-queries-and-results)
9. [LLM research and model recommendation](#9-llm-research-and-model-recommendation)
10. [Ethics, privacy and compliance](#10-ethics-privacy-and-compliance)
11. [Limitations and next steps](#11-limitations-and-next-steps)
12. [Tests](#12-tests)

---

## 1. Project architecture overview

```text
ai-prospect-discovery/
├── app/                              # The FastAPI application
│   ├── main.py                       # App, lifespan (shared httpx client), error handlers, rate limit, routes
│   ├── config.py                     # All settings from env/.env (keys, models, prices, budgets); placeholder detection
│   ├── schemas.py                    # Pydantic: request, spec-shaped response, LLM schemas (Intent, RelevanceBatch), errors
│   ├── models.py                     # Internal SourceRecord / Cluster: every datum keeps its provenance
│   ├── errors.py                     # AppError hierarchy → consistent JSON error envelope
│   ├── prompts/
│   │   ├── intent_system.txt         # Prompt: query → structured Intent (location resolution, aliases, exclusions)
│   │   └── relevance_system.txt      # Prompt: batched relevance verdicts by candidate ID (untrusted-data guard)
│   ├── services/
│   │   ├── llm_service.py            # Anthropic + Gemini adapters; structured() = primary → repair retry → fallback vendor
│   │   ├── query_service.py          # parse_intent() (cached) + deterministic platform query builders
│   │   ├── search_service.py         # Serper + YouTube clients, per-request budget, 429/5xx retry, TTL cache
│   │   ├── profile_extractor.py      # Fetch prospects' OWN websites (SSRF-safe, robots.txt) → published contacts + social links
│   │   ├── deduplication_service.py  # Union-find entity resolution on hard identity signals only
│   │   ├── relevance_service.py      # Deterministic evidence scoring + LLM verdicts (quote must be an exact substring)
│   │   └── prospect_service.py       # Pipeline glue: intent → parallel discovery → enrich → dedupe → relevance → response
│   ├── platforms/                    # One pluggable module per platform (registry pattern)
│   │   ├── base.py                   # PlatformAdapter protocol + REGISTRY + @register
│   │   ├── serp_site.py              # Generic site:-search adapter (used by LinkedIn/Instagram/Facebook/X/Threads)
│   │   ├── linkedin.py instagram.py facebook.py x_platform.py threads.py   # Register the generic adapter per platform
│   │   ├── youtube.py                # YouTube Data API v3 (official): search.list + channels.list
│   │   ├── google.py                 # Google as a discovery source: Places + web search → businesses' own websites
│   │   └── whatsapp.py email.py      # Honest "extracted only from published pages" adapters
│   └── utils/
│       ├── validators.py             # URL normalisation + SSRF guard (blocks private/loopback/metadata IPs)
│       ├── fetch.py                  # safe_fetch (per-hop redirect validation, size/time caps) + robots.txt check
│       ├── normalizers.py            # Profile-URL canonicalisation per platform + SERP title/name parsing
│       ├── contacts.py               # Email / phone (E.164, country check) / WhatsApp link validation
│       └── cache.py                  # Small in-memory TTL cache
├── tests/                            # pytest suite, fully mocked (no network, no keys)
├── scripts/
│   ├── check_keys.py                 # 1 live call per integration → OK / FAIL / SKIP
│   ├── list_models.py                # Lists model IDs your Anthropic / Gemini keys can use
│   ├── run_test_queries.py           # Runs the 5 spec queries + 1 unseen → samples/*.json + samples/RESULTS.md
│   ├── smoke_test.sh / smoke_test.ps1# Endpoint smoke tests (bash / PowerShell)
│   └── run_local.sh / run_local.ps1  # Run without Docker (venv → tests → server)
├── samples/                          # Output of run_test_queries (empty until the first live run)
├── docs/
│   ├── SPEC.md                       # The original assignment specification
│   ├── BUILD_GUIDE.md                # The build guide this implementation follows
│   └── screenshots/                  # Add screenshots after the live run
├── Dockerfile                        # python:3.12-slim, non-root user, healthcheck, entrypoint
├── docker-entrypoint.sh              # "serve" (default) → uvicorn on $PORT (4000); any other args are run as a command
├── docker-compose.yml                # One service "api", port 4000:4000, env from .env, ./samples mounted
├── .dockerignore  .gitignore  .gitattributes
├── .env.example                      # Template of every variable (documented)
├── .env                              # Pre-filled with dummy values — replace before launch (never commit)
├── requirements.txt                  # Pinned runtime dependencies
├── requirements-dev.txt              # + pytest
├── pytest.ini
└── .github/workflows/tests.yml       # CI: run pytest on push
```

**A note on the build guide:** `docs/BUILD_GUIDE.md` was the design document. This package follows it and adds a few things for handoff:

- prices and model IDs are set through environment variables
- placeholder keys are detected and treated as missing
- robots.txt is respected when fetching websites
- `/health` reports which integrations are configured
- helper scripts and the container setup

Where the two differ, **the code in this package is authoritative**.

---

## 2. Configuration step (.env)

All secrets and environment-specific values live in **one file**, `.env`, in the project root. Docker Compose loads it through `env_file`, and running without Docker loads it through pydantic-settings. Any value that starts with `YOUR_` or `REPLACE_` is treated as **not configured**.

**Variables you must update before launch:**

| Variable | What to put there | Where to get it |
|---|---|---|
| `SERPER_API_KEY` | Serper API key | https://serper.dev (2,500 free queries) |
| `YOUTUBE_API_KEY` | Google API key with **YouTube Data API v3** enabled | Google Cloud Console → APIs & Services → enable YouTube Data API v3 → Credentials → API key |
| `ANTHROPIC_API_KEY` | Anthropic key | https://console.anthropic.com |
| `GEMINI_API_KEY` | Gemini key | https://aistudio.google.com |
| `PRIMARY_MODEL` | Exact model ID of a **Claude Haiku-class** model | Run `python -m scripts.list_models` once the keys are set |
| `FALLBACK_MODEL` | Exact model ID of a **Gemini Flash-Lite-class** model | Same command |

**Recommended** (used only for cost reporting in `meta`):

- `PRIMARY_PRICE_IN_PER_M`, `PRIMARY_PRICE_OUT_PER_M`, `FALLBACK_PRICE_IN_PER_M`, `FALLBACK_PRICE_OUT_PER_M`
- Use USD per 1M tokens, taken from the providers' official pricing pages on the day you run it.

**Optional:**

- `PRIMARY_PROVIDER` / `FALLBACK_PROVIDER`: `anthropic` or `gemini`. Swap them to change which vendor is primary.
- Budgets and limits, with defaults: `MAX_SERP_CALLS=12`, `MAX_SITE_FETCHES=8`, `RATE_LIMIT=10/minute`, `CACHE_TTL_S=21600`, `RESPECT_ROBOTS_TXT=true`.

**Before going public, set spend caps** on your Anthropic, Google Cloud and Serper accounts. Never commit `.env`; it is already listed in `.gitignore` and `.dockerignore`.

---

## 3. One-command run

### With Docker (recommended)

Requires Docker Desktop on Windows/macOS, or Docker Engine with the Compose plugin on Linux.

```bash
docker compose up --build
```

The API is then available at **http://localhost:4000**. Add `-d` to run it in the background. Other useful commands:

```bash
docker compose logs -f api                                # follow logs
docker compose run --rm api pytest                        # run the test suite inside the image
docker compose run --rm api python -m scripts.list_models # list usable model IDs for your keys
docker compose run --rm api python -m scripts.check_keys  # 1 live call per integration
docker compose down                                       # stop
```

After you edit `.env`, apply the change with `docker compose up -d --force-recreate`. A rebuild is not needed.

### Without Docker

Requires Python 3.10+.

```powershell
# Windows PowerShell
.\scripts\run_local.ps1
```
```bash
# macOS / Linux
./scripts/run_local.sh
```

Both scripts create a `.venv`, install `requirements-dev.txt`, run the tests and start `uvicorn app.main:app --host 0.0.0.0 --port 4000`.

### Deploying publicly (e.g. Render)

1. Push the repo to GitHub.
2. In Render: **New → Web Service** → pick the repo. It detects the Dockerfile.
3. Add the variables from §2 under **Environment**.
4. Set the health check path to `/health`.

The container reads `$PORT`, so it works on platforms that assign their own port. On the free tier the service sleeps when idle, so open `/docs` once before you share the link.

---

## 4. Verification / smoke test

**1. Health and configuration.** Secrets are never shown here; only true/false.
```bash
curl http://localhost:4000/health
```
Expected output is `{"status":"ok","configured":{"serper":true,"youtube":true,"anthropic":true,...},...}`. Any `false` means that `.env` value is still a placeholder.

**2. Key check.** This makes 1 live call per service:
```bash
docker compose run --rm api python -m scripts.check_keys
```
Expected output is one `[ OK ]` line per configured service.

**3. Endpoint smoke tests:**
```bash
./scripts/smoke_test.sh                   # macOS/Linux (curl)
```
```powershell
.\scripts\smoke_test.ps1                  # Windows PowerShell
```
These check `/health`, `/docs` and `/openapi.json`, two 422 validation cases, and one live discovery.

**4. Manual discovery request:**
```bash
curl -s -X POST http://localhost:4000/prospect-discovery \
  -H "Content-Type: application/json" \
  -d '{"query": "Restaurant owners in Dubai UAE"}'
```
In PowerShell:
```powershell
Invoke-RestMethod -Method Post -Uri http://localhost:4000/prospect-discovery `
  -ContentType "application/json" -Body '{"query": "Restaurant owners in Dubai UAE"}' | ConvertTo-Json -Depth 6
```

**5. Evidence mode.** This shows sources, signals, merge reasons, per-platform status, tokens and latency:
```bash
curl -s -X POST "http://localhost:4000/prospect-discovery?include_evidence=true" \
  -H "Content-Type: application/json" -d '{"query": "Startup founders in London UK"}'
```

**6. The assignment's test queries:**
```bash
python -m scripts.run_test_queries http://localhost:4000
```
This writes `samples/q1..q6.json`, `samples/q*_evidence.json` and `samples/RESULTS.md`. Running it from the host needs only `pip install httpx`.

| Result | Meaning |
|---|---|
| `200` with `total_prospects: 0` | Search keys are missing or rejected. Check `platform_status` in evidence mode |
| `503 LLM_UNAVAILABLE` | LLM keys or model IDs are not set or are invalid |
| `429` | Rate limit reached (`RATE_LIMIT`) |

---

## 5. API contract

### Request
```http
POST /prospect-discovery
Content-Type: application/json

{"query": "Football lovers in Washington DC in USA"}
```
| Query parameter | Default | Effect |
|---|---|---|
| `include_evidence` | `false` | Adds `prospects[].evidence` (status, score, signals, quotes, merge reasons, sources), plus `intent`, `platform_status` and `meta` (latency, search calls, tokens, cost) |
| `include_possible` | `false` | Also returns prospects with partial evidence (`status: "possible"`) |

### Default response (exact spec shape)

The structure is shown below. Values in `<…>` are filled from real discovery results.
```json
{
  "success": true,
  "query": "Restaurant owners in Dubai UAE",
  "total_prospects": 1,
  "prospects": [
    {
      "name": "<name parsed from the source>",
      "location": "<location from snippet / Places address>",
      "social_link": [
        {"platform": "Google",    "link": "<business's own website>"},
        {"platform": "Instagram", "link": "https://www.instagram.com/<handle>"},
        {"platform": "Email",     "link": "mailto:<published address>"},
        {"platform": "Phone",     "link": "tel:+<E.164 number>"},
        {"platform": "WhatsApp",  "link": "https://wa.me/<published number>"}
      ]
    }
  ]
}
```
**Platform names:** `Google`, `LinkedIn`, `X`, `YouTube`, `Instagram`, `WhatsApp`, `Facebook`, `Email`, `Threads`, plus **`Phone`**. The spec's rule 6 requires phone numbers inside `social_link`, but its platform list has no phone entry, so `Phone` is the one addition.

### Errors

Every error uses the same JSON envelope:
```json
{"success": false, "error": {"code": "VALIDATION_ERROR", "message": "...", "details": {}}}
```
| HTTP | `code` | When |
|---|---|---|
| 422 | `VALIDATION_ERROR` | Body missing or invalid; query must be 3–200 characters |
| 422 | `INVALID_QUERY` | No identifiable audience in the query |
| 429 | `RATE_LIMITED` | Too many requests from one IP |
| 503 | `LLM_UNAVAILABLE` | Primary, retry and fallback LLM all failed or are not configured |
| 500 | `INTERNAL_ERROR` | Unexpected; details go to the logs only |

If every platform fails, the API still returns `200` with zero prospects. In evidence mode, `platform_status` explains why.

---

## 6. How discovery works

```
query ─► 1. LLM → Intent (audience, interest synonyms, city/state/country + ISO code, aliases, look-alike exclusions, individual|business|mixed)
       ─► 2. deterministic query templates (no hard-coded queries; the LLM only supplies synonyms/aliases)
       ─► 3. 9 platform adapters in parallel (per-adapter timeout, retry on 429/5xx, status per platform, ≤12 search calls)
       ─► 4. enrichment: ≤8 prospects' OWN websites (SSRF guard, robots.txt, 1 MB/8 s caps) → mailto / tel / wa.me / JSON-LD / social links
       ─► 5. entity resolution (union-find)
       ─► 6. relevance (deterministic evidence + 1 batched LLM call by ID, quote-verified)
       ─► 7. spec-shaped JSON (confirmed prospects only by default)
```

**Profile validation (`normalizers.canonicalize`).** Only profile URLs are accepted:

| Platform | Accepted | Rejected |
|---|---|---|
| LinkedIn | `/in/<slug>`, `/company/<slug>` | `/posts/`, `/pulse/` |
| Instagram | `/<handle>` | `/p/`, `/reel/`, `/explore/` |
| X | `/<handle>` | `/status/`, `/search`, `/hashtag` |
| Facebook | `/<page>`, `profile.php?id=` | `/groups/`, `/events/`, `/watch` |
| YouTube | `/@handle`, `/channel/UC…` | `/watch` |
| Threads | `/@handle` | — |

URLs are canonicalised: lowercase handles, tracking parameters removed, locale subdomains folded. Google result pages, articles and directories (Yelp, Tripadvisor, Justdial and others) are never returned as prospects.

**Contact validation (`utils/contacts.py`):**

- **Email:** syntax check with `email-validator`. Image-filename false positives and placeholder domains are rejected. Addresses are never guessed.
- **Phone:** `phonenumbers` validity check plus a match against the query's country, then formatted as E.164.
- **WhatsApp:** a link is returned **only** if it was published on the page as a `wa.me` or `api.whatsapp.com` link. It is never built from an ordinary phone number.
- For hobby/individual audiences, personal phone numbers are dropped entirely.

**Duplicate detection (`deduplication_service.resolve`).** Records are merged into one prospect only on hard identity signals:

| Signal | Merges? |
|---|---|
| Same canonical URL | ✅ |
| Profile linked from the prospect's own website or channel description (exactly one link per platform; team and directory pages are ignored) | ✅ |
| Same handle on two platforms **and** display names ≥ 85% similar | ✅ |
| Same published email or phone | ✅ |
| Same name + same city | ❌ never on its own. A missed merge is preferred over merging two different people |

**Relevance (`relevance_service`):**

| Status | Rule |
|---|---|
| `confirmed` (returned by default) | Quoted evidence of interest, role or business category **and** of location, or a location-scoped Places result |
| `possible` (only with `include_possible=true`) | Partial evidence |
| `rejected` | Text contains an excluded look-alike place (e.g. Washington State, London Ontario, Abu Dhabi), or the LLM classifies it as a club, fan page or venue when the audience is individuals |

The relevance LLM sees candidates **by numeric ID only**. Its `evidence_quote` must be an **exact substring** of that candidate's text, otherwise it is ignored. As a result, the LLM can never add a link, a name or a contact.

---

## 7. Platform coverage and what is not integrated

| Platform | Status | How |
|---|---|---|
| Google | ✅ Integrated | Serper `places` + web search → businesses' own websites (directories and articles excluded) |
| YouTube | ✅ Integrated (official API) | YouTube Data API v3: `search.list` (type=channel) + `channels.list` |
| LinkedIn | 🟡 Via search API | `site:linkedin.com/in` + title/snippet parsing |
| Instagram | 🟡 Via search API | `site:instagram.com`, posts and reels excluded |
| Facebook | 🟡 Via search API | `site:facebook.com`, groups, posts and events excluded |
| X | 🟡 Via search API | `site:x.com` / `twitter.com`, status URLs excluded |
| Threads | 🟡 Via search API | `site:threads.com` / `threads.net` |
| Email | 🟢 Extracted | `mailto:`, JSON-LD, page text, YouTube descriptions, snippets |
| WhatsApp | 🟢 Extracted | Only literal `wa.me` / `api.whatsapp.com` links published by the prospect |

**Not integrated natively, and why:**

- **LinkedIn API:** there is no public people search; it is partner programmes only.
- **Instagram and Facebook (Meta Graph API):** Business Discovery needs a known username, an owned Instagram Business account and app review. There is no keyword search for users.
- **X API:** user search is on paid tiers.
- **Threads API:** keyword search requires app review.
- **WhatsApp:** there is no discovery API at all. The Business API only messages users who opted in.

All of these are covered through public search-engine indexes instead. Profiles are **never** scraped and logins are never bypassed.

**Search sources considered:**

- Google Custom Search JSON API is closed to new customers.
- Bing Search API has been retired.
- **Serper** is the one used. It returns Google results through a third-party provider, a legal grey area that this README discloses.
- **Brave Search API** (its own index) is the drop-in alternative: swap the client in `search_service.py`.

---

## 8. Test queries and results

Run `python -m scripts.run_test_queries` after configuring the keys (§4, step 6). Then paste `samples/RESULTS.md` here, link `samples/q1.json` … `q6.json`, and add honest notes where results are thin.

| # | Query | Expected audience |
|---|---|---|
| 1 | Football lovers in Washington DC in USA | Football enthusiasts (individuals) |
| 2 | Digital marketing agency owners in New York USA | Marketing business owners |
| 3 | Startup founders in London UK | Startup founders |
| 4 | Cricket lovers in Ahmedabad India | Cricket enthusiasts (individuals) |
| 5 | Restaurant owners in Dubai UAE | Restaurant business owners |
| 6 | Yoga instructors in Bangalore India | Unseen query (shows nothing is hard-coded) |

*Results: generated on the target device. Nothing has been pre-filled or invented.*

---

## 9. LLM research and model recommendation

**Re-check every price on the official pricing pages before publishing, and note the date you checked.** The snapshot below dates from 24 Nov 2026. Anthropic and Gemini figures came from their official pages; the OpenAI figure came from an aggregator and must be verified.

| Provider | Model class | USD per 1M tokens (in / out) | Context | Structured output | Est. cost / request* |
|---|---|---|---|---|---|
| Anthropic | Claude Haiku 5.5 | $0.10 / $0.50 | 1M | Forced tool call with JSON schema | ≈ $0.002 |
| Google | Gemini 3.5 Flash-Lite | $0.30 / $2.50 | ~1M | Native `response_schema` (Pydantic) | ≈ $0.009 |
| Google | Gemini 3.8 Flash | $0.75 / $3.75 (promo to 31 Dec 2026) | ~1M | Native `response_schema` | ≈ $0.015 |
| OpenAI | Small GPT-6-class (aggregator; verify) | ≈ $0.10 / $0.50 | ~1M | Strict `json_schema` | ≈ $0.002 |

\*Estimated per request: one intent call (about 700 in / 250 out tokens) plus one relevance batch (≤ 40 candidates, about 6.4k in / 2.4k out). That is about 7.1k input and 2.65k output tokens in total.

**Recommendation:**

- **Primary:** a Claude Haiku-class model. Both tasks are short, schema-bound classification and extraction, so a small model is enough. It is the cheapest per request, and forced tool use gives reliable JSON.
- **Fallback:** a Gemini Flash-Lite-class model, from a different vendor, which protects against a single provider's outage or rate limit.
- **Upgrade path:** move only the intent call to a larger model if location parsing needs it. That call is about 950 tokens, so the cost barely changes.

Report the **measured** values (`meta.latency_ms`, token counts and `llm_cost_usd` from evidence mode) separately from these estimates.

**Other costs per request:**

| Item | Volume | Cost |
|---|---|---|
| Serper | About 7 calls (cap 12) | About $0.007 at about $1 per 1k; free within the first 2,500 |
| YouTube | 1 `search.list` + 1 `channels.list` | $0. `search.list` has its own quota bucket of 100 calls a day |

**Cost optimisations already in the code:**

- Intent cache (24 h) and search-result cache (6 h).
- Query templates instead of LLM-generated queries.
- Deterministic URL, contact, dedup and keyword checks before any LLM call.
- One batched relevance call (top 40 candidates, snippets ≤ 500 characters).
- Short, fixed system prompts and temperature 0.
- Hard per-request budgets for search calls and site fetches.

---

## 10. Ethics, privacy and compliance

- **Sources:** only authorized APIs: Serper (Google results via a third-party provider, swappable for Brave) and the YouTube Data API. No logins and no bypassing of access controls. Social platform pages are **never** fetched.
- **Websites:** a prospect's own website is fetched only if its `robots.txt` allows it. Fetches are capped at ≤ 8 per request and go through an SSRF guard with size and time limits.
- **Traceability:** every returned item can be traced to its source (`include_evidence=true`). Verified and inferred signals are labelled separately.
- **No fabrication:** the LLM never produces names, links or contacts. Emails are never guessed, and WhatsApp links are never built from plain phone numbers.
- **Minimal data:** no personal phone numbers are returned for hobby or interest audiences. Business contacts appear only when the business published them. There is no database, only a short-lived in-memory cache.
- **Legal context:** GDPR applies in the UK/EU (legitimate interest; Art. 14 transparency). India's DPDP Act 2023 covers data the person made public. The UAE has its PDPL. This tool is for discovery, not for unsolicited bulk messaging; any outreach is subject to CAN-SPAM, TCPA and local equivalents.
- **Removal requests:** contact `<your email>`.
- **Sample files:** remove private individuals' contact details before committing anything to a public repository.

---

## 11. Limitations and next steps

- **Search index coverage:** results depend on what the public search index holds. Hobby audiences rarely publish contacts, which is expected and honest.
- **Snippet text:** profile data comes from search snippets, which may be stale. A liveness check is a next step; note that LinkedIn and Instagram answer automated requests with login walls.
- **YouTube quota:** the default is 100 `search.list` calls a day. Results are cached for 6 hours.
- **Scaling:** Redis cache, a job queue with webhooks for slow requests, per-provider token buckets, and batch LLM APIs for bulk jobs.
- **Native platform APIs:** add them if partner or app-review access is granted. A new platform is one module plus `@register`.

---

## 12. Tests

```bash
python -m pytest                     # locally (after pip install -r requirements-dev.txt)
docker compose run --rm api pytest   # inside the container
```

There are **32 tests**. All external calls are mocked, so they need no network and no keys. They cover:

- **Profile URLs:** canonicalisation, and rejection of posts, groups, status and search URLs.
- **Contacts:**
  - email validation
  - phone validation and the country check
  - WhatsApp links accepted only when published
- **Deduplication:**
  - same handle + same name merges
  - same name, different people stays separate
  - same handle with a different name stays separate
  - a cross-link from the prospect's own site merges
- **Website extraction:** contacts are extracted, and team pages are ignored as identity signals.
- **robots.txt:** disallowed pages are respected.
- **End-to-end API:**
  - exact spec shape
  - post URLs and excluded locations filtered out
  - phone number inside `social_link`
  - evidence mode
  - 422 envelope
- **Configuration:** `/health` reports configuration without exposing secrets, and placeholder keys count as unconfigured.
