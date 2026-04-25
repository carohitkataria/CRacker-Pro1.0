import React, { useRef, useState } from "react";
import api, { formatApiErrorDetail } from "@/lib/api";
import { X, Plus, Trash, UserPlus, FilePdf, MagicWand, Warning, CheckCircle } from "@phosphor-icons/react";

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

  // PDF auto-parse state
  const pdfRef = useRef(null);
  const [parsing, setParsing] = useState(false);
  const [parsePreview, setParsePreview] = useState(null);
  const [parseErr, setParseErr] = useState("");

  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }));

  const onPickPdf = async (file) => {
    if (!file) return;
    setParsing(true); setParseErr(""); setParsePreview(null);
    try {
      const fd = new FormData(); fd.append("file", file);
      const { data } = await api.post("/projects/parse-pdf", fd, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setParsePreview({ ...data, applied: false });
    } catch (e) {
      setParseErr(formatApiErrorDetail(e.response?.data?.detail) || e.message);
    } finally {
      setParsing(false);
      if (pdfRef.current) pdfRef.current.value = "";
    }
  };

  const applyParsed = () => {
    if (!parsePreview?.parsed) return;
    const p = parsePreview.parsed;
    setForm((f) => {
      const next = { ...f };
      // Only fill empty fields to avoid clobbering manual edits
      const fillIfEmpty = (key, val) => { if (val !== null && val !== undefined && val !== "" && (next[key] === undefined || next[key] === "" || next[key] === 0 || next[key] === null)) next[key] = val; };
      fillIfEmpty("customer_po_number", p.customer_po_number);
      fillIfEmpty("po_date", normaliseDate(p.po_date));
      fillIfEmpty("start_date", normaliseDate(p.start_date));
      fillIfEmpty("end_date", normaliseDate(p.end_date));
      fillIfEmpty("po_value", p.po_value);
      fillIfEmpty("currency", p.currency);
      fillIfEmpty("billing_type", p.billing_type);
      fillIfEmpty("description", p.description);
      // Customer name (only if Customer PO and field empty)
      if (p.po_type === "Customer PO" && p.customer_name && !next.customer_name) {
        next.customer_name = p.customer_name;
      }
      // Milestones — only replace when current list is empty
      if (Array.isArray(p.milestones) && p.milestones.length > 0 && (!next.milestones || next.milestones.length === 0)) {
        next.milestones = p.milestones.map((m) => ({
          milestone_name: m.milestone_name || "",
          due_date: normaliseDate(m.due_date) || "",
          value: Number(m.value || 0),
          is_billed: !!m.is_billed,
        }));
        if (!next.billing_type) next.billing_type = "Milestone";
      }
      return next;
    });
    setParsePreview((pp) => ({ ...pp, applied: true }));
  };

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
          {/* PDF Auto-Parse Panel */}
          <div className="border border-[var(--border)] p-4 bg-[var(--surface-2)]">
            <div className="flex items-start gap-3">
              <div className="shrink-0 mt-0.5">
                <MagicWand size={22} weight="duotone" className="text-[var(--gold)]" />
              </div>
              <div className="flex-1 min-w-0">
                <div className="text-[10px] tracking-overline text-[var(--muted)]">Smart Auto-Fill</div>
                <div className="font-display text-sm font-bold mb-0.5">Parse a PO PDF to pre-fill this form</div>
                <p className="text-[12px] text-[var(--muted)] mb-3">
                  Detects whether the file is a <span className="font-semibold text-[var(--text)]">Customer PO</span> (WAISL is the vendor) or a{" "}
                  <span className="font-semibold text-[var(--text)]">Vendor PO</span> (WAISL is the issuer). Review the extracted fields and <span className="font-semibold text-[var(--gold)]">Apply</span> to populate the form. Empty fields only — your edits are preserved.
                </p>
                <div className="flex items-center gap-2 flex-wrap">
                  <input
                    ref={pdfRef}
                    type="file"
                    accept="application/pdf,.pdf"
                    className="hidden"
                    onChange={(e) => onPickPdf(e.target.files?.[0])}
                    data-testid="modal-pdf-input"
                  />
                  <button
                    type="button"
                    className="btn-secondary text-xs flex items-center gap-1"
                    onClick={() => pdfRef.current?.click()}
                    disabled={parsing}
                    data-testid="modal-pdf-pick"
                  >
                    <FilePdf size={12} weight="bold" /> {parsing ? "Parsing…" : (parsePreview ? "Choose another PDF" : "Choose PDF & Parse")}
                  </button>
                  {parsePreview && (
                    <span className="text-[11px] text-[var(--muted)] truncate">
                      {parsePreview.file_name} · {(parsePreview.size / 1024).toFixed(0)} KB
                    </span>
                  )}
                </div>

                {parseErr && (
                  <div className="text-xs text-[var(--danger)] mt-3 flex items-start gap-1">
                    <Warning size={12} weight="bold" /> {parseErr}
                  </div>
                )}

                {parsePreview?.parsed && <ParsedPreview parsed={parsePreview.parsed} applied={parsePreview.applied} onApply={applyParsed} />}
              </div>
            </div>
          </div>

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

// Normalise common PO date formats to YYYY-MM-DD for <input type="date" />
function normaliseDate(s) {
  if (!s || typeof s !== "string") return "";
  const months = { jan: "01", feb: "02", mar: "03", apr: "04", may: "05", jun: "06", jul: "07", aug: "08", sep: "09", sept: "09", oct: "10", nov: "11", dec: "12" };
  const t = s.trim().replace(/[\s\.]+/g, "-").replace(/\/+/g, "-");
  // dd-mm-yyyy or dd-mmm-yyyy or dd-month-yyyy
  let m = t.match(/^(\d{1,2})-([A-Za-z0-9]{1,9})-(\d{2,4})$/);
  if (m) {
    let [, d, mo, y] = m;
    if (/^\d+$/.test(mo)) mo = mo.padStart(2, "0");
    else mo = months[mo.toLowerCase().slice(0, 4)] || months[mo.toLowerCase().slice(0, 3)] || "";
    if (!mo) return "";
    if (y.length === 2) y = (parseInt(y, 10) > 50 ? "19" : "20") + y;
    return `${y}-${mo}-${d.padStart(2, "0")}`;
  }
  // yyyy-mm-dd already
  m = t.match(/^(\d{4})-(\d{1,2})-(\d{1,2})$/);
  if (m) return `${m[1]}-${m[2].padStart(2, "0")}-${m[3].padStart(2, "0")}`;
  return "";
}

function ParsedPreview({ parsed, applied, onApply }) {
  const cls = parsed.po_classification || {};
  const typeStyle =
    parsed.po_type === "Customer PO" ? "badge-approved" :
    parsed.po_type === "Vendor PO" ? "badge-gold" : "badge-neutral";
  const items = [
    ["PO Number", parsed.customer_po_number],
    ["PO Date", parsed.po_date],
    ["PO Value", parsed.po_value != null ? Number(parsed.po_value).toLocaleString() : null],
    ["Currency", parsed.currency],
    ["Start Date", parsed.start_date],
    ["End Date", parsed.end_date],
    ["Billing Type", parsed.billing_type],
    ["Issuer", parsed.issuer],
    ["Recipient", parsed.recipient],
    ["Customer", parsed.customer_name],
    ["Vendor", parsed.vendor_name],
    ["Description", parsed.description],
  ].filter(([, v]) => v);

  return (
    <div className="mt-3 border border-[var(--border)] bg-[var(--surface)] p-3" data-testid="parse-preview">
      <div className="flex items-center justify-between mb-2 gap-2 flex-wrap">
        <div className="flex items-center gap-2">
          <span className={`badge ${typeStyle}`} data-testid="parse-po-type">{parsed.po_type}</span>
          {cls.confidence && <span className="text-[10px] tracking-overline text-[var(--muted)]">Confidence · {cls.confidence}</span>}
        </div>
        {applied ? (
          <span className="badge badge-approved flex items-center gap-1"><CheckCircle size={10} weight="bold" /> Applied</span>
        ) : (
          <button type="button" className="btn-primary text-xs flex items-center gap-1" onClick={onApply} data-testid="parse-apply-btn">
            <CheckCircle size={12} weight="bold" /> Apply to form
          </button>
        )}
      </div>

      {items.length > 0 ? (
        <div className="grid grid-cols-2 md:grid-cols-3 gap-x-4 gap-y-1.5 text-xs">
          {items.map(([k, v]) => (
            <div key={k} className="min-w-0">
              <div className="text-[9px] tracking-overline text-[var(--muted)]">{k}</div>
              <div className="text-[var(--text)] truncate" title={String(v)}>{String(v)}</div>
            </div>
          ))}
        </div>
      ) : (
        <div className="text-xs text-[var(--muted)]">No structured fields detected — please fill manually.</div>
      )}

      {Array.isArray(parsed.milestones) && parsed.milestones.length > 0 && (
        <div className="mt-3 pt-3 border-t border-[var(--border-soft)]">
          <div className="text-[10px] tracking-overline text-[var(--muted)] mb-1">Milestones found · {parsed.milestones.length}</div>
          <div className="text-[11px] text-[var(--muted)]">
            {parsed.milestones.slice(0, 4).map((m, i) => (
              <span key={i} className="inline-block mr-3">
                <span className="text-[var(--text)]">{m.milestone_name}</span> · {m.due_date} · {Number(m.value || 0).toLocaleString()}
              </span>
            ))}
            {parsed.milestones.length > 4 && <span>… +{parsed.milestones.length - 4} more</span>}
          </div>
        </div>
      )}

      {Array.isArray(parsed.warnings) && parsed.warnings.length > 0 && (
        <div className="mt-2 text-[11px] text-[var(--warning)] flex items-start gap-1">
          <Warning size={12} weight="bold" /> {parsed.warnings.join(" · ")}
        </div>
      )}
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
