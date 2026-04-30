import React, { useEffect, useState } from "react";
import api from "@/lib/api";
import PageHeader from "@/components/PageHeader";
import { useCurrency } from "@/lib/currency";
import { formatCurrency } from "@/lib/format";
import { useNavigate } from "react-router-dom";
import { Stack, MagnifyingGlass } from "@phosphor-icons/react";

export default function WBSBudgetPage() {
  const { mode, inrPerUsd } = useCurrency();
  const navigate = useNavigate();
  const [rows, setRows] = useState([]);
  const [search, setSearch] = useState("");

  useEffect(() => {
    api.get("/projects").then((r) => setRows(r.data)).catch(() => {});
  }, []);

  const filtered = rows.filter((p) => {
    if (!search) return true;
    const s = search.toLowerCase();
    return (p.wbs_element || "").toLowerCase().includes(s)
        || (p.project_name || "").toLowerCase().includes(s)
        || (p.customer_name || "").toLowerCase().includes(s);
  });

  const totalPO = filtered.reduce((acc, p) => acc + (p.po_value || 0), 0);
  const totalRevenue = filtered.reduce((acc, p) => acc + (p.revenue_total || 0), 0);
  const totalCost = filtered.reduce((acc, p) => acc + (p.cost_total || 0), 0);

  return (
    <div data-testid="wbs-budget-page">
      <PageHeader
        title="WBS and Budget"
        subtitle="WBS-element-level budget vs actuals across projects"
        breadcrumb="HOME · WBS AND BUDGET"
      />
      <div className="px-8 py-6 space-y-5">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <Tile label="WBS Elements" value={filtered.length} icon={<Stack size={16} weight="duotone" className="text-[var(--gold)]" />} />
          <Tile label="Total PO" value={formatCurrency(totalPO, mode, inrPerUsd)} />
          <Tile label="Revenue Plan" value={formatCurrency(totalRevenue, mode, inrPerUsd)} />
          <Tile label="Cost Plan" value={formatCurrency(totalCost, mode, inrPerUsd)} />
        </div>

        <div className="tile p-4 flex items-center gap-3">
          <div className="relative flex-1">
            <MagnifyingGlass size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--muted)]" />
            <input
              className="input pl-9"
              placeholder="Search WBS, project, customer…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              data-testid="wbs-search"
            />
          </div>
        </div>

        <div className="tile overflow-hidden">
          <table className="tbl" data-testid="wbs-table">
            <thead>
              <tr>
                <th>WBS Element</th>
                <th>Project</th>
                <th>Customer</th>
                <th>Stage</th>
                <th className="num">PO Value</th>
                <th className="num">Revenue</th>
                <th className="num">Cost</th>
                <th className="num">Margin</th>
                <th className="num">Margin %</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((p) => (
                <tr key={p.id} className="cursor-pointer" onClick={() => navigate(`/projects/${p.id}`)} data-testid={`wbs-row-${p.id}`}>
                  <td className="font-mono text-xs">{p.wbs_element || "—"}</td>
                  <td className="font-medium">{p.project_name}</td>
                  <td>{p.customer_name || "—"}</td>
                  <td>{p.current_stage}</td>
                  <td className="num">{formatCurrency(p.po_value, mode, inrPerUsd)}</td>
                  <td className="num">{formatCurrency(p.revenue_total, mode, inrPerUsd)}</td>
                  <td className="num">{formatCurrency(p.cost_total, mode, inrPerUsd)}</td>
                  <td className="num">{formatCurrency(p.margin_total, mode, inrPerUsd)}</td>
                  <td className={`num ${(p.margin_pct || 0) < 15 ? "text-[var(--danger)]" : ""}`}>{(p.margin_pct || 0).toFixed(1)}%</td>
                </tr>
              ))}
              {filtered.length === 0 && (
                <tr><td colSpan={9} className="text-center py-12 text-[var(--muted)]">No WBS rows yet — create projects to populate.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

function Tile({ label, value, icon }) {
  return (
    <div className="tile p-4">
      <div className="flex items-start justify-between">
        <div className="text-[10px] tracking-overline text-[var(--muted)]">{label}</div>
        {icon}
      </div>
      <div className="font-mono font-semibold text-2xl mt-1">{value}</div>
    </div>
  );
}
