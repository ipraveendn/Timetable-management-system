# VYUHA — AI-Powered College Timetable & Substitution System
## Master Project Context File
### Upload this file to any AI (Claude, Cursor, Cline) to build the entire project

---

## 1. WHAT IS VYUHA

VYUHA is a web-based SaaS application that solves three problems every college faces:

**Problem 1:** Building a timetable manually takes 2-3 days every semester. Admin uses Excel and trial-and-error to avoid conflicts. One change breaks everything.

**Problem 2:** When a teacher goes on leave, HOD spends 1-2 hours calling teachers one by one to find a replacement. No system checks if the replacement teaches the right subject or is already busy.

**Problem 3:** Every college has different data — some have rooms, some don't. Some have 6 slots per day, some have 8. One rigid system cannot handle all colleges.

**VYUHA solves all three:**
- Admin uploads one Excel file → AI generates conflict-free timetable in seconds
- Teacher goes on leave → system finds best replacement in 2 seconds automatically
- Different colleges → feature flags adapt the system to each college's data

---

## 2. WHO USES VYUHA

| Role | What They Do |
|------|-------------|
| Admin | Uploads Excel data, generates timetable, manages everything |
| HOD | Views full timetable, approves leave requests, confirms substitutions |
| Faculty/Teacher | Views personal timetable, applies for leave |
| Attendance Coordinator | Views substitution log, downloads monthly reports |

Each role gets their own dashboard after login. Same website, different screens.

---

## 3. TECH STACK — ALL FREE

| Layer | Tool | Why |
|-------|------|-----|
| Frontend | React + Vite + Tailwind CSS | Fast, free, beautiful |
| Backend | Python FastAPI | Simple, fast API |
| Database | Supabase (PostgreSQL) | Free tier, built-in auth |
| AI Brain | Llama 3.1 70B via OpenRouter | Free AI model |
| Excel Reading | Python openpyxl | Reads uploaded Excel |
| Email Alerts | Gmail SMTP | Free notifications |
| Frontend Hosting | Vercel | Free deployment |
| Backend Hosting | Railway.app | Free tier |
| AI Coding | Cline + VS Code | Free AI coding tool |

**Total build cost: $0**

---

## 4. FIVE CORE TECHNOLOGIES

### Technology 1 — Feature Flags
Every college has different data and different needs. Feature flags handle this.

Each college has a `college_config` record with boolean flags:
- `has_rooms` — does this college have room data?
- `has_shifts` — does this college have shift-based scheduling?
- `slots_per_day` — how many time slots per day? (6, 7, 8, etc.)
- `working_days` — which days? Mon-Fri or Mon-Sat?
- `wants_room_alloc` — should rooms be assigned in timetable?

**How it works:** When admin uploads Excel, system detects which sheets exist and auto-sets flags. If no Rooms sheet → `has_rooms = false` → room rules skipped automatically. Zero errors.

---

### Technology 2 — Rule-Based Timetable Engine
Generates conflict-free timetable using pure logic. NOT machine learning.

**6 Rules checked for every slot:**
1. Is this faculty already teaching at this exact time? → FACULTY TIME LOCK
2. Does this faculty teach this subject? → SUBJECT MATCH
3. Is this faculty assigned to this semester? → SEMESTER MATCH
4. Has this faculty hit their max classes today? → DAILY LOAD LOCK
5. Is this room already occupied? (if rooms enabled) → ROOM LOCK
6. Is this the right room type for this subject? (if rooms enabled) → ROOM TYPE MATCH

All 6 rules must pass. If any fails → skip → try next option.

---

### Technology 3 — Conflict Locking System
Makes double booking physically impossible.

**5 Locks:**
- **Faculty Lock** — Check in-memory dict AND database before every assignment
- **Room Lock** — Same dual check for rooms
- **Subject Lock** — Count assignments vs weekly limit before each new one
- **Load Lock** — Count today's classes vs max before adding
- **Substitution Lock** — Check substitutions table too, not just timetable

**How it works:** Every time a slot is assigned → immediately locked in memory dict. Next slot checks both memory AND database. Zero gap between assign and lock.

---

### Technology 4 — Conflict Validator
Final safety gate before any timetable is saved to database.

**What it checks:**
1. Any faculty assigned to 2+ classes same time? → REJECT
2. Any room used for 2+ classes same time? → REJECT
3. Any subject scheduled more than weekly limit? → REJECT
4. Any faculty assigned to subject they don't teach? → REJECT
5. Any faculty exceeding their daily max? → REJECT

**Golden Rule:** Timetable is NEVER saved to database without validator returning zero conflicts. If conflicts found → show exact list to admin → do not save.

---

### Technology 5 — AI Substitution Engine
Finds best replacement teacher in 2 seconds using 5 rules.

**5 Rules:**
1. Candidate must teach same subject as absent teacher
2. Candidate must handle same semester
3. Candidate must be free at exact leave time
4. Candidate must not already be covering another class same time
5. Candidate must not exceed their daily max load

**Ranking:** Sort passing candidates by lowest workload that day. Return top 3 with confidence score.

**Edge case:** If no substitute found → return clear warning. Never crash.

---

### Technology 6 — Chat Handler Agent
HOD and Admin type naturally. AI understands and acts.

**How it works:**
1. User types message in chat box
2. Message sent to FastAPI backend
3. Backend sends to Llama AI with system context + available tools
4. Llama understands intent → calls the right tool/function
5. Tool executes → result returned to Llama
6. Llama formats clean human-readable response
7. User sees clear reply with action buttons

**College ID:** Never typed by user. Always attached from login session automatically.

**Example conversations:**
```
User:  "sharma leave today who replaces"
AI:    "Prof. Sharma has 2 classes today:
        9am Maths Sem1 → Prof. Priya available [Confirm]
        2pm Stats Sem3 → Prof. Kumar available [Confirm]"

User:  "who is free thursday 11am"
AI:    "3 faculty free at Thursday 11am:
        Prof. Priya (2 classes that day)
        Prof. Raju (3 classes that day)"

User:  "how many classes does priya have today"
AI:    "Prof. Priya has 3 classes today. Max allowed: 4."
```

---

## 5. DATABASE SCHEMA — ALL 8 TABLES

```sql
-- Table 1: colleges
id uuid PK, name text, code text UNIQUE,
email text, plan text DEFAULT 'free',
created_at timestamptz

-- Table 2: college_config
id uuid PK, college_id uuid FK,
has_rooms bool DEFAULT false,
has_subjects bool DEFAULT true,
has_faculty bool DEFAULT true,
has_shifts bool DEFAULT false,
wants_room_alloc bool DEFAULT false,
wants_workload_report bool DEFAULT true,
working_days text[] DEFAULT '{Mon,Tue,Wed,Thu,Fri}',
slots_per_day int4 DEFAULT 6,
slot_duration_mins int4 DEFAULT 60,
start_time time DEFAULT '09:00',
created_at timestamptz

-- Table 3: faculty
id uuid PK, college_id uuid FK,
name text, employee_id text,
subjects text[], semesters int4[],
max_per_day int4 DEFAULT 4,
available_days text[], department text,
is_active bool DEFAULT true,
created_at timestamptz

-- Table 4: subjects
id uuid PK, college_id uuid FK,
name text, semester int4,
classes_per_week int4,
room_type text, duration_mins int4 DEFAULT 60,
created_at timestamptz

-- Table 5: rooms
id uuid PK, college_id uuid FK,
room_code text, room_name text,
capacity int4, room_type text,
available_days text[],
created_at timestamptz

-- Table 6: timetable
id uuid PK, college_id uuid FK,
semester int4, day text,
start_time time, end_time time,
subject_id uuid FK, faculty_id uuid FK,
room_id uuid FK NULLABLE,
is_substituted bool DEFAULT false,
created_at timestamptz

-- Table 7: leave_requests
id uuid PK, college_id uuid FK,
faculty_id uuid FK,
leave_date date, leave_type text,
status text DEFAULT 'Pending',
submitted_at timestamptz

-- Table 8: substitutions
id uuid PK, college_id uuid FK,
original_faculty_id uuid FK,
substitute_faculty_id uuid FK,
timetable_slot_id uuid FK,
date date, status text DEFAULT 'Pending',
notified_at timestamptz,
created_at timestamptz
```

Enable Row Level Security on ALL tables.
Add `college_id` index on every table.

---

## 6. BACKEND API ENDPOINTS

```
POST   /upload-excel              Upload Excel, auto-detect modules, save data
POST   /generate-timetable        Run rule engine + validator, save if clean
GET    /timetable?semester=       Get timetable for a semester
GET    /timetable/faculty/{id}    Get personal timetable for one teacher
GET    /timetable/full            Get full college timetable (HOD/Admin)
POST   /leave/submit              Faculty submits leave request
GET    /leave/all                 Admin/HOD views all leave requests
POST   /leave/approve/{id}        Approve leave + trigger substitution finder
POST   /leave/reject/{id}         Reject leave request
GET    /substitution/find/{id}    Find best substitutes for a leave
POST   /substitution/confirm      Confirm substitute + send notifications
GET    /substitution/log          Coordinator views all substitutions
GET    /report/monthly            Generate monthly report
POST   /chat                      Chat handler — natural language queries
GET    /health                    Health check
```

---

## 7. FRONTEND SCREENS

### Screen 1 — Login Page (everyone)
- Email + password
- On login → detect role → redirect to correct dashboard
- Roles: admin, hod, faculty, coordinator

### Screen 2 — Admin Dashboard
**Sidebar navigation:**
- Upload Data
- Generate Timetable
- View Timetable
- Faculty List
- Leave Requests
- Reports
- Chat

**Upload section:**
- Drag drop .xlsx file
- Shows detected modules after upload
- Success/error feedback

**Generate section:**
- Big generate button
- Loading state with progress text
- Success: summary (classes scheduled, unresolved count)
- Conflict found: exact list in red, do not save

**View Timetable:**
- Semester dropdown filter
- Grid: columns=days, rows=time slots
- Cell shows: subject + teacher + room
- Export Excel and PDF buttons

### Screen 3 — HOD Dashboard
- Today summary cards: total classes, on leave, substitutions, uncovered
- Pending leaves table with Approve/Reject buttons
- On approve: substitute suggestions appear inline with Confirm button
- Red alert banner if any class uncovered
- Full timetable view with filters
- Chat box

### Screen 4 — Faculty Dashboard
- Personal weekly timetable (their classes only)
- Apply leave form: date picker + leave type
- Substitution duties this week
- Leave history with status badges
- Chat box

### Screen 5 — Coordinator Dashboard
- Substitution log table with filters
- Faculty workload bars (green/yellow/red)
- Monthly summary cards
- Download report buttons

---

## 8. EXCEL TEMPLATE — WHAT COLLEGES MUST UPLOAD

### Sheet 1 — Faculty (REQUIRED)
| Column | Required | Example |
|--------|----------|---------|
| Name | YES | Dr. Sharma |
| Employee ID | YES | F001 |
| Subjects | YES | Maths, Statistics |
| Semesters | YES | 1, 3 |
| Max Per Day | NO | 4 |
| Available Days | NO | Mon,Tue,Wed,Thu,Fri |
| Department | NO | CSE |

### Sheet 2 — Subjects (REQUIRED)
| Column | Required | Example |
|--------|----------|---------|
| Name | YES | Engineering Maths |
| Semester | YES | 1 |
| Classes Per Week | YES | 5 |
| Room Type | NO | Classroom |
| Duration Mins | NO | 60 |

### Sheet 3 — Rooms (OPTIONAL)
| Column | Required | Example |
|--------|----------|---------|
| Room Code | YES | R101 |
| Room Name | YES | Room 101 |
| Type | YES | Classroom |
| Capacity | NO | 60 |
| Available Days | NO | Mon-Sat |

### Sheet 4 — Config (OPTIONAL)
| Column | Example |
|--------|---------|
| slots_per_day | 8 |
| start_time | 09:00 |
| working_days | Mon,Tue,Wed,Thu,Fri,Sat |

---

## 9. DUMMY DATA FOR TESTING

### 15 Faculty Members
```
F001, Dr. Sharma,    Maths+Statistics,        Sem 1+3, max 4/day
F002, Prof. Priya,   Physics+Electronics,     Sem 2+4, max 3/day
F003, Dr. Raju,      CS+DBMS,                 Sem 1+2, max 4/day
F004, Prof. Mehta,   Chemistry+Biology,       Sem 3+4, max 3/day
F005, Dr. Kumar,     Maths+Data Science,      Sem 2+4, max 4/day
F006, Prof. Anitha,  English+Communication,   Sem 1+2+3+4, max 5/day
F007, Dr. Venkat,    Electronics+Circuits,    Sem 1+3, max 4/day
F008, Prof. Lakshmi, DBMS+Software Engg,      Sem 3+4, max 3/day
F009, Dr. Suresh,    Physics+Maths,           Sem 1+2, max 4/day
F010, Prof. Divya,   Data Science+AI,         Sem 3+4, max 3/day
F011, Dr. Rajesh,    Chemistry+Env Science,   Sem 1+2, max 4/day
F012, Prof. Nithya,  CS+Python,               Sem 2+3, max 4/day
F013, Dr. Arun,      Statistics+Ops Research, Sem 3+4, max 3/day
F014, Prof. Kavitha, English+Soft Skills,     Sem 1+2+3, max 5/day
F015, Dr. Mohan,     Electronics+VLSI,        Sem 2+4, max 4/day
```

### Subjects Per Semester
```
Sem 1: Eng Maths(5), Physics(4), Chemistry(4), English(3), CS(4)
Sem 2: Maths2(5), Physics2(4), DBMS(4), Data Science(3), English2(3)
Sem 3: Statistics(4), Electronics(4), Software Engg(4), AI(3), Communication(3)
Sem 4: Ops Research(4), VLSI(4), Python(4), Data Science Adv(3), Soft Skills(3)
```

### 9 Rooms
```
R101-R104: Classrooms (60 capacity)
L101: Physics Lab (40)
L102: Chemistry Lab (40)
L103: Electronics Lab (40)
C101: Computer Lab A (40)
C102: Computer Lab B (40)
```

### College Config
```
slots_per_day = 8
start_time = 09:00
working_days = Mon,Tue,Wed,Thu,Fri,Sat
semesters = 4
has_rooms = true
wants_room_alloc = true
```

---

## 10. EXPECTED OUTPUT — WHAT THE APP PRODUCES

### Output 1 — Individual Teacher Timetable
```
DR. SHARMA — WEEKLY TIMETABLE
Day     | Time      | Subject    | Semester | Room
--------|-----------|------------|----------|------
Monday  | 9-10am    | Maths      | Sem 1    | R101
Monday  | 11-12pm   | Statistics | Sem 3    | R102
Tuesday | 9-10am    | Maths      | Sem 1    | R101
...
Total this week: 12 classes
```

### Output 2 — Full College Timetable (HOD/Admin view)
```
         MON           TUE           WED
9-10am   Maths/Sharma  Physics/Priya Maths/Sharma
         Sem1 R101     Sem2 L101     Sem1 R101
10-11am  CS/Raju       DBMS/Raju     CS/Raju
         Sem1 C101     Sem2 C101     Sem1 C101
...
```

### Output 3 — Substitution Suggestion
```
Prof. Sharma on leave Thursday.
His 2 classes need coverage:

Class 1: 9am Maths Sem1
  → Prof. Suresh (teaches Maths, free 9am, 2 classes today) [Confirm]
  → Dr. Kumar (teaches Maths, free 9am, 3 classes today) [Confirm]

Class 2: 2pm Statistics Sem3
  → Dr. Arun (teaches Stats, free 2pm, 1 class today) [Confirm]
```

### Output 4 — Monthly Coordinator Report
```
JANUARY 2025 — SUBSTITUTION REPORT
Total substitutions: 24
Auto-covered: 22 (91%)
Manual: 2 (9%)

Most absent: Dr. Sharma (4 times)
Most covered: Prof. Priya (6 substitutions)

Faculty Workload:
Dr. Sharma   ████████░░ 80%
Prof. Priya  ██████████ 100% ← at limit
Dr. Raju     ██████░░░░ 60%
```

---

## 11. COMPLETE FOLDER STRUCTURE

```
vyuha/
├── backend/
│   ├── main.py                  # FastAPI app, CORS, rate limiting
│   ├── database.py              # Supabase connection
│   ├── models.py                # Pydantic validation models
│   ├── excel_reader.py          # Read Excel, auto-detect modules
│   ├── feature_flags.py         # Read college_config, active rules
│   ├── timetable_engine.py      # Rule engine + 5-lock conflict locking
│   ├── conflict_validator.py    # Zero tolerance validator
│   ├── substitution_engine.py   # 5-rule AI matching
│   ├── leave_manager.py         # Leave CRUD + approval flow
│   ├── chat_handler.py          # Natural language agent + tool calling
│   ├── notifier.py              # Gmail SMTP notifications
│   ├── requirements.txt         # Pinned versions
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   │   ├── LoginPage.jsx
│   │   │   ├── AdminDashboard.jsx
│   │   │   ├── HODDashboard.jsx
│   │   │   ├── FacultyDashboard.jsx
│   │   │   └── CoordinatorDashboard.jsx
│   │   ├── components/
│   │   │   ├── ChatHandler.jsx
│   │   │   ├── TimetableGrid.jsx
│   │   │   ├── SubstituteCard.jsx
│   │   │   └── WorkloadBar.jsx
│   │   ├── services/
│   │   │   └── api.js
│   │   └── App.jsx
│   └── .env.example
├── sample_data/
│   └── sample_input.xlsx        # Dummy data ready to upload
├── .gitignore
└── README.md
```

---

## 12. ENVIRONMENT VARIABLES NEEDED

### Backend (.env)
```
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_anon_key
OPENROUTER_API_KEY=your_openrouter_key
GMAIL_ADDRESS=your@gmail.com
GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx
FRONTEND_URL=https://your-app.vercel.app
```

### Frontend (.env)
```
VITE_API_URL=https://your-backend.railway.app
```

---

## 13. NON-NEGOTIABLE RULES FOR BUILDING

1. Production ready code only. Zero placeholder code. Zero TODO comments.
2. All secrets in .env files. Nothing hardcoded. Ever.
3. Every function wrapped in try/except with clear error messages.
4. Every database query filtered by college_id.
5. Timetable NEVER saved without conflict_validator returning zero conflicts.
6. Feature flags checked before every optional module runs.
7. 5 locks checked before every slot assignment.
8. Chat handler always attaches college_id from session — never from user input.
9. Must work when deployed on Railway + Vercel — not just localhost.
10. One teacher can teach multiple subjects — subjects stored as array.
11. slots_per_day is configurable — never hardcoded as 6 or 8.
12. If no substitute found — return clear warning, never crash.

---

## 14. HOW TO BUILD — PHASE BY PHASE

```
Phase 1 — Setup (Day 1-2)
→ Create folder structure
→ Setup FastAPI backend
→ Setup React Vite frontend
→ Create all 8 Supabase tables
→ Enable RLS on all tables

Phase 2 — Core Engine (Day 3-7)
→ Build Excel reader with auto-detection
→ Build feature flags system
→ Build timetable engine with 5 locks
→ Build conflict validator

Phase 3 — Features (Day 8-14)
→ Build leave management system
→ Build substitution engine
→ Build notification system

Phase 4 — Frontend (Day 15-21)
→ Build all 4 dashboards
→ Build chat handler component
→ Connect all API calls

Phase 5 — Deploy (Day 22-25)
→ Deploy backend on Railway
→ Deploy frontend on Vercel
→ Security audit
→ Test with dummy data

Phase 6 — Polish (Day 26-30)
→ Fix bugs
→ Improve UI
→ Prepare demo
→ Create sample Excel template
```

---

## 15. DEMO SCRIPT — 10 MINUTES

```
Min 0-1:  "Every college wastes 3 days building timetable 
           and 2 hours finding substitutes. VYUHA solves both."

Min 1-3:  Upload sample Excel → Click Generate
           Show: 60+ classes scheduled in seconds, zero conflicts

Min 3-5:  Show full timetable grid
           Show Dr. Sharma's personal timetable
           Filter by semester

Min 5-7:  Type in chat: "sharma leave today"
           Show: AI finds 2 replacements in 2 seconds
           Click Confirm → done

Min 7-8:  Show coordinator dashboard
           Monthly substitution log
           Download report

Min 8-10: "One Excel upload. Zero manual scheduling.
           Zero phone calls. 2 seconds instead of 2 hours.
           Works for any college. Plug and play."
```

---

## 16. STANDARD REQUIREMENTS FOR COLLEGES USING VYUHA

VYUHA defines the standard. Colleges follow it.

**To use VYUHA, college must provide:**
1. Teacher names and employee IDs
2. Verified subjects each teacher can teach
3. Which semesters each teacher handles
4. Subject list with weekly class count
5. Optionally: room data, shift data

**VYUHA does NOT accept:**
- Random unverified teacher-subject assignments
- Incomplete faculty data
- Missing required columns in Excel

**This forces colleges to organize their data properly before using VYUHA.**

---


