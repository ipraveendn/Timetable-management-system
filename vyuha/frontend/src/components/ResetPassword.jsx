import { useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Lock, Eye, EyeOff, ArrowLeft, Sparkles, GraduationCap } from 'lucide-react';
import { authAPI, normalizeApiError } from '../lib/api';
import './Login.css';

const ResetPassword = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const token = searchParams.get('token') || '';

  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');

    if (!token) {
      setError('Missing reset token. Open the reset link from your email again.');
      return;
    }

    if (newPassword !== confirmPassword) {
      setError('Passwords do not match.');
      return;
    }

    setLoading(true);
    try {
      const response = await authAPI.resetPassword(token, newPassword);
      setSuccess(response.message || 'Password reset successfully.');
      setTimeout(() => navigate('/login'), 1500);
    } catch (err) {
      setError(normalizeApiError(err, 'Unable to reset password'));
    } finally {
      setLoading(false);
    }
  };

  const cardVariants = {
    hidden: { opacity: 0, y: 40 },
    visible: { opacity: 1, y: 0, transition: { duration: 0.7 } },
  };

  return (
    <div className="login-container-3d">
      <div className="animated-bg">
        <motion.div className="floating-shape shape-1" animate={{ y: [-20, 20, -20] }} transition={{ duration: 6, repeat: Infinity }} />
        <motion.div className="floating-shape shape-2" animate={{ y: [20, -20, 20] }} transition={{ duration: 7, repeat: Infinity }} />
        <motion.div className="gradient-overlay" />
      </div>

      <motion.div className="glass-card" variants={cardVariants} initial="hidden" animate="visible">
        <div className="logo-section-3d">
          <div className="logo-glow">
            <GraduationCap size={52} />
          </div>
          <h1 className="app-title">VYUHA</h1>
          <p className="app-subtitle">Create a new password</p>
        </div>

        {!token && (
          <div className="error-message">
            No reset token found. Use the link from your email or request a new one.
          </div>
        )}
        {error && <div className="error-message">{error}</div>}
        {success && <div className="error-message success">{success}</div>}

        <form className="login-form-3d" onSubmit={handleSubmit}>
          <div className="input-group-3d">
            <Lock size={20} className="input-icon" />
            <input
              type={showPassword ? 'text' : 'password'}
              placeholder="New password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              required
            />
            <button type="button" className="toggle-password" onClick={() => setShowPassword((v) => !v)}>
              {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
            </button>
          </div>

          <div className="input-group-3d">
            <Lock size={20} className="input-icon" />
            <input
              type={showPassword ? 'text' : 'password'}
              placeholder="Confirm new password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              required
            />
          </div>

          <button type="submit" className="submit-btn-3d" disabled={loading || !token}>
            <Sparkles size={18} className="btn-icon" />
            {loading ? 'Resetting...' : 'Reset password'}
          </button>
        </form>

        <div className="toggle-section">
          <p>
            <Link to="/forgot-password" className="toggle-btn">
              Request another link
            </Link>
          </p>
          <p>
            <Link to="/login" className="toggle-btn">
              <ArrowLeft size={16} style={{ display: 'inline', marginRight: 6 }} />
              Back to Sign In
            </Link>
          </p>
        </div>
      </motion.div>
    </div>
  );
};

export default ResetPassword;
