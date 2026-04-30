import React from "react";
import "@/App.css";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider, useAuth } from "@/lib/auth";
import { CurrencyProvider } from "@/lib/currency";
import { ThemeProvider } from "@/lib/theme";
import AppLayout from "@/components/AppLayout";
import LoginPage from "@/pages/LoginPage";
import DashboardPage from "@/pages/DashboardPage";
import ProjectsPage from "@/pages/ProjectsPage";
import ProjectDetailPage from "@/pages/ProjectDetailPage";
import MasterPage from "@/pages/MasterPage";
import CustomerProfilePage from "@/pages/CustomerProfilePage";
import UploadsPage from "@/pages/UploadsPage";
import ApprovalsPage from "@/pages/ApprovalsPage";
import AuditPage from "@/pages/AuditPage";
import AdminUsersPage from "@/pages/AdminUsersPage";
import ApprovalMatrixPage from "@/pages/ApprovalMatrixPage";
import SettingsPage from "@/pages/SettingsPage";
import PipelinePage from "@/pages/PipelinePage";
import ChangeRequestsPage from "@/pages/ChangeRequestsPage";
import WBSBudgetPage from "@/pages/WBSBudgetPage";

function Protected({ children, adminOnly }) {
  const { user } = useAuth();
  if (user === null) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[var(--bg)]">
        <div className="text-[var(--muted)] tracking-overline text-xs">Loading…</div>
      </div>
    );
  }
  if (!user) return <Navigate to="/login" replace />;
  if (adminOnly && user.role !== "admin") return <Navigate to="/dashboard" replace />;
  return <AppLayout>{children}</AppLayout>;
}

function App() {
  return (
    <div className="App">
      <BrowserRouter>
        <AuthProvider>
          <ThemeProvider>
            <CurrencyProvider>
              <Routes>
                <Route path="/login" element={<LoginPage />} />
                <Route path="/" element={<Navigate to="/dashboard" replace />} />
                <Route path="/dashboard" element={<Protected><DashboardPage /></Protected>} />
                <Route path="/projects" element={<Protected><ProjectsPage /></Protected>} />
                <Route path="/projects/:id" element={<Protected><ProjectDetailPage /></Protected>} />
                <Route path="/pipeline" element={<Protected><PipelinePage /></Protected>} />
                <Route path="/change-requests" element={<Protected><ChangeRequestsPage /></Protected>} />
                <Route path="/wbs-budget" element={<Protected><WBSBudgetPage /></Protected>} />
                <Route path="/customers" element={<Protected><MasterPage entityKey="customers" /></Protected>} />
                <Route path="/customers/:id" element={<Protected><CustomerProfilePage /></Protected>} />
                <Route path="/suppliers" element={<Protected><MasterPage entityKey="suppliers" /></Protected>} />
                <Route path="/employees" element={<Protected><MasterPage entityKey="employees" /></Protected>} />
                <Route path="/uploads" element={<Protected><UploadsPage /></Protected>} />
                <Route path="/approvals" element={<Protected><ApprovalsPage /></Protected>} />
                <Route path="/audit" element={<Protected><AuditPage /></Protected>} />
                <Route path="/admin/users" element={<Protected adminOnly><AdminUsersPage /></Protected>} />
                <Route path="/admin/approval-matrix" element={<Protected adminOnly><ApprovalMatrixPage /></Protected>} />
                <Route path="/admin/settings" element={<Protected adminOnly><SettingsPage /></Protected>} />
                <Route path="*" element={<Navigate to="/dashboard" replace />} />
              </Routes>
            </CurrencyProvider>
          </ThemeProvider>
        </AuthProvider>
      </BrowserRouter>
    </div>
  );
}

export default App;
