# Huduma Global — AI Diaspora Services Platform

A Django-based AI assistant that helps Kenyan diaspora customers initiate and track services back home — money transfers, service hires, document verification, and airport pickups.

---

## Quick Start

```bash
# 1. Install dependencies
pip install django openai

# 2. Apply migrations
python manage.py migrate

# 3. (Optional) Seed sample data
python manage.py shell < seed.py

# 4. Run the server
python manage.py runserver
```

Open http://localhost:8000 in your browser.

---

## Features Implemented

- Plain-English input with example chips
- AI intent extraction (5 intents, structured JSON)
- Risk scoring with Kenya-specific logic 
- Task creation with unique codes (VG-XXXXXXXX) 
- Step generation (intent-specific, 3–6 steps) 
- Three-format messages (WhatsApp, Email, SMS) 
- Employee/team assignment 
- Task dashboard with live status updates 
- Full database persistence + SQL dump 

---

## Risk Scoring Logic

Scores are calculated from 0–100. Levels: **Low** (0–30), **Medium** (31–60), **High** (61–100).

### Rules

**Base score by intent:**
- `send_money`: 20 — financial transactions always carry baseline risk
- `verify_document`: 25 — document fraud is common; involves third-party trust
- `hire_service`: 10 — lower financial exposure
- `get_airport_transfer`: 8 — logistical, not financial
- `check_status`: 0 — no action taken

**Urgency modifier:**
- High urgency: +20 — urgency is a classic social engineering signal
- Low urgency: −5

**Amount (money transfers, normalised to KES):**
- ≥ 500,000: +30
- ≥ 100,000: +20
- ≥ 50,000: +10
- ≥ 10,000: +5

**Recipient clarity:**
- No recipient name: +15 — unverified recipient = higher fraud risk
- No stated relationship: +5

**Document type:**
- Land title: +25 — land fraud is extremely common in Kenya; title deeds are frequently forged
- National ID / passport: +10
- General certificate: +8

**Combined signal:**
- High urgency + money transfer: additional +10 — "send money urgently for sick relative" is a well-known scam pattern

---

## System Prompt Design

### What I included
- A strict instruction to return **only JSON** with no prose, no markdown fences — this was critical to make the output reliably parseable
- An exact JSON schema with every field specified, including null defaults — prevents KeyError at parse time
- Explicit intent enumeration so the model can't invent new ones
- A `{TASK_CODE}` literal placeholder in all three messages, replaced server-side after the task record is created
- Intent-specific step guidance embedded implicitly by asking for "logical steps to fulfil the task"

### What I excluded
- Customer history / prior task data (not modelled yet; would be added in v2 as a RAG lookup)
- Any tone instructions beyond channel type — the model naturally adapts WhatsApp vs email well
- Explicit step count per intent — I found "3–6 steps" in the prompt led to inconsistent output; removing the number and letting the model judge produced better results

---

## Decisions I Made and Why

### AI tools used
- **Claude (claude.ai)** — to review the system prompt design and test edge cases like ambiguous requests
- **Claude Code** — for rapid iteration on the Django models and views structure
- **Copilot** — minor autocomplete in CSS

### One decision where I overrode AI suggestions
When I first asked Claude to help structure the risk scoring, it suggested a simple lookup table: `{"send_money": 30, "verify_document": 40, ...}` with a single multiplier. I overrode this because flat scores ignore the interaction effects that matter most in fraud detection — particularly the combination of high urgency + large amount + unknown recipient, which is precisely the pattern of "send money urgently for sick relative" scams. I built additive scoring instead, so multiple risk factors compound.

### One thing that didn't work as expected
The AI initially returned JSON with inconsistent field names — sometimes `"recipient"` instead of `"recipient_name"`, sometimes omitting null fields entirely. This caused KeyError crashes in the views. I resolved it by making the system prompt more explicit: listing every expected field with its type and null default, and adding a `re.sub` step server-side to strip any accidental markdown fences the model might prefix. The strictness of the schema in the prompt was the real fix.

---

## Project Structure

```
vunoh_global/
├── assistant/
│   ├── models.py          # Task, TaskStep, TaskMessage, StatusHistory
│   ├── views.py           # API endpoints + dashboard view
│   ├── ai_engine.py       # Claude integration, risk scoring, team assignment
│   └── urls.py
├── templates/assistant/
│   └── dashboard.html     # Single-page dashboard
├── static/
│   ├── css/main.css
│   └── js/main.js
├── schema_and_data.sql    # SQL dump with schema + 5 sample tasks
└── README.md
```

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Dashboard UI |
| POST | `/api/submit/` | Submit a new request |
| GET | `/api/tasks/` | List all tasks (JSON) |
| POST | `/api/tasks/<id>/status/` | Update task status |

