import React, { useState } from "react";
import api, { formatApiErrorDetail } from "@/lib/api";
import { X, CheckCircle, Warning, CaretLeft, CaretRight } from "@phosphor-icons/react";
import AirplaneButton from "./AirplaneButton";

const STAGES = [
  {
    key: "Prospecting",
    label: "1. Prospecting",
    description: "Identify and qualify the opportunity",
    fields: [
      { name: "opportunity_title", label: "Opportunity Title", required: true, type: "text", full: true },
      { name: "customer_name", label: "Customer Name", required: true, type: "customer" },
      { name: "bd_owner", label: "BD / Account Owner Email", required: true, type: "email" },
      { name: "expected_revenue", label: "Expected Revenue (₹)", required: true, type: "number" },
      { name: "industry", label: "Industry / Sector", required: false, type: "text" },
      { name: "source", label: "Lead Source", required: false, type: "select", options: ["Repeat", "Referral", "RFP", "Cold", "Inbound"] },
      { name: "business_category", label: "Business Category", required: true, type: "select", options: ["GMR", "Non-GMR"] },
      { name: "priority", label: "Priority", required: false, type: "select", options: ["High", "Medium", "Low"] },
    ],
  },
  {
    key: "Active Discussion",
    label: "2. Active Discussion",
    description: "Solution scoping and stakeholder alignment",
    fields: [
      { name: "solution_scope", label: "Solution Scope", required: true, type: "textarea", full: true },
      { name: "expected_timeline", label: "Expected Timeline", required: true, type: "text" },
      { name: "competitors", label: "Competitors Identified", required: false, type: "text" },
    ],
  },
  {
    key: "Proposal Submitted",
    label: "3. Proposal Submitted",
    description: "Commercial proposal delivered",
    fields: [
      { name: "proposal_value", label: "Proposal Value (₹)", required: true, type: "number" },
      { name: "proposal_submitted_on", label: "Submission Date", required: true, type: "date" },
      { name: "proposal_validity", label: "Validity", required: false, type: "text" },
      { name: "proposal_notes", label: "Proposal Notes", required: false, type: "textarea", full: true },
    ],
  },
  {
    key: "Evaluation/Negotiation",
    label: "4. Evaluation / Negotiation",
    description: "Commercial and technical negotiation",
    fields: [
      { name: "negotiated_value", label: "Negotiated Value (₹)", required: true, type: "number" },
      { name: "estimated_margin_pct", label: "Estimated Margin %", required: true, type: "number" },
      { name: "expected_decision_date", label: "Expected Decision Date", required: true, type: "date" },
      { name: "negotiation_notes", label: "Negotiation Notes", required: false, type: "textarea", full: true },
    ],
  },
  {
    key: "Closed",
    label: "5. Closed",
    description: "Win / loss outcome — finance handoff gated on Win",
    fields: [
      { name: "outcome", label: "Outcome", required: true, type: "select", options: ["Open", "Won", "Lost"] },
      { name: "closure_date", label: "Closure Date", required: false, type: "date" },
      { name: "win_loss_reason", label: "Win / Loss Reason", required: false, type: "textarea", full: true },
    ],
  },
];

const emptyForm = {
  opportunity_title: "", customer_id: "", customer_name: "", bd_owner: "",
  expected_revenue: 0, currency: "INR", source: "Repeat", industry: "",
  solution_scope: "", expected_timeline: "", competitors: "", stakeholders: [],
  proposal_value: 0, proposal_submitted_on: "", proposal_validity: "", proposal_notes: "",
  negotiated_value: 0, estimated_margin_pct: 0, expected_decision_date: "", negotiation_notes: "",
  outcome: "Open", closure_date: "", win_loss_reason: "",
  business_category: "Non-GMR", priority: "Medium", remarks: "",
};

export default function PipelineWizardModal({ opportunity, customers, onClose, onSaved }) {
  const [form, setForm] = useState(
    opportunity ? { ...emptyForm, ...opportunity } : emptyForm
  );
  const [activeStage, setActiveStage] = useState(0);
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);

  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }));

  const onSubmit = async () => {
    setBusy(true); setErr("");
    try {
      const payload = {
        ...form,
        expected_revenue: Number(form.expected_revenue || 0),
        proposal_value: Number(form.proposal_value || 0),
        negotiated_value: Number(form.negotiated_value || 0),
        estimated_margin_pct: Number(form.estimated_margin_pct || 0),
      };
      if (opportunity?.id) {
        await api.put(`/pipeline/${opportunity.id}`, payload);
      } else {
        await api.post("/pipeline", payload);
      }
      onSaved();
    } catch (e) {
      setErr(formatApiErrorDetail(e.response?.data?.detail) || e.message);
    } finally { setBusy(false); }
  };

  const prev = () => setActiveStage((i) => Math.max(0, i - 1));
  const next = () => setActiveStage((i) => Math.min(STAGES.length - 1, i + 1));

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" data-testid="pipeline-wizard-modal">
      <div className="bg-[var(--surface)] w-full max-w-4xl max-h-[92vh] overflow-y-auto border border-[var(--border)]">
        <div className="flex items-center justify-between p-5 border-b border-[var(--border)] sticky top-0 bg-[var(--surface)] z-10">
          <div>
            <div className="text-[10px] tracking-overline text-[var(--muted)]">{opportunity ? "EDIT" : "NEW"} OPPORTUNITY</div>
            <h2 className="font-display text-xl font-bold">{opportunity?.opportunity_title || "New Pipeline Opportunity"}</h2>
          </div>
          <button className="btn-ghost" onClick={onClose} data-testid="pipeline-modal-close"><X size={18} /></button>
        </div>

        {/* Stage tabs */}
        <div className="grid grid-cols-5 border-b border-[var(--border)] sticky top-[73px] bg-[var(--surface)] z-10" data-testid="pipeline-stage-tabs">
          {STAGES.map((s, i) => (
            <button
              key={s.key}
              onClick={() => setActiveStage(i)}
              className={`px-3 py-3 text-left border-r border-[var(--border)] transition-colors last:border-r-0
                ${i === activeStage ? "bg-[var(--surface-2)] border-b-2 border-b-[var(--gold)]" : "opacity-70 hover:opacity-100"}`}
              data-testid={`pipeline-tab-${i}`}
            >
              <div className="text-[10px] tracking-overline text-[var(--muted)]">Stage {i + 1}</div>
              <div className="font-display text-xs font-bold text-[var(--text)] truncate">{s.label.replace(/^\d+\.\s/, "")}</div>
            </button>
          ))}
        </div>

        <div className="p-5 space-y-5">
          <div className="text-[11px] text-[var(--muted)]">
            <span className="font-semibold text-[var(--text)]">{STAGES[activeStage].label}</span> — {STAGES[activeStage].description}
            <span className="ml-3 text-[var(--gold)]">* marks required fields (informational only — validation is not enforced yet).</span>
          </div>

          <div className="grid grid-cols-2 gap-4" data-testid={`pipeline-stage-panel-${activeStage}`}>
            {STAGES[activeStage].fields.map((f) => (
              <FieldRenderer key={f.name} field={f} form={form} set={set} customers={customers} />
            ))}
          </div>

          {err && <div className="text-xs text-[var(--danger)] bg-[color-mix(in_srgb,var(--danger)_10%,transparent)] p-2 border border-[var(--danger)] flex items-center gap-1"><Warning size={12} weight="bold" /> {err}</div>}

          <div className="flex items-center justify-between pt-2 border-t border-[var(--border)]">
            <button
              type="button"
              onClick={prev}
              disabled={activeStage === 0}
              className="btn-secondary text-xs flex items-center gap-1 disabled:opacity-40"
              data-testid="pipeline-prev-btn"
            >
              <CaretLeft size={12} /> Previous Stage
            </button>

            <div className="flex items-center gap-2">
              <button type="button" className="btn-secondary" onClick={onClose}>Cancel</button>
              {activeStage < STAGES.length - 1 && (
                <button
                  type="button"
                  onClick={next}
                  className="btn-secondary text-xs flex items-center gap-1"
                  data-testid="pipeline-next-btn"
                >
                  Next Stage <CaretRight size={12} />
                </button>
              )}
              <AirplaneButton
                type="button"
                onClick={onSubmit}
                disabled={busy}
                testid="pipeline-submit"
              >
                {busy ? "Saving…" : (opportunity ? "Update" : "Save Opportunity")}
              </AirplaneButton>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function FieldRenderer({ field, form, set, customers }) {
  const value = form[field.name] ?? (field.type === "number" ? 0 : "");
  const lab = (
    <label className="block text-[10px] tracking-overline text-[var(--muted)] mb-1.5">
      {field.label} {field.required && <span className="text-[var(--gold)]">*</span>}
    </label>
  );
  const wrapCls = field.full ? "col-span-2" : "";
  const tid = `pipe-field-${field.name}`;

  if (field.type === "textarea") {
    return (
      <div className={wrapCls}>
        {lab}
        <textarea
          className="input"
          rows={2}
          value={value}
          onChange={(e) => set(field.name, e.target.value)}
          data-testid={tid}
        />
      </div>
    );
  }
  if (field.type === "select") {
    return (
      <div className={wrapCls}>
        {lab}
        <select className="input" value={value} onChange={(e) => set(field.name, e.target.value)} data-testid={tid}>
          {field.options.map((o) => <option key={o} value={o}>{o}</option>)}
        </select>
      </div>
    );
  }
  if (field.type === "customer") {
    return (
      <div className={wrapCls}>
        {lab}
        <select
          className="input"
          value={form.customer_id || ""}
          onChange={(e) => {
            const id = e.target.value;
            const c = (customers || []).find((x) => x.id === id);
            set("customer_id", id);
            set("customer_name", c?.customer_name || "");
          }}
          data-testid={tid}
        >
          <option value="">— Select Customer —</option>
          {(customers || []).map((c) => <option key={c.id} value={c.id}>{c.customer_name}</option>)}
        </select>
      </div>
    );
  }
  return (
    <div className={wrapCls}>
      {lab}
      <input
        type={field.type === "number" ? "number" : field.type === "date" ? "date" : field.type === "email" ? "email" : "text"}
        className={field.type === "number" ? "input font-mono" : "input"}
        value={value}
        onChange={(e) => set(field.name, e.target.value)}
        data-testid={tid}
      />
    </div>
  );
}

export { STAGES as PIPELINE_STAGES };
