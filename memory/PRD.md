# CRacker Pro – Product Requirements Document (PRD)

## Original Problem Statement
Build an enterprise-grade Business Finance webportal ("CRacker Pro") for managing the project commercial lifecycle (Pipeline → Deal P&L → Customer PO → Operations → Closure). Replace fragile Excel-based tracking with audit-tracked workflows, configurable approvals, master data management, and a real-time finance dashboard. Source: User-provided BRD (Webpage BRD - Development Plan.docx) + sample Revenue & Expenses master.

## User Choices (locked-in)
- **Stack**: React + FastAPI + MongoDB
- **MVP scope**: Auth + Admin Panel + Masters + Excel Upload + Dashboard + Audit + Workflow Engine + Approval Matrix
- **Auth**: JWT with admin-managed users (no OTP)
- **Theme**: Design agent picked premium Swiss High-Contrast + Warm Beige hybrid (Charcoal sidebar, Alabaster bg, Matte Gold accents, Cabinet Grotesk + Work Sans + JetBrains Mono fonts)
- **Email integration**: Skipped in MVP (in-app only)

## User Personas
- **Admin** – manages users, masters, approval matrix
- **Finance** – raises queries, reviews margins, recognizes revenue
- **Sales / Delivery** – owns project execution, replies to queries
- **Leadership (CFO/CEO/COO)** – drill-down dashboards, approvals
- **Approver** – stage-gate reviewer per matrix rules

## Core Requirements
1. End-to-end project lifecycle (5 stages, forward + backward transitions, approval gating)
2. Master data: Project, Customer, Employee, Supplier, Revenue Line, Cost Line
3. Excel Upload Engine with template download, validation, failed rows report, upload logs
4. Configurable Approval Matrix (margin / revenue / business category / target stage)
5. Interactive dashboard: KPI tiles (clickable), funnel chart, billing trend, top customers, vendor exposure, delayed/low-margin lists
6. Currency toggle ₹ Lakh/Crore ↔ $ Million
7. Permanent audit trail of every change with old/new diff
8. Premium enterprise UI: dark sidebar, alabaster light content, gold accents, JetBrains Mono for tabular data, sharp `rounded-sm` corners

## Implementation Status (Phase 1 – completed Jan 2026)
- ✅ JWT auth, bcrypt, brute-force lockout (email-only), admin seeding
- ✅ Admin user management + admin-driven password reset
- ✅ All 6 master data CRUD endpoints with audit trail
- ✅ Project CRUD with auto margin computation (margin_total + margin_pct)
- ✅ Workflow engine (5 stages) with `can_transition` rules; forward + backward (rework)
- ✅ Approval Matrix engine: business category + revenue range + margin range + target stage triggers
- ✅ Approval queue with role-based and email-list approvers
- ✅ Excel Upload Engine: template/export/upload for project/customer/employee/supplier/revenue/cost (string coercion fixes int corruption)
- ✅ Dashboard summary endpoint: stage_summary, totals, recognized vs unbilled, top customers, vendor exposure, monthly billing, delayed projects, low-margin projects, approvals_pending
- ✅ Audit trail viewer with entity_type filter
- ✅ Frontend: Login (split-screen), Dashboard, Projects (list + detail w/ 5 tabs + stage tracker), Customers/Suppliers/Employees masters, Excel Upload, Approvals queue, Audit Trail, Admin Users, Approval Matrix
- ✅ Currency toggle (₹ Cr / $ M), KPI tiles clickable for drill-down, recharts visualizations, sidebar role-based menu
- ✅ Seeded sample data: 6 projects, 4 customers, 2 employees, 3 suppliers, 2 approval rules, revenue & cost lines
- ✅ Test suite (24/25 pytest passing, all frontend flows verified by testing agent)

## Backlog / Future Phases
### P1 (next session)
- Finance Query Discussion Engine (threaded queries, attachments)
- Customer Profile module (linked projects, ageing, risk notes, PO history)
- Notifications panel (in-app event feed)
- Project list export to Excel

### P2
- Email integration (SendGrid/Resend) for approval / query / delay alerts
- PDF Parsing Engine for Customer POs (FastAPI service)
- Vendor PO management (full CRUD)
- Stage progress tracker by milestones (revenue vs milestone toggle)
- Forecasting (revenue/cost ARIMA or LLM-based)
- Advanced search, saved filters, leadership-only dashboard view

### P3
- SAP API integration for SAP customer code, balance outstanding sync
- Mobile-responsive layout
- Bulk approve/reject in approval queue
- Configurable role-based field-level visibility

## Test Credentials
See `/app/memory/test_credentials.md`.

## Key Files
- Backend: `/app/backend/{server,auth,models,services,excel_utils}.py`
- Frontend: `/app/frontend/src/{App.js, lib/, components/, pages/}`
- Design: `/app/design_guidelines.json`
- Tests: `/app/backend/tests/test_crackerpro.py`
