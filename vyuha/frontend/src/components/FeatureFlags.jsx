import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  Settings,
  ArrowLeft,
  Loader2,
  CheckCircle2,
  AlertTriangle,
  CalendarDays,
  Sun,
  Coffee,
  GraduationCap,
  FlaskConical,
  Scale,
  Sparkles,
  Save,
  RotateCcw
} from 'lucide-react';
import { getFeatureFlags, updateFeatureFlags } from '../lib/api';
import './FeatureFlags.css';

const FLAG_CONFIG = [
  {
    key: 'saturday_enabled',
    label: 'Saturday Classes',
    description: 'Include Saturday in the weekly schedule for all semesters',
    icon: CalendarDays,
    color: '#7c3aed',
  },
  {
    key: 'sunday_enabled',
    label: 'Sunday Classes',
    description: 'Include Sunday in the weekly schedule (rare, for intensive programs)',
    icon: Sun,
    color: '#f59e0b',
  },
  {
    key: 'break_after_3rd_period',
    label: 'Break After 3rd Period',
    description: 'Enforce a mandatory break at 11:00 AM (no classes scheduled)',
    icon: Coffee,
    color: '#22c55e',
  },
  {
    key: 'lab_sessions_enabled',
    label: 'Lab Sessions',
    description: 'Allow 2-hour lab block scheduling for practical subjects',
    icon: FlaskConical,
    color: '#3b82f6',
  },
  {
    key: 'even_distribution',
    label: 'Even Distribution',
    description: 'Balance workload equally across all eligible faculty members',
    icon: Scale,
    color: '#ec4899',
  },
  {
    key: 'ai_chat',
    label: 'AI Assistant',
    description: 'Enable Groq-powered natural language chat and smart suggestions. Manual mode stays available when this is off.',
    icon: Sparkles,
    color: '#8b5cf6',
  },
];

const FeatureFlags = () => {
  const navigate = useNavigate();
  const [flags, setFlags] = useState(null);
  const [originalFlags, setOriginalFlags] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saveResult, setSaveResult] = useState(null);
  const [maxLectures, setMaxLectures] = useState(4);

  useEffect(() => {
    fetchFlags();
  }, []);

  const fetchFlags = async () => {
    try {
      setLoading(true);
      const data = await getFeatureFlags();
      setFlags(data);
      setOriginalFlags(data);
      setMaxLectures(data.max_lectures_per_day || 4);
    } catch (err) {
      console.error('Error fetching flags:', err);
      // Use defaults
      const defaults = {
        saturday_enabled: true,
        sunday_enabled: false,
        break_after_3rd_period: true,
        max_lectures_per_day: 4,
        lab_sessions_enabled: true,
        even_distribution: true,
        ai_chat: true,
      };
      setFlags(defaults);
      setOriginalFlags(defaults);
    } finally {
      setLoading(false);
    }
  };

  const toggleFlag = (key) => {
    setFlags(prev => ({ ...prev, [key]: !prev[key] }));
    setSaveResult(null);
  };

  const handleSave = async () => {
    try {
      setSaving(true);
      setSaveResult(null);
      const payload = { ...flags, max_lectures_per_day: maxLectures };
      await updateFeatureFlags(payload);
      setOriginalFlags(payload);
      setFlags(payload);
      setSaveResult({ type: 'success', message: 'Settings saved! Changes will apply on next timetable generation.' });
    } catch (err) {
      setSaveResult({ type: 'error', message: err.response?.data?.detail || 'Failed to save settings.' });
    } finally {
      setSaving(false);
    }
  };

  const handleReset = () => {
    setFlags({ ...originalFlags });
    setMaxLectures(originalFlags?.max_lectures_per_day || 4);
    setSaveResult(null);
  };

  const hasChanges = flags && originalFlags && (
    JSON.stringify({ ...flags, max_lectures_per_day: maxLectures }) !==
    JSON.stringify(originalFlags)
  );

  if (loading) {
    return (
      <div className="ff-loading">
        <Loader2 className="animate-spin" size={40} />
        <p>Loading settings...</p>
      </div>
    );
  }

  return (
    <div className="ff-container">
      {/* Animated Background */}
      <div className="ff-bg">
        <motion.div className="ff-orb ff-orb-1"
          animate={{ scale: [1, 1.2, 1], rotate: [0, 180, 360], opacity: [0.2, 0.4, 0.2] }}
          transition={{ duration: 20, repeat: Infinity, ease: "linear" }}
        />
        <motion.div className="ff-orb ff-orb-2"
          animate={{ scale: [1.2, 1, 1.2], rotate: [360, 180, 0], opacity: [0.15, 0.3, 0.15] }}
          transition={{ duration: 15, repeat: Infinity, ease: "linear" }}
        />
      </div>

      <div className="ff-content">
        {/* Header */}
        <motion.div className="ff-header"
          initial={{ opacity: 0, y: -20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5 }}>
          <motion.button className="ff-back-btn" onClick={() => navigate('/dashboard')}
            whileHover={{ scale: 1.05, x: -3 }} whileTap={{ scale: 0.95 }}>
            <ArrowLeft size={20} />
            Back
          </motion.button>
          <div className="ff-title-section">
            <div className="ff-title-icon">
              <Settings size={28} />
            </div>
            <div>
              <h1 className="ff-title">Feature Flags</h1>
              <p className="ff-subtitle">ON/OFF switches that adapt the scheduling engine to your college</p>
            </div>
          </div>
        </motion.div>

        {/* Toggle Cards */}
        <div className="ff-grid">
          {FLAG_CONFIG.map((flag, index) => {
            const Icon = flag.icon;
            const isOn = flags?.[flag.key] ?? false;
            return (
              <motion.div
                key={flag.key}
                className={`ff-card ${isOn ? 'active' : 'inactive'}`}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.08, duration: 0.4 }}
                whileHover={{ y: -4, scale: 1.02 }}
              >
                <div className="ff-card-header">
                  <div className="ff-card-icon" style={{ background: `${flag.color}20`, color: flag.color }}>
                    <Icon size={22} />
                  </div>
                  <motion.button
                    className={`ff-toggle ${isOn ? 'on' : 'off'}`}
                    onClick={() => toggleFlag(flag.key)}
                    whileTap={{ scale: 0.9 }}
                    style={isOn ? { background: `linear-gradient(135deg, ${flag.color}, ${flag.color}cc)` } : {}}
                  >
                    <motion.div
                      className="ff-toggle-knob"
                      animate={{ x: isOn ? 22 : 2 }}
                      transition={{ type: 'spring', stiffness: 500, damping: 30 }}
                    />
                  </motion.button>
                </div>
                <h3 className="ff-card-title">{flag.label}</h3>
                <p className="ff-card-desc">{flag.description}</p>
                <div className={`ff-status ${isOn ? 'on' : 'off'}`}>
                  {isOn ? 'ENABLED' : 'DISABLED'}
                </div>
              </motion.div>
            );
          })}

          {/* Max Lectures Card (Slider) */}
          <motion.div
            className="ff-card active"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: FLAG_CONFIG.length * 0.08, duration: 0.4 }}
            whileHover={{ y: -4, scale: 1.02 }}
          >
            <div className="ff-card-header">
              <div className="ff-card-icon" style={{ background: '#f9731620', color: '#f97316' }}>
                <GraduationCap size={22} />
              </div>
              <span className="ff-slider-value">{maxLectures}</span>
            </div>
            <h3 className="ff-card-title">Max Lectures / Day</h3>
            <p className="ff-card-desc">Global cap on how many classes any teacher can have per day</p>
            <input
              type="range"
              min="1"
              max="8"
              value={maxLectures}
              onChange={(e) => {
                setMaxLectures(parseInt(e.target.value));
                setSaveResult(null);
              }}
              className="ff-slider"
            />
            <div className="ff-slider-labels">
              <span>1</span>
              <span>4</span>
              <span>8</span>
            </div>
          </motion.div>
        </div>

        {/* Action Bar */}
        <motion.div className="ff-actions"
          initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.5 }}>
          {saveResult && (
            <motion.div
              className={`ff-result ${saveResult.type}`}
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
            >
              {saveResult.type === 'success' ?
                <CheckCircle2 size={18} /> : <AlertTriangle size={18} />}
              {saveResult.message}
            </motion.div>
          )}
          <div className="ff-action-buttons">
            <motion.button className="ff-btn ff-btn-reset" onClick={handleReset}
              disabled={!hasChanges}
              whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}>
              <RotateCcw size={18} />
              Reset
            </motion.button>
            <motion.button className="ff-btn ff-btn-save" onClick={handleSave}
              disabled={saving}
              whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}>
              {saving ? <><Loader2 className="animate-spin" size={18} /> Saving...</> :
                <><Save size={18} /> Save Settings</>}
            </motion.button>
          </div>
        </motion.div>
      </div>
    </div>
  );
};

export default FeatureFlags;
