# CLAUDE.md — Project Context for Claude Code
# This file is automatically read by Claude Code at every session start

## ⚠️ CRITICAL — DO THIS FIRST BEFORE ANYTHING ELSE
Read these files in EXACT order before writing a single line of code:
1. `.kiro/steering/00-master.md`
2. `.kiro/steering/12-progress.md`
3. `.kiro/steering/11-build-strategy.md`
4. Then the relevant domain file for the current task

Then answer verification questions from `00-master.md` and WAIT for user confirmation.

---

## Project
**Wexa AI Technical Assessment**
Real-Time Analytics & Reporting Platform
Position: Senior Full Stack Engineer (Python)
Deadline: 2 days from receipt

---

## Quick Reference — Tech Stack
| Layer | Technology |
|---|---|
| Frontend | Next.js 14+ App Router, TypeScript, Tailwind, Shadcn/UI |
| State | Zustand |
| Charts | Recharts |
| Data Fetching | TanStack Query v5 |
| Backend | FastAPI, Python 3.11+ |
| ORM | SQLAlchemy 2.0 async |
| Migrations | Alembic |
| Validation | Pydantic v2 |
| Task Queue | Celery + Celery Beat |
| Cache/Queue | Redis via Upstash |
| Database | PostgreSQL via Neon |
| Email | Resend |
| Frontend Host | Vercel |
| Backend Host | Railway |

---

## Priority Order (NEVER deviate)
```
Phase 1 → Project architecture setup
Phase 2 → Auth & Multi-tenancy        ← MUST HAVE (30% score depends on this)
Phase 3 → Data Ingestion              ← MUST HAVE
Phase 4 → Dashboards & Widgets        ← MUST HAVE
Phase 5 → Alerts & Notifications      ← SHOULD HAVE (only after phase 4 done)
Phase 6 → WebSockets & Real-time      ← SHOULD HAVE (only after phase 5 done)
Phase 7 → Bonus features              ← SKIP unless all above complete
```

---

## Absolute Rules — NEVER Break These
- ✅ Always use async/await throughout
- ✅ Always add type hints to every function
- ✅ Always use Pydantic v2 syntax
- ✅ Always use SQLAlchemy 2.0 async patterns
- ✅ Always handle errors with custom exceptions
- ✅ Always update `.kiro/steering/12-progress.md` after completing any task
- ✅ Always commit to git after completing each phase
- ❌ Never use sync SQLAlchemy sessions
- ❌ Never hardcode environment variables
- ❌ Never build Should Have before Must Have is 100% complete
- ❌ Never start next phase without user confirmation
- ❌ Never use packages not listed in `03-tech-stack.md`
- ❌ Never create files outside defined folder structure in `02-architecture.md`
- ❌ Never guess — if unsure, STOP and ask user

---

## Conflict Resolution Hierarchy
```
1. User instruction in chat        → HIGHEST priority
2. Original PDF requirements       → Second priority
3. Steering files                  → Third priority
4. Your own judgment               → LOWEST priority (ask user first)
```

---

## Current Status
→ ALWAYS check `.kiro/steering/12-progress.md` first
→ Never assume what is done — read the file

---

## When Switching From Kiro To Claude Code
1. Read `12-progress.md` carefully
2. Read the specific domain steering file for current task
3. Answer verification questions
4. Wait for user confirmation
5. Continue from EXACT point Kiro stopped

---

## Before Ending Any Session
Run this checklist:
- [ ] Update `12-progress.md` with exact current status
- [ ] Note exact file and function being worked on
- [ ] Note any decisions made this session
- [ ] Note any blockers found
- [ ] Commit all changes to git with descriptive message
