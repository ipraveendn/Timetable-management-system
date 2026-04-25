/**
 * VYUHA Auth Provider
 * Handles role-based authentication and user context
 */
/* eslint-disable react-refresh/only-export-components */

import { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { authAPI, setAuthToken, autoHandlerAPI, normalizeApiError } from './api';

const AuthContext = createContext(null);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [notifications, setNotifications] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);

  const logout = useCallback(() => {
    setAuthToken(null);
    localStorage.removeItem('auth_token');
    localStorage.removeItem('user_data');
    setUser(null);
    setNotifications([]);
    setUnreadCount(0);
  }, []);

  const fetchNotifications = useCallback(async () => {
    try {
      const response = await autoHandlerAPI.getNotifications();
      setNotifications(response.notifications || []);
      setUnreadCount(response.notifications?.filter(n => !n.is_read).length || 0);
    } catch (e) {
      console.error('Failed to fetch notifications:', e);
    }
  }, []);

  // Initialize auth state from localStorage
  useEffect(() => {
    const initAuth = async () => {
      const token = localStorage.getItem('auth_token');
      const userData = localStorage.getItem('user_data');
      
      if (token && userData) {
        try {
          const parsedUser = JSON.parse(userData);
          setUser(parsedUser);
          setAuthToken(token);
          
          // Fetch fresh profile
          try {
            const profile = await authAPI.getProfile();
            setUser(profile);
            localStorage.setItem('user_data', JSON.stringify(profile));
          } catch (e) {
            // Token might be expired
            console.error('Failed to fetch profile:', e);
          }
        } catch (e) {
          console.error('Failed to parse user data:', e);
          logout();
        }
      }
      setLoading(false);
    };

    initAuth();
  }, [logout]);

  // Fetch notifications when user is logged in
  useEffect(() => {
    if (user) {
      fetchNotifications();
      // Poll for new notifications every 30 seconds
      const interval = setInterval(fetchNotifications, 30000);
      return () => clearInterval(interval);
    }
  }, [user, fetchNotifications]);

  const login = async (email, password) => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await authAPI.login(email, password);
      
      if (response.token && response.user) {
        // Save token and user data
        setAuthToken(response.token);
        localStorage.setItem('auth_token', response.token);
        localStorage.setItem('user_data', JSON.stringify(response.user));
        
        setUser(response.user);
        return { success: true, user: response.user };
      } else {
        throw new Error('Invalid response from server');
      }
    } catch (e) {
      const errorMessage = normalizeApiError(e, 'Login failed');
      setError(errorMessage);
      return { success: false, error: errorMessage };
    } finally {
      setLoading(false);
    }
  };

  const register = async (userData) => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await authAPI.register(userData);
      return { success: true, message: response.message || 'Registration submitted' };
    } catch (e) {
      const errorMessage = normalizeApiError(e, 'Registration failed');
      setError(errorMessage);
      return { success: false, error: errorMessage };
    } finally {
      setLoading(false);
    }
  };

  const markNotificationRead = async (notificationId) => {
    try {
      await autoHandlerAPI.markNotificationRead(notificationId);
      setNotifications(prev => 
        prev.map(n => n.id === notificationId ? { ...n, is_read: true } : n)
      );
      setUnreadCount(prev => Math.max(0, prev - 1));
    } catch (e) {
      console.error('Failed to mark notification as read:', e);
    }
  };

  const markAllNotificationsRead = async () => {
    try {
      await autoHandlerAPI.markAllNotificationsRead();
      setNotifications(prev => prev.map(n => ({ ...n, is_read: true })));
      setUnreadCount(0);
    } catch (e) {
      console.error('Failed to mark all notifications as read:', e);
    }
  };

  const hasRole = useCallback((roles) => {
    if (!user) return false;
    if (!roles) return true;
    
    const roleArray = Array.isArray(roles) ? roles : [roles];
    return roleArray.includes(user.role);
  }, [user]);

  const isAdmin = useCallback(() => {
    return hasRole(['admin', 'superadmin']);
  }, [hasRole]);

  const isHOD = useCallback(() => {
    return hasRole(['admin', 'hod', 'superadmin']);
  }, [hasRole]);

  const isSuperadmin = useCallback(() => {
    return hasRole('superadmin');
  }, [hasRole]);

  const value = {
    user,
    loading,
    error,
    notifications,
    unreadCount,
    login,
    register,
    logout,
    markNotificationRead,
    markAllNotificationsRead,
    hasRole,
    isAdmin,
    isHOD,
    isSuperadmin,
    fetchNotifications,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};

export default AuthProvider;
