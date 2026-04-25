import { useState, useEffect, useRef } from 'react';
import { useNavigate, Link, useLocation } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
  LayoutDashboard,
  Calendar,
  Users,
  DoorOpen,
  BookOpen,
  MessageCircle,
  LogOut,
  Bell,
  ChevronDown,
  Menu,
  X,
  Sparkles,
  Upload,
  Zap,
  Eye,
  Send,
  CheckCircle2,
  Loader2,
  FileSpreadsheet,
  AlertTriangle,
  ArrowRight,
  Clock,
  Settings,
  Shield
} from 'lucide-react';
import { CalendarDays } from 'lucide-react';
import { timetableAPI, autoHandlerAPI, uploadExcel, exportSourceData, normalizeApiError } from '../lib/api';
import { useAuth } from '../lib/AuthProvider';
import NotificationDropdown from './NotificationDropdown';
import './Dashboard.css';

const STORAGE_KEYS = {
  uploadMode: 'vyuha_upload_mode',
};

const Dashboard = () => {
  const { user, logout } = useAuth();
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [activeMenu, setActiveMenu] = useState('dashboard');
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();
  const location = useLocation();

  // Stepper State
  const [currentStep, setCurrentStep] = useState(0);
  const [uploadStatus, setUploadStatus] = useState({ done: false, counts: null, error: null });
  const [generateStatus, setGenerateStatus] = useState({ done: false, slotsGenerated: 0, error: null });
  const [timetablePreview, setTimetablePreview] = useState([]);
  const [approveStatus, setApproveStatus] = useState({ done: false, error: null });
  const [stats, setStats] = useState({ 
    faculty: 0, 
    subjects: 0, 
    rooms: 0,
    pending_leaves: 0,
    pending_substitutions: 0,
    today_classes: 0
  });
  const [isProcessing, setIsProcessing] = useState(false);
  const [uploadMode, setUploadMode] = useState(() => localStorage.getItem(STORAGE_KEYS.uploadMode) || 'replace');
  const fileInputRef = useRef(null);

  useEffect(() => {
    const initDashboard = async () => {
      await fetchStats();
      await loadExistingTimetable();
    };
    const path = location.pathname.replace('/', '');
    setActiveMenu(path || 'dashboard');
    initDashboard();
  }, [location]);

  const fetchStats = async () => {
    try {
      setLoading(true);
      // Use the new dashboard stats endpoint
      const dashboardStats = await autoHandlerAPI.getDashboardStats();
      setStats({
        faculty: dashboardStats.faculty_count || 0,
        subjects: dashboardStats.subjects_count || 0,
        rooms: dashboardStats.rooms_count || 0,
        pending_leaves: dashboardStats.pending_leaves || 0,
        pending_substitutions: dashboardStats.pending_substitutions || 0,
        today_classes: dashboardStats.today_classes || 0
      });
    } catch (err) {
      console.error('Error fetching stats:', err);
      // Fallback for older versions or error states
      setStats(prev => ({ ...prev }));
    } finally {
      setLoading(false);
    }
  };

  const loadExistingTimetable = async () => {
    try {
      const response = await timetableAPI.get(1);
      const existing = response.timetable || [];
      setTimetablePreview(existing);
      if (existing.length > 0) {
        setGenerateStatus(prev => ({ ...prev, done: true, slotsGenerated: existing.length }));
      }
    } catch (err) {
      console.error('Failed to load existing timetable:', err);
    }
  };

  const handleLogout = async () => {
    logout();
    navigate('/login');
  };

  // Step 1: Upload Excel
  const handleUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    setIsProcessing(true);
    setUploadStatus({ done: false, counts: null, error: null });
    try {
      const replaceExisting = uploadMode === 'replace';
      const res = await uploadExcel(file, replaceExisting);
      setUploadStatus({ done: true, counts: res, error: null });
      await fetchStats();
      await loadExistingTimetable();
      setCurrentStep(1);
    } catch (err) {
      setUploadStatus({ done: false, counts: null, error: normalizeApiError(err, 'Upload failed') });
    } finally {
      setIsProcessing(false);
    }
  };

  const handleDownloadCurrentData = async () => {
    try {
      const blob = await exportSourceData();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${user?.college_id || 'vyuha'}_source_data.xlsx`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      setUploadStatus(prev => ({ ...prev, error: normalizeApiError(err, 'Download failed') }));
    }
  };

  // Step 2: Generate Timetable
  const handleGenerate = async () => {
    setIsProcessing(true);
    setGenerateStatus({ done: false, slotsGenerated: 0, error: null });
    try {
      const res = await timetableAPI.generate();
      setGenerateStatus({ done: true, slotsGenerated: res.slots_generated, error: null });
      setCurrentStep(2);
      // Fetch preview for semester 1
      try {
        const preview = await timetableAPI.get(1);
        setTimetablePreview(preview.timetable || []);
      } catch { /* ignore preview fetch error */ }
    } catch (err) {
      setGenerateStatus({ done: false, slotsGenerated: 0, error: normalizeApiError(err, 'Generation failed') });
    } finally {
      setIsProcessing(false);
    }
  };

  // Step 3: Approve & Notify
  const handleApprove = async () => {
    setIsProcessing(true);
    setApproveStatus({ done: false, error: null });
    try {
      // Validate and approve
      await autoHandlerAPI.validateTimetable(true); // auto-fix minor issues
      setApproveStatus({ done: true, error: null });
      setCurrentStep(3);
    } catch (err) {
      setApproveStatus({ done: false, error: normalizeApiError(err, 'Approval failed') });
    } finally {
      setIsProcessing(false);
    }
  };

  const goToStep = (stepIndex) => {
    setCurrentStep(stepIndex);
    if (stepIndex === 0) {
      setApproveStatus({ done: false, error: null });
      setGenerateStatus(prev => ({ ...prev, done: false, slotsGenerated: 0, error: prev.error }));
    }
  };

  const menuItems = [
    { id: 'dashboard', label: 'Command Center', icon: LayoutDashboard, path: '/dashboard' },
    { id: 'timetable', label: 'Timetable', icon: Calendar, path: '/timetable' },
    { id: 'users', label: 'User Management', icon: Shield, path: '/users' },
    { id: 'faculty', label: 'Faculty', icon: Users, path: '/faculty' },
    { id: 'substitution', label: 'Substitutions', icon: Zap, path: '/chat' }, // Linked to Chat or dedicated Sub Engine
    { id: 'leave', label: 'Leave Management', icon: CalendarDays, path: '/leave' },
    { id: 'rooms', label: 'Rooms', icon: DoorOpen, path: '/rooms' },
    { id: 'subjects', label: 'Subjects', icon: BookOpen, path: '/subjects' },
    { id: 'settings', label: 'Settings', icon: Settings, path: '/settings' },
  ];

  const steps = [
    { label: 'Upload Data', icon: Upload, desc: 'Upload Faculty, Subjects & Rooms Excel' },
    { label: 'Generate', icon: Zap, desc: 'Auto-generate conflict-free master timetable' },
    { label: 'Review & Edit', icon: Eye, desc: 'Preview schedule, edit via AI Assistant' },
    { label: 'Approve & Notify', icon: Send, desc: 'Publish and email all faculty their schedules' },
  ];

  const sidebarVariants = {
    open: { width: 260, transition: { duration: 0.3, ease: "easeOut" } },
    closed: { width: 72, transition: { duration: 0.3, ease: "easeOut" } }
  };

  return (
    <div className="dashboard-container-3d">
      {/* Animated Background */}
      <div className="dashboard-bg">
        <motion.div className="bg-orb orb-1"
          animate={{ scale: [1, 1.2, 1], rotate: [0, 180, 360], opacity: [0.3, 0.5, 0.3] }}
          transition={{ duration: 20, repeat: Infinity, ease: "linear" }}
        />
        <motion.div className="bg-orb orb-2"
          animate={{ scale: [1.2, 1, 1.2], rotate: [360, 180, 0], opacity: [0.2, 0.4, 0.2] }}
          transition={{ duration: 15, repeat: Infinity, ease: "linear" }}
        />
      </div>

      {/* Sidebar */}
      <motion.aside className={`sidebar-3d ${sidebarOpen ? 'open' : 'closed'}`}
        variants={sidebarVariants} initial="open" animate={sidebarOpen ? "open" : "closed"}>
        <div className="sidebar-header-3d">
          <motion.div className="logo-section-3d" whileHover={{ scale: 1.05 }}>
            <div className="logo-icon-3d"><Sparkles size={24} /></div>
            <AnimatePresence>
              {sidebarOpen && (
                <motion.span className="logo-text-3d"
                  initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -10 }}>
                  VYUHA
                </motion.span>
              )}
            </AnimatePresence>
          </motion.div>
          <motion.button className="toggle-btn-3d" onClick={() => setSidebarOpen(!sidebarOpen)}
            whileHover={{ scale: 1.1 }} whileTap={{ scale: 0.95 }}>
            {sidebarOpen ? <X size={20} /> : <Menu size={20} />}
          </motion.button>
        </div>

        <nav className="sidebar-nav-3d">
          {menuItems.map((item, index) => {
            const Icon = item.icon;
            const isActive = activeMenu === item.id;
            return (
              <Link key={item.id} to={item.path}
                className={`nav-item-3d ${isActive ? 'active' : ''}`}
                onClick={() => setActiveMenu(item.id)}>
                <motion.div whileHover={{ scale: 1.1, rotate: 5 }} whileTap={{ scale: 0.95 }}>
                  <Icon size={22} />
                </motion.div>
                <AnimatePresence>
                  {sidebarOpen && (
                    <motion.span initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }}
                      exit={{ opacity: 0, x: -10 }} transition={{ delay: index * 0.05 }}>
                      {item.label}
                    </motion.span>
                  )}
                </AnimatePresence>
                {isActive && (
                  <motion.div className="active-indicator" layoutId="activeIndicator"
                    transition={{ type: "spring", stiffness: 300 }} />
                )}
              </Link>
            );
          })}
        </nav>

        <div className="sidebar-footer-3d">
          <motion.button className="nav-item-3d logout" onClick={handleLogout}
            whileHover={{ scale: 1.02, x: 5 }} whileTap={{ scale: 0.98 }}>
            <LogOut size={22} />
            <AnimatePresence>
              {sidebarOpen && <motion.span>Logout</motion.span>}
            </AnimatePresence>
          </motion.button>
        </div>
      </motion.aside>

      {/* Main Content */}
      <main className="main-content-3d">
        {/* Header */}
        <motion.header className="dashboard-header-3d"
          initial={{ opacity: 0, y: -20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5 }}>
          <div className="header-search-3d" style={{flex: 1}}>
            <h2 style={{margin: 0, fontWeight: 700, color: 'white'}}>Admin Command Center</h2>
          </div>
          <div className="header-actions-3d" style={{ display: 'flex', alignItems: 'center' }}>
            <NotificationDropdown />
            <motion.div className="user-profile-3d" whileHover={{ scale: 1.02 }}>
              <div className="avatar-3d">
                <span>{user?.email?.charAt(0).toUpperCase() || 'A'}</span>
              </div>
              <div className="user-info-3d">
                <span className="name">{user?.email?.split('@')[0] || 'Admin'}</span>
                <span className="role">Management</span>
              </div>
            </motion.div>
          </div>
        </motion.header>

        {/* Dashboard Content */}
        <div className="dashboard-content-3d">
          {/* Stats Row */}
          <div className="stats-grid-3d">
            {[
              { label: 'Faculty', value: stats.faculty, icon: Users, color: 'blue' },
              { label: 'Subjects', value: stats.subjects, icon: BookOpen, color: 'purple' },
              { label: 'Rooms', value: stats.rooms, icon: DoorOpen, color: 'green' },
            ].map((stat, index) => (
              <motion.div key={stat.label} className={`stat-card-3d ${stat.color}`}
                initial={{ opacity: 0, y: 30 }} animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.1, duration: 0.5 }}
                whileHover={{ scale: 1.03, y: -5 }}>
                <motion.div className="stat-icon-3d"><stat.icon size={28} /></motion.div>
                <div className="stat-info-3d">
                  <span className="stat-value-3d">
                    {loading ? <Loader2 className="animate-spin" size={24} /> : stat.value}
                  </span>
                  <span className="stat-label-3d">{stat.label}</span>
                </div>
                <div className="stat-glow" />
              </motion.div>
            ))}
          </div>

          {/* 4 Step Command Pipeline */}
          <motion.div className="content-card-3d" style={{ marginTop: '1.5rem' }}
            initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }}>
            <h3 style={{ marginBottom: '1.5rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <Zap size={20} /> Timetable Pipeline
            </h3>

            {/* Stepper bar */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '2rem', flexWrap: 'wrap' }}>
              {steps.map((step, i) => {
                const Icon = step.icon;
                const isComplete = i < currentStep || (i === 3 && approveStatus.done);
                const isActive = i === currentStep;
                return (
                  <div key={i} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <motion.div
                      role="button"
                      tabIndex={0}
                      onClick={() => goToStep(i)}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter' || e.key === ' ') goToStep(i);
                      }}
                      style={{
                        display: 'flex', alignItems: 'center', gap: '0.5rem', padding: '0.6rem 1rem',
                        borderRadius: '12px', fontSize: '0.85rem', fontWeight: 600,
                        background: isComplete ? 'linear-gradient(135deg, #22c55e, #16a34a)' :
                                   isActive ? 'linear-gradient(135deg, #7c3aed, #6d28d9)' :
                                   'rgba(255,255,255,0.07)',
                        color: (isComplete || isActive) ? 'white' : 'rgba(255,255,255,0.5)',
                        boxShadow: isActive ? '0 0 20px rgba(124, 58, 237, 0.4)' : 'none',
                        cursor: 'pointer',
                      }}
                      animate={isActive ? { scale: [1, 1.02, 1] } : {}}
                      transition={{ duration: 1.5, repeat: Infinity }}
                    >
                      {isComplete ? <CheckCircle2 size={16} /> : <Icon size={16} />}
                      {step.label}
                    </motion.div>
                    {i < steps.length - 1 && <ArrowRight size={16} style={{ color: 'rgba(255,255,255,0.3)' }} />}
                  </div>
                );
              })}
            </div>

            {timetablePreview.length > 0 && (
              <div style={{
                marginBottom: '1.5rem',
                padding: '1rem 1.25rem',
                borderRadius: '14px',
                background: 'rgba(255,255,255,0.04)',
                border: '1px solid rgba(124,58,237,0.25)'
              }}>
                <h4 style={{ margin: '0 0 0.75rem', color: 'white' }}>Loaded timetable preview</h4>
                <p style={{ margin: '0 0 0.75rem', color: 'rgba(255,255,255,0.65)', fontSize: '0.9rem' }}>
                  {timetablePreview.length} slots are stored in the database for this college. Open the timetable page to view the full schedule.
                </p>
                <div style={{ display: 'grid', gap: '0.5rem' }}>
                  {timetablePreview.slice(0, 5).map((slot) => (
                    <div key={slot.id} style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      gap: '1rem',
                      padding: '0.65rem 0.85rem',
                      borderRadius: '10px',
                      background: 'rgba(255,255,255,0.03)',
                      color: 'rgba(255,255,255,0.85)',
                      fontSize: '0.9rem'
                    }}>
                      <span>{slot.day}</span>
                      <span>{String(slot.start_time).slice(0, 5)} - {String(slot.end_time).slice(0, 5)}</span>
                      <span>#{slot.semester}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Step Content */}
            <AnimatePresence mode="wait">
              {/* Step 0: Upload */}
              {currentStep === 0 && (
                <motion.div key="upload" initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -20 }}
                  style={{ background: 'rgba(255,255,255,0.04)', borderRadius: '16px', padding: '2rem', border: '1px dashed rgba(124,58,237,0.4)' }}>
                  <div style={{ textAlign: 'center' }}>
                    <FileSpreadsheet size={48} style={{ color: '#7c3aed', marginBottom: '1rem' }} />
                    <h4 style={{ marginBottom: '0.5rem' }}>Upload Source Data</h4>
                    <p style={{ color: 'rgba(255,255,255,0.6)', marginBottom: '1.5rem', fontSize: '0.9rem' }}>
                      Upload an Excel file with <strong>Faculty</strong>, <strong>Subjects</strong>, and <strong>Rooms</strong> sheets.
                    </p>
                    <div style={{ marginBottom: '1rem', textAlign: 'left', display: 'flex', gap: '0.75rem', justifyContent: 'center', flexWrap: 'wrap' }}>
                      <button
                        type="button"
                        onClick={() => {
                          setUploadMode('replace');
                          localStorage.setItem(STORAGE_KEYS.uploadMode, 'replace');
                        }}
                        style={{
                          padding: '0.55rem 1rem',
                          borderRadius: '10px',
                          border: uploadMode === 'replace' ? '1px solid #a855f7' : '1px solid rgba(255,255,255,0.12)',
                          background: uploadMode === 'replace' ? 'rgba(168,85,247,0.18)' : 'rgba(255,255,255,0.05)',
                          color: uploadMode === 'replace' ? '#e9d5ff' : 'rgba(255,255,255,0.75)',
                          cursor: 'pointer',
                        }}
                      >
                        Replace existing data
                      </button>
                      <button
                        type="button"
                        onClick={() => {
                          setUploadMode('append');
                          localStorage.setItem(STORAGE_KEYS.uploadMode, 'append');
                        }}
                        style={{
                          padding: '0.55rem 1rem',
                          borderRadius: '10px',
                          border: uploadMode === 'append' ? '1px solid #22c55e' : '1px solid rgba(255,255,255,0.12)',
                          background: uploadMode === 'append' ? 'rgba(34,197,94,0.18)' : 'rgba(255,255,255,0.05)',
                          color: uploadMode === 'append' ? '#dcfce7' : 'rgba(255,255,255,0.75)',
                          cursor: 'pointer',
                        }}
                      >
                        Keep existing data
                      </button>
                    </div>
                    <p style={{ color: 'rgba(255,255,255,0.5)', marginBottom: '1rem', fontSize: '0.8rem' }}>
                      {uploadMode === 'replace'
                        ? 'Replace removes the current college dataset before importing the new Excel file.'
                        : 'Keep existing leaves current data in place and tries to add the new rows.'}
                    </p>
                    <input ref={fileInputRef} type="file" accept=".xlsx,.xls" onChange={handleUpload}
                      style={{ display: 'none' }} />
                    <motion.button
                      onClick={() => fileInputRef.current.click()}
                      disabled={isProcessing}
                      whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}
                      style={{
                        padding: '0.8rem 2rem', borderRadius: '12px', border: 'none', cursor: 'pointer',
                        background: 'linear-gradient(135deg, #7c3aed, #6d28d9)', color: 'white',
                        fontWeight: 600, fontSize: '1rem', display: 'flex', alignItems: 'center',
                        gap: '0.5rem', margin: '0 auto',
                      }}>
                      {isProcessing ? <><Loader2 className="animate-spin" size={18} /> Uploading...</> :
                        <><Upload size={18} /> Choose Excel File</>}
                    </motion.button>
                    {uploadStatus.error && (
                      <p style={{ color: '#ef4444', marginTop: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem', justifyContent: 'center' }}>
                        <AlertTriangle size={16} /> {uploadStatus.error}
                      </p>
                    )}
                    {uploadStatus.done && uploadStatus.counts && (
                      <p style={{ color: '#22c55e', marginTop: '1rem' }}>
                        Imported {uploadStatus.counts.faculty_count} faculty, {uploadStatus.counts.subjects_count} subjects, and {uploadStatus.counts.rooms_count} rooms.
                      </p>
                    )}
                    <div style={{ marginTop: '1rem' }}>
                      <button
                        type="button"
                        onClick={() => goToStep(0)}
                        style={{
                          padding: '0.6rem 1rem',
                          borderRadius: '10px',
                          border: '1px solid rgba(255,255,255,0.15)',
                          background: 'rgba(255,255,255,0.04)',
                          color: 'rgba(255,255,255,0.85)',
                          cursor: 'pointer'
                        }}
                      >
                        Stay on upload step
                      </button>
                    </div>
                    <div style={{ marginTop: '0.75rem' }}>
                      <button
                        type="button"
                        onClick={handleDownloadCurrentData}
                        style={{
                          padding: '0.6rem 1rem',
                          borderRadius: '10px',
                          border: '1px solid rgba(34,197,94,0.3)',
                          background: 'rgba(34,197,94,0.08)',
                          color: '#86efac',
                          cursor: 'pointer'
                        }}
                      >
                        Download current Excel
                      </button>
                    </div>
                  </div>
                </motion.div>
              )}

              {/* Step 1: Generate */}
              {currentStep === 1 && (
                <motion.div key="generate" initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -20 }}
                  style={{ background: 'rgba(255,255,255,0.04)', borderRadius: '16px', padding: '2rem' }}>
                  <div style={{ textAlign: 'center' }}>
                    <CheckCircle2 size={32} style={{ color: '#22c55e', marginBottom: '0.5rem' }} />
                    <p style={{ color: '#22c55e', fontWeight: 600, marginBottom: '1rem' }}>
                      ✅ Data loaded: {stats.faculty} Faculty, {stats.subjects} Subjects, {stats.rooms} Rooms
                    </p>
                    <Zap size={48} style={{ color: '#f59e0b', marginBottom: '1rem' }} />
                    <h4 style={{ marginBottom: '0.5rem' }}>Generate Master Timetable</h4>
                    <p style={{ color: 'rgba(255,255,255,0.6)', marginBottom: '1.5rem', fontSize: '0.9rem' }}>
                      The 6-rule engine will auto-schedule all classes with zero conflicts.
                    </p>
                    <motion.button
                      onClick={handleGenerate}
                      disabled={isProcessing}
                      whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}
                      style={{
                        padding: '0.8rem 2rem', borderRadius: '12px', border: 'none', cursor: 'pointer',
                        background: 'linear-gradient(135deg, #f59e0b, #d97706)', color: 'white',
                        fontWeight: 600, fontSize: '1rem', display: 'flex', alignItems: 'center',
                        gap: '0.5rem', margin: '0 auto',
                      }}>
                      {isProcessing ? <><Loader2 className="animate-spin" size={18} /> Generating...</> :
                        <><Zap size={18} /> Generate Now</>}
                    </motion.button>
                    {generateStatus.error && (
                      <p style={{ color: '#ef4444', marginTop: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem', justifyContent: 'center' }}>
                        <AlertTriangle size={16} /> {generateStatus.error}
                      </p>
                    )}
                  </div>
                </motion.div>
              )}

              {/* Step 2: Review */}
              {currentStep === 2 && (
                <motion.div key="review" initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -20 }}
                  style={{ background: 'rgba(255,255,255,0.04)', borderRadius: '16px', padding: '2rem' }}>
                  <CheckCircle2 size={32} style={{ color: '#22c55e', marginBottom: '0.5rem' }} />
                  <p style={{ color: '#22c55e', fontWeight: 600, marginBottom: '1rem', textAlign: 'center' }}>
                    ✅ Generated {generateStatus.slotsGenerated} class slots with 0 conflicts!
                  </p>
                  <div style={{ display: 'flex', gap: '1rem', justifyContent: 'center', flexWrap: 'wrap' }}>
                    <motion.button
                      onClick={() => goToStep(0)}
                      whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}
                      style={{
                        padding: '0.8rem 1.5rem', borderRadius: '12px', border: '1px solid rgba(255,255,255,0.12)',
                        cursor: 'pointer', background: 'rgba(255,255,255,0.05)', color: 'rgba(255,255,255,0.8)',
                        fontWeight: 600, display: 'flex', alignItems: 'center', gap: '0.5rem',
                      }}>
                      <Upload size={18} /> Upload New Data
                    </motion.button>
                    <motion.button
                      onClick={() => navigate('/timetable')}
                      whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}
                      style={{
                        padding: '0.8rem 1.5rem', borderRadius: '12px', border: '1px solid rgba(124,58,237,0.5)',
                        cursor: 'pointer', background: 'rgba(124,58,237,0.15)', color: '#a78bfa',
                        fontWeight: 600, display: 'flex', alignItems: 'center', gap: '0.5rem',
                      }}>
                      <Eye size={18} /> View Full Timetable
                    </motion.button>
                    <motion.button
                      onClick={() => navigate('/chat')}
                      whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}
                      style={{
                        padding: '0.8rem 1.5rem', borderRadius: '12px', border: '1px solid rgba(124,58,237,0.5)',
                        cursor: 'pointer', background: 'rgba(124,58,237,0.15)', color: '#a78bfa',
                        fontWeight: 600, display: 'flex', alignItems: 'center', gap: '0.5rem',
                      }}>
                      <MessageCircle size={18} /> Edit with AI
                    </motion.button>
                    <motion.button
                      onClick={() => setCurrentStep(3)}
                      whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}
                      style={{
                        padding: '0.8rem 2rem', borderRadius: '12px', border: 'none', cursor: 'pointer',
                        background: 'linear-gradient(135deg, #22c55e, #16a34a)', color: 'white',
                        fontWeight: 600, display: 'flex', alignItems: 'center', gap: '0.5rem',
                      }}>
                      <ArrowRight size={18} /> Proceed to Approve
                    </motion.button>
                  </div>
                </motion.div>
              )}

              {/* Step 3: Approve & Notify */}
              {currentStep === 3 && !approveStatus.done && (
                <motion.div key="approve" initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -20 }}
                  style={{ background: 'rgba(255,255,255,0.04)', borderRadius: '16px', padding: '2rem', textAlign: 'center' }}>
                  <Send size={48} style={{ color: '#3b82f6', marginBottom: '1rem' }} />
                  <h4 style={{ marginBottom: '0.5rem' }}>Approve & Notify All Faculty</h4>
                  <p style={{ color: 'rgba(255,255,255,0.6)', marginBottom: '1.5rem', fontSize: '0.9rem' }}>
                    This will email every faculty member their individual timetable schedule.
                  </p>
                  <motion.button
                    onClick={handleApprove}
                    disabled={isProcessing}
                    whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}
                    style={{
                      padding: '0.8rem 2rem', borderRadius: '12px', border: 'none', cursor: 'pointer',
                      background: 'linear-gradient(135deg, #3b82f6, #2563eb)', color: 'white',
                      fontWeight: 600, fontSize: '1rem', display: 'flex', alignItems: 'center',
                      gap: '0.5rem', margin: '0 auto',
                    }}>
                    {isProcessing ? <><Loader2 className="animate-spin" size={18} /> Sending Emails...</> :
                      <><Send size={18} /> Approve & Send Notifications</>}
                  </motion.button>
                  {approveStatus.error && (
                    <p style={{ color: '#ef4444', marginTop: '1rem' }}>
                      <AlertTriangle size={16} /> {approveStatus.error}
                    </p>
                  )}
                  <div style={{ marginTop: '1rem' }}>
                    <button
                      type="button"
                      onClick={() => goToStep(0)}
                      style={{
                        padding: '0.7rem 1.1rem',
                        borderRadius: '10px',
                        border: '1px solid rgba(255,255,255,0.12)',
                        background: 'rgba(255,255,255,0.05)',
                        color: 'rgba(255,255,255,0.8)',
                        cursor: 'pointer'
                      }}
                    >
                      Upload New Data
                    </button>
                  </div>
                </motion.div>
              )}

              {/* Final: Done */}
              {approveStatus.done && (
                <motion.div key="done" initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }}
                  style={{ background: 'linear-gradient(135deg, rgba(34,197,94,0.1), rgba(22,163,74,0.1))', borderRadius: '16px', padding: '2rem', textAlign: 'center', border: '1px solid rgba(34,197,94,0.3)' }}>
                  <motion.div animate={{ scale: [1, 1.1, 1] }} transition={{ duration: 1, repeat: 2 }}>
                    <CheckCircle2 size={64} style={{ color: '#22c55e', marginBottom: '1rem' }} />
                  </motion.div>
                  <h3 style={{ color: '#22c55e' }}>Timetable Published Successfully! 🎉</h3>
                  <p style={{ color: 'rgba(255,255,255,0.7)', marginTop: '0.5rem' }}>
                    All faculty members have been notified via email with their schedules.
                  </p>
                </motion.div>
              )}
            </AnimatePresence>
          </motion.div>
        </div>
      </main>
    </div>
  );
};

export default Dashboard;
