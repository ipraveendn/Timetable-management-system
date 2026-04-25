# VYUHA Production Deployment Checklist

## Pre-Deployment Requirements

### 1. Environment Variables
- [ ] Copy `.env.example` to `.env`
- [ ] Set `ENVIRONMENT=production`
- [ ] Set `DEBUG=false`
- [ ] Set `LOG_LEVEL=INFO` or `ERROR`
- [ ] Configure production domain in `ALLOWED_ORIGINS`
- [ ] Set secure JWT_SECRET (64+ characters)
- [ ] Configure SMTP credentials for email notifications
- [ ] Set `RATE_LIMIT_REQUESTS=100` (or lower for stricter limits)

### 2. Database (Supabase)
- [ ] Run `schema.sql` on production database
- [ ] Enable RLS on all tables (already in schema.sql)
- [ ] Verify RLS policies are working
- [ ] Create initial superadmin user manually
- [ ] Test multi-tenant isolation between colleges

### 3. Backend Security
- [ ] Rate limiting enabled in production (middleware added)
- [ ] CORS restricted to production domains only
- [ ] JWT expiry set to reasonable value (24 hours recommended)
- [ ] No debug mode in production

### 4. Frontend Security
- [ ] Set `VITE_API_URL` to production backend URL
- [ ] Lint passes: `npm run lint`
- [ ] Build optimized: `npm run build`
- [ ] Test on Vercel before production deployment

### 5. CI Quality Gates
- [ ] GitHub Actions workflow `.github/workflows/ci.yml` is active
- [ ] Frontend lint + build must pass on PR
- [ ] Backend syntax checks must pass on PR
- [ ] Optional external smoke test configured with `BACKEND_SMOKE_URL`

## Deployment Steps

### Backend (Railway/Render/AWS)
```bash
cd backend
pip install -r requirements.txt
# Set all environment variables in deployment platform
python main.py
```

### Frontend (Vercel/Netlify)
```bash
cd frontend
npm install
npm run build
# Deploy to hosting platform
```

## Post-Deployment Verification

### Health Checks
- [ ] `/health` endpoint returns 200
- [ ] `/health/detailed` shows all checks passing
- [ ] Smoke test passes:
  - `python backend/test_production_ready.py --api-url https://<backend-url> --expect-db`

### Security Checks
- [ ] Rate limiting working (test with multiple rapid requests)
- [ ] CORS blocking unauthorized origins
- [ ] RLS preventing cross-tenant data access

### Functional Tests
- [ ] User can register/login as college admin
- [ ] Superadmin can approve colleges
- [ ] Excel upload works
- [ ] Timetable generation completes
- [ ] Leave requests and substitutions work
- [ ] Chat assistant responds

## Monitoring
- [ ] Set up logging aggregation (Datadog, Sentry, etc.)
- [ ] Configure alerts for errors
- [ ] Monitor rate limit hits
- [ ] Track response times

## Rollback Plan
- [ ] Keep previous deployment version
- [ ] Database backup before schema changes
- [ ] Easy way to revert environment variables
