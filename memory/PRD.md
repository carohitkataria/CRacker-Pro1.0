# CRacker Pro – Product Requirements Document (PRD)

## Original Problem Statement
Build an enterprise-grade Business Finance webportal ("CRacker Pro") for managing the project commercial lifecycle (Pipeline → Deal P&L → Customer PO → Operations → Closure). Replace fragile Excel-based tracking with audit-tracked workflows, configurable approvals, master data management, and a real-time finance dashboard. Source: User-provided BRD + Revenue & Expenses master.

Feb 2026 update: implement BRD "Webpage BRD - Development Plan 30th April 2026" — Pipeline module + Navigation/Space optimisation.

## User Choices (locked-in)
- Stack: React + FastAPI + MongoDB
- Auth: JWT, admin-managed users (no OTP)
- Theme: premium dark+gold/alabaster (Cabinet Grotesk + Work Sans + JetBrains Mono)
- Email: skipped in MVP (in-app only)
- BRD (Apr 2026): tabbed stage-wise wizard, `*` markers without blocking validation, finance OR admin approves Closed-Won handoff, BRD default field set per stage.

## User Personas
Admin · Finance · Sales/Delivery · Leadership (CFO/CEO/COO) · Approver

## Implementation Status

### Phase 1 — Jan 2026 ✅
JWT auth, brute-force lockout, admin user mgmt, 6 master data CRUD + audit trail, Project CRUD with auto margin, 5-stage workflow engine, Approval Matrix engine, Excel upload, Dashboard, Audit trail.

### Phase 2 — Jan 2026 ✅
Pencil edit on Projects list, Finance Query discussion engine, Customer Profile aggregator, Project Document attachments with PDF auto-parse.

### Phase 3 Iteration 3 — Feb 2026 ✅
PDF auto-parse in New/Edit Project modal (Customer vs Vendor PO), Royal Purple theme, Microsoft Graph email placeholders.

### Phase 3 Iteration 4 — Feb 2026 ✅
Unified SAP Excel uploader (4-sheet workbook), Excel autofill, Project Detail crash fix, admin Delete Project, Customer delete guard, clickable Revenue/Cost tiles.

### Phase 3 Iteration 5 — Feb 2026 ✅
Undo last SAP import, Aviation visual identity (airplane CTA + tricolor stripe + watermark).

### Phase 4 Iteration 6 — Feb 2026 ✅ — Pipeline + Navigation BRD
- **Pipeline module (5-stage opportunity funnel)** — `Pipeline` model + `/api/pipeline` CRUD + `/api/pipeline/summary` + `/api/pipeline/{id}/advance` + `/api/pipeline/{id}/close?outcome=Won|Lost` + `/api/pipeline/{id}/approve-handoff`. Stages: Prospecting → Active Discussion → Proposal Submitted → Evaluation/Negotiation → Closed.
- **Finance Approval Gate** — Closed-Won sets `handoff_status='Pending Finance'`. Finance OR Admin can approve → auto-creates a Project stub (po_value mirrors negotiated_value|proposal_value|expected_revenue, margin mirrors estimated_margin_pct, customer/business_category copied). Reject sets `handoff_status='Rejected'` and does NOT create a Project. Non-finance/admin callers get 403.
- **Tabbed stage-wise wizard** (`PipelineWizardModal`) with progressive disclosure. `*` markers visible on mandatory fields but no validation blocks save.
- **Collapsible sidebar** (`AppLayout.jsx`) — icons-only mode with hover tooltips; state persisted to `localStorage.cp_sidebar_collapsed`.
- **Navigation rename + add** — Customers → Customer Profile, new entries for Pipeline + Change Requests.
- **Dashboard updates** — "Recognized Revenue" → "Revenue"; Top 10 Suppliers (cost spend, up from 5); colored management flag badges (GMR/Non-GMR/Delayed/Low Margin/High/Medium/Low) on Delayed + Low Margin tables.
- **Document upload requires mandatory `name`** — `POST /api/projects/{pid}/documents?name=<required>`; UI disables Save button until both name + file present; 422 when name missing.
- **Enriched Customer Profile** — added `industry`, `sector`, `address_billing`, `address_shipping`, `secondary_contact_person`, `secondary_email`, `secondary_phone`, `website`, `account_owner_email` fields. Shown on Customer Profile page + editable via Masters/Customers modal.
- **Project Form `*` markers** — Project Name, WBS, Customer, Customer PO, PO/Start/End Date, Billing Type, PO/Revenue/Cost Value, Business Category, P&L Location/Region, Location, Ownership Email.
- Seeded 4 sample pipeline opportunities covering all stages.
- 16/16 pytest pipeline tests passing (`test_pipeline_iter6.py`). Full frontend e2e verified.

## Backlog / Future Phases

### P1 (next)
- Pipeline Kanban board view (drag-drop between stages)
- Convert `PUT /api/pipeline/{id}` to partial update (exclude_unset=True) — minor UX hardening
- Email notifications on Pipeline stage changes / handoff requests (Microsoft Graph already wired)
- Customer Profile: PO history & contracts upload
- Split Projects into "Active Projects" vs "Change Requests" at model-level (currently heuristic filter)
- Bulk approve/reject in approvals queue

### P2
- Dashboard advanced cascading filters + date range
- AI Margin Risk Radar (Emergent LLM key) — narrative briefing
- Forecasting (revenue/cost)
- Refactor `server.py` (~1800 lines) into `/app/backend/routes/` modules

### P3
- SAP API integration (live sync)
- Mobile-responsive layout
- Document storage on S3 / GridFS

## Test Credentials
See `/app/memory/test_credentials.md` — admin@crackerpro.com / Admin@123 (idempotent seed).

## Key Files
- Backend: `/app/backend/{server,auth,models,services,excel_utils,pdf_parser,sap_parser,notifications}.py`
- Frontend: `/app/frontend/src/{App.js, lib/, components/, pages/}` — incl. `PipelineWizardModal.jsx`, `PipelinePage.jsx`, `ChangeRequestsPage.jsx`
- Design: `/app/design_guidelines.json`
- Tests: `/app/backend/tests/test_pipeline_iter6.py` (+ earlier iter test suites)
