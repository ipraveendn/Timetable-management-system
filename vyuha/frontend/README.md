# VYUHA Frontend

## Local Setup

```bash
cd /home/rushi/project/frontend
npm ci
npm run dev
```

Frontend default URL: `http://localhost:5173`

## Environment

Create `.env` from `.env.example`.

Key variable:

```env
VITE_API_URL=https://your-backend-url
```

Notes:
- In development, requests use `/api` proxy from `vite.config.js`.
- In production build, `VITE_API_URL` is used when set.

## Quality Checks

```bash
npm run lint
npm run build
```

## Deploy (Vercel)

- Build command: `npm run build`
- Output directory: `dist`
- Configure `VITE_API_URL` in Vercel project settings to your Railway backend URL.
- Keep backend CORS `ALLOWED_ORIGINS` aligned with your Vercel domain.
