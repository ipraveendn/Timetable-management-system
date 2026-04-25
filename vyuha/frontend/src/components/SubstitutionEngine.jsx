import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { ChevronLeft, RefreshCw, Users, CheckCircle, XCircle, AlertCircle, Calendar, Clock, UserCheck } from 'lucide-react';
import { substitutionAPI, leaveAPI, normalizeApiError } from '../lib/api';
import { useAuth } from '../lib/AuthProvider';
import './SubstitutionEngine.css';

const SubstitutionEngine = () => {
  const [pendingLeaves, setPendingLeaves] = useState([]);
  const [pendingSubstitutions, setPendingSubstitutions] = useState([]);
  const [selectedLeave, setSelectedLeave] = useState(null);
  const [leaveSlots, setLeaveSlots] = useState([]);
  const [loading, setLoading] = useState(false);
  const [actionLoading, setActionLoading] = useState(null);
  const [error, setError] = useState(null);
  
  const navigate = useNavigate();
  const { isHOD } = useAuth();

  // Load initial data
  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [leavesRes, subsRes] = await Promise.all([
        leaveAPI.getPending(),
        substitutionAPI.getPending()
      ]);
      
      setPendingLeaves(leavesRes.pending_leaves || []);
      setPendingSubstitutions(subsRes.pending_substitutions || []);
    } catch (err) {
      setError(normalizeApiError(err, 'Failed to load substitution data'));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!isHOD()) {
      navigate('/dashboard');
      return;
    }
    loadData();
  }, [isHOD, navigate, loadData]);

  // Find substitutes for a specific leave request
  const handleFindSubstitutes = async (leaveId) => {
    setActionLoading(`find-${leaveId}`);
    setError(null);
    try {
      const result = await substitutionAPI.find(leaveId);
      setSelectedLeave(pendingLeaves.find(l => l.id === leaveId));
      setLeaveSlots(result.affected_slots || []);
    } catch (err) {
      setError(normalizeApiError(err, 'Failed to find substitutes'));
    } finally {
      setActionLoading(null);
    }
  };

  // Assign a substitute to a specific slot
  const handleAssign = async (slotId, substituteId) => {
    if (!selectedLeave) return;
    
    setActionLoading(`assign-${slotId}`);
    setError(null);
    try {
      await substitutionAPI.assign({
        leave_id: selectedLeave.id,
        slot_id: slotId,
        substitute_faculty_id: substituteId
      });
      
      // Refresh to show in pending substitutions
      await loadData();
      
      // Remove this slot from current view
      setLeaveSlots(prev => prev.filter(s => s.slot_id !== slotId));
      
      if (leaveSlots.length <= 1) {
        setSelectedLeave(null);
      }
    } catch (err) {
      setError(normalizeApiError(err, 'Failed to assign substitute'));
    } finally {
      setActionLoading(null);
    }
  };

  // Confirm a pending substitution
  const handleConfirm = async (subId) => {
    setActionLoading(`confirm-${subId}`);
    setError(null);
    try {
      await substitutionAPI.confirm(subId);
      await loadData();
    } catch (err) {
      setError(normalizeApiError(err, 'Failed to confirm substitution'));
    } finally {
      setActionLoading(null);
    }
  };

  if (loading) {
    return (
      <div className="loading-container">
        <RefreshCw size={40} className="spin" />
        <p>Loading Substitution System...</p>
      </div>
    );
  }

  return (
    <div className="substitution-engine">
      <div className="page-header-section">
        <button className="back-btn" onClick={() => navigate('/dashboard')}>
          <ChevronLeft size={20} />
          Back to Dashboard
        </button>
        <h1>Substitution Engine</h1>
        <button className="refresh-btn" onClick={loadData}>
          <RefreshCw size={18} />
          Refresh
        </button>
      </div>

      {error && (
        <div className="error-banner">
          <AlertCircle size={20} />
          <span>{error}</span>
          <button onClick={() => setError(null)}>×</button>
        </div>
      )}

      {/* STEP 1: Process Pending Leaves */}
      <section className="engine-section">
        <h2><Calendar size={20} /> Pending Leaves (Needs Coverage)</h2>
        {pendingLeaves.length === 0 ? (
          <div className="empty-state">
            <CheckCircle size={40} color="#10b981" />
            <p>All current leaves are being processed or covered.</p>
          </div>
        ) : (
          <div className="leaves-grid">
            {pendingLeaves.map(leave => (
              <div key={leave.id} className={`leave-card ${selectedLeave?.id === leave.id ? 'selected' : ''}`}>
                <div className="leave-header">
                  <span className="fac-name">{leave.faculty_name}</span>
                  <span className="leave-type">{leave.leave_type}</span>
                </div>
                <div className="leave-body">
                  <div className="info-row">
                    <Calendar size={14} /> <span>{leave.leave_date}</span>
                  </div>
                  <div className="info-row">
                    <Info size={14} /> <span>Reason: {leave.reason || 'Not specified'}</span>
                  </div>
                </div>
                <button 
                  className="find-btn" 
                  onClick={() => handleFindSubstitutes(leave.id)}
                  disabled={actionLoading === `find-${leave.id}`}
                >
                  {actionLoading === `find-${leave.id}` ? 'Analyzing...' : 'Find Substitutes'}
                </button>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* STEP 2: Assign Substitutes per Slot */}
      {selectedLeave && (
        <section className="engine-section slot-analysis">
          <div className="section-header">
            <h2><Clock size={20} /> Slots for {selectedLeave.faculty_name} on {selectedLeave.leave_date}</h2>
            <button className="close-btn" onClick={() => setSelectedLeave(null)}>Close Analysis</button>
          </div>
          
          <div className="slots-list">
            {leaveSlots.length === 0 ? (
              <p className="no-slots">No active classes found for this teacher on this day.</p>
            ) : (
              leaveSlots.map(slot => (
                <div key={slot.slot_id} className="slot-card">
                  <div className="slot-time">
                    <Clock size={16} />
                    <span>{slot.start_time} - {slot.end_time}</span>
                  </div>
                  
                  <div className="sub-options">
                    <h3>Suggested Substitutes:</h3>
                    {slot.substitutes.length === 0 ? (
                      <p className="no-sub-found">No eligible substitutes found for this time slot.</p>
                    ) : (
                      <div className="subs-row">
                        {slot.substitutes.map(sub => (
                          <div key={sub.faculty_id} className="sub-option-card">
                            <span className="sub-name">{sub.name}</span>
                            <span className="sub-load">Load: {sub.current_load} classes</span>
                            <button 
                              className="assign-btn"
                              onClick={() => handleAssign(slot.slot_id, sub.faculty_id)}
                              disabled={actionLoading === `assign-${slot.slot_id}`}
                            >
                              {actionLoading === `assign-${slot.slot_id}` ? 'Assigning...' : 'Assign'}
                            </button>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>
        </section>
      )}

      {/* STEP 3: Confirm Pending Substitutions */}
      <section className="engine-section">
        <h2><UserCheck size={20} /> Awaiting Confirmation</h2>
        {pendingSubstitutions.length === 0 ? (
          <div className="empty-state">
            <p>No substitutions are currently awaiting confirmation.</p>
          </div>
        ) : (
          <div className="subs-log-list">
            {pendingSubstitutions.map(sub => (
              <div key={sub.id} className="sub-log-item">
                <div className="sub-pair">
                  <span className="orig">{sub.original_faculty}</span>
                  <span className="arrow">→</span>
                  <span className="repl">{sub.substitute_faculty}</span>
                </div>
                <div className="sub-meta">
                  <span>{sub.date}</span>
                  <span>{sub.time}</span>
                </div>
                <button 
                  className="confirm-btn"
                  onClick={() => handleConfirm(sub.id)}
                  disabled={actionLoading === `confirm-${sub.id}`}
                >
                  {actionLoading === `confirm-${sub.id}` ? 'Processing...' : 'Confirm Duty'}
                </button>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
};

export default SubstitutionEngine;
