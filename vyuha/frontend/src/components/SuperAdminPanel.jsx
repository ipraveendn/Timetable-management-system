import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  Building2, Users, Shield, Activity, CheckCircle, XCircle, Clock,
  ChevronRight, AlertTriangle, Plus, Search, Loader2, BarChart3
} from 'lucide-react';
import { useAuth } from '../lib/AuthProvider';
import { superadminAPI } from '../lib/api';
import './SuperAdminPanel.css';

const SuperAdminPanel = () => {
  const { logout } = useAuth();
  const navigate = useNavigate();
  
  const [colleges, setColleges] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [selectedCollege, setSelectedCollege] = useState(null);
  const [collegeDetails, setCollegeDetails] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [filter, setFilter] = useState('all'); // all, active, pending, suspended
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [actionLoading, setActionLoading] = useState(null);
  const [createLoading, setCreateLoading] = useState(false);
  const [createError, setCreateError] = useState('');
  const [panelMessage, setPanelMessage] = useState(null);
  const [suspendTargetCollegeId, setSuspendTargetCollegeId] = useState(null);
  const [createForm, setCreateForm] = useState({
    name: '',
    code: '',
    contact_email: '',
    admin_email: '',
    admin_name: '',
    admin_password: ''
  });

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [collegesRes, statsRes] = await Promise.all([
        superadminAPI.getColleges(),
        superadminAPI.getStats()
      ]);
      setColleges(collegesRes.colleges || []);
      setStats(statsRes);
    } catch (error) {
      console.error('Error fetching data:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchCollegeDetails = async (collegeId) => {
    try {
      setSelectedCollege(collegeId);
      const details = await superadminAPI.getCollegeDetails(collegeId);
      setCollegeDetails(details);
    } catch (error) {
      console.error('Error fetching college details:', error);
    }
  };

  const handleApproveCollege = async (collegeId) => {
    try {
      setActionLoading(collegeId);
      await superadminAPI.approveCollege(collegeId);
      fetchData();
      if (selectedCollege === collegeId) {
        fetchCollegeDetails(collegeId);
      }
    } catch (error) {
      console.error('Error approving college:', error);
    } finally {
      setActionLoading(null);
    }
  };

  const handleSuspendCollege = async (collegeId) => {
    try {
      setActionLoading(collegeId);
      await superadminAPI.suspendCollege(collegeId);
      await fetchData();
      if (selectedCollege === collegeId) {
        await fetchCollegeDetails(collegeId);
      }
      setPanelMessage({ type: 'success', text: `College ${collegeId} suspended.` });
    } catch (error) {
      console.error('Error suspending college:', error);
      setPanelMessage({ type: 'error', text: error.response?.data?.detail || 'Failed to suspend college' });
    } finally {
      setActionLoading(null);
    }
  };

  const resetCreateForm = () => {
    setCreateForm({
      name: '',
      code: '',
      contact_email: '',
      admin_email: '',
      admin_name: '',
      admin_password: ''
    });
    setCreateError('');
  };

  const openCreateModal = () => {
    resetCreateForm();
    setShowCreateModal(true);
  };

  const closeCreateModal = () => {
    setShowCreateModal(false);
    setCreateLoading(false);
    setCreateError('');
  };

  const handleCreateCollege = async (e) => {
    e.preventDefault();
    setCreateError('');
    setPanelMessage(null);

    const requiredFields = [
      'name',
      'code',
      'contact_email',
      'admin_email',
      'admin_name',
      'admin_password'
    ];
    for (const field of requiredFields) {
      if (!String(createForm[field] || '').trim()) {
        setCreateError('Please fill all fields.');
        return;
      }
    }

    if (createForm.admin_password.length < 8) {
      setCreateError('Admin password must be at least 8 characters.');
      return;
    }

    try {
      setCreateLoading(true);
      const result = await superadminAPI.createCollege({
        name: createForm.name.trim(),
        code: createForm.code.trim(),
        contact_email: createForm.contact_email.trim(),
        admin_email: createForm.admin_email.trim(),
        admin_name: createForm.admin_name.trim(),
        admin_password: createForm.admin_password
      });

      await fetchData();
      closeCreateModal();
      setPanelMessage({
        type: 'success',
        text: `College created successfully. College ID: ${result.college_id}`
      });
    } catch (error) {
      setCreateError(error.response?.data?.detail || 'Failed to create college');
    } finally {
      setCreateLoading(false);
    }
  };

  const filteredColleges = colleges.filter(c => {
    const matchesSearch = c.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
                         c.college_id.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesFilter = filter === 'all' || c.status === filter;
    return matchesSearch && matchesFilter;
  });

  const getStatusColor = (status) => {
    switch (status) {
      case 'active': return '#22c55e';
      case 'pending': return '#f59e0b';
      case 'suspended': return '#ef4444';
      default: return '#6b7280';
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'active': return <CheckCircle size={16} />;
      case 'pending': return <Clock size={16} />;
      case 'suspended': return <XCircle size={16} />;
      default: return <Activity size={16} />;
    }
  };

  if (loading) {
    return (
      <div className="superadmin-loading">
        <Loader2 className="animate-spin" size={48} />
        <p>Loading Superadmin Panel...</p>
      </div>
    );
  }

  return (
    <div className="superadmin-panel">
      {/* Header */}
      <header className="superadmin-header">
        <div className="header-content">
          <div className="logo-section">
            <Shield className="shield-icon" size={32} />
            <div>
              <h1>Superadmin Panel</h1>
              <p>VYUHA Platform Management</p>
            </div>
          </div>
          <div className="header-actions">
            <button className="btn-secondary" onClick={() => navigate('/dashboard')}>
              Back to Dashboard
            </button>
            <button className="btn-danger" onClick={logout}>
              Logout
            </button>
          </div>
        </div>
      </header>

      <div className="superadmin-content">
        {/* Stats Overview */}
        <div className="stats-grid">
          <motion.div className="stat-card" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
            <Building2 className="stat-icon blue" />
            <div className="stat-info">
              <span className="stat-value">{stats?.total_colleges || 0}</span>
              <span className="stat-label">Total Colleges</span>
            </div>
          </motion.div>
          
          <motion.div className="stat-card" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}>
            <CheckCircle className="stat-icon green" />
            <div className="stat-info">
              <span className="stat-value">{stats?.active_colleges || 0}</span>
              <span className="stat-label">Active</span>
            </div>
          </motion.div>
          
          <motion.div className="stat-card" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}>
            <Clock className="stat-icon yellow" />
            <div className="stat-info">
              <span className="stat-value">{stats?.pending_colleges || 0}</span>
              <span className="stat-label">Pending</span>
            </div>
          </motion.div>
          
          <motion.div className="stat-card" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }}>
            <Users className="stat-icon purple" />
            <div className="stat-info">
              <span className="stat-value">{stats?.total_users || 0}</span>
              <span className="stat-label">Total Users</span>
            </div>
          </motion.div>
        </div>

        <div className="main-grid">
          {/* Colleges List */}
          <div className="colleges-section">
            <div className="section-header">
              <h2><Building2 size={20} /> All Colleges</h2>
              <button className="btn-primary" onClick={openCreateModal}>
                <Plus size={18} /> Add College
              </button>
            </div>

            {/* Search and Filter */}
            <div className="search-filter-bar">
              <div className="search-input">
                <Search size={18} />
                <input
                  type="text"
                  placeholder="Search colleges..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                />
              </div>
              <div className="filter-tabs">
                {['all', 'active', 'pending', 'suspended'].map(f => (
                  <button
                    key={f}
                    className={filter === f ? 'active' : ''}
                    onClick={() => setFilter(f)}
                  >
                    {f.charAt(0).toUpperCase() + f.slice(1)}
                  </button>
                ))}
              </div>
            </div>

            {/* Colleges List */}
            <div className="colleges-list">
              {filteredColleges.length === 0 ? (
                <div className="empty-state">
                  <Building2 size={48} />
                  <p>No colleges found</p>
                </div>
              ) : (
                filteredColleges.map((college, index) => (
                  <motion.div
                    key={college.id}
                    className={`college-card ${selectedCollege === college.college_id ? 'selected' : ''}`}
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: index * 0.05 }}
                    onClick={() => fetchCollegeDetails(college.college_id)}
                  >
                    <div className="college-main">
                      <div className="college-info">
                        <h3>{college.name}</h3>
                        <p className="college-id">{college.college_id}</p>
                        {college.code && <p className="college-code">Code: {college.code}</p>}
                      </div>
                      <div className="college-status" style={{ color: getStatusColor(college.status) }}>
                        {getStatusIcon(college.status)}
                        <span>{college.status}</span>
                      </div>
                    </div>
                    <ChevronRight className="chevron" size={20} />
                  </motion.div>
                ))
              )}
            </div>
          </div>

          {/* College Details */}
          <div className="details-section">
            {collegeDetails ? (
              <motion.div
                className="college-details"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
              >
                <div className="details-header">
                  <div>
                    <h2>{collegeDetails.college?.name}</h2>
                    <p className="details-id">{collegeDetails.college?.college_id}</p>
                  </div>
                  <div className="status-badge" style={{ background: getStatusColor(collegeDetails.college?.status) }}>
                    {getStatusIcon(collegeDetails.college?.status)}
                    {collegeDetails.college?.status}
                  </div>
                </div>

                <div className="details-stats">
                  <div className="detail-stat">
                    <Users size={20} />
                    <span>{collegeDetails.users?.total || 0} Users</span>
                  </div>
                  <div className="detail-stat">
                    <Activity size={20} />
                    <span>{collegeDetails.faculty_members || 0} Faculty</span>
                  </div>
                  <div className="detail-stat">
                    <BarChart3 size={20} />
                    <span>{collegeDetails.subjects || 0} Subjects</span>
                  </div>
                </div>

                <div className="user-breakdown">
                  <h4>User Breakdown</h4>
                  <div className="breakdown-grid">
                    <div className="breakdown-item">
                      <Shield size={16} />
                      <span>{collegeDetails.users?.admins || 0} Admins</span>
                    </div>
                    <div className="breakdown-item">
                      <Users size={16} />
                      <span>{collegeDetails.users?.faculty || 0} Faculty</span>
                    </div>
                    <div className="breakdown-item">
                      <Activity size={16} />
                      <span>{collegeDetails.users?.hods || 0} Principals</span>
                    </div>
                    <div className="breakdown-item">
                      <Clock size={16} />
                      <span>{collegeDetails.pending_registrations || 0} Pending</span>
                    </div>
                  </div>
                </div>

                <div className="details-actions">
                  {collegeDetails.college?.status === 'pending' && (
                    <button
                      className="btn-success"
                      onClick={() => handleApproveCollege(collegeDetails.college?.college_id)}
                      disabled={actionLoading === collegeDetails.college?.college_id}
                    >
                      {actionLoading === collegeDetails.college?.college_id ? (
                        <Loader2 className="animate-spin" size={18} />
                      ) : (
                        <CheckCircle size={18} />
                      )}
                      Approve College
                    </button>
                  )}
                  
                  {collegeDetails.college?.status === 'active' && (
                    <button
                      className="btn-danger"
                      onClick={() => setSuspendTargetCollegeId(collegeDetails.college?.college_id)}
                      disabled={actionLoading === collegeDetails.college?.college_id}
                    >
                      {actionLoading === collegeDetails.college?.college_id ? (
                        <Loader2 className="animate-spin" size={18} />
                      ) : (
                        <XCircle size={18} />
                      )}
                      Suspend College
                    </button>
                  )}
                </div>

                <div className="college-meta">
                  <p>Contact: {collegeDetails.college?.contact_email || 'N/A'}</p>
                  <p>Created: {new Date(collegeDetails.college?.created_at).toLocaleDateString()}</p>
                </div>
              </motion.div>
            ) : (
              <div className="no-selection">
                <Shield size={64} />
                <h3>Select a College</h3>
                <p>Click on a college to view its details</p>
              </div>
            )}
          </div>
        </div>
      </div>

      {panelMessage && (
        <div className={`panel-message ${panelMessage.type}`}>
          <span>{panelMessage.text}</span>
          <button onClick={() => setPanelMessage(null)}>Dismiss</button>
        </div>
      )}

      {showCreateModal && (
        <div className="modal-overlay">
          <div className="create-college-modal">
            <div className="modal-head">
              <h3>Create New College</h3>
              <button onClick={closeCreateModal} className="close-btn" disabled={createLoading}>
                Close
              </button>
            </div>

            <form onSubmit={handleCreateCollege} className="modal-form">
              <label>
                College Name
                <input
                  type="text"
                  value={createForm.name}
                  onChange={(e) => setCreateForm((prev) => ({ ...prev, name: e.target.value }))}
                  required
                />
              </label>

              <label>
                College Code
                <input
                  type="text"
                  value={createForm.code}
                  onChange={(e) => setCreateForm((prev) => ({ ...prev, code: e.target.value }))}
                  required
                />
              </label>

              <label>
                Contact Email
                <input
                  type="email"
                  value={createForm.contact_email}
                  onChange={(e) => setCreateForm((prev) => ({ ...prev, contact_email: e.target.value }))}
                  required
                />
              </label>

              <label>
                Admin Name
                <input
                  type="text"
                  value={createForm.admin_name}
                  onChange={(e) => setCreateForm((prev) => ({ ...prev, admin_name: e.target.value }))}
                  required
                />
              </label>

              <label>
                Admin Email
                <input
                  type="email"
                  value={createForm.admin_email}
                  onChange={(e) => setCreateForm((prev) => ({ ...prev, admin_email: e.target.value }))}
                  required
                />
              </label>

              <label>
                Admin Password
                <input
                  type="password"
                  value={createForm.admin_password}
                  onChange={(e) => setCreateForm((prev) => ({ ...prev, admin_password: e.target.value }))}
                  minLength={8}
                  required
                />
              </label>

              {createError && <p className="form-error">{createError}</p>}

              <div className="modal-actions">
                <button type="button" className="btn-secondary" onClick={closeCreateModal} disabled={createLoading}>
                  Cancel
                </button>
                <button type="submit" className="btn-primary" disabled={createLoading}>
                  {createLoading ? <><Loader2 className="animate-spin" size={16} /> Creating...</> : 'Create College'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {suspendTargetCollegeId && (
        <div className="modal-overlay" onClick={() => setSuspendTargetCollegeId(null)}>
          <div className="create-college-modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-head">
              <h3>Suspend College</h3>
              <button onClick={() => setSuspendTargetCollegeId(null)} className="close-btn">
                Close
              </button>
            </div>
            <p className="form-error" style={{ color: 'rgba(255,255,255,0.85)' }}>
              Are you sure you want to suspend <strong>{suspendTargetCollegeId}</strong>? This will block active usage.
            </p>
            <div className="modal-actions">
              <button className="btn-secondary" type="button" onClick={() => setSuspendTargetCollegeId(null)}>
                Cancel
              </button>
              <button
                className="btn-danger"
                type="button"
                onClick={async () => {
                  const target = suspendTargetCollegeId;
                  setSuspendTargetCollegeId(null);
                  await handleSuspendCollege(target);
                }}
              >
                Confirm Suspend
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default SuperAdminPanel;
