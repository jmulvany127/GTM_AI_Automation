# Implementation Plan: Unified Outreach Agent

Branch: feature/unified-outreach-agent
Spec: docs/superpowers/specs/2026-06-24-unified-outreach-agent-design.md
Date: 2026-06-24

---

## Global Constraints

- Branch: `feature/unified-outreach-agent` — never commit to `main`
- Conventional commits required
- All external services (Anthropic, Gmail, Slack, HubSpot) must be mocked in tests
- `outreach_service.py` and `app/routers/outreach.py` must remain UNTOUCHED
- No new migrations needed — existing schema supports all changes
- Docker-based test runner: `docker compose exec api python -m pytest tests/test_outreach_agent.py -q`
- `execute_run_outreach_agent` must be importable by `app/routers/leads.py`
- `_ALLOWED_ACTIONS` lives in `app/agents/gtm_workflow_agent.py` but is also imported into `workflow.py` via `from app.agents.gtm_workflow_agent import _ALLOWED_ACTIONS`
- The dispatch map `_DISPATCH` is in `app/routers/workflow.py`
- Slack threshold: `overall_score >= 70` (DB value 0–100 scale, matching current implementation)

---

## Task 1 — Rewrite outreach agent service

**File:** `app/services/outreach_agent_service.py`

**Changes:**
1. Update function signature: `run_outreach_agent(lead: dict, analysis: dict) -> dict`
   — remove `outreach: dict` parameter entirely
2. Rewrite `_SYSTEM_PROMPT` to be the unified content + channel decision agent:
   - Inject Domino AI product context at top (already present — keep all config imports)
   - Establish agent as owner of outreach content generation AND channel decision
   - Instruct to return all 10 keys in one JSON object
   - Specify exact content rules: email under 130 words, linkedin under 280 chars,
     follow-up under 90 words, signature format, no placeholder text
   - Include the decision signals (score thresholds, personal domain rules, persona signals)
3. Update `_FALLBACK` to include all 10 keys:
   - `subject`: "Review Required — Outreach Not Generated"
   - `email_body`: None
   - `follow_up_email`: None
   - `linkedin_message`: None
   - `call_notes`: None
   - `chosen_channel`: "deferred"
   - `agent_reasoning`: "Agent unavailable — defaulting to deferred."
   - `requires_human_review`: True
   - `review_reason`: "Agent unavailable — review before sending"
   - `personalisation_notes`: None
   - `fallback`: True
4. Update `_apply_deterministic_overrides(result, lead, analysis)` — remove `outreach` param.
   Change the missing-linkedin check from `outreach.get("linkedin_message")` to
   `result.get("linkedin_message")` (since linkedin_message is now generated inline by the agent).
5. Update `user_message` construction — remove the "Outreach Content Available" section
   (no pre-generated content to pass in). Include full lead info and analysis.
6. Update `max_tokens` from 512 to 2000
7. Update the call site: `result = _apply_deterministic_overrides(result, lead, analysis)`

**Commit:** `refactor: rewrite outreach agent as unified content and channel owner`

---

## Task 2 — Update orchestrator allowed actions and system prompt

**Files:** `app/agents/gtm_workflow_agent.py`

**Changes:**
1. In `_ALLOWED_ACTIONS`: remove `"generate_outreach"`, add `"run_outreach_agent"`
2. In `_SYSTEM_PROMPT`:
   - In Decision Rules: replace `generate_outreach` with `run_outreach_agent`
   - In Allowed Actions list: replace `- generate_outreach` with `- run_outreach_agent`
   - Add description: "`run_outreach_agent`: generates personalised outreach content, decides
     the best channel, and executes sending. Use this when the lead warrants outreach."
3. Also update `workflow.py` `_DISPATCH`:
   - Remove `"generate_outreach": execute_generate_outreach` entry
   - Add `"run_outreach_agent": _dispatch_run_outreach_agent` entry
     where `_dispatch_run_outreach_agent(lead, db)` is a thin wrapper around
     `execute_run_outreach_agent(lead, db)`
   - Remove the hardcoded side effect block (lines 263–285: the `if action == "generate_outreach":` block)
   - Remove `execute_generate_outreach` function entirely (it's no longer needed)
   - Keep `execute_run_outreach_agent` but update it (see Task 3)

**Commit:** `refactor: make run_outreach_agent a proper orchestrator action`

---

## Task 3 — Implement unified execution pipeline

**File:** `app/routers/workflow.py`

**Changes:**
Rewrite `execute_run_outreach_agent` with new signature `(lead, db: AsyncSession) -> dict`:

1. Fetch latest analysis from DB (same as `execute_generate_outreach` did)
2. Build `lead_dict` and `analysis_dict` from ORM objects
3. Call `run_outreach_agent(lead_dict, analysis_dict)` — unified agent, no outreach param
4. Write content keys to `OutreachMessage`:
   ```python
   outreach = OutreachMessage(
       lead_id=lead.id,
       subject=agent_result.get("subject"),
       email_body=agent_result.get("email_body"),
       follow_up_email=agent_result.get("follow_up_email"),
       linkedin_message=agent_result.get("linkedin_message"),
       call_notes=agent_result.get("call_notes"),
   )
   db.add(outreach)
   await db.flush()
   ```
5. Write decision keys to `OutreachExecutionLog`:
   ```python
   log = OutreachExecutionLog(
       lead_id=lead.id,
       outreach_message_id=outreach.id,
       agent_reasoning=agent_result.get("agent_reasoning"),
       chosen_channel=agent_result.get("chosen_channel"),
       requires_human_review=agent_result.get("requires_human_review", False),
       review_reason=agent_result.get("review_reason"),
       execution_status="pending",
   )
   db.add(log)
   await db.flush()
   ```
6. Execute sending based on channel + review status (preserve current logic):
   - `requires_human_review` True → set `lead.status = "needs_review"`, Slack review alert, skip sending
   - `chosen_channel` in (`email`, `both`) AND not requires_human_review → Gmail send, update status
   - `chosen_channel` in (`linkedin`, `both`) AND not requires_human_review → set `linkedin_pending`
   - `overall_score >= 70` AND NOT requires_human_review → Slack lead alert
7. Return `agent_result` dict (for the dispatch result map)

Update `_DISPATCH` entry so `run_outreach_agent` maps to this function directly
(dispatch signature is `(lead, db)` which matches — no wrapper needed).

**Also update `app/routers/leads.py`:**
- Standalone `POST /leads/{id}/run-outreach-agent` endpoint:
  - Remove the check for existing `outreach_message` (404 guard) — no longer needed
  - Remove the DB query for `outreach` (lines 130–138 in current file)
  - Just fetch lead and analysis; call `execute_run_outreach_agent(lead, db)` directly
  - Keep the existing `outreach_execution_log` duplicate guard
  - Update the response to include content keys from the outreach record created
  - Keep `from app.routers.workflow import execute_run_outreach_agent` import

**Commit:** `refactor: implement unified outreach agent execution pipeline`

---

## Task 4 — Update lead detail dashboard

**Files:** `templates/lead_detail.html`

**Changes:**
1. Merge the two separate sections ("Outreach" and "Outreach Agent Decision") into one
   unified section titled "Outreach"
2. Unified section shows:
   - From outreach_messages: subject, email_body, follow_up_email, linkedin_message, call_notes
   - From execution_log: chosen_channel, agent_reasoning, execution_status, requires_human_review, review_reason, decided_at
3. If `execution_log.chosen_channel` in (`linkedin`, `both`) AND `execution_log.execution_status == "linkedin_pending"`:
   Show a prominent callout box with the LinkedIn message in a copy-to-clipboard box
4. If no execution_log exists (agent never run): show a single "Run Outreach Agent" button
   (no longer conditional on outreach existing first)
5. Remove the `runOutreachAgent` JS function's conditionality — it should simply POST to
   `/leads/{id}/run-outreach-agent` in any "not yet run" state
6. Keep the `runAgent` JS function unchanged

Also update `app/routers/dashboard.py` if it passes `outreach` separately from `execution_log`
— check that both `outreach` and `execution_log` variables are passed to the template.

**Commit:** `refactor: update lead detail dashboard for unified outreach agent`

---

## Task 5 — Tests

**File:** `tests/test_outreach_agent.py`

**Rewrite tests for unified architecture:**

### Test 1: `POST /leads/{id}/run-outreach-agent` returns 200 with both content and decision keys
- Mock: lead exists, analysis exists, no existing execution_log, unified agent returns all 10 keys
- Assert: 200 status, response contains `chosen_channel`, `agent_reasoning`, `requires_human_review`
- Note: standalone endpoint now only requires lead + analysis (no outreach prerequisite)

### Test 2: `POST /leads/{id}/run-outreach-agent` returns 404 when no analysis exists
- Mock: lead exists, no analysis
- Assert: 404

### Test 3: Service fallback returns all content + decision keys with requires_human_review=True
- Call `run_outreach_agent(lead_dict, analysis_dict)` (2 params, not 3)
- Mock Anthropic to raise exception
- Assert: `fallback` is True, all 10 keys present, `requires_human_review` is True,
  `chosen_channel` is "deferred"

### Test 4: Gmail is called when channel is email and requires_human_review is False
- Mock: full agent result with `chosen_channel="email"`, `requires_human_review=False`
- Assert: `gmail_service.send_email` was called once

### Test 5: Gmail is not called when requires_human_review is True
- Mock: full agent result with `requires_human_review=True`
- Assert: `gmail_service.send_email` was NOT called

### Test 6: Slack is called when overall_score >= 70
- Mock: analysis with `overall_score=80`, agent returns `requires_human_review=False`
- Assert: `slack_service.send_alert` was called

### Test 7: Orchestrator dispatches `run_outreach_agent` as a proper declared action
- Mock orchestrator to return `{"actions": ["analyze_lead", "run_outreach_agent"]}`
- Mock `execute_run_outreach_agent` in the dispatch
- Assert: 200, `run_outreach_agent` appears in `actions_executed`
- This replaces the old "handoff called when generate_outreach executed" test

### Test 8: Deterministic override — personal email domain forces deferred + review
- Call `run_outreach_agent(lead_dict, analysis_dict)` with gmail.com email
- LLM returns `chosen_channel="both"`, `requires_human_review=False`
- Assert: result `chosen_channel=="deferred"`, `requires_human_review==True`

Run: `docker compose exec api python -m pytest tests/test_outreach_agent.py -q`
Fix all failures before committing.

**Commit:** `test: update outreach agent tests for unified architecture`

---

## Task 6 — Smoke test

Rebuild and reset:
```bash
docker compose down -v
docker compose up --build -d
docker compose exec api alembic upgrade head
docker compose exec api python scripts/seed.py
```

Run full pipeline on a fresh lead:
```bash
curl -X POST http://localhost:8000/leads/1/run-agent
```

Confirm in DB:
- `lead_analysis` record with scores populated
- `outreach_messages` record with subject, email_body, linkedin_message all populated
- `outreach_execution_log` record with chosen_channel and agent_reasoning
- `automation_metrics` record
- `execution_status` is sent, failed, or linkedin_pending — not null or pending

Confirm in Docker logs: no swallowed exceptions.

**Commit:** `chore: smoke test unified outreach agent end to end`

---

## Task 7 — PR

Push branch and open PR to main:
- Title: `Refactor: Unified Outreach Agent — Full Ownership of Content and Channel`
- Body: before/after description, list of changed files
- Do NOT merge
- No Claude attribution in PR description

**Commit:** (no commit — just PR creation)
