from fastapi import FastAPI, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
import os
import logging
from pathlib import Path
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Load environment variables before importing modules that read env at import-time.
# Use an explicit path so the backend always reads backend/.env, not a sibling .env.
BACKEND_ENV_PATH = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=BACKEND_ENV_PATH, override=True)

# Initialize configuration (validates all env vars)
try:
    from config import init_config, get_config
    config = init_config()
except ValueError as e:
    logger.error("Configuration error: %s", e)
    logger.error("Please check your .env file and ensure all required variables are set.")
    raise

from dependencies import get_college_id
from database import supabase
from tools.email_tool import send_email
from monitoring import (
    log_request_middleware,
    get_metrics,
    health_checker,
    get_logger,
    log_action
)
from rate_limiter import RateLimitMiddleware

# Import our modular routers
from excel_reader import router as excel_router
from timetable_engine import router as timetable_router
from leave_manager import router as leave_router
from substitution_engine import router as substitution_router
from chat_handler import router as chat_router
from entity_router import router as entity_router
from feature_flags import router as feature_flags_router

# NEW: Import auth and admin routers
from auth_system import router as auth_router, get_current_user_from_token
from superadmin_router import router as superadmin_router
from auto_handler import router as auto_handler_router

# Initialize FastAPI app
app = FastAPI(title="VYUHA Backend API", version="2.0.0", description="AI-Powered Timetable & Substitution System")

# Add request logging middleware
@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    return await log_request_middleware(request, call_next)

# Allow CORS for frontend (restrict in production)
allowed_origins = [
    origin.strip()
    for origin in os.getenv(
        "ALLOWED_ORIGINS",
        "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173,http://127.0.0.1:3000"
    ).split(",")
    if origin.strip()
]

frontend_url = os.getenv("FRONTEND_URL", "").strip().rstrip("/")
if frontend_url and frontend_url not in allowed_origins:
    allowed_origins.append(frontend_url)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-College-ID"],
)

# Add rate limiting middleware (enabled in production)
env = os.getenv("ENVIRONMENT", "development").lower()
rate_limit_enabled = env == "production"
app.add_middleware(RateLimitMiddleware, enabled=rate_limit_enabled)

# Include ALL Routers
app.include_router(auth_router)              # Auth & User Management
app.include_router(superadmin_router)        # Superadmin Panel
app.include_router(auto_handler_router)       # Auto Handler & Notifications
app.include_router(excel_router)             # Excel Upload
app.include_router(timetable_router)          # Timetable Generation
app.include_router(leave_router)              # Leave Management
app.include_router(substitution_router)       # Substitution Engine
app.include_router(chat_router)               # AI Chat Handler
app.include_router(entity_router)             # Entity Data (Faculty, Rooms, Subjects)
app.include_router(feature_flags_router)      # Feature Flags

@app.get("/")
async def root():
    """Root endpoint with API info."""
    return {
        "name": "VYUHA API",
        "version": "2.0.0",
        "status": "running",
        "docs": "/docs"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint to ensure the API is running."""
    return {"status": "healthy", "service": "VYUHA Backend", "version": "2.0.0"}

@app.get("/health/detailed")
async def health_check_detailed():
    """Detailed health check with all registered checks."""
    return await health_checker.run_checks()

@app.get("/metrics")
async def get_metrics_endpoint():
    """Get current metrics and statistics."""
    return get_metrics().get_stats()

@app.get("/logs")
async def get_recent_logs(lines: int = 100):
    """Get recent log entries (requires admin access)."""
    # This is a simple endpoint - in production, integrate with log aggregation
    return {"message": "Use external log aggregation (e.g., ELK, Datadog) for production"}

@app.post("/approve-timetable")
async def approve_timetable(
    college_id: str = Depends(get_college_id),
    current_user: dict = Depends(get_current_user_from_token)
):
    """Approve the generated timetable and email all faculty their schedules."""
    try:
        if current_user.get("role") not in ["admin", "hod", "superadmin"]:
            return JSONResponse(status_code=403, content={"detail": "Only admin or HOD can approve timetable"})

        if not supabase:
            return JSONResponse(status_code=500, content={"detail": "Database not connected"})

        # Get all faculty with emails
        faculty_res = supabase.table("faculty").select("*").eq("college_id", college_id).execute()
        faculty_map = {f["id"]: f for f in faculty_res.data}

        # Get all timetable slots
        tt_res = supabase.table("timetable_slots").select("*").eq("college_id", college_id).execute()
        slots = tt_res.data

        # Get subject names
        sub_res = supabase.table("subjects").select("*").eq("college_id", college_id).execute()
        sub_map = {s["id"]: s.get("name", "Unknown") for s in sub_res.data}

        # Get room names
        room_res = supabase.table("rooms").select("*").eq("college_id", college_id).execute()
        room_map = {r["id"]: r.get("room_name", r.get("name", "Unknown")) for r in room_res.data}

        # Group by faculty
        faculty_schedules = {}
        for slot in slots:
            fid = slot["faculty_id"]
            if fid not in faculty_schedules:
                faculty_schedules[fid] = []
            faculty_schedules[fid].append(slot)

        import json
        email_cache = {}
        cache_path = os.path.join(os.path.dirname(__file__), "email_cache.json")
        if os.path.exists(cache_path):
            with open(cache_path, "r") as f:
                email_cache = json.load(f)

        sent = 0
        failed = 0
        for fid, schedule in faculty_schedules.items():
            f = faculty_map.get(fid)
            
            # Use real DB email if exists, otherwise fallback to local cache
            f_email = f.get("email") if f and f.get("email") else email_cache.get(f.get("name", ""))
            
            if not f or not f_email:
                continue

            lines = [f"Dear {f['name']},\n\nYour timetable has been officially published. Here is your schedule:\n"]
            for s in sorted(schedule, key=lambda x: (x["day"], x["start_time"])):
                sub_name = sub_map.get(s["subject_id"], "Unknown")
                room_name = room_map.get(s.get("room_id"), "TBD")
                lines.append(f"  {s['day']} | {s['start_time']}-{s['end_time']} | {sub_name} | Room: {room_name}")
            lines.append("\nRegards,\nVYUHA Admin")

            body = "\n".join(lines)
            ok = send_email(f_email, "Your Official Timetable - VYUHA", body)
            if ok:
                sent += 1
            else:
                failed += 1

        return {"message": f"Notifications sent to {sent} faculty.", "sent": sent, "failed": failed}

    except Exception as e:
        return JSONResponse(status_code=500, content={"detail": f"Error approving timetable: {str(e)}"})

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
