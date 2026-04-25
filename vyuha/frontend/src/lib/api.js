import axios from 'axios';

const DEFAULT_LOCAL_API_URL = 'http://localhost:8000';

const normalizeBaseUrl = (value) => {
  if (!value) return '';
  return value.trim().replace(/\/+$/, '');
};

const resolveApiBaseUrl = () => {
  if (import.meta.env.DEV) {
    return '/api';
  }

  const configured = normalizeBaseUrl(import.meta.env.VITE_API_URL);
  if (configured) return configured;

  if (typeof window === 'undefined') {
    return DEFAULT_LOCAL_API_URL;
  }

  if (window.location.protocol === 'file:') {
    return DEFAULT_LOCAL_API_URL;
  }

  const hostname = window.location.hostname;
  const isLocalHost = ['localhost', '127.0.0.1', '0.0.0.0'].includes(hostname);
  return isLocalHost ? DEFAULT_LOCAL_API_URL : window.location.origin;
};

const API_BASE_URL = resolveApiBaseUrl();

export const getApiBaseUrl = () => API_BASE_URL;

export const normalizeApiError = (error, fallback = 'Request failed') => {
  // Backend responded with structured error
  if (error?.response?.data?.detail) return error.response.data.detail;
  if (error?.response?.data?.message) return error.response.data.message;

  // No response means connectivity/CORS/mixed-content issue
  if (!error?.response && (error?.message === 'Network Error' || error?.code === 'ERR_NETWORK')) {
    return `Cannot reach backend API at ${API_BASE_URL}. Set VITE_API_URL to a reachable backend URL or serve the API from the same origin.`;
  }

  return error?.message || fallback;
};

// Create axios instance
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Token management
export const setAuthToken = (token) => {
  if (token) {
    apiClient.defaults.headers.common['Authorization'] = `Bearer ${token}`;
    localStorage.setItem('auth_token', token);
  } else {
    delete apiClient.defaults.headers.common['Authorization'];
    localStorage.removeItem('auth_token');
  }
};

export const getAuthToken = () => {
  return localStorage.getItem('auth_token');
};

// Initialize token from storage
const initToken = getAuthToken();
if (initToken) {
  apiClient.defaults.headers.common['Authorization'] = `Bearer ${initToken}`;
}

// Add college_id to all requests
apiClient.interceptors.request.use(async (config) => {
  // Get college_id from stored user data or token
  const userData = localStorage.getItem('user_data');
  let collegeId = 'DEFAULT';
  
  if (userData) {
    try {
      const user = JSON.parse(userData);
      collegeId = user.college_id || 'DEFAULT';
    } catch (e) {
      console.error('Error parsing user data:', e);
    }
  }

  const normalizedCollegeId = String(collegeId).trim() || 'DEFAULT';
  config.headers['X-College-ID'] = normalizedCollegeId;
  return config;
});

// ============================================
// AUTH API FUNCTIONS
// ============================================

export const authAPI = {
  // Login with email/password
  login: async (email, password) => {
    const response = await apiClient.post('/auth/login', { email, password });
    return response.data;
  },

  // Register new user
  register: async (userData) => {
    const response = await apiClient.post('/auth/register', userData);
    return response.data;
  },

  // Request new college onboarding (public)
  requestCollege: async (collegeData) => {
    const response = await apiClient.post('/auth/request-college', collegeData);
    return response.data;
  },

  // Get current user profile
  getProfile: async () => {
    const response = await apiClient.get('/auth/me');
    return response.data;
  },

  // Change password
  changePassword: async (oldPassword, newPassword) => {
    const response = await apiClient.put('/auth/password', { old_password: oldPassword, new_password: newPassword });
    return response.data;
  },

  // Request a password reset link
  forgotPassword: async (email) => {
    const response = await apiClient.post('/auth/forgot-password', { email });
    return response.data;
  },

  // Reset password with one-time token
  resetPassword: async (token, newPassword) => {
    const response = await apiClient.post('/auth/reset-password', { token, new_password: newPassword });
    return response.data;
  },

  // Get all users (admin)
  getUsers: async () => {
    const response = await apiClient.get('/auth/users');
    return response.data;
  },

  // Get pending users (admin)
  getPendingUsers: async () => {
    const response = await apiClient.get('/auth/pending-users');
    return response.data;
  },

  // Approve user (admin)
  approveUser: async (pendingId) => {
    const response = await apiClient.post(`/auth/approve-user/${pendingId}`);
    return response.data;
  },

  // Reject user (admin)
  rejectUser: async (pendingId, reason) => {
    const response = await apiClient.post(`/auth/reject-user/${pendingId}?reason=${reason}`);
    return response.data;
  },

  // Change user role (admin)
  changeUserRole: async (userId, newRole) => {
    const response = await apiClient.put(`/auth/users/${userId}/role?new_role=${newRole}`);
    return response.data;
  },

  // Change user status (admin)
  changeUserStatus: async (userId, newStatus) => {
    const response = await apiClient.put(`/auth/users/${userId}/status?new_status=${newStatus}`);
    return response.data;
  },

  // Invite and create a user directly (admin/hod)
  inviteUser: async (payload) => {
    const response = await apiClient.post('/auth/invite-user', payload);
    return response.data;
  },
};

// ============================================
// SUPERADMIN API FUNCTIONS
// ============================================

export const superadminAPI = {
  // Get all colleges
  getColleges: async () => {
    const response = await apiClient.get('/superadmin/colleges');
    return response.data;
  },

  // Create new college
  createCollege: async (data) => {
    const response = await apiClient.post('/superadmin/colleges', data);
    return response.data;
  },

  // Approve college
  approveCollege: async (collegeId) => {
    const response = await apiClient.put(`/superadmin/colleges/${collegeId}/approve`);
    return response.data;
  },

  // Suspend college
  suspendCollege: async (collegeId) => {
    const response = await apiClient.put(`/superadmin/colleges/${collegeId}/suspend`);
    return response.data;
  },

  // Get college details
  getCollegeDetails: async (collegeId) => {
    const response = await apiClient.get(`/superadmin/colleges/${collegeId}/details`);
    return response.data;
  },

  // Get overall stats
  getStats: async () => {
    const response = await apiClient.get('/superadmin/stats');
    return response.data;
  },

  // Get all audit logs
  getAuditLogs: async (collegeId = null) => {
    const response = await apiClient.get('/superadmin/audit-logs', { params: { college_id: collegeId } });
    return response.data;
  },
};

// ============================================
// AUTO HANDLER API FUNCTIONS
// ============================================

export const autoHandlerAPI = {
  // Process leave request (auto-find substitutes)
  processLeave: async (leaveId) => {
    const response = await apiClient.post(`/auto/process-leave/${leaveId}`);
    return response.data;
  },

  // Validate timetable
  validateTimetable: async (autoFix = false) => {
    const response = await apiClient.post(`/auto/validate-timetable?auto_fix=${autoFix}`);
    return response.data;
  },

  // Confirm substitution
  confirmSubstitution: async (substitutionId) => {
    const response = await apiClient.post(`/auto/confirm-substitution/${substitutionId}`);
    return response.data;
  },

  // Generate and validate timetable
  generateAndValidate: async () => {
    const response = await apiClient.post('/auto/generate-and-validate');
    return response.data;
  },

  // Get dashboard stats
  getDashboardStats: async () => {
    const response = await apiClient.get('/auto/dashboard-stats');
    return response.data;
  },

  // Get notifications
  getNotifications: async (unreadOnly = false) => {
    const response = await apiClient.get('/auto/notifications', { params: { unread_only: unreadOnly } });
    return response.data;
  },

  // Mark notification as read
  markNotificationRead: async (notificationId) => {
    const response = await apiClient.put(`/auto/notifications/${notificationId}/read`);
    return response.data;
  },

  // Mark all notifications as read
  markAllNotificationsRead: async () => {
    const response = await apiClient.put('/auto/notifications/read-all');
    return response.data;
  },
};

// ============================================
// TIMETABLE API FUNCTIONS
// ============================================

export const timetableAPI = {
  // Generate timetable
  generate: async () => {
    const response = await apiClient.post('/generate-timetable');
    return response.data;
  },

  // Get timetable
  get: async (semester) => {
    const response = await apiClient.get(`/timetable?semester=${semester}`);
    return response.data;
  },

  // Get faculty timetable
  getFacultyTimetable: async (facultyId) => {
    const response = await apiClient.get(`/timetable/faculty/${facultyId}`);
    return response.data;
  },

  // Get room timetable
  getRoomTimetable: async (roomId) => {
    const response = await apiClient.get(`/timetable/room/${roomId}`);
    return response.data;
  },

  // Export timetable
  export: async (semester, format = 'excel') => {
    const response = await apiClient.get(`/export/timetable?semester=${semester}&format=${format}`, {
      responseType: 'blob',
    });
    return response.data;
  },
};

// ============================================
// LEAVE MANAGEMENT API FUNCTIONS
// ============================================

export const leaveAPI = {
  // Submit leave request
  submit: async (leaveData) => {
    const response = await apiClient.post('/leave/submit', leaveData);
    return response.data;
  },

  // Get all leaves
  getAll: async () => {
    const response = await apiClient.get('/leave/all');
    return response.data;
  },

  // Get pending leaves
  getPending: async () => {
    const response = await apiClient.get('/leave/pending');
    return response.data;
  },

  // Approve leave
  approve: async (leaveId) => {
    const response = await apiClient.post(`/leave/approve/${leaveId}`);
    return response.data;
  },

  // Reject leave
  reject: async (leaveId, reason = '') => {
    const response = await apiClient.post(`/leave/reject/${leaveId}?reason=${encodeURIComponent(reason)}`);
    return response.data;
  },

  // Cancel leave
  cancel: async (leaveId) => {
    const response = await apiClient.post(`/leave/cancel/${leaveId}`);
    return response.data;
  },
};

// ============================================
// SUBSTITUTION API FUNCTIONS
// ============================================

export const substitutionAPI = {
  // Find substitutes for leave
  find: async (leaveId) => {
    const response = await apiClient.post(`/substitution/find/${leaveId}`);
    return response.data;
  },

  // Assign substitute to a specific slot
  assign: async (payload) => {
    // payload should be { leave_id, slot_id, substitute_faculty_id }
    const response = await apiClient.post('/substitution/assign', payload);
    return response.data;
  },

  // Confirm substitution
  confirm: async (substitutionId) => {
    const response = await apiClient.post(`/substitution/confirm/${substitutionId}`);
    return response.data;
  },

  // Reject substitution
  reject: async (substitutionId, reason = '') => {
    const response = await apiClient.post(`/substitution/reject/${substitutionId}?reason=${encodeURIComponent(reason)}`);
    return response.data;
  },

  // Get substitution log
  getLog: async () => {
    const response = await apiClient.get('/substitution/log');
    return response.data;
  },

  // Get pending substitutions
  getPending: async () => {
    const response = await apiClient.get('/substitution/pending');
    return response.data;
  },

  // Get substitutions where current faculty is the substitute
  getMyAssignments: async () => {
    const response = await apiClient.get('/substitution/my-assignments');
    return response.data;
  },

  // Get substitutions where current faculty's class was covered
  getMyCovered: async () => {
    const response = await apiClient.get('/substitution/my-covered');
    return response.data;
  },
};

// ============================================
// ENTITY API FUNCTIONS
// ============================================

export const entityAPI = {
  // Get faculty
  getFaculty: async () => {
    const response = await apiClient.get('/faculty');
    return response.data;
  },

  // Add faculty
  addFaculty: async (facultyData) => {
    const response = await apiClient.post('/faculty', facultyData);
    return response.data;
  },

  // Update faculty
  updateFaculty: async (id, facultyData) => {
    const response = await apiClient.put(`/faculty/${id}`, facultyData);
    return response.data;
  },

  // Delete faculty
  deleteFaculty: async (id) => {
    const response = await apiClient.delete(`/faculty/${id}`);
    return response.data;
  },

  // Get subjects
  getSubjects: async () => {
    const response = await apiClient.get('/subjects');
    return response.data;
  },

  // Add subject
  addSubject: async (subjectData) => {
    const response = await apiClient.post('/subjects', subjectData);
    return response.data;
  },

  // Update subject
  updateSubject: async (id, subjectData) => {
    const response = await apiClient.put(`/subjects/${id}`, subjectData);
    return response.data;
  },

  // Delete subject
  deleteSubject: async (id) => {
    const response = await apiClient.delete(`/subjects/${id}`);
    return response.data;
  },

  // Get rooms
  getRooms: async () => {
    const response = await apiClient.get('/rooms');
    return response.data;
  },

  // Add room
  addRoom: async (roomData) => {
    const response = await apiClient.post('/rooms', roomData);
    return response.data;
  },

  // Update room
  updateRoom: async (id, roomData) => {
    const response = await apiClient.put(`/rooms/${id}`, roomData);
    return response.data;
  },

  // Delete room
  deleteRoom: async (id) => {
    const response = await apiClient.delete(`/rooms/${id}`);
    return response.data;
  },
};

// ============================================
// LEGACY COMPATIBILITY EXPORTS
// ============================================

// Auth
export const login = authAPI.login;
export const register = authAPI.register;
export const getProfile = authAPI.getProfile;
export const forgotPassword = authAPI.forgotPassword;
export const resetPassword = authAPI.resetPassword;

// Faculty
export const getFaculty = entityAPI.getFaculty;
export const addFaculty = entityAPI.addFaculty;
export const updateFaculty = entityAPI.updateFaculty;
export const deleteFaculty = entityAPI.deleteFaculty;

// Subjects
export const getSubjects = entityAPI.getSubjects;
export const addSubject = entityAPI.addSubject;
export const updateSubject = entityAPI.updateSubject;
export const deleteSubject = entityAPI.deleteSubject;

// Rooms
export const getRooms = entityAPI.getRooms;
export const addRoom = entityAPI.addRoom;
export const updateRoom = entityAPI.updateRoom;
export const deleteRoom = entityAPI.deleteRoom;

// Timetable
export const generateTimetable = timetableAPI.generate;
export const getTimetable = timetableAPI.get;
export const getFacultyTimetable = timetableAPI.getFacultyTimetable;
export const getRoomTimetable = timetableAPI.getRoomTimetable;
export const exportTimetable = timetableAPI.export;

// Leave
export const getLeaves = leaveAPI.getAll;
export const submitLeave = leaveAPI.submit;
export const approveLeave = leaveAPI.approve;
export const rejectLeave = leaveAPI.reject;

// Substitution
export const findSubstitution = substitutionAPI.find;
export const assignSubstitute = substitutionAPI.assign;
export const confirmSubstitution = substitutionAPI.confirm;
export const getSubstitutions = substitutionAPI.getLog;

// Feature Flags
export const getFeatureFlags = async () => {
  const response = await apiClient.get('/feature-flags');
  return response.data;
};

export const updateFeatureFlags = async (flags) => {
  const response = await apiClient.put('/feature-flags', flags);
  return response.data;
};

// Chat
export const createChatSession = async (title = 'Chat Session') => {
  const response = await apiClient.post('/chat/session', { title });
  return response.data;
};

export const getChatSessionMessages = async (sessionId, limit = 50) => {
  const response = await apiClient.get(`/chat/session/${sessionId}/messages`, {
    params: { limit },
  });
  return response.data;
};

export const confirmChatAction = async (sessionId, actionType, params = {}) => {
  const response = await apiClient.post('/chat/action/confirm', {
    session_id: sessionId,
    action_type: actionType,
    params,
  });
  return response.data;
};

export const sendChatMessage = async (message, history = [], context = {}, sessionId = null) => {
  const response = await apiClient.post('/chat', {
    message,
    session_id: sessionId || undefined,
    history,
    context,
  });
  return response.data;
};

// Excel
export const uploadExcel = async (file, replaceExisting = true) => {
  const formData = new FormData();
  formData.append('file', file);
  const response = await apiClient.post('/upload-excel', formData, {
    params: { replace_existing: replaceExisting },
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return response.data;
};

export const exportSourceData = async () => {
  const response = await apiClient.get('/export/source-data', {
    responseType: 'blob',
  });
  return response.data;
};

export const approveTimetable = async () => {
  const response = await apiClient.post('/approve-timetable');
  return response.data;
};

export default apiClient;
