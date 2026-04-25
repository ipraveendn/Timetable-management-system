import { useState } from 'react';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Mail, ArrowLeft, Send, GraduationCap } from 'lucide-react';
import { authAPI, normalizeApiError } from '../lib/api';
import './Login.css';

const ForgotPassword = () => {
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [resetLink, setResetLink] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    setSuccess('');
    setResetLink('');

    try {
      const response = await authAPI.forgotPassword(email);
      setSuccess(response.message || 'If the email exists, a reset link will be sent.');
      if (response.reset_link) {
        setResetLink(response.reset_link);
      }
    } catch (err) {
      setError(normalizeApiError(err, 'Unable to request password reset'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-container-3d">
      <div className="animated-bg">
        <motion.div className="floating-shape shape-1" animate={{ y: [-20, 20, -20] }} transition={{ duration: 6, repeat: Infinity }} />
        <motion.div className="floating-shape shape-2" animate={{ y: [20, -20, 20] }} transition={{ duration: 7, repeat: Infinity }} />
        <motion.div className="gradient-overlay" />
      </div>

      <motion.div className="glass-card" initial={{ opacity: 0, y: 40 }} animate={{ opacity: 1, y: 0 }}>
        <div className="logo-section-3d">
          <div className="logo-glow">
            <GraduationCap size={52} />
          </div>
          <h1 className="app-title">VYUHA</h1>
          <p className="app-subtitle">Reset your account password</p>
        </div>

        {error && <div className="error-message">{error}</div>}
        {success && <div className="error-message success">{success}</div>}
        {resetLink && (
          <div className="error-message success">
            Dev reset link: <a href={resetLink}>{resetLink}</a>
          </div>
        )}

        <form className="login-form-3d" onSubmit={handleSubmit}>
          <div className="input-group-3d">
            <Mail size={20} className="input-icon" />
            <input
              type="email"
              placeholder="Enter your email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </div>

          <button type="submit" className="submit-btn-3d" disabled={loading}>
            <Send size={18} className="btn-icon" />
            {loading ? 'Sending...' : 'Send reset link'}
          </button>
        </form>

        <div className="toggle-section">
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

export default ForgotPassword;
