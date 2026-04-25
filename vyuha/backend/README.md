# VYUHA Backend

## Local Setup

```bash
cd /home/rushi/project/backend
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
./venv/bin/python main.py
```

API default URL: `http://localhost:8000`

## Required Environment Variables

```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
SUPABASE_KEY=your-anon-key
JWT_SECRET=at-least-32-characters-long-random-secret
ALLOWED_ORIGINS=https://your-frontend-domain.vercel.app
ENVIRONMENT=production
```

Optional:

```env
FRONTEND_URL=https://your-frontend-domain.vercel.app
GROQ_API_KEY=...
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=...
SMTP_PASSWORD=...
SMTP_FROM_EMAIL=noreply@institution.edu
```

## Production Constraints

- In `ENVIRONMENT=production`, CORS origins must be HTTPS.
- Localhost origins are rejected in production validation.
- `/health/detailed` now reports `unhealthy` when any dependency check fails.

## Non-Destructive Smoke Test

Run against local or deployed API:

```bash
cd /home/rushi/project/backend
./venv/bin/python test_production_ready.py --api-url http://localhost:8000 --expect-db
```

Optional auth check uses env vars:

```bash
export BACKEND_SMOKE_EMAIL=admin@example.edu
export BACKEND_SMOKE_PASSWORD='your-password'
./venv/bin/python test_production_ready.py --api-url https://your-backend-url --expect-db
```

## Deploy (Railway)

- Entry command: `uvicorn main:app --host 0.0.0.0 --port $PORT` (already in `Procfile`).
- Set all required env vars in Railway.
- Verify after deploy:
1. `GET /health`
2. `GET /health/detailed`
3. Smoke test script against Railway URL.
