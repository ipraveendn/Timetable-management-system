"""
VYUHA Rate Limiter Middleware
Production-ready rate limiting using in-memory storage
"""

import time
from collections import defaultdict
from typing import Dict, Tuple
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
import hashlib


class RateLimiter:
    """
    Token bucket rate limiter with configurable limits
    """
    
    def __init__(self, requests_per_minute: int = 100, burst_limit: int = 150):
        self.requests_per_minute = requests_per_minute
        self.burst_limit = burst_limit
        self.buckets: Dict[str, Dict] = defaultdict(self._create_bucket)
    
    def _create_bucket(self):
        return {
            "tokens": self.burst_limit,
            "last_update": time.time()
        }
    
    def _get_client_id(self, request: Request) -> str:
        """Get unique identifier for client (IP + optional API key)"""
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            client_ip = forwarded.split(",")[0].strip()
        else:
            client_ip = request.client.host if request.client else "unknown"
        
        auth_header = request.headers.get("Authorization")
        if auth_header:
            api_key = hashlib.md5(auth_header[:50].encode()).hexdigest()[:8]
            return f"{client_ip}:{api_key}"
        
        return client_ip
    
    def _refill_tokens(self, bucket: Dict) -> None:
        """Refill tokens based on elapsed time"""
        now = time.time()
        elapsed = now - bucket["last_update"]
        
        tokens_to_add = elapsed * (self.requests_per_minute / 60.0)
        bucket["tokens"] = min(self.burst_limit, bucket["tokens"] + tokens_to_add)
        bucket["last_update"] = now
    
    def check_rate_limit(self, request: Request) -> Tuple[bool, Dict]:
        """
        Check if request is within rate limit
        Returns (is_allowed, headers)
        """
        client_id = self._get_client_id(request)
        bucket = self.buckets[client_id]
        
        self._refill_tokens(bucket)
        
        if bucket["tokens"] >= 1.0:
            bucket["tokens"] -= 1.0
            remaining = int(bucket["tokens"])
            reset_time = int(bucket["last_update"] + 60)
            
            return True, {
                "X-RateLimit-Limit": str(self.requests_per_minute),
                "X-RateLimit-Remaining": str(remaining),
                "X-RateLimit-Reset": str(reset_time)
            }
        else:
            return False, {
                "X-RateLimit-Limit": str(self.requests_per_minute),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(int(bucket["last_update"] + 60))
            }


rate_limiter = RateLimiter()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    FastAPI middleware for rate limiting
    """
    
    def __init__(self, app, enabled: bool = True):
        super().__init__(app)
        self.enabled = enabled
    
    async def dispatch(self, request: Request, call_next):
        if not self.enabled:
            return await call_next(request)
        
        # Skip rate limiting for health checks and static assets
        path = request.url.path
        if path in ["/", "/health", "/health/detailed", "/docs", "/openapi.json"]:
            return await call_next(request)
        
        # Check rate limit
        allowed, headers = rate_limiter.check_rate_limit(request)
        
        if not allowed:
            return JSONResponse(
                status_code=429,
                content={
                    "success": False,
                    "error": "Rate limit exceeded. Please try again later.",
                    "code": 429
                },
                headers=headers
            )
        
        response = await call_next(request)
        
        # Add rate limit headers to response
        for key, value in headers.items():
            response.headers[key] = value
        
        return response


def get_rate_limit_status() -> Dict:
    """Get current rate limiter statistics"""
    return {
        "requests_per_minute": rate_limiter.requests_per_minute,
        "burst_limit": rate_limiter.burst_limit,
        "active_clients": len(rate_limiter.buckets)
    }