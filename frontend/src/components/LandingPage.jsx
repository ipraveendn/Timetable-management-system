import React from 'react';
import { motion, useScroll, useTransform } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import { Sparkles, Calendar, Users, Zap, CheckCircle2 } from 'lucide-react';
import './LandingPage.css';

const LandingPage = () => {
  const navigate = useNavigate();
  const { scrollYProgress } = useScroll();
  
  // Parallax transforms
  const yHero = useTransform(scrollYProgress, [0, 1], [0, 800]);
  const opacityHero = useTransform(scrollYProgress, [0, 0.2], [1, 0]);
  const scaleHero = useTransform(scrollYProgress, [0, 0.2], [1, 0.8]);

  return (
    <div className="landing-container">
      {/* Background Animated Grid & Glow */}
      <div className="landing-bg-glow" />
      <div className="landing-grid" />

      {/* Navigation */}
      <nav className="landing-nav">
        <div className="landing-logo">
          <Sparkles className="landing-logo-icon" size={28} />
          VYUHA
        </div>
        <button className="landing-login-btn" onClick={() => navigate('/login')}>
          Login / Request College
        </button>
      </nav>

      {/* Hero Section */}
      <section className="landing-section" style={{ minHeight: '100vh', justifyContent: 'center' }}>
        <motion.div 
          style={{ y: yHero, opacity: opacityHero, scale: scaleHero }}
          className="hero-content"
          initial={{ opacity: 0, y: 50 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 1, ease: "easeOut" }}
        >
          <h1 className="hero-title">
            The Future of <span>Intelligent Timetables</span>
          </h1>
          <p className="hero-subtitle">
            VYUHA is a state-of-the-art scheduling and substitution engine designed for modern colleges. 
            Automate timetable generation, manage faculty leaves, and eliminate conflicts instantly.
          </p>
          <div className="hero-cta-container" style={{ justifyContent: 'center' }}>
            <button className="hero-cta-primary" onClick={() => navigate('/login')}>
              Get Started
            </button>
            <button className="hero-cta-secondary" onClick={() => {
              document.getElementById('features').scrollIntoView({ behavior: 'smooth' });
            }}>
              Explore Features
            </button>
          </div>
        </motion.div>
      </section>

      {/* Features Section */}
      <section className="landing-section" id="features">
        <motion.h2 
          className="section-heading"
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
        >
          Unrivaled Capabilities
        </motion.h2>
        
        <div className="features-grid">
          {[
            {
              icon: <Calendar size={30} />,
              title: "Smart Timetable Engine",
              desc: "Rule-based conflict resolution ensuring no room, subject, or faculty clashes with automated load-balancing."
            },
            {
              icon: <Zap size={30} />,
              title: "Effortless Substitution",
              desc: "Instantly finds the best available substitute based on department, workload, and subject expertise."
            },
            {
              icon: <Users size={30} />,
              title: "Centralized Portals",
              desc: "Dedicated interfaces for Admins, Principals, and Teachers with seamless leave request integration."
            }
          ].map((feature, idx) => (
            <motion.div 
              key={idx}
              className="feature-card"
              initial={{ opacity: 0, y: 50 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: idx * 0.2 }}
            >
              <div className="feature-icon-container">
                {feature.icon}
              </div>
              <h3 className="feature-title">{feature.title}</h3>
              <p className="feature-desc">{feature.desc}</p>
            </motion.div>
          ))}
        </div>
      </section>

      {/* Pricing Section */}
      <section className="landing-section" id="pricing">
        <motion.h2 
          className="section-heading"
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
        >
          Transparent Pricing
        </motion.h2>

        <div className="pricing-grid">
          {/* Single Premium Tier */}
          <motion.div 
            className="pricing-card featured"
            initial={{ opacity: 0, y: 50 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
          >
            <div className="pricing-badge">Full Access</div>
            <div className="pricing-tier" style={{ color: 'white' }}>Premium</div>
            <div className="pricing-price" style={{ color: 'white' }}>₹999<span>/month</span></div>
            <p style={{ color: '#d1d5db', marginBottom: '1rem' }}>The complete solution for modern institution management.</p>
            <ul className="pricing-features">
              <li style={{ color: 'white' }}><CheckCircle2 size={18} /> Unlimited Faculty Records</li>
              <li style={{ color: 'white' }}><CheckCircle2 size={18} /> Automated Timetable Generation</li>
              <li style={{ color: 'white' }}><CheckCircle2 size={18} /> Advanced AI-Powered Scheduling</li>
              <li style={{ color: 'white' }}><CheckCircle2 size={18} /> Effortless Faculty Substitution</li>
              <li style={{ color: 'white' }}><CheckCircle2 size={18} /> Custom Onboarding & Support</li>
            </ul>
            <button className="pricing-btn primary" onClick={() => navigate('/login')}>
              Get Started
            </button>
          </motion.div>
        </div>
      </section>

      {/* Footer */}
      <footer style={{ padding: '2rem', textAlign: 'center', color: '#6b7280', borderTop: '1px solid rgba(255,255,255,0.05)', backdropFilter: 'blur(10px)' }}>
        <p>© 2026 VYUHA. All rights reserved.</p>
      </footer>
    </div>
  );
};

export default LandingPage;
