# Phase 3: Claude AI Lead Analysis — Design Spec

**Date:** 2026-06-16
**Branch:** feature/lead-analysis
**Status:** Approved

---

## Overview

Phase 3 adds AI-powered lead analysis via the Anthropic API. When a lead is submitted to `POST /leads/{lead_id}/analyze`, the system calls Claude Haiku to produce a structured scoring and narrative for the lead, stores the result in a new `lead_analysis` table, and updates the lead's status to `"analyzed"`.

---

## Architecture & Data Flow

```
POST /leads/{lead_id}/analyze
  → load Lead from DB          (404 if not found)
  → ai_service.analyze_lead(lead)
      → build system prompt + user message
      → call AsyncAnthropic.messages.create()
      → parse JSON from response.content[0].text
      → on failure: retry once, then return safe fallback dict
  → create LeadAnalysis row in DB
  → update lead.status = "analyzed", commit
  → return LeadAnalysisRead
```

**Separation of concerns:**
- The router owns all DB reads and writes.
- `ai_service.analyze_lead()` is a pure async function — it receives a `Lead` object, calls the Anthropic API, and returns a dict. It does not touch the database.
- This boundary makes each layer independently testable.

**No ORM relationship added to `Lead`:** The FK is enforced at the DB level. The router fetches both objects independently. Keeps the `Lead` model clean.

---

## Database Model

**File:** `app/models/analysis.py`
**Table:** `lead_analysis`

| Column | SQLAlchemy Type | Nullable | Notes |
|---|---|---|---|
| `id` | Integer PK | No | autoincrement |
| `lead_id` | Integer FK → `leads.id` | No | |
| `company_summary` | Text | Yes | |
| `persona_type` | String(100) | Yes | |
| `pain_points` | Text | Yes | |
| `buying_signals` | Text | Yes | |
| `objections` | Text | Yes | |
| `fit_score` | Integer | Yes | 0–100 |
| `urgency_score` | Integer | Yes | 0–100 |
| `overall_score` | Integer | Yes | 0–100 |
| `recommended_action` | String(100) | Yes | |
| `confidence_score` | Float | Yes | 0.0–1.0 |
| `raw_ai_json` | Text | Yes | full Claude response stored for debugging |
| `created_at` | DateTime(timezone=True) | No | server_default=now() |

---

## Pydantic Schemas

**File:** `app/schemas/analysis.py`

### `LeadAnalysisCreate`
All analysis fields (no `id`, `lead_id`, or `created_at`). Used internally by the router when constructing the DB row.

### `LeadAnalysisRead`
All analysis fields plus `id`, `lead_id`, `created_at`. `model_config = {"from_attributes": True}`. Returned in API responses.

---

## AI Service

**File:** `app/services/ai_service.py`

**Function signature:**
```python
async def analyze_lead(lead: Lead) -> dict:
```

**Model:** `claude-haiku-4-5-20251001`

**System prompt instructs Claude to:**
- Return only a valid JSON object, no explanation, no markdown fences
- Use cautious, conservative language — do not invent specific facts about the company
- Populate all required fields even when uncertain, defaulting to low scores when signal is weak
- Score fields must be integers 0–100; confidence_score must be a float 0.0–1.0

**User message:** Formatted block of lead fields:
```
Name: {first_name} {last_name}
Company: {company}
Job Title: {job_title}
Website: {company_website}
Source: {source}
Notes: {notes}
```

**Expected JSON structure Claude returns (10 fields):**
```json
{
  "company_summary": "...",
  "persona_type": "...",
  "pain_points": "...",
  "buying_signals": "...",
  "objections": "...",
  "fit_score": 0,
  "urgency_score": 0,
  "overall_score": 0,
  "recommended_action": "...",
  "confidence_score": 0.0
}
```

The service adds `raw_ai_json` (the full raw response text from `response.content[0].text`) to the dict before returning it to the router. This gives the router a 11-field dict that maps directly to the `LeadAnalysis` model columns.

**Retry & fallback logic:**
1. Call Claude. If exception raised, retry once.
2. After successful call, parse `response.content[0].text` with `json.loads()`.
3. If JSON parse fails, return a safe fallback dict: all text fields `None`, all scores `0`, `confidence_score` `0.0`, `raw_ai_json` set to the raw unparseable text for debugging.
4. The router stores the fallback row regardless — the analysis event is always recorded.

**Client instantiation:** `AsyncAnthropic` instantiated per call. `ANTHROPIC_API_KEY` read from `Settings`.

---

## Router

**File:** `app/routers/analysis.py`

**Endpoint:** `POST /leads/{lead_id}/analyze`

Steps:
1. Load lead by `lead_id` → 404 if `None`
2. Call `ai_service.analyze_lead(lead)` → `analysis_dict`
3. Create `LeadAnalysis(**analysis_dict, lead_id=lead_id)` and add to session
4. Update `lead.status = "analyzed"`
5. `await db.commit()`
6. `await db.refresh(analysis)`
7. Return `LeadAnalysisRead.model_validate(analysis)`

**Registration:** Add to `app/main.py` alongside the existing leads router.

---

## Configuration & Dependencies

**`app/config.py`:** Add `ANTHROPIC_API_KEY: str` to `Settings`.

**`requirements.txt`:** Add `anthropic>=0.25.0`

**`.env.example`:** Add `ANTHROPIC_API_KEY=your_key_here`

---

## Alembic Migration

Run after implementing the model:
```bash
alembic revision --autogenerate -m "add lead_analysis table"
```

The `LeadAnalysis` model must be imported somewhere that `alembic/env.py` picks up (e.g., imported in `app/models/__init__.py`).

---

## Tests

**File:** `tests/test_analysis.py`

Same `AsyncMock`/`MagicMock` pattern as `tests/test_leads.py`. No real API or DB calls.

**Test cases:**
1. `POST /leads/{id}/analyze` → 200 with correct `LeadAnalysisRead` structure
2. `POST /leads/{id}/analyze` → 404 when lead not found
3. `analyze_lead()` with mocked Anthropic returning malformed JSON → safe fallback returned, no exception raised
4. All score fields (`fit_score`, `urgency_score`, `overall_score`) are integers 0–100
5. `confidence_score` is a float 0.0–1.0

**Mock strategy:** Patch `app.services.ai_service.AsyncAnthropic` with `unittest.mock.patch`. The patched client returns a mock response with a `.content[0].text` attribute containing a valid JSON string.

---

## File Checklist

| File | Action |
|---|---|
| `app/models/analysis.py` | Create |
| `app/models/__init__.py` | Import `LeadAnalysis` so alembic sees it |
| `app/schemas/analysis.py` | Create |
| `app/services/ai_service.py` | Create |
| `app/routers/analysis.py` | Create |
| `app/main.py` | Register analysis router |
| `app/config.py` | Add `ANTHROPIC_API_KEY` to `Settings` |
| `requirements.txt` | Add `anthropic>=0.25.0` |
| `.env.example` | Add `ANTHROPIC_API_KEY=your_key_here` |
| `alembic/versions/` | New migration file |
| `tests/test_analysis.py` | Create |

---

## Git Workflow

- Branch: `feature/lead-analysis`
- Conventional commits per task
- Push and open PR when complete
- Do NOT merge — wait for review
