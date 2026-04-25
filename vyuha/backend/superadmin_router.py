"""
VYUHA Superadmin Router
Complete college management for superadmin
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import bcrypt
import re
import logging
from database import supabase
from auth_system import get_current_user_from_token

router = APIRouter(prefix="/superadmin", tags=["Superadmin"])
logger = logging.getLogger(__name__)

# ============================================
# SUPERADMIN HELPERS
# ============================================

def require_superadmin(current_user: dict = Depends(get_current_user_from_token)):
    """Ensure user is superadmin."""
    if current_user["role"] != "superadmin":
        raise HTTPException(
            status_code=403,
            detail="Superadmin access required"
        )
    return current_user

def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode(), salt).decode()


def _generate_unique_college_id(code: str) -> str:
    clean = re.sub(r"[^A-Za-z0-9]", "", (code or "").upper())
    base = f"COL{clean[:6]}" if clean else "COLLEGE"
    for i in range(1000):
        suffix = "" if i == 0 else f"{i:03d}"
        candidate = f"{base}{suffix}"[:20]
        existing = supabase.table("colleges").select("id").eq("college_id", candidate).execute()
        if not existing.data:
            return candidate
    raise HTTPException(status_code=500, detail="Unable to generate unique college ID")

# ============================================
# COLLEGE MANAGEMENT
# ============================================

@router.get("/colleges")
async def get_all_colleges(current_user: dict = Depends(require_superadmin)):
    """Get all colleges (superadmin only)."""
    colleges_res = supabase.table("colleges").select("*").order("created_at", desc=True).execute()
    return {"colleges": colleges_res.data}

class CollegeCreate(BaseModel):
    name: str
    code: str
    contact_email: str
    admin_email: str
    admin_name: str
    admin_password: str

@router.post("/colleges")
async def create_college(
    request: CollegeCreate,
    current_user: dict = Depends(require_superadmin)
):
    """Create a new college and first admin user."""
    
    # Generate unique college_id
    college_id = _generate_unique_college_id(request.code)
    
    # Check if admin email exists
    existing_user = supabase.table("users").select("id").eq("email", request.admin_email).execute()
    if existing_user.data:
        raise HTTPException(
            status_code=400,
            detail="Admin email already registered"
        )
    
    # Create college
    college_data = {
        "college_id": college_id,
        "name": request.name,
        "contact_email": request.contact_email,
        "status": "active",
        "approved_at": datetime.utcnow().isoformat()
    }

    try:
        # Try inserting with code column
        college_result = supabase.table("colleges").insert({**college_data, "code": request.code.upper()}).execute()
    except Exception as e:
        # Fallback if code column doesn't exist
        if "column colleges.code does not exist" in str(e):
            college_result = supabase.table("colleges").insert(college_data).execute()
        else:
            raise HTTPException(status_code=500, detail=f"Failed to create college record: {str(e)}")
    
    # Create admin user
    password_hash = hash_password(request.admin_password)
    admin_data = {
        "college_id": college_id,
        "email": request.admin_email,
        "password_hash": password_hash,
        "name": request.admin_name,
        "role": "admin",
        "email_verified": True,
        "status": "active"
    }
    
    try:
        admin_result = supabase.table("users").insert(admin_data).execute()
    except Exception as e:
        # Rollback college if user creation fails
        supabase.table("colleges").delete().eq("college_id", college_id).execute()
        raise HTTPException(status_code=500, detail=f"Failed to create admin user: {str(e)}")
    
    # Create feature flags (ignore if table doesn't exist)
    try:
        supabase.table("feature_flags").insert({"college_id": college_id}).execute()
    except Exception as exc:
        logger.warning("Feature flag bootstrap failed for college %s: %s", college_id, exc)
    
    # Create audit log
    try:
        supabase.table("audit_logs").insert({
            "college_id": college_id,
            "user_id": current_user["id"],
            "action": "create_college",
            "entity_type": "college",
            "new_value": {"name": request.name, "code": request.code}
        }).execute()
    except Exception as exc:
        logger.warning("Audit log creation failed for college %s: %s", college_id, exc)
    
    return {
        "message": f"College '{request.name}' created successfully",
        "college_id": college_id,
        "admin_email": request.admin_email
    }

@router.put("/colleges/{college_id}/approve")
async def approve_college(
    college_id: str,
    current_user: dict = Depends(require_superadmin)
):
    """Approve a pending college."""
    
    college_res = supabase.table("colleges").select("*").eq("college_id", college_id).execute()
    if not college_res.data:
        raise HTTPException(status_code=404, detail="College not found")
    
    college = college_res.data[0]
    
    if college["status"] == "active":
        raise HTTPException(status_code=400, detail="College already active")
    
    supabase.table("colleges").update({
        "status": "active",
        "approved_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat()
    }).eq("college_id", college_id).execute()

    # Activate college users (including requested admin created during onboarding request)
    supabase.table("users").update({
        "status": "active",
        "email_verified": True,
        "updated_at": datetime.utcnow().isoformat()
    }).eq("college_id", college_id).eq("status", "inactive").execute()
    
    # Notify via notification for superadmin's internal tracking
    supabase.table("audit_logs").insert({
        "college_id": college_id,
        "user_id": current_user["id"],
        "action": "approve_college",
        "entity_type": "college",
        "entity_id": college["id"],
        "new_value": {"status": "active"}
    }).execute()
    
    return {"message": f"College {college_id} approved successfully"}

@router.put("/colleges/{college_id}/suspend")
async def suspend_college(
    college_id: str,
    current_user: dict = Depends(require_superadmin)
):
    """Suspend a college."""
    
    supabase.table("colleges").update({
        "status": "suspended",
        "updated_at": datetime.utcnow().isoformat()
    }).eq("college_id", college_id).execute()
    
    # Suspend all users in college
    supabase.table("users").update({
        "status": "suspended"
    }).eq("college_id", college_id).execute()
    
    # Audit log
    supabase.table("audit_logs").insert({
        "college_id": college_id,
        "user_id": current_user["id"],
        "action": "suspend_college",
        "entity_type": "college",
        "new_value": {"status": "suspended"}
    }).execute()
    
    return {"message": f"College {college_id} suspended"}

@router.delete("/colleges/{college_id}")
async def delete_college(
    college_id: str,
    current_user: dict = Depends(require_superadmin)
):
    """Delete a college and all its data."""
    
    # This cascades via ON DELETE CASCADE
    supabase.table("colleges").delete().eq("college_id", college_id).execute()
    
    # Audit log (user_id won't exist after college deletion)
    # So we log without college_id context
    
    return {"message": f"College {college_id} deleted"}

# ============================================
# STATISTICS & OVERVIEW
# ============================================

@router.get("/stats")
async def get_overall_stats(current_user: dict = Depends(require_superadmin)):
    """Get overall platform statistics."""
    
    colleges_res = supabase.table("colleges").select("*").execute()
    users_res = supabase.table("users").select("role").execute()
    
    colleges = colleges_res.data
    users = users_res.data
    
    stats = {
        "total_colleges": len(colleges),
        "active_colleges": len([c for c in colleges if c["status"] == "active"]),
        "pending_colleges": len([c for c in colleges if c["status"] == "pending"]),
        "suspended_colleges": len([c for c in colleges if c["status"] == "suspended"]),
        "total_users": len(users),
        "admins": len([u for u in users if u.get("role") == "admin"]),
        "faculty": len([u for u in users if u.get("role") == "faculty"]),
        "hods": len([u for u in users if u.get("role") == "hod"]),
        "coordinators": len([u for u in users if u.get("role") == "coordinator"])
    }
    
    return stats

@router.get("/colleges/{college_id}/details")
async def get_college_details(
    college_id: str,
    current_user: dict = Depends(require_superadmin)
):
    """Get detailed info about a specific college."""
    
    # College info
    college_res = supabase.table("colleges").select("*").eq("college_id", college_id).execute()
    if not college_res.data:
        raise HTTPException(status_code=404, detail="College not found")
    
    college = college_res.data[0]
    
    # User counts
    users_res = supabase.table("users").select("role").eq("college_id", college_id).execute()
    users = users_res.data
    
    # Pending users
    pending_res = supabase.table("pending_users").select("id").eq("college_id", college_id).eq("status", "pending").execute()
    
    # Faculty count
    faculty_res = supabase.table("faculty").select("id").eq("college_id", college_id).execute()
    
    # Subjects count
    subjects_res = supabase.table("subjects").select("id").eq("college_id", college_id).execute()
    
    # Rooms count
    rooms_res = supabase.table("rooms").select("id").eq("college_id", college_id).execute()
    
    return {
        "college": college,
        "users": {
            "total": len(users),
            "admins": len([u for u in users if u.get("role") == "admin"]),
            "faculty": len([u for u in users if u.get("role") == "faculty"]),
            "hods": len([u for u in users if u.get("role") == "hod"]),
            "coordinators": len([u for u in users if u.get("role") == "coordinator"])
        },
        "pending_registrations": len(pending_res.data),
        "faculty_members": len(faculty_res.data),
        "subjects": len(subjects_res.data),
        "rooms": len(rooms_res.data)
    }

# ============================================
# AUDIT LOGS
# ============================================

@router.get("/audit-logs")
async def get_all_audit_logs(
    college_id: Optional[str] = None,
    limit: int = 100,
    current_user: dict = Depends(require_superadmin)
):
    """Get audit logs across all colleges (superadmin only)."""
    
    query = supabase.table("audit_logs").select("*").order("created_at", desc=True).limit(limit)
    
    if college_id:
        query = query.eq("college_id", college_id)
    
    logs_res = query.execute()
    return {"audit_logs": logs_res.data}

# ============================================
# SYSTEM CONFIGURATION
# ============================================

@router.get("/system-config")
async def get_system_config(current_user: dict = Depends(require_superadmin)):
    """Get system configuration."""
    
    # Return system-wide settings
    return {
        "version": "2.0.0",
        "max_colleges": 1000,
        "features": {
            "multi_tenant": True,
            "role_based_access": True,
            "auto_substitution": True,
            "ai_chat": True,
            "email_notifications": True
        },
        "roles": ["superadmin", "admin", "hod", "faculty", "coordinator"]
    }
