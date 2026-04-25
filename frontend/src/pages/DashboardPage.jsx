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

// eslint-disable-next-line no-unused-vars
function KpiTile({ label, value, sub, icon: Icon, onClick, accent, testid }) {
  return (
    <div
      className={`tile ${onClick ? "tile-clickable" : ""} p-5 flex flex-col justify-between min-h-[112px]`}
      onClick={onClick}
      data-testid={testid}
    >
      <div className="flex items-start justify-between">
        <div className="text-[10px] tracking-overline text-[var(--muted)]">{label}</div>
        {Icon && <Icon size={16} weight="duotone" className="text-[var(--gold)]" />}
      </div>
      <div>
        <div className={`font-mono font-semibold tracking-tight ${accent ? "text-[var(--gold)]" : "text-[var(--text)]"} text-3xl mt-2`}>
          {value}
        </div>
        {sub && <div className="text-[11px] text-[var(--muted)] mt-1">{sub}</div>}
      </div>
      {onClick && (
        <div className="text-[var(--gold)] flex items-center gap-1 text-[11px] tracking-overline mt-2 opacity-0 group-hover:opacity-100">
          DRILL DOWN <ArrowUpRight size={12} />
        </div>
      )}
    </div>
  );
}

export default function DashboardPage() {
  const { mode, inrPerUsd } = useCurrency();
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
  // Vibrant minimal palette (inspired by reference) — works across themes
  const CHART_PALETTE = [
    "#E07A3C", // orange
    "#FFC000", // gold
    "#7BB661", // green
    "#7B3F00", // brown
    "#5C2B84", // royal purple
    "#8B9A2B", // olive
    "#D9A45B", // tan
    "#3CA67A", // teal-green
    "#C46A3C", // terracotta
    "#3D8B7A", // dark teal
  ];
  const PIE_COLORS = CHART_PALETTE;
  const STAGE_COLORS = ["#E07A3C", "#FFC000", "#7BB661", "#5C2B84", "#7B3F00"];
  const totalVendor = (vendor_exposure || []).reduce((s, v) => s + (v.amount || 0), 0) || 1;

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
            value={formatCurrency(totals.total_po_value, mode, inrPerUsd)}
            sub={`Revenue ${formatCurrency(totals.total_revenue, mode, inrPerUsd)}`}
            icon={TrendUp}
            onClick={() => navigate("/projects")}
            testid="kpi-total-po"
          />
          <KpiTile
            label="Total Margin"
            value={formatCurrency(totals.total_margin, mode, inrPerUsd)}
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
            value={formatCurrency(recognized_unbilled.recognized, mode, inrPerUsd)}
            sub={`Billed ${formatCurrency(recognized_unbilled.billed, mode, inrPerUsd)}`}
            testid="kpi-recognized"
          />
          <KpiTile
            label="Recognized but Unbilled"
            value={formatCurrency(recognized_unbilled.unbilled, mode, inrPerUsd)}
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
                <div className="text-[10px] tracking-overline text-[var(--muted)]">Monthly Billing Trend</div>
                <div className="font-display text-lg font-bold">Recognized vs Billed (Cr)</div>
              </div>
            </div>
            <ResponsiveContainer width="100%" height={240}>
              <LineChart data={monthChart} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="2 4" stroke="var(--border-soft)" vertical={false} />
                <XAxis dataKey="month" stroke="var(--muted)" fontSize={11} tickLine={false} axisLine={false} />
                <YAxis stroke="var(--muted)" fontSize={11} tickLine={false} axisLine={false} />
                <Tooltip contentStyle={{ borderRadius: 4, border: "1px solid var(--border)", background: "var(--surface)", fontSize: 12 }} />
                <Legend iconType="circle" wrapperStyle={{ fontSize: 12, paddingTop: 8 }} />
                <Line type="monotone" dataKey="recognized" name="Recognized (Cr)" stroke="#5C2B84" strokeWidth={2.5} dot={{ r: 3, fill: "#5C2B84" }} activeDot={{ r: 5 }} />
                <Line type="monotone" dataKey="billed" name="Billed (Cr)" stroke="#FFC000" strokeWidth={2.5} dot={{ r: 3, fill: "#FFC000" }} activeDot={{ r: 5 }} />
              </LineChart>
            </ResponsiveContainer>
          </div>

          <div className="tile p-5" data-testid="chart-stage-funnel">
            <div className="text-[10px] tracking-overline text-[var(--muted)] mb-1">Pipeline Funnel</div>
            <div className="font-display text-lg font-bold mb-4">Stage Distribution</div>
            <ResponsiveContainer width="100%" height={240}>
              <BarChart data={stageChart} layout="vertical" margin={{ top: 4, left: 8, right: 24, bottom: 0 }}>
                <CartesianGrid strokeDasharray="2 4" stroke="var(--border-soft)" horizontal={false} />
                <XAxis type="number" stroke="var(--muted)" fontSize={11} tickLine={false} axisLine={false} />
                <YAxis type="category" dataKey="name" stroke="var(--muted)" fontSize={11} width={90} tickLine={false} axisLine={false} />
                <Tooltip contentStyle={{ borderRadius: 4, border: "1px solid var(--border)", background: "var(--surface)", fontSize: 12 }} cursor={{ fill: "var(--surface-2)" }} />
                <Bar dataKey="count" radius={[0, 4, 4, 0]} label={{ position: "right", fill: "var(--text)", fontSize: 11, fontWeight: 600 }}>
                  {stageChart.map((_, i) => <Cell key={i} fill={STAGE_COLORS[i % STAGE_COLORS.length]} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Lists */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <div className="tile p-5" data-testid="top-customers-tile">
            <div className="flex items-center justify-between mb-4">
              <div>
                <div className="text-[10px] tracking-overline text-[var(--muted)]">Top Customers</div>
                <div className="font-display text-lg font-bold">By PO Value</div>
              </div>
              <Buildings size={18} weight="duotone" className="text-[var(--gold)]" />
            </div>
            <table className="tbl">
              <thead>
                <tr><th>Customer</th><th className="num">PO Value</th><th className="num">Projects</th></tr>
              </thead>
              <tbody>
                {top_customers.map((c) => (
                  <tr key={c.customer_id}>
                    <td>{c.customer_name}</td>
                    <td className="num">{formatCurrency(c.po_value, mode, inrPerUsd)}</td>
                    <td className="num">{c.count}</td>
                  </tr>
                ))}
                {top_customers.length === 0 && (
                  <tr><td colSpan={3} className="text-[var(--muted)] text-center py-4">No data</td></tr>
                )}
              </tbody>
            </table>
          </div>

          <div className="tile p-5" data-testid="vendor-exposure-tile">
            <div className="flex items-center justify-between mb-4">
              <div>
                <div className="text-[10px] tracking-overline text-[var(--muted)]">Vendor Exposure</div>
                <div className="font-display text-lg font-bold">By Cost Spend</div>
              </div>
              <Truck size={18} weight="duotone" className="text-[var(--gold)]" />
            </div>
            <div className="grid grid-cols-2 gap-4 items-center">
              <ResponsiveContainer width="100%" height={200}>
                <PieChart>
                  <Pie
                    data={vendor_exposure}
                    dataKey="amount"
                    nameKey="supplier_name"
                    innerRadius={42}
                    outerRadius={80}
                    paddingAngle={2}
                    stroke="var(--surface)"
                    strokeWidth={2}
                    label={({ percent }) => percent > 0.04 ? `${Math.round(percent * 100)}%` : ""}
                    labelLine={false}
                    fontSize={11}
                  >
                    {vendor_exposure.map((_, i) => <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />)}
                  </Pie>
                  <Tooltip
                    formatter={(v, n) => [formatCurrency(v, mode, inrPerUsd), n]}
                    contentStyle={{ borderRadius: 4, border: "1px solid var(--border)", background: "var(--surface)", fontSize: 12 }}
                  />
                </PieChart>
              </ResponsiveContainer>
              <div className="space-y-1.5">
                {vendor_exposure.map((v, i) => {
                  const pct = ((v.amount || 0) / totalVendor) * 100;
                  return (
                    <div key={v.supplier_name} className="flex items-center justify-between text-xs gap-2">
                      <div className="flex items-center gap-2 min-w-0">
                        <span className="w-2.5 h-2.5 rounded-sm shrink-0" style={{ background: PIE_COLORS[i % PIE_COLORS.length] }} />
                        <span className="truncate">{v.supplier_name}</span>
                      </div>
                      <span className="font-mono text-[var(--muted)]">{pct.toFixed(0)}%</span>
                    </div>
                  );
                })}
                {vendor_exposure.length === 0 && <div className="text-xs text-[var(--muted)]">No cost data yet</div>}
              </div>
            </div>
          </div>
        </div>

        {/* Delayed + Low margin */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <div className="tile p-5" data-testid="delayed-projects-tile">
            <div className="flex items-center justify-between mb-4">
              <div>
                <div className="text-[10px] tracking-overline text-[var(--muted)]">Delayed Projects</div>
                <div className="font-display text-lg font-bold">Past End Date · Not Closed</div>
              </div>
            </div>
            <table className="tbl">
              <thead><tr><th>Project</th><th>Customer</th><th>End Date</th><th className="num">PO</th></tr></thead>
              <tbody>
                {delayed_projects.slice(0, 6).map((p) => (
                  <tr key={p.id} className="cursor-pointer" onClick={() => navigate(`/projects/${p.id}`)}>
                    <td className="text-[var(--text)]">{p.project_name}</td>
                    <td>{p.customer_name || "—"}</td>
                    <td className="text-[var(--danger)]">{p.end_date}</td>
                    <td className="num">{formatCurrency(p.po_value, mode, inrPerUsd)}</td>
                  </tr>
                ))}
                {delayed_projects.length === 0 && (
                  <tr><td colSpan={4} className="text-[var(--muted)] text-center py-6">No delayed projects 🎯</td></tr>
                )}
              </tbody>
            </table>
          </div>

          <div className="tile p-5" data-testid="low-margin-tile">
            <div className="flex items-center justify-between mb-4">
              <div>
                <div className="text-[10px] tracking-overline text-[var(--muted)]">Low Margin Projects</div>
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
                    <td className="num text-[var(--danger)]">{(p.margin_pct || 0).toFixed(1)}%</td>
                    <td className="num">{formatCurrency(p.po_value, mode, inrPerUsd)}</td>
                  </tr>
                ))}
                {low_margin_projects.length === 0 && (
                  <tr><td colSpan={4} className="text-[var(--muted)] text-center py-6">All projects healthy ✓</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
