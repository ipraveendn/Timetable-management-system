"""
VYUHA Authentication System
Complete JWT-based auth with role support
"""

from fastapi import APIRouter, HTTPException, Depends, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, validator
from typing import Optional, List
from datetime import datetime, timedelta
import jwt
import bcrypt
import os
import re
import hashlib
import secrets
from urllib.parse import urlencode
from database import supabase
from dependencies import get_current_user, get_college_id, require_roles
from monitoring import timed, log_action, get_logger
from config import get_config
from tools.email_tool import send_email

router = APIRouter(prefix="/auth", tags=["Authentication"])
logger = get_logger()
security = HTTPBearer()

# Load configuration
config = get_config()
JWT_SECRET = config.jwt.secret
JWT_ALGORITHM = config.jwt.algorithm
JWT_EXPIRY_HOURS = config.jwt.expiry_hours


def _require_jwt_secret() -> str:
    if not JWT_SECRET:
        raise ValueError("JWT_SECRET not configured. Check your environment variables.")
    return JWT_SECRET


def _translate_db_error(exc: Exception) -> HTTPException:
    """Convert low-level Supabase/PostgREST errors into actionable API errors."""
    msg = str(exc)
    if "PGRST205" in msg and "Could not find the table" in msg:
        return HTTPException(
            status_code=503,
            detail="Database schema is not initialized. Apply backend/schema.sql in Supabase and reload API."
        )
    if "violates unique constraint" in msg:
        return HTTPException(status_code=400, detail="Record already exists")
    return HTTPException(status_code=500, detail=f"Database error: {msg}")

# Pydantic Models
class RegisterRequest(BaseModel):
    email: str
    password: str
    name: str
    college_id: str
    role: str = "faculty"
    department: Optional[str] = None
    employee_id: Optional[str] = None
    phone: Optional[str] = None

    @validator('email')
    def validate_email(cls, v):
        if not v or '@' not in v:
            raise ValueError('Invalid email format')
        return v.lower().strip()

    @validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        if not any(c in '!@#$%^&*()_+-=[]{}|;:,.<>?/' for c in v):
            raise ValueError('Password must contain at least one special character')
        return v

    @validator('name')
    def validate_name(cls, v):
        if not v or len(v.strip()) < 2:
            raise ValueError('Name must be at least 2 characters long')
        return v.strip()

class LoginRequest(BaseModel):
    email: str
    password: str

    @validator('email')
    def validate_email(cls, v):
        if not v or '@' not in v:
            raise ValueError('Invalid email format')
        return v.lower().strip()

class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str


class ForgotPasswordRequest(BaseModel):
    email: str

    @validator('email')
    def validate_email(cls, v):
        if not v or '@' not in v:
            raise ValueError('Invalid email format')
        return v.lower().strip()


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

    @validator('new_password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        if not any(c in '!@#$%^&*()_+-=[]{}|;:,.<>?/' for c in v):
            raise ValueError('Password must contain at least one special character')
        return v

class UserProfile(BaseModel):
    id: int
    college_id: str
    email: str
    name: str
    role: str
    department: Optional[str]
    employee_id: Optional[str]
    phone: Optional[str]
    status: str
    created_at: datetime


class CollegeRequest(BaseModel):
    name: str
    code: str
    contact_email: str
    admin_name: str
    admin_email: str
    admin_password: str


class InviteUserRequest(BaseModel):
    email: str
    name: str
    role: str = "faculty"
    department: Optional[str] = None
    employee_id: Optional[str] = None
    phone: Optional[str] = None
    temporary_password: str

def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    # Use 12 rounds for better security/consistency
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    """Verify a password against its hash."""
    try:
        if not password or not hashed:
            return False
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    except Exception as e:
        logger.warning("Password verification error: %s", str(e))
        return False


def hash_reset_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def serialize_timestamp(value) -> str:
    if not value:
        return ""
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def get_frontend_base_url() -> str:
    return os.getenv("FRONTEND_URL", "http://localhost:5173").strip().rstrip("/")


def build_reset_password_link(token: str) -> str:
    params = urlencode({"token": token})
    return f"{get_frontend_base_url()}/reset-password?{params}"

def create_jwt_token(user_data: dict) -> str:
    """Create a JWT token for authenticated user."""
    jwt_secret = _require_jwt_secret()
    password_changed_at = serialize_timestamp(user_data.get("password_changed_at"))
    payload = {
        "user_id": user_data["id"],
        "email": user_data["email"],
        "college_id": user_data["college_id"],
        "role": user_data["role"],
        "password_changed_at": password_changed_at,
        "exp": datetime.utcnow() + timedelta(hours=JWT_EXPIRY_HOURS),
        "iat": datetime.utcnow()
    }
    return jwt.encode(payload, jwt_secret, algorithm=JWT_ALGORITHM, headers={"alg": JWT_ALGORITHM})

def decode_jwt_token(token: str) -> dict:
    """Decode and validate a JWT token."""
    jwt_secret = _require_jwt_secret()
    try:
        payload = jwt.decode(token, jwt_secret, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired"
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )


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

async def get_current_user_from_token(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> dict:
    """Dependency to get current user from JWT token."""
    token = credentials.credentials
    payload = decode_jwt_token(token)
    
    # Fetch full user data from database
    user_res = supabase.table("users").select("*").eq("id", payload["user_id"]).execute()
    
    if not user_res.data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    user = user_res.data[0]

    token_password_changed_at = payload.get("password_changed_at")
    user_password_changed_at = serialize_timestamp(user.get("password_changed_at"))
    if user_password_changed_at and token_password_changed_at != user_password_changed_at:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired. Please log in again."
        )

    if user["status"] == "suspended":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account suspended"
        )

    # Bind tenant header to token user for non-superadmin users.
    header_college_id = request.headers.get("X-College-ID") or request.headers.get("x-college-id")
    if header_college_id and user.get("role") != "superadmin":
        normalized = str(header_college_id).strip()
        if normalized != user.get("college_id"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Tenant mismatch between token and X-College-ID"
            )
    
    return user

# ============================================
# AUTH ENDPOINTS
# ============================================

@router.post("/register")
@timed
async def register_user(request: RegisterRequest):
    """Register a new user (goes to pending_users for approval)."""
    logger.info(f"User registration attempt: {request.email}")
    
    # Validate college exists
    college_res = supabase.table("colleges").select("*").eq("college_id", request.college_id).execute()
    if not college_res.data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid college ID"
        )
    
    college = college_res.data[0]
    if college["status"] != "active":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="College is not active. Please wait for approval."
        )
    
    # Check if email already exists
    existing_user = supabase.table("users").select("id").eq("email", request.email).execute()
    if existing_user.data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Check pending users
    existing_pending = supabase.table("pending_users").select("id").eq("email", request.email).execute()
    if existing_pending.data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already has a pending registration"
        )
    
    # Hash password
    password_hash = hash_password(request.password)
    
    # Insert into pending_users
    pending_data = {
        "college_id": request.college_id,
        "email": request.email,
        "password_hash": password_hash,
        "name": request.name,
        "requested_role": request.role,
        "department": request.department,
        "employee_id": request.employee_id,
        "phone": request.phone,
        "status": "pending"
    }
    
    result = supabase.table("pending_users").insert(pending_data).execute()
    
    # Create notification for college admin
    admins = supabase.table("users").select("id").eq("college_id", request.college_id).eq("role", "admin").execute()
    for admin in admins.data:
        supabase.table("notifications").insert({
            "college_id": request.college_id,
            "user_id": admin["id"],
            "type": "user_registration",
            "title": "New User Registration",
            "message": f"New {request.role} registration: {request.name} ({request.email})",
            "data": {"pending_user_id": result.data[0]["id"] if result.data else None}
        }).execute()
    
    return {
        "message": "Registration submitted successfully. Please wait for admin approval.",
        "status": "pending",
        "email": request.email
    }


@router.post("/request-college")
@timed
async def request_college_onboarding(request: CollegeRequest):
    """Public endpoint for new college onboarding request."""
    logger.info(f"College request attempt: {request.name} ({request.code})")

    if len(request.admin_password) < 8:
        raise HTTPException(status_code=400, detail="Admin password must be at least 8 characters")

    normalized_code = request.code.strip().upper()

    try:
        existing_admin = supabase.table("users").select("id").eq("email", request.admin_email).execute()
        if existing_admin.data:
            raise HTTPException(status_code=400, detail="Admin email already registered")
    except HTTPException:
        raise
    except Exception as exc:
        raise _translate_db_error(exc)

    college_id = _generate_unique_college_id(normalized_code)

    college_payload = {
        "college_id": college_id,
        "name": request.name.strip(),
        "contact_email": request.contact_email,
        "status": "pending"
    }
    try:
        # Prefer storing code when column exists.
        college_insert = supabase.table("colleges").insert({**college_payload, "code": normalized_code}).execute()
    except Exception as exc:
        if "column colleges.code does not exist" in str(exc):
            try:
                college_insert = supabase.table("colleges").insert(college_payload).execute()
            except Exception as inner_exc:
                raise _translate_db_error(inner_exc)
        else:
            raise _translate_db_error(exc)

    if not college_insert.data:
        raise HTTPException(status_code=500, detail="Failed to create college request")

    try:
        supabase.table("users").insert({
            "college_id": college_id,
            "email": request.admin_email,
            "password_hash": hash_password(request.admin_password),
            "name": request.admin_name.strip(),
            "role": "admin",
            "email_verified": False,
            "status": "inactive"
        }).execute()
    except Exception as exc:
        # Roll back newly created college so onboarding stays consistent.
        try:
            supabase.table("colleges").delete().eq("college_id", college_id).execute()
        except Exception as rollback_exc:
            logger.warning("Rollback failed for college %s: %s", college_id, rollback_exc)
        raise _translate_db_error(exc)

    # Notify all superadmins
    try:
        superadmins = supabase.table("users").select("id").eq("role", "superadmin").execute()
        for sa in superadmins.data:
            supabase.table("notifications").insert({
                "college_id": college_id,
                "user_id": sa["id"],
                "type": "college_request",
                "title": "New College Onboarding Request",
                "message": f"{request.name} requested onboarding. Approve to activate admin login.",
                "data": {"college_id": college_id, "code": normalized_code}
            }).execute()
    except Exception:
        # Notification failure should not fail onboarding request creation.
        logger.warning("Failed to create onboarding notifications for college %s", college_id)

    return {
        "message": "College onboarding request submitted. Superadmin approval is required.",
        "college_id": college_id,
        "status": "pending"
    }

@router.post("/login")
@timed
async def login_user(request: LoginRequest):
    """Login with email and password."""
    email_normalized = request.email.lower().strip()
    logger.info(f"Login attempt for: {email_normalized}")
    
    # Find user (case-insensitive)
    user_res = supabase.table("users").select("*").ilike("email", email_normalized).execute()
    
    if not user_res.data:
        logger.warning(f"Login failed: User not found for {email_normalized}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    user = user_res.data[0]
    
    # Verify password
    if not verify_password(request.password, user["password_hash"]):
        logger.warning(f"Login failed: Password mismatch for {email_normalized}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    # Check status
    if user["status"] == "suspended":
        logger.warning(f"Login blocked: Account suspended for {email_normalized}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account suspended. Contact administrator."
        )
    
    if user["status"] == "inactive":
        logger.warning(f"Login blocked: Account inactive for {email_normalized}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account inactive. Contact administrator."
        )

    # Superadmin bypasses college status check
    if user.get("role") != "superadmin":
        college_res = supabase.table("colleges").select("status").eq("college_id", user["college_id"]).execute()
        if not college_res.data or college_res.data[0].get("status") != "active":
            logger.warning(f"Login blocked: College {user['college_id']} not active for {email_normalized}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="College is not active yet. Wait for superadmin approval."
            )
    
    # Update last login
    try:
        supabase.table("users").update({"last_login": datetime.utcnow().isoformat()}).eq("id", user["id"]).execute()
    except:
        pass # Don't fail login just because we couldn't update last_login
    
    # Create JWT token
    token = create_jwt_token(user)
    logger.info(f"Login successful: {user['email']} (role: {user['role']})")
    return {
        "token": token,
        "user": {
            "id": user["id"],
            "email": user["email"],
            "name": user["name"],
            "role": user["role"],
            "college_id": user["college_id"],
            "department": user.get("department"),
            "employee_id": user.get("employee_id")
        }
    }


@router.post("/forgot-password")
@timed
async def forgot_password(request: ForgotPasswordRequest):
    """Send a password reset link to the user's email."""
    email_normalized = request.email.lower().strip()
    user_res = supabase.table("users").select("id, email, name, password_changed_at").eq("email", email_normalized).execute()

    if not user_res.data:
        return {"message": "If the email exists, a reset link will be sent."}

    user = user_res.data[0]
    raw_token = secrets.token_urlsafe(32)
    token_hash = hash_reset_token(raw_token)
    expires_at = (datetime.utcnow() + timedelta(hours=1)).isoformat()

    try:
        supabase.table("password_reset_tokens").insert({
            "email": email_normalized,
            "user_id": user["id"],
            "token_hash": token_hash,
            "expires_at": expires_at
        }).execute()
    except Exception as exc:
        raise _translate_db_error(exc)

    reset_link = build_reset_password_link(raw_token)
    subject = "Reset your VYUHA password"
    message = (
        f"Hello {user.get('name', 'there')},\n\n"
        f"We received a request to reset your VYUHA password.\n"
        f"Use the link below to choose a new password:\n\n"
        f"{reset_link}\n\n"
        f"This link expires in 1 hour. If you did not request a reset, you can ignore this email."
    )

    email_sent = send_email(email_normalized, subject, message)
    
    if not email_sent:
        logger.error(f"Failed to send password reset email to {email_normalized}")
        # If in production, we should tell the user there was a delivery issue
        if os.getenv("ENVIRONMENT", "development").lower() == "production":
             raise HTTPException(
                status_code=500, 
                detail="Email delivery failed. Please check your SMTP settings or contact support."
            )
        else:
            return {
                "message": "Email delivery failed (Development Mode). Here is your link:",
                "reset_link": reset_link
            }

    return {"message": "A reset link has been sent to your email address."}


@router.post("/reset-password")
@timed
async def reset_password(request: ResetPasswordRequest):
    """Reset a password using a one-time token."""
    token_hash = hash_reset_token(request.token)
    now_iso = datetime.utcnow().isoformat()

    token_res = supabase.table("password_reset_tokens").select("*").eq("token_hash", token_hash).is_("used_at", None).gte("expires_at", now_iso).execute()
    if not token_res.data:
        raise HTTPException(status_code=400, detail="Reset token is invalid or expired")

    token_row = token_res.data[0]
    user_res = supabase.table("users").select("*").eq("id", token_row["user_id"]).execute()
    if not user_res.data:
        raise HTTPException(status_code=404, detail="User not found")

    new_hash = hash_password(request.new_password)
    changed_at = datetime.utcnow().isoformat()

    try:
        supabase.table("users").update({
            "password_hash": new_hash,
            "password_changed_at": changed_at,
            "updated_at": changed_at
        }).eq("id", token_row["user_id"]).execute()

        supabase.table("password_reset_tokens").update({
            "used_at": changed_at
        }).eq("id", token_row["id"]).execute()
    except Exception as exc:
        raise _translate_db_error(exc)

    return {"message": "Password reset successfully. Please log in with your new password."}

@router.get("/me")
async def get_profile(current_user: dict = Depends(get_current_user_from_token)):
    """Get current user profile."""
    return {
        "id": current_user["id"],
        "college_id": current_user["college_id"],
        "email": current_user["email"],
        "name": current_user["name"],
        "role": current_user["role"],
        "department": current_user.get("department"),
        "employee_id": current_user.get("employee_id"),
        "phone": current_user.get("phone"),
        "status": current_user["status"],
        "avatar_url": current_user.get("avatar_url"),
        "last_login": current_user.get("last_login"),
        "created_at": current_user["created_at"]
    }

@router.put("/password")
async def change_password(
    request: ChangePasswordRequest,
    current_user: dict = Depends(get_current_user_from_token)
):
    """Change user password."""
    
    # Verify old password
    if not verify_password(request.old_password, current_user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
    
    # Hash new password
    new_hash = hash_password(request.new_password)
    
    # Update password
    changed_at = datetime.utcnow().isoformat()
    supabase.table("users").update({
        "password_hash": new_hash,
        "password_changed_at": changed_at,
        "updated_at": changed_at
    }).eq("id", current_user["id"]).execute()
    
    return {"message": "Password changed successfully"}

@router.get("/users")
async def get_all_users(
    college_id: str = Depends(get_college_id),
    current_user: dict = Depends(get_current_user_from_token)
):
    """Get all users in college (admin/hod only)."""
    
    # Require admin or hod role
    if current_user["role"] not in ["admin", "principal", "superadmin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin or Principal can view all users"
        )
    
    users_res = supabase.table("users").select("*").eq("college_id", college_id).execute()
    
    # Remove password hashes from response
    users = []
    for u in users_res.data:
        users.append({
            "id": u["id"],
            "college_id": u["college_id"],
            "email": u["email"],
            "name": u["name"],
            "role": u["role"],
            "department": u.get("department"),
            "employee_id": u.get("employee_id"),
            "phone": u.get("phone"),
            "status": u["status"],
            "last_login": u.get("last_login"),
            "created_at": u["created_at"]
        })
    
    return {"users": users}

@router.get("/pending-users")
async def get_pending_users(
    college_id: str = Depends(get_college_id),
    current_user: dict = Depends(get_current_user_from_token)
):
    """Get pending user registrations (admin only)."""
    
    if current_user["role"] not in ["admin", "superadmin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin can view pending users"
        )
    
    pending_res = supabase.table("pending_users").select("*").eq("college_id", college_id).eq("status", "pending").execute()
    
    return {"pending_users": pending_res.data}

@router.post("/approve-user/{pending_id}")
@timed
async def approve_user(
    pending_id: int,
    current_user: dict = Depends(get_current_user_from_token)
):
    """Approve a pending user registration."""
    logger.info(f"User approval attempt: pending_id={pending_id} by user={current_user.get('email')}")
    
    if current_user["role"] not in ["admin", "superadmin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin can approve users"
        )
    
    # Get pending user
    pending_res = supabase.table("pending_users").select("*").eq("id", pending_id).execute()
    if not pending_res.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pending user not found"
        )
    
    pending = pending_res.data[0]
    
    if pending["status"] != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not pending"
        )
    
    # Create actual user
    new_user = {
        "college_id": pending["college_id"],
        "email": pending["email"],
        "password_hash": pending["password_hash"],
        "name": pending["name"],
        "role": pending["requested_role"],
        "department": pending.get("department"),
        "employee_id": pending.get("employee_id"),
        "phone": pending.get("phone"),
        "email_verified": True,
        "status": "active"
    }
    
    user_result = supabase.table("users").insert(new_user).execute()
    
    # Update pending status
    supabase.table("pending_users").update({
        "status": "approved",
        "approved_by": current_user["id"],
        "reviewed_at": datetime.utcnow().isoformat()
    }).eq("id", pending_id).execute()
    
    # Create notification for user
    supabase.table("notifications").insert({
        "college_id": pending["college_id"],
        "user_id": user_result.data[0]["id"] if user_result.data else None,
        "type": "account_approved",
        "title": "Account Approved!",
        "message": f"Your account has been approved. You can now login as {pending['requested_role']}.",
        "data": {"role": pending["requested_role"]}
    }).execute()
    
    # Create audit log
    supabase.table("audit_logs").insert({
        "college_id": pending["college_id"],
        "user_id": current_user["id"],
        "action": "approve_user",
        "entity_type": "user",
        "entity_id": user_result.data[0]["id"] if user_result.data else None,
        "new_value": {"approved_email": pending["email"], "role": pending["requested_role"]}
    }).execute()
    
    return {
        "message": "User approved successfully",
        "user_id": user_result.data[0]["id"] if user_result.data else None
    }

@router.post("/reject-user/{pending_id}")
async def reject_user(
    pending_id: int,
    reason: str = "",
    current_user: dict = Depends(get_current_user_from_token)
):
    """Reject a pending user registration."""
    
    if current_user["role"] not in ["admin", "superadmin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin can reject users"
        )
    
    # Get pending user
    pending_res = supabase.table("pending_users").select("*").eq("id", pending_id).execute()
    if not pending_res.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pending user not found"
        )
    
    pending = pending_res.data[0]
    
    if pending["status"] != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not pending"
        )
    
    # Update pending status
    supabase.table("pending_users").update({
        "status": "rejected",
        "rejected_by": current_user["id"],
        "rejection_reason": reason,
        "reviewed_at": datetime.utcnow().isoformat()
    }).eq("id", pending_id).execute()
    
    # Create audit log
    supabase.table("audit_logs").insert({
        "college_id": pending["college_id"],
        "user_id": current_user["id"],
        "action": "reject_user",
        "entity_type": "pending_user",
        "entity_id": pending_id,
        "new_value": {"email": pending["email"], "reason": reason}
    }).execute()
    
    return {"message": "User rejected"}

@router.put("/users/{user_id}/role")
async def change_user_role(
    user_id: int,
    new_role: str,
    current_user: dict = Depends(get_current_user_from_token)
):
    """Change a user's role (admin only)."""
    
    if current_user["role"] not in ["admin", "superadmin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin can change roles"
        )
    
    # Validate role
    valid_roles = ["admin", "principal", "faculty"]
    if new_role not in valid_roles:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role. Must be one of: {', '.join(valid_roles)}"
        )
    
    # Get target user
    user_res = supabase.table("users").select("*").eq("id", user_id).execute()
    if not user_res.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    target_user = user_res.data[0]
    
    # Prevent changing superadmin
    if target_user["role"] == "superadmin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot change superadmin role"
        )
    
    # Superadmin can assign any role, admin can only assign non-admin roles
    if current_user["role"] == "admin" and new_role == "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only superadmin can promote to admin"
        )
    
    old_role = target_user["role"]
    
    # Update role
    supabase.table("users").update({
        "role": new_role,
        "updated_at": datetime.utcnow().isoformat()
    }).eq("id", user_id).execute()
    
    # Create audit log
    supabase.table("audit_logs").insert({
        "college_id": target_user["college_id"],
        "user_id": current_user["id"],
        "action": "change_role",
        "entity_type": "user",
        "entity_id": user_id,
        "old_value": {"role": old_role},
        "new_value": {"role": new_role}
    }).execute()
    
    # Notify user
    supabase.table("notifications").insert({
        "college_id": target_user["college_id"],
        "user_id": user_id,
        "type": "role_change",
        "title": "Role Changed",
        "message": f"Your role has been changed from {old_role} to {new_role}.",
        "data": {"old_role": old_role, "new_role": new_role}
    }).execute()
    
    return {"message": f"Role changed from {old_role} to {new_role}"}

@router.put("/users/{user_id}/status")
async def change_user_status(
    user_id: int,
    new_status: str,
    current_user: dict = Depends(get_current_user_from_token)
):
    """Change a user's status (admin only)."""
    
    if current_user["role"] not in ["admin", "superadmin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin can change user status"
        )
    
    # Validate status
    valid_statuses = ["active", "inactive", "suspended"]
    if new_status not in valid_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
        )
    
    # Get target user
    user_res = supabase.table("users").select("*").eq("id", user_id).execute()
    if not user_res.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    target_user = user_res.data[0]
    
    # Prevent changing superadmin
    if target_user["role"] == "superadmin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot change superadmin status"
        )
    
    # Update status
    supabase.table("users").update({
        "status": new_status,
        "updated_at": datetime.utcnow().isoformat()
    }).eq("id", user_id).execute()
    
    # Create audit log
    supabase.table("audit_logs").insert({
        "college_id": target_user["college_id"],
        "user_id": current_user["id"],
        "action": "change_status",
        "entity_type": "user",
        "entity_id": user_id,
        "new_value": {"status": new_status}
    }).execute()
    
    return {"message": f"User status changed to {new_status}"}


@router.post("/invite-user")
async def invite_user(
    request: InviteUserRequest,
    college_id: str = Depends(get_college_id),
    current_user: dict = Depends(get_current_user_from_token)
):
    """Admin/Principal invite flow to directly create teacher/staff users."""
    if current_user["role"] not in ["admin", "principal", "superadmin"]:
        raise HTTPException(status_code=403, detail="Only admin/Principal can invite users")

    valid_roles = ["faculty", "admin", "principal", "admin"]
    if request.role not in valid_roles:
        raise HTTPException(status_code=400, detail="Invalid role for invitation")

    existing = supabase.table("users").select("id").eq("email", request.email).execute()
    if existing.data:
        raise HTTPException(status_code=400, detail="Email already registered")

    user_insert = supabase.table("users").insert({
        "college_id": college_id,
        "email": request.email,
        "password_hash": hash_password(request.temporary_password),
        "name": request.name,
        "role": request.role,
        "department": request.department,
        "employee_id": request.employee_id,
        "phone": request.phone,
        "email_verified": True,
        "status": "active"
    }).execute()

    if not user_insert.data:
        raise HTTPException(status_code=500, detail="Failed to create invited user")

    new_user = user_insert.data[0]

    # Send invitation email
    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173")
    subject = "Invitation to join VYUHA"
    message = (
        f"Hello {request.name},\n\n"
        f"You have been invited to join VYUHA as a {request.role}.\n\n"
        f"You can log in at {frontend_url} using the following credentials:\n"
        f"Email: {request.email}\n"
        f"Temporary Password: {request.temporary_password}\n\n"
        f"Please log in and change your password as soon as possible."
    )
    send_email(request.email, subject, message)

    supabase.table("audit_logs").insert({
        "college_id": college_id,
        "user_id": current_user["id"],
        "action": "invite_user",
        "entity_type": "user",
        "entity_id": new_user["id"],
        "new_value": {"email": request.email, "role": request.role}
    }).execute()

    return {"message": "User invited successfully", "user_id": new_user["id"]}
