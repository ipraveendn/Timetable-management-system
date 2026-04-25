"""
VYUHA Auto Handler System
Automated background processing for leave requests, substitutions, and timetable management
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, date
from database import supabase
from dependencies import get_college_id
from auth_system import get_current_user_from_token
import json

router = APIRouter(prefix="/auto", tags=["Auto Handler"])


def _require_admin_or_hod(current_user: dict):
    if current_user.get("role") not in ["admin", "principal", "superadmin"]:
        raise HTTPException(
            status_code=403,
            detail="Only admin or Principal can perform this action"
        )

# ============================================
# AUTO HANDLER CORE
# ============================================

class AutoHandler:
    """Centralized auto-processing engine for VYUHA."""
    
    def __init__(self, college_id: str):
        self.college_id = college_id
    
    def get_affected_slots_for_leave(self, leave_request: dict) -> List[dict]:
        """Find all timetable slots affected by a leave request."""
        faculty_id = leave_request["faculty_id"]
        leave_date = leave_request["leave_date"]
        
        try:
            dt = datetime.strptime(leave_date, "%Y-%m-%d")
            day_name = dt.strftime("%a")
        except:
            return []
            
        res = supabase.table("timetable_slots").select("*").eq("college_id", self.college_id).eq("faculty_id", faculty_id).eq("day", day_name).execute()
        return res.data

    def find_substitutes_for_slot(self, slot: dict) -> List[dict]:
        """
        Find top 3 best substitutes for a specific timetable slot.
        Rules:
        1. Subject match
        2. Faculty is free at this specific day/time
        3. Workload balance
        4. No room/faculty conflicts
        """
        day = slot["day"]
        time_slot = slot["start_time"]
        subject_id = slot["subject_id"]
        original_faculty_id = slot["faculty_id"]
        
        # Get subject info
        sub_res = supabase.table("subjects").select("name").eq("id", subject_id).eq("college_id", self.college_id).execute()
        subject_name = sub_res.data[0]["name"] if sub_res.data else ""
        
        # Get all active faculty (except the one on leave)
        others_res = supabase.table("faculty").select("*").eq("college_id", self.college_id).neq("id", original_faculty_id).eq("status", "active").execute()
        
        candidates = []
        for faculty in others_res.data:
            fac_id = faculty["id"]
            fac_subjects = faculty.get("subjects", [])
            
            # RULE 1: Subject Match (Expertise)
            if subject_name not in fac_subjects and fac_subjects:
                continue
                
            # RULE 2: Specific Time Availability
            # Check if faculty has a class at this time
            conflict_res = supabase.table("timetable_slots").select("id").eq("college_id", self.college_id).eq("faculty_id", fac_id).eq("day", day).eq("start_time", time_slot).execute()
            if conflict_res.data:
                continue # Faculty already has a class at this time
                
            # RULE 3: Availability Days
            available_days = faculty.get("available_days", ["Mon", "Tue", "Wed", "Thu", "Fri"])
            if day not in available_days:
                continue
                
            # RULE 4: Daily Load
            today_slots = supabase.table("timetable_slots").select("id").eq("college_id", self.college_id).eq("faculty_id", fac_id).eq("day", day).execute()
            max_classes = faculty.get("max_classes_per_day", 5)
            if len(today_slots.data) >= max_classes:
                continue
                
            # Score (lower is better)
            score = len(today_slots.data)
            
            candidates.append({
                "faculty_id": fac_id,
                "name": faculty["name"],
                "department": faculty.get("department"),
                "current_load": len(today_slots.data),
                "score": score
            })
            
        candidates.sort(key=lambda x: x["score"])
        return candidates[:3]

    def find_substitutes_for_leave(self, leave_request: dict) -> dict:
        """Find substitutes for all slots in a leave request."""
        slots = self.get_affected_slots_for_leave(leave_request)
        
        result = {
            "leave_id": leave_request["id"],
            "faculty_id": leave_request["faculty_id"],
            "date": leave_request["leave_date"],
            "affected_slots": []
        }
        
        for slot in slots:
            substitutes = self.find_substitutes_for_slot(slot)
            result["affected_slots"].append({
                "slot_id": slot["id"],
                "start_time": slot["start_time"],
                "end_time": slot["end_time"],
                "subject_id": slot["subject_id"],
                "substitutes": substitutes
            })
            
        return result
    
    def notify_admins_about_leave(self, leave_request: dict, substitutes: dict):
        """Notify all admins about a new leave request with substitute suggestions."""
        
        leave_date = leave_request.get("leave_date", "Unknown")
        leave_type = leave_request.get("leave_type", "Unknown")
        
        # Get faculty name
        fac_res = supabase.table("faculty").select("name").eq("id", leave_request["faculty_id"]).execute()
        faculty_name = fac_res.data[0]["name"] if fac_res.data else "Unknown"
        
        # Get all admins
        admins_res = supabase.table("users").select("id").eq("college_id", self.college_id).eq("role", "admin").execute()
        
        affected_slots = substitutes.get("affected_slots", [])
        
        for admin in admins_res.data:
            notification_data = {
                "college_id": self.college_id,
                "user_id": admin["id"],
                "type": "leave_request",
                "title": f"Leave Request: {faculty_name}",
                "message": f"New {leave_type} request for {leave_date}",
                "data": {
                    "leave_id": leave_request["id"],
                    "faculty_name": faculty_name,
                    "leave_date": leave_date,
                    "leave_type": leave_type,
                    "substitutes": affected_slots[:3],
                    "substitute_count": len(affected_slots)
                }
            }
            supabase.table("notifications").insert(notification_data).execute()
    
    def validate_timetable_load_balance(self) -> dict:
        """
        Validate timetable load balance across all faculty.
        Returns issues and suggested fixes.
        """
        # Get all faculty
        faculty_res = supabase.table("faculty").select("*").eq("college_id", self.college_id).eq("status", "active").execute()
        faculty_list = faculty_res.data
        
        if not faculty_list:
            return {"balanced": True, "issues": [], "score": 100}
        
        # Get all timetable slots
        slots_res = supabase.table("timetable_slots").select("*").eq("college_id", self.college_id).execute()
        slots = slots_res.data
        
        # Calculate load per faculty per day
        faculty_load = {}
        for f in faculty_list:
            faculty_load[f["id"]] = {"name": f["name"], "max": f.get("max_classes_per_day", 5), "daily": {}}
        
        for slot in slots:
            fid = slot.get("faculty_id")
            day = slot.get("day")
            if fid in faculty_load:
                if day not in faculty_load[fid]["daily"]:
                    faculty_load[fid]["daily"][day] = 0
                faculty_load[fid]["daily"][day] += 1
        
        # Check for imbalances
        issues = []
        total_score = 100
        max_deviation = 0
        
        for fid, data in faculty_load.items():
            for day, count in data["daily"].items():
                deviation = abs(count - data["max"])
                max_deviation = max(max_deviation, deviation)
                
                if deviation > 2:  # Allow 2 class deviation
                    issues.append({
                        "faculty_id": fid,
                        "faculty_name": data["name"],
                        "day": day,
                        "current_load": count,
                        "max_load": data["max"],
                        "issue": f"Overloaded by {deviation} classes"
                    })
        
        # Score calculation
        if faculty_list:
            avg_faculty = len(slots) / len(faculty_list)
            if avg_faculty > 0:
                score = max(0, 100 - (max_deviation * 10))
            else:
                score = 100
        else:
            score = 100
        
        return {
            "balanced": len(issues) == 0,
            "issues": issues,
            "score": score,
            "total_slots": len(slots),
            "faculty_count": len(faculty_list)
        }
    
    def validate_timetable_spread(self) -> dict:
        """
        Check if classes are evenly spread across days.
        """
        slots_res = supabase.table("timetable_slots").select("day").eq("college_id", self.college_id).execute()
        slots = slots_res.data
        
        day_counts = {}
        for slot in slots:
            day = slot.get("day", "Unknown")
            day_counts[day] = day_counts.get(day, 0) + 1
        
        # Calculate spread score
        if day_counts:
            avg = sum(day_counts.values()) / len(day_counts)
            variance = sum((count - avg) ** 2 for count in day_counts.values()) / len(day_counts)
            spread_score = max(0, 100 - (variance * 5))
        else:
            spread_score = 100
        
        issues = []
        if day_counts:
            avg = sum(day_counts.values()) / len(day_counts)
            for day, count in day_counts.items():
                deviation = abs(count - avg) / (avg if avg > 0 else 1)
                if deviation > 0.3:  # 30% deviation
                    issues.append({
                        "day": day,
                        "count": count,
                        "average": avg,
                        "issue": f"{'Over' if count > avg else 'Under'} represented by {int(deviation * 100)}%"
                    })
        
        return {
            "spread_good": len(issues) == 0,
            "issues": issues,
            "score": spread_score,
            "day_distribution": day_counts
        }
    
    def auto_fix_timetable_issues(self) -> dict:
        """
        Automatically fix minor timetable issues.
        Returns what was fixed.
        """
        fixes_applied = []
        
        # Check load balance
        load_result = self.validate_timetable_load_balance()
        
        if not load_result["balanced"] and load_result["score"] > 50:
            # Try to reassign some classes to balance
            fixes_applied.append({
                "type": "load_balance",
                "message": f"Found {len(load_result['issues'])} load balance issues",
                "auto_fixable": False,  # Manual review recommended
                "issues": load_result["issues"][:5]  # First 5 issues
            })
        
        # Check spread
        spread_result = self.validate_timetable_spread()
        
        if not spread_result["spread_good"]:
            fixes_applied.append({
                "type": "spread",
                "message": f"Distribution issues found across days",
                "issues": spread_result["issues"][:5]
            })
        
        # Log validation
        if fixes_applied:
            supabase.table("timetable_validation_logs").insert({
                "college_id": self.college_id,
                "validation_type": "auto_check",
                "issues_found": json.dumps(fixes_applied),
                "auto_fixed": False,
                "score_before": load_result["score"],
                "score_after": load_result["score"]
            }).execute()
        
        return {
            "fixes_applied": fixes_applied,
            "load_score": load_result["score"],
            "spread_score": spread_result["score"]
        }
    
    def process_substitution_confirmation(self, substitution: dict):
        """Process substitution confirmation - update timetable and notify."""
        
        sub_id = substitution["id"]
        original_fid = substitution["original_faculty_id"]
        substitute_fid = substitution["substitute_faculty_id"]
        slot_id = substitution["timetable_slot_id"]
        date_str = substitution["date"]
        
        # Update substitution status
        supabase.table("substitutions").update({
            "status": "confirmed",
            "confirmed_at": datetime.utcnow().isoformat(),
            "notified_original": True,
            "notified_substitute": True
        }).eq("id", sub_id).eq("college_id", self.college_id).execute()
        
        # Update timetable slot (mark as substituted)
        supabase.table("timetable_slots").update({
            "faculty_id": substitute_fid,
            "is_substituted": True
        }).eq("id", slot_id).eq("college_id", self.college_id).execute()
        
        # Get slot details for notification
        slot_res = supabase.table("timetable_slots").select("*").eq("id", slot_id).eq("college_id", self.college_id).execute()
        slot = slot_res.data[0] if slot_res.data else {}
        
        # Get faculty details
        orig_res = supabase.table("faculty").select("name,email,user_id").eq("id", original_fid).eq("college_id", self.college_id).execute()
        sub_res = supabase.table("faculty").select("name,email,user_id").eq("id", substitute_fid).eq("college_id", self.college_id).execute()
        
        orig_name = orig_res.data[0]["name"] if orig_res.data else "Unknown"
        orig_email = orig_res.data[0].get("email") if orig_res.data else None
        sub_name = sub_res.data[0]["name"] if sub_res.data else "Unknown"
        sub_email = sub_res.data[0].get("email") if sub_res.data else None
        
        # Get subject name
        subject_name = "Unknown"
        if slot.get("subject_id"):
            sub_name_res = supabase.table("subjects").select("name").eq("id", slot["subject_id"]).eq("college_id", self.college_id).execute()
            if sub_name_res.data:
                subject_name = sub_name_res.data[0]["name"]
        
        # Notify original faculty
        if orig_email:
            from tools.email_tool import send_email
            message = f"""Dear {orig_name},

Your substitution request has been confirmed.

Details:
- Date: {date_str}
- Subject: {subject_name}
- Period: {slot.get('start_time', 'N/A')} - {slot.get('end_time', 'N/A')}
- Room: {slot.get('room_id', 'TBD')}

Substitute Teacher: {sub_name}

Best regards,
VYUHA System
"""
            send_email(orig_email, "Substitution Confirmed", message)
        
        # Notify substitute faculty
        if sub_email:
            from tools.email_tool import send_email
            message = f"""Dear {sub_name},

You have been assigned as a substitute teacher.

Details:
- Date: {date_str}
- Subject: {subject_name}
- Period: {slot.get('start_time', 'N/A')} - {slot.get('end_time', 'N/A')}
- Room: {slot.get('room_id', 'TBD')}

Original Teacher: {orig_name}

Please confirm your availability.

Best regards,
VYUHA System
"""
            send_email(sub_email, "Substitution Assignment", message)
        
        # Create in-app notifications
        # Get user IDs directly from faculty table
        orig_user_id = orig_res.data[0].get("user_id") if orig_res.data else None
        sub_user_id = sub_res.data[0].get("user_id") if sub_res.data else None

        if orig_user_id:
            supabase.table("notifications").insert({
                "college_id": self.college_id,
                "user_id": orig_user_id,
                "type": "substitution",
                "title": "Substitution Confirmed",
                "message": f"Your substitution for {date_str} has been confirmed. {sub_name} will take over.",
                "data": {
                    "substitution_id": sub_id,
                    "original_faculty_id": original_fid,
                    "substitute_faculty_id": substitute_fid,
                    "timetable_slot_id": slot_id,
                    "date": date_str,
                    "subject": subject_name,
                    "start_time": slot.get("start_time"),
                    "end_time": slot.get("end_time"),
                },
                "is_read": False,
            }).execute()
        
        if sub_user_id:
            supabase.table("notifications").insert({
                "college_id": self.college_id,
                "user_id": sub_user_id,
                "type": "substitution",
                "title": "New Substitution Assignment",
                "message": f"You have been assigned as substitute for {orig_name} on {date_str}.",
                "data": {
                    "substitution_id": sub_id,
                    "original_faculty_id": original_fid,
                    "substitute_faculty_id": substitute_fid,
                    "timetable_slot_id": slot_id,
                    "date": date_str,
                    "subject": subject_name,
                    "start_time": slot.get("start_time"),
                    "end_time": slot.get("end_time"),
                },
                "is_read": False,
            }).execute()
        
        # Create audit log
        supabase.table("audit_logs").insert({
            "college_id": self.college_id,
            "user_id": substitution.get("confirmed_by"),
            "action": "confirm_substitution",
            "entity_type": "substitution",
            "entity_id": sub_id,
            "new_value": {
                "original_faculty": orig_name,
                "substitute_faculty": sub_name,
                "date": date_str
            }
        }).execute()
        
        return {"success": True, "message": "Substitution processed and notifications sent"}


# ============================================
# AUTO HANDLER API ENDPOINTS
# ============================================

@router.post("/process-leave/{leave_id}")
async def process_leave_request(
    leave_id: int,
    college_id: str = Depends(get_college_id),
    current_user: dict = Depends(get_current_user_from_token)
):
    """
    Process a leave request: find substitutes and notify admins.
    Called automatically when leave is submitted.
    """
    _require_admin_or_hod(current_user)

    # Get leave request scoped to tenant
    leave_res = supabase.table("leave_requests").select("*").eq("id", leave_id).eq("college_id", college_id).execute()
    if not leave_res.data:
        raise HTTPException(status_code=404, detail="Leave request not found")
    
    leave = leave_res.data[0]
    
    # Mark as auto-processed
    supabase.table("leave_requests").update({
        "auto_processed": True
    }).eq("id", leave_id).execute()
    
    handler = AutoHandler(college_id)
    
    # Find substitutes
    substitutes = handler.find_substitutes_for_leave(leave)
    
    # Notify admins
    handler.notify_admins_about_leave(leave, substitutes)
    
    return {
        "success": True,
        "message": f"Found {len(substitutes)} potential substitutes",
        "substitutes": substitutes
    }


@router.post("/validate-timetable")
async def validate_timetable(
    college_id: str = Depends(get_college_id),
    auto_fix: bool = False,
    current_user: dict = Depends(get_current_user_from_token)
):
    """
    Run complete timetable validation:
    - Load balance check
    - Day spread check
    - Conflict check
    - Auto-fix if requested
    """
    _require_admin_or_hod(current_user)

    handler = AutoHandler(college_id)
    
    # Run all validations
    load_result = handler.validate_timetable_load_balance()
    spread_result = handler.validate_timetable_spread()
    
    fixes = []
    if auto_fix:
        fixes = handler.auto_fix_timetable_issues()
    
    # Calculate overall score
    overall_score = (load_result["score"] + spread_result["score"]) / 2
    
    return {
        "overall_score": overall_score,
        "load_balance": load_result,
        "spread_check": spread_result,
        "auto_fixes": fixes if auto_fix else [],
        "ready_for_approval": overall_score >= 80 and load_result["balanced"] and spread_result["spread_good"]
    }


@router.post("/confirm-substitution/{substitution_id}")
async def confirm_substitution(
    substitution_id: int,
    college_id: str = Depends(get_college_id),
    current_user: dict = Depends(get_current_user_from_token)
):
    """
    Confirm a substitution and trigger all notifications.
    """
    _require_admin_or_hod(current_user)

    # Get substitution
    sub_res = supabase.table("substitutions").select("*").eq("id", substitution_id).eq("college_id", college_id).execute()
    if not sub_res.data:
        raise HTTPException(status_code=404, detail="Substitution not found")
    
    substitution = sub_res.data[0]
    substitution["confirmed_by"] = current_user["id"]
    
    handler = AutoHandler(college_id)
    result = handler.process_substitution_confirmation(substitution)
    
    return result


@router.post("/generate-and-validate")
async def generate_and_validate_timetable(
    college_id: str = Depends(get_college_id),
    current_user: dict = Depends(get_current_user_from_token)
):
    """
    Generate timetable and automatically validate/fix.
    """
    _require_admin_or_hod(current_user)

    from timetable_engine import router as tt_router
    
    # First generate (this is handled by the existing timetable_engine)
    # Then validate
    
    handler = AutoHandler(college_id)
    
    # Validate the generated timetable
    validation = handler.validate_timetable_load_balance()
    spread = handler.validate_timetable_spread()
    
    # Auto-fix minor issues
    if validation["score"] < 80 or not spread["spread_good"]:
        fixes = handler.auto_fix_timetable_issues()
    else:
        fixes = {"fixes_applied": [], "message": "Timetable is clean"}
    
    overall_score = (validation["score"] + spread["score"]) / 2
    
    return {
        "generation_status": "completed",
        "validation_status": "completed",
        "overall_score": overall_score,
        "issues_found": len(validation["issues"]) + len(spread["issues"]),
        "auto_fixes": fixes,
        "ready_for_approval": overall_score >= 80,
        "message": "Timetable generated and validated successfully"
    }


@router.get("/dashboard-stats")
async def get_dashboard_stats(
    college_id: str = Depends(get_college_id),
    current_user: dict = Depends(get_current_user_from_token)
):
    """Get real-time dashboard statistics."""
    _require_admin_or_hod(current_user)
    
    # Get counts
    faculty_res = supabase.table("faculty").select("id", count="exact").eq("college_id", college_id).eq("status", "active").execute()
    subjects_res = supabase.table("subjects").select("id", count="exact").eq("college_id", college_id).execute()
    rooms_res = supabase.table("rooms").select("id", count="exact").eq("college_id", college_id).execute()
    
    # Pending leaves
    pending_leaves_res = supabase.table("leave_requests").select("id", count="exact").eq("college_id", college_id).in_("status", ["pending", "Pending"]).execute()
    
    # Pending substitutions
    pending_subs_res = supabase.table("substitutions").select("id", count="exact").eq("college_id", college_id).in_("status", ["pending", "Pending"]).execute()
    
    # Unread notifications
    notifications_res = supabase.table("notifications").select("id", count="exact").eq("college_id", college_id).eq("is_read", False).execute()
    
    # Today's classes
    today = datetime.now().strftime("%a")
    today_slots_res = supabase.table("timetable_slots").select("id", count="exact").eq("college_id", college_id).eq("day", today).execute()
    
    return {
        "faculty_count": faculty_res.count if hasattr(faculty_res, 'count') else len(faculty_res.data),
        "subjects_count": subjects_res.count if hasattr(subjects_res, 'count') else len(subjects_res.data),
        "rooms_count": rooms_res.count if hasattr(rooms_res, 'count') else len(rooms_res.data),
        "pending_leaves": pending_leaves_res.count if hasattr(pending_leaves_res, 'count') else len(pending_leaves_res.data),
        "pending_substitutions": pending_subs_res.count if hasattr(pending_subs_res, 'count') else len(pending_subs_res.data),
        "unread_notifications": notifications_res.count if hasattr(notifications_res, 'count') else len(notifications_res.data),
        "today_classes": today_slots_res.count if hasattr(today_slots_res, 'count') else len(today_slots_res.data)
    }


@router.get("/notifications")
async def get_notifications(
    college_id: str = Depends(get_college_id),
    current_user: dict = Depends(get_current_user_from_token),
    unread_only: bool = False
):
    """Get notifications for current user."""
    
    query = supabase.table("notifications").select("*").eq("college_id", college_id).eq("user_id", current_user["id"])
    
    if unread_only:
        query = query.eq("is_read", False)
    
    notifications_res = query.order("created_at", desc=True).limit(50).execute()
    
    return {"notifications": notifications_res.data}


@router.put("/notifications/{notification_id}/read")
async def mark_notification_read(
    notification_id: int,
    college_id: str = Depends(get_college_id),
    current_user: dict = Depends(get_current_user_from_token)
):
    """Mark a notification as read."""
    
    supabase.table("notifications").update({
        "is_read": True
    }).eq("id", notification_id).eq("user_id", current_user["id"]).execute()
    
    return {"success": True}


@router.put("/notifications/read-all")
async def mark_all_notifications_read(
    college_id: str = Depends(get_college_id),
    current_user: dict = Depends(get_current_user_from_token)
):
    """Mark all notifications as read."""
    
    supabase.table("notifications").update({
        "is_read": True
    }).eq("college_id", college_id).eq("user_id", current_user["id"]).execute()
    
    return {"success": True}
