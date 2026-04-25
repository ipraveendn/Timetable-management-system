import os
import json
import base64
import logging
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_KEY")


def _is_placeholder(value: str | None) -> bool:
    if not value:
        return True
    normalized = value.strip().lower()
    return normalized.startswith("your-") or normalized.startswith("replace-") or normalized.startswith("example-")


def _jwt_role(token: str) -> str:
    """Best-effort role extraction from Supabase JWT without verification."""
    try:
        payload_part = token.split(".")[1]
        padding = "=" * (-len(payload_part) % 4)
        payload = json.loads(base64.urlsafe_b64decode(payload_part + padding).decode())
        return str(payload.get("role", "")).strip()
    except Exception:
        return ""


service_role = _jwt_role(SUPABASE_SERVICE_KEY) if SUPABASE_SERVICE_KEY else ""
if SUPABASE_SERVICE_KEY and service_role == "service_role" and not _is_placeholder(SUPABASE_SERVICE_KEY):
    SUPABASE_KEY = SUPABASE_SERVICE_KEY
elif SUPABASE_ANON_KEY and not _is_placeholder(SUPABASE_ANON_KEY):
    if SUPABASE_SERVICE_KEY and not _is_placeholder(SUPABASE_SERVICE_KEY):
        logger.warning("SUPABASE_SERVICE_ROLE_KEY is not usable. Falling back to SUPABASE_KEY.")
    SUPABASE_KEY = SUPABASE_ANON_KEY
else:
    SUPABASE_KEY = SUPABASE_SERVICE_KEY if SUPABASE_SERVICE_KEY else SUPABASE_ANON_KEY

if not SUPABASE_URL or not SUPABASE_KEY:
    logger.warning("SUPABASE_URL or SUPABASE_KEY is missing from environment variables.")

supabase: Client = None
if SUPABASE_URL and SUPABASE_KEY and "your-" not in SUPABASE_KEY:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
else:
    logger.warning("Running with supabase=None (no valid credentials)")
