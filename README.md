# Domino AI — Multi-Agent GTM Operating System

An AI-powered GTM automation platform that qualifies leads, generates personalised outreach, and executes multi-channel sales workflows — built with a multi-agent architecture on Claude AI, FastAPI, and HubSpot.

![Python](https://img.shields.io/badge/Python-3.12-blue?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.110-009688?logo=fastapi&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-316192?logo=postgresql&logoColor=white)
![Claude AI](https://img.shields.io/badge/Claude_AI-Haiku-orange?logo=anthropic&logoColor=white)
![HubSpot](https://img.shields.io/badge/HubSpot-CRM-FF7A59?logo=hubspot&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)

---

## Overview

GTM teams at B2B SaaS companies spend hours every week on work that shouldn't require human judgement: reading a new lead's profile, deciding whether they fit the ICP, writing a personalised email, choosing whether to also send a LinkedIn message, syncing the contact to HubSpot, and logging the outcome. Each step is low-complexity but high-volume, and the cumulative cost across a sales team is enormous.

Domino AI replaces that manual workflow with an autonomous multi-agent pipeline. A lead enters the system — through the UI, the API, or the AI-powered text parser — and a GTM Orchestrator Agent reads the record and decides which actions to execute. From there, specialist agents handle the execution: an Outreach Agent generates personalised content, picks the right channel, and sends via Gmail. Slack alerts notify the rep when a lead is high-priority or needs human attention. HubSpot is updated automatically.

The system is built around two AI agents with clearly defined responsibilities. The Orchestrator is a strategic decision-maker: it reads the lead, evaluates fit, and produces a JSON action plan. The Outreach Agent is a specialist executor: it takes the lead and analysis, generates all outreach content, decides the channel, sends the email, fires the Slack alert, and logs the HubSpot task — all in a single agent call. Neither agent encroaches on the other's domain.

This platform was built to serve revenue teams at multifamily PropTech companies, with seed data and outreach content modelled around Domino AI — a fictional AI-powered revenue operations platform for multifamily operators. The codebase demonstrates real production patterns: safe AI fallbacks, full audit logging, a clean router/service separation, and a deterministic override layer that enforces business rules the LLM cannot circumvent.

---

## Why I Built This

I built this as a portfolio project targeting GTM Engineer roles, specifically in the PropTech and multifamily housing sector. I wanted to demonstrate something concrete: not just that I can call an LLM, but that I understand how to build a system where agents make autonomous decisions with defined boundaries, handoff patterns, and failure modes.

The problem Domino AI solves is real. GTM teams waste enormous time on qualification, outreach writing, and CRM hygiene — tasks that are repetitive, context-dependent, and exactly the kind of work AI handles better and faster than humans at scale. A system that eliminates that work isn't a nice-to-have; it's a structural competitive advantage for any sales team.

The choice to use two agents rather than one reflects how I think about AI system design. A single monolithic agent that does everything is fragile and hard to reason about. Two agents with clearly scoped responsibilities are easier to test, debug, extend, and explain to a non-technical stakeholder. The Orchestrator decides what to do. The Outreach Agent decides how to do it.

The seed data and outreach templates are modelled around Domino AI selling to multifamily operators: VP Operations at national REITs, Directors of Leasing at regional property managers, CTOs evaluating PropTech solutions. This is deliberate — it demonstrates domain knowledge of the housing sector, not just generic SaaS lead patterns.

---

## Architecture

```
Lead Input
    │
    ▼
GTM Orchestrator Agent (Claude)
    │
    ├── analyze_lead ──────────────► Lead Analysis Service
    │                                    │
    │                                    ▼
    │                               lead_analysis Table
    │
    ├── run_outreach_agent ────────► Outreach Agent (Claude)
    │                                    │
    │                                    ├── Generates content
    │                                    ├── Decides channel
    │                                    ├── Sends via Gmail
    │                                    ├── Alerts via Slack
    │                                    └── Logs to HubSpot
    │
    ├── sync_hubspot ──────────────► HubSpot Service
    │                                    │
    │                                    ├── Search contact by email
    │                                    ├── Create or update contact
    │                                    └── Create note / task
    │
    └── mark_needs_review / skip_outreach
```

**Orchestrator decides what to do; the Outreach Agent decides how to do it.** The boundary between them is enforced by the dispatch map in the workflow router: the orchestrator's action plan is a list of string keys, and the dispatch map routes each key to its executor function. The outreach agent is never called directly by the orchestrator — it is invoked by its executor, which handles all downstream side effects.

**Routers own all database reads and writes.** Services are pure functions: they accept Python objects and return dicts. They never touch the database. This makes services independently testable and keeps the data access layer predictable.

**Safe fallbacks on every AI call.** Each agent has a `_FALLBACK` dict that is returned when the API call or JSON parse fails. The system degrades gracefully — a lead gets flagged for review rather than crashing the pipeline.

**All actions are logged even on failure.** The `outreach_execution_log` and `crm_sync_logs` tables capture the outcome of every action attempt, including error messages on failure. There is always a full audit trail.

---

## Multi-Agent Design

This is the core of the system and the most important section for understanding the architecture.

### GTM Orchestrator Agent

The Orchestrator lives in `app/agents/gtm_workflow_agent.py`. It receives a lead record and an optional prior analysis, then calls Claude (claude-haiku-4-5-20251001) with a system prompt that includes the full company and ICP context. Claude returns a JSON object with an `actions` array — a prioritised list of steps to execute.

The Orchestrator does not hardcode the workflow. Claude decides. The allowed action set is:

- `analyze_lead` — run AI lead analysis and score the lead
- `run_outreach_agent` — invoke the Outreach Agent for full outreach execution
- `sync_hubspot` — create or update the HubSpot contact and attach a note
- `create_hubspot_task` — create a HubSpot task for manual follow-up
- `mark_needs_review` — flag the lead for human review and halt automation
- `skip_outreach` — mark the lead as skipped; no outreach sent

Any action not in this set is silently dropped before execution, preventing prompt injection from causing unintended side effects.

### Outreach Execution Agent

The Outreach Agent lives in `app/services/outreach_agent_service.py`. It receives the lead dict and analysis dict, then calls Claude with a system prompt that includes outreach content rules and channel decision rules. In a **single AI call**, it generates every content field — email body, follow-up email, LinkedIn message, subject line, call notes — and makes the channel decision.

After the AI call, a `_apply_deterministic_overrides` function enforces hard business rules that Claude cannot override: personal email domains are always deferred, low overall scores always trigger human review, missing LinkedIn message always strips LinkedIn from the chosen channel. This separation — LLM handles judgement, deterministic code handles invariants — is a deliberate design choice.

The Outreach Agent owns the full outreach motion downstream: it writes to `outreach_messages` and `outreach_execution_log`, sends via Gmail, fires Slack alerts, and creates HubSpot tasks for LinkedIn actions.

### Why Two Agents

Separation of concerns. The Orchestrator is a strategic decision-maker with visibility over the full lead pipeline. The Outreach Agent is a specialist with deep context about content, channel strategy, and outreach rules. Neither needs to know about the other's internals.

A single agent doing both jobs would produce a larger, harder-to-tune prompt and would make it difficult to improve outreach quality without risking changes to workflow planning behaviour. Two agents allow each to be optimised, tested, and extended independently.

### How the Handoff Works

1. The Orchestrator includes `run_outreach_agent` in its action plan
2. The dispatch map in `app/routers/workflow.py` routes this to `execute_run_outreach_agent`
3. `execute_run_outreach_agent` fetches the latest analysis from the database and invokes the Outreach Agent
4. The Outreach Agent completes all downstream actions and returns its result dict
5. The executor writes the result to the database and returns to the main dispatch loop

### Adding New Actions

Three steps:
1. Add the action name to `_ALLOWED_ACTIONS` in `app/agents/gtm_workflow_agent.py` and include it in the orchestrator system prompt
2. Implement the executor function in `app/routers/workflow.py` following the `async def execute_*(lead, db) -> dict` signature
3. Register the executor in the `_DISPATCH` map in the same file

---

## Core Features

- **AI lead analysis** — fit score, urgency score, overall score (0–100), persona type, pain points, buying signals, objections, recommended action, and confidence score
- **Multi-agent outreach pipeline** — content generation and channel decision in a single Outreach Agent call, with deterministic overrides enforcing business rules
- **Multi-channel execution** — Gmail SMTP sending for email, LinkedIn manual action alerts via Slack for LinkedIn outreach
- **Slack notifications** — lead alerts for high-scoring leads, human review alerts for flagged leads, LinkedIn action required messages with the full message to send
- **HubSpot integration** — contact search to avoid duplicates, create or update contact with AI scores, note creation with analysis summary, task creation for LinkedIn manual actions
- **Call intelligence** — paste any call transcript, Claude extracts pain points, objections, competitors, budget signals, decision timeline, buying intent score (0–10), recommended follow-up, follow-up email draft, and CRM note; auto-syncs to HubSpot if the contact exists
- **AI lead parsing** — paste any unstructured text (LinkedIn profile, email signature, CRM export), Claude extracts all standard lead fields
- **ROI metrics dashboard** — total leads processed, average scores, hours saved, HubSpot sync rate, agent run timing
- **Seed data** — 20 realistic multifamily operator leads modelled as Domino AI prospects, covering a range of personas, company sizes, and fit scores

---

## HubSpot Integration

The HubSpot service (`app/services/hubspot_service.py`) implements four operations against the HubSpot v3 API:

1. **Contact search by email** — before creating any contact, the service searches by email to prevent duplicates. If a contact exists, its ID is returned and used for updates.
2. **Create or update contact** — the lead's full profile is synced including name, email, company, job title, phone, location, and AI-generated scores (`ai_fit_score`, `ai_overall_score`, `ai_recommended_action`). Existing contacts are updated with PATCH; new contacts are created with POST.
3. **Create note on contact** — an analysis summary is written as a HubSpot note, including persona type, pain points, buying signals, overall score, recommended action, and the generated email body. Notes are associated to the contact using HubSpot's v3 association type 202.
4. **Create task for LinkedIn actions** — when the Outreach Agent selects LinkedIn or both as the channel, a HubSpot task is created with the LinkedIn message as the task body, due immediately, associated to the contact.

HubSpot sync success rate is tracked in the `crm_sync_logs` table and surfaced in the ROI dashboard.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.12, FastAPI, SQLAlchemy, Alembic |
| Database | PostgreSQL 15 |
| AI | Anthropic API (claude-haiku-4-5-20251001) |
| CRM | HubSpot API v3 |
| Email | Gmail SMTP (SSL, port 465) |
| Alerts | Slack Incoming Webhooks |
| Frontend | Jinja2 Templates |
| Infrastructure | Docker, Docker Compose |
| Testing | pytest, pytest-asyncio, httpx |

---

## Local Setup

### Prerequisites

- Python 3.12
- Docker Desktop
- An Anthropic API key (required)
- A HubSpot private app access token (optional — CRM features are skipped if not set)
- A Gmail account with 2FA enabled and an App Password generated
- A Slack incoming webhook URL (optional — Slack alerts are skipped if not set)

### Steps

**1. Clone the repository**

```bash
git clone https://github.com/jmulvany127/GTM_AI_Automation.git
cd GTM_AI_Automation
```

**2. Configure environment variables**

```bash
cp .env.example .env
```

Open `.env` and fill in the values. Required variables:

| Variable | Description |
|---|---|
| `DATABASE_URL` | PostgreSQL connection string — leave as-is when using Docker Compose |
| `APP_ENV` | Application environment: `development` or `production` |
| `ANTHROPIC_API_KEY` | Your Anthropic API key — get one at console.anthropic.com |
| `HUBSPOT_ACCESS_TOKEN` | HubSpot private app token — create one in HubSpot Settings → Integrations → Private Apps |
| `SLACK_WEBHOOK_URL` | Slack incoming webhook URL — create one at api.slack.com/apps |
| `GMAIL_APP_PASSWORD` | Google App Password (not your account password) — generate at myaccount.google.com/apppasswords after enabling 2FA |
| `GMAIL_SENDER_ADDRESS` | The Gmail address you want to send outreach from |
| `USER_FULL_NAME` | Your full name — appears in email signatures and HubSpot owner field |
| `USER_EMAIL` | Your email — appears in HubSpot owner field |
| `COMPANY_NAME` | Your company name — injected into all agent prompts and outreach content |
| `COMPANY_LOCATION` | Your company location — injected into agent context |
| `COMPANY_DESCRIPTION` | Short description of your company — injected into agent system prompts |
| `PRODUCT_DESCRIPTION` | What your product does — used by the AI to write relevant outreach |
| `VALUE_PROPOSITION` | Your key value proposition — used to personalise outreach content |
| `TARGET_CUSTOMER` | ICP description — used by the Orchestrator to score lead fit |
| `KEY_INTEGRATIONS` | Key product integrations — referenced in call intelligence output |
| `KEY_PAIN_POINTS_WE_SOLVE` | Pain points your product addresses — used in outreach personalisation |
| `SENDER_TITLE` | Your job title — appears in outreach email signatures |
| `SENDER_COMPANY` | Your company name in the sender signature (usually matches COMPANY_NAME) |

**3. Start the services**

```bash
docker compose up --build -d
```

**4. Run database migrations**

```bash
docker compose exec api alembic upgrade head
```

**5. Seed the database**

```bash
docker compose exec api python scripts/seed.py
```

**6. Open the dashboard**

```
http://localhost:8000/dashboard/leads
```

**7. Explore the API**

```
http://localhost:8000/docs
```

---

## Seed Data

The seed script inserts 20 realistic B2B leads modelled as ideal Domino AI prospects in the multifamily housing sector. The dataset covers a range of personas:

- VP of Operations at national REITs managing 10,000+ units
- Directors of Leasing at regional operators evaluating PropTech
- CTOs and Heads of Technology assessing AI infrastructure
- Property Managers at mid-size portfolios still running manual workflows
- RevOps and Sales Directors at companies with leasing tech debt

All leads start with status `new`. Run the agent on any lead to see the full pipeline execute — analysis, outreach, channel decision, Gmail send, Slack alert, and HubSpot sync.

To reset the database and re-seed from scratch:

```bash
docker compose down -v && docker compose up -d && docker compose exec api alembic upgrade head && docker compose exec api python scripts/seed.py
```

---

## API Reference

Full interactive API documentation with request/response schemas is available at `http://localhost:8000/docs`.

### Leads

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/leads` | Create a new lead |
| `GET` | `/leads` | List all leads |
| `GET` | `/leads/{id}` | Get a single lead by ID |
| `PATCH` | `/leads/{id}` | Update a lead |
| `DELETE` | `/leads/{id}` | Delete a lead |

### Pipeline

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/leads/{id}/analyze` | Run AI analysis on a lead |
| `POST` | `/leads/{id}/generate-outreach` | Generate outreach content (no channel decision or sending) |
| `POST` | `/leads/{id}/run-agent` | Run the full GTM Orchestrator Agent — analysis, outreach, HubSpot sync |
| `POST` | `/leads/{id}/run-outreach-agent` | Run the Outreach Agent independently on an already-analysed lead |
| `POST` | `/leads/{id}/mark-linkedin-sent` | Mark a pending LinkedIn action as sent |

### CRM

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/leads/{id}/sync-hubspot` | Sync lead to HubSpot — create or update contact, attach note |

### Call Intelligence

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/call-notes/analyze` | Analyse a call transcript — extract intel and optionally sync to HubSpot |

### Metrics

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/metrics/roi` | ROI metrics — leads processed, time saved, scores, sync rates |

### Dashboard

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/dashboard/leads` | Lead list view |
| `GET` | `/dashboard/leads/{id}` | Lead detail view — analysis, outreach, CRM status |
| `GET` | `/dashboard/metrics` | ROI metrics view |
| `GET` | `/dashboard/call-notes` | Call intelligence list view |
| `GET` | `/dashboard/call-notes/new` | New call analysis form |

### Parsing

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/leads/parse` | Parse unstructured text into lead fields using AI |

---

## Database Schema

| Table | Purpose |
|---|---|
| `leads` | Core lead records — name, email, company, job title, status, source, location |
| `lead_analysis` | AI analysis output per lead — fit score, urgency score, overall score, persona type, pain points, buying signals, objections, recommended action, confidence score |
| `outreach_messages` | Generated outreach content per lead — email body, follow-up email, LinkedIn message, subject, call notes |
| `outreach_execution_log` | Outreach Agent channel decisions and execution status — chosen channel, agent reasoning, human review flag, execution status (pending / sent / failed / pending_manual) |
| `automation_metrics` | Agent run timing and ROI data per lead — actions executed, time saved estimate, requires human review flag |
| `crm_sync_logs` | HubSpot sync attempts and results per lead — sync status, external contact ID, error message |
| `call_analysis` | Call transcript analysis results — pain points, objections, competitors, budget signals, buying intent score, follow-up email, CRM note |

---

## Future Improvements

The current system covers the core GTM pipeline end-to-end. These are genuine extensions that would make it production-ready and more powerful:

**Multi-user authentication with role-based lead ownership** — right now the system is single-user. Adding JWT auth with lead ownership and assignment would allow a full sales team to use it, with each rep seeing only their own pipeline.

**Deployment to Railway or Render with demo mode** — the system is Docker Compose-local today. A public deployment with a read-only demo mode would let hiring managers and prospects interact with a live version without needing real API keys.

**RAG over prospect company websites** — instead of relying on job title and company name alone, a retrieval agent could scrape and embed the prospect's company website before outreach runs, enabling hyper-personalised messaging tied to their specific portfolio or product strategy.

**LinkedIn API integration** — LinkedIn outreach is currently manual-action-only due to API access constraints. When official partner API access becomes available, the Outreach Agent's LinkedIn channel could be fully automated.

**Webhook intake for real-time lead ingestion** — right now leads enter via the UI or API. Adding webhook endpoints would allow real-time ingestion from web forms, Typeform, HubSpot forms, or other CRMs, making the pipeline fully event-driven.

**A/B testing framework for outreach variants** — the Outreach Agent currently generates one version of every message. A framework that generates two variants and tracks reply rates would let the system learn which messaging patterns convert at the segment level.

**Expanded agent vocabulary** — a Research Agent that gathers company intel before outreach; a Scheduling Agent that books discovery calls when a prospect replies positively; a Renewal Agent for multifamily operators managing lease expiries. The three-step extension pattern in the codebase makes each of these straightforward to add.

---

## Author

Built by James Mulvany
GTM Engineer | New York
GitHub: [github.com/jmulvany127](https://github.com/jmulvany127)
