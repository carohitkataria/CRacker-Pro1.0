# CRacker Pro – Product Requirements Document (PRD)

## Original Problem Statement
Build an enterprise-grade Business Finance webportal ("CRacker Pro") for managing the project commercial lifecycle (Pipeline → Deal P&L → Customer PO → Operations → Closure). Replace fragile Excel-based tracking with audit-tracked workflows, configurable approvals, master data management, and a real-time finance dashboard. Source: User-provided BRD + Revenue & Expenses master.

## User Choices (locked-in)
- Stack: React + FastAPI + MongoDB
- Auth: JWT, admin-managed users (no OTP)
- Theme: design-agent picked premium dark+gold/alabaster (Cabinet Grotesk + Work Sans + JetBrains Mono)
- Email: skipped in MVP (in-app only)
- Phase 2 user choices: skip AI Margin Radar; add pencil edit on every project row; build Finance Queries + Customer Profile + Document Attachments (with optional PDF auto-parse)

## User Personas
Admin · Finance · Sales/Delivery · Leadership (CFO/CEO/COO) · Approver

## Core Requirements (BRD-derived)
1. End-to-end project lifecycle (5 stages, forward + backward, approval gating)
2. Master data: Project, Customer, Employee, Supplier, Revenue Line, Cost Line
3. Excel Upload Engine with template, validation, failed rows report, audit logs
4. Configurable Approval Matrix (margin/revenue/category/target stage)
5. Interactive dashboard: KPI tiles (clickable), funnel, billing trend, top customers, vendor exposure, delayed/low-margin lists
6. Currency toggle ₹ Cr ↔ $ M
7. Permanent audit trail (old/new diff)
8. Premium enterprise UI

## Implementation Status

### Phase 1 — Completed Jan 2026 ✅
- JWT auth, bcrypt, brute-force lockout (email-keyed), idempotent admin seeding
- Admin user mgmt + admin-driven password reset
- All 6 master data CRUD endpoints with audit trail
- Project CRUD with auto margin computation (margin_total + margin_pct)
- Workflow engine (5 stages) with `can_transition`; forward + backward (rework)
- Approval Matrix engine: business_category + revenue range + margin range + target stage triggers
- Approval queue with role-based and email-list approvers
- Excel Upload Engine for project/customer/employee/supplier/revenue/cost (string coercion)
- Dashboard summary endpoint
- Audit trail viewer
- Frontend: Login, Dashboard, Projects (list + detail w/ 5 tabs + stage tracker), Masters, Excel Upload, Approvals, Audit, Admin Users, Approval Matrix
- Currency toggle, KPI tiles clickable, recharts visualizations, sidebar role-based menu
- Seeded sample data + 24-test pytest suite

### Phase 2 — Completed Jan 2026 ✅
- **Pencil edit button on every Projects list row** (data-testid `project-edit-{id}`) opens edit modal in-place
- **Finance Query Discussion Engine** — threaded queries per project
  - `POST /api/projects/{pid}/queries` create query
  - `GET /api/projects/{pid}/queries` list
  - `POST /api/queries/{qid}/replies` add reply
  - `PATCH /api/queries/{qid}/status` Open/Closed
  - UI: split-pane (list + thread) with reply input, close/reopen
- **Customer Profile module** — `/customers/:id`
  - `GET /api/customers/{cid}/profile` aggregator: customer + totals + billing position + 4-bucket ageing + stage distribution + linked projects + revenue/cost lines
  - UI: contact strip, SAP outstanding, risk notes, totals, billing rows, ageing bar chart, linked projects table, stage distribution
  - Customer rows in Customers list now navigate to profile
- **Project Document Attachments** with optional PDF auto-parse
  - `POST /api/projects/{pid}/documents?parse=true&apply_extracted=true` (multipart)
  - `GET /api/projects/{pid}/documents`, `GET /api/documents/{did}/download`, `DELETE /api/documents/{did}`
  - PDF parsing via pdfplumber + regex extracts: customer_po_number, po_date, po_value, currency, vendor_references, milestones
  - Optional "apply to project" only fills empty fields (safe)
  - UI: Documents tab with checkboxes for parse + apply, drag-drop, list with download/delete
- Tests: 36/36 pytest passing (24 phase 1 + 13 phase 2 + 1 pencil/customer regression)

## Backlog / Future Phases

### P1 (next)
- Email notifications (SendGrid/Resend) for approvals/queries/delays
- Bulk approve/reject in approvals queue
- Saved/preset filters for projects + audit
- Notification feed (in-app event center)
- Customer Profile: PO history & contracts upload

### P2
- AI Margin Risk Radar (Emergent LLM key) — narrative briefing on the dashboard
- Stage progress tracker by milestones (revenue vs milestone toggle)
- Vendor PO management (full CRUD)
- Forecasting (revenue/cost)
- Advanced search + leadership-only dashboard view

### P3
- SAP API integration (SAP customer code, balance outstanding sync)
- Mobile-responsive layout
- Configurable role-based field-level visibility
- Document storage on S3 / GridFS (currently local disk under /app/backend/uploads/)

## Test Credentials
See `/app/memory/test_credentials.md`.

## Key Files
- Backend: `/app/backend/{server,auth,models,services,excel_utils,pdf_parser}.py`
- Frontend: `/app/frontend/src/{App.js, lib/, components/, pages/}` including `pages/CustomerProfilePage.jsx`
- Design: `/app/design_guidelines.json`
- Tests: `/app/backend/tests/test_crackerpro.py` + `test_phase2.py`
