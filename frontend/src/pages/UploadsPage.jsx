import React, { useEffect, useRef, useState } from "react";
import api, { formatApiErrorDetail } from "@/lib/api";
import PageHeader from "@/components/PageHeader";
import { CloudArrowUp, DownloadSimple, FileXls, CheckCircle, WarningCircle } from "@phosphor-icons/react";
import { formatDateTime } from "@/lib/format";

const ENTITIES = [
  { key: "project", label: "Projects" },
  { key: "customer", label: "Customers" },
  { key: "employee", label: "Employees" },
  { key: "supplier", label: "Suppliers" },
  { key: "revenue", label: "Revenue Lines" },
  { key: "cost", label: "Cost Lines" },
];

export default function UploadsPage() {
  const [entity, setEntity] = useState("project");
  const [logs, setLogs] = useState([]);
  const [result, setResult] = useState(null);
  const [busy, setBusy] = useState(false);
  const [drag, setDrag] = useState(false);
  const inputRef = useRef();

  const loadLogs = async () => {
    const { data } = await api.get("/uploads/logs");
    setLogs(data);
  };
  useEffect(() => { loadLogs(); }, []);

  const downloadTemplate = async () => {
    const r = await api.get(`/uploads/template/${entity}`, { responseType: "blob" });
    const url = window.URL.createObjectURL(new Blob([r.data]));
    const a = document.createElement("a"); a.href = url; a.download = `${entity}_template.xlsx`; a.click();
    window.URL.revokeObjectURL(url);
  };

  const handleFile = async (file) => {
    if (!file) return;
    setBusy(true); setResult(null);
    try {
      const fd = new FormData(); fd.append("file", file);
      const { data } = await api.post(`/uploads/${entity}`, fd, { headers: { "Content-Type": "multipart/form-data" } });
      setResult(data);
      loadLogs();
    } catch (e) {
      setResult({ error: formatApiErrorDetail(e.response?.data?.detail) || e.message });
    } finally { setBusy(false); }
  };

  return (
    <div data-testid="uploads-page">
      <PageHeader
        title="Excel Upload Engine"
        subtitle="Bulk import masters and projects from Excel — with validation and audit"
        breadcrumb="HOME · EXCEL UPLOAD"
      />

      <div className="px-8 py-6 space-y-6">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          <div className="lg:col-span-2 space-y-4">
            <div className="tile p-5">
              <div className="text-[10px] tracking-overline text-[#5E5E5A] mb-2">Step 1 · Choose entity</div>
              <div className="flex flex-wrap gap-2">
                {ENTITIES.map((e) => (
                  <button
                    key={e.key}
                    onClick={() => setEntity(e.key)}
                    className={`px-3 py-2 text-xs font-medium border ${entity === e.key ? "bg-[#111110] text-white border-[#111110]" : "border-[#E5E5E0] text-[#5E5E5A] hover:border-[#A67C00]"}`}
                    data-testid={`entity-${e.key}`}
                  >
                    {e.label}
                  </button>
                ))}
              </div>
            </div>

            <div className="tile p-5">
              <div className="flex items-center justify-between mb-3">
                <div>
                  <div className="text-[10px] tracking-overline text-[#5E5E5A]">Step 2 · Download template</div>
                  <p className="text-sm text-[#5E5E5A]">Get the empty Excel template for <span className="font-semibold">{entity}</span>.</p>
                </div>
                <button className="btn-secondary text-xs flex items-center gap-1" onClick={downloadTemplate} data-testid="download-template-btn">
                  <DownloadSimple size={12} /> Download Template
                </button>
              </div>
            </div>

            <div
              className={`tile p-10 border-2 border-dashed transition-all ${drag ? "border-[#A67C00] bg-[#fdf6e3]" : "border-[#E5E5E0]"}`}
              onDragOver={(e) => { e.preventDefault(); setDrag(true); }}
              onDragLeave={() => setDrag(false)}
              onDrop={(e) => { e.preventDefault(); setDrag(false); const f = e.dataTransfer.files?.[0]; handleFile(f); }}
              data-testid="drop-zone"
            >
              <div className="text-center">
                <CloudArrowUp size={42} weight="duotone" className="text-[#A67C00] mx-auto" />
                <div className="font-display text-lg font-bold mt-3">Step 3 · Drop your filled Excel here</div>
                <p className="text-sm text-[#5E5E5A] mt-1">or click below to choose a file (.xlsx)</p>
                <input
                  ref={inputRef}
                  type="file"
                  accept=".xlsx"
                  className="hidden"
                  onChange={(e) => handleFile(e.target.files?.[0])}
                  data-testid="upload-input"
                />
                <button
                  className="btn-primary mt-4"
                  onClick={() => inputRef.current?.click()}
                  disabled={busy}
                  data-testid="upload-trigger"
                >
                  {busy ? "Processing…" : "Choose File"}
                </button>
              </div>
            </div>

            {result && (
              <div className="tile p-5" data-testid="upload-result">
                <div className="flex items-center gap-3 mb-3">
                  {result.error
                    ? <WarningCircle size={22} className="text-[#991B1B]" />
                    : result.failed_rows === 0
                      ? <CheckCircle size={22} className="text-[#2E6B4A]" />
                      : <WarningCircle size={22} className="text-[#B45309]" />}
                  <div>
                    <div className="font-display text-lg font-bold">
                      {result.error ? "Upload failed" : "Upload complete"}
                    </div>
                    {!result.error && (
                      <div className="text-sm text-[#5E5E5A]">
                        Total {result.total_rows} · ✓ {result.success_rows} succeeded · ✗ {result.failed_rows} failed
                      </div>
                    )}
                    {result.error && <div className="text-sm text-[#991B1B]">{result.error}</div>}
                  </div>
                </div>
                {result.failures?.length > 0 && (
                  <div>
                    <div className="text-[10px] tracking-overline text-[#5E5E5A] mb-1">Failed Rows</div>
                    <div className="max-h-64 overflow-y-auto border border-[#E5E5E0]">
                      <table className="tbl">
                        <thead><tr><th>Row</th><th>Errors</th></tr></thead>
                        <tbody>
                          {result.failures.map((f, i) => (
                            <tr key={i}>
                              <td className="font-mono">{f.row}</td>
                              <td className="text-[#991B1B] text-xs">{(f.errors || []).join("; ")}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>

          <div className="tile p-5">
            <div className="flex items-center justify-between mb-3">
              <div>
                <div className="text-[10px] tracking-overline text-[#5E5E5A]">Recent Upload Logs</div>
                <div className="font-display font-bold">Last 200 jobs</div>
              </div>
              <FileXls size={18} weight="duotone" className="text-[#A67C00]" />
            </div>
            <div className="space-y-3 max-h-[460px] overflow-y-auto">
              {logs.map((l) => (
                <div key={l.id} className="border border-[#E5E5E0] p-3" data-testid={`log-${l.id}`}>
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-semibold uppercase tracking-wider text-[#A67C00]">{l.entity_type}</span>
                    <span className="text-[#5E5E5A]">{formatDateTime(l.uploaded_at)}</span>
                  </div>
                  <div className="text-sm font-medium mt-1 truncate">{l.file_name}</div>
                  <div className="text-xs text-[#5E5E5A] mt-1">
                    {l.success_rows} ok / <span className="text-[#991B1B]">{l.failed_rows} failed</span> · {l.uploaded_by}
                  </div>
                </div>
              ))}
              {logs.length === 0 && <div className="text-sm text-[#5E5E5A] text-center py-6">No uploads yet</div>}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
