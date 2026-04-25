import React from "react";

export default function PageHeader({ title, subtitle, actions, breadcrumb, testid }) {
  return (
    <div className="px-8 py-6 border-b border-[var(--border)] bg-[var(--surface)]" data-testid={testid || "page-header"}>
      {breadcrumb && <div className="text-[11px] tracking-overline text-[var(--muted)] mb-2">{breadcrumb}</div>}
      <div className="flex items-end justify-between gap-4">
        <div>
          <h1 className="font-display text-3xl font-bold tracking-tight text-[var(--text)]">{title}</h1>
          {subtitle && <p className="text-sm text-[var(--muted)] mt-1">{subtitle}</p>}
        </div>
        {actions && <div className="flex items-center gap-2">{actions}</div>}
      </div>
    </div>
  );
}
