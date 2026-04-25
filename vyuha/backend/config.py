"""
VYUHA Centralized Configuration Management
Validates all environment variables on startup
"""

import os
from typing import List, Optional
from dataclasses import dataclass
from enum import Enum

class Environment(str, Enum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"

@dataclass
class DatabaseConfig:
    """Database configuration settings"""
    supabase_url: str
    supabase_service_role_key: str
    supabase_anon_key: Optional[str] = None

    @classmethod
    def from_env(cls) -> "DatabaseConfig":
        return cls(
            supabase_url=os.getenv("SUPABASE_URL", "").strip(),
            supabase_service_role_key=os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip(),
            supabase_anon_key=os.getenv("SUPABASE_KEY", "").strip() or None
        )

    def validate(self) -> List[str]:
        """Validate database configuration"""
        errors = []
        if not self.supabase_url:
            errors.append("SUPABASE_URL is required")
        if not self.supabase_service_role_key:
            errors.append("SUPABASE_SERVICE_ROLE_KEY is required")
        return errors

@dataclass
class JWTConfig:
    """JWT configuration settings"""
    secret: str
    algorithm: str = "HS256"
    expiry_hours: int = 24
    refresh_expiry_days: int = 30

    @classmethod
    def from_env(cls) -> "JWTConfig":
        expiry = os.getenv("JWT_EXPIRY_HOURS")
        refresh_expiry = os.getenv("JWT_REFRESH_EXPIRY_DAYS")

        return cls(
            secret=os.getenv("JWT_SECRET", "").strip(),
            algorithm=os.getenv("JWT_ALGORITHM", "HS256").strip(),
            expiry_hours=int(expiry) if expiry else 24,
            refresh_expiry_days=int(refresh_expiry) if refresh_expiry else 30
        )

    def validate(self) -> List[str]:
        """Validate JWT configuration"""
        errors = []
        if not self.secret:
            errors.append("JWT_SECRET is required")
        if len(self.secret) < 32:
            errors.append("JWT_SECRET should be at least 32 characters for security")
        return errors

@dataclass
class EmailConfig:
    """Email/SMTP configuration"""
    smtp_server: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_use_tls: bool = True
    smtp_username: Optional[str] = None
    smtp_password: Optional[str] = None
    smtp_from_email: str = "noreply@institution.edu"
    smtp_from_name: str = "VYUHA Academy"

    @classmethod
    def from_env(cls) -> "EmailConfig":
        port = os.getenv("SMTP_PORT")
        use_tls = os.getenv("SMTP_USE_TLS", "true").lower()
        
        # Support both standard names and common Render/GMAIL fallbacks
        username = os.getenv("SMTP_USERNAME") or os.getenv("GMAIL_ADDRESS")
        password = os.getenv("SMTP_PASSWORD") or os.getenv("GMAIL_APP_PASSWORD")

        return cls(
            smtp_server=os.getenv("SMTP_SERVER", "smtp.gmail.com").strip(),
            smtp_port=int(port) if port else 587,
            smtp_use_tls=use_tls in ("true", "1", "yes"),
            smtp_username=username.strip() if username else None,
            smtp_password=password.strip() if password else None,
            smtp_from_email=os.getenv("SMTP_FROM_EMAIL", username or "noreply@institution.edu").strip(),
            smtp_from_name=os.getenv("SMTP_FROM_NAME", "VYUHA Academy").strip()
        )

    def validate(self) -> List[str]:
        """Validate email configuration"""
        errors = []
        if self.smtp_use_tls and self.smtp_port != 587:
            errors.append("SMTP_USE_TLS=True requires SMTP_PORT=587")
        # Email delivery is optional; missing credentials should not block app startup.
        # send_email() already returns False when SMTP is not configured.
        if not self.smtp_from_email or "@" not in self.smtp_from_email:
            errors.append("SMTP_FROM_EMAIL must be a valid email address")
        return errors

@dataclass
class SecurityConfig:
    """Security-related configuration"""
    allowed_origins: List[str]
    cors_allow_credentials: bool = True
    cors_allow_methods: List[str] = None
    cors_allow_headers: List[str] = None
    rate_limit_requests: int = 100
    rate_limit_window: int = 60  # seconds
    jwt_expiry_hours: int = 24
    session_timeout_minutes: int = 30

    def __post_init__(self):
        if self.cors_allow_methods is None:
            self.cors_allow_methods = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
        if self.cors_allow_headers is None:
            self.cors_allow_headers = [
                "Authorization",
                "Content-Type",
                "X-College-ID",
                "X-Request-ID"
            ]

    @classmethod
    def from_env(cls) -> "SecurityConfig":
        origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173,http://localhost:3000")
        allowed_origins = [o.strip() for o in origins.split(",") if o.strip()]

        rate_limit = os.getenv("RATE_LIMIT_REQUESTS")
        rate_window = os.getenv("RATE_LIMIT_WINDOW")

        return cls(
            allowed_origins=allowed_origins,
            cors_allow_credentials=os.getenv("CORS_ALLOW_CREDENTIALS", "true").lower() in ("true", "1", "yes"),
            rate_limit_requests=int(rate_limit) if rate_limit else 100,
            rate_limit_window=int(rate_window) if rate_window else 60,
            jwt_expiry_hours=int(os.getenv("JWT_EXPIRY_HOURS", "24")),
            session_timeout_minutes=int(os.getenv("SESSION_TIMEOUT_MINUTES", "30"))
        )

    def validate(self) -> List[str]:
        """Validate security configuration"""
        errors = []
        if not self.allowed_origins:
            errors.append("ALLOWED_ORIGINS is required (comma-separated list)")
        return errors

@dataclass
class AppConfig:
    """Main application configuration"""
    environment: Environment
    debug: bool = False
    log_level: str = "INFO"
    app_url: str = "http://localhost:8000"
    api_version: str = "2.0.0"

    database: DatabaseConfig = None
    jwt: JWTConfig = None
    email: EmailConfig = None
    security: SecurityConfig = None

    @classmethod
    def from_env(cls) -> "AppConfig":
        env_str = os.getenv("ENVIRONMENT", "development").lower()
        environment = Environment.DEVELOPMENT
        if env_str == "production":
            environment = Environment.PRODUCTION
        elif env_str == "staging":
            environment = Environment.STAGING

        debug = os.getenv("DEBUG", "false").lower() in ("true", "1", "yes")

        return cls(
            environment=environment,
            debug=debug,
            log_level=os.getenv("LOG_LEVEL", "INFO" if not debug else "DEBUG"),
            app_url=os.getenv("APP_URL", "http://localhost:8000"),
            api_version=os.getenv("API_VERSION", "2.0.0"),
            database=DatabaseConfig.from_env(),
            jwt=JWTConfig.from_env(),
            email=EmailConfig.from_env(),
            security=SecurityConfig.from_env()
        )

    def validate(self) -> List[str]:
        """Validate entire configuration"""
        errors = []

        # Validate all sub-configs
        if self.database:
            errors.extend([f"Database: {e}" for e in self.database.validate()])
        if self.jwt:
            errors.extend([f"JWT: {e}" for e in self.jwt.validate()])
        if self.email:
            errors.extend([f"Email: {e}" for e in self.email.validate()])
        if self.security:
            errors.extend([f"Security: {e}" for e in self.security.validate()])
            # if self.environment == Environment.PRODUCTION:
            #     pass

        return errors

# Global config instance (singleton pattern)
_config: Optional[AppConfig] = None

def get_config() -> AppConfig:
    """Get the global configuration instance (lazy loaded)"""
    global _config
    if _config is None:
        _config = AppConfig.from_env()
        errors = _config.validate()
        if errors:
            raise ValueError(f"Configuration validation failed:\n" + "\n".join(f"  - {e}" for e in errors))
    return _config

def init_config() -> AppConfig:
    """Initialize configuration and return it"""
    return get_config()

# Export commonly used configs for convenience
config = get_config()
