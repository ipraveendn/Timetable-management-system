import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { Calendar, User, LogOut, CheckCircle2, AlertTriangle, Sparkles, BookOpen, CalendarDays } from 'lucide-react';
import { useAuth } from '../lib/AuthProvider';
import { toast } from 'react-toastify';
import { timetableAPI, getFaculty, submitLeave, getLeaves, substitutionAPI } from '../lib/api';
import NotificationDropdown from './NotificationDropdown';
import './Dashboard.css'; // Reusing global secure 3D styles

const FacultyDashboard = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [timetable, setTimetable] = useState([]);
  const [myLeaves, setMyLeaves] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [facultyData, setFacultyData] = useState(null);
  const [replacementAssignments, setReplacementAssignments] = useState([]);
  const [myCoveredClasses, setMyCoveredClasses] = useState([]);

  const [isLeaveModalOpen, setIsLeaveModalOpen] = useState(false);
  const [leaveFormData, setLeaveFormData] = useState({
    leave_date: '',
    end_date: '',
    leave_type: 'Medical',
    reason: ''
  });

  useEffect(() => {
    const fetchMyData = async () => {
      try {
        setLoading(true);
        // Resolve faculty from logged-in account: prefer user_id, fallback email.
        const listRes = await getFaculty();
        const allFaculty = listRes.faculty || listRes;
        
        let me = null;
        if (Array.isArray(allFaculty)) {
          const normalizedUserId = String(user?.id ?? '');
          me = allFaculty.find((f) => String(f.user_id ?? '') === normalizedUserId)
            || allFaculty.find((f) => f.email?.toLowerCase() === user?.email?.toLowerCase());
        }
        
        if (me) {
          setFacultyData(me);
          const scheduleRes = await timetableAPI.getFacultyTimetable(me.id);
          setTimetable(Array.isArray(scheduleRes.timetable) ? scheduleRes.timetable : []);
          
          try {
            const leavesRes = await getLeaves();
            const leavesData = Array.isArray(leavesRes) ? leavesRes : (leavesRes?.leaves || []);
            // Only show leaves for THIS faculty
            const myFilteredLeaves = leavesData.filter(l => l.faculty_id === me.id);
            setMyLeaves(myFilteredLeaves);
          } catch (e) {
            console.error("Error fetching leaves", e);
          }

          try {
            const [assignmentsRes, coveredRes] = await Promise.all([
              substitutionAPI.getMyAssignments(),
              substitutionAPI.getMyCovered(),
            ]);
            setReplacementAssignments(assignmentsRes?.assignments || []);
            setMyCoveredClasses(coveredRes?.covered || []);
          } catch (e) {
            console.error("Error fetching substitution details", e);
            setReplacementAssignments([]);
            setMyCoveredClasses([]);
          }
        } else {
          setError("Your user profile is not linked to an active faculty record. Please contact the administrator.");
        }
      } catch (err) {
        console.error(err);
        setError("Could not load your information.");
      } finally {
        setLoading(false);
      }
    };
    
    if (user?.email) {
      fetchMyData();
    }
  }, [user]);

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const handleLeaveInputChange = (e) => {
    const { name, value } = e.target;
    setLeaveFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handleLeaveSubmit = async (e) => {
    e.preventDefault();
    if (!facultyData) {
      toast.error("Faculty data not found.");
      return;
    }
    
    try {
      const payload = {
        ...leaveFormData,
        faculty_id: facultyData.id
      };
      
      if (!payload.end_date) {
        delete payload.end_date;
      }

      await submitLeave(payload);
      toast.success('Leave requested successfully');
      setIsLeaveModalOpen(false);
      setLeaveFormData({
        leave_date: '',
        end_date: '',
        leave_type: 'Medical',
        reason: ''
      });
      // Refresh leaves
      try {
        const leavesRes = await getLeaves();
        const leavesData = Array.isArray(leavesRes) ? leavesRes : (leavesRes?.leaves || []);
        // MUST FILTER HERE TOO
        const myFilteredLeaves = leavesData.filter(l => l.faculty_id === facultyData.id);
        setMyLeaves(myFilteredLeaves);
      } catch (e) {
        console.error("Error refreshing leaves", e);
      }
    } catch (error) {
      console.error('Error submitting leave:', error);
      toast.error(error.response?.data?.detail || 'Failed to submit leave');
    }
  };

  // Group timetable by day
  const groupTimetable = () => {
    const grouped = { Mon: [], Tue: [], Wed: [], Thu: [], Fri: [], Sat: [] };
    timetable.forEach(slot => {
      if (grouped[slot.day]) {
        grouped[slot.day].push(slot);
      }
    });
    // Sort slots by time
    Object.keys(grouped).forEach(day => {
      grouped[day].sort((a, b) => a.start_time.localeCompare(b.start_time));
    });
    return grouped;
  };

  const schedule = groupTimetable();

  return (
    <div className="dashboard-container-3d" style={{ flexDirection: 'column' }}>
      <div className="dashboard-bg">
        <motion.div className="bg-orb orb-1" animate={{ scale: [1, 1.2, 1], opacity: [0.3, 0.5, 0.3] }} transition={{ duration: 20, repeat: Infinity }} />
      </div>

      <nav className="dashboard-header-3d" style={{ position: 'relative', zIndex: 500, padding: '1.5rem 3rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: 'rgba(0,0,0,0.5)', backdropFilter: 'blur(10px)', borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <Sparkles style={{color: '#a78bfa'}} size={28} />
          <h2 style={{ margin: 0, fontWeight: 'bold', color: 'white' }}>Teacher Portal</h2>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '1.5rem' }}>
          <NotificationDropdown />
          <span style={{ color: 'rgba(255,255,255,0.8)' }}><User size={18} style={{ marginRight: '8px', verticalAlign: 'text-bottom' }}/> {user?.name || user?.email}</span>
           <motion.button 
             onClick={() => setIsLeaveModalOpen(true)}
             whileHover={{ scale: 1.05 }}
             style={{ padding: '0.5rem 1rem', borderRadius: '8px', cursor: 'pointer', background: 'rgba(245,158,11,0.15)', border: '1px solid rgba(245,158,11,0.5)', color: '#fde68a', fontWeight: 'bold', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
             <CalendarDays size={18} /> Request Leave
           </motion.button>
          <motion.button whileHover={{ scale: 1.05 }} onClick={handleLogout} style={{ cursor: 'pointer', padding: '0.5rem 1rem', borderRadius: '8px', background: 'rgba(239,68,68,0.2)', border: '1px solid #ef4444', color: '#fca5a5', display: 'flex', alignItems: 'center' }}>
            <LogOut size={18} style={{ marginRight: '8px' }}/> Logout
          </motion.button>
        </div>
      </nav>

      <main className="main-content-3d" style={{ position: 'relative', zIndex: 10, padding: '3rem', maxWidth: '1400px', margin: '0 auto', height: 'calc(100vh - 80px)', overflowY: 'auto' }}>
        
        {loading ? (
          <div style={{ textAlign: 'center', padding: '5rem', color: 'rgba(255,255,255,0.6)' }}>Loading your schedule...</div>
        ) : error ? (
           <div style={{ background: 'rgba(239,68,68,0.1)', border: '1px solid #ef4444', padding: '2rem', borderRadius: '16px', color: '#fca5a5' }}>
             <AlertTriangle size={32} style={{ marginBottom: '1rem' }} />
             <h3>Access Error</h3>
             <p>{error}</p>
           </div>
        ) : (
          <>
            <div className="stats-grid-3d" style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1.5rem', marginBottom: '3rem' }}>
               <div className="stat-card-3d blue" style={{ padding: '1.5rem' }}>
                 <div className="stat-info-3d">
                   <span className="stat-value-3d" style={{fontSize: '2.5rem'}}>{timetable.length}</span>
                   <span className="stat-label-3d">Classes This Week</span>
                 </div>
               </div>
               <div className="stat-card-3d green" style={{ padding: '1.5rem' }}>
                 <div className="stat-info-3d">
                   <span className="stat-value-3d" style={{fontSize: '2.5rem'}}>{facultyData?.department || 'General'}</span>
                   <span className="stat-label-3d">Department</span>
                 </div>
               </div>
               <div className="stat-card-3d purple" style={{ padding: '1.5rem', display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
                 <div className="stat-info-3d">
                    <span className="stat-value-3d" style={{fontSize: '2.5rem', color: '#a78bfa'}}>{schedule['Mon'].length > 0 ? schedule['Mon'].length : 'Off'}</span>
                   <span className="stat-label-3d">Classes Today</span>
                 </div>
               </div>
            </div>

            <div className="content-card-3d" style={{ padding: '2rem', borderRadius: '16px', background: 'glassmorphism' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem', borderBottom: '1px solid rgba(255,255,255,0.1)', paddingBottom: '1rem' }}>
                 <h3 style={{ color: 'white', margin: 0 }}>Your Weekly Master Timetable</h3>
              </div>
              
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '1.5rem' }}>
                {['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'].map(day => (
                  <div key={day} style={{ background: 'rgba(0,0,0,0.3)', borderRadius: '12px', padding: '1.5rem 1rem' }}>
                    <h4 style={{ textAlign: 'center', color: '#a78bfa', margin: '0 0 1.5rem 0', paddingBottom: '0.5rem', borderBottom: '2px solid rgba(167,139,250,0.2)' }}>{day}</h4>
                    {schedule[day].length === 0 ? (
                      <div style={{ textAlign: 'center', color: 'rgba(255,255,255,0.3)', padding: '2rem 0', fontSize: '0.9rem', fontStyle: 'italic' }}>Off Day</div>
                    ) : (
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                        {schedule[day].map((slot, i) => (
                           <motion.div whileHover={{ scale: 1.02 }} key={i} style={{ background: 'linear-gradient(135deg, rgba(124,58,237,0.15), rgba(109,40,217,0.05))', border: '1px solid rgba(124,58,237,0.3)', borderRadius: '10px', padding: '1rem', flex: 1 }}>
                             <div style={{ color: 'rgba(255,255,255,0.95)', fontWeight: 'bold', marginBottom: '6px', fontSize: '1rem' }}>{slot.start_time.slice(0,5)} - {slot.end_time.slice(0,5)}</div>
                             <div style={{ color: '#e9d5ff', display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.9rem' }}><BookOpen size={14}/> Subject <b>{slot.subject_id}</b></div>
                             {slot.room_id && <div style={{ color: 'rgba(255,255,255,0.6)', marginTop: '4px', fontSize: '0.85rem' }}>Room {slot.room_id}</div>}
                             {slot.is_substituted && <div style={{ marginTop: '0.75rem', color: '#f59e0b', fontSize: '0.8rem', fontWeight: 'bold', background: 'rgba(245,158,11,0.1)', padding: '4px 8px', borderRadius: '4px', display: 'inline-block' }}>* Substitute Duty</div>}
                           </motion.div>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>

            {replacementAssignments.length > 0 && (
              <div className="content-card-3d" style={{ marginTop: '2rem', padding: '2rem', borderRadius: '16px', background: 'rgba(34,197,94,0.06)', border: '1px solid rgba(34,197,94,0.18)' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1.5rem' }}>
                  <CheckCircle2 size={22} style={{ color: '#4ade80' }} />
                  <h3 style={{ color: 'white', margin: 0 }}>Replacement Assignments</h3>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '1rem' }}>
                  {replacementAssignments.map((assignment) => (
                    <motion.div
                      key={assignment.id}
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      style={{ background: 'rgba(0,0,0,0.24)', border: '1px solid rgba(74,222,128,0.22)', borderRadius: '12px', padding: '1.25rem' }}
                    >
                      <div style={{ color: '#bbf7d0', fontSize: '12px', fontWeight: '700', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: '0.5rem' }}>
                        Assigned Replacement
                      </div>
                      <div style={{ color: 'white', fontWeight: '700', marginBottom: '0.5rem' }}>
                        For {assignment.original_faculty_name}
                      </div>
                      <div style={{ color: 'rgba(255,255,255,0.72)', fontSize: '13px', lineHeight: 1.7 }}>
                        <div>Date: {assignment.date}</div>
                        <div>Time: {assignment.time || `${assignment.start_time || ''} - ${assignment.end_time || ''}`}</div>
                        <div>Subject: {assignment.subject || 'Unknown'}</div>
                        {assignment.room_id && <div>Room: {assignment.room_id}</div>}
                      </div>
                      <div style={{ marginTop: '0.75rem', display: 'inline-block', color: '#4ade80', fontSize: '12px', fontWeight: '700', background: 'rgba(34,197,94,0.12)', padding: '4px 8px', borderRadius: '999px', textTransform: 'uppercase' }}>
                        {assignment.status}
                      </div>
                    </motion.div>
                  ))}
                </div>
              </div>
            )}

            {myCoveredClasses.length > 0 && (
              <div className="content-card-3d" style={{ marginTop: '2rem', padding: '2rem', borderRadius: '16px', background: 'rgba(245,158,11,0.08)', border: '1px solid rgba(245,158,11,0.2)' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1.5rem' }}>
                  <Calendar size={22} style={{ color: '#fbbf24' }} />
                  <h3 style={{ color: 'white', margin: 0 }}>My Classes Covered</h3>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '1rem' }}>
                  {myCoveredClasses.map((item) => (
                    <motion.div
                      key={item.id}
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      style={{ background: 'rgba(0,0,0,0.24)', border: '1px solid rgba(245,158,11,0.26)', borderRadius: '12px', padding: '1.25rem' }}
                    >
                      <div style={{ color: '#fde68a', fontSize: '12px', fontWeight: '700', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: '0.5rem' }}>
                        Covered By Replacement
                      </div>
                      <div style={{ color: 'white', fontWeight: '700', marginBottom: '0.5rem' }}>
                        {item.substitute_faculty_name}
                      </div>
                      <div style={{ color: 'rgba(255,255,255,0.72)', fontSize: '13px', lineHeight: 1.7 }}>
                        <div>Date: {item.date}</div>
                        <div>Time: {item.time || `${item.start_time || ''} - ${item.end_time || ''}`}</div>
                        <div>Subject: {item.subject || 'Unknown'}</div>
                        {item.room_id && <div>Room: {item.room_id}</div>}
                      </div>
                      <div style={{ marginTop: '0.75rem', display: 'inline-block', color: '#fbbf24', fontSize: '12px', fontWeight: '700', background: 'rgba(245,158,11,0.14)', padding: '4px 8px', borderRadius: '999px', textTransform: 'uppercase' }}>
                        {item.status}
                      </div>
                    </motion.div>
                  ))}
                </div>
              </div>
            )}
          </>
        )}

        {/* My Leave Requests Section */}
        {!loading && !error && facultyData && (
          <div style={{ marginTop: '3rem' }}>
            <h3 style={{ color: 'white', marginBottom: '1.5rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <CalendarDays size={20} /> My Leave Requests
            </h3>
            {myLeaves.length === 0 ? (
              <div style={{ background: 'rgba(255,255,255,0.02)', border: '1px dashed rgba(255,255,255,0.1)', padding: '2rem', borderRadius: '12px', textAlign: 'center', color: 'rgba(255,255,255,0.4)' }}>
                You have not submitted any leave requests.
              </div>
            ) : (
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: '1rem' }}>
                {myLeaves.map(leave => (
                  <motion.div 
                    key={leave.id}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    style={{ background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '12px', padding: '1.5rem', position: 'relative', overflow: 'hidden' }}
                  >
                    <div style={{ position: 'absolute', top: 0, left: 0, width: '4px', height: '100%', background: leave.status === 'approved' ? '#22c55e' : leave.status === 'rejected' ? '#ef4444' : '#f59e0b' }} />
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.5rem' }}>
                      <span style={{ fontWeight: '600', color: 'white' }}>{leave.leave_type}</span>
                      <span style={{ 
                        fontSize: '11px', 
                        padding: '4px 8px', 
                        borderRadius: '20px', 
                        fontWeight: '600',
                        textTransform: 'uppercase',
                        background: leave.status === 'approved' ? 'rgba(34,197,94,0.15)' : leave.status === 'rejected' ? 'rgba(239,68,68,0.15)' : 'rgba(245,158,11,0.15)',
                        color: leave.status === 'approved' ? '#4ade80' : leave.status === 'rejected' ? '#f87171' : '#fbbf24'
                      }}>
                        {leave.status}
                      </span>
                    </div>
                    <div style={{ fontSize: '13px', color: 'rgba(255,255,255,0.6)', marginBottom: '0.5rem' }}>
                      {leave.leave_date} {leave.end_date && `to ${leave.end_date}`}
                    </div>
                    {leave.reason && (
                      <div style={{ fontSize: '13px', color: 'rgba(255,255,255,0.4)', fontStyle: 'italic' }}>
                        "{leave.reason}"
                      </div>
                    )}
                  </motion.div>
                ))}
              </div>
            )}
          </div>
        )}

      </main>

      {/* Request Leave Modal */}
      {isLeaveModalOpen && (
        <div className="modal-overlay" onClick={() => setIsLeaveModalOpen(false)} style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.7)', backdropFilter: 'blur(8px)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }}>
          <motion.div
            className="modal-content"
            onClick={e => e.stopPropagation()}
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            style={{ background: 'linear-gradient(135deg, #1a1a2e, #16213e)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '20px', padding: '32px', width: '90%', maxWidth: '480px', boxShadow: '0 25px 60px rgba(0,0,0,0.5)' }}
          >
            <h2 style={{ color: 'white', fontSize: '20px', fontWeight: '700', margin: '0 0 24px' }}>Request Leave</h2>
            <form onSubmit={handleLeaveSubmit}>
              <div className="form-group" style={{ marginBottom: '20px' }}>
                <label htmlFor="leave_type" style={{ display: 'block', fontSize: '13px', fontWeight: '600', color: 'rgba(255,255,255,0.7)', marginBottom: '8px' }}>Leave Type</label>
                <select
                  id="leave_type"
                  name="leave_type"
                  value={leaveFormData.leave_type}
                  onChange={handleLeaveInputChange}
                  required
                  style={{ width: '100%', padding: '12px 16px', background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.12)', borderRadius: '10px', color: 'white', fontSize: '14px', outline: 'none' }}
                >
                  <option value="Medical" style={{ background: '#1a1a2e', color: 'white' }}>Medical Leave</option>
                  <option value="Personal" style={{ background: '#1a1a2e', color: 'white' }}>Personal Leave</option>
                  <option value="Emergency" style={{ background: '#1a1a2e', color: 'white' }}>Emergency Leave</option>
                  <option value="Vacation" style={{ background: '#1a1a2e', color: 'white' }}>Vacation</option>
                  <option value="Maternity" style={{ background: '#1a1a2e', color: 'white' }}>Maternity Leave</option>
                  <option value="Other" style={{ background: '#1a1a2e', color: 'white' }}>Other</option>
                </select>
              </div>
              <div className="form-group" style={{ marginBottom: '20px' }}>
                <label htmlFor="leave_date" style={{ display: 'block', fontSize: '13px', fontWeight: '600', color: 'rgba(255,255,255,0.7)', marginBottom: '8px' }}>Start Date</label>
                <input
                  type="date"
                  id="leave_date"
                  name="leave_date"
                  value={leaveFormData.leave_date}
                  onChange={handleLeaveInputChange}
                  required
                  style={{ width: '100%', padding: '12px 16px', background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.12)', borderRadius: '10px', color: 'white', fontSize: '14px', outline: 'none', boxSizing: 'border-box' }}
                />
              </div>
              <div className="form-group" style={{ marginBottom: '20px' }}>
                <label htmlFor="end_date" style={{ display: 'block', fontSize: '13px', fontWeight: '600', color: 'rgba(255,255,255,0.7)', marginBottom: '8px' }}>End Date (Optional)</label>
                <input
                  type="date"
                  id="end_date"
                  name="end_date"
                  value={leaveFormData.end_date}
                  onChange={handleLeaveInputChange}
                  style={{ width: '100%', padding: '12px 16px', background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.12)', borderRadius: '10px', color: 'white', fontSize: '14px', outline: 'none', boxSizing: 'border-box' }}
                />
              </div>
              <div className="form-group" style={{ marginBottom: '20px' }}>
                <label htmlFor="reason" style={{ display: 'block', fontSize: '13px', fontWeight: '600', color: 'rgba(255,255,255,0.7)', marginBottom: '8px' }}>Reason</label>
                <textarea
                  id="reason"
                  name="reason"
                  value={leaveFormData.reason}
                  onChange={handleLeaveInputChange}
                  rows="3"
                  placeholder="Briefly describe the reason..."
                  required
                  style={{ width: '100%', padding: '12px 16px', background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.12)', borderRadius: '10px', color: 'white', fontSize: '14px', outline: 'none', resize: 'vertical', minHeight: '80px', boxSizing: 'border-box' }}
                />
              </div>
              <div className="form-actions" style={{ display: 'flex', gap: '12px', justifyContent: 'flex-end', marginTop: '24px' }}>
                <button type="button" onClick={() => setIsLeaveModalOpen(false)} style={{ background: 'rgba(255,255,255,0.08)', border: '1px solid rgba(255,255,255,0.15)', color: 'rgba(255,255,255,0.8)', padding: '10px 20px', borderRadius: '12px', fontWeight: '600', fontSize: '14px', cursor: 'pointer' }}>
                  Cancel
                </button>
                <button type="submit" style={{ background: 'linear-gradient(135deg, #7c3aed, #6d28d9)', border: 'none', color: 'white', padding: '10px 20px', borderRadius: '12px', fontWeight: '600', fontSize: '14px', cursor: 'pointer', boxShadow: '0 4px 15px rgba(124,58,237,0.3)' }}>
                  Submit Request
                </button>
              </div>
            </form>
          </motion.div>
        </div>
      )}
    </div>
  );
};

export default FacultyDashboard;
