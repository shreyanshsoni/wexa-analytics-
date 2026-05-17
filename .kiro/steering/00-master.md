# 00-master.md — Master Context File
# READ THIS FIRST BEFORE ANY OTHER FILE

---

## What Is This Project
Wexa AI technical assessment for Senior Full Stack Engineer (Python) position.
Build a Real-Time Analytics & Reporting Platform — think lightweight Mixpanel/Metabase.

## Original Requirements Source of Truth
→ File: `wexa_ai_assessment.pdf`
→ This PDF is the HIGHEST priority reference
→ If any steering file conflicts with PDF — PDF wins always
→ Report any conflict to user immediately before proceeding

---

## How To Use Steering Files

### Read Order (MANDATORY — every session)
```
1. This file              (00-master.md)
2. Current progress       (12-progress.md)
3. Build strategy         (11-build-strategy.md)
4. Then domain file for current task only
```

### Domain File Map
| Current Task | Read This File |
|---|---|
| Setting up project | 02-architecture.md + 14-coding-order.md |
| Auth / roles / permissions | 06-security-auth.md |
| Database / migrations / seeding | 05-database.md |
| Data ingestion / API keys / pipeline | 04-features.md + 07-backend.md |
| Dashboards / widgets / charts | 04-features.md + 08-frontend.md |
| Alerts / notifications | 04-features.md + 07-backend.md |
| WebSockets / real-time | 04-features.md + 08-frontend.md |
| API endpoints / responses | 07-backend.md + 13-api-shapes.md |
| Frontend components / state | 08-frontend.md |
| Deployment / environment | 09-infrastructure.md |
| Testing / quality | 10-quality.md |
| Tech stack / packages | 03-tech-stack.md |

---

## Verification Questions — Answer Before Coding
Every session start, answer ALL of these and WAIT for user confirmation:

```
1. What phase are we currently in? (check 12-progress.md)
2. What is the exact task right now?
3. Which steering files did you read?
4. What does "done" look like for this task?
5. What files will you create or modify?
6. Are there any Must Have features still incomplete?
```

DO NOT start coding until user confirms answers are correct.

---

## Evaluation Criteria (Never Forget These Weights)
```
30% → Python Code Quality & Architecture
       (clean separation, type hints, async, DI, SOLID)

25% → Functionality & Completeness
       (must-haves working, edge cases, error states, pipeline reliability)

10% → UI/UX & Frontend
       (responsive, chart interactions, loading states, optimistic updates)
```

**Implication:** Perfect architecture + 3 working must-have features > messy code with all features

---

## Must Have vs Should Have (From PDF)
```
MUST HAVE (build these first, completely):
├── Authentication & Multi-tenancy
├── Data Ingestion
└── Dashboards & Widgets

SHOULD HAVE (only after must-haves are 100% done):
├── Alerts & Notifications
└── Real-Time WebSocket Updates

OPTIONAL (skip unless everything else is complete):
└── Google OAuth
    GraphQL API
    OpenTelemetry
    Load testing
    Feature flags
```

---

## Conflict Resolution Hierarchy
```
Priority 1 → User instruction in chat (always wins)
Priority 2 → Original PDF requirements
Priority 3 → Steering files
Priority 4 → AI judgment (ask user before acting on this)
```

---

## Context Window Management
When session is getting long (many files read, much code written):
1. STOP before context fills completely
2. Update `12-progress.md` with granular current status
3. Note exact function/line being worked on
4. Commit all changes to git
5. Tell user: "Context is filling up. I've updated progress.md and committed. Please start a new session."

---

## Absolute Rules — NEVER Break
```
✅ Async/await everywhere
✅ Type hints on every function and variable
✅ Pydantic v2 syntax only
✅ SQLAlchemy 2.0 async only
✅ Custom exceptions always
✅ Update 12-progress.md after every completed task
✅ Git commit after every completed phase
✅ Answer verification questions before coding
✅ Wait for user confirmation before next phase

❌ Never sync SQLAlchemy
❌ Never hardcode env variables
❌ Never build Should Have before Must Have complete
❌ Never start next phase without user saying "proceed"
❌ Never use packages not in 03-tech-stack.md
❌ Never create files outside structure in 02-architecture.md
❌ Never guess — always ask user when unsure
❌ Never skip error handling
❌ Never skip type hints
❌ Never push to main branch directly
```

---

## Two Phases of Development
```
Phase 1 — Local Development
  Frontend  → localhost:3000
  Backend   → localhost:8000
  Celery    → local terminal
  DB        → Neon (dev branch)
  Redis     → Upstash (wexa-dev database)

Phase 2 — Production
  Frontend  → Vercel
  Backend   → Railway
  Celery    → Railway (separate service)
  DB        → Neon (main branch)
  Redis     → Upstash (wexa-prod database)
```

---

## Git Branch Strategy
```
main   → production (auto deploys to Vercel + Railway)
dev    → daily development (NEVER auto deploys)

Rule: Always code on dev branch
      Only merge to main when ready to deploy
```

---

## AI Handoff Protocol
### Before switching AI:
1. Ask current AI: "Update 12-progress.md with granular current status"
2. Verify progress.md is accurate
3. Git commit everything with message: "chore: progress update before AI switch"
4. Note the exact steering files relevant to current task

### After switching AI:
1. Give new AI: "Read all .kiro/steering/ files starting with 00-master.md"
2. Upload PDF if possible
3. Ask verification questions
4. Confirm answers before proceeding
