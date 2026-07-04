import { Routes, Route, Navigate } from 'react-router-dom';
import AppLayout from './components/layout/AppLayout';
import LoginPage from './pages/Login';
import DashboardPage from './pages/Dashboard';
import MeetingUploadPage from './pages/MeetingUpload';
import MeetingDetailPage from './pages/MeetingDetail';
import TaskManagementPage from './pages/TaskManagement';
import ModelConfigPage from './pages/ModelConfig';
import TokenUsagePage from './pages/TokenUsage';
import ApiManagementPage from './pages/ApiManagement';
import TranslationViewPage from './pages/TranslationView';
import SearchResultPage from './pages/SearchResult';
import { useAuthStore } from './stores/authStore';
import { JSX } from 'react';

function RequireAuth({ children }: { children: JSX.Element }) {
  const isAuth = useAuthStore((s) => s.isAuthenticated());
  return isAuth ? children : <Navigate to="/login" replace />;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        path="/"
        element={
          <RequireAuth>
            <AppLayout />
          </RequireAuth>
        }
      >
        <Route index element={<Navigate to="/dashboard" replace />} />
        <Route path="dashboard" element={<DashboardPage />} />
        <Route path="meetings/upload" element={<MeetingUploadPage />} />
        <Route path="meetings/:id" element={<MeetingDetailPage />} />
        <Route path="tasks" element={<TaskManagementPage />} />
        <Route path="models" element={<ModelConfigPage />} />
        <Route path="token-usage" element={<TokenUsagePage />} />
        <Route path="api-keys" element={<ApiManagementPage />} />
        <Route path="translations/:meetingId" element={<TranslationViewPage />} />
        <Route path="search" element={<SearchResultPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
}
