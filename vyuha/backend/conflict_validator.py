from typing import List, Dict, Any

class ConflictValidator:
    @staticmethod
    def validate(generated_slots: List[Dict[str, Any]], faculty_data: List[Dict], subjects_data: List[Dict]) -> List[str]:
        """
        Final safety gate: Returns a list of string conflict messages.
        If the list is empty, the timetable is completely conflict-free and safe to save.
        """
        conflicts = []
        
        # Lookups for O(1) checking
        faculty_lookup = {f["id"]: f for f in faculty_data}
        subject_lookup = {s["id"]: s for s in subjects_data}
        
        # Tracking dictionaries
        faculty_time_map = {}  # {faculty_id: {day: set(time_slots)}}
        room_time_map = {}     # {room_id: {day: set(time_slots)}}
        subject_count_map = {} # {subject_id: count}
        faculty_daily_load = {}# {faculty_id: {day: count}}
        
        for slot in generated_slots:
            fac_id = slot["faculty_id"]
            room_id = slot.get("room_id")
            sub_id = slot["subject_id"]
            day = slot["day"]
            time_str = slot["start_time"]
            
            # Initialization
            for map_dict, key in [(faculty_time_map, fac_id), (room_time_map, room_id), (faculty_daily_load, fac_id)]:
                if key and key not in map_dict:
                    map_dict[key] = {}
                if key and day not in map_dict[key]:
                    map_dict[key][day] = set() if map_dict is not faculty_daily_load else 0
            
            if sub_id not in subject_count_map:
                subject_count_map[sub_id] = 0
                
            # --- Check 1: Any faculty assigned to 2+ classes same time? ---
            if time_str in faculty_time_map[fac_id][day]:
                conflicts.append(f"Faculty {faculty_lookup[fac_id]['name']} is double-booked on {day} at {time_str}")
            faculty_time_map[fac_id][day].add(time_str)
            
            # --- Check 2: Any room used for 2+ classes same time? ---
            if room_id:
                if time_str in room_time_map[room_id][day]:
                    conflicts.append(f"Room {room_id} is double-booked on {day} at {time_str}")
                room_time_map[room_id][day].add(time_str)
            
            # --- Check 3: Any subject scheduled more than weekly limit? ---
            subject_count_map[sub_id] += 1
            
            # --- Check 4: Any faculty assigned to subject they don't teach? ---
            fac_subjects = faculty_lookup[fac_id].get("subjects", [])
            sub_name = subject_lookup[sub_id].get("name")
            if fac_subjects and sub_name not in fac_subjects:
                conflicts.append(f"Faculty {faculty_lookup[fac_id]['name']} assigned to {sub_name} but does not teach it.")
                
            # --- Check 5: Any faculty exceeding their daily max? ---
            faculty_daily_load[fac_id][day] += 1
        
        # Post-loop checks (Max daily limit & Subject limits)
        for fac_id, days_load in faculty_daily_load.items():
            max_allowed = faculty_lookup[fac_id].get("max_classes_per_day", 4)
            for day, count in days_load.items():
                if count > max_allowed:
                    conflicts.append(f"Faculty {faculty_lookup[fac_id]['name']} exceeded max classes ({count}/{max_allowed}) on {day}.")
                    
        for sub_id, count in subject_count_map.items():
            max_allowed = subject_lookup[sub_id].get("classes_per_week", 4)
            if count > max_allowed:
                conflicts.append(f"Subject {subject_lookup[sub_id].get('name')} scheduled {count} times (max {max_allowed} allowed).")
                
        return conflicts
