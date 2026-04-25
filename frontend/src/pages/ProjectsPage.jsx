import React, { useEffect, useState } from "react";
import api from "@/lib/api";
import PageHeader from "@/components/PageHeader";
import { useCurrency } from "@/lib/currency";
import { formatCurrency, formatDate } from "@/lib/format";
import { useNavigate } from "react-router-dom";
import { StatusBadge } from "@/components/StatusBadge";
import { STAGES } from "@/components/StageTracker";
import { Plus, MagnifyingGlass, FunnelSimple } from "@phosphor-icons/react";
import ProjectFormModal from "@/components/ProjectFormModal";

export default function ProjectsPage() {
  const { mode } = useCurrency();
  const navigate = useNavigate();
  const [projects, setProjects] = useState([]);
  const [stage, setStage] = useState("");
  const [search, setSearch] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const [customers, setCustomers] = useState([]);

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

  return (
    <div data-testid="projects-page">
      <PageHeader
        title="Projects"
        subtitle="End-to-end commercial lifecycle"
        breadcrumb="HOME · PROJECTS"
        actions={
          <button className="btn-primary flex items-center gap-2" onClick={() => setShowCreate(true)} data-testid="new-project-btn">
            <Plus size={14} weight="bold" /> New Project
          </button>
        }
      />

      <div className="px-8 py-5 space-y-4">
        {/* Filters */}
        <div className="tile p-4 flex flex-wrap items-center gap-3">
          <div className="relative flex-1 min-w-[240px]">
            <MagnifyingGlass size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-[#5E5E5A]" />
            <input
              className="input pl-9"
              placeholder="Search by project, WBS or customer…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && load()}
              data-testid="project-search"
            />
          </div>
          <FunnelSimple size={14} className="text-[#5E5E5A]" />
          <button
            className={`btn-ghost ${!stage ? "text-[#A67C00] border-[#A67C00]" : ""} border`}
            onClick={() => setStage("")}
            data-testid="filter-all"
          >
            All
          </button>
          {STAGES.map((s) => (
            <button
              key={s}
              className={`btn-ghost ${stage === s ? "text-[#A67C00] border-[#A67C00]" : ""} border`}
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
              </tr>
            </thead>
            <tbody>
              {projects.map((p) => (
                <tr key={p.id} className="cursor-pointer" onClick={() => navigate(`/projects/${p.id}`)} data-testid={`project-row-${p.id}`}>
                  <td>
                    <div className="font-medium text-[#111110]">{p.project_name}</div>
                    <div className="text-[11px] text-[#5E5E5A]">{p.business_category} · {p.location}</div>
                  </td>
                  <td className="font-mono text-xs">
                    <div>{p.wbs_element || "—"}</div>
                    <div className="text-[#5E5E5A]">{p.customer_po_number || ""}</div>
                  </td>
                  <td>{p.customer_name || "—"}</td>
                  <td><StatusBadge status={p.current_stage} /></td>
                  <td><StatusBadge status={p.approval_status} /></td>
                  <td className="num">{formatCurrency(p.po_value, mode)}</td>
                  <td className={`num ${(p.margin_pct || 0) < 15 ? "text-[#991B1B]" : ""}`}>{(p.margin_pct || 0).toFixed(1)}%</td>
                  <td>{formatDate(p.end_date)}</td>
                </tr>
              ))}
              {projects.length === 0 && (
                <tr><td colSpan={8} className="text-center py-12 text-[#5E5E5A]">No projects yet</td></tr>
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
    </div>
  );
}
