# Python Practical Test – AI-Powered Multi-Platform Prospect Discovery API

| Details | Information |
|---|---|
| **Technology** | Python 3.x, FastAPI |
| **AI Integration** | OpenAI / Gemini / Anthropic / Other LLM |
| **Duration** | Maximum 4 Hours |
| **Difficulty** | Intermediate |
| **Submission** | Public GitHub Repository |

## 1. Objective

Develop a Python application using FastAPI that discovers relevant prospects across multiple online platforms based on a natural-language search query.

The application should understand the user's search intent, identify the target audience and geographical location, discover relevant public profiles across supported platforms, consolidate matching profiles, and return a structured JSON list of prospects.

The system should also identify publicly available contact information, including email addresses, phone numbers, and WhatsApp contact links.

Additionally, applicants must research and recommend the most suitable LLM platform or model based on accuracy, response speed, and API cost.

Applicants are expected to understand the problem, select suitable technologies, and implement the solution independently.

## 2. API Requirement

Create one REST API endpoint.

**Endpoint:**

```http
POST http://localhost:4000/prospect-discovery
```

### Request Body

```json
{
  "query": "Football lovers in Washington DC in USA"
}
```

### Input Requirements

- Accept a natural-language prospect discovery query.
- Understand the target audience, interests, and location.
- Identify the relevant city, state, and country where available.
- Search for relevant prospects across supported platforms.
- Extract publicly accessible profile information.
- Identify publicly available email and phone contact information.
- Consolidate multiple profiles belonging to the same individual.
- Return prospects in structured JSON format.
- Handle invalid queries, unavailable platforms, and API failures gracefully.

## 3. Supported Platforms

The prospect discovery engine must support the following platforms:

| No. | Platform | Discovery Target |
|---|---|---|
| 1 | Google | Publicly indexed profiles and websites |
| 2 | LinkedIn | Public professional profiles |
| 3 | X | Public user profiles |
| 4 | YouTube | Public creator and channel profiles |
| 5 | Instagram | Public profiles |
| 6 | WhatsApp | Publicly available contact links |
| 7 | Facebook | Public profiles and pages |
| 8 | Email | Publicly published email addresses |
| 9 | Threads | Public profiles |

The architecture should allow additional platforms to be integrated in the future.

**Important:** Google is a discovery/search source. The final prospect records should contain relevant individual or business profiles, not generic search-result URLs.

## 4. Functional Requirements

The API must implement the following functionality.

### Section 1: Natural Language Query Understanding

Understand the user's search query and extract structured search parameters.

**Example Input:**

```text
Football lovers in Washington DC in USA
```

**Expected Understanding:**

```json
{
  "interest": "Football",
  "audience": "Football lovers",
  "location": {
    "city": "Washington DC",
    "state": "District of Columbia",
    "country": "USA"
  },
  "target_type": "individual"
}
```

The system should dynamically understand different interests, audiences, locations, and countries.

It should not depend on hardcoded search queries.

### Section 2: Multi-Platform Prospect Discovery

Discover relevant prospects using the supported platforms.

**Expected Information:**

- Prospect's full name.
- Relevant public profile.
- Geographical location.
- Available social media profiles.
- Publicly available contact information.
- Relevance to the submitted query.

**Discovery Requirements:**

1. Search across multiple supported platforms.
2. Identify relevant public profiles.
3. Collect verified profile URLs.
4. Identify multiple social profiles belonging to the same prospect.
5. Avoid irrelevant profiles.
6. Avoid fabricated names, URLs, and contact information.
7. Support platform-specific discovery methods.

The system should use official APIs, permitted search APIs, or other authorized public discovery sources.

### Section 3: Social Profile Consolidation and Duplicate Detection

The same individual may have profiles across multiple platforms.

The system must identify and consolidate matching profiles into a single prospect record.

**Example:**

A person discovered through Google, LinkedIn, and Instagram should ideally appear as one prospect with three social profile links.

Expected functionality:

- Identify duplicate profiles.
- Match profiles using available identity signals.
- Consolidate verified links.
- Avoid merging different individuals with similar names.
- Maintain profile-level source information internally where useful.

### Section 4: Public Contact Information Discovery

Identify publicly available contact information associated with discovered prospects.

**Supported information:**

- Email address.
- Phone number.
- WhatsApp contact link.

**Requirements:**

- Extract only publicly published contact information.
- Validate email formats and phone numbers.
- Associate contact details with the correct prospect.
- Avoid generating or guessing contact information.
- Include email and phone information inside the `social_link` array.

Do not access private profiles, bypass authentication, or collect restricted personal information.

### Section 5: Prospect Relevance and Filtering

The system must identify whether a discovered prospect is relevant to the submitted query.

For example:

**Query:**

```text
Football lovers in Washington DC in USA
```

A relevant prospect should have available public information indicating a connection to football and/or the specified location.

Evaluate:

- Interest relevance.
- Location relevance.
- Audience relevance.
- Profile authenticity.
- Available supporting evidence.

Do not classify a prospect as a confirmed match based only on a name or an unsupported assumption.

## 5. Expected API Response

The API must return all discovered prospects in a structured JSON response.

### Expected JSON Structure

```json
{
  "success": true,
  "query": "Football lovers in Washington DC in USA",
  "total_prospects": 2,
  "prospects": [
    {
      "name": "John Smith",
      "location": "Washington DC, USA",
      "social_link": [
        {
          "platform": "Facebook",
          "link": "<verified_public_profile_link>"
        },
        {
          "platform": "Instagram",
          "link": "<verified_public_profile_link>"
        },
        {
          "platform": "LinkedIn",
          "link": "<verified_public_profile_link>"
        },
        {
          "platform": "X",
          "link": "<verified_public_profile_link>"
        },
        {
          "platform": "Email",
          "link": "mailto:<public_email_address>"
        },
        {
          "platform": "WhatsApp",
          "link": "<public_whatsapp_contact_link>"
        }
      ]
    },
    {
      "name": "Michael Johnson",
      "location": "Washington DC, USA",
      "social_link": [
        {
          "platform": "YouTube",
          "link": "<verified_public_channel_link>"
        },
        {
          "platform": "Threads",
          "link": "<verified_public_profile_link>"
        }
      ]
    }
  ]
}
```

*Note: This is an illustrative JSON structure, not actual discovered prospect data.*

### Output Rules

1. `name` is required.
2. `location` should be provided when available.
3. `social_link` must always be an array.
4. Each social link must contain `platform` and `link`.
5. Use the platform names defined in this assessment.
6. Email and phone information must also be included in `social_link`.
7. Include only verified or sufficiently validated public links.
8. Do not generate fake profiles, emails, or phone numbers.
9. Do not return duplicate prospects.
10. Return valid JSON without additional explanatory text.

## 6. Practical Test Cases

Candidates must test the implementation using at least the following queries.

| No. | Search Query | Expected Audience |
|---|---|---|
| 1 | Football lovers in Washington DC in USA | Football enthusiasts |
| 2 | Digital marketing agency owners in New York USA | Marketing business owners |
| 3 | Startup founders in London UK | Startup founders |
| 4 | Cricket lovers in Ahmedabad India | Cricket enthusiasts |
| 5 | Restaurant owners in Dubai UAE | Restaurant business owners |

The system should dynamically understand different interests, professions, industries, audiences, and geographical locations.

The candidate should demonstrate actual discovery results for the test queries wherever authorized sources provide sufficient information.

## 7. Technical Requirements

Use the following technologies:

- Python 3.x
- FastAPI
- Uvicorn
- Pydantic
- HTTPX or Requests
- BeautifulSoup or equivalent HTML parser, where applicable
- OpenAI, Gemini, Anthropic, or another LLM API
- Authorized search APIs or platform APIs
- Environment variables for API credentials

### Suggested Processing Flow

1. Receive the prospect discovery query.
2. Validate the input.
3. Send the query to an LLM for intent understanding.
4. Extract audience, interest, and geographical parameters.
5. Generate platform-specific search queries.
6. Execute discovery across available platforms.
7. Extract public profile information.
8. Validate profile URLs and publicly available contact details.
9. Calculate prospect relevance.
10. Identify and consolidate duplicate profiles.
11. Generate the final structured JSON response.
12. Validate the response using Pydantic.
13. Return results through FastAPI.

### Suggested Architecture

```text
User Query
    |
    v
Query Understanding (LLM)
    |
    v
Audience & Location Extraction
    |
    v
Search Query Generation
    |
    v
Multi-Platform Discovery
    |
    +---- Google
    +---- LinkedIn
    +---- X
    +---- YouTube
    +---- Instagram
    +---- Facebook
    +---- Threads
    +---- WhatsApp / Public Contact Sources
    |
    v
Profile Extraction & Validation
    |
    v
Duplicate Detection
    |
    v
Prospect Relevance Evaluation
    |
    v
Structured JSON Response
```

### Important Implementation Considerations

- Design platform integrations as independent modules.
- Handle platform API failures independently.
- Implement timeout and rate-limit handling.
- Avoid unnecessary repeated API calls.
- Cache discovery results where appropriate.
- Maintain source URLs for verification.
- Do not assume all platforms provide searchable public profile APIs.
- Do not bypass platform authentication or access restrictions.

## 8. LLM Platform & Model Research – Cost, Speed and Accuracy

Identify and recommend the most suitable LLM platform or model for this prospect discovery application.

The objective is to achieve:

- Accurate natural-language query understanding.
- Relevant search query generation.
- Reliable profile relevance classification.
- Fast response time.
- Minimum API cost.
- Reliable structured JSON output.

### A. LLM Platform Comparison

Research and compare at least three LLM providers or models.

Examples:

- OpenAI
- Google Gemini
- Anthropic Claude
- Other suitable LLM providers

Compare the following:

| Criteria | Description |
|---|---|
| Provider | LLM platform |
| Model Name | Recommended model |
| API Cost | Input and output token pricing |
| Response Speed | Expected or measured response time |
| Accuracy | Query understanding and relevance classification |
| Context Window | Maximum supported input context |
| JSON Support | Structured response capabilities |
| Recommendation | Suitability for this application |

### B. Best Model Selection

Recommend the most suitable model based on:

1. Natural-language query understanding.
2. Search query generation.
3. Prospect relevance classification.
4. Structured JSON generation.
5. Response speed.
6. API cost.

### C. Cost Optimization

Suggest ways to reduce API costs without compromising discovery quality.

Consider:

- Optimizing LLM prompts.
- Reducing unnecessary token usage.
- Using smaller models for simple classification.
- Avoiding repeated API calls.
- Caching query understanding results.
- Processing multiple search results efficiently.
- Using deterministic validation instead of LLM calls wherever possible.

### D. Final LLM Recommendation

Provide:

- Recommended LLM provider.
- Recommended model name.
- Estimated input token usage.
- Estimated output token usage.
- Estimated API cost per discovery request.
- Expected response time.
- Reason for selecting the model.
- Alternative model for fallback.
- Recommended approach for balancing accuracy, speed, and cost.

**Important:** Use current provider pricing and documentation. Distinguish estimated performance from measured benchmarks.

## 9. Suggested Project Structure

```text
ai-prospect-discovery/
│
├── app/
│   ├── main.py
│   ├── config.py
│   ├── schemas.py
│   │
│   ├── services/
│   │   ├── query_service.py
│   │   ├── search_service.py
│   │   ├── prospect_service.py
│   │   ├── profile_extractor.py
│   │   ├── deduplication_service.py
│   │   ├── relevance_service.py
│   │   └── llm_service.py
│   │
│   ├── platforms/
│   │   ├── google.py
│   │   ├── linkedin.py
│   │   ├── facebook.py
│   │   ├── instagram.py
│   │   ├── x_platform.py
│   │   ├── youtube.py
│   │   ├── whatsapp.py
│   │   └── threads.py
│   │
│   └── utils/
│       ├── validators.py
│       └── normalizers.py
│
├── tests/
│   └── test_prospect_discovery.py
│
├── .env.example
├── requirements.txt
└── README.md
```

## 10. Evaluation Criteria

| Criteria | Marks |
|---|---:|
| Natural Language Query Understanding | 15 |
| Multi-Platform Discovery Implementation | 25 |
| Prospect Relevance and Accuracy | 15 |
| Duplicate Detection and Profile Consolidation | 10 |
| Public Profile and Contact Validation | 10 |
| Structured JSON Output and API Design | 10 |
| LLM Model Research and Cost Optimization | 10 |
| Code Quality, Error Handling and Documentation | 5 |
| **Total** | **100** |

## 11. Important Instructions

- Use actual publicly available discovery results.
- Do not generate generic or fabricated prospects.
- Do not invent profile links, names, email addresses, or phone numbers.
- Use authorized APIs and permitted discovery methods.
- Clearly distinguish verified information from inferred information.
- Handle platform API limitations and failures gracefully.
- Do not bypass authentication or access private profiles.
- Protect API keys and credentials.
- Implement appropriate rate-limit handling.
- Ensure duplicate profiles are consolidated correctly.
- Return valid structured JSON responses.
- Document any platform that could not be integrated and explain the limitation.
- A working prototype with reliable results is more important than claiming support for all platforms without implementation.

## 12. Submission Instructions

Once you complete the practical test:

1. Upload your complete Python source code to GitHub.
2. Make your GitHub repository **Public**.
3. Include a README.md with setup and execution instructions.
4. Include sample API requests and responses.
5. Add screenshots or logs demonstrating your implementation.
6. Include your LLM comparison and final model recommendation in the README.
7. Document the discovery sources and supported platforms.
8. Ensure no API keys, passwords, or private credentials are committed.

**Duration: Maximum 4 Hours.**

**Submission Deadline: 30th November 2026.**

## 13. Application Verification & Deployment

As part of our recruitment process, following our official company social media accounts and sharing your profile links are mandatory verification steps.

**1. Follow Dxora Technologies on LinkedIn**

https://www.linkedin.com/company/dxora-technologies

**2. Follow CREST on Instagram**

https://www.instagram.com/crestspot/

### Deploy Your Practical Test Application

- Deploy your completed FastAPI application on a publicly accessible server.
- Ensure the API is running and accessible.
- Provide a Live Demo URL.
- Share the API documentation link (`/docs`).
- Ensure the prospect discovery endpoint is working and returns structured JSON.

**Example:**

| Requirement | Example |
|---|---|
| Live Demo | `https://your-domain.com` |
| API Endpoint | `https://your-domain.com/prospect-discovery` |
| API Documentation | `https://your-domain.com/docs` |

**Important:** Please share your LinkedIn and Instagram profile links while submitting your application for verification.

## 14. Final Submission – Email Instructions

After completing the practical test, send an email to:

**To:** hr@chivoxai.com

**Subject:** Your Name - Python Practical Prospect Discovery Test Review

### Email Body

Please include:

1. Your Full Name.
2. Demo Link.
3. Public GitHub Repository Link.
4. Contact Number.
5. Current Location.
6. LinkedIn Profile Link.
7. Instagram Profile Link.
8. Preferred Date and Time for Final Discussion.

## 15. Final Round – Dxora Panel Interview

Our technical team will review your GitHub repository and evaluate your implementation.

Shortlisted applicants will be contacted for the final technical discussion with the **Dxora Panel**.

We will evaluate:

- Python programming skills.
- FastAPI and REST API development.
- Natural-language query understanding.
- Multi-platform prospect discovery.
- Search API integration.
- Profile extraction and validation.
- Duplicate detection and entity resolution.
- LLM integration and prompt engineering.
- LLM model selection and cost optimization.
- Problem-solving and code quality.

---

**All the best! We look forward to reviewing your work.**
