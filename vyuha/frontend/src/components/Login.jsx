import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { GraduationCap, Mail, Lock, Building2, Eye, EyeOff, Sparkles, ArrowLeft } from 'lucide-react';
import { useAuth } from '../lib/AuthProvider';
import { authAPI, normalizeApiError } from '../lib/api';
import './Login.css';

const Login = () => {
  const { login, register } = useAuth();
  const navigate = useNavigate();
  
  const [mode, setMode] = useState('login'); // login | register | request_college
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  const [collegeId, setCollegeId] = useState('');
  const [collegeName, setCollegeName] = useState('');
  const [collegeCode, setCollegeCode] = useState('');
  const [contactEmail, setContactEmail] = useState('');
  const [requestAdminName, setRequestAdminName] = useState('');
  const [requestAdminEmail, setRequestAdminEmail] = useState('');
  const [requestAdminPassword, setRequestAdminPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [showRequestPassword, setShowRequestPassword] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    setSuccess('');

    try {
      if (mode === 'login') {
        // Sign in with new auth system
        const result = await login(email, password);
        if (result.success) {
          // Navigate based on role
          if (result.user.role === 'superadmin') {
            navigate('/superadmin');
          } else {
            navigate('/dashboard');
          }
        } else {
          setError(result.error);
        }
      } else if (mode === 'register') {
        // Sign up
        const result = await register({
          email,
          password,
          name,
          college_id: collegeId,
          role: 'faculty'
        });
        if (result.success) {
          setSuccess('Registration submitted! Please wait for college admin approval.');
          setMode('login');
        } else {
          setError(result.error);
        }
      } else {
        const response = await authAPI.requestCollege({
          name: collegeName,
          code: collegeCode,
          contact_email: contactEmail,
          admin_name: requestAdminName,
          admin_email: requestAdminEmail,
          admin_password: requestAdminPassword
        });
        setSuccess(`${response.message} Your college ID: ${response.college_id}`);
        setMode('login');
      }
    } catch (err) {
      setError(normalizeApiError(err, 'An error occurred'));
    } finally {
      setLoading(false);
    }
  };

  // Floating animation variants
  const floatingVariants = {
    animate: {
      y: [-20, 20, -20],
      rotate: [0, 10, -10, 0],
      transition: {
        duration: 6,
        repeat: Infinity,
        ease: "easeInOut"
      }
    }
  };

  const cardVariants = {
    hidden: { 
      opacity: 0, 
      y: 50,
      rotateX: -15
    },
    visible: { 
      opacity: 1, 
      y: 0,
      rotateX: 0,
      transition: {
        duration: 0.8,
        ease: "easeOut"
      }
    }
  };

  const inputVariants = {
    focus: { 
      scale: 1.02,
      boxShadow: "0 0 20px rgba(0, 123, 255, 0.3)",
      transition: { duration: 0.2 }
    }
  };

  return (
    <div className="login-container-3d">
      {/* Animated Background */}
      <div className="animated-bg">
        <motion.div 
          className="floating-shape shape-1"
          variants={floatingVariants}
          animate="animate"
        />
        <motion.div 
          className="floating-shape shape-2"
          variants={floatingVariants}
          animate="animate"
          style={{ animationDelay: "2s" }}
        />
        <motion.div 
          className="floating-shape shape-3"
          variants={floatingVariants}
          animate="animate"
          style={{ animationDelay: "4s" }}
        />
        <div className="gradient-overlay" />
      </div>

      {/* Glass Card */}
      <motion.div 
        className="glass-card"
        variants={cardVariants}
        initial="hidden"
        animate="visible"
        style={{ perspective: 1000, position: 'relative' }}
      >
        <button 
          onClick={() => navigate('/')}
          style={{ position: 'absolute', top: '20px', left: '20px', background: 'transparent', border: 'none', color: 'rgba(255,255,255,0.6)', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '6px', fontSize: '14px', transition: 'color 0.2s', zIndex: 10 }}
          onMouseEnter={(e) => e.currentTarget.style.color = 'white'}
          onMouseLeave={(e) => e.currentTarget.style.color = 'rgba(255,255,255,0.6)'}
        >
          <ArrowLeft size={16} /> Home
        </button>

        {/* Logo Section */}
        <motion.div 
          className="logo-section-3d"
          whileHover={{ scale: 1.05, rotateY: 10 }}
          transition={{ type: "spring", stiffness: 300 }}
        >
          <div className="logo-glow">
            <GraduationCap size={56} />
          </div>
          <motion.h1 
            className="app-title"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
          >
            VYUHA
          </motion.h1>
          <motion.p 
            className="app-subtitle"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.4 }}
          >
            AI-Powered Timetable & Substitution System
          </motion.p>
        </motion.div>

        {/* Form Section */}
        <motion.form 
          onSubmit={handleSubmit}
          className="login-form-3d"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.5 }}
        >
          <AnimatePresence mode="wait">
            {(error || success) && (
              <motion.div 
                className={`error-message ${success ? 'success' : ''}`}
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
              >
                {success || error}
              </motion.div>
            )}
          </AnimatePresence>

          {mode === 'register' && (
            <>
              <motion.div 
                className="input-group-3d"
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.1 }}
              >
                <Building2 size={20} className="input-icon" />
                <motion.input
                  type="text"
                  placeholder="Full Name"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  required={mode === 'register'}
                  whileFocus="focus"
                  variants={inputVariants}
                />
              </motion.div>
              <motion.div 
                className="input-group-3d"
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.15 }}
              >
                <Building2 size={20} className="input-icon" />
                <motion.input
                  type="text"
                  placeholder="College ID"
                  value={collegeId}
                  onChange={(e) => setCollegeId(e.target.value)}
                  required={mode === 'register'}
                  whileFocus="focus"
                  variants={inputVariants}
                />
              </motion.div>
            </>
          )}

          {mode === 'request_college' && (
            <>
              <motion.div className="input-group-3d" initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }}>
                <Building2 size={20} className="input-icon" />
                <motion.input type="text" placeholder="College Name" value={collegeName} onChange={(e) => setCollegeName(e.target.value)} required whileFocus="focus" variants={inputVariants} />
              </motion.div>
              <motion.div className="input-group-3d" initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }}>
                <Building2 size={20} className="input-icon" />
                <motion.input type="text" placeholder="College Code (e.g. PCCE)" value={collegeCode} onChange={(e) => setCollegeCode(e.target.value)} required whileFocus="focus" variants={inputVariants} />
              </motion.div>
              <motion.div className="input-group-3d" initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }}>
                <Mail size={20} className="input-icon" />
                <motion.input type="email" placeholder="College Contact Email" value={contactEmail} onChange={(e) => setContactEmail(e.target.value)} required whileFocus="focus" variants={inputVariants} />
              </motion.div>
              <motion.div className="input-group-3d" initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }}>
                <Building2 size={20} className="input-icon" />
                <motion.input type="text" placeholder="Proposed Admin Name" value={requestAdminName} onChange={(e) => setRequestAdminName(e.target.value)} required whileFocus="focus" variants={inputVariants} />
              </motion.div>
              <motion.div className="input-group-3d" initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }}>
                <Mail size={20} className="input-icon" />
                <motion.input type="email" placeholder="Proposed Admin Email" value={requestAdminEmail} onChange={(e) => setRequestAdminEmail(e.target.value)} required whileFocus="focus" variants={inputVariants} />
              </motion.div>
            </>
          )}

          {mode !== 'request_college' ? (
            <>
              <motion.div 
                className="input-group-3d"
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.2 }}
              >
                <Mail size={20} className="input-icon" />
                <motion.input
                  type="email"
                  placeholder="Email address"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  whileFocus="focus"
                  variants={inputVariants}
                />
              </motion.div>

              <motion.div 
                className="input-group-3d"
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.3 }}
              >
                <Lock size={20} className="input-icon" />
                <motion.input
                  type={showPassword ? "text" : "password"}
                  placeholder="Password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  whileFocus="focus"
                  variants={inputVariants}
                />
                <button 
                  type="button"
                  className="toggle-password"
                  onClick={() => setShowPassword(!showPassword)}
                >
                  {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                </button>
              </motion.div>
            </>
          ) : (
            <motion.div className="input-group-3d" initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }}>
              <Lock size={20} className="input-icon" />
              <motion.input
                type={showRequestPassword ? "text" : "password"}
                placeholder="Admin Password (min 8)"
                value={requestAdminPassword}
                onChange={(e) => setRequestAdminPassword(e.target.value)}
                required
                minLength={8}
                whileFocus="focus"
                variants={inputVariants}
              />
              <button type="button" className="toggle-password" onClick={() => setShowRequestPassword(!showRequestPassword)}>
                {showRequestPassword ? <EyeOff size={18} /> : <Eye size={18} />}
              </button>
            </motion.div>
          )}

          {mode === 'login' && (
            <motion.div 
              className="form-options"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.4 }}
            >
              <label className="remember-me">
                <input type="checkbox" />
                <span>Remember me</span>
              </label>
              <button
                type="button"
                className="forgot-password"
                onClick={() => navigate('/forgot-password')}
              >
                Forgot password?
              </button>
            </motion.div>
          )}

          <motion.button 
            type="submit" 
            className="submit-btn-3d"
            disabled={loading}
            whileHover={{ 
              scale: 1.02,
              boxShadow: "0 20px 40px rgba(0, 123, 255, 0.4)"
            }}
            whileTap={{ scale: 0.98 }}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.5 }}
          >
            <Sparkles size={18} className="btn-icon" />
            {loading ? 'Processing...' : (mode === 'login' ? 'Sign In' : (mode === 'register' ? 'Register User' : 'Request College Approval'))}
          </motion.button>
        </motion.form>

        {/* Toggle Section */}
        <motion.div 
          className="toggle-section"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.6 }}
        >
          <p>
            {mode === 'login' ? "New here?" : "Already registered?"}
            <button 
              type="button"
              className="toggle-btn"
              onClick={() => {
                setMode(mode === 'login' ? 'register' : 'login');
                setError('');
                setSuccess('');
              }}
            >
              {mode === 'login' ? 'Register User' : 'Sign In'}
            </button>
            {mode !== 'request_college' && (
              <button
                type="button"
                className="toggle-btn"
                onClick={() => {
                  setMode('request_college');
                  setError('');
                  setSuccess('');
                }}
              >
                Request College
              </button>
            )}
            {mode === 'request_college' && (
              <button
                type="button"
                className="toggle-btn"
                onClick={() => {
                  setMode('login');
                  setError('');
                  setSuccess('');
                }}
              >
                Back to Sign In
              </button>
            )}
          </p>
        </motion.div>

      </motion.div>
    </div>
  );
};

export default Login;
