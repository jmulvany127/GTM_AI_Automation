````markdown
# AI GTM Operating System

An AI-powered Go-To-Market (GTM) automation platform that automates lead qualification, outreach generation, CRM updates, and revenue operations workflows using Large Language Models, workflow orchestration, and CRM integrations.

## Overview

Modern revenue teams spend significant time on repetitive manual work:

- Researching accounts
- Qualifying leads
- Updating CRM records
- Writing outreach emails
- Logging sales notes
- Tracking follow-up actions

This project automates those workflows by combining AI, workflow orchestration, and CRM integrations into a single platform.

A new lead enters the system, the platform analyzes the account, identifies likely pain points, generates personalized outreach, updates HubSpot, and tracks business impact through ROI metrics.

The system also includes a GTM Workflow Agent that decides which actions should be executed for each lead based on lead quality, confidence, and business rules.

---

## Key Features

### AI Lead Analysis

Automatically analyzes incoming leads and generates:

- Company summary
- Persona classification
- Pain points
- Buying signals
- Objections
- Fit score
- Urgency score
- Recommended next action

### Outreach Generation

Generates:

- Personalized email outreach
- Follow-up emails
- LinkedIn messages
- Sales call preparation notes

### GTM Workflow Agent

A controlled AI workflow agent that decides:

- Whether a lead should be analyzed
- Whether outreach should be generated
- Whether a lead should be synced to HubSpot
- Whether a follow-up task should be created
- Whether human review is required

### HubSpot Integration

Automatically:

- Creates or updates contacts
- Creates notes
- Creates follow-up tasks
- Logs synchronization events

### Call Intelligence

Analyzes sales call transcripts and extracts:

- Pain points
- Objections
- Competitors
- Budget signals
- Decision timeline
- Buying intent indicators
- Recommended follow-up actions

### ROI Tracking

Tracks:

- Leads processed
- High-priority leads
- Estimated hours saved
- Workflow execution time
- CRM synchronization success rates

---

# Architecture

```text
Frontend Dashboard
        │
        ▼
FastAPI Backend
        │
        ▼
GTM Workflow Agent
        │
 ┌──────┼──────────────┐
 ▼      ▼              ▼
OpenAI  PostgreSQL  HubSpot
        │
        ▼
 Metrics Dashboard
```

---

# Workflow

## Lead Processing Workflow

```text
Lead Submitted
      │
      ▼
Store Lead
      │
      ▼
Agent Creates Workflow Plan
      │
      ▼
AI Analysis
      │
      ▼
Lead Scoring
      │
      ▼
Outreach Generation
      │
      ▼
HubSpot Sync
      │
      ▼
Metrics Logging
      │
      ▼
Dashboard
```

---

## Call Intelligence Workflow

```text
Sales Transcript
        │
        ▼
OpenAI Analysis
        │
        ▼
Pain Points
Objections
Buying Signals
Competitors
Timeline
        │
        ▼
CRM Note
Follow-Up Email
Task Recommendation
```

---

# Technology Stack

## Backend

- Python 3.11
- FastAPI
- SQLAlchemy
- Alembic
- PostgreSQL

## AI

- OpenAI API
- Structured JSON outputs
- Prompt engineering
- Workflow planning agent

## CRM

- HubSpot API

## Infrastructure

- Docker
- Docker Compose

## Frontend

- Jinja Templates
- HTML/CSS

## Deployment

- Render
- Railway

---

# Database Schema

## leads

Stores lead information.

| Field | Description |
|---------|------------|
| id | Primary key |
| first_name | Lead first name |
| last_name | Lead last name |
| email | Email address |
| company | Company |
| job_title | Job title |
| company_website | Company website |
| source | Lead source |
| notes | Notes |
| status | Workflow status |

---

## lead_analysis

Stores AI-generated analysis.

| Field | Description |
|---------|------------|
| company_summary | AI company summary |
| persona_type | Persona classification |
| pain_points | Extracted pain points |
| buying_signals | Buying indicators |
| objections | Potential objections |
| fit_score | Lead fit score |
| urgency_score | Urgency score |
| overall_score | Overall lead score |
| confidence_score | AI confidence |

---

## outreach_messages

Stores generated outreach.

| Field | Description |
|---------|------------|
| subject | Email subject |
| email_body | Initial outreach |
| follow_up_email | Follow-up email |
| linkedin_message | LinkedIn message |
| call_notes | Call preparation notes |

---

## crm_sync_logs

Stores HubSpot synchronization events.

| Field | Description |
|---------|------------|
| sync_status | Success or failure |
| external_contact_id | HubSpot contact ID |
| error_message | Failure reason |

---

## automation_metrics

Stores ROI metrics.

| Field | Description |
|---------|------------|
| workflow_name | Executed workflow |
| automated_time_seconds | Runtime |
| estimated_time_saved_minutes | Estimated savings |

---

# GTM Workflow Agent

The GTM Workflow Agent acts as the system orchestrator.

Rather than hardcoding every step, the agent decides which actions should be executed for a given lead.

## Allowed Actions

```text
analyze_lead
generate_outreach
sync_hubspot
create_hubspot_task
mark_needs_review
skip_outreach
```

## Example Agent Output

```json
{
  "actions": [
    "analyze_lead",
    "generate_outreach",
    "sync_hubspot",
    "create_hubspot_task"
  ],
  "requires_human_review": false,
  "reasoning_summary": "Strong operations persona with clear automation pain points."
}
```

This approach enables flexible workflow automation while maintaining predictable system behavior.

---

# API Endpoints

## Health Check

```http
GET /health
```

---

## Lead Management

```http
POST /leads
GET /leads
GET /leads/{id}
PATCH /leads/{id}
DELETE /leads/{id}
```

---

## AI Analysis

```http
POST /leads/{id}/analyze
```

---

## Outreach Generation

```http
POST /leads/{id}/generate-outreach
```

---

## Agent Workflow

```http
POST /leads/{id}/run-agent
```

---

## HubSpot Sync

```http
POST /leads/{id}/sync-hubspot
```

---

## ROI Metrics

```http
GET /metrics/roi
```

---

## Call Intelligence

```http
POST /call-notes/analyze
```

---

# Example Workflow

### Step 1

Create a lead:

```json
{
  "first_name": "Sarah",
  "last_name": "Chen",
  "email": "sarah.chen@urbanliving.com",
  "company": "Urban Living Property Group",
  "job_title": "VP of Operations",
  "company_website": "https://urbanliving.com",
  "source": "webinar"
}
```

### Step 2

Run workflow:

```http
POST /leads/1/run-agent
```

### Step 3

Agent decides:

```json
{
  "actions": [
    "analyze_lead",
    "generate_outreach",
    "sync_hubspot"
  ]
}
```

### Step 4

System generates:

- AI lead analysis
- Personalized outreach
- HubSpot contact
- CRM note
- ROI metrics

---

# Local Development

## Clone Repository

```bash
git clone https://github.com/yourusername/ai-gtm-operating-system.git

cd ai-gtm-operating-system
```

## Configure Environment Variables

Create:

```bash
.env
```

Example:

```env
DATABASE_URL=postgresql://postgres:postgres@db:5432/gtm_db

OPENAI_API_KEY=your_key_here

HUBSPOT_ACCESS_TOKEN=your_token_here
```

---

## Start Services

```bash
docker compose up --build
```

---

## Run Migrations

```bash
alembic upgrade head
```

---

## Open API Docs

```text
http://localhost:8000/docs
```

---

## Seed Data

The seed script populates the database with 20 realistic B2B leads from the residential housing and property management sector, runs the full GTM pipeline (analysis, outreach generation, and agent workflow) on each new lead, and submits 6 realistic sales call transcripts for AI analysis. The script is idempotent — leads are matched by email address, so running it multiple times is safe and duplicate leads are skipped automatically.

**Prerequisites:** The application must be running before executing the seed script.

```bash
docker compose up --build
```

**Run the seed script:**

```bash
docker compose exec api python scripts/seed.py
```

**Reset all seeded data** (requires typing `yes` to confirm):

```bash
docker compose exec api python scripts/reset_db.py
```

---

# Future Improvements

### CRM Integrations

- Salesforce
- Pipedrive
- Outreach

### Workflow Automation

- Zapier integration
- Slack alerts
- Email notifications

### Advanced AI

- Multi-agent workflows
- Company website RAG
- Autonomous follow-up recommendations
- Pipeline health monitoring

### Analytics

- Conversion funnel tracking
- Pipeline forecasting
- Revenue attribution

---

# Why I Built This

I built this project to explore the intersection of software engineering, AI systems, workflow automation, and revenue operations.

Rather than building another chatbot or AI wrapper, I wanted to build a realistic internal platform that automates high-value business workflows and demonstrates how AI can be integrated directly into operational systems.

The project simulates the type of automation a GTM Engineer would build at a fast-scaling AI company, combining backend engineering, API integrations, workflow orchestration, AI tooling, and business impact measurement into a single system.
````
