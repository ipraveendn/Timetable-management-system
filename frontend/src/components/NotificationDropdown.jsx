import React, { useState, useEffect, useRef } from 'react';
import { Bell, Check } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { autoHandlerAPI } from '../lib/api';

const NotificationDropdown = () => {
  const [notifications, setNotifications] = useState([]);
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef(null);

  const fetchNotifications = async () => {
    try {
      const res = await autoHandlerAPI.getNotifications();
      setNotifications(res.notifications || res || []);
    } catch (err) {
      console.error("Failed to load notifications", err);
    }
  };

  useEffect(() => {
    const init = async () => {
      await fetchNotifications();
    };
    init();
    const interval = setInterval(fetchNotifications, 30000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const markAsRead = async (id, e) => {
    if (e) e.stopPropagation();
    try {
      await autoHandlerAPI.markNotificationRead(id);
      setNotifications(notifications.map(n => n.id === id ? { ...n, is_read: true } : n));
    } catch (err) {
      console.error(err);
    }
  };

  const markAllRead = async () => {
    try {
      await autoHandlerAPI.markAllNotificationsRead();
      setNotifications(notifications.map(n => ({ ...n, is_read: true })));
    } catch (err) {
      console.error(err);
    }
  };

  const unreadCount = notifications.filter(n => !n.is_read).length;

  return (
    <div ref={dropdownRef} style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
      <motion.button 
        whileHover={{ scale: 1.1 }} 
        whileTap={{ scale: 0.95 }}
        onClick={() => setIsOpen(!isOpen)}
        style={{ 
          background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.1)', 
          borderRadius: '50%', width: '40px', height: '40px', display: 'flex', 
          alignItems: 'center', justifyContent: 'center', cursor: 'pointer',
          position: 'relative', color: 'rgba(255,255,255,0.8)', marginRight: '1rem'
        }}
      >
        <Bell size={20} />
        {unreadCount > 0 && (
          <span style={{
            position: 'absolute', top: '-2px', right: '-2px', background: '#ef4444', 
            color: 'white', fontSize: '0.7rem', fontWeight: 'bold', 
            width: '18px', height: '18px', borderRadius: '50%', 
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            boxShadow: '0 0 10px rgba(239, 68, 68, 0.5)'
          }}>
            {unreadCount > 9 ? '9+' : unreadCount}
          </span>
        )}
      </motion.button>

      <AnimatePresence>
        {isOpen && (
          <motion.div 
            initial={{ opacity: 0, y: 10, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 10, scale: 0.95 }}
            transition={{ duration: 0.2 }}
            style={{
              position: 'absolute', top: '50px', right: 0, width: '320px',
              background: 'rgba(15, 20, 30, 0.95)', backdropFilter: 'blur(16px)',
              border: '1px solid rgba(124,58,237,0.3)', borderRadius: '12px',
              boxShadow: '0 10px 40px rgba(0,0,0,0.5)', zIndex: 1000, overflow: 'hidden'
            }}
          >
            <div style={{ padding: '1rem', borderBottom: '1px solid rgba(255,255,255,0.08)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <h4 style={{ margin: 0, color: 'white' }}>Notifications</h4>
              {unreadCount > 0 && (
                <button onClick={markAllRead} style={{ background: 'transparent', border: 'none', color: '#a78bfa', fontSize: '0.8rem', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '4px' }}>
                  <Check size={14}/> Mark all read
                </button>
              )}
            </div>
            
            <div style={{ maxHeight: '350px', overflowY: 'auto', padding: '0.5rem' }}>
              {notifications.length === 0 ? (
                <div style={{ padding: '2rem', textAlign: 'center', color: 'rgba(255,255,255,0.4)', fontSize: '0.9rem' }}>
                  <Bell size={24} style={{ opacity: 0.2, marginBottom: '0.5rem', display: 'inline-block' }} />
                  <div>No notifications yet</div>
                </div>
              ) : (
                notifications.map(n => (
                  <div key={n.id} 
                    onClick={() => markAsRead(n.id)}
                    style={{ 
                      padding: '0.75rem', borderRadius: '8px', marginBottom: '0.5rem', 
                      background: n.is_read ? 'transparent' : 'rgba(124,58,237,0.1)', 
                      borderLeft: n.is_read ? '2px solid transparent' : '2px solid #a78bfa',
                      cursor: n.is_read ? 'default' : 'pointer',
                      transition: 'background 0.2s'
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '4px' }}>
                      <strong style={{ color: n.is_read ? 'rgba(255,255,255,0.6)' : 'white', fontSize: '0.9rem' }}>{n.title}</strong>
                      {!n.is_read && <div style={{ minWidth: '8px', minHeight: '8px', background: '#a78bfa', borderRadius: '50%' }}/>}
                    </div>
                    <div style={{ color: 'rgba(255,255,255,0.5)', fontSize: '0.8rem', lineHeight: '1.4' }}>
                      {n.message}
                    </div>
                    <div style={{ marginTop: '0.5rem', fontSize: '0.7rem', color: 'rgba(255,255,255,0.3)' }}>
                       {new Date(n.created_at).toLocaleString()}
                    </div>
                  </div>
                ))
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default NotificationDropdown;
