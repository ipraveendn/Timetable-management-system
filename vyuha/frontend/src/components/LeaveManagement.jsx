import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { ChevronLeft, Plus, CheckCircle, XCircle, Clock, Search, Loader2, CalendarDays, FileText } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { toast } from 'react-toastify';
import { useAuth } from '../lib/AuthProvider';
import { getLeaves, approveLeave, rejectLeave } from '../lib/api';
import './LeaveManagement.css';

const LeaveManagement = () => {
  const { user } = useAuth();
  const [leaves, setLeaves] = useState([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');
  const navigate = useNavigate();

  useEffect(() => {
    fetchLeaves();
  }, []);

  const fetchLeaves = async () => {
    try {
      setLoading(true);
      const response = await getLeaves();
      const leavesData = Array.isArray(response) ? response : (response?.leaves || []);
      const formattedLeaves = leavesData.map(l => ({
        id: l.id,
        faculty_id: l.faculty_id,
        faculty_name: l.faculty_name || 'Unknown Faculty',
        leave_date: l.leave_date,
        end_date: l.end_date,
        leave_type: l.leave_type,
        status: l.status,
        reason: l.reason || '',
        created_at: l.created_at
      }));
      setLeaves(formattedLeaves);
    } catch (error) {
      console.error('Error fetching leaves:', error);
      toast.error('Failed to load leaves');
      setLeaves([]);
    } finally {
      setLoading(false);
    }
  };



  const filteredLeaves = leaves.filter(leave => {
    const matchesSearch = leave.faculty_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      leave.leave_type.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesStatus = statusFilter === 'all' || leave.status?.toLowerCase() === statusFilter;
    return matchesSearch && matchesStatus;
  });

  const stats = {
    total: leaves.length,
    pending: leaves.filter(l => l.status?.toLowerCase() === 'pending').length,
    approved: leaves.filter(l => l.status?.toLowerCase() === 'approved').length,
    rejected: leaves.filter(l => l.status?.toLowerCase() === 'rejected').length,
  };

  const getStatusIcon = (status) => {
    switch (String(status || '').toLowerCase()) {
      case 'approved': return <CheckCircle size={20} className="status-approved" />;
      case 'rejected': return <XCircle size={20} className="status-rejected" />;
      default: return <Clock size={20} className="status-pending" />;
    }
  };

  const handleApproveLeave = async (id) => {
    try {
      await approveLeave(id);
      toast.success('Leave approved successfully');
      fetchLeaves();
    } catch (error) {
      console.error('Error approving leave:', error);
      toast.error('Failed to approve leave');
    }
  };

  const handleRejectLeave = async (id) => {
    try {
      await rejectLeave(id);
      toast.success('Leave rejected successfully');
      fetchLeaves();
    } catch (error) {
      console.error('Error rejecting leave:', error);
      toast.error('Failed to reject leave');
    }
  };

  const isAdmin = user?.role === 'admin' || user?.role === 'principal' || user?.role === 'superadmin';

  return (
    <div className="leave-management">
      <div className="page-header-section">
        <button className="back-btn" onClick={() => navigate(-1)}>
          <ChevronLeft size={20} />
          Back
        </button>
        <h1><CalendarDays size={24} style={{ verticalAlign: 'text-bottom', marginRight: 8 }} /> Leave Management</h1>
      </div>

      {/* Stats */}
      <div className="leave-stats-row">
        <div className="leave-stat-card">
          <span className="leave-stat-value" style={{ color: '#667eea' }}>{stats.total}</span>
          <span className="leave-stat-label">Total Leaves</span>
        </div>
        <div className="leave-stat-card">
          <span className="leave-stat-value" style={{ color: '#f59e0b' }}>{stats.pending}</span>
          <span className="leave-stat-label">Pending</span>
        </div>
        <div className="leave-stat-card">
          <span className="leave-stat-value" style={{ color: '#22c55e' }}>{stats.approved}</span>
          <span className="leave-stat-label">Approved</span>
        </div>
        <div className="leave-stat-card">
          <span className="leave-stat-value" style={{ color: '#ef4444' }}>{stats.rejected}</span>
          <span className="leave-stat-label">Rejected</span>
        </div>
      </div>

      {/* Filter + Search */}
      <div className="filter-row">
        {['all', 'pending', 'approved', 'rejected'].map(f => (
          <button
            key={f}
            className={`filter-tab ${statusFilter === f ? 'active' : ''}`}
            onClick={() => setStatusFilter(f)}
          >
            {f === 'all' ? 'All' : f.charAt(0).toUpperCase() + f.slice(1)}
          </button>
        ))}
      </div>

      <div className="search-bar">
        <Search size={18} />
        <input
          type="text"
          placeholder="Search by faculty name or leave type..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
        />
      </div>

      {/* Leave List */}
      <div className="leaves-list">
        {loading ? (
          <div className="loading">
            <Loader2 className="animate-spin" size={32} />
            <p>Loading leaves...</p>
          </div>
        ) : filteredLeaves.length === 0 ? (
          <div className="empty-leaves">
            <FileText size={48} />
            <h3>No leave requests found</h3>
            <p>{statusFilter !== 'all' ? `No ${statusFilter} leaves.` : 'Click "Request Leave" to submit one.'}</p>
          </div>
        ) : (
          <AnimatePresence>
            {filteredLeaves.map((leave, index) => (
              <motion.div
                key={leave.id}
                className="leave-card"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.05 }}
                whileHover={{ y: -3 }}
              >
                <div className="leave-status">{getStatusIcon(leave.status)}</div>
                <div className="leave-info">
                  <h3>{leave.faculty_name}</h3>
                  <p className="leave-detail">
                    {leave.leave_type} • {leave.leave_date} {leave.end_date && `to ${leave.end_date}`}
                  </p>
                  {leave.reason && <p className="leave-reason">"{leave.reason}"</p>}
                  <p className="leave-date">Submitted: {leave.submitted_at ? new Date(leave.submitted_at).toLocaleDateString() : 'N/A'}</p>
                </div>
                <div className={`leave-badge ${(leave.status || 'pending').toLowerCase()}`}>
                  {leave.status || 'Pending'}
                </div>
                {leave.status?.toLowerCase() === 'pending' && isAdmin && (
                  <div className="leave-actions">
                    <button
                      className="btn btn-success btn-sm"
                      onClick={() => handleApproveLeave(leave.id)}
                    >
                      <CheckCircle size={14} /> Approve
                    </button>
                    <button
                      className="btn btn-danger btn-sm"
                      onClick={() => handleRejectLeave(leave.id)}
                    >
                      <XCircle size={14} /> Reject
                    </button>
                  </div>
                )}
              </motion.div>
            ))}
          </AnimatePresence>
        )}
      </div>
    </div>
  );
};

export default LeaveManagement;