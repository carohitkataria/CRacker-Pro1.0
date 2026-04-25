import React, { useState } from "react";
import api, { formatApiErrorDetail } from "@/lib/api";
import { X, Plus, Trash, UserPlus } from "@phosphor-icons/react";

const empty = {
  project_name: "", wbs_element: "", customer_po_number: "", po_date: "",
  start_date: "", end_date: "", billing_type: "Monthly",
  customer_id: "", description: "", currency: "INR",
  po_value: 0, revenue_total: 0, cost_total: 0,
  country: "India", pnl_location: "", pnl_region: "",
  business_category: "Non-GMR", location: "", category1: "",
  ownership_email: "", baseline_remarks: "",
  milestones: [],
};

export default function ProjectFormModal({ project, customers: initialCustomers, onClose, onSaved }) {
  const [form, setForm] = useState(project ? { ...empty, ...project, milestones: project.milestones || [] } : empty);
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  const [customers, setCustomers] = useState(initialCustomers || []);
  const [showNewCust, setShowNewCust] = useState(false);

  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }));

  const addMilestone = () => {
    set("milestones", [...(form.milestones || []), { milestone_name: "", due_date: "", value: 0, is_billed: false }]);
  };
  const updateMilestone = (i, patch) => {
    const next = [...form.milestones];
    next[i] = { ...next[i], ...patch };
    set("milestones", next);
  };
  const removeMilestone = (i) => {
    set("milestones", form.milestones.filter((_, idx) => idx !== i));
  };

  const onSubmit = async (e) => {
    e.preventDefault();
    setBusy(true); setErr("");
    try {
      const payload = {
        ...form,
        po_value: Number(form.po_value || 0),
        revenue_total: Number(form.revenue_total || 0),
        cost_total: Number(form.cost_total || 0),
        milestones: (form.milestones || []).map((m) => ({
          ...m, value: Number(m.value || 0), is_billed: !!m.is_billed,
        })),
      };
      if (project?.id) {
        await api.put(`/projects/${project.id}`, payload);
      } else {
        await api.post("/projects", payload);
      }
      onSaved();
    } catch (e) {
      setErr(formatApiErrorDetail(e.response?.data?.detail) || e.message);
    } finally { setBusy(false); }
  };

  const onCustomerCreated = (c) => {
    setCustomers((arr) => [c, ...arr]);
    set("customer_id", c.id);
    set("customer_name", c.customer_name);
    setShowNewCust(false);
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" data-testid="project-modal">
      <div className="bg-[var(--surface)] w-full max-w-3xl max-h-[90vh] overflow-y-auto border border-[var(--border)]">
        <div className="flex items-center justify-between p-5 border-b border-[var(--border)] sticky top-0 bg-[var(--surface)] z-10">
          <div>
            <div className="text-[10px] tracking-overline text-[var(--muted)]">{project ? "EDIT" : "CREATE"} PROJECT</div>
            <h2 className="font-display text-xl font-bold">{project ? "Edit Project" : "New Project"}</h2>
          </div>
          <button className="btn-ghost" onClick={onClose} data-testid="modal-close"><X size={18} /></button>
        </div>

        <form onSubmit={onSubmit} className="p-5 space-y-5">
          <div className="grid grid-cols-2 gap-4">
            <Field label="Project Name *">
              <input className="input" required value={form.project_name} onChange={(e) => set("project_name", e.target.value)} data-testid="form-project-name" />
            </Field>
            <Field label="WBS Element">
              <input className="input font-mono" value={form.wbs_element || ""} onChange={(e) => set("wbs_element", e.target.value)} data-testid="form-wbs" />
            </Field>

            <Field label="Customer">
              <div className="flex gap-2">
                <select className="input flex-1" value={form.customer_id || ""} onChange={(e) => {
                  const id = e.target.value;
                  set("customer_id", id);
                  const c = customers.find((x) => x.id === id);
                  set("customer_name", c ? c.customer_name : "");
                }} data-testid="form-customer">
                  <option value="">— Select —</option>
                  {customers.map((c) => <option key={c.id} value={c.id}>{c.customer_name}</option>)}
                </select>
                <button type="button" className="btn-secondary text-xs flex items-center gap-1 whitespace-nowrap" onClick={() => setShowNewCust(true)} data-testid="add-customer-inline">
                  <UserPlus size={12} weight="bold" /> New
                </button>
              </div>
            </Field>
            <Field label="Customer PO Number">
              <input className="input" value={form.customer_po_number || ""} onChange={(e) => set("customer_po_number", e.target.value)} />
            </Field>

            <Field label="PO Date"><input type="date" className="input" value={form.po_date || ""} onChange={(e) => set("po_date", e.target.value)} /></Field>
            <Field label="Start Date"><input type="date" className="input" value={form.start_date || ""} onChange={(e) => set("start_date", e.target.value)} /></Field>
            <Field label="End Date"><input type="date" className="input" value={form.end_date || ""} onChange={(e) => set("end_date", e.target.value)} /></Field>
            <Field label="Billing Type">
              <select className="input" value={form.billing_type} onChange={(e) => set("billing_type", e.target.value)} data-testid="form-billing-type">
                <option>Monthly</option><option>Milestone</option>
              </select>
            </Field>

            <Field label="PO Value (₹)"><input type="number" className="input font-mono" value={form.po_value} onChange={(e) => set("po_value", e.target.value)} data-testid="form-po-value" /></Field>
            <Field label="Revenue Total (₹)"><input type="number" className="input font-mono" value={form.revenue_total} onChange={(e) => set("revenue_total", e.target.value)} /></Field>
            <Field label="Cost Total (₹)"><input type="number" className="input font-mono" value={form.cost_total} onChange={(e) => set("cost_total", e.target.value)} /></Field>
            <Field label="Business Category">
              <select className="input" value={form.business_category} onChange={(e) => set("business_category", e.target.value)}>
                <option>GMR</option><option>Non-GMR</option>
              </select>
            </Field>

            <Field label="P&L Location"><input className="input" value={form.pnl_location || ""} onChange={(e) => set("pnl_location", e.target.value)} /></Field>
            <Field label="P&L Region"><input className="input" value={form.pnl_region || ""} onChange={(e) => set("pnl_region", e.target.value)} /></Field>
            <Field label="Location"><input className="input" value={form.location || ""} onChange={(e) => set("location", e.target.value)} /></Field>
            <Field label="Ownership Email"><input className="input" value={form.ownership_email || ""} onChange={(e) => set("ownership_email", e.target.value)} /></Field>

            <Field label="Description" full><textarea className="input" rows={2} value={form.description || ""} onChange={(e) => set("description", e.target.value)} /></Field>
            <Field label="Baseline Remarks" full><textarea className="input" rows={2} value={form.baseline_remarks || ""} onChange={(e) => set("baseline_remarks", e.target.value)} /></Field>
          </div>

          {/* Milestones editor */}
          <div className="border border-[var(--border)] p-4">
            <div className="flex items-center justify-between mb-3">
              <div>
                <div className="text-[10px] tracking-overline text-[var(--muted)]">Milestones</div>
                <div className="text-sm font-medium text-[var(--text)]">
                  {form.milestones?.length || 0} milestone(s) — auto-extracted from PDF or added manually
                </div>
              </div>
              <button type="button" className="btn-secondary text-xs flex items-center gap-1" onClick={addMilestone} data-testid="add-milestone-btn">
                <Plus size={12} weight="bold" /> Add Milestone
              </button>
            </div>
            {form.milestones?.length > 0 ? (
              <div className="space-y-2">
                {form.milestones.map((m, i) => (
                  <div key={i} className="grid grid-cols-12 gap-2 items-center" data-testid={`milestone-row-${i}`}>
                    <input className="input col-span-4" placeholder="Milestone name" value={m.milestone_name || ""} onChange={(e) => updateMilestone(i, { milestone_name: e.target.value })} />
                    <input type="date" className="input col-span-3" value={m.due_date || ""} onChange={(e) => updateMilestone(i, { due_date: e.target.value })} />
                    <input type="number" className="input col-span-3 font-mono" placeholder="Value" value={m.value || 0} onChange={(e) => updateMilestone(i, { value: e.target.value })} />
                    <label className="col-span-1 flex items-center gap-1 text-xs text-[var(--muted)]">
                      <input type="checkbox" checked={!!m.is_billed} onChange={(e) => updateMilestone(i, { is_billed: e.target.checked })} /> Billed
                    </label>
                    <button type="button" className="btn-ghost col-span-1" onClick={() => removeMilestone(i)} data-testid={`milestone-remove-${i}`}>
                      <Trash size={14} />
                    </button>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-sm text-[var(--muted)] py-4 text-center border border-dashed border-[var(--border)]">
                No milestones yet. PDF auto-parse can pre-fill these — or click <span className="font-semibold text-[var(--gold)]">Add Milestone</span>.
              </div>
            )}
          </div>

          {err && <div className="text-xs text-[var(--danger)] bg-[color-mix(in_srgb,var(--danger)_10%,transparent)] p-2 border border-[var(--danger)]">{err}</div>}

          <div className="flex justify-end gap-2 pt-2">
            <button type="button" className="btn-secondary" onClick={onClose}>Cancel</button>
            <button type="submit" className="btn-primary" disabled={busy} data-testid="form-submit">
              {busy ? "Saving…" : "Save Project"}
            </button>
          </div>
        </form>

        {showNewCust && <InlineCustomerForm onClose={() => setShowNewCust(false)} onCreated={onCustomerCreated} />}
      </div>
    </div>
  );
}

function Field({ label, children, full }) {
  return (
    <div className={full ? "col-span-2" : ""}>
      <label className="block text-[10px] tracking-overline text-[var(--muted)] mb-1.5">{label}</label>
      {children}
    </div>
  );
}

function InlineCustomerForm({ onClose, onCreated }) {
  const [form, setForm] = useState({ customer_name: "", sap_customer_code: "", contact_person: "", email: "", phone: "", country: "India" });
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }));
  const submit = async (e) => {
    e.preventDefault(); setBusy(true); setErr("");
    try {
      const { data } = await api.post("/customers", form);
      onCreated(data);
    } catch (e) {
      setErr(formatApiErrorDetail(e.response?.data?.detail) || e.message);
    } finally { setBusy(false); }
  };
  return (
    <div className="fixed inset-0 bg-black/60 z-[60] flex items-center justify-center p-4" data-testid="inline-customer-modal">
      <form onSubmit={submit} className="bg-[var(--surface)] border border-[var(--border)] w-full max-w-md">
        <div className="p-5 border-b border-[var(--border)] flex justify-between items-center">
          <h3 className="font-display text-lg font-bold">Quick Add Customer</h3>
          <button type="button" className="btn-ghost" onClick={onClose}><X size={16} /></button>
        </div>
        <div className="p-5 space-y-3">
          <input className="input" required placeholder="Customer Name *" value={form.customer_name} onChange={(e) => set("customer_name", e.target.value)} data-testid="inline-cust-name" />
          <input className="input" placeholder="SAP Customer Code" value={form.sap_customer_code} onChange={(e) => set("sap_customer_code", e.target.value)} />
          <input className="input" placeholder="Contact Person" value={form.contact_person} onChange={(e) => set("contact_person", e.target.value)} />
          <input className="input" type="email" placeholder="Email" value={form.email} onChange={(e) => set("email", e.target.value)} />
          <input className="input" placeholder="Phone" value={form.phone} onChange={(e) => set("phone", e.target.value)} />
          <input className="input" placeholder="Country" value={form.country} onChange={(e) => set("country", e.target.value)} />
          {err && <div className="text-xs text-[var(--danger)]">{err}</div>}
        </div>
        <div className="p-5 border-t border-[var(--border)] flex justify-end gap-2">
          <button type="button" className="btn-secondary" onClick={onClose}>Cancel</button>
          <button type="submit" className="btn-primary" disabled={busy} data-testid="inline-cust-submit">{busy ? "Creating…" : "Create Customer"}</button>
        </div>
      </form>
    </div>
  );
}
