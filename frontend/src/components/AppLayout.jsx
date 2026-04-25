import React from "react";
import { NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "@/lib/auth";
import { useCurrency } from "@/lib/currency";
import {
  ChartLineUp, FolderSimple, Database, UploadSimple, GavelIcon,
  ShieldCheck, ClockCounterClockwise, SignOut, Wallet, UsersThree, Truck, UserCircle,
} from "@phosphor-icons/react";

const NAV = [
  { to: "/dashboard", label: "Dashboard", icon: ChartLineUp, testid: "nav-dashboard" },
  { to: "/projects", label: "Projects", icon: FolderSimple, testid: "nav-projects" },
  { to: "/customers", label: "Customers", icon: UsersThree, testid: "nav-customers" },
  { to: "/suppliers", label: "Suppliers", icon: Truck, testid: "nav-suppliers" },
  { to: "/employees", label: "Employees", icon: UserCircle, testid: "nav-employees" },
  { to: "/uploads", label: "Excel Upload", icon: UploadSimple, testid: "nav-uploads" },
  { to: "/approvals", label: "Approvals", icon: GavelIcon, testid: "nav-approvals" },
  { to: "/audit", label: "Audit Trail", icon: ClockCounterClockwise, testid: "nav-audit" },
];

const ADMIN_NAV = [
  { to: "/admin/users", label: "User Management", icon: ShieldCheck, testid: "nav-admin-users" },
  { to: "/admin/approval-matrix", label: "Approval Matrix", icon: Database, testid: "nav-admin-rules" },
];

export default function AppLayout({ children }) {
  const { user, logout } = useAuth();
  const { mode, setMode } = useCurrency();
  const navigate = useNavigate();

  return (
    <div className="flex min-h-screen bg-[#FAFAF8]">
      {/* Sidebar */}
      <aside className="w-64 bg-[#111110] text-white flex flex-col" data-testid="app-sidebar">
        <div className="px-6 py-6 border-b border-white/10">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 bg-[#A67C00] flex items-center justify-center">
              <Wallet weight="bold" size={18} className="text-black" />
            </div>
            <div>
              <div className="font-display text-lg font-bold tracking-tight">CRacker Pro</div>
              <div className="text-[10px] tracking-overline text-white/50">Business Finance</div>
            </div>
          </div>
        </div>

        <nav className="flex-1 py-3 overflow-y-auto">
          <div className="px-4 py-2 text-[10px] tracking-overline text-white/40">Workspace</div>
          {NAV.map((n) => (
            <NavLink key={n.to} to={n.to} className={({ isActive }) => `nav-link ${isActive ? "active" : ""}`} data-testid={n.testid}>
              <n.icon size={18} weight="duotone" />
              <span>{n.label}</span>
            </NavLink>
          ))}
          {user?.role === "admin" && (
            <>
              <div className="px-4 py-2 mt-4 text-[10px] tracking-overline text-white/40">Administration</div>
              {ADMIN_NAV.map((n) => (
                <NavLink key={n.to} to={n.to} className={({ isActive }) => `nav-link ${isActive ? "active" : ""}`} data-testid={n.testid}>
                  <n.icon size={18} weight="duotone" />
                  <span>{n.label}</span>
                </NavLink>
              ))}
            </>
          )}
        </nav>

        <div className="px-4 py-4 border-t border-white/10">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-sm font-semibold" data-testid="sidebar-user-name">{user?.name}</div>
              <div className="text-[11px] text-white/50 capitalize">{user?.role}</div>
            </div>
            <button className="btn-ghost text-white/70 hover:text-[#D4AF37]" onClick={async () => { await logout(); navigate("/login"); }} data-testid="logout-btn">
              <SignOut size={18} weight="bold" />
            </button>
          </div>
        </div>
      </aside>

      {/* Main */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Top bar */}
        <div className="h-16 px-8 border-b border-[#E5E5E0] bg-white flex items-center justify-between" data-testid="app-topbar">
          <div className="text-xs text-[#5E5E5A] tracking-overline">Project Commercial Lifecycle</div>
          <div className="flex items-center gap-4">
            {/* Currency toggle */}
            <div className="flex items-center bg-[#FAFAF8] border border-[#E5E5E0] p-0.5" data-testid="currency-toggle">
              <button
                className={`px-3 py-1 text-xs font-semibold ${mode === "INR" ? "bg-white border border-[#A67C00] text-[#A67C00]" : "text-[#5E5E5A]"}`}
                onClick={() => setMode("INR")}
                data-testid="currency-inr-btn"
              >
                ₹ Crore
              </button>
              <button
                className={`px-3 py-1 text-xs font-semibold ${mode === "USD" ? "bg-white border border-[#A67C00] text-[#A67C00]" : "text-[#5E5E5A]"}`}
                onClick={() => setMode("USD")}
                data-testid="currency-usd-btn"
              >
                $ Million
              </button>
            </div>
          </div>
        </div>
        <main className="flex-1 overflow-auto">{children}</main>
      </div>
    </div>
  );
}
