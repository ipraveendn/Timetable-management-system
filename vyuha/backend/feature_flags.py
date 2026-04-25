from fastapi import APIRouter, HTTPException, Depends
from database import supabase
from dependencies import get_college_id
import json
import os

router = APIRouter(tags=["Feature Flags"])

# Default flags for every new college
DEFAULT_FLAGS = {
    "saturday_enabled": True,
    "sunday_enabled": False,
    "break_after_3rd_period": True,
    "max_lectures_per_day": 4,
    "lab_sessions_enabled": True,
    "even_distribution": True,
    "ai_chat": True,
    "slots_per_day": 8,
    "start_time": "09:00",
    "slot_duration_mins": 60
    ,
    "chat_persistent_memory": True,
    "chat_guided_workflows": True,
    "chat_assume_then_confirm": True
}

# Local file storage path (fallback when DB table doesn't exist)
FLAGS_FILE = os.path.join(os.path.dirname(__file__), "feature_flags_store.json")


def _load_local_flags():
    """Load flags from local JSON file."""
    if os.path.exists(FLAGS_FILE):
        with open(FLAGS_FILE, "r") as f:
            return json.load(f)
    return {}


def _save_local_flags(all_flags):
    """Save all flags to local JSON file."""
    with open(FLAGS_FILE, "w") as f:
        json.dump(all_flags, f, indent=2)


def _try_supabase_read(college_id):
    """Try reading from Supabase. Returns None if table doesn't exist."""
    try:
        res = supabase.table("feature_flags").select("*").eq("college_id", college_id).execute()
        if res.data and len(res.data) > 0:
            return res.data[0]
        return {}  # Table exists but no data for this college
    except Exception as e:
        error_msg = str(e)
        if "PGRST" in error_msg or "does not exist" in error_msg:
            return None  # Table doesn't exist
        return None


def _try_supabase_write(college_id, validated):
    """Try writing to Supabase. Returns True if successful."""
    try:
        existing = supabase.table("feature_flags").select("id").eq("college_id", college_id).execute()
        if existing.data and len(existing.data) > 0:
            supabase.table("feature_flags").update(validated).eq("college_id", college_id).execute()
        else:
            supabase.table("feature_flags").insert({**validated, "college_id": college_id}).execute()
        return True
    except Exception:
        return False


@router.get("/feature-flags")
async def get_feature_flags(college_id: str = Depends(get_college_id)):
    """Get feature flags for the college. Uses Supabase if available, local file otherwise."""
    merged = dict(DEFAULT_FLAGS)

    # Try Supabase first
    db_flags = _try_supabase_read(college_id)
    
    if db_flags is not None and db_flags:
        # Got flags from DB
        merged.update({k: db_flags.get(k, v) for k, v in DEFAULT_FLAGS.items()})
    
    # Fallback: local JSON file
    all_flags = _load_local_flags()
    college_flags = all_flags.get(college_id, {})
    
    merged.update({k: college_flags.get(k, merged.get(k, v)) for k, v in DEFAULT_FLAGS.items()})
    return merged


@router.put("/feature-flags")
async def update_feature_flags(flags: dict, college_id: str = Depends(get_college_id)):
    """Save feature flags. Tries Supabase first, falls back to local file."""
    # Validate: only allow known flag keys
    validated = {}
    for key, default_val in DEFAULT_FLAGS.items():
        if key in flags:
            validated[key] = flags[key]
        else:
            validated[key] = default_val
    
    # Try Supabase first
    saved_to_db = _try_supabase_write(college_id, validated)
    
    # Always save to local file as backup
    all_flags = _load_local_flags()
    all_flags[college_id] = validated
    _save_local_flags(all_flags)
    
    storage = "database" if saved_to_db else "local file"
    return {"message": f"Feature flags saved successfully ({storage})", "flags": validated}
