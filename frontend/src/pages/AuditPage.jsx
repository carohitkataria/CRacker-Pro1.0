import React, { useEffect, useState } from "react";
import api from "@/lib/api";
import PageHeader from "@/components/PageHeader";
import { StatusBadge } from "@/components/StatusBadge";
import { formatDateTime } from "@/lib/format";

const ENTITY_TYPES = ["", "project", "customer", "employee", "supplier", "user", "approval_rule", "approval_request", "upload", "revenue_line", "cost_line"];

export default function AuditPage() {
  const [type, setType] = useState("");
  const [rows, setRows] = useState([]);

  const load = async () => {
    const { data } = await api.get("/audit", { params: { entity_type: type || undefined, limit: 200 } });
    setRows(data);
  };
  useEffect(() => { load(); /* eslint-disable-line */ }, [type]);

  return (
    <div data-testid="audit-page">
      <PageHeader title="Audit Trail" subtitle="Permanent record of every change" breadcrumb="HOME · AUDIT" />
      <div className="px-8 py-5">
        <div className="tile p-3 mb-4 flex flex-wrap gap-2">
          <span className="text-[10px] tracking-overline text-[#5E5E5A] self-center mr-2">FILTER ENTITY</span>
          {ENTITY_TYPES.map((t) => (
            <button key={t} onClick={() => setType(t)}
              className={`px-3 py-1.5 text-xs border ${type === t ? "bg-[#111110] text-white border-[#111110]" : "border-[#E5E5E0] text-[#5E5E5A] hover:border-[#A67C00]"}`}
              data-testid={`audit-filter-${t || "all"}`}>{t || "All"}</button>
          ))}
        </div>
        <div className="tile overflow-x-auto">
          <table className="tbl">
            <thead><tr><th>Timestamp</th><th>Entity</th><th>Action</th><th>User</th><th>Reason</th><th>Changes</th></tr></thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.id} data-testid={`audit-row-${r.id}`}>
                  <td className="text-xs">{formatDateTime(r.timestamp)}</td>
                  <td className="text-xs"><span className="font-mono">{r.entity_type}</span><div className="text-[10px] text-[#5E5E5A]">{(r.entity_id || "").slice(0, 8)}</div></td>
                  <td><StatusBadge status={r.action} /></td>
                  <td className="text-xs">{r.user_email || "system"}</td>
                  <td className="text-xs">{r.reason || "—"}</td>
                  <td><pre className="font-mono text-[10px] whitespace-pre-wrap max-w-md">{JSON.stringify(r.field_changes, null, 2)}</pre></td>
                </tr>
              ))}
              {rows.length === 0 && <tr><td colSpan={6} className="text-center py-12 text-[#5E5E5A]">No audit events</td></tr>}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
