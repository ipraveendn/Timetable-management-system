from fastapi import APIRouter, HTTPException, Depends
from models import BaseModel
from dependencies import get_college_id, get_current_user
from database import supabase
import os
import httpx
import json
import datetime
from typing import Optional, List, Dict, Any
from pathlib import Path
from dotenv import load_dotenv
from tools.email_tool import send_email
from feature_flags import DEFAULT_FLAGS, _load_local_flags
from auto_handler import AutoHandler
from monitoring import get_logger
import re
from uuid import uuid4

router = APIRouter(prefix="/chat", tags=["AI Chat Handler"])
logger = get_logger()

# Always read the backend .env explicitly so the chat handler cannot pick up a stale
# or unrelated environment file from another directory.
load_dotenv(dotenv_path=Path(__file__).resolve().parent / ".env", override=True)

SAFE_ASSISTANT_FALLBACK_MESSAGE = (
    "I can help with timetable lookups, substitute suggestions, and replacement notifications. "
    "Please include a teacher name, day, time, or replacement teacher."
)

CASUAL_CHAT_PATTERNS = [
    r"\bhi\b",
    r"\bhello\b",
    r"\bhey\b",
    r"\bwho are you\b",
    r"\bwhat('?s| is) your name\b",
    r"\bwhat are you doing\b",
    r"\bwhat should i ask\b",
    r"\bhelp me\b",
    r"\bhow are you\b",
    r"\bthank(s| you)\b",
]

SUBSTITUTION_PATTERNS = [
    r"\bsubstitute\b",
    r"\bsubstitution\b",
    r"\bsubtitute\b",
    r"\bsubtitution\b",
    r"\bsubtituion\b",
    r"\breplacement\b",
    r"\breplace\b",
    r"\babsent\b",
    r"\bleave\b",
    r"\bcover\b",
]

# Patterns that detect pronoun-based substitution follow-ups like
# "i want substitution for him" or "replace her".
PRONOUN_SUBSTITUTION_PATTERNS = [
    r"\b(?:substitut\w*|replace\w*|cover)\b.*\b(?:him|her|them|that\s+(?:faculty|teacher|professor)|this\s+(?:faculty|teacher|professor)|same\s+(?:faculty|teacher|professor))\b",
    r"\b(?:him|her|them)\b.*\b(?:substitut\w*|replace\w*)\b",
    r"\b(?:i\s+want|find|get|need)\b.*\b(?:substitut\w*|replace\w*)\b.*\b(?:him|her|them|for\s+(?:him|her|them))\b",
]

PRONOUN_TOKENS = {
    "him", "her", "his", "hers", "them", "they", "he", "she",
    "that faculty", "this faculty", "that teacher", "this teacher",
    "same faculty", "same teacher", "same professor",
    "that professor", "this professor", "it",
}

SCHEDULE_PATTERNS = [
    r"\bschedule\b",
    r"\btimetable\b",
    r"\broom\b",
    r"\bsubject\b",
    r"\bclass(es)?\b",
    r"\blecture(s)?\b",
    r"\bperiod(s)?\b",
    r"\bwhen is\b",
    r"\bwhere is\b",
    r"\btoday\b",
    r"\btomorrow\b",
    r"\byesterday\b",
    r"\bmonday\b",
    r"\btuesday\b",
    r"\bwednesday\b",
    r"\bthursday\b",
    r"\bfriday\b",
    r"\bsaturday\b",
    r"\bsunday\b",
    r"\bmon\b",
    r"\btue\b",
    r"\bwed\b",
    r"\bthu\b",
    r"\bfri\b",
    r"\bsat\b",
    r"\bsun\b",
    r"\bconflict(s)?\b",
]

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    history: Optional[List[dict]] = None
    context: Optional[dict] = None


class ChatSessionCreateRequest(BaseModel):
    title: Optional[str] = None


class ChatActionConfirmRequest(BaseModel):
    session_id: str
    action_type: str
    params: Dict[str, Any] = {}


def _get_groq_api_key() -> str:
    return os.getenv("GROQ_API_KEY", "").strip()


def _utc_now() -> datetime.datetime:
    return datetime.datetime.utcnow()


def _expiry_30_days() -> str:
    return (_utc_now() + datetime.timedelta(days=30)).isoformat()


def _chat_memory_enabled(college_id: str) -> bool:
    try:
        flags = _load_local_flags().get(college_id, {})
        return bool(flags.get("chat_persistent_memory", True))
    except Exception:
        return True


def _create_chat_session(college_id: str, user_id: int, title: Optional[str] = None) -> str:
    session_id = str(uuid4())
    if not supabase or not _chat_memory_enabled(college_id):
        return session_id
    try:
        supabase.table("chat_sessions").insert({
            "id": session_id,
            "college_id": college_id,
            "user_id": user_id,
            "title": (title or "Chat Session").strip()[:255],
            "last_activity_at": _utc_now().isoformat(),
        }).execute()
    except Exception as exc:
        logger.warning("Chat session create failed: %s", exc)
    return session_id


def _touch_chat_session(session_id: str) -> None:
    if not supabase:
        return
    try:
        supabase.table("chat_sessions").update({
            "last_activity_at": _utc_now().isoformat(),
        }).eq("id", session_id).execute()
    except Exception as exc:
        logger.warning("Chat session touch failed: %s", exc)


def _get_chat_session(session_id: str, college_id: str, user_id: int) -> Optional[Dict[str, Any]]:
    if not supabase:
        return None
    try:
        res = (
            supabase.table("chat_sessions")
            .select("*")
            .eq("id", session_id)
            .eq("college_id", college_id)
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )
        if not res.data:
            return None
        return res.data[0]
    except Exception as exc:
        logger.warning("Chat session fetch failed: %s", exc)
        return None


def _persist_chat_message(
    session_id: str,
    college_id: str,
    user_id: int,
    role: str,
    content: str,
    intent: Optional[str] = None,
) -> None:
    if not supabase or not session_id or not _chat_memory_enabled(college_id):
        return
    try:
        supabase.table("chat_messages").insert({
            "session_id": session_id,
            "college_id": college_id,
            "user_id": user_id,
            "role": role,
            "content": content,
            "intent": intent,
        }).execute()
        _touch_chat_session(session_id)
    except Exception as exc:
        logger.warning("Persist chat message failed: %s", exc)


def _get_recent_session_history(session_id: str, limit: int = 20) -> List[Dict[str, str]]:
    if not supabase or not session_id:
        return []
    try:
        res = (
            supabase.table("chat_messages")
            .select("role,content,created_at")
            .eq("session_id", session_id)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        rows = list(reversed(res.data or []))
        return [{"role": row.get("role", "assistant"), "content": row.get("content", "")} for row in rows]
    except Exception as exc:
        logger.warning("Load recent session history failed: %s", exc)
        return []


def _upsert_memory_fact(
    session_id: str,
    college_id: str,
    user_id: int,
    fact_key: str,
    fact_value: Dict[str, Any],
    fact_type: str = "workflow",
    confidence: float = 0.85,
) -> None:
    if not supabase or not session_id or not _chat_memory_enabled(college_id):
        return
    try:
        existing = (
            supabase.table("chat_memory_facts")
            .select("id")
            .eq("session_id", session_id)
            .eq("fact_key", fact_key)
            .limit(1)
            .execute()
        )
        payload = {
            "session_id": session_id,
            "college_id": college_id,
            "user_id": user_id,
            "fact_type": fact_type,
            "fact_key": fact_key,
            "fact_value_json": fact_value,
            "confidence": confidence,
            "expires_at": _expiry_30_days(),
            "updated_at": _utc_now().isoformat(),
        }
        if existing.data:
            supabase.table("chat_memory_facts").update(payload).eq("id", existing.data[0]["id"]).execute()
        else:
            supabase.table("chat_memory_facts").insert(payload).execute()
    except Exception as exc:
        logger.warning("Upsert memory fact failed for %s: %s", fact_key, exc)


def _load_memory_facts(session_id: str) -> Dict[str, Any]:
    if not supabase or not session_id:
        return {}
    try:
        now_iso = _utc_now().isoformat()
        res = (
            supabase.table("chat_memory_facts")
            .select("fact_key,fact_value_json,expires_at")
            .eq("session_id", session_id)
            .gte("expires_at", now_iso)
            .order("updated_at", desc=True)
            .execute()
        )
        facts: Dict[str, Any] = {}
        for row in res.data or []:
            key = row.get("fact_key")
            if key and key not in facts:
                facts[key] = row.get("fact_value_json") or {}
        return facts
    except Exception as exc:
        logger.warning("Load memory facts failed: %s", exc)
        return {}


def _merge_chat_context(
    request_context: Optional[Dict[str, Any]],
    memory_facts: Dict[str, Any],
) -> Dict[str, Any]:
    context = dict(request_context or {})

    if not context.get("substitution_faculty"):
        context["substitution_faculty"] = (
            (memory_facts.get("substitution_faculty") or {}).get("name") or ""
        )

    if not context.get("substitution_targets"):
        remembered_targets = (memory_facts.get("substitution_targets") or {}).get("names") or []
        if isinstance(remembered_targets, list):
            context["substitution_targets"] = [str(item).strip() for item in remembered_targets if str(item).strip()]

    if not context.get("last_referenced_faculty"):
        context["last_referenced_faculty"] = (
            (memory_facts.get("last_referenced_faculty") or {}).get("name") or ""
        )

    return context

async def execute_find_substitute(faculty_name: str, college_id: str):
    try:
        fac_res = (
            supabase.table("faculty")
            .select("id,name")
            .eq("college_id", college_id)
            .ilike("name", f"%{faculty_name}%")
            .execute()
        )
        if not fac_res.data:
            return f"Could not find faculty matching '{faculty_name}'."

        # Default to schedule-based substitute selection so availability/load are considered.
        resolved_name = fac_res.data[0]["name"]
        return await execute_substitute_for_faculty_schedule(college_id, resolved_name)
    except Exception as e:
        return f"Error finding substitutes: {str(e)}"


def _normalize_day(day: Optional[str]) -> Optional[str]:
    if not day:
        return None
    day_map = {
        "monday": "Mon", "tuesday": "Tue", "wednesday": "Wed",
        "thursday": "Thu", "friday": "Fri", "saturday": "Sat", "sunday": "Sun",
        "mon": "Mon", "tue": "Tue", "wed": "Wed", "thu": "Thu",
        "fri": "Fri", "sat": "Sat", "sun": "Sun",
    }
    return day_map.get(str(day).strip().lower(), str(day).strip())


def _date_for_slot_day(day: Optional[str], preferred_date: Optional[str] = None) -> str:
    if preferred_date:
        return preferred_date
    normalized_day = _normalize_day(day)
    today = datetime.datetime.now().date()
    if not normalized_day:
        return today.isoformat()

    days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    try:
        target = days.index(normalized_day)
    except ValueError:
        return today.isoformat()
    delta = (target - today.weekday()) % 7
    return (today + datetime.timedelta(days=delta)).isoformat()


def _format_time(value: Any) -> str:
    text = str(value or "")
    return text[:5] if len(text) >= 5 else text


def _normalize_faculty_query(value: str) -> str:
    """Normalize user-facing faculty references like 'professor redev' or 'ID: EMB005'."""
    text = re.sub(r"\s+", " ", str(value or "").strip())
    if not text:
        return ""

    text = re.sub(
        r"^(?:faculty|teacher|professor|prof|dr|mr|mrs|ms)\s+",
        "",
        text,
        flags=re.IGNORECASE,
    ).strip()
    text = re.sub(
        r"^(?:employee\s*id|emp\s*id|id|employee|emp|code)\s*[:\-]?\s*",
        "",
        text,
        flags=re.IGNORECASE,
    ).strip()

    if ":" in text:
        prefix, remainder = text.split(":", 1)
        if re.search(r"\b(?:id|employee\s*id|emp\s*id|emp|code)\b", prefix, re.IGNORECASE):
            text = remainder.strip()

    return text.rstrip("?.!,").strip()


def _find_faculty_by_name(college_id: str, faculty_name: str) -> Optional[Dict[str, Any]]:
    if not faculty_name or not supabase:
        return None
    normalized = _normalize_faculty_query(faculty_name)
    if not normalized:
        return None
    exact_res = (
        supabase.table("faculty")
        .select("*")
        .eq("college_id", college_id)
        .ilike("employee_id", normalized)
        .limit(1)
        .execute()
    )
    if exact_res.data:
        return exact_res.data[0]
    name_res = (
        supabase.table("faculty")
        .select("*")
        .eq("college_id", college_id)
        .ilike("name", f"%{normalized}%")
        .limit(1)
        .execute()
    )
    if name_res.data:
        return name_res.data[0]
    res = (
        supabase.table("faculty")
        .select("*")
        .eq("college_id", college_id)
        .ilike("employee_id", f"%{normalized}%")
        .limit(1)
        .execute()
    )
    return (res.data or [None])[0]


def _extract_faculty_names_from_message(message: str, college_id: str) -> List[str]:
    if not supabase:
        return []
    try:
        faculty_res = supabase.table("faculty").select("name").eq("college_id", college_id).execute()
        names = []
        normalized = re.sub(r"\s+", " ", message or "")
        for faculty in faculty_res.data or []:
            name = str(faculty.get("name") or "").strip()
            if name and re.search(rf"\b{re.escape(name)}\b", normalized, re.IGNORECASE):
                names.append(name)
        return names
    except Exception as exc:
        logger.warning("Faculty name extraction failed: %s", exc)
        return []


def _is_replacement_notification_request(message: str, history: Optional[List[dict]] = None, context: Optional[dict] = None) -> bool:
    lowered = (message or "").lower()
    has_action = any(token in lowered for token in ["notify", "notification", "send", "assign", "confirm", "email", "mail"])
    has_replacement = any(token in lowered for token in ["replacement", "replacment", "substitute", "substitution", "cover"])
    
    if has_action and has_replacement:
        return True
        
    if has_action and _message_contains_pronoun_reference(message):
        if _has_recent_substitution_intent(history, context):
            return True
            
    return False


def _resolve_replacement_request(
    message: str,
    college_id: str,
    context: Optional[Dict[str, Any]],
    history: Optional[List[Dict[str, Any]]],
    memory_facts: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    entities = _extract_query_entities(message, college_id)
    relative_date = _resolve_relative_date(message)

    absent_faculty = ""
    if context and isinstance(context, dict):
        absent_faculty = (
            str(context.get("substitution_faculty") or "").strip()
            or str(context.get("last_referenced_faculty") or "").strip()
        )
    if not absent_faculty:
        absent_fact = (memory_facts or {}).get("substitution_faculty") or {}
        absent_faculty = str(absent_fact.get("name") or "").strip()
    if not absent_faculty:
        absent_faculty = _extract_recent_absent_faculty(history) or ""

    names_in_message = _extract_faculty_names_from_message(message, college_id)
    if not absent_faculty and len(names_in_message) >= 2:
        # "Assign Kumar as replacement for Sharma" means Kumar is the replacement.
        absent_faculty = names_in_message[1]

    substitute_name = ""
    for name in names_in_message:
        if absent_faculty and name.lower() == absent_faculty.lower():
            continue
        substitute_name = name
        break

    if not substitute_name and context and isinstance(context, dict):
        targets = context.get("substitution_targets") or []
        if isinstance(targets, list) and targets:
            substitute_name = str(targets[0]).strip()
    if not substitute_name:
        targets_fact = (memory_facts or {}).get("substitution_targets") or {}
        targets = targets_fact.get("names") or []
        if targets:
            substitute_name = str(targets[0]).strip()
    if not substitute_name:
        recent_targets = _extract_recent_substitution_targets(history)
        if recent_targets:
            substitute_name = recent_targets[0]

    return {
        "absent_faculty": absent_faculty,
        "substitute_name": substitute_name,
        "day": entities.get("day"),
        "time_slot": entities.get("time_slot"),
        "date": relative_date,
    }


async def execute_replacement_notification(
    college_id: str,
    absent_faculty_name: str,
    substitute_name: str,
    current_user: Dict[str, Any],
    day: Optional[str] = None,
    time_slot: Optional[str] = None,
    date_value: Optional[str] = None,
) -> str:
    """Create confirmed substitution records and notify the replacement faculty."""
    try:
        absent = _find_faculty_by_name(college_id, absent_faculty_name)
        substitute = _find_faculty_by_name(college_id, substitute_name)
        if not absent:
            return f"I could not find the absent faculty '{absent_faculty_name}'."
        if not substitute:
            return f"I could not find the replacement teacher '{substitute_name}'."
        if absent["id"] == substitute["id"]:
            return "The absent faculty and replacement teacher cannot be the same person."

        normalized_day = _normalize_day(day)
        if date_value:
            try:
                normalized_day = datetime.datetime.strptime(date_value, "%Y-%m-%d").strftime("%a")
            except ValueError:
                pass

        query = (
            supabase.table("timetable_slots")
            .select("*")
            .eq("college_id", college_id)
            .eq("faculty_id", absent["id"])
        )
        if normalized_day:
            query = query.eq("day", normalized_day)
        if time_slot:
            formatted_time = time_slot if ":" in time_slot and len(time_slot) == 8 else f"{time_slot}:00" if len(time_slot) == 5 else time_slot
            query = query.eq("start_time", formatted_time)

        slots = query.order("day").order("start_time").execute().data or []
        if not slots:
            day_text = f" on {normalized_day}" if normalized_day else ""
            return f"No timetable slots found for {absent['name']}{day_text}."

        handler = AutoHandler(college_id)
        assigned = []
        skipped = []
        for slot in slots[:6]:
            candidates = handler.find_substitutes_for_slot(slot)
            candidate_ids = {candidate["faculty_id"] for candidate in candidates}
            if substitute["id"] not in candidate_ids:
                skipped.append(f"{slot['day']} {_format_time(slot.get('start_time'))}: {substitute['name']} is not available/eligible")
                continue

            assignment_date = _date_for_slot_day(slot.get("day"), date_value)
            existing_res = (
                supabase.table("substitutions")
                .select("*")
                .eq("college_id", college_id)
                .eq("timetable_slot_id", slot["id"])
                .eq("date", assignment_date)
                .in_("status", ["pending", "confirmed"])
                .limit(1)
                .execute()
            )
            if existing_res.data:
                substitution = existing_res.data[0]
                supabase.table("substitutions").update({
                    "substitute_faculty_id": substitute["id"],
                    "status": "pending",
                    "auto_assigned": True,
                }).eq("id", substitution["id"]).execute()
                substitution["substitute_faculty_id"] = substitute["id"]
                substitution["status"] = "pending"
            else:
                inserted = supabase.table("substitutions").insert({
                    "college_id": college_id,
                    "leave_request_id": None,
                    "original_faculty_id": absent["id"],
                    "substitute_faculty_id": substitute["id"],
                    "timetable_slot_id": slot["id"],
                    "date": assignment_date,
                    "status": "pending",
                    "priority": 1,
                    "auto_assigned": True,
                }).execute()
                substitution = inserted.data[0] if inserted.data else None

            if not substitution:
                skipped.append(f"{slot['day']} {_format_time(slot.get('start_time'))}: could not create assignment")
                continue

            substitution["confirmed_by"] = current_user.get("id")
            result = handler.process_substitution_confirmation(substitution)
            if result.get("success"):
                assigned.append(f"{slot['day']} {_format_time(slot.get('start_time'))}-{_format_time(slot.get('end_time'))}")
            else:
                skipped.append(f"{slot['day']} {_format_time(slot.get('start_time'))}: notification failed")

        if not assigned:
            detail = "\n".join(f"- {item}" for item in skipped[:5])
            return f"I could not assign {substitute['name']} as replacement for {absent['name']}.\n{detail}".strip()

        response = [
            f"Replacement assigned: **{substitute['name']}** will cover **{absent['name']}**.",
            "Notifications were sent and the assignment is visible in the teacher dashboard.",
            "Covered slots:",
        ]
        response.extend(f"- {item}" for item in assigned)
        if skipped:
            response.append("Skipped slots:")
            response.extend(f"- {item}" for item in skipped[:5])
        return "\n".join(response)
    except Exception as exc:
        logger.warning("Replacement notification failed: %s", exc)
        return f"I could not complete the replacement notification: {str(exc)}"


async def execute_substitute_for_faculty_schedule(
    college_id: str,
    faculty_name: str,
    day: Optional[str] = None,
    time_slot: Optional[str] = None,
):
    """Return substitutes for the actual timetable slots assigned to a faculty member."""
    try:
        faculty_res = (
            supabase.table("faculty")
            .select("id,name")
            .eq("college_id", college_id)
            .ilike("name", f"%{faculty_name}%")
            .execute()
        )
        if not faculty_res.data:
            return f"Could not find faculty matching '{faculty_name}'."

        faculty = faculty_res.data[0]
        query = supabase.table("timetable_slots").select("*").eq("college_id", college_id).eq("faculty_id", faculty["id"])
        if day:
            query = query.eq("day", day)
        if time_slot:
            formatted_time = time_slot if ":" in time_slot and len(time_slot) == 8 else f"{time_slot}:00" if len(time_slot) == 5 else time_slot
            query = query.eq("start_time", formatted_time)

        slots_res = query.order("day").order("start_time").execute()
        slots = slots_res.data or []
        if not slots:
            return f"No timetable slots found for {faculty['name']}{f' on {day}' if day else ''}."

        handler = AutoHandler(college_id)
        lines = [
            f"✅ Absent faculty: **{faculty['name']}**",
            "Basis: subject match, teacher availability, day availability, and current daily load.",
        ]
        if day:
            lines[1] += f" Filtered for {day}."

        for slot in slots[:6]:
            substitutes = handler.find_substitutes_for_slot(slot)
            if not substitutes:
                lines.append(f"- {slot['day']} {slot['start_time'][:5]}-{slot['end_time'][:5]}: no substitute found")
                continue

            top_names = ", ".join(
                f"{sub['name']} (score {sub.get('score', 'NA')}, load {sub.get('current_load', 'NA')})"
                for sub in substitutes[:3]
            )
            lines.append(
                f"- {slot['day']} {slot['start_time'][:5]}-{slot['end_time'][:5]}: {top_names}"
            )

        return "\n".join(lines)
    except Exception as e:
        return f"Error finding substitutes for {faculty_name}: {str(e)}"


async def execute_query_timetable(college_id: str, day: Optional[str] = None, time_slot: Optional[str] = None, faculty_name: Optional[str] = None, room_name: Optional[str] = None, subject_name: Optional[str] = None):
    # Mapping for day normalization
    DAY_MAP = {
        "monday": "Mon", "tuesday": "Tue", "wednesday": "Wed", "thursday": "Thu", "friday": "Fri", "saturday": "Sat", "sunday": "Sun",
        "mon": "Mon", "tue": "Tue", "wed": "Wed", "thu": "Thu", "fri": "Fri", "sat": "Sat", "sun": "Sun"
    }
    if day:
        day = DAY_MAP.get(day.lower(), day)
    
    try:
        # Step 1: Resolve IDs from Names if provided
        fac_id = None
        if faculty_name:
            faculty_res = (
                supabase.table("faculty")
                .select("id,name,employee_id")
                .eq("college_id", college_id)
                .eq("employee_id", faculty_name)
                .limit(1)
                .execute()
            )
            if not faculty_res.data:
                faculty_res = (
                    supabase.table("faculty")
                    .select("id,name,employee_id")
                    .eq("college_id", college_id)
                    .ilike("name", f"%{faculty_name}%")
                    .limit(1)
                    .execute()
                )
            if faculty_res.data:
                fac_id = faculty_res.data[0]["id"]
            else:
                return f"Could not find any teacher matching '{faculty_name}'."
            
        room_id = None
        if room_name:
            room_query = supabase.table("rooms").select("id").eq("college_id", college_id)
            res = room_query.ilike("room_name", f"%{room_name}%").execute()
            if not res.data:
                res = room_query.ilike("room_code", f"%{room_name}%").execute()
            if res.data: room_id = res.data[0]["id"]
            
        sub_id = None
        if subject_name:
            res = supabase.table("subjects").select("id").eq("college_id", college_id).ilike("name", f"%{subject_name}%").execute()
            if res.data: sub_id = res.data[0]["id"]

        # Step 2: Build the query
        query = supabase.table("timetable_slots").select("*").eq("college_id", college_id)
        if day: query = query.eq("day", day)
        if time_slot:
            # Postgres 'time' columns don't support ILIKE. Use exact match with padding.
            formatted_time = time_slot if ":" in time_slot and len(time_slot) == 8 else f"{time_slot}:00" if len(time_slot) == 5 else time_slot
            query = query.eq("start_time", formatted_time)
        if fac_id: query = query.eq("faculty_id", fac_id)
        if room_id: query = query.eq("room_id", room_id)
        if sub_id: query = query.eq("subject_id", sub_id)
        
        res = query.execute()
        if not res.data:
            return "No matching timetable slots found for that specific room, teacher, or time."

        # Step 3: Fetch related names for formatting
        slots = res.data[:8] # Limit to 8 slots
        fac_map = {}
        room_map = {}
        sub_map = {}
        
        # Batch fetch mapping (simple version)
        fac_ids = list(set(s["faculty_id"] for s in slots))
        room_ids = list(set(s["room_id"] for s in slots))
        sub_ids = list(set(s["subject_id"] for s in slots))
        
        if fac_ids:
            fdata = supabase.table("faculty").select("id,name").in_("id", fac_ids).execute().data
            fac_map = {f["id"]: f["name"] for f in fdata}
        if room_ids:
            rdata = supabase.table("rooms").select("id,room_name,room_code").in_("id", room_ids).execute().data
            room_map = {
                r["id"]: r.get("room_name") or r.get("room_code") or "Unknown"
                for r in rdata
            }
        if sub_ids:
            sdata = supabase.table("subjects").select("id,name").in_("id", sub_ids).execute().data
            sub_map = {s["id"]: s["name"] for s in sdata}

        # Step 4: Format output
        res_str = "📅 **Schedule Found:**\n"
        for s in slots:
            res_str += f"- **{s['day']}** at **{s['start_time'][:5]}**: {fac_map.get(s['faculty_id'], 'Unknown')} | {sub_map.get(s['subject_id'], 'Unknown')} | {room_map.get(s['room_id'], 'Unknown')}\n"
            
        return res_str
    except Exception as e:
        logger.warning("Timetable query failed: %s", e)
        return "I couldn't look up that schedule right now. Try asking for a teacher, room code, subject, or day."


def _resolve_relative_date(message: str):
    lowered = (message or "").lower()
    now = datetime.datetime.now()
    if "today" in lowered:
        return now.strftime("%Y-%m-%d")
    if "tomorrow" in lowered:
        return (now + datetime.timedelta(days=1)).strftime("%Y-%m-%d")
    if "yesterday" in lowered:
        return (now - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
    
    # Handle day names (find next occurrence of the day)
    day_map = {
        "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3, "friday": 4, "saturday": 5, "sunday": 6,
        "mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6
    }
    for token, target_weekday in day_map.items():
        if re.search(rf"\b{re.escape(token)}\b", lowered):
            days_ahead = target_weekday - now.weekday()
            if days_ahead <= 0: # Target day already happened this week or is today
                days_ahead += 7
            return (now + datetime.timedelta(days=days_ahead)).strftime("%Y-%m-%d")

    return None


async def execute_substitution_for_date(college_id: str, date_str: str, faculty_name: str = None):
    """Return deterministic substitute suggestions for leave requests on a given date."""
    try:
        requested_faculty = _find_faculty_by_name(college_id, faculty_name) if faculty_name else None
        if faculty_name and not requested_faculty:
            return f"I couldn't find a teacher named '{faculty_name}' in the database."

        leave_res = (
            supabase.table("leave_requests")
            .select("*")
            .eq("college_id", college_id)
            .eq("leave_date", date_str)
            .in_("status", ["pending", "approved"])
            .order("submitted_at", desc=True)
            .execute()
        )
        leaves = leave_res.data or []
        if requested_faculty:
            leaves = [leave for leave in leaves if leave.get("faculty_id") == requested_faculty["id"]]

        if not leaves and not faculty_name:
            return f"Tell me which teacher needs a substitute for {date_str}."
        
        # If we have a faculty name but no formal leave, create a virtual leave context.
        if not leaves and faculty_name:
            leaves = [{"faculty_id": requested_faculty["id"], "leave_date": date_str, "status": "virtual"}]

        handler = AutoHandler(college_id)

        faculty_ids = list({leave["faculty_id"] for leave in leaves})
        faculty_map = {}
        if faculty_ids:
            fac_res = supabase.table("faculty").select("id,name").in_("id", faculty_ids).execute()
            faculty_map = {row["id"]: row["name"] for row in (fac_res.data or [])}

        lines = [f"✅ Substitute suggestions for {date_str}:"]
        for leave in leaves[:5]:
            leave_label = faculty_map.get(leave["faculty_id"], f"Faculty #{leave['faculty_id']}")
            slots = handler.get_affected_slots_for_leave(leave)
            if not slots:
                lines.append(f"- {leave_label}: no timetable slots found on that date.")
                continue

            lines.append(f"- Absent faculty: {leave_label}")

            for slot in slots[:4]:
                substitutes = handler.find_substitutes_for_slot(slot)
                if not substitutes:
                    lines.append(
                        f"  - {slot.get('start_time', '')[:5]} - {slot.get('end_time', '')[:5]}: no substitute found"
                    )
                    continue

                names = ", ".join(
                    f"{sub['name']} (score {sub.get('score', 'NA')}, load {sub.get('current_load', 'NA')})"
                    for sub in substitutes[:3]
                )
                lines.append(
                    f"  - {slot.get('start_time', '')[:5]} - {slot.get('end_time', '')[:5]}: {names}"
                )

        return "\n".join(lines)
    except Exception as e:
        return f"Error finding substitutes for {date_str}: {str(e)}"


def _get_ai_chat_enabled(college_id: str) -> bool:
    """Read the per-college AI toggle with a local-file fallback."""
    default_enabled = bool(DEFAULT_FLAGS.get("ai_chat", True))

    try:
        res = supabase.table("feature_flags").select("ai_chat").eq("college_id", college_id).execute()
        if res.data:
            value = res.data[0].get("ai_chat")
            if value is not None:
                return bool(value)
    except Exception as err:
        logger.warning("Feature flag read failed: %s", err)

    local_flags = _load_local_flags().get(college_id, {})
    if "ai_chat" in local_flags:
        return bool(local_flags["ai_chat"])

    return default_enabled


def _extract_query_entities(message: str, college_id: str = None):
    """Lightweight parsing for manual mode so the assistant remains useful without AI."""
    normalized = re.sub(r"\s+", " ", message.strip())
    lowered = normalized.lower()

    day_map = {
        "monday": "Mon", "tuesday": "Tue", "wednesday": "Wed", "thursday": "Thu",
        "friday": "Fri", "saturday": "Sat", "sunday": "Sun",
        "mon": "Mon", "tue": "Tue", "wed": "Wed", "thu": "Thu",
        "fri": "Fri", "sat": "Sat", "sun": "Sun"
    }

    day = None
    if "today" in lowered:
        day = datetime.datetime.now().strftime("%a")
    elif "tomorrow" in lowered:
        day = (datetime.datetime.now() + datetime.timedelta(days=1)).strftime("%a")
    elif "yesterday" in lowered:
        day = (datetime.datetime.now() - datetime.timedelta(days=1)).strftime("%a")
    else:
        for token, short_day in day_map.items():
            if re.search(rf"\b{re.escape(token)}\b", lowered):
                day = short_day
                break

    time_match = re.search(r"\b(\d{1,2}:\d{2})\b", normalized)
    time_slot = time_match.group(1) if time_match else None

    faculty_name = None
    room_name = None
    subject_name = None

    # NEW: Direct Faculty Name Lookup (Bulletproof)
    # We scan the message for any faculty name that exists in the database for this college
    try:
        if supabase and college_id:
            all_fac_res = supabase.table("faculty").select("id, name").eq("college_id", college_id).execute()
        else:
            all_fac_res = None
        if all_fac_res and all_fac_res.data:
            # First pass: Exact full name match (highest priority)
            for fac in all_fac_res.data:
                name = str(fac.get("name") or "").strip()
                if not name: continue
                if re.search(rf"\b{re.escape(name)}\b", normalized, re.IGNORECASE):
                    faculty_name = name
                    break
            
            # Second pass: Partial name match (significant parts)
            if not faculty_name:
                for fac in all_fac_res.data:
                    full_name = str(fac.get("name") or "").strip()
                    if not full_name: continue
                    # Split name into parts, ignore very short ones (<=2 chars)
                    parts = [p for p in re.split(r"[ .'-]+", full_name) if len(p) >= 3]
                    for part in parts:
                        if re.search(rf"\b{re.escape(part)}\b", normalized, re.IGNORECASE):
                            faculty_name = full_name
                            break
                    if faculty_name:
                        break
    except Exception as e:
        logger.warning("Direct faculty lookup failed: %s", e)

    # Fallback to regex if direct lookup didn't work (for new/unloaded names)
    if not faculty_name:
        faculty_patterns = [
            r"(?:for|of|teacher|faculty|professor|mr|mrs|ms|dr|replace|substitute|cover|with|to)\s+([A-Za-z0-9][A-Za-z0-9 .'-]{0,80})",
            r"(?:find|show|check|get)\s+(?:schedule|timetable|substitute|replacement)\s+(?:for|of)?\s+([A-Za-z0-9][A-Za-z0-9 .'-]{0,80})",
            r"([A-Za-z0-9]{3,20})\s+(?:timetable|schedule|substitute|replacement|replace)",
            r"(?:timetable|schedule|substitute|replacement|replace|cover)\s+(?:of|for)?\s*([A-Za-z0-9]{3,20})",
            r"who\s+(?:can|will)\s+(?:replace|cover|substitute)\s+([A-Za-z0-9][A-Za-z0-9 .'-]{0,80})",
        ]
        for pattern in faculty_patterns:
            match = re.search(pattern, normalized, re.IGNORECASE)
            if match:
                faculty_name = match.group(1).strip().rstrip("?.!,")
                break

    # Guard: avoid treating temporal phrases (e.g., "for tomorrow") as faculty names.
    if faculty_name:
        faculty_name = re.sub(
            r"^(?:faculty|teacher|professor|prof|mr|mrs|ms|dr)\s+",
            "",
            faculty_name.strip(),
            flags=re.IGNORECASE,
        ).strip()
        fac_lower = faculty_name.lower()
        day_tokens = set(day_map.keys()) | {
            "today",
            "tomorrow",
            "yesterday",
            "morning",
            "afternoon",
            "evening",
            "night",
            "class",
            "classes",
            "him",
            "his",
            "her",
            "hers",
            "them",
            "they",
            "he",
            "she",
            "that faculty",
            "this faculty",
            "same faculty",
            "same teacher",
            "same professor",
        }
        if (fac_lower in day_tokens or 
            any(re.search(rf"\b{re.escape(token)}\b", fac_lower) for token in day_tokens) or 
            re.match(r"^\d{4}-\d{2}-\d{2}$", fac_lower)):
            faculty_name = None

    room_match = re.search(r"(?:room|lab)\s+([A-Za-z0-9 .'-]{1,50})", normalized, re.IGNORECASE)
    if room_match:
        room_name = room_match.group(1).strip().rstrip("?.!,")

    subject_match = re.search(r"(?:subject)\s+([A-Za-z0-9 .'-]{1,80})", normalized, re.IGNORECASE)
    if subject_match:
        subject_name = subject_match.group(1).strip().rstrip("?.!,")

    return {
        "day": day,
        "time_slot": time_slot,
        "faculty_name": faculty_name,
        "room_name": room_name,
        "subject_name": subject_name,
    }


def _is_substitution_query_text(message: str) -> bool:
    lowered = (message or "").lower().strip()
    if any(re.search(pattern, lowered, re.IGNORECASE) for pattern in SUBSTITUTION_PATTERNS):
        return True

    # Detect pronoun-based substitution follow-ups (e.g. "i want substitution for him")
    if any(re.search(p, lowered, re.IGNORECASE) for p in PRONOUN_SUBSTITUTION_PATTERNS):
        return True

    # Typo-tolerant fallback for variants like "subtituion", "substituion", etc.
    for token in re.findall(r"[a-z]+", lowered):
        if not token.startswith("sub"):
            continue
        if any(fragment in token for fragment in ["stitu", "stit", "titu", "btit"]):
            return True
    return False


def _is_manual_fallback_message(message: str) -> bool:
    lowered = (message or "").lower()
    return any(
        phrase in lowered
        for phrase in [
            "manual mode is active",
            "manual mode is still available",
            "ai assistant is unavailable",
            "ai assistant timed out",
            "ai assistant is temporarily unavailable",
            "ai assistant is busy right now",
            "manual fallback",
        ]
    )


def _is_casual_chat(message: str) -> bool:
    lowered = (message or "").lower().strip()
    return any(re.search(pattern, lowered, re.IGNORECASE) for pattern in CASUAL_CHAT_PATTERNS)


def _has_recent_substitution_intent(history: Optional[List[dict]], context: Optional[dict]) -> bool:
    if context and isinstance(context, dict):
        if str(context.get("substitution_faculty") or "").strip():
            return True

    if not history:
        return False

    for turn in reversed(history[-6:]):
        if str(turn.get("role", "")).lower() != "user":
            continue
        content = str(turn.get("content", "") or "")
        if _is_substitution_query_text(content):
            return True
    return False


def _message_contains_pronoun_reference(message: str) -> bool:
    """Check if the message uses a pronoun that refers to a previously mentioned entity."""
    lowered = (message or "").lower().strip()
    return any(re.search(rf"\b{re.escape(token)}\b", lowered) for token in PRONOUN_TOKENS)


def _resolve_pronoun_to_faculty(
    message: str,
    context: Optional[Dict[str, Any]],
    history: Optional[List[Dict[str, Any]]],
    memory_facts: Optional[Dict[str, Any]] = None,
) -> Optional[str]:
    """Resolve a pronoun ('him', 'her', 'them', etc.) to the most recently referenced faculty name."""
    if not _message_contains_pronoun_reference(message):
        return None

    # 1. Check explicit context fields
    if context and isinstance(context, dict):
        for key in ("substitution_faculty", "last_referenced_faculty"):
            val = str(context.get(key) or "").strip()
            if val:
                return val

    # 2. Check memory facts
    if memory_facts and isinstance(memory_facts, dict):
        for key in ("last_referenced_faculty", "substitution_faculty"):
            fact = memory_facts.get(key)
            if isinstance(fact, dict):
                val = str(fact.get("name") or "").strip()
                if val:
                    return val

    # 3. Fall back to conversation history
    return _extract_recent_faculty_reference(history)


def _classify_chat_intent(
    message: str,
    college_id: str,
    history: Optional[List[dict]] = None,
    context: Optional[dict] = None,
) -> str:
    lowered = (message or "").lower().strip()
    if _is_followup_availability_question(message):
        return "substitution"
    if _is_casual_chat(message):
        return "casual"
    if _is_substitution_query_text(message):
        return "substitution"
    # Detect pronoun follow-ups with substitution intent even without explicit keyword
    if _message_contains_pronoun_reference(message) and _has_recent_substitution_intent(history, context):
        return "substitution"
    if any(re.search(pattern, lowered, re.IGNORECASE) for pattern in SCHEDULE_PATTERNS):
        if _has_substitution_context(message, history, context, college_id):
            return "substitution"
        return "schedule"
    return "general"


def _is_followup_availability_question(message: str) -> bool:
    lowered = (message or "").lower().strip()
    return bool(
        re.search(r"\b(are|is)\s+(they|them|these|those)\s+free\s+now\b", lowered)
        or re.search(r"\bfree\s+now\b", lowered)
        or re.search(r"\bavailable\s+now\b", lowered)
        or re.search(r"\bwho\s+(is|are)\s+available\b", lowered)
        or re.search(r"\b(show|list|tell)\s+(me\s+)?(who\s+)?(is|are)\s+available\b", lowered)
        or re.search(r"\bwhich\s+(faculty|teacher|substitute|teachers|faculty members)\s+(is|are)\s+available\b", lowered)
    )


def _has_substitution_context(message: str, history: Optional[List[dict]], context: Optional[dict], college_id: str = None) -> bool:
    entities = _extract_query_entities(message, college_id)
    if entities.get("faculty_name") or entities.get("day") or entities.get("time_slot"):
        return True

    if _resolve_relative_date(message):
        return True

    if context and isinstance(context, dict):
        targets = context.get("substitution_targets") or []
        if isinstance(targets, list) and any(str(item).strip() for item in targets):
            return True
        if str(context.get("substitution_faculty") or "").strip():
            return True

    recent_targets = _extract_recent_substitution_targets(history)
    if recent_targets:
        return True

    return bool(_extract_recent_absent_faculty(history))


def _casual_chat_reply(message: str) -> str:
    lowered = (message or "").lower().strip()

    if re.search(r"\b(who are you|what('?s| is) your name)\b", lowered):
        return (
            "I’m VYUHA Assistant. I help with timetables, substitutions, leave handling, "
            "and schedule lookups."
        )
    if re.search(r"\b(hi|hello|hey)\b", lowered):
        return "Hello. How can I help with timetables or substitutions?"
    if re.search(r"\bhow are you\b", lowered):
        return "I’m ready to help with timetables, substitutions, and scheduling queries."
    if re.search(r"\bthank(s| you)\b", lowered):
        return "You’re welcome."
    if re.search(r"\bhelp me\b", lowered) or re.search(r"\bwhat should i ask\b", lowered):
        return (
            "You can ask things like: 'Show me today’s schedule', "
            "'Find a substitute for tomorrow', or 'Check room 101'."
        )

    return "I’m VYUHA Assistant. Ask me about schedules, substitutions, rooms, or leaves."


def _extract_recent_substitution_targets(history: Optional[List[dict]]) -> List[str]:
    """Pull the latest substitute names from the most recent substitution-style assistant reply."""
    if not history:
        return []

    for turn in reversed(history):
        content = str(turn.get("content", "") or "")
        lowered = content.lower()
        if (
            "suggested substitutes" not in lowered
            and "substitute suggestions" not in lowered
            and "top substitute candidates" not in lowered
            and "absent faculty" not in lowered
        ):
            continue

        names: List[str] = []
        for line in content.splitlines():
            line = line.strip()
            if not line.startswith("-") and not line.startswith("•"):
                continue
            match = re.search(r"\*\*([A-Za-z][A-Za-z0-9 .'-]{1,80})\*\*", line)
            if match:
                names.append(match.group(1).strip())
            else:
                plain = re.sub(r"^[\-•]\s*", "", line).strip()
                plain = re.sub(r"\(.*?\)", "", plain).strip()
                plain = plain.split(":")[0].strip()
                if plain and plain.lower() not in {"suggested substitutes", "basis"}:
                    names.append(plain)

        # Deduplicate while preserving order.
        seen = set()
        deduped = []
        for name in names:
            if name.lower() in seen:
                continue
            seen.add(name.lower())
            deduped.append(name)
        return deduped

    return []


def _extract_substitute_names_from_text(text: str) -> List[str]:
    names: List[str] = []
    for line in str(text or "").splitlines():
        line = line.strip()
        if not line.startswith("-"):
            continue
        match = re.search(r"-\s+[A-Za-z]{3}\s+\d{2}:\d{2}-\d{2}:\d{2}:\s+(.+)$", line)
        if not match:
            continue
        chunk = match.group(1)
        for candidate in chunk.split(","):
            name_match = re.match(r"\s*([A-Za-z][A-Za-z0-9 .'-]{1,80})\s+\(score", candidate.strip())
            if name_match:
                names.append(name_match.group(1).strip())
    seen = set()
    deduped: List[str] = []
    for name in names:
        lowered = name.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        deduped.append(name)
    return deduped


def _extract_recent_absent_faculty(history: Optional[List[dict]]) -> Optional[str]:
    if not history:
        return None

    # Prefer explicit assistant response marker first.
    for turn in reversed(history[-12:]):
        content = str(turn.get("content", "") or "")
        match = re.search(r"Absent faculty:\s*\*\*([^*]+)\*\*", content, re.IGNORECASE)
        if match:
            return match.group(1).strip()

    # Fallback: infer from recent user substitution query.
    for turn in reversed(history[-12:]):
        if str(turn.get("role", "")).lower() != "user":
            continue
        content = str(turn.get("content", "") or "")
        if not any(re.search(pattern, content, re.IGNORECASE) for pattern in SUBSTITUTION_PATTERNS):
            continue
        entities = _extract_query_entities(content, None)
        if entities.get("faculty_name"):
            return entities["faculty_name"]

    return None


def _extract_recent_faculty_reference(history: Optional[List[dict]]) -> Optional[str]:
    if not history:
        return None

    absent_faculty = _extract_recent_absent_faculty(history)
    if absent_faculty:
        return absent_faculty

    for turn in reversed(history[-12:]):
        if str(turn.get("role", "")).lower() != "user":
            continue
        content = str(turn.get("content", "") or "")
        entities = _extract_query_entities(content, None)
        faculty_name = str(entities.get("faculty_name") or "").strip()
        if faculty_name:
            return faculty_name

    return None


async def execute_check_current_availability(college_id: str, faculty_names: List[str]):
    """Check whether the given faculty members are free at the current time."""
    try:
        if not faculty_names:
            return "I don’t know which faculty to check. Ask about a specific substitute list first."

        now = datetime.datetime.now()
        today = now.strftime("%a")
        current_time = now.time()
        current_time_str = now.strftime("%H:%M:%S")

        lines = [f"✅ Current availability for {today} at {current_time_str[:5]}:"]
        for faculty_name in faculty_names[:6]:
            fac_res = (
                supabase.table("faculty")
                .select("id,name")
                .eq("college_id", college_id)
                .ilike("name", f"%{faculty_name}%")
                .execute()
            )
            if not fac_res.data:
                lines.append(f"- {faculty_name}: not found")
                continue

            faculty = fac_res.data[0]
            slots_res = (
                supabase.table("timetable_slots")
                .select("day,start_time,end_time,subject_id,room_id")
                .eq("college_id", college_id)
                .eq("faculty_id", faculty["id"])
                .eq("day", today)
                .execute()
            )

            busy_slot = None
            for slot in slots_res.data or []:
                start_time = slot.get("start_time")
                end_time = slot.get("end_time")
                if isinstance(start_time, str):
                    start_time = datetime.datetime.strptime(start_time[:5], "%H:%M").time()
                if isinstance(end_time, str):
                    end_time = datetime.datetime.strptime(end_time[:5], "%H:%M").time()
                if start_time and end_time and start_time <= current_time < end_time:
                    busy_slot = slot
                    break

            if busy_slot:
                lines.append(
                    f"- {faculty['name']}: busy now ({busy_slot['start_time'][:5]}-{busy_slot['end_time'][:5]})"
                )
            else:
                lines.append(f"- {faculty['name']}: free now")

        return "\n".join(lines)
    except Exception as e:
        return f"Error checking current availability: {str(e)}"


async def _manual_assistant_response(
    message: str,
    college_id: str,
    history: Optional[List[dict]] = None,
    context: Optional[dict] = None,
    memory_facts: Optional[Dict[str, Any]] = None,
):
    """Fallback path when AI is disabled or unavailable."""
    lowered = message.lower()
    is_substitution_query = _is_substitution_query_text(message)
    is_schedule_query = any(
        re.search(pattern, lowered, re.IGNORECASE) for pattern in SCHEDULE_PATTERNS
    )

    if is_substitution_query:
        entities = _extract_query_entities(message, college_id)
        relative_date = _resolve_relative_date(message)
        if relative_date:
            try:
                entities["day"] = datetime.datetime.strptime(relative_date, "%Y-%m-%d").strftime("%a")
            except ValueError:
                pass
        if not entities.get("faculty_name"):
            context_faculty = ""
            if context and isinstance(context, dict):
                context_faculty = (
                    str(context.get("substitution_faculty") or "").strip()
                    or str(context.get("last_referenced_faculty") or "").strip()
                )
            entities["faculty_name"] = context_faculty or _extract_recent_faculty_reference(history)

        # Date-first substitution request, e.g. "find substitute for tomorrow".
        if relative_date and not entities.get("faculty_name"):
            return await execute_substitution_for_date(college_id, relative_date)

        if entities.get("faculty_name"):
            if entities.get("day") or entities.get("time_slot"):
                return await execute_substitute_for_faculty_schedule(
                    college_id,
                    entities["faculty_name"],
                    day=entities.get("day"),
                    time_slot=entities.get("time_slot"),
                )
            return await execute_find_substitute(entities["faculty_name"], college_id)
        if relative_date:
            return await execute_substitution_for_date(college_id, relative_date)
        return (
            "Tell me the faculty name, or ask by date. Example: "
            "\"Find a substitute for Dr. Sharma\" or \"Find a substitute for tomorrow\"."
        )

    if is_schedule_query:
        entities = _extract_query_entities(message, college_id)
        # Resolve pronouns ("his schedule", "her schedule") to the actual faculty
        if not entities.get("faculty_name") and _message_contains_pronoun_reference(message):
            resolved = _resolve_pronoun_to_faculty(message, context, history, memory_facts)
            if resolved:
                entities["faculty_name"] = resolved
        if any(entities.values()):
            return await execute_query_timetable(college_id, **entities)
        return (
            "Ask with a day, room, subject, or teacher name, "
            "for example: \"Show me today's schedule\"."
        )

    if any(keyword in lowered for keyword in ["email", "notify", "send mail", "send email"]):
        return (
            "I can send replacement notifications when you include the absent teacher and replacement teacher."
        )

    return SAFE_ASSISTANT_FALLBACK_MESSAGE


def _infer_substitution_action(
    message: str,
    college_id: str,
    context: Optional[Dict[str, Any]],
    history: Optional[List[Dict[str, Any]]],
    memory_facts: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    entities = _extract_query_entities(message, college_id)
    relative_date = _resolve_relative_date(message)
    if relative_date:
        try:
            entities["day"] = datetime.datetime.strptime(relative_date, "%Y-%m-%d").strftime("%a")
        except ValueError:
            pass
    inferred = False
    confidence = 0.45

    faculty_name = entities.get("faculty_name")

    # FIX: Resolve pronouns ("him", "her", "them") to the actual faculty name
    if not faculty_name and _message_contains_pronoun_reference(message):
        resolved = _resolve_pronoun_to_faculty(message, context, history, memory_facts)
        if resolved:
            faculty_name = resolved
            inferred = True
            confidence = 0.88

    if not faculty_name:
        context_faculty = ""
        if context and isinstance(context, dict):
            context_faculty = (
                str(context.get("substitution_faculty") or "").strip()
                or str(context.get("last_referenced_faculty") or "").strip()
            )
        if context_faculty:
            faculty_name = context_faculty
            inferred = True
            confidence = 0.82
        else:
            recent_faculty = _extract_recent_faculty_reference(history)
            if recent_faculty:
                faculty_name = recent_faculty
                inferred = True
                confidence = 0.74

    if faculty_name and not inferred:
        confidence = 0.95
    elif relative_date and not faculty_name:
        confidence = 0.9
    elif entities.get("day") or entities.get("time_slot"):
        confidence = max(confidence, 0.8)

    params = {
        "faculty_name": faculty_name,
        "day": entities.get("day"),
        "time_slot": entities.get("time_slot"),
        "date": relative_date,
        "source_message": message,
        "inferred_faculty": inferred,
    }
    return {"confidence": confidence, "params": params}


async def _execute_confirmed_action(action_type: str, params: Dict[str, Any], college_id: str) -> str:
    if action_type == "find_substitute":
        faculty_name = str(params.get("faculty_name") or "").strip()
        day = params.get("day")
        time_slot = params.get("time_slot")
        date_value = str(params.get("date") or "").strip()

        if date_value and not faculty_name:
            return await execute_substitution_for_date(college_id, date_value)
        if not faculty_name:
            return (
                "I still need a faculty name or explicit date. "
                "Example: 'Find a substitute for Dr. Sharma tomorrow'."
            )
        if date_value and not day:
            try:
                day = datetime.datetime.strptime(date_value, "%Y-%m-%d").strftime("%a")
            except ValueError:
                pass
        if day or time_slot:
            return await execute_substitute_for_faculty_schedule(
                college_id,
                faculty_name,
                day=day,
                time_slot=time_slot,
            )
        return await execute_find_substitute(faculty_name, college_id)

    if action_type == "query_timetable":
        return await execute_query_timetable(
            college_id,
            day=params.get("day"),
            time_slot=params.get("time_slot"),
            faculty_name=params.get("faculty_name"),
            room_name=params.get("room_name"),
            subject_name=params.get("subject_name"),
        )

    return "Unsupported action type."


async def call_groq(
    sys_prompt: str,
    user_prompt: str,
    college_id: str,
    include_tools: bool = True,
    history: Optional[List[dict]] = None,
):
    """
    Calls Groq's endpoint running Llama 3.3 70B.
    Sends multi-turn conversation history so the model has context.
    If the key is missing or it fails, it degrades gracefully.
    """
    groq_api_key = _get_groq_api_key()
    if not groq_api_key:
        logger.warning("GROQ_API_KEY is missing or empty; falling back to manual mode.")
        return SAFE_ASSISTANT_FALLBACK_MESSAGE
        
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {groq_api_key}",
        "Content-Type": "application/json"
    }

    # Build multi-turn messages array
    messages = [{"role": "system", "content": sys_prompt}]
    for turn in (history or [])[-10:]:
        role = str(turn.get("role", "user")).strip()
        content = str(turn.get("content", "")).strip()
        if role in ("user", "assistant") and content:
            messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": user_prompt})
    
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": messages,
        "temperature": 0.2,
        "tools": [
            {
                "type": "function",
                "function": {
                    "name": "send_email",
                    "description": "Send a formal email to a teacher alerting them about a class substitution, schedule change, or generic notification.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "teacher_email": {
                                "type": "string",
                                "description": "The email address of the teacher."
                            },
                            "subject": {
                                "type": "string",
                                "description": "The subject line of the email."
                            },
                            "message_body": {
                                "type": "string",
                                "description": "The body content of the email containing all schedules and times."
                            }
                        },
                        "required": ["teacher_email", "subject", "message_body"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "find_substitute",
                    "description": "Finds potential substitute teachers for a faculty member who is absent, based on matching skills and subjects.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "faculty_name": {
                                "type": "string",
                                "description": "The name or ID of the absent faculty member."
                            }
                        },
                        "required": ["faculty_name"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "query_timetable",
                    "description": "Answers questions about the timetable/schedule by searching for specific rooms, teachers, days, or times.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "day": {"type": "string", "enum": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"], "description": "Three-letter day abbreviation (e.g., Mon, Tue). Use the provided current date context to resolve 'today', 'tomorrow', or 'yesterday'."},
                            "time_slot": {"type": "string", "description": "The starting time of the class (e.g. 08:00, 09:00)."},
                            "faculty_name": {"type": "string"},
                            "room_name": {"type": "string", "description": "The room name (e.g. Lab B204, Hall A101)."},
                            "subject_name": {"type": "string"}
                        }
                    }
                }
            }
        ] if include_tools else []
    }
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            message = data["choices"][0]["message"]
            
            # Agentic Loop: Check for Tool execution request
            if message.get("tool_calls"):
                for tool_call in message["tool_calls"]:
                    if tool_call["function"]["name"] == "send_email":
                        args = json.loads(tool_call["function"]["arguments"])
                        success = send_email(args["teacher_email"], args["subject"], args["message_body"])
                        return f"✅ Action Executed: I have successfully emailed **{args['teacher_email']}** regarding '{args['subject']}'!"
                    elif tool_call["function"]["name"] == "find_substitute":
                        args = json.loads(tool_call["function"]["arguments"])
                        entities = _extract_query_entities(user_prompt, college_id)
                        if entities.get("day") or entities.get("time_slot"):
                            return await execute_substitute_for_faculty_schedule(
                                college_id,
                                args["faculty_name"],
                                day=entities.get("day"),
                                time_slot=entities.get("time_slot"),
                            )
                        resolved_day = _resolve_relative_date(user_prompt)
                        if resolved_day:
                            try:
                                resolved_day = datetime.datetime.strptime(resolved_day, "%Y-%m-%d").strftime("%a")
                            except ValueError:
                                pass
                            return await execute_substitute_for_faculty_schedule(
                                college_id,
                                args["faculty_name"],
                                day=resolved_day,
                            )
                        return await execute_find_substitute(args["faculty_name"], college_id)
                    elif tool_call["function"]["name"] == "query_timetable":
                        args = json.loads(tool_call["function"]["arguments"])
                        return await execute_query_timetable(college_id, **args)
            
            return message.get("content") or "Action Completed."
            
        except httpx.HTTPStatusError as e:
            error_detail = e.response.text[:200] if e.response else "Unknown"
            logger.warning("Groq HTTP error: %s", error_detail)
            if e.response and e.response.status_code == 429:
                return SAFE_ASSISTANT_FALLBACK_MESSAGE
            if e.response and e.response.status_code in (401, 403):
                return SAFE_ASSISTANT_FALLBACK_MESSAGE
            if e.response and e.response.status_code == 503:
                return SAFE_ASSISTANT_FALLBACK_MESSAGE
            return SAFE_ASSISTANT_FALLBACK_MESSAGE
        except httpx.TimeoutException:
            logger.warning("Groq API timed out")
            return SAFE_ASSISTANT_FALLBACK_MESSAGE
        except Exception as e:
            logger.warning("Error calling AI: %s", e)
            return SAFE_ASSISTANT_FALLBACK_MESSAGE

@router.post("/session")
async def create_chat_session(
    request: ChatSessionCreateRequest,
    college_id: str = Depends(get_college_id),
    current_user: dict = Depends(get_current_user),
):
    session_id = _create_chat_session(college_id, int(current_user["id"]), request.title)
    return {"session_id": session_id}


@router.get("/session/{session_id}/messages")
async def get_chat_session_messages(
    session_id: str,
    limit: int = 50,
    college_id: str = Depends(get_college_id),
    current_user: dict = Depends(get_current_user),
):
    session = _get_chat_session(session_id, college_id, int(current_user["id"]))
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    safe_limit = min(max(limit, 1), 200)
    history = _get_recent_session_history(session_id, limit=safe_limit)
    return {"session_id": session_id, "messages": history}


@router.post("/action/confirm")
async def confirm_chat_action(
    request: ChatActionConfirmRequest,
    college_id: str = Depends(get_college_id),
    current_user: dict = Depends(get_current_user),
):
    session = _get_chat_session(request.session_id, college_id, int(current_user["id"]))
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    response_text = await _execute_confirmed_action(request.action_type, request.params or {}, college_id)
    _persist_chat_message(
        request.session_id,
        college_id,
        int(current_user["id"]),
        "assistant",
        response_text,
        intent=request.action_type,
    )
    _upsert_memory_fact(
        request.session_id,
        college_id,
        int(current_user["id"]),
        "last_confirmed_action",
        {"type": request.action_type, "params": request.params or {}},
        fact_type="workflow",
        confidence=0.95,
    )
    return {
        "session_id": request.session_id,
        "response": response_text,
        "needs_confirmation": False,
        "proposed_actions": [],
        "execution_mode": "manual",
    }


@router.post("")
async def chat_interaction(
    request: ChatRequest,
    college_id: str = Depends(get_college_id),
    current_user: dict = Depends(get_current_user),
):
    current_dt = datetime.datetime.now()
    current_date = current_dt.strftime("%Y-%m-%d")
    current_day = current_dt.strftime("%a")
    
    try:
        user_id = int(current_user["id"])
        session_id = (request.session_id or "").strip()
        if session_id:
            session = _get_chat_session(session_id, college_id, user_id)
            if not session:
                session_id = _create_chat_session(college_id, user_id, "Recovered Chat Session")
        else:
            session_id = _create_chat_session(college_id, user_id, "Chat Session")

        ai_flag_enabled = _get_ai_chat_enabled(college_id)
        groq_api_key = _get_groq_api_key()
        ai_available = bool(ai_flag_enabled and groq_api_key)
        ui_mode = "ai" if ai_available else "manual"

        session_history = _get_recent_session_history(session_id, limit=20)
        incoming_history = request.history or []
        merged_history = session_history or incoming_history[-20:]
        memory_facts = _load_memory_facts(session_id)
        merged_context = _merge_chat_context(request.context, memory_facts)

        _persist_chat_message(session_id, college_id, user_id, "user", request.message, intent="incoming")
        incoming_entities = _extract_query_entities(request.message, college_id)
        incoming_faculty_name = str(incoming_entities.get("faculty_name") or "").strip()

        # Also resolve pronouns for memory saving — ensures faculty reference persists
        # even when entity extraction produces no name (e.g. "his schedule").
        if not incoming_faculty_name and _message_contains_pronoun_reference(request.message):
            resolved_ref = _resolve_pronoun_to_faculty(
                request.message, merged_context, merged_history, memory_facts
            )
            if resolved_ref:
                incoming_faculty_name = resolved_ref

        if incoming_faculty_name:
            _upsert_memory_fact(
                session_id,
                college_id,
                user_id,
                "last_referenced_faculty",
                {"name": incoming_faculty_name},
                fact_type="conversation_context",
                confidence=0.85,
            )

        recent_substitutes = []
        if merged_context and isinstance(merged_context, dict):
            raw_targets = merged_context.get("substitution_targets") or []
            if isinstance(raw_targets, list):
                recent_substitutes = [str(item).strip() for item in raw_targets if str(item).strip()]
        if not recent_substitutes:
            recent_substitutes = _extract_recent_substitution_targets(merged_history)

        if _is_followup_availability_question(request.message) and recent_substitutes:
            availability = await execute_check_current_availability(college_id, recent_substitutes)
            _persist_chat_message(session_id, college_id, user_id, "assistant", availability, intent="substitution")
            return {
                "session_id": session_id,
                "response": availability,
                "mode": ui_mode,
                "execution_mode": "manual",
                "ai_enabled": ai_available,
                "warning": None,
                "intent": "substitution",
                "needs_confirmation": False,
                "proposed_actions": [],
            }

        intent = _classify_chat_intent(request.message, college_id, merged_history, merged_context)

        if intent == "casual":
            response_text = _casual_chat_reply(request.message)
            _persist_chat_message(session_id, college_id, user_id, "assistant", response_text, intent="casual")
            return {
                "session_id": session_id,
                "response": response_text,
                "mode": ui_mode,
                "execution_mode": "manual",
                "ai_enabled": ai_available,
                "warning": None,
                "intent": "casual",
                "needs_confirmation": False,
                "proposed_actions": [],
            }

        faculty_context = ""
        try:
            # Step 1: Gather absolute contextual data safely
            faculty_res = supabase.table("faculty").select("id,name,subjects").eq("college_id", college_id).execute()
            
            # Build a textual context
            if hasattr(faculty_res, 'data') and faculty_res.data:
                faculty_context = "Current Faculty Data:\n"
                for f in faculty_res.data:
                    subjects = f.get('subjects') or []
                    faculty_context += f"- {f.get('name', 'Unknown')} (ID: {f.get('id')}) teaches {', '.join(subjects)}\n"
        except Exception as db_err:
            logger.warning("DB Context Error: %s", db_err)
            faculty_context = "Database disconnected. No faculty context available."
            
        # Build conversation memory section for the system prompt
        memory_lines = []
        if merged_context.get("substitution_faculty"):
            memory_lines.append(f"- Last discussed faculty (absent): {merged_context['substitution_faculty']}")
        if merged_context.get("last_referenced_faculty"):
            ref_fac = merged_context["last_referenced_faculty"]
            if isinstance(ref_fac, dict):
                ref_fac = ref_fac.get("name", "")
            if ref_fac:
                memory_lines.append(f"- Last referenced faculty: {ref_fac}")
        if merged_context.get("substitution_targets"):
            targets = merged_context["substitution_targets"]
            if isinstance(targets, list) and targets:
                memory_lines.append(f"- Recent substitute candidates: {', '.join(str(t) for t in targets[:5])}")
        memory_section = "\n".join(memory_lines) if memory_lines else "No prior conversation context."

        system_prompt = f"""
        You are the VYUHA AI Assistant for College Timetables and Substitutions.
        You are talking to an Admin/Principal. Be extremely concise. Do not use filler words.
        If asked about substitutions, rank them based on free time.
        
        CURRENT CONTEXT:
        - Today's Date: {current_date}
        - Today's Day: {current_day}

        CONVERSATION MEMORY (from prior messages in this session):
        {memory_section}
        When the user says "him", "her", "them", "that faculty", etc., they are referring to the faculty mentioned in the conversation memory above. Resolve these pronouns accordingly.
        
        CRITICAL AGENT INSTRUCTIONS:
        1. If the Admin says a teacher is absent/on leave, USE `find_substitute`.
        2. If the Admin asks "Who is in room X", "What is Mr Y's schedule", or "When is Subject Z", USE `query_timetable`.
        3. If the Admin says "email the teacher" or "notify them", USE `send_email`.
        
        You MUST USE TOOL CALLS to get real data. Never say "I don't have access to room assignments" if you can use `query_timetable`.
        
        Always resolve relative dates like "today", "tomorrow", or "yesterday" using the provided day context before calling tools.
        
        {faculty_context}
        """

        if intent == "substitution":
            if _is_replacement_notification_request(request.message, merged_history, merged_context):
                notify_params = _resolve_replacement_request(
                    request.message,
                    college_id,
                    merged_context,
                    merged_history,
                    memory_facts,
                )
                if not notify_params.get("absent_faculty") or not notify_params.get("substitute_name"):
                    response_text = (
                        "Tell me both teachers for the replacement. Example: "
                        "'Assign Prof. Kumar as replacement for Prof. Sharma tomorrow'."
                    )
                else:
                    response_text = await execute_replacement_notification(
                        college_id,
                        notify_params["absent_faculty"],
                        notify_params["substitute_name"],
                        current_user,
                        day=notify_params.get("day"),
                        time_slot=notify_params.get("time_slot"),
                        date_value=notify_params.get("date"),
                    )
                _persist_chat_message(session_id, college_id, user_id, "assistant", response_text, intent="substitution")
                return {
                    "session_id": session_id,
                    "response": response_text,
                    "mode": ui_mode,
                    "execution_mode": "manual",
                    "ai_enabled": ai_available,
                    "warning": None,
                    "intent": "substitution",
                    "needs_confirmation": False,
                    "proposed_actions": [],
                }

            inferred_action = _infer_substitution_action(request.message, college_id, merged_context, merged_history, memory_facts)
            params = inferred_action["params"]
            confidence = float(inferred_action["confidence"])
            if not params.get("faculty_name") and not params.get("date"):
                response_text = (
                    "I need one detail to continue: tell me the faculty name or a date. "
                    "Example: 'Find substitute for Dr. Sharma tomorrow'."
                )
                _persist_chat_message(session_id, college_id, user_id, "assistant", response_text, intent="substitution")
                return {
                    "session_id": session_id,
                    "response": response_text,
                    "mode": ui_mode,
                    "execution_mode": "manual",
                    "ai_enabled": ai_available,
                    "warning": None, # SILENCED
                    "intent": "substitution",
                    "needs_confirmation": False,
                    "proposed_actions": [],
                }

            # Assume-then-confirm: run preview deterministically but require explicit final confirmation.
            preview = await _execute_confirmed_action("find_substitute", params, college_id)
            preview_lower = str(preview or "").lower()
            preview_failed = (
                preview_lower.startswith("could not find faculty")
                or preview_lower.startswith("error ")
                or preview_lower.startswith("error finding")
                or preview_lower.startswith("i still need")
            )
            if preview_failed:
                _persist_chat_message(session_id, college_id, user_id, "assistant", preview, intent="substitution")
                return {
                    "session_id": session_id,
                    "response": preview,
                    "mode": ui_mode,
                    "execution_mode": "manual",
                    "ai_enabled": ai_available,
                    "warning": None, # SILENCED
                    "intent": "substitution",
                    "needs_confirmation": False,
                    "proposed_actions": [],
                }
            assumption_note = ""
            if params.get("inferred_faculty") and params.get("faculty_name"):
                assumption_note = f"Assumed faculty from memory: {params['faculty_name']}.\n\n"
            response_text = f"{assumption_note}{preview}"
            proposed_actions = [{
                "type": "find_substitute",
                "params": params,
                "confidence": round(confidence, 3),
            }]
            _persist_chat_message(session_id, college_id, user_id, "assistant", response_text, intent="substitution")
            if params.get("faculty_name"):
                _upsert_memory_fact(
                    session_id,
                    college_id,
                    user_id,
                    "substitution_faculty",
                    {"name": params.get("faculty_name")},
                    fact_type="substitution_context",
                    confidence=confidence,
                )
                _upsert_memory_fact(
                    session_id,
                    college_id,
                    user_id,
                    "last_referenced_faculty",
                    {"name": params.get("faculty_name")},
                    fact_type="conversation_context",
                    confidence=confidence,
                )
            targets = _extract_substitute_names_from_text(preview)
            if targets:
                _upsert_memory_fact(
                    session_id,
                    college_id,
                    user_id,
                    "substitution_targets",
                    {"names": targets},
                    fact_type="substitution_context",
                    confidence=max(0.8, confidence),
                )
            return {
                "session_id": session_id,
                "response": response_text,
                "mode": ui_mode,
                "execution_mode": "manual",
                "ai_enabled": ai_available,
                "warning": None, # SILENCED
                "intent": "substitution",
                "needs_confirmation": False,
                "proposed_actions": [],
            }

        # Step 2: Route by intent.
        # Substitution is always deterministic to avoid model hallucinating faculty names.
        if intent == "schedule":
            # Pre-resolve pronouns for schedule queries (e.g. "get his schedule")
            schedule_entities = _extract_query_entities(request.message, college_id)
            if not schedule_entities.get("faculty_name") and _message_contains_pronoun_reference(request.message):
                resolved_fac = _resolve_pronoun_to_faculty(request.message, merged_context, merged_history, memory_facts)
                if resolved_fac:
                    schedule_entities["faculty_name"] = resolved_fac
            if any(schedule_entities.values()):
                ai_response = await execute_query_timetable(college_id, **schedule_entities)
            else:
                ai_response = await _manual_assistant_response(
                    request.message,
                    college_id,
                    history=merged_history,
                    context=merged_context,
                    memory_facts=memory_facts,
                )
            execution_mode = "manual"
        else:
            # General chat: allow AI if available, but never expose tool-calling.
            if ai_available:
                general_prompt = (
                    "You are VYUHA Assistant. Answer briefly and naturally. "
                    "Do not use tools. If the user asks about schedules or substitutions, "
                    "ask them to rephrase with a clear timetable or substitution request."
                )
                ai_response = await call_groq(general_prompt, request.message, college_id, include_tools=False, history=merged_history)
                execution_mode = "manual" if _is_manual_fallback_message(ai_response) else "ai"
            else:
                ai_response = _casual_chat_reply(request.message)
                execution_mode = "manual"

        _persist_chat_message(session_id, college_id, user_id, "assistant", ai_response, intent=intent)

        return {
            "session_id": session_id,
            "response": ai_response,
            "mode": ui_mode,
            "execution_mode": execution_mode,
            "ai_enabled": ai_available,
            "warning": None,
            "intent": intent,
            "needs_confirmation": False,
            "proposed_actions": [],
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error in chat processing: {str(e)}")
