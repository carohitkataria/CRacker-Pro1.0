import React, { useEffect, useState } from "react";
import api from "@/lib/api";
import PageHeader from "@/components/PageHeader";
import { useCurrency } from "@/lib/currency";
import { formatCurrency, formatNumber } from "@/lib/format";
import { useNavigate } from "react-router-dom";
import { ArrowUpRight, TrendUp, Warning, Receipt, Buildings, Truck } from "@phosphor-icons/react";
import {
  BarChart, Bar, XAxis, YAxis, ResponsiveContainer, Tooltip,
  LineChart, Line, CartesianGrid, Legend, PieChart, Pie, Cell,
} from "recharts";

function KpiTile({ label, value, sub, icon: Icon, onClick, accent, testid }) {
  return (
    <div
      className={`tile ${onClick ? "tile-clickable" : ""} p-5 flex flex-col justify-between min-h-[112px]`}
      onClick={onClick}
      data-testid={testid}
    >
      <div className="flex items-start justify-between">
        <div className="text-[10px] tracking-overline text-[#5E5E5A]">{label}</div>
        {Icon && <Icon size={16} weight="duotone" className="text-[#A67C00]" />}
      </div>
      <div>
        <div className={`font-mono font-semibold tracking-tight ${accent ? "text-[#A67C00]" : "text-[#111110]"} text-3xl mt-2`}>
          {value}
        </div>
        {sub && <div className="text-[11px] text-[#5E5E5A] mt-1">{sub}</div>}
      </div>
      {onClick && (
        <div className="text-[#A67C00] flex items-center gap-1 text-[11px] tracking-overline mt-2 opacity-0 group-hover:opacity-100">
          DRILL DOWN <ArrowUpRight size={12} />
        </div>
      )}
    </div>
  );
}

export default function DashboardPage() {
  const { mode } = useCurrency();
  const navigate = useNavigate();
  const [data, setData] = useState(null);

  useEffect(() => {
    api.get("/dashboard/summary").then((r) => setData(r.data)).catch(() => {});
  }, []);

  if (!data) {
    return (
      <div>
        <PageHeader title="Dashboard" subtitle="Loading insights..." testid="dashboard-header" />
        <div className="px-8 py-6 grid grid-cols-4 gap-4">
          {[...Array(8)].map((_, i) => <div key={i} className="h-28 skeleton" />)}
        </div>
      </div>
    );
  }

  const { totals, stage_summary, recognized_unbilled, top_customers, vendor_exposure, monthly_billing,
    delayed_projects, low_margin_projects, approvals_pending } = data;

  const stageChart = stage_summary.map((s) => ({ name: s.stage, count: s.count, value: s.po_value / 1e7 }));
  const monthChart = monthly_billing.map((m) => ({
    month: m.month, billed: m.billed / 1e7, recognized: m.recognized / 1e7,
  }));
  const PIE_COLORS = ["#A67C00", "#D4AF37", "#2E6B4A", "#B45309", "#5E5E5A"];

  return (
    <div data-testid="dashboard-page">
      <PageHeader
        title="Finance Dashboard"
        subtitle="Live overview of the project commercial lifecycle"
        breadcrumb="HOME · DASHBOARD"
        testid="dashboard-header"
      />

      <div className="px-8 py-6 space-y-6">
        {/* KPI ROW */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <KpiTile
            label="Total Projects"
            value={formatNumber(totals.total_projects)}
            sub={`Across ${stage_summary.length} stages`}
            icon={Buildings}
            onClick={() => navigate("/projects")}
            testid="kpi-total-projects"
          />
          <KpiTile
            label="Total PO Value"
            value={formatCurrency(totals.total_po_value, mode)}
            sub={`Revenue ${formatCurrency(totals.total_revenue, mode)}`}
            icon={TrendUp}
            onClick={() => navigate("/projects")}
            testid="kpi-total-po"
          />
          <KpiTile
            label="Total Margin"
            value={formatCurrency(totals.total_margin, mode)}
            sub={`${totals.margin_pct.toFixed(1)}% blended margin`}
            icon={Receipt}
            accent
            testid="kpi-total-margin"
          />
          <KpiTile
            label="Approvals Pending"
            value={formatNumber(approvals_pending)}
            sub="Click to action"
            icon={Warning}
            onClick={() => navigate("/approvals")}
            testid="kpi-approvals"
          />
        </div>

        {/* Secondary KPIs */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <KpiTile
            label="Recognized Revenue"
            value={formatCurrency(recognized_unbilled.recognized, mode)}
            sub={`Billed ${formatCurrency(recognized_unbilled.billed, mode)}`}
            testid="kpi-recognized"
          />
          <KpiTile
            label="Recognized but Unbilled"
            value={formatCurrency(recognized_unbilled.unbilled, mode)}
            sub="Working capital exposure"
            accent
            testid="kpi-unbilled"
          />
          <KpiTile
            label="Delayed Projects"
            value={formatNumber(delayed_projects.length)}
            sub={`${low_margin_projects.length} low-margin alerts`}
            icon={Warning}
            onClick={() => navigate("/projects")}
            testid="kpi-delayed"
          />
        </div>

        {/* CHART ROW */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          <div className="tile p-5 lg:col-span-2" data-testid="chart-monthly-billing">
            <div className="flex items-center justify-between mb-4">
              <div>
                <div className="text-[10px] tracking-overline text-[#5E5E5A]">Monthly Billing Trend</div>
                <div className="font-display text-lg font-bold">Recognized vs Billed (Cr)</div>
              </div>
            </div>
            <ResponsiveContainer width="100%" height={240}>
              <LineChart data={monthChart}>
                <CartesianGrid strokeDasharray="2 4" stroke="#E5E5E0" />
                <XAxis dataKey="month" stroke="#5E5E5A" fontSize={11} />
                <YAxis stroke="#5E5E5A" fontSize={11} />
                <Tooltip contentStyle={{ borderRadius: 2, borderColor: "#E5E5E0", fontSize: 12 }} />
                <Legend iconType="square" wrapperStyle={{ fontSize: 12 }} />
                <Line type="monotone" dataKey="recognized" name="Recognized (Cr)" stroke="#A67C00" strokeWidth={2} dot={{ r: 3 }} />
                <Line type="monotone" dataKey="billed" name="Billed (Cr)" stroke="#111110" strokeWidth={2} dot={{ r: 3 }} />
              </LineChart>
            </ResponsiveContainer>
          </div>

          <div className="tile p-5" data-testid="chart-stage-funnel">
            <div className="text-[10px] tracking-overline text-[#5E5E5A] mb-1">Pipeline Funnel</div>
            <div className="font-display text-lg font-bold mb-4">Stage Distribution</div>
            <ResponsiveContainer width="100%" height={240}>
              <BarChart data={stageChart} layout="vertical" margin={{ left: 8, right: 16 }}>
                <CartesianGrid strokeDasharray="2 4" stroke="#E5E5E0" />
                <XAxis type="number" stroke="#5E5E5A" fontSize={11} />
                <YAxis type="category" dataKey="name" stroke="#5E5E5A" fontSize={11} width={90} />
                <Tooltip contentStyle={{ borderRadius: 2, borderColor: "#E5E5E0", fontSize: 12 }} />
                <Bar dataKey="count" fill="#A67C00" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Lists */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <div className="tile p-5" data-testid="top-customers-tile">
            <div className="flex items-center justify-between mb-4">
              <div>
                <div className="text-[10px] tracking-overline text-[#5E5E5A]">Top Customers</div>
                <div className="font-display text-lg font-bold">By PO Value</div>
              </div>
              <Buildings size={18} weight="duotone" className="text-[#A67C00]" />
            </div>
            <table className="tbl">
              <thead>
                <tr><th>Customer</th><th className="num">PO Value</th><th className="num">Projects</th></tr>
              </thead>
              <tbody>
                {top_customers.map((c) => (
                  <tr key={c.customer_id}>
                    <td>{c.customer_name}</td>
                    <td className="num">{formatCurrency(c.po_value, mode)}</td>
                    <td className="num">{c.count}</td>
                  </tr>
                ))}
                {top_customers.length === 0 && (
                  <tr><td colSpan={3} className="text-[#5E5E5A] text-center py-4">No data</td></tr>
                )}
              </tbody>
            </table>
          </div>

          <div className="tile p-5" data-testid="vendor-exposure-tile">
            <div className="flex items-center justify-between mb-4">
              <div>
                <div className="text-[10px] tracking-overline text-[#5E5E5A]">Vendor Exposure</div>
                <div className="font-display text-lg font-bold">By Cost Spend</div>
              </div>
              <Truck size={18} weight="duotone" className="text-[#A67C00]" />
            </div>
            <div className="grid grid-cols-2 gap-4 items-center">
              <ResponsiveContainer width="100%" height={180}>
                <PieChart>
                  <Pie data={vendor_exposure} dataKey="amount" nameKey="supplier_name" innerRadius={40} outerRadius={70}>
                    {vendor_exposure.map((_, i) => <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />)}
                  </Pie>
                  <Tooltip contentStyle={{ borderRadius: 2, borderColor: "#E5E5E0", fontSize: 12 }} />
                </PieChart>
              </ResponsiveContainer>
              <div className="space-y-2">
                {vendor_exposure.map((v, i) => (
                  <div key={v.supplier_name} className="flex items-center justify-between text-xs">
                    <div className="flex items-center gap-2">
                      <span className="w-2 h-2" style={{ background: PIE_COLORS[i % PIE_COLORS.length] }} />
                      <span className="truncate max-w-[120px]">{v.supplier_name}</span>
                    </div>
                    <span className="font-mono">{formatCurrency(v.amount, mode)}</span>
                  </div>
                ))}
                {vendor_exposure.length === 0 && <div className="text-xs text-[#5E5E5A]">No cost data yet</div>}
              </div>
            </div>
          </div>
        </div>

        {/* Delayed + Low margin */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <div className="tile p-5" data-testid="delayed-projects-tile">
            <div className="flex items-center justify-between mb-4">
              <div>
                <div className="text-[10px] tracking-overline text-[#5E5E5A]">Delayed Projects</div>
                <div className="font-display text-lg font-bold">Past End Date · Not Closed</div>
              </div>
            </div>
            <table className="tbl">
              <thead><tr><th>Project</th><th>Customer</th><th>End Date</th><th className="num">PO</th></tr></thead>
              <tbody>
                {delayed_projects.slice(0, 6).map((p) => (
                  <tr key={p.id} className="cursor-pointer" onClick={() => navigate(`/projects/${p.id}`)}>
                    <td className="text-[#111110]">{p.project_name}</td>
                    <td>{p.customer_name || "—"}</td>
                    <td className="text-[#991B1B]">{p.end_date}</td>
                    <td className="num">{formatCurrency(p.po_value, mode)}</td>
                  </tr>
                ))}
                {delayed_projects.length === 0 && (
                  <tr><td colSpan={4} className="text-[#5E5E5A] text-center py-6">No delayed projects 🎯</td></tr>
                )}
              </tbody>
            </table>
          </div>

          <div className="tile p-5" data-testid="low-margin-tile">
            <div className="flex items-center justify-between mb-4">
              <div>
                <div className="text-[10px] tracking-overline text-[#5E5E5A]">Low Margin Projects</div>
                <div className="font-display text-lg font-bold">Margin &lt; 15%</div>
              </div>
            </div>
            <table className="tbl">
              <thead><tr><th>Project</th><th>Stage</th><th className="num">Margin %</th><th className="num">PO</th></tr></thead>
              <tbody>
                {low_margin_projects.slice(0, 6).map((p) => (
                  <tr key={p.id} className="cursor-pointer" onClick={() => navigate(`/projects/${p.id}`)}>
                    <td>{p.project_name}</td>
                    <td>{p.current_stage}</td>
                    <td className="num text-[#991B1B]">{(p.margin_pct || 0).toFixed(1)}%</td>
                    <td className="num">{formatCurrency(p.po_value, mode)}</td>
                  </tr>
                ))}
                {low_margin_projects.length === 0 && (
                  <tr><td colSpan={4} className="text-[#5E5E5A] text-center py-6">All projects healthy ✓</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
