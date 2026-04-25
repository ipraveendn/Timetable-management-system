"""
VYUHA Dependencies
Helper functions for FastAPI routes
"""

import jwt
from fastapi import Request, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import List, Optional, Dict, Any
from functools import wraps
from config import get_config
from database import supabase

security = HTTPBearer()
config = get_config()

# ============================================
# JWT HELPERS
# ============================================

def decode_jwt_token(token: str) -> Dict[str, Any]:
    """Decode and validate a JWT token."""
    try:
        payload = jwt.decode(
            token, 
            config.jwt.secret, 
            algorithms=[config.jwt.algorithm]
        )
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

async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Dict[str, Any]:
    """
    Dependency to get current user from JWT token.
    Validates token and returns user info from payload or DB.
    """
    token = credentials.credentials
    payload = decode_jwt_token(token)
    
    # Check tenant isolation
    header_college_id = request.headers.get("X-College-ID") or request.headers.get("x-college-id")
    token_college_id = payload.get("college_id")
    
    if header_college_id and token_college_id:
        if str(header_college_id).strip() != str(token_college_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Tenant mismatch: Header college_id does not match token"
            )

    # Return payload as minimal user info (can fetch from DB if needed elsewhere)
    # For performance, we trust the JWT payload after signature verification
    return {
        "id": payload.get("user_id"),
        "email": payload.get("email"),
        "college_id": token_college_id,
        "role": payload.get("role")
    }

# ============================================
# COLLEGE ID HELPERS
# ============================================

async def get_college_id(request: Request) -> str:
    """Get college_id from request headers with validation."""
    college_id = request.headers.get("X-College-ID") or request.headers.get("x-college-id")
    
    if not college_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="X-College-ID header is required"
        )
    
    normalized = str(college_id).strip()
    if not (3 <= len(normalized) <= 20):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid X-College-ID format"
        )
    return normalized

# ============================================
# ROLE-BASED ACCESS CONTROL
# ============================================

def require_roles(allowed_roles: List[str]):
    """
    Decorator to require specific roles for an endpoint.
    Usage: @router.get(...) @require_roles(["admin", "principal"])
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Get current_user from kwargs (provided by Depends)
            current_user = kwargs.get("current_user")
            
            if not current_user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )
            
            user_role = current_user.get("role", "")
            
            # Superadmin has access to everything
            if user_role == "superadmin":
                return await func(*args, **kwargs)
            
            if user_role not in allowed_roles:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Access denied. Required roles: {', '.join(allowed_roles)}"
                )
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


def require_admin(current_user: dict = None):
    """Require admin or higher role."""
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    role = current_user.get("role", "")
    
    if role not in ["admin", "superadmin"]:
        raise HTTPException(
            status_code=403,
            detail="Admin access required"
        )
    
    return current_user


def require_hod_or_above(current_user: dict = None):
    """Require hod or higher role."""
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    role = current_user.get("role", "")
    
    if role not in ["admin", "principal", "superadmin"]:
        raise HTTPException(
            status_code=403,
            detail="Principal or Admin access required"
        )
    
    return current_user


# ============================================
# VALIDATION HELPERS
# ============================================

def validate_college_id(college_id: str) -> bool:
    """Validate college_id format."""
    if not college_id:
        return False
    if len(college_id) < 3 or len(college_id) > 20:
        return False
    return True


def validate_email(email: str) -> bool:
    """Basic email validation."""
    if not email or "@" not in email:
        return False
    parts = email.split("@")
    if len(parts) != 2:
        return False
    if not parts[0] or not parts[1]:
        return False
    if "." not in parts[1]:
        return False
    return True


def validate_date_format(date_str: str) -> bool:
    """Validate date string format (YYYY-MM-DD)."""
    from datetime import datetime
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        return True
    except:
        return False


# ============================================
# PAGINATION HELPERS
# ============================================

def get_pagination_params(skip: int = 0, limit: int = 100, max_limit: int = 1000):
    """Get pagination parameters with defaults."""
    skip = max(0, skip)
    limit = min(max(1, limit), max_limit)
    return skip, limit


# ============================================
# RESPONSE HELPERS
# ============================================

def success_response(data=None, message="Success", **kwargs):
    """Create a standardized success response."""
    response = {"success": True, "message": message}
    if data is not None:
        response["data"] = data
    response.update(kwargs)
    return response


def error_response(message="Error", code=400, **kwargs):
    """Create a standardized error response."""
    response = {"success": False, "error": message, "code": code}
    response.update(kwargs)
    return response
