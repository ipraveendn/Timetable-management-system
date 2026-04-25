from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from database import supabase
from dependencies import get_college_id
from auth_system import get_current_user_from_token
from auto_handler import AutoHandler

router = APIRouter(prefix="/leave", tags=["Leave Management"])

class LeaveRequest(BaseModel):
    faculty_id: int
    leave_date: str
    end_date: Optional[str] = None
    leave_type: str
    reason: Optional[str] = None
    status: str = "pending"

@router.post("/submit")
async def submit_leave(
    leave: LeaveRequest, 
    college_id: str = Depends(get_college_id),
    current_user: dict = Depends(get_current_user_from_token)
):
    """Submit a leave request and auto-process it."""
    try:
        # Insert leave request
        leave_data = {
            "college_id": college_id,
            "faculty_id": leave.faculty_id,
            "leave_date": leave.leave_date,
            "end_date": leave.end_date,
            "leave_type": leave.leave_type,
            "reason": leave.reason,
            "status": "pending",
            "submitted_at": datetime.utcnow().isoformat()
        }
        
        result = supabase.table("leave_requests").insert(leave_data).execute()
        
        if not result.data:
            raise HTTPException(status_code=500, detail="Failed to submit leave")
        
        leave_id = result.data[0]["id"]
        leave_data["id"] = leave_id
        
        # AUTO HANDLER: Process leave and find substitutes
        handler = AutoHandler(college_id)
        
        # Find substitutes
        substitutes = handler.find_substitutes_for_leave(leave_data)
        
        # Notify admins
        handler.notify_admins_about_leave(leave_data, substitutes)
        
        # Create audit log
        supabase.table("audit_logs").insert({
            "college_id": college_id,
            "user_id": current_user.get("id"),
            "action": "submit_leave",
            "entity_type": "leave_request",
            "entity_id": leave_id,
            "new_value": {
                "faculty_id": leave.faculty_id,
                "leave_date": leave.leave_date,
                "leave_type": leave.leave_type
            }
        }).execute()
        
        return {
            "message": "Leave request submitted successfully",
            "leave_id": leave_id,
            "auto_processed": True,
            "substitutes_found": len(substitutes.get("affected_slots", [])),
            "top_substitutes": substitutes.get("affected_slots", [])[:3]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error submitting leave: {str(e)}")

@router.get("/all")
async def get_all_leaves(
    college_id: str = Depends(get_college_id),
    current_user: dict = Depends(get_current_user_from_token)
):
    """Get all leave requests for the college."""
    try:
        query = supabase.table("leave_requests").select("*").eq("college_id", college_id)
        
        if current_user.get("role") not in ["admin", "principal", "superadmin"]:
            # Try by user_id first
            fac_res = supabase.table("faculty").select("id").eq("user_id", current_user["id"]).execute()
            
            # Fallback to email if user_id is not linked
            if not fac_res.data and current_user.get("email"):
                fac_res = supabase.table("faculty").select("id").ilike("email", current_user["email"]).execute()
                
            if not fac_res.data:
                return {"leaves": []}
            query = query.eq("faculty_id", fac_res.data[0]["id"])
            
        res = query.order("submitted_at", desc=True).execute()
        
        # Enrich with faculty names
        faculty_ids = list(set([l["faculty_id"] for l in res.data]))
        faculty_map = {}
        if faculty_ids:
            fac_res = supabase.table("faculty").select("id, name").in_("id", faculty_ids).execute()
            faculty_map = {f["id"]: f["name"] for f in fac_res.data}
        
        leaves = []
        for l in res.data:
            leaves.append({
                "id": l["id"],
                "faculty_id": l["faculty_id"],
                "faculty_name": faculty_map.get(l["faculty_id"], "Unknown"),
                "leave_date": l["leave_date"],
                "end_date": l.get("end_date"),
                "leave_type": l["leave_type"],
                "reason": l.get("reason"),
                "status": l["status"],
                "auto_processed": l.get("auto_processed", False),
                "submitted_at": l.get("submitted_at"),
                "reviewed_at": l.get("reviewed_at")
            })
        
        return {"leaves": leaves}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching leaves: {str(e)}")

@router.get("/pending")
async def get_pending_leaves(
    college_id: str = Depends(get_college_id),
    current_user: dict = Depends(get_current_user_from_token)
):
    """Get pending leave requests (admin only)."""
    if current_user["role"] not in ["admin", "principal", "superadmin"]:
        raise HTTPException(status_code=403, detail="Only admin or Principal can view pending leaves")
    
    try:
        res = supabase.table("leave_requests").select("*").eq("college_id", college_id).in_("status", ["pending", "Pending"]).order("submitted_at", desc=True).execute()
        return {"leaves": res.data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching pending leaves: {str(e)}")

@router.post("/approve/{leave_id}")
async def approve_leave(
    leave_id: int,
    college_id: str = Depends(get_college_id),
    current_user: dict = Depends(get_current_user_from_token)
):
    """Approve a leave request."""
    if current_user["role"] not in ["admin", "principal", "superadmin"]:
        raise HTTPException(status_code=403, detail="Only admin or Principal can approve leaves")
    
    try:
        # Update leave status
        supabase.table("leave_requests").update({
            "status": "approved",
            "approved_by": current_user["id"],
            "reviewed_at": datetime.utcnow().isoformat()
        }).eq("id", leave_id).eq("college_id", college_id).execute()
        
        # Create audit log
        supabase.table("audit_logs").insert({
            "college_id": college_id,
            "user_id": current_user["id"],
            "action": "approve_leave",
            "entity_type": "leave_request",
            "entity_id": leave_id,
            "new_value": {"status": "approved"}
        }).execute()

        # NEW: Create notification for the teacher
        # Get faculty info to find the user_id
        leave_res = supabase.table("leave_requests").select("faculty_id").eq("id", leave_id).execute()
        if leave_res.data:
            faculty_id = leave_res.data[0]["faculty_id"]
            faculty_res = supabase.table("faculty").select("user_id, name").eq("id", faculty_id).execute()
            if faculty_res.data and faculty_res.data[0].get("user_id"):
                teacher_user_id = faculty_res.data[0]["user_id"]
                teacher_name = faculty_res.data[0]["name"]
                
                supabase.table("notifications").insert({
                    "college_id": college_id,
                    "user_id": teacher_user_id,
                    "type": "leave_approved",
                    "title": "Leave Approved",
                    "message": f"Hello {teacher_name}, your leave request for {leave_id} has been approved.",
                    "is_read": False
                }).execute()

        return {"message": "Leave approved successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error approving leave: {str(e)}")

@router.post("/reject/{leave_id}")
async def reject_leave(
    leave_id: int,
    reason: str = "",
    college_id: str = Depends(get_college_id),
    current_user: dict = Depends(get_current_user_from_token)
):
    """Reject a leave request."""
    if current_user["role"] not in ["admin", "principal", "superadmin"]:
        raise HTTPException(status_code=403, detail="Only admin or Principal can reject leaves")
    
    try:
        # Update leave status
        supabase.table("leave_requests").update({
            "status": "rejected",
            "rejected_by": current_user["id"],
            "reviewed_at": datetime.utcnow().isoformat()
        }).eq("id", leave_id).eq("college_id", college_id).execute()
        
        # Create audit log
        supabase.table("audit_logs").insert({
            "college_id": college_id,
            "user_id": current_user["id"],
            "action": "reject_leave",
            "entity_type": "leave_request",
            "entity_id": leave_id,
            "new_value": {"status": "rejected", "reason": reason}
        }).execute()

        # NEW: Create notification for the teacher
        leave_res = supabase.table("leave_requests").select("faculty_id").eq("id", leave_id).execute()
        if leave_res.data:
            faculty_id = leave_res.data[0]["faculty_id"]
            faculty_res = supabase.table("faculty").select("user_id, name").eq("id", faculty_id).execute()
            if faculty_res.data and faculty_res.data[0].get("user_id"):
                teacher_user_id = faculty_res.data[0]["user_id"]
                teacher_name = faculty_res.data[0]["name"]
                
                supabase.table("notifications").insert({
                    "college_id": college_id,
                    "user_id": teacher_user_id,
                    "type": "leave_rejected",
                    "title": "Leave Rejected",
                    "message": f"Hello {teacher_name}, your leave request has been rejected. Reason: {reason or 'Not specified'}",
                    "is_read": False
                }).execute()

        return {"message": "Leave rejected"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error rejecting leave: {str(e)}")

@router.post("/cancel/{leave_id}")
async def cancel_leave(
    leave_id: int,
    college_id: str = Depends(get_college_id),
    current_user: dict = Depends(get_current_user_from_token)
):
    """Cancel a leave request (by the faculty themselves)."""
    try:
        # Verify the leave belongs to this user
        leave_res = supabase.table("leave_requests").select("*").eq("id", leave_id).eq("college_id", college_id).execute()
        
        if not leave_res.data:
            raise HTTPException(status_code=404, detail="Leave request not found")
        
        leave = leave_res.data[0]
        
        if current_user["role"] not in ["admin", "principal", "superadmin"]:
            faculty_res = supabase.table("faculty").select("id, user_id").eq("id", leave["faculty_id"]).eq("college_id", college_id).execute()
            if not faculty_res.data or faculty_res.data[0].get("user_id") != current_user["id"]:
                raise HTTPException(status_code=403, detail="You can only cancel your own leave request")

        if leave["status"] not in ["pending", "Pending", "approved", "Approved"]:
            raise HTTPException(status_code=400, detail="Cannot cancel this leave")
        
        supabase.table("leave_requests").update({
            "status": "cancelled"
        }).eq("id", leave_id).execute()
        
        return {"message": "Leave cancelled"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error cancelling leave: {str(e)}")
