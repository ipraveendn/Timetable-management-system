# VYUHA — AI Agent Instructions

> This file tells AI coding agents (Codex, Claude Code, Cline, Cursor, etc.) how to work with VYUHA.

---

## Project Overview

VYUHA is an AI-powered college timetable & substitution SaaS platform.

| Layer | Tech | Path |
|-------|------|------|
| Backend | Python 3.12 + FastAPI | `backend/` |
| Frontend | React 18 + Vite | `frontend/` |
| Database | Supabase (PostgreSQL + RLS) | Remote |
| AI Chat | Groq API (Llama 3.3 70B) | `backend/chat_handler.py` |
| Email | Gmail SMTP | `backend/tools/email_tool.py` |

---

## Key Files (by importance for debugging)

### Backend Core
| File | Lines | Purpose |
|------|-------|---------|
| `backend/chat_handler.py` | ~1650 | AI chatbot: intent classification → pronoun resolution → action inference → Groq API / manual fallback |
| `backend/auto_handler.py` | ~675 | Substitution engine: slot matching, load balancing, substitute ranking |
| `backend/main.py` | ~200 | FastAPI app, CORS, middleware, router mounting |
| `backend/auth_system.py` | ~900 | JWT auth, RBAC, login/register, college onboarding |
| `backend/timetable_engine.py` | ~350 | Rule-based timetable generation with 5-lock conflict system |
| `backend/config.py` | ~200 | Environment config, Supabase URL/keys |
| `backend/database.py` | ~50 | Supabase client singleton |

### Frontend Core
| File | Purpose |
|------|---------|
| `frontend/src/components/ChatAssistant.jsx` | Chat UI with markdown rendering, session management |
| `frontend/src/components/Dashboard.jsx` | Admin command center (Upload → Generate → Review → Approve) |
| `frontend/src/lib/api.js` | All API calls (axios), auth token management, college_id header |
| `frontend/src/App.jsx` | Router, auth context, protected routes |

---

## Architecture: Chat Handler Flow

```
User message
    │
    ▼
┌─────────────────────────┐
│ _classify_chat_intent() │ → casual / substitution / schedule / general
└─────────┬───────────────┘
          │
    ┌─────┴──────┐
    │            │
substitution   schedule / general
    │            │
    ▼            ▼
┌──────────────┐  ┌─────────────┐
│ DETERMINISTIC│  │ call_groq() │ → multi-turn history + tools
│ _infer_sub.. │  │ with manual │
│ _execute_..  │  │ fallback    │
└──────────────┘  └─────────────┘
```

**Critical**: Substitution queries NEVER go through Groq — they use deterministic DB lookups to avoid hallucinated faculty names.

---

## Memory & Pronoun Resolution Chain

When user says "him", "his", "her", "them", etc., the system resolves via:

1. `merged_context["substitution_faculty"]` — from frontend state
2. `merged_context["last_referenced_faculty"]` — from memory facts DB
3. `memory_facts["last_referenced_faculty"]` — direct DB lookup
4. `_extract_recent_faculty_reference(history)` — scan session history

**Key**: Every mentioned faculty is saved to `chat_memory_facts` table via `_upsert_memory_fact()`. If the regex fails to extract a name, the chain breaks.

---

## Debugging Workflows

### "Chat returns wrong response"
1. Check intent: add `print(f"INTENT: {intent}")` in `chat_interaction()`
2. Check pronoun resolution: does `_resolve_pronoun_to_faculty()` find the faculty?
3. Check memory: is `last_referenced_faculty` in `chat_memory_facts` table?
4. Check entity extraction: does `_extract_query_entities()` parse the message correctly?
5. Check Groq: is `GROQ_API_KEY` set? Is the API responding?

### "Substitution not finding results"
1. Check `faculty` table: does the name exist? Is `status = 'active'`?
2. Check `timetable_slots`: does the faculty have slots on that day?
3. Check `auto_handler.find_substitutes_for_slot()`: are candidates excluded by subject mismatch or load limits?

### "Frontend shows error"
1. Check browser console (F12) for network errors
2. Check `X-College-ID` header — is it set correctly?
3. Check auth token — is it expired?
4. Check CORS — is backend allowing the frontend origin?

### "Backend won't start"
1. Check `.env` — all required vars present?
2. Run: `python3 -c "import py_compile; py_compile.compile('main.py', doraise=True)"`
3. Check: `source venv/bin/activate && uvicorn main:app --reload --port 8000`

---

## Common Pitfalls

| Pitfall | Details |
|---------|---------|
| **Faculty names can be numeric** | "Faculty 01" — regex must use `[A-Za-z0-9]` not just `[A-Za-z]` |
| **Pronouns break substitution** | "him/his/her" must be resolved via memory chain, not passed as literal faculty names |
| **Groq API can timeout** | Always add manual fallback paths for schedule/general queries |
| **`today`/`tomorrow` resolution** | Use `datetime.now().strftime("%a")` — never hardcode day names |
| **Supabase RLS** | All tables have Row Level Security — use `service_role` key for backend |
| **College tenant isolation** | Every query MUST filter by `college_id` — never return cross-tenant data |

---

## Environment Variables (backend/.env)

```
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_KEY=eyJ...                    # anon key
SUPABASE_SERVICE_ROLE_KEY=eyJ...       # service role key (for RLS bypass)
JWT_SECRET=your_jwt_secret
GROQ_API_KEY=gsk_...                   # Groq API key for Llama chat
GMAIL_ADDRESS=your@gmail.com
GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx
```

---

## Commands

```bash
# Backend
cd backend && source venv/bin/activate
uvicorn main:app --reload --port 8000

# Frontend
cd frontend && npm run dev

# Syntax check
python3 -c "import py_compile; py_compile.compile('FILE.py', doraise=True)"

# Frontend build check
cd frontend && npm run build
```

---

## Database Tables

Core: `colleges`, `users`, `faculty`, `subjects`, `rooms`, `timetable_slots`
Leave: `leave_requests`, `substitutions`
Chat: `chat_sessions`, `chat_messages`, `chat_memory_facts`
System: `feature_flags`, `notifications`, `audit_logs`, `timetable_validation_logs`

Schema: `backend/schema.sql`

---

## Non-Negotiable Rules

1. **Never save timetable without conflict validator returning zero conflicts**
2. **Every DB query must filter by `college_id`** — no cross-tenant data leaks
3. **Substitution always deterministic** — never let LLM hallucinate faculty names
4. **Secrets in `.env` only** — nothing hardcoded
5. **Every function has try/except** — never crash, always return clear error
6. **Feature flags checked before optional modules** — not all colleges have rooms/shifts
