import { Suspense, lazy } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './lib/AuthProvider';
import './App.css';

const LandingPage = lazy(() => import('./components/LandingPage'));
const Login = lazy(() => import('./components/Login'));
const ForgotPassword = lazy(() => import('./components/ForgotPassword'));
const ResetPassword = lazy(() => import('./components/ResetPassword'));
const Dashboard = lazy(() => import('./components/Dashboard'));
const TimetableEditor = lazy(() => import('./components/TimetableEditor'));
const FacultyManagement = lazy(() => import('./components/FacultyManagement'));
const RoomManagement = lazy(() => import('./components/RoomManagement'));
const SubjectManagement = lazy(() => import('./components/SubjectManagement'));
const ChatAssistant = lazy(() => import('./components/ChatAssistant'));
const FeatureFlags = lazy(() => import('./components/FeatureFlags'));
const SuperAdminPanel = lazy(() => import('./components/SuperAdminPanel'));
const UserManagement = lazy(() => import('./components/UserManagement'));
const FacultyDashboard = lazy(() => import('./components/FacultyDashboard'));
const LeaveManagement = lazy(() => import('./components/LeaveManagement'));

const RouteLoading = () => (
  <div className="loading-screen">
    <div className="loading-spinner">Loading...</div>
  </div>
);

// Role-based route guard component
const ProtectedRoute = ({ children, allowedRoles }) => {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="loading-screen">
        <div className="loading-spinner">Loading...</div>
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  if (allowedRoles && !allowedRoles.includes(user.role)) {
    // Faculty users go to faculty portal, others go to dashboard
    const fallback = user.role === 'faculty' ? '/faculty-portal' : '/dashboard';
    return <Navigate to={fallback} replace />;
  }

  return children;
};


// Role-based dashboard redirect
const DashboardRedirect = () => {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="loading-screen">
        <div className="loading-spinner">Loading...</div>
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  // Redirect based on role
  switch (user.role) {
    case 'superadmin':
      return <Navigate to="/superadmin" replace />;
    case 'admin':
    case 'principal':
      return <Dashboard />;
    case 'faculty':
      return <FacultyDashboard />;
    default:
      return <FacultyDashboard />;
  }
};

function AppRoutes() {
  const { user } = useAuth();

  return (
    <Suspense fallback={<RouteLoading />}>
      <Routes>
        {/* Public routes */}
        <Route 
          path="/login" 
          element={user ? <Navigate to="/dashboard" replace /> : <Login />} 
        />
        <Route path="/forgot-password" element={<ForgotPassword />} />
        <Route path="/reset-password" element={<ResetPassword />} />

        {/* Superadmin only */}
        <Route
          path="/superadmin"
          element={
            <ProtectedRoute allowedRoles={['superadmin']}>
              <SuperAdminPanel />
            </ProtectedRoute>
          }
        />

        {/* Admin and superadmin only */}
        <Route
          path="/users"
          element={
            <ProtectedRoute allowedRoles={['admin', 'superadmin']}>
              <UserManagement />
            </ProtectedRoute>
          }
        />

        {/* Protected routes - any authenticated user */}
        <Route
          path="/dashboard"
          element={
            <ProtectedRoute allowedRoles={['admin', 'principal', 'superadmin']}>
              <DashboardRedirect />
            </ProtectedRoute>
          }
        />
        
        <Route
          path="/faculty-portal"
          element={
            <ProtectedRoute allowedRoles={['faculty', 'admin', 'principal', 'superadmin']}>
              <FacultyDashboard />
            </ProtectedRoute>
          }
        />

        <Route
          path="/timetable"
          element={
            <ProtectedRoute>
              <TimetableEditor />
            </ProtectedRoute>
          }
        />

        <Route
          path="/faculty"
          element={
            <ProtectedRoute>
              <FacultyManagement />
            </ProtectedRoute>
          }
        />

        <Route
          path="/rooms"
          element={
            <ProtectedRoute>
              <RoomManagement />
            </ProtectedRoute>
          }
        />

        <Route
          path="/subjects"
          element={
            <ProtectedRoute>
              <SubjectManagement />
            </ProtectedRoute>
          }
        />

        <Route
          path="/chat"
          element={
            <ProtectedRoute>
              <ChatAssistant />
            </ProtectedRoute>
          }
        />

        <Route
          path="/leave"
          element={
            <ProtectedRoute>
              <LeaveManagement />
            </ProtectedRoute>
          }
        />

        <Route
          path="/settings"
          element={
            <ProtectedRoute>
              <FeatureFlags />
            </ProtectedRoute>
          }
        />

        {/* Default route points to Landing Page */}
        <Route path="/" element={<LandingPage />} />

        {/* 404 fallback */}
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </Suspense>
  );
}

function App() {
  return (
    <AuthProvider>
      <Router>
        <div className="app">
          <AppRoutes />
        </div>
      </Router>
    </AuthProvider>
  );
}

export default App;
