import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  Users, Plus, Search, Shield, UserCheck, UserX,
  ChevronLeft, Loader2, CheckCircle, XCircle, Clock
} from 'lucide-react';
import { useAuth } from '../lib/AuthProvider';
import { authAPI } from '../lib/api';
import { toast } from 'react-toastify';
import './UserManagement.css';

const UserManagement = () => {
  const { isAdmin } = useAuth();
  const navigate = useNavigate();
  
  const [users, setUsers] = useState([]);
  const [pendingUsers, setPendingUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [filter, setFilter] = useState('all');
  const [actionLoading, setActionLoading] = useState(null);
  const [showRejectModal, setShowRejectModal] = useState(false);
  const [rejectTargetId, setRejectTargetId] = useState(null);
  const [rejectReason, setRejectReason] = useState('');
  const [showInviteModal, setShowInviteModal] = useState(false);
  const [inviteForm, setInviteForm] = useState({
    name: '',
    email: '',
    temporary_password: '',
  });

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      const [usersRes, pendingRes] = await Promise.all([
        authAPI.getUsers(),
        authAPI.getPendingUsers()
      ]);
      setUsers(usersRes.users || []);
      setPendingUsers(pendingRes.pending_users || []);
    } catch (error) {
      console.error('Error fetching data:', error);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!isAdmin()) {
      navigate('/dashboard');
      return;
    }
    fetchData();
  }, [isAdmin, navigate, fetchData]);

  const handleApproveUser = async (pendingId) => {
    try {
      setActionLoading(pendingId);
      await authAPI.approveUser(pendingId);
      fetchData();
    } catch (error) {
      console.error('Error approving user:', error);
    } finally {
      setActionLoading(null);
    }
  };

  const openRejectModal = (pendingId) => {
    setRejectTargetId(pendingId);
    setRejectReason('');
    setShowRejectModal(true);
  };

  const handleRejectUser = async () => {
    if (!rejectTargetId) return;
    try {
      setActionLoading(rejectTargetId);
      await authAPI.rejectUser(rejectTargetId, rejectReason.trim());
      await fetchData();
      setShowRejectModal(false);
      setRejectTargetId(null);
      toast.success('User rejected successfully.');
    } catch (error) {
      console.error('Error rejecting user:', error);
      toast.error(error.response?.data?.detail || 'Failed to reject user');
    } finally {
      setActionLoading(null);
    }
  };

  const handleChangeRole = async (userId, newRole) => {
    try {
      setActionLoading(userId);
      await authAPI.changeUserRole(userId, newRole);
      fetchData();
    } catch (error) {
      console.error('Error changing role:', error);
      toast.error(error.response?.data?.detail || 'Failed to change role');
    } finally {
      setActionLoading(null);
    }
  };

  const handleChangeStatus = async (userId, newStatus) => {
    try {
      setActionLoading(userId);
      await authAPI.changeUserStatus(userId, newStatus);
      fetchData();
    } catch (error) {
      console.error('Error changing status:', error);
      toast.error(error.response?.data?.detail || 'Failed to change status');
    } finally {
      setActionLoading(null);
    }
  };

  const openInviteModal = () => {
    setInviteForm({
      name: '',
      email: '',
      temporary_password: '',
    });
    setShowInviteModal(true);
  };

  const handleInviteUser = async (e) => {
    e.preventDefault();
    const payload = {
      name: inviteForm.name.trim(),
      email: inviteForm.email.trim(),
      role: 'faculty',
      temporary_password: inviteForm.temporary_password,
    };
    if (!payload.name || !payload.email || !payload.temporary_password) {
      toast.error('All fields are required.');
      return;
    }
    if (payload.temporary_password.length < 8) {
      toast.error('Temporary password must be at least 8 characters.');
      return;
    }
    try {
      setActionLoading('invite');
      await authAPI.inviteUser(payload);
      await fetchData();
      setShowInviteModal(false);
      toast.success('Teacher invited successfully.');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to invite teacher');
    } finally {
      setActionLoading(null);
    }
  };

  const filteredUsers = users.filter(u => {
    const matchesSearch = u.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
                         u.email.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesFilter = filter === 'all' || u.role === filter || u.status === filter;
    return matchesSearch && matchesFilter;
  });

  const getRoleBadgeColor = (role) => {
    switch (role) {
      case 'admin': return '#ef4444';
      case 'principal': return '#f59e0b';
      case 'faculty': return '#3b82f6';
      default: return '#6b7280';
    }
  };

  const getStatusBadgeColor = (status) => {
    switch (status) {
      case 'active': return '#22c55e';
      case 'inactive': return '#6b7280';
      case 'suspended': return '#ef4444';
      default: return '#6b7280';
    }
  };

  if (loading) {
    return (
      <div className="user-management-loading">
        <Loader2 className="animate-spin" size={48} />
        <p>Loading users...</p>
      </div>
    );
  }

  return (
    <div className="user-management">
      <div className="page-header-section">
        <button className="back-btn" onClick={() => navigate('/dashboard')}>
          <ChevronLeft size={20} />
          Back
        </button>
        <h1><Users size={24} /> User Management</h1>
        <button className="btn btn-primary" onClick={openInviteModal} disabled={actionLoading === 'invite'}>
          <Plus size={18} />
          {actionLoading === 'invite' ? 'Inviting...' : 'Invite Teacher'}
        </button>
      </div>

      {/* Pending Users Section */}
      {pendingUsers.length > 0 && (
        <div className="pending-section">
          <h2><Clock size={20} /> Pending Approvals ({pendingUsers.length})</h2>
          <div className="pending-grid">
            {pendingUsers.map((pending, index) => (
              <motion.div
                key={pending.id}
                className="pending-card"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.05 }}
              >
                <div className="pending-info">
                  <h3>{pending.name}</h3>
                  <p className="email">{pending.email}</p>
                  <div className="pending-meta">
                    <span className="role-badge" style={{ background: getRoleBadgeColor(pending.requested_role) }}>
                      {pending.requested_role}
                    </span>
                    <span className="department">{pending.department || 'No Department'}</span>
                  </div>
                  <p className="submitted-at">
                    Submitted: {new Date(pending.created_at).toLocaleDateString()}
                  </p>
                </div>
                <div className="pending-actions">
                  <button
                    className="btn btn-success"
                    onClick={() => handleApproveUser(pending.id)}
                    disabled={actionLoading === pending.id}
                  >
                    {actionLoading === pending.id ? (
                      <Loader2 className="animate-spin" size={16} />
                    ) : (
                      <CheckCircle size={16} />
                    )}
                    Approve
                  </button>
                  <button
                    className="btn btn-danger"
                    onClick={() => openRejectModal(pending.id)}
                    disabled={actionLoading === pending.id}
                  >
                    <XCircle size={16} />
                    Reject
                  </button>
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      )}

      {/* Search and Filter */}
      <div className="search-filter-bar">
        <div className="search-input">
          <Search size={18} />
          <input
            type="text"
            placeholder="Search users..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>
        <div className="filter-tabs">
          <button className={filter === 'all' ? 'active' : ''} onClick={() => setFilter('all')}>
            All
          </button>
          <button className={filter === 'admin' ? 'active' : ''} onClick={() => setFilter('admin')}>
            <Shield size={14} /> Admin
          </button>
          <button className={filter === 'principal' ? 'active' : ''} onClick={() => setFilter('principal')}>
            Principal
          </button>
          <button className={filter === 'faculty' ? 'active' : ''} onClick={() => setFilter('faculty')}>
            Faculty
          </button>
        </div>
      </div>

      {/* Users Grid */}
      <div className="users-grid">
        {filteredUsers.map((u, index) => (
          <motion.div
            key={u.id}
            className="user-card"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.05 }}
          >
            <div className="user-header">
              <div className="user-avatar">
                {u.name.charAt(0).toUpperCase()}
              </div>
              <div className="user-main">
                <h3>{u.name}</h3>
                <p className="email">{u.email}</p>
              </div>
              <div className="status-badge" style={{ background: getStatusBadgeColor(u.status) }}>
                {u.status}
              </div>
            </div>
            
            <div className="user-details">
              <div className="detail-row">
                <span className="label">Role:</span>
                <select
                  value={u.role}
                  onChange={(e) => handleChangeRole(u.id, e.target.value)}
                  disabled={actionLoading === u.id || u.role === 'superadmin'}
                  className="role-select"
                  style={{ borderColor: getRoleBadgeColor(u.role) }}
                >
                  <option value="admin">Admin</option>
                  <option value="principal">Principal</option>
                  <option value="faculty">Faculty</option>
                </select>
              </div>
              <div className="detail-row">
                <span className="label">Department:</span>
                <span>{u.department || 'N/A'}</span>
              </div>
              <div className="detail-row">
                <span className="label">Employee ID:</span>
                <span>{u.employee_id || 'N/A'}</span>
              </div>
              <div className="detail-row">
                <span className="label">Last Login:</span>
                <span>{u.last_login ? new Date(u.last_login).toLocaleString() : 'Never'}</span>
              </div>
            </div>

            <div className="user-actions">
              {u.status === 'active' ? (
                <button
                  className="action-btn danger"
                  onClick={() => handleChangeStatus(u.id, 'suspended')}
                  disabled={actionLoading === u.id || u.role === 'superadmin'}
                  title="Suspend User"
                >
                  <UserX size={16} />
                </button>
              ) : (
                <button
                  className="action-btn success"
                  onClick={() => handleChangeStatus(u.id, 'active')}
                  disabled={actionLoading === u.id}
                  title="Activate User"
                >
                  <UserCheck size={16} />
                </button>
              )}
            </div>
          </motion.div>
        ))}
      </div>

      {filteredUsers.length === 0 && (
        <div className="empty-state">
          <Users size={48} />
          <h3>No users found</h3>
          <p>Try adjusting your search or filter</p>
        </div>
      )}

      {showInviteModal && (
        <div className="um-modal-overlay" onClick={() => setShowInviteModal(false)}>
          <div className="um-modal" onClick={(e) => e.stopPropagation()}>
            <h3>Invite Teacher</h3>
            <form onSubmit={handleInviteUser} className="um-modal-form">
              <label>
                Name
                <input
                  type="text"
                  value={inviteForm.name}
                  onChange={(e) => setInviteForm((prev) => ({ ...prev, name: e.target.value }))}
                  required
                />
              </label>
              <label>
                Email
                <input
                  type="email"
                  value={inviteForm.email}
                  onChange={(e) => setInviteForm((prev) => ({ ...prev, email: e.target.value }))}
                  required
                />
              </label>
              <label>
                Temporary Password
                <input
                  type="password"
                  minLength={8}
                  value={inviteForm.temporary_password}
                  onChange={(e) => setInviteForm((prev) => ({ ...prev, temporary_password: e.target.value }))}
                  required
                />
              </label>
              <div className="um-modal-actions">
                <button type="button" className="btn btn-secondary" onClick={() => setShowInviteModal(false)}>
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary" disabled={actionLoading === 'invite'}>
                  {actionLoading === 'invite' ? 'Inviting...' : 'Invite'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {showRejectModal && (
        <div className="um-modal-overlay" onClick={() => setShowRejectModal(false)}>
          <div className="um-modal" onClick={(e) => e.stopPropagation()}>
            <h3>Reject User</h3>
            <p>Optionally provide a reason to include in the rejection response.</p>
            <textarea
              rows={4}
              value={rejectReason}
              onChange={(e) => setRejectReason(e.target.value)}
              placeholder="Reason (optional)"
            />
            <div className="um-modal-actions">
              <button type="button" className="btn btn-secondary" onClick={() => setShowRejectModal(false)}>
                Cancel
              </button>
              <button type="button" className="btn btn-danger" onClick={handleRejectUser} disabled={actionLoading === rejectTargetId}>
                {actionLoading === rejectTargetId ? 'Rejecting...' : 'Reject User'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default UserManagement;
