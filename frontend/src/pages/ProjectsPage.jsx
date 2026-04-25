import React, { useEffect, useRef, useState } from "react";
import api from "@/lib/api";
import PageHeader from "@/components/PageHeader";
import { useCurrency } from "@/lib/currency";
import { formatCurrency, formatDate } from "@/lib/format";
import { useNavigate } from "react-router-dom";
import { StatusBadge } from "@/components/StatusBadge";
import { STAGES } from "@/components/StageTracker";
import { Plus, MagnifyingGlass, FunnelSimple, PencilSimple, UploadSimple, DownloadSimple } from "@phosphor-icons/react";
import ProjectFormModal from "@/components/ProjectFormModal";

export default function ProjectsPage() {
  const { mode, inrPerUsd } = useCurrency();
  const navigate = useNavigate();
  const [projects, setProjects] = useState([]);
  const [stage, setStage] = useState("");
  const [search, setSearch] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const [editing, setEditing] = useState(null);
  const [customers, setCustomers] = useState([]);
  const [uploadResult, setUploadResult] = useState(null);
  const fileRef = useRef();

  const load = async () => {
    const params = {};
    if (stage) params.stage = stage;
    if (search) params.search = search;
    const { data } = await api.get("/projects", { params });
    setProjects(data);
  };

  useEffect(() => {
    load();
    api.get("/customers").then((r) => setCustomers(r.data)).catch(() => {});
  }, [stage]); // eslint-disable-line

  const downloadTemplate = async () => {
    const r = await api.get("/uploads/template/project", { responseType: "blob" });
    const url = window.URL.createObjectURL(new Blob([r.data]));
    const a = document.createElement("a"); a.href = url; a.download = "project_template.xlsx"; a.click();
    window.URL.revokeObjectURL(url);
  };

  const onUpload = async (file) => {
    if (!file) return;
    const fd = new FormData(); fd.append("file", file);
    try {
      const { data } = await api.post("/uploads/project", fd, { headers: { "Content-Type": "multipart/form-data" } });
      setUploadResult(data);
      load();
    } catch (e) {
      setUploadResult({ error: e.response?.data?.detail || e.message });
    }
    if (fileRef.current) fileRef.current.value = "";
  };

  return (
    <div data-testid="projects-page">
      <PageHeader
        title="Projects"
        subtitle="End-to-end commercial lifecycle"
        breadcrumb="HOME · PROJECTS"
        actions={
          <div className="flex items-center gap-2">
            <button className="btn-secondary text-xs flex items-center gap-1" onClick={downloadTemplate} data-testid="dl-project-template">
              <DownloadSimple size={12} weight="bold" /> Template
            </button>
            <input ref={fileRef} type="file" accept=".xlsx,.xls,.csv" className="hidden" onChange={(e) => onUpload(e.target.files?.[0])} data-testid="project-upload-input" />
            <button className="btn-secondary text-xs flex items-center gap-1" onClick={() => fileRef.current?.click()} data-testid="upload-projects-btn">
              <UploadSimple size={12} weight="bold" /> Upload Excel
            </button>
            <button className="btn-primary flex items-center gap-2" onClick={() => setShowCreate(true)} data-testid="new-project-btn">
              <Plus size={14} weight="bold" /> New Project
            </button>
          </div>
        }
      />

      {uploadResult && (
        <div className="mx-8 mt-5 tile p-4" data-testid="project-upload-result">
          {uploadResult.error ? (
            <div className="text-sm text-[var(--danger)]">Upload failed: {uploadResult.error}</div>
          ) : (
            <div className="flex items-center justify-between">
              <div className="text-sm">
                <span className="font-semibold">{uploadResult.success_rows}</span> created · {" "}
                <span className="text-[var(--danger)] font-semibold">{uploadResult.failed_rows}</span> failed · {" "}
                <span className="text-[var(--muted)]">file: {uploadResult.file_name}</span>
              </div>
              <button className="btn-ghost text-xs" onClick={() => setUploadResult(null)}>Dismiss</button>
            </div>
          )}
        </div>
      )}

      <div className="px-8 py-5 space-y-4">
        {/* Filters */}
        <div className="tile p-4 flex flex-wrap items-center gap-3">
          <div className="relative flex-1 min-w-[240px]">
            <MagnifyingGlass size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--muted)]" />
            <input
              className="input pl-9"
              placeholder="Search by project, WBS or customer…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && load()}
              data-testid="project-search"
            />
          </div>
          <FunnelSimple size={14} className="text-[var(--muted)]" />
          <button
            className={`btn-ghost ${!stage ? "text-[var(--gold)] border-[var(--gold)]" : ""} border`}
            onClick={() => setStage("")}
            data-testid="filter-all"
          >
            All
          </button>
          {STAGES.map((s) => (
            <button
              key={s}
              className={`btn-ghost ${stage === s ? "text-[var(--gold)] border-[var(--gold)]" : ""} border`}
              onClick={() => setStage(s)}
              data-testid={`filter-${s.replace(/[^a-zA-Z0-9]/g, "-").toLowerCase()}`}
            >
              {s}
            </button>
          ))}
          <button className="btn-secondary" onClick={load} data-testid="apply-search-btn">Search</button>
        </div>

        <div className="tile overflow-hidden">
          <table className="tbl" data-testid="projects-table">
            <thead>
              <tr>
                <th>Project</th>
                <th>WBS / PO</th>
                <th>Customer</th>
                <th>Stage</th>
                <th>Approval</th>
                <th className="num">PO Value</th>
                <th className="num">Margin %</th>
                <th>End Date</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {projects.map((p) => (
                <tr key={p.id} className="cursor-pointer" onClick={() => navigate(`/projects/${p.id}`)} data-testid={`project-row-${p.id}`}>
                  <td>
                    <div className="font-medium text-[var(--text)]">{p.project_name}</div>
                    <div className="text-[11px] text-[var(--muted)]">{p.business_category} · {p.location}</div>
                  </td>
                  <td className="font-mono text-xs">
                    <div>{p.wbs_element || "—"}</div>
                    <div className="text-[var(--muted)]">{p.customer_po_number || ""}</div>
                  </td>
                  <td>{p.customer_name || "—"}</td>
                  <td><StatusBadge status={p.current_stage} /></td>
                  <td><StatusBadge status={p.approval_status} /></td>
                  <td className="num">{formatCurrency(p.po_value, mode, inrPerUsd)}</td>
                  <td className={`num ${(p.margin_pct || 0) < 15 ? "text-[var(--danger)]" : ""}`}>{(p.margin_pct || 0).toFixed(1)}%</td>
                  <td>{formatDate(p.end_date)}</td>
                  <td className="text-right">
                    <button
                      className="btn-ghost"
                      title="Edit project"
                      onClick={(e) => { e.stopPropagation(); setEditing(p); }}
                      data-testid={`project-edit-${p.id}`}
                    >
                      <PencilSimple size={16} weight="duotone" className="text-[var(--gold)]" />
                    </button>
                  </td>
                </tr>
              ))}
              {projects.length === 0 && (
                <tr><td colSpan={9} className="text-center py-12 text-[var(--muted)]">No projects yet</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {showCreate && (
        <ProjectFormModal
          customers={customers}
          onClose={() => setShowCreate(false)}
          onSaved={() => { setShowCreate(false); load(); }}
        />
      )}
      {editing && (
        <ProjectFormModal
          project={editing}
          customers={customers}
          onClose={() => setEditing(null)}
          onSaved={() => { setEditing(null); load(); }}
        />
      )}
    </div>
  );
}
