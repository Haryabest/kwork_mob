import '@mantine/core/styles.css';
import '@mantine/notifications/styles.css';
import './styles/vektor.css';

import { MantineProvider } from '@mantine/core';
import { Notifications } from '@mantine/notifications';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import { AuthProvider } from './auth/AuthContext';
import { defaultRouteFor } from './auth/roles';
import AppLayout from './components/AppLayout';
import ProtectedRoute from './components/ProtectedRoute';
import LoginPage from './pages/LoginPage';
import DashboardPage from './pages/DashboardPage';
import WorkersPage from './pages/WorkersPage';
import UsersPage from './pages/UsersPage';
import CompaniesPage from './pages/CompaniesPage';
import PromocodesPage from './pages/PromocodesPage';
import AnalyticsPage from './pages/AnalyticsPage';
import CampaignsPage from './pages/CampaignsPage';
import PushPage from './pages/PushPage';
import ModerationPage from './pages/ModerationPage';
import TaxPage from './pages/TaxPage';
import LegalPage from './pages/LegalPage';
import SettingsPage from './pages/SettingsPage';
import LogsPage from './pages/LogsPage';
import AlertLogPage from './pages/AlertLogPage';
import StoragePage from './pages/StoragePage';
import SoftLaunchPage from './pages/SoftLaunchPage';
import MaintenancePage from './pages/MaintenancePage';
import WebhooksDashboardPage from './pages/WebhooksDashboardPage';
import MarketplacePage from './pages/MarketplacePage';
import AccessLogPage from './pages/AccessLogPage';
import TaskConflictsPage from './pages/TaskConflictsPage';
import WatermarkVerifyPage from './pages/WatermarkVerifyPage';
import TicketsPage from './pages/support/TicketsPage';
import TicketDetailPage from './pages/support/TicketDetailPage';
import FaqEditorPage from './pages/support/FaqEditorPage';
import SupportStatsPage from './pages/support/SupportStatsPage';
import { CompanyDetailPage, InvitationsPage, UserDetailPage } from './pages/AdminPages';
import { theme } from './theme';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { staleTime: 15_000, refetchOnWindowFocus: false, retry: 1 },
  },
});

function RootRedirect() {
  const raw = localStorage.getItem('staff_user');
  if (!raw) return <Navigate to="/login" replace />;
  const user = JSON.parse(raw) as { role: 'admin' | 'support_agent' };
  return <Navigate to={defaultRouteFor(user.role)} replace />;
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <MantineProvider theme={theme} defaultColorScheme="light">
      <Notifications position="top-right" />
      <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route element={<ProtectedRoute />}>
              <Route element={<AppLayout />}>
                <Route path="/" element={<DashboardPage />} />
                <Route path="/workers" element={<WorkersPage />} />
                <Route path="/soft-launch" element={<SoftLaunchPage />} />
                <Route path="/maintenance" element={<MaintenancePage />} />
                <Route path="/webhooks" element={<WebhooksDashboardPage />} />
                <Route path="/marketplace" element={<MarketplacePage />} />
                <Route path="/access-log" element={<AccessLogPage />} />
                <Route path="/task-conflicts" element={<TaskConflictsPage />} />
                <Route path="/watermark-verify" element={<WatermarkVerifyPage />} />
                <Route path="/users" element={<UsersPage />} />
                <Route path="/users/:id" element={<UserDetailPage />} />
                <Route path="/companies" element={<CompaniesPage />} />
                <Route path="/companies/:id" element={<CompanyDetailPage />} />
                <Route path="/invitations" element={<InvitationsPage />} />
                <Route path="/promocodes" element={<PromocodesPage />} />
                <Route path="/campaigns" element={<CampaignsPage />} />
                <Route path="/analytics" element={<AnalyticsPage />} />
                <Route path="/push" element={<PushPage />} />
                <Route path="/moderation" element={<ModerationPage />} />
                <Route path="/tax" element={<TaxPage />} />
                <Route path="/legal" element={<LegalPage />} />
                <Route path="/settings" element={<SettingsPage />} />
                <Route path="/logs" element={<LogsPage />} />
                <Route path="/alert-log" element={<AlertLogPage />} />
                <Route path="/storage" element={<StoragePage />} />
                <Route path="/support/tickets" element={<TicketsPage />} />
                <Route path="/support/tickets/:id" element={<TicketDetailPage />} />
                <Route path="/support/faq" element={<FaqEditorPage />} />
                <Route path="/support/stats" element={<SupportStatsPage />} />
              </Route>
            </Route>
            <Route path="*" element={<RootRedirect />} />
          </Routes>
        </BrowserRouter>
      </AuthProvider>
      </QueryClientProvider>
    </MantineProvider>
  </React.StrictMode>,
);
