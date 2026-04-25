import React, { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import api, { formatApiErrorDetail } from "@/lib/api";
import PageHeader from "@/components/PageHeader";
import StageTracker, { STAGES } from "@/components/StageTracker";
import { StatusBadge } from "@/components/StatusBadge";
import { useCurrency } from "@/lib/currency";
import { formatCurrency, formatDate, formatDateTime } from "@/lib/format";
import { ArrowLeft, ArrowRight, Plus, Trash, PencilSimple } from "@phosphor-icons/react";
import ProjectFormModal from "@/components/ProjectFormModal";

const TABS = ["Overview", "Revenue", "Cost", "Milestones", "Audit"];

export default function ProjectDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { mode } = useCurrency();

  const [project, setProject] = useState(null);
  const [tab, setTab] = useState("Overview");
  const [revenue, setRevenue] = useState([]);
  const [cost, setCost] = useState([]);
  const [audit, setAudit] = useState([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [showEdit, setShowEdit] = useState(false);
  const [customers, setCustomers] = useState([]);

  const load = async () => {
    const { data } = await api.get(`/projects/${id}`);
    setProject(data);
    const [r, c, a] = await Promise.all([
      api.get(`/projects/${id}/revenue`),
      api.get(`/projects/${id}/cost`),
      api.get(`/audit?entity_id=${id}&entity_type=project`),
    ]);
    setRevenue(r.data); setCost(c.data); setAudit(a.data);
  };

  useEffect(() => {
    load();
    api.get("/customers").then((r) => setCustomers(r.data)).catch(() => {});
  }, [id]); // eslint-disable-line

  if (!project) return <div className="p-8">Loading…</div>;

  const advance = async (target) => {
    setError(""); setBusy(true);
    try {
      const reason = window.prompt(`Reason for moving to "${target}"? (optional)`) || "";
      const { data } = await api.post(`/projects/${project.id}/transition`, { target_stage: target, reason });
      setProject(data);
      load();
    } catch (e) {
      setError(formatApiErrorDetail(e.response?.data?.detail) || e.message);
    } finally { setBusy(false); }
  };

  const idx = STAGES.indexOf(project.current_stage);
  const nextStage = idx >= 0 && idx < STAGES.length - 1 ? STAGES[idx + 1] : null;
  const prevStage = idx > 0 ? STAGES[idx - 1] : null;

  return (
    <div data-testid="project-detail-page">
      <PageHeader
        title={project.project_name}
        subtitle={`${project.wbs_element || ""}  ·  ${project.customer_name || ""}`}
        breadcrumb={<><button onClick={() => navigate("/projects")} className="hover:text-[#A67C00] inline-flex items-center gap-1"><ArrowLeft size={11} /> ALL PROJECTS</button> · {project.current_stage.toUpperCase()}</>}
        actions={
          <div className="flex items-center gap-2">
            {prevStage && (
              <button className="btn-secondary text-xs" onClick={() => advance(prevStage)} disabled={busy} data-testid="rewind-stage-btn">
                ← Send back to {prevStage}
              </button>
            )}
            {nextStage && (
              <button className="btn-primary text-xs flex items-center gap-1" onClick={() => advance(nextStage)} disabled={busy} data-testid="advance-stage-btn">
                Advance to {nextStage} <ArrowRight size={12} weight="bold" />
              </button>
            )}
            <button className="btn-secondary text-xs flex items-center gap-1" onClick={() => setShowEdit(true)} data-testid="edit-project-btn">
              <PencilSimple size={12} /> Edit
            </button>
          </div>
        }
      />

      {/* Stage tracker */}
      <div className="px-8 py-4 border-b border-[#E5E5E0] bg-white">
        <StageTracker current={project.current_stage} />
        {error && <div className="text-xs text-[#991B1B] bg-[#fdeaea] p-2 mt-3 border border-[#f1c2c2]">{error}</div>}
      </div>

      {/* Quick stats */}
      <div className="px-8 py-5 grid grid-cols-2 md:grid-cols-5 gap-3">
        <Stat label="PO Value" value={formatCurrency(project.po_value, mode)} />
        <Stat label="Revenue Plan" value={formatCurrency(project.revenue_total, mode)} />
        <Stat label="Cost Plan" value={formatCurrency(project.cost_total, mode)} />
        <Stat label="Margin" value={formatCurrency(project.margin_total, mode)} accent />
        <Stat label="Margin %" value={`${(project.margin_pct || 0).toFixed(1)}%`} accent={project.margin_pct >= 15} danger={project.margin_pct < 15} />
      </div>

      {/* Tabs */}
      <div className="px-8 border-b border-[#E5E5E0] bg-white">
        <div className="flex gap-1">
          {TABS.map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`px-4 py-3 text-sm font-medium border-b-2 ${tab === t ? "border-[#A67C00] text-[#A67C00]" : "border-transparent text-[#5E5E5A] hover:text-[#111110]"}`}
              data-testid={`tab-${t.toLowerCase()}`}
            >
              {t}
            </button>
          ))}
        </div>
      </div>

      <div className="px-8 py-6">
        {tab === "Overview" && <Overview project={project} />}
        {tab === "Revenue" && <RevenueTab projectId={id} rows={revenue} reload={load} mode={mode} />}
        {tab === "Cost" && <CostTab projectId={id} rows={cost} reload={load} mode={mode} />}
        {tab === "Milestones" && <Milestones project={project} mode={mode} />}
        {tab === "Audit" && <AuditTab rows={audit} />}
      </div>

      {showEdit && (
        <ProjectFormModal
          project={project}
          customers={customers}
          onClose={() => setShowEdit(false)}
          onSaved={() => { setShowEdit(false); load(); }}
        />
      )}
    </div>
  );
}

function Stat({ label, value, accent, danger }) {
  return (
    <div className="tile p-4">
      <div className="text-[10px] tracking-overline text-[#5E5E5A]">{label}</div>
      <div className={`font-mono font-semibold text-xl mt-1 ${accent ? "text-[#A67C00]" : danger ? "text-[#991B1B]" : "text-[#111110]"}`}>{value}</div>
    </div>
  );
}

function Overview({ project }) {
  const fields = [
    ["Customer", project.customer_name],
    ["Customer PO Number", project.customer_po_number],
    ["PO Date", formatDate(project.po_date)],
    ["Start Date", formatDate(project.start_date)],
    ["End Date", formatDate(project.end_date)],
    ["Billing Type", project.billing_type],
    ["Currency", project.currency],
    ["Country", project.country],
    ["P&L Location", project.pnl_location],
    ["P&L Region", project.pnl_region],
    ["Business Category", project.business_category],
    ["Project Grouping", project.project_grouping],
    ["Location", project.location],
    ["Ownership Email", project.ownership_email],
    ["Approval Status", <StatusBadge key="a" status={project.approval_status} />],
    ["Created By", project.created_by],
    ["Updated At", formatDateTime(project.updated_at)],
  ];
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-x-10 gap-y-4">
      {fields.map(([k, v]) => (
        <div key={k} className="flex justify-between border-b border-[#E5E5E0] pb-2">
          <span className="text-xs text-[#5E5E5A] tracking-overline">{k}</span>
          <span className="text-sm font-medium text-[#111110]">{v || "—"}</span>
        </div>
      ))}
      {(project.description || project.baseline_remarks || project.finance_remarks) && (
        <div className="md:col-span-2 mt-4 grid md:grid-cols-3 gap-4">
          <div className="tile p-4"><div className="text-[10px] tracking-overline text-[#5E5E5A] mb-1">Description</div><div className="text-sm">{project.description || "—"}</div></div>
          <div className="tile p-4"><div className="text-[10px] tracking-overline text-[#5E5E5A] mb-1">Baseline Remarks</div><div className="text-sm">{project.baseline_remarks || "—"}</div></div>
          <div className="tile p-4"><div className="text-[10px] tracking-overline text-[#5E5E5A] mb-1">Finance Remarks</div><div className="text-sm">{project.finance_remarks || "—"}</div></div>
        </div>
      )}
    </div>
  );
}

function RevenueTab({ projectId, rows, reload, mode }) {
  const [show, setShow] = useState(false);
  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-display text-lg font-bold">Revenue Lines</h3>
        <button className="btn-primary text-xs flex items-center gap-1" onClick={() => setShow(true)} data-testid="add-revenue-btn"><Plus size={12} /> Add Revenue</button>
      </div>
      <table className="tbl tile">
        <thead><tr><th>Code</th><th>Description</th><th>Recognition</th><th>Billing</th><th>Status</th><th className="num">Amount</th><th></th></tr></thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.id}>
              <td className="font-mono text-xs">{r.revenue_code || "—"}</td>
              <td>{r.description || "—"}</td>
              <td>{formatDate(r.recognition_date)}</td>
              <td>{formatDate(r.billing_date)}</td>
              <td><StatusBadge status={r.is_billed ? "Approved" : "Pending"} /></td>
              <td className="num">{formatCurrency(r.amount, mode)}</td>
              <td><button className="btn-ghost" onClick={async () => { await api.delete(`/revenue/${r.id}`); reload(); }}><Trash size={14} /></button></td>
            </tr>
          ))}
          {rows.length === 0 && <tr><td colSpan={7} className="text-center py-8 text-[#5E5E5A]">No revenue lines yet</td></tr>}
        </tbody>
      </table>
      {show && <LineModal title="Revenue Line" entity="revenue" projectId={projectId} onClose={() => setShow(false)} onSaved={() => { setShow(false); reload(); }} />}
    </div>
  );
}

function CostTab({ projectId, rows, reload, mode }) {
  const [show, setShow] = useState(false);
  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-display text-lg font-bold">Cost Lines</h3>
        <button className="btn-primary text-xs flex items-center gap-1" onClick={() => setShow(true)} data-testid="add-cost-btn"><Plus size={12} /> Add Cost</button>
      </div>
      <table className="tbl tile">
        <thead><tr><th>Vendor PO</th><th>Supplier</th><th>Description</th><th>Date</th><th>Category</th><th className="num">Amount</th><th></th></tr></thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.id}>
              <td className="font-mono text-xs">{r.vendor_po_ref || "—"}</td>
              <td>{r.supplier_name || "—"}</td>
              <td>{r.description || "—"}</td>
              <td>{formatDate(r.expense_date)}</td>
              <td>{r.category || "—"}</td>
              <td className="num">{formatCurrency(r.amount, mode)}</td>
              <td><button className="btn-ghost" onClick={async () => { await api.delete(`/cost/${r.id}`); reload(); }}><Trash size={14} /></button></td>
            </tr>
          ))}
          {rows.length === 0 && <tr><td colSpan={7} className="text-center py-8 text-[#5E5E5A]">No cost lines yet</td></tr>}
        </tbody>
      </table>
      {show && <LineModal title="Cost Line" entity="cost" projectId={projectId} onClose={() => setShow(false)} onSaved={() => { setShow(false); reload(); }} />}
    </div>
  );
}

function LineModal({ title, entity, projectId, onClose, onSaved }) {
  const [form, setForm] = useState(entity === "revenue"
    ? { revenue_code: "", description: "", amount: 0, recognition_date: "", billing_date: "", is_billed: false }
    : { vendor_po_ref: "", supplier_name: "", description: "", amount: 0, expense_date: "", category: "" });
  const [busy, setBusy] = useState(false);
  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }));
  const submit = async (e) => {
    e.preventDefault(); setBusy(true);
    try {
      const url = entity === "revenue" ? `/projects/${projectId}/revenue` : `/projects/${projectId}/cost`;
      await api.post(url, { ...form, project_id: projectId, amount: Number(form.amount || 0) });
      onSaved();
    } finally { setBusy(false); }
  };
  return (
    <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4">
      <form onSubmit={submit} className="bg-white border border-[#E5E5E0] w-full max-w-lg p-5 space-y-3" data-testid={`${entity}-line-modal`}>
        <h3 className="font-display text-lg font-bold">{title}</h3>
        {entity === "revenue" ? (
          <>
            <input className="input" placeholder="Revenue code" value={form.revenue_code} onChange={(e) => set("revenue_code", e.target.value)} />
            <input className="input" placeholder="Description" value={form.description} onChange={(e) => set("description", e.target.value)} />
            <div className="grid grid-cols-2 gap-3">
              <input type="date" className="input" value={form.recognition_date} onChange={(e) => set("recognition_date", e.target.value)} />
              <input type="date" className="input" value={form.billing_date} onChange={(e) => set("billing_date", e.target.value)} />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <input type="number" className="input" placeholder="Amount" value={form.amount} onChange={(e) => set("amount", e.target.value)} />
              <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={form.is_billed} onChange={(e) => set("is_billed", e.target.checked)} /> Billed</label>
            </div>
          </>
        ) : (
          <>
            <input className="input" placeholder="Vendor PO ref" value={form.vendor_po_ref} onChange={(e) => set("vendor_po_ref", e.target.value)} />
            <input className="input" placeholder="Supplier name" value={form.supplier_name} onChange={(e) => set("supplier_name", e.target.value)} />
            <input className="input" placeholder="Description" value={form.description} onChange={(e) => set("description", e.target.value)} />
            <div className="grid grid-cols-2 gap-3">
              <input type="date" className="input" value={form.expense_date} onChange={(e) => set("expense_date", e.target.value)} />
              <input className="input" placeholder="Category" value={form.category} onChange={(e) => set("category", e.target.value)} />
            </div>
            <input type="number" className="input" placeholder="Amount" value={form.amount} onChange={(e) => set("amount", e.target.value)} />
          </>
        )}
        <div className="flex justify-end gap-2 pt-2">
          <button type="button" className="btn-secondary" onClick={onClose}>Cancel</button>
          <button type="submit" className="btn-primary" disabled={busy} data-testid="line-modal-submit">{busy ? "Saving…" : "Save"}</button>
        </div>
      </form>
    </div>
  );
}

function Milestones({ project, mode }) {
  const ms = project.milestones || [];
  return (
    <div>
      <h3 className="font-display text-lg font-bold mb-4">Milestones</h3>
      {ms.length === 0 ? (
        <div className="tile p-8 text-center text-[#5E5E5A] text-sm">No milestones for this project</div>
      ) : (
        <table className="tbl tile">
          <thead><tr><th>Milestone</th><th>Due Date</th><th className="num">Value</th><th>Status</th></tr></thead>
          <tbody>
            {ms.map((m, i) => (
              <tr key={i}>
                <td>{m.milestone_name}</td>
                <td>{formatDate(m.due_date)}</td>
                <td className="num">{formatCurrency(m.value, mode)}</td>
                <td><StatusBadge status={m.is_billed ? "Approved" : "Pending"} /></td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

function AuditTab({ rows }) {
  return (
    <div>
      <h3 className="font-display text-lg font-bold mb-4">Audit Trail</h3>
      <table className="tbl tile">
        <thead><tr><th>Timestamp</th><th>Action</th><th>User</th><th>Details</th></tr></thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.id}>
              <td className="text-xs">{formatDateTime(r.timestamp)}</td>
              <td><StatusBadge status={r.action} /></td>
              <td className="text-xs">{r.user_email || "—"}</td>
              <td className="text-xs"><pre className="font-mono text-[10px] whitespace-pre-wrap">{JSON.stringify(r.field_changes, null, 2)}</pre></td>
            </tr>
          ))}
          {rows.length === 0 && <tr><td colSpan={4} className="text-center py-8 text-[#5E5E5A]">No audit events</td></tr>}
        </tbody>
      </table>
    </div>
  );
}
