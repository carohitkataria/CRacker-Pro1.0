import React, { useEffect, useState } from "react";
import api from "@/lib/api";
import PageHeader from "@/components/PageHeader";
import { useCurrency } from "@/lib/currency";
import { formatCurrency, formatDate } from "@/lib/format";
import { useNavigate } from "react-router-dom";
import { StatusBadge } from "@/components/StatusBadge";
import { MagnifyingGlass, ArrowsClockwise } from "@phosphor-icons/react";

const CR_KEYWORDS = /change\s*request|cr\b|change\s*order|co\b|amendment/i;

function isChangeRequest(p) {
  return (
    CR_KEYWORDS.test(p.category1 || "") ||
    CR_KEYWORDS.test(p.category2 || "") ||
    CR_KEYWORDS.test(p.project_name || "") ||
    CR_KEYWORDS.test(p.description || "")
  );
}

export default function ChangeRequestsPage() {
  const { mode, inrPerUsd } = useCurrency();
  const navigate = useNavigate();
  const [rows, setRows] = useState([]);
  const [search, setSearch] = useState("");

  const load = async () => {
    const { data } = await api.get("/projects");
    setRows(data.filter(isChangeRequest));
  };

  useEffect(() => { load(); }, []);

  const filtered = rows.filter((r) => {
    if (!search) return true;
    const s = search.toLowerCase();
    return (
      (r.project_name || "").toLowerCase().includes(s) ||
      (r.wbs_element || "").toLowerCase().includes(s) ||
      (r.customer_name || "").toLowerCase().includes(s)
    );
  });

  return (
    <div data-testid="change-requests-page">
      <PageHeader
        title="Change Requests"
        subtitle="Amendments / change orders tagged from existing projects"
        breadcrumb="HOME · CHANGE REQUESTS"
      />
      <div className="px-8 py-6 space-y-5">
        <div className="tile p-4 flex items-center gap-3">
          <div className="relative flex-1">
            <MagnifyingGlass size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--muted)]" />
            <input
              className="input pl-9"
              placeholder="Search change requests…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              data-testid="change-requests-search"
            />
          </div>
          <div className="text-[11px] text-[var(--muted)] flex items-center gap-2">
            <ArrowsClockwise size={14} /> {filtered.length} record{filtered.length === 1 ? "" : "s"}
          </div>
        </div>

        <div className="tile overflow-hidden">
          <table className="tbl" data-testid="change-requests-table">
            <thead>
              <tr>
                <th>Request</th><th>WBS</th><th>Customer</th><th>Stage</th><th className="num">PO</th><th>End Date</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((p) => (
                <tr key={p.id} className="cursor-pointer" onClick={() => navigate(`/projects/${p.id}`)} data-testid={`cr-row-${p.id}`}>
                  <td>
                    <div className="font-medium text-[var(--text)]">{p.project_name}</div>
                    <div className="text-[11px] text-[var(--muted)]">{p.category1 || p.category2 || ""}</div>
                  </td>
                  <td className="font-mono text-xs">{p.wbs_element || "—"}</td>
                  <td>{p.customer_name || "—"}</td>
                  <td><StatusBadge status={p.current_stage} /></td>
                  <td className="num">{formatCurrency(p.po_value, mode, inrPerUsd)}</td>
                  <td>{formatDate(p.end_date)}</td>
                </tr>
              ))}
              {filtered.length === 0 && (
                <tr><td colSpan={6} className="text-center py-12 text-[var(--muted)]">
                  No change requests found. Tag projects with <span className="font-mono text-[var(--gold)]">Change Request</span> in Category 1 to see them here.
                </td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
