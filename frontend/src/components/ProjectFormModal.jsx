import React, { useState } from "react";
import api, { formatApiErrorDetail } from "@/lib/api";
import { X } from "@phosphor-icons/react";

const empty = {
  project_name: "", wbs_element: "", customer_po_number: "", po_date: "",
  start_date: "", end_date: "", billing_type: "Monthly",
  customer_id: "", description: "", currency: "INR",
  po_value: 0, revenue_total: 0, cost_total: 0,
  country: "India", pnl_location: "", pnl_region: "",
  business_category: "Non-GMR", location: "", category1: "",
  ownership_email: "", baseline_remarks: "",
};

export default function ProjectFormModal({ project, customers, onClose, onSaved }) {
  const [form, setForm] = useState(project ? { ...empty, ...project } : empty);
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);

  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }));

  const onSubmit = async (e) => {
    e.preventDefault();
    setBusy(true); setErr("");
    try {
      const payload = { ...form, po_value: Number(form.po_value || 0), revenue_total: Number(form.revenue_total || 0), cost_total: Number(form.cost_total || 0) };
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

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4" data-testid="project-modal">
      <div className="bg-white w-full max-w-3xl max-h-[90vh] overflow-y-auto border border-[#E5E5E0]">
        <div className="flex items-center justify-between p-5 border-b border-[#E5E5E0]">
          <div>
            <div className="text-[10px] tracking-overline text-[#5E5E5A]">{project ? "EDIT" : "CREATE"} PROJECT</div>
            <h2 className="font-display text-xl font-bold">{project ? "Edit Project" : "New Project"}</h2>
          </div>
          <button className="btn-ghost" onClick={onClose} data-testid="modal-close"><X size={18} /></button>
        </div>

        <form onSubmit={onSubmit} className="p-5 grid grid-cols-2 gap-4">
          <Field label="Project Name *" required>
            <input className="input" required value={form.project_name} onChange={(e) => set("project_name", e.target.value)} data-testid="form-project-name" />
          </Field>
          <Field label="WBS Element">
            <input className="input font-mono" value={form.wbs_element || ""} onChange={(e) => set("wbs_element", e.target.value)} data-testid="form-wbs" />
          </Field>
          <Field label="Customer">
            <select className="input" value={form.customer_id || ""} onChange={(e) => {
              const id = e.target.value;
              set("customer_id", id);
              const c = customers.find((x) => x.id === id);
              set("customer_name", c ? c.customer_name : "");
            }} data-testid="form-customer">
              <option value="">— Select —</option>
              {customers.map((c) => <option key={c.id} value={c.id}>{c.customer_name}</option>)}
            </select>
          </Field>
          <Field label="Customer PO Number">
            <input className="input" value={form.customer_po_number || ""} onChange={(e) => set("customer_po_number", e.target.value)} />
          </Field>
          <Field label="PO Date">
            <input type="date" className="input" value={form.po_date || ""} onChange={(e) => set("po_date", e.target.value)} />
          </Field>
          <Field label="Start Date">
            <input type="date" className="input" value={form.start_date || ""} onChange={(e) => set("start_date", e.target.value)} />
          </Field>
          <Field label="End Date">
            <input type="date" className="input" value={form.end_date || ""} onChange={(e) => set("end_date", e.target.value)} />
          </Field>
          <Field label="Billing Type">
            <select className="input" value={form.billing_type} onChange={(e) => set("billing_type", e.target.value)}>
              <option>Monthly</option><option>Milestone</option>
            </select>
          </Field>
          <Field label="PO Value (₹)">
            <input type="number" className="input font-mono" value={form.po_value} onChange={(e) => set("po_value", e.target.value)} data-testid="form-po-value" />
          </Field>
          <Field label="Revenue Total (₹)">
            <input type="number" className="input font-mono" value={form.revenue_total} onChange={(e) => set("revenue_total", e.target.value)} />
          </Field>
          <Field label="Cost Total (₹)">
            <input type="number" className="input font-mono" value={form.cost_total} onChange={(e) => set("cost_total", e.target.value)} />
          </Field>
          <Field label="Business Category">
            <select className="input" value={form.business_category} onChange={(e) => set("business_category", e.target.value)}>
              <option>GMR</option><option>Non-GMR</option>
            </select>
          </Field>
          <Field label="P&L Location">
            <input className="input" value={form.pnl_location || ""} onChange={(e) => set("pnl_location", e.target.value)} />
          </Field>
          <Field label="P&L Region">
            <input className="input" value={form.pnl_region || ""} onChange={(e) => set("pnl_region", e.target.value)} />
          </Field>
          <Field label="Location">
            <input className="input" value={form.location || ""} onChange={(e) => set("location", e.target.value)} />
          </Field>
          <Field label="Ownership Email">
            <input className="input" value={form.ownership_email || ""} onChange={(e) => set("ownership_email", e.target.value)} />
          </Field>
          <Field label="Description" full>
            <textarea className="input" rows={2} value={form.description || ""} onChange={(e) => set("description", e.target.value)} />
          </Field>
          <Field label="Baseline Remarks" full>
            <textarea className="input" rows={2} value={form.baseline_remarks || ""} onChange={(e) => set("baseline_remarks", e.target.value)} />
          </Field>

          {err && <div className="col-span-2 text-xs text-[#991B1B] bg-[#fdeaea] p-2 border border-[#f1c2c2]">{err}</div>}

          <div className="col-span-2 flex justify-end gap-2 mt-2">
            <button type="button" className="btn-secondary" onClick={onClose}>Cancel</button>
            <button type="submit" className="btn-primary" disabled={busy} data-testid="form-submit">
              {busy ? "Saving…" : "Save Project"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function Field({ label, children, full, required }) {
  return (
    <div className={full ? "col-span-2" : ""}>
      <label className="block text-[10px] tracking-overline text-[#5E5E5A] mb-1.5">{label}</label>
      {children}
    </div>
  );
}
