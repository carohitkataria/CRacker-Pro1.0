import React, { useEffect, useState } from "react";
import api, { formatApiErrorDetail } from "@/lib/api";
import PageHeader from "@/components/PageHeader";
import { Plus, X, Key, Trash } from "@phosphor-icons/react";

const ROLES = ["admin", "finance", "sales", "delivery", "leadership", "approver"];

export default function AdminUsersPage() {
  const [rows, setRows] = useState([]);
  const [show, setShow] = useState(false);
  const [editing, setEditing] = useState(null);
  const [resetUser, setResetUser] = useState(null);

  const load = async () => {
    const { data } = await api.get("/admin/users");
    setRows(data);
  };
  useEffect(() => { load(); }, []);

  const onDeactivate = async (id) => {
    if (!window.confirm("Deactivate this user?")) return;
    await api.delete(`/admin/users/${id}`); load();
  };

  return (
    <div data-testid="admin-users-page">
      <PageHeader
        title="User Management"
        subtitle="Provision access · reset passwords · manage roles"
        breadcrumb="HOME · ADMIN · USERS"
        actions={<button className="btn-primary text-xs flex items-center gap-1" onClick={() => { setEditing(null); setShow(true); }} data-testid="add-user-btn"><Plus size={12} /> Add User</button>}
      />
      <div className="px-8 py-5">
        <div className="tile overflow-x-auto">
          <table className="tbl">
            <thead><tr><th>Name</th><th>Email</th><th>Role</th><th>Location</th><th>Reporting Manager</th><th>Active</th><th></th></tr></thead>
            <tbody>
              {rows.map((u) => (
                <tr key={u.id} data-testid={`user-row-${u.id}`}>
                  <td className="font-medium">{u.name}</td>
                  <td>{u.email}</td>
                  <td><span className="badge badge-gold capitalize">{u.role}</span></td>
                  <td>{u.location || "—"}</td>
                  <td>{u.reporting_manager_email || "—"}</td>
                  <td>{u.is_active ? <span className="badge badge-approved">Active</span> : <span className="badge badge-rejected">Inactive</span>}</td>
                  <td>
                    <button className="btn-ghost text-xs" onClick={() => { setEditing(u); setShow(true); }}>Edit</button>
                    <button className="btn-ghost text-xs ml-1" onClick={() => setResetUser(u)} data-testid={`reset-${u.id}`}><Key size={12} /></button>
                    <button className="btn-ghost text-xs ml-1" onClick={() => onDeactivate(u.id)}><Trash size={12} /></button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {show && <UserModal user={editing} onClose={() => setShow(false)} onSaved={() => { setShow(false); load(); }} />}
      {resetUser && <ResetModal user={resetUser} onClose={() => setResetUser(null)} />}
    </div>
  );
}

function UserModal({ user, onClose, onSaved }) {
  const isEdit = !!user?.id;
  const [form, setForm] = useState(user || { email: "", password: "", name: "", role: "finance", location: "", reporting_manager_email: "" });
  const [err, setErr] = useState(""); const [busy, setBusy] = useState(false);
  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }));
  const submit = async (e) => {
    e.preventDefault(); setBusy(true); setErr("");
    try {
      if (isEdit) {
        await api.put(`/admin/users/${user.id}`, { name: form.name, role: form.role, location: form.location, reporting_manager_email: form.reporting_manager_email });
      } else {
        await api.post("/admin/users", form);
      }
      onSaved();
    } catch (e) { setErr(formatApiErrorDetail(e.response?.data?.detail) || e.message); } finally { setBusy(false); }
  };
  return (
    <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4">
      <form onSubmit={submit} className="bg-[var(--surface)] border border-[var(--border)] w-full max-w-md" data-testid="user-modal">
        <div className="p-5 border-b flex justify-between items-center"><h3 className="font-display text-lg font-bold">{isEdit ? "Edit" : "New"} User</h3><button type="button" onClick={onClose}><X size={16} /></button></div>
        <div className="p-5 space-y-3">
          <input className="input" placeholder="Full name" required value={form.name} onChange={(e) => set("name", e.target.value)} data-testid="user-name" />
          <input type="email" className="input" placeholder="Email" required disabled={isEdit} value={form.email} onChange={(e) => set("email", e.target.value)} data-testid="user-email" />
          {!isEdit && <input type="password" className="input" placeholder="Initial password" required minLength={6} value={form.password} onChange={(e) => set("password", e.target.value)} data-testid="user-password" />}
          <select className="input" value={form.role} onChange={(e) => set("role", e.target.value)} data-testid="user-role">
            {ROLES.map((r) => <option key={r} value={r} className="capitalize">{r}</option>)}
          </select>
          <input className="input" placeholder="Location" value={form.location || ""} onChange={(e) => set("location", e.target.value)} />
          <input className="input" placeholder="Reporting manager email" value={form.reporting_manager_email || ""} onChange={(e) => set("reporting_manager_email", e.target.value)} />
          {err && <div className="text-xs text-[var(--danger)] bg-[color-mix(in_srgb,var(--danger)_12%,transparent)] border border-[color-mix(in_srgb,var(--danger)_30%,transparent)] p-2">{err}</div>}
        </div>
        <div className="p-5 border-t flex justify-end gap-2">
          <button type="button" className="btn-secondary" onClick={onClose}>Cancel</button>
          <button type="submit" className="btn-primary" disabled={busy} data-testid="user-modal-submit">{busy ? "Saving…" : "Save"}</button>
        </div>
      </form>
    </div>
  );
}

function ResetModal({ user, onClose }) {
  const [pwd, setPwd] = useState("");
  const [busy, setBusy] = useState(false); const [err, setErr] = useState("");
  const submit = async (e) => {
    e.preventDefault(); setBusy(true); setErr("");
    try { await api.post("/admin/users/reset-password", { user_id: user.id, new_password: pwd }); onClose(); alert("Password reset"); }
    catch (e) { setErr(formatApiErrorDetail(e.response?.data?.detail) || e.message); }
    finally { setBusy(false); }
  };
  return (
    <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4">
      <form onSubmit={submit} className="bg-[var(--surface)] border w-full max-w-sm p-5 space-y-3" data-testid="reset-modal">
        <h3 className="font-display text-lg font-bold">Reset password for</h3>
        <div className="text-sm text-[var(--muted)]">{user.email}</div>
        <input type="password" className="input" required minLength={6} placeholder="New password" value={pwd} onChange={(e) => setPwd(e.target.value)} data-testid="reset-password-input" />
        {err && <div className="text-xs text-[var(--danger)]">{err}</div>}
        <div className="flex justify-end gap-2">
          <button type="button" className="btn-secondary" onClick={onClose}>Cancel</button>
          <button className="btn-primary" disabled={busy} data-testid="reset-submit">{busy ? "Saving…" : "Reset"}</button>
        </div>
      </form>
    </div>
  );
}
