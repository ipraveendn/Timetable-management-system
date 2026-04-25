import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# 1. Setup Mock Environment
sys.path.append(os.path.join(os.getcwd(), 'backend'))

mock_supabase = MagicMock()

# Mock the database module globally
import database
database.supabase = mock_supabase

from auto_handler import AutoHandler
from timetable_engine import calculate_slots

class TestVyuhalogic(unittest.TestCase):

    def setUp(self):
        self.college_id = "MOCK_COLLEGE"
        self.handler = AutoHandler(self.college_id)
        mock_supabase.reset_mock()

    def test_calculate_slots(self):
        """Verify dynamic time slot generation."""
        # Test 9:00 AM start, 4 slots, 60 mins duration
        slots = calculate_slots("09:00", 4, 60)
        self.assertEqual(slots, ["09:00", "10:00", "11:00", "12:00"])
        
        # Test 8:30 AM start, 3 slots, 45 mins duration
        slots = calculate_slots("08:30", 3, 45)
        self.assertEqual(slots, ["08:30", "09:15", "10:00"])

    def test_multi_slot_substitution_logic(self):
        """
        Verify that AutoHandler correctly identifies ALL slots for a leave
        and finds substitutes for each.
        """
        # Mock Leave Request
        leave_request = {
            "id": 1,
            "faculty_id": "FAC_A",
            "leave_date": "2026-04-06" # A Monday
        }
        
        # Mock Affected Slots (2 slots on Monday)
        mock_slots = [
            {"id": 101, "day": "Mon", "start_time": "09:00", "end_time": "10:00", "subject_id": "SUB_1", "faculty_id": "FAC_A"},
            {"id": 102, "day": "Mon", "start_time": "11:00", "end_time": "12:00", "subject_id": "SUB_2", "faculty_id": "FAC_A"}
        ]
        
        # Mocking Supabase calls inside get_affected_slots_for_leave
        mock_supabase.table().select().eq().eq().eq().execute.return_value = MagicMock(data=mock_slots)
        
        # Mocking finding substitutes for each slot
        # Slot 101 substitutes
        sub_1 = [{"faculty_id": "FAC_B", "name": "Prof. B", "score": 1, "current_load": 1}]
        # Slot 102 substitutes
        sub_2 = [{"faculty_id": "FAC_C", "name": "Prof. C", "score": 0, "current_load": 0}]
        
        # We need to mock the find_substitutes_for_slot call 
        # Since it's an internal call, we'll patch it or mock the DB calls it makes
        with patch.object(AutoHandler, 'find_substitutes_for_slot') as mock_find_slot:
            mock_find_slot.side_effect = [sub_1, sub_2]
            
            result = self.handler.find_substitutes_for_leave(leave_request)
            
            # VERIFICATION
            self.assertEqual(len(result["affected_slots"]), 2)
            self.assertEqual(result["affected_slots"][0]["slot_id"], 101)
            self.assertEqual(result["affected_slots"][1]["slot_id"], 102)
            self.assertEqual(result["affected_slots"][0]["substitutes"], sub_1)
            self.assertEqual(result["affected_slots"][1]["substitutes"], sub_2)
            
            print("[VERIFY] Multi-slot substitution logic: PASSED")

    def test_conflict_detection_in_substitution(self):
        """Verify that a faculty already busy at a time slot is NOT suggested as substitute."""
        slot = {"id": 999, "day": "Mon", "start_time": "10:00", "subject_id": "SUB_X", "faculty_id": "FAC_A"}
        
        # Mock faculty list
        mock_faculty = [{"id": "FAC_B", "name": "Prof B", "subjects": ["Maths"], "available_days": ["Mon"]}]
        mock_supabase.table("faculty").select().eq().neq().eq().execute.return_value = MagicMock(data=mock_faculty)
        mock_supabase.table("subjects").select().eq().execute.return_value = MagicMock(data=[{"name": "Maths"}])
        
        # Mock a conflict: Prof B already has a class on Mon at 10:00
        mock_supabase.table("timetable_slots").select().eq().eq().eq().execute.return_value = MagicMock(data=[{"id": 505}])
        
        subs = self.handler.find_substitutes_for_slot(slot)
        
        # VERIFICATION: Should be empty because FAC_B has a conflict
        self.assertEqual(len(subs), 0)
        print("[VERIFY] Conflict detection in substitution: PASSED")

if __name__ == '__main__':
    unittest.main()
