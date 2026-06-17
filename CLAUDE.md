# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AI-powered Go-To-Market automation platform. Leads enter the system, a GTM Workflow Agent decides which actions to execute (analyze, generate outreach, sync HubSpot), and results are tracked via ROI metrics.

## Tech Stack

- **Backend**: Python 3.12, FastAPI, SQLAlchemy, Alembic
- **Database**: PostgreSQL
- **AI**: OpenAI API (structured JSON outputs)
- **CRM**: HubSpot API
- **Frontend**: Jinja2 templates (HTML/CSS)
- **Infrastructure**: Docker, Docker Compose

## Development Commands

```bash
# Start all services (API + PostgreSQL)
docker compose up --build

# Run database migrations
alembic upgrade head

# Create a new migration
alembic revision --autogenerate -m "description"

# API docs (once running)
open http://localhost:8000/docs
```

## Environment Variables

Required in `.env`:
```
DATABASE_URL=postgresql://postgres:postgres@db:5432/gtm_db
OPENAI_API_KEY=your_key_here
ANTHROPIC_API_KEY=your_anthropic_key_here
HUBSPOT_ACCESS_TOKEN=your_token_here
```

## Architecture

The system has a single FastAPI backend that routes all requests. The core flow is:

1. **Lead ingestion** → stored in `leads` table
2. **GTM Workflow Agent** → calls OpenAI to produce a JSON plan of actions (`analyze_lead`, `generate_outreach`, `sync_hubspot`, `create_hubspot_task`, `mark_needs_review`, `skip_outreach`)
3. **Action executors** → each action is a discrete function that calls OpenAI or HubSpot and writes results to the appropriate table
4. **Metrics logging** → every executed workflow writes to `automation_metrics`

Key tables: `leads`, `lead_analysis`, `outreach_messages`, `crm_sync_logs`, `automation_metrics`.

The Agent is the orchestrator — it does not hardcode which steps run. It returns a structured JSON plan, and the backend iterates over the `actions` array. This means adding new action types requires: (1) adding to the allowed actions list in the agent prompt, (2) implementing the executor function, (3) registering it in the action dispatch map.

## API Shape

All routes are under a single FastAPI app. Lead lifecycle: `POST /leads` → `POST /leads/{id}/run-agent`. Individual steps can also be triggered directly: `/analyze`, `/generate-outreach`, `/sync-hubspot`. Call intelligence is separate: `POST /call-notes/analyze`.

## Git Workflow
- All work on feature branches — never commit to `main`
- Branch naming: `feature/<topic>`, `fix/<topic>`, `chore/<topic>`
- Commit after each logical unit of work using Conventional Commits
- Push branch when task is complete and open a PR
- Do NOT merge — wait for my review

## Folder Structure
app/
├── main.py
├── config.py
├── database.py
├── models/
├── schemas/
├── routers/
├── services/
├── agents/
├── templates/
└── static/

## Agent Prompt Format
When I give you a task, follow this structure:
- Do not change unrelated files
- Follow the existing folder structure above
- Add error handling
- Explain what you changed