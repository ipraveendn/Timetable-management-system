from pydantic import BaseModel
from typing import List, Optional

class Faculty(BaseModel):
    name: str
    employee_id: str
    email: str
    subjects: List[str]
    semesters: List[int]
    max_classes_per_day: int
    available_days: List[str]
    department: str

class Subject(BaseModel):
    name: str
    semester: int
    classes_per_week: int
    room_type_required: str
    duration_minutes: int

class Room(BaseModel):
    room_code: str
    room_name: str
    capacity: int
    room_type: str
    available_days: List[str]

class TimetableSlot(BaseModel):
    semester: int
    day: str
    start_time: str
    end_time: str
    subject_id: str
    faculty_id: str
    room_id: str
    is_substituted: bool = False

class LeaveRequest(BaseModel):
    faculty_id: str
    leave_date: str
    leave_type: str
    status: str = "Pending"

class Substitution(BaseModel):
    id: Optional[str] = None # Added Optional ID since it might be queried
    original_faculty_id: str
    substitute_faculty_id: str
    timetable_slot_id: str
    date: str
    status: str = "Pending"
