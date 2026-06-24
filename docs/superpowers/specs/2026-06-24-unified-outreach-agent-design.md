# Design Spec: Unified Outreach Agent

Branch: feature/unified-outreach-agent
Date: 2026-06-24

---

## Current State

### What `outreach_agent_service.py` currently returns (5 keys — channel decision only)
```
chosen_channel, agent_reasoning, requires_human_review, review_reason, personalisation_notes
```

### What `outreach_service.py` currently returns (5 keys — content only)
```
subject, email_body, follow_up_email, linkedin_message, call_notes
```

### Hardcoded side effect in `workflow.py` — exact location
Lines 263–285 in `app/routers/workflow.py`. After the `generate_outreach` executor dispatches
and returns, there is a hardcoded `if action == "generate_outreach":` block that immediately
calls `execute_run_outreach_agent` as a side effect. This is NOT a declared dispatch action.

```python
if action == "generate_outreach":
    try:
        analysis_row = await db.execute(...)
        analysis_obj = analysis_row.scalar_one_or_none()
        outreach_row = await db.execute(...)
        outreach_obj = outreach_row.scalar_one_or_none()
        _, agent_result = await execute_run_outreach_agent(lead, analysis_obj, outreach_obj, db)
        results["outreach_agent"] = agent_result
    except Exception as exc:
        _logger.error("Outreach agent handoff failed: %s", exc)
        results["outreach_agent"] = {"status": "error", "detail": str(exc)}
```

### `_ALLOWED_ACTIONS` in `app/agents/gtm_workflow_agent.py`
```python
_ALLOWED_ACTIONS = {
    "analyze_lead",
    "generate_outreach",
    "sync_hubspot",
    "create_hubspot_task",
    "mark_needs_review",
    "skip_outreach",
}
```

### `_DISPATCH` in `app/routers/workflow.py`
```python
_DISPATCH = {
    "analyze_lead": execute_analyze_lead,
    "generate_outreach": execute_generate_outreach,
    "sync_hubspot": execute_sync_hubspot,
    "create_hubspot_task": execute_create_hubspot_task,
    "mark_needs_review": execute_mark_needs_review,
    "skip_outreach": execute_skip_outreach,
}
```

### Does `run_outreach_agent` currently appear in `_ALLOWED_ACTIONS`? **No.**
### Does `generate_outreach` currently appear in `_ALLOWED_ACTIONS`? **Yes.**

### Where is `outreach_messages` currently written and by which service?
Two paths:
1. **Orchestrator path**: `execute_generate_outreach` in `workflow.py` calls `outreach_service.generate_outreach` then writes `OutreachMessage` to DB.
2. **Standalone endpoint path**: `POST /leads/{id}/generate-outreach` in `app/routers/outreach.py` calls the same service and writes to DB.

---

## Target State

### Unified Outreach Agent (`app/services/outreach_agent_service.py`)

One AI call generates both content and channel decision. Returns all 10 keys:

**Content keys:**
- `subject` — compelling email subject line personalised to the lead
- `email_body` — personalised email under 130 words, signed with `{USER_FULL_NAME} | {SENDER_TITLE} | {COMPANY_NAME}`
- `follow_up_email` — follow-up email under 90 words
- `linkedin_message` — complete LinkedIn message strictly under 280 characters, never truncated
- `call_notes` — prep notes for a future call

**Decision keys:**
- `chosen_channel` — email, linkedin, both, or deferred
- `agent_reasoning` — 2-3 sentences explaining channel decision
- `requires_human_review` — boolean
- `review_reason` — string or null
- `personalisation_notes` — additional context or null

Function signature: `run_outreach_agent(lead: dict, analysis: dict) -> dict`
(No longer receives pre-generated outreach content as input.)

Fallback dict: includes all 10 keys with sensible placeholders, `requires_human_review: True`,
`review_reason: "Agent unavailable — review before sending"`, `fallback: True`.

`max_tokens`: 2000 to ensure full JSON never truncated.

`_apply_deterministic_overrides` must check `result.get("linkedin_message")` (generated inline)
instead of `outreach.get("linkedin_message")` (pre-generated). Signature changes to
`_apply_deterministic_overrides(result, lead, analysis)`.

### Orchestrator (`app/agents/gtm_workflow_agent.py`)

- Remove `generate_outreach` from `_ALLOWED_ACTIONS`
- Add `run_outreach_agent` to `_ALLOWED_ACTIONS`
- Update system prompt: remove mention of `generate_outreach`, replace with `run_outreach_agent`
- Decision rule update: `generate_outreach` → `run_outreach_agent`

### Dispatch (`app/routers/workflow.py`)

- Remove `generate_outreach` entry from `_DISPATCH`
- Add `run_outreach_agent` to `_DISPATCH` pointing to a new `execute_run_outreach_agent_dispatch` wrapper
  that matches the `(lead, db)` signature used by other dispatch executors
- Remove the hardcoded side effect block (lines 263–285)
- Keep the existing `execute_run_outreach_agent` function but update its signature:
  - OLD: `(lead, analysis_obj, outreach_obj, db)` — received pre-generated outreach
  - NEW: `(lead, db)` for dispatch path — fetches analysis from DB, calls unified agent,
    writes BOTH `OutreachMessage` AND `OutreachExecutionLog`

### Router execution sequence after unified agent returns

After `run_outreach_agent` returns its 10 keys:
1. Write content keys (`subject`, `email_body`, `follow_up_email`, `linkedin_message`, `call_notes`) to `outreach_messages` table
2. Write decision keys to `outreach_execution_log` table (linked to the new `outreach_messages` row)
3. If `requires_human_review` is False AND `chosen_channel` in (`email`, `both`) → call `gmail_service.send_email`, set `execution_status` to `sent` on success or `failed` on failure
4. If `chosen_channel` in (`linkedin`, `both`) → set `execution_status` to `linkedin_pending`
5. If `overall_score >= 70` OR `requires_human_review` is True → call `slack_service.send_alert`
6. Slack: use `build_review_alert` when `requires_human_review` is True, `build_lead_alert` when score >= 70

Note: The plan spec says score 7.0 (out of 10). The DB stores score as 0–100. The Slack
`build_lead_alert` already divides by 10 when > 10. The threshold comparison is against the
DB value. Using `>= 70` (consistent with current workflow.py line 195 which uses `>= 70`).

### Standalone endpoint (`app/routers/leads.py`)

`POST /leads/{id}/run-outreach-agent`:
- OLD: required existing `outreach_message` (404 if missing)
- NEW: requires only existing analysis; does NOT require pre-existing outreach message
- Duplicate guard: check for existing `outreach_execution_log` (unchanged)
- Calls the same `execute_run_outreach_agent` function used by the dispatch path

### `outreach_service.py` (the content-only service)

**Unchanged.** Remains a standalone utility. The `/generate-outreach` endpoint remains
available for manual use only. Never called by the orchestrator or outreach agent.

### Lead detail template (`templates/lead_detail.html`)

- Merge "Outreach" and "Outreach Agent Decision" into one "Outreach" section
- Show unified content: subject, email_body, follow_up_email, linkedin_message, call_notes,
  chosen_channel, agent_reasoning, execution_status, requires_human_review, review_reason
- If `execution_log.chosen_channel` includes linkedin AND `execution_status == "linkedin_pending"`:
  show prominent manual action callout with LinkedIn message in a copy-to-clipboard box
- If no execution log exists (agent never run): show single "Run Outreach Agent" button
- Remove separate "Run Outreach Agent" button that appears only after outreach exists

---

## Files Changing

1. `app/services/outreach_agent_service.py` — full rewrite
2. `app/agents/gtm_workflow_agent.py` — update `_ALLOWED_ACTIONS` + system prompt
3. `app/routers/workflow.py` — rewrite `execute_run_outreach_agent`, add to dispatch, remove hardcoded side effect, remove `execute_generate_outreach` from dispatch
4. `app/routers/leads.py` — update standalone endpoint (no outreach prerequisite, import cleanup)
5. `templates/lead_detail.html` — merge sections, update buttons, add LinkedIn callout
6. `tests/test_outreach_agent.py` — full rewrite

## Files NOT Changing

- `app/services/outreach_service.py`
- `app/routers/outreach.py`
- All models
- All migrations (no schema changes needed — `outreach_messages` already has all content columns)
- `app/schemas/outreach.py`
