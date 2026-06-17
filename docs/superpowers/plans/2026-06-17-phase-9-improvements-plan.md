# Implementation Plan — Phase 9 Improvements

Branch: `feature/phase-9-improvements`
Spec: `docs/superpowers/specs/2026-06-17-phase-9-improvements-design.md`

## Global Constraints

- Python 3.12, FastAPI, SQLAlchemy async, Alembic, Jinja2, Anthropic SDK
- No new pip packages
- All filtering client-side JS — no extra API endpoints
- Follow existing CSS conventions (.badge-*, .btn-*, .card-*)
- Do not change unrelated files
- Conventional Commits per task
- No Claude/tool attribution in commit messages or PR description

---

## Task 1 — Add title and description to CallAnalysis model

**Files to change:**
- `app/models/call_analysis.py` — add `title: Mapped[str | None] = mapped_column(String(255), nullable=True, default=None)` and `description: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)`
- `app/schemas/call_analysis.py` — add `title: str | None = None` and `description: str | None = None` to both `CallAnalysisRequest` and `CallAnalysisResponse`
- `app/services/call_intelligence_service.py` — update `_SYSTEM_PROMPT` to request `title` (max 60 chars, e.g. "Discovery call with Sarah Chen — Greystar") and `description` (1–2 sentences). Update `_FALLBACK` dict to include both keys as `None`. The `analyze_transcript` function signature stays the same — it returns the enriched dict.
- `app/routers/call_notes.py` — in the `analyze_call` handler: read `body.title` and `body.description`; call `analyze_transcript(body.transcript)`; use `body.title or analysis_dict.get("title")` for the record's `title` field; same for `description`. Construct `CallAnalysis` record with both new fields.
- `alembic/versions/<hash>_add_title_description_to_call_analysis.py` — generate via `alembic revision --autogenerate -m "add title and description to call_analysis"` INSIDE the container using `docker compose exec api alembic revision --autogenerate -m "add title and description to call_analysis"`, then run `docker compose exec api alembic upgrade head`

**Commit:** `feat: add title and description fields to call analysis`

---

## Task 2 — Call notes list dashboard page

**Files to change:**
- `app/routers/dashboard.py` — update `dashboard_call_notes_list` to also fetch all leads that have ≥1 call note, pass as `all_leads` to template; also pass full leads list for filter dropdown.
- `templates/call_notes_list.html` — full rebuild. Table columns: Title (link), Lead (link or "No lead linked"), Intent Score (coloured badge), Decision Timeline, Recommended Follow-up (truncated 80 chars), Date Created. Filter bar above table: search input, lead dropdown, intent dropdown (All/High/Medium/Low), linked dropdown (All/Linked/Unlinked), date from/to inputs, Clear Filters button. "New Call Analysis" button linking to `/dashboard/call-notes/new`. All filtering in JS using data attributes on rows.

**Commit:** `feat: add call notes list dashboard page with filtering`

---

## Task 3 — Standalone call analysis submission form

**Files to change:**
- `app/routers/dashboard.py` — add `GET /dashboard/call-notes/new` route; fetch all leads; read optional `lead_id` query param (int | None); pass `all_leads` and `preselected_lead_id` to template.
- `templates/call_notes_new.html` — new template. Form fields: Title (text, optional), Description (textarea, optional), Lead selector (select, optional — pre-select if `preselected_lead_id`), Transcript (textarea, required). Submit via JS fetch to `POST /call-notes/analyze`, loading state on button, redirect to `/dashboard/call-notes/{id}` on success, inline error div on failure.

**Commit:** `feat: add standalone call analysis submission form`

---

## Task 4 — Improve call analysis detail page

**Files to change:**
- `app/routers/dashboard.py` — update `dashboard_call_analysis` to also fetch the linked Lead if `analysis.lead_id` is set; pass `lead: Lead | None` to template.
- `templates/call_analysis.html` — full redesign. Section order: (1) Header card: title (h2 or fallback "Call Analysis #{id}"), description (p), lead link or "No lead linked", date, intent badge; (2) Call Intelligence Summary: decision_timeline, recommended_follow_up, competitors; (3) Pain Points & Signals: pain_points, budget_signals; (4) Objections; (5) Follow-Up Email with Copy button; (6) CRM Note with Copy button and HubSpot label.

**Commit:** `feat: redesign call analysis detail page`

---

## Task 5 — Add call notes section to lead detail page

**Files to change:**
- `app/routers/dashboard.py` — update `dashboard_lead_detail` to fetch all `CallAnalysis` records for this lead ordered by `created_at desc`; pass as `call_analyses`.
- `templates/lead_detail.html` — add Section 5 after HubSpot Sync. If `call_analyses` empty: "No call notes yet" + Add Call Note button. If non-empty: compact table (Title/Intent/Date/View link) + Add Call Note button below. Button links to `/dashboard/call-notes/new?lead_id={lead.id}`.
- `app/routers/dashboard.py` (GET /dashboard/call-notes/new) — read `lead_id` query param and pass as `preselected_lead_id`.

**Commit:** `feat: add call notes section to lead detail page`

---

## Task 6 — Add Run Agent button to lead detail page

**Files to change:**
- `app/routers/dashboard.py` — update `dashboard_lead_detail` to fetch most recent `AutomationMetrics` record for this lead; pass as `agent_run` (None if no record exists). Must import `AutomationMetrics` from `app.models.metrics`.
- `templates/lead_detail.html` — in the Lead Info card header: if `agent_run is None` show Run Agent button; else show "Agent last run: {datetime}". JS `runAgent()` function identical to leads.html.

**Commit:** `feat: add run agent button to lead detail page`

---

## Task 7 — Add email column to leads list dashboard

**Files to change:**
- `templates/leads.html` — insert Email column as 3rd column (after Name, Company, before Title). Render as `mailto:` link. Update empty-state colspan from 8 to 9.

Note: The route `dashboard_leads` already returns `lead.email` via the Lead object — no route change needed.

**Commit:** `feat: add email column to leads list dashboard`

---

## Task 8 — CSS updates

**Files to change:**
- `static/style.css` — append new rules for:
  - `.filter-bar` — flexbox row, gap, flex-wrap
  - `.filter-bar input, .filter-bar select` — consistent height/padding/border
  - `.filter-bar .btn-clear` — secondary button style
  - `.intent-badge` base + `.intent-badge-high`, `.intent-badge-mid`, `.intent-badge-low` — coloured inline badge
  - `.btn-copy` — small secondary-style button for clipboard
  - `.call-notes-compact td, .call-notes-compact th` — tighter padding for the compact table in lead detail
  - `.form-group` — margin-bottom spacing for form rows
  - `.form-help` — small grey helper text
  - `.agent-last-run` — subtle grey italic status line
  - `.call-note-add-btn` — consistent "Add Call Note" button positioning

**Commit:** `feat: update CSS for all phase 9 improvements`

---

## Task 9 — Smoke test

- Start app: `docker compose up -d --build` (or `docker compose up -q`)
- Run: `docker compose exec api alembic upgrade head`
- Verify HTTP 200 for: GET /dashboard/leads, GET /dashboard/leads/1, GET /dashboard/call-notes, GET /dashboard/call-notes/new, GET /dashboard/metrics
- Use the Playwright MCP browser tool or curl to check responses
- Fix any Python import errors, template errors, or 500s found
- Note: /dashboard/leads/1 may 404 if no lead exists — that is acceptable

**Commit:** `chore: smoke test all dashboard routes`

---

## Task 10 — PR

- `git push -u origin feature/phase-9-improvements`
- Open PR to main with title: "Phase 9 Improvements: Call Notes UI and Lead Page Enhancements"
- PR body: list every change across all tasks. No attribution.
- Do NOT merge.
