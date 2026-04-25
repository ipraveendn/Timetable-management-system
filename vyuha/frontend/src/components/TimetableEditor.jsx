import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  ChevronLeft,
  Plus,
  Trash2,
  Save,
  X,
  Users,
  DoorOpen,
  Loader2,
  Sparkles
} from 'lucide-react';
import { motion } from 'framer-motion';
import { getFacultyTimetable, generateTimetable, getFaculty, getSubjects, getRooms } from '../lib/api';
import './TimetableEditor.css';

const TimetableEditor = () => {
  const [selectedFacultyId, setSelectedFacultyId] = useState('');
  const [timetable, setTimetable] = useState({});
  const [loading, setLoading] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [selectedSlot, setSelectedSlot] = useState(null);
  const [facultyList, setFacultyList] = useState([]);
  const [subjectsList, setSubjectsList] = useState([]);
  const [roomsList, setRoomsList] = useState([]);
  
  const days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
  const timeSlots = [
    '08:00', '09:00', '10:00', '11:00', '12:00', 
    '13:00', '14:00', '15:00', '16:00', '17:00'
  ];

  const navigate = useNavigate();

  const fetchTimetable = useCallback(async () => {
    setLoading(true);
    try {
      const response = await getFacultyTimetable(selectedFacultyId);
      const slots = response.timetable || [];
      
      const facultyMap = {};
      facultyList.forEach(f => facultyMap[f.id] = f.name);
      
      const subjectMap = {};
      subjectsList.forEach(s => subjectMap[s.id] = s.name);
      
      const roomMap = {};
      roomsList.forEach(r => roomMap[r.id] = r.name);

      const formatted = {};
      slots.forEach(slot => {
        if (!formatted[slot.day]) formatted[slot.day] = {};
        const timeKey = slot.start_time ? slot.start_time.substring(0, 5) : null;
        if (timeKey) {
          formatted[slot.day][timeKey] = {
            id: slot.id,
            subject: subjectMap[slot.subject_id] || 'Unknown',
            faculty: facultyMap[slot.faculty_id] || 'Unknown',
            room: roomMap[slot.room_id] || 'Unknown',
            isSubstituted: slot.is_substituted
          };
        }
      });
      setTimetable(formatted);
    } catch (error) {
      console.error('Error fetching timetable:', error);
      setTimetable({});
    } finally {
      setLoading(false);
    }
  }, [selectedFacultyId, facultyList, subjectsList, roomsList]);

  const fetchFaculty = useCallback(async () => {
    try {
      const response = await getFaculty();
      const facultyData = Array.isArray(response) ? response.map(f => ({
        id: f.id,
        name: f.name
      })) : response.data?.map(f => ({
        id: f.id,
        name: f.name
      })) || [];
      setFacultyList(facultyData);
    } catch (error) {
      console.error('Error fetching faculty:', error);
      setFacultyList([]);
    }
  }, []);

  const fetchSubjects = useCallback(async () => {
    try {
      const response = await getSubjects();
      const subjectsData = Array.isArray(response) ? response.map(s => ({
        id: s.id,
        name: s.name
      })) : response.data?.map(s => ({
        id: s.id,
        name: s.name
      })) || [];
      setSubjectsList(subjectsData);
    } catch (error) {
      console.error('Error fetching subjects:', error);
      setSubjectsList([]);
    }
  }, []);

  const fetchRooms = useCallback(async () => {
    try {
      const response = await getRooms();
      const roomsData = Array.isArray(response) ? response.map(r => ({
        id: r.id,
        name: r.room_name || r.name
      })) : response.data?.map(r => ({
        id: r.id,
        name: r.room_name || r.name
      })) || [];
      setRoomsList(roomsData);
    } catch (error) {
      console.error('Error fetching rooms:', error);
      setRoomsList([]);
    }
  }, []);

  useEffect(() => {
    fetchFaculty();
    fetchSubjects();
    fetchRooms();
  }, [fetchFaculty, fetchSubjects, fetchRooms]);

  useEffect(() => {
    if (selectedFacultyId && facultyList.length && subjectsList.length && roomsList.length) {
      fetchTimetable();
    } else {
      setTimetable({});
    }
  }, [selectedFacultyId, facultyList, subjectsList, roomsList, fetchTimetable]);

  const handleGenerateTimetable = async () => {
    setLoading(true);
    try {
      await generateTimetable();
      if (selectedFacultyId) {
        await fetchTimetable();
      }
    } catch (error) {
      console.error('Error generating timetable:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleCellClick = (day, time) => {
    if (!selectedFacultyId) return;
    setSelectedSlot({ day, time, ...timetable[day]?.[time] });
    setShowEditModal(true);
  };

  const handleSaveSlot = async () => {
    try {
      // Logic to actually save would go here if backend supported updating single slots.
      // For now, close modal.
      setShowEditModal(false);
      await fetchTimetable();
    } catch (error) {
      console.error('Error saving slot:', error);
    }
  };

  const handleDeleteSlot = async () => {
    try {
      // Deletion logic would go here.
      setShowEditModal(false);
      await fetchTimetable();
    } catch (error) {
      console.error('Error deleting slot:', error);
    }
  };

  return (
    <div className="timetable-editor">
      {/* Header */}
      <div className="timetable-header">
        <button className="back-btn" onClick={() => navigate('/dashboard')}>
          <ChevronLeft size={20} />
          Back to Dashboard
        </button>
        <h1>Timetable Editor</h1>
      </div>

      {/* Controls */}
      <div className="timetable-controls">
        <div className="semester-selector">
          <label>View Faculty Timetable:</label>
          <select 
            value={selectedFacultyId} 
            onChange={(e) => setSelectedFacultyId(e.target.value)}
          >
            <option value="">-- Select Faculty --</option>
            {facultyList.map(f => (
              <option key={f.id} value={f.id}>{f.name}</option>
            ))}
          </select>
        </div>

        <div className="action-buttons">
          <button 
            className="btn btn-primary"
            onClick={handleGenerateTimetable}
          >
            <Sparkles size={18} />
            Generate All Timetables
          </button>
        </div>
      </div>

      {/* Timetable Grid */}
      <div className="timetable-grid-container">
        {!selectedFacultyId ? (
          <div className="select-prompt">
            <Users size={48} className="prompt-icon" />
            <h2>Select a Faculty Member</h2>
            <p>Admin security rule: You cannot view all combined timetables. Please select an individual faculty member to view and edit their schedule.</p>
          </div>
        ) : loading ? (
          <div className="loading">
            <Loader2 className="animate-spin" size={32} />
            <p>Loading timetable...</p>
          </div>
        ) : (
          <motion.div 
            className="timetable-grid"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.5 }}
          >
            {/* Header Row */}
            <div className="grid-header">
              <div className="time-header">Time / Day</div>
              {days.map(day => (
                <div key={day} className="day-header">{day}</div>
              ))}
            </div>

            {/* Time Slots */}
            {timeSlots.map((time, timeIndex) => (
              <motion.div 
                key={time} 
                className="grid-row"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: timeIndex * 0.05 }}
              >
                <div className="time-slot">{time}</div>
                {days.map(day => {
                  const slot = timetable[day]?.[time];
                  return (
                    <motion.div 
                      key={`${day}-${time}`}
                      className={`grid-cell ${slot ? 'occupied' : 'empty'} ${slot?.isSubstituted ? 'substituted' : ''}`}
                      onClick={() => handleCellClick(day, time)}
                      whileHover={{ scale: 1.05 }}
                      whileTap={{ scale: 0.95 }}
                    >
                      {slot ? (
                        <div className="slot-content">
                          <span className="subject">{slot.subject}</span>
                          <span className="faculty">
                            <Users size={12} />
                            {slot.faculty}
                          </span>
                          <span className="room">
                            <DoorOpen size={12} />
                            {slot.room}
                          </span>
                          {slot.isSubstituted && (
                            <span className="substituted-badge">Sub</span>
                          )}
                        </div>
                      ) : (
                        <Plus size={20} className="add-icon" />
                      )}
                    </motion.div>
                  );
                })}
              </motion.div>
            ))}
          </motion.div>
        )}
      </div>

      {/* Edit Modal */}
      {showEditModal && selectedSlot && (
        <div className="modal-overlay">
          <div className="modal">
            <div className="modal-header">
              <h3>Edit Slot - {selectedSlot.day} {selectedSlot.time}</h3>
              <button onClick={() => setShowEditModal(false)}>
                <X size={20} />
              </button>
            </div>
            <div className="modal-body">
              <div className="form-group">
                <label>Subject</label>
                <select defaultValue={selectedSlot.subject || ''}>
                  <option value="">Select Subject</option>
                  {subjectsList.map(s => (
                    <option key={s.id} value={s.name}>{s.name}</option>
                  ))}
                </select>
              </div>
              <div className="form-group">
                <label>Faculty</label>
                <select defaultValue={selectedSlot.faculty || ''}>
                  <option value="">Select Faculty</option>
                  {facultyList.map(f => (
                    <option key={f.id} value={f.name}>{f.name}</option>
                  ))}
                </select>
              </div>
              <div className="form-group">
                <label>Room</label>
                <select defaultValue={selectedSlot.room || ''}>
                  <option value="">Select Room</option>
                  {roomsList.map(r => (
                    <option key={r.id} value={r.name}>{r.name}</option>
                  ))}
                </select>
              </div>
            </div>
            <div className="modal-footer">
              {selectedSlot.subject && (
                <button 
                  className="btn btn-danger"
                  onClick={() => handleDeleteSlot(selectedSlot.day, selectedSlot.time)}
                >
                  <Trash2 size={16} />
                  Delete
                </button>
              )}
              <button 
                className="btn btn-primary"
                onClick={() => handleSaveSlot(selectedSlot)}
              >
                <Save size={16} />
                Save
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default TimetableEditor;
