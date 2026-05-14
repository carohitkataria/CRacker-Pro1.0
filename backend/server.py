"""CRacker Pro - Business Finance webportal backend."""
from dotenv import load_dotenv
from pathlib import Path
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

import os
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any

from fastapi import FastAPI, APIRouter, HTTPException, Depends, Request, Response, UploadFile, File, Query
from fastapi.responses import StreamingResponse
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import io

from auth import (
    hash_password, verify_password, create_access_token, create_refresh_token,
    set_auth_cookies, clear_auth_cookies, decode_token, make_get_current_user,
)
from models import (
    UserCreate, UserUpdate, UserOut, LoginInput, PasswordChange,
    CustomerIn, CustomerOut, EmployeeIn, EmployeeOut, SupplierIn, SupplierOut,
    ProjectIn, ProjectOut, StageTransitionIn,
    RevenueLineIn, RevenueLineOut, CostLineIn, CostLineOut,
    ApprovalRuleIn, ApprovalRuleOut, ApprovalActionIn, ApprovalRequestOut,
    AuditLogOut, UploadLogOut, gen_id, now_iso, STAGES,
    PipelineIn, PipelineOut, PipelineStageIn, PipelineHandoffAction, PIPELINE_STAGES,
    RoleIn, RoleOut, WORKSPACE_SECTIONS,
)
from services import (
    can_transition, write_audit, compute_margin, find_matching_rule, create_approval_request,
)
from excel_utils import (
    build_template_xlsx, parse_xlsx, build_export_xlsx, SCHEMAS,
)
import sap_parser
from notifications import mailer, tpl_approval_request, tpl_test_email

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("crackerpro")

# ---------- DB ----------
mongo_url = os.environ["MONGO_URL"]
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ["DB_NAME"]]

app = FastAPI(title="CRacker Pro API")
api = APIRouter(prefix="/api")

get_current_user = make_get_current_user(db)


def require_role(*roles):
    async def _dep(user: dict = Depends(get_current_user)):
        if user.get("role") not in roles:
            raise HTTPException(status_code=403, detail=f"Forbidden, role required: {roles}")
        return user
    return _dep


# ---------- STARTUP ----------
@app.on_event("startup")
async def on_startup():
    # Indexes
    await db.users.create_index("email", unique=True)
    await db.users.create_index("id", unique=True)
    await db.projects.create_index("id", unique=True)
    await db.projects.create_index("wbs_element")
    await db.customers.create_index("id", unique=True)
    await db.employees.create_index("id", unique=True)
    await db.employees.create_index("email_id", unique=True)
    await db.suppliers.create_index("id", unique=True)
    await db.revenue_lines.create_index("id", unique=True)
    await db.cost_lines.create_index("id", unique=True)
    await db.approval_rules.create_index("id", unique=True)
    await db.approval_requests.create_index("id", unique=True)
    await db.audit_logs.create_index("timestamp")
    await db.upload_logs.create_index("uploaded_at")
    await db.login_attempts.create_index("identifier")
    await db.pipelines.create_index("id", unique=True)
    await db.roles.create_index("id", unique=True)
    await db.roles.create_index("name", unique=True)
    await db.employees.create_index("employee_no", unique=False)

    # Migration: drop legacy employee rows that don't have employee_no (old schema)
    legacy = await db.employees.count_documents({"employee_no": {"$exists": False}})
    if legacy > 0:
        await db.employees.delete_many({"employee_no": {"$exists": False}})
        logger.info("Migrated out %d legacy employee rows", legacy)

    # Admin seed
    admin_email = os.environ.get("ADMIN_EMAIL", "admin@crackerpro.com")
    admin_password = os.environ.get("ADMIN_PASSWORD", "Admin@123")
    existing = await db.users.find_one({"email": admin_email})
    if not existing:
        await db.users.insert_one({
            "id": gen_id(), "email": admin_email,
            "password_hash": hash_password(admin_password),
            "name": "System Administrator", "role": "admin",
            "location": "HQ", "reporting_manager_email": None,
            "is_active": True, "created_at": now_iso(),
        })
        logger.info("Seeded admin user %s", admin_email)
    elif not verify_password(admin_password, existing.get("password_hash", "")):
        await db.users.update_one(
            {"email": admin_email},
            {"$set": {"password_hash": hash_password(admin_password)}},
        )

    # Seed default approval rule(s) and sample data once
    if await db.approval_rules.count_documents({}) == 0:
        await db.approval_rules.insert_many([
            {"id": gen_id(), "name": "High Value Deal P&L", "business_category": "Any",
             "min_revenue": 50000000, "max_revenue": None, "min_margin_pct": None, "max_margin_pct": None,
             "target_stage": "Deal P&L", "approver_emails": [admin_email], "approver_role": "leadership",
             "is_active": True, "created_at": now_iso()},
            {"id": gen_id(), "name": "Low Margin Alert (Margin < 15%)", "business_category": "Any",
             "min_revenue": None, "max_revenue": None, "min_margin_pct": None, "max_margin_pct": 15.0,
             "target_stage": "Customer PO", "approver_emails": [admin_email], "approver_role": "finance",
             "is_active": True, "created_at": now_iso()},
        ])

    if await db.customers.count_documents({}) == 0:
        sample_customers = [
            {"id": gen_id(), "customer_name": "DIAL - Delhi International Airport", "sap_customer_code": "C001",
             "balance_outstanding_sap": 12500000, "risk_notes": "Strategic customer", "contact_person": "R. Sharma",
             "email": "rsharma@dial.in", "phone": "+91-11-2345-6789", "country": "India", "created_at": now_iso()},
            {"id": gen_id(), "customer_name": "GHIAL - Hyderabad Airport", "sap_customer_code": "C002",
             "balance_outstanding_sap": 8400000, "risk_notes": "", "contact_person": "P. Reddy",
             "email": "preddy@ghial.com", "phone": "+91-40-2345-1111", "country": "India", "created_at": now_iso()},
            {"id": gen_id(), "customer_name": "BIAL - Bengaluru Airport", "sap_customer_code": "C003",
             "balance_outstanding_sap": 5200000, "risk_notes": "", "contact_person": "K. Iyer",
             "email": "kiyer@bial.aero", "phone": "+91-80-6678-2222", "country": "India", "created_at": now_iso()},
            {"id": gen_id(), "customer_name": "Calicut International", "sap_customer_code": "C004",
             "balance_outstanding_sap": 1800000, "risk_notes": "Watch ageing", "contact_person": "M. Nair",
             "email": "mnair@ccj.in", "phone": "+91-495-271-5555", "country": "India", "created_at": now_iso()},
        ]
        await db.customers.insert_many(sample_customers)

    if await db.suppliers.count_documents({}) == 0:
        await db.suppliers.insert_many([
            {"id": gen_id(), "supplier_code": "S001", "supplier_name": "NPT Servers Pvt Ltd",
             "contact_person": "S. Kumar", "email": "sk@npt.com", "phone": "+91-22-1234-1111",
             "address": "Mumbai", "created_at": now_iso()},
            {"id": gen_id(), "supplier_code": "S002", "supplier_name": "AGISS Services",
             "contact_person": "A. Gupta", "email": "ag@agiss.com", "phone": "+91-11-9876-2222",
             "address": "New Delhi", "created_at": now_iso()},
            {"id": gen_id(), "supplier_code": "S003", "supplier_name": "SmartBuggy Tech",
             "contact_person": "V. Rao", "email": "vrao@smartbuggy.in", "phone": "+91-40-5544-3333",
             "address": "Hyderabad", "created_at": now_iso()},
        ])

    if await db.employees.count_documents({}) == 0:
        await db.employees.insert_many([
            {"id": gen_id(), "employee_no": "W0626", "email_id": "KSreedhar.Rao@waisldigital.com",
             "status": "Active", "joining_date": "02-02-2024", "exit_date": None,
             "employment_type": "Employee", "employee_name": "K Sreedhar Rao",
             "role_zoho": "COO", "l1_manager": "W0989", "location": "New Delhi",
             "department": "Corporate", "sub_department": "L1 Management", "created_at": now_iso()},
            {"id": gen_id(), "employee_no": "W0683", "email_id": "Rishabh.Gupta@waisldigital.com",
             "status": "Active", "joining_date": "22-04-2024", "exit_date": None,
             "employment_type": "Employee", "employee_name": "Rishabh Gupta",
             "role_zoho": "Manager Corporate Finance", "l1_manager": "W1018", "location": "New Delhi",
             "department": "Finance", "sub_department": "Business Finance", "created_at": now_iso()},
            {"id": gen_id(), "employee_no": "W0839", "email_id": "Gurpreet.Singh@waisldigital.com",
             "status": "Active", "joining_date": "07-01-2025", "exit_date": None,
             "employment_type": "Employee", "employee_name": "Gurpreet Singh",
             "role_zoho": "CFO", "l1_manager": "W0989", "location": "New Delhi",
             "department": "Corporate", "sub_department": "L1 Management", "created_at": now_iso()},
            {"id": gen_id(), "employee_no": "W1067", "email_id": "Rohit.Kataria@waisldigital.com",
             "status": "Active", "joining_date": "01-12-2025", "exit_date": None,
             "employment_type": "Employee", "employee_name": "Rohit Kataria",
             "role_zoho": "Manager Business Finance", "l1_manager": "W1018", "location": "New Delhi",
             "department": "Finance", "sub_department": "Business Finance", "created_at": now_iso()},
            {"id": gen_id(), "employee_no": "W0989", "email_id": "Ankit.Arora@waisldigital.com",
             "status": "Active", "joining_date": "18-08-2025", "exit_date": None,
             "employment_type": "Employee", "employee_name": "Ankit Arora",
             "role_zoho": "CEO", "l1_manager": "W0989", "location": "Dubai",
             "department": "Corporate", "sub_department": "L1 Management", "created_at": now_iso()},
            {"id": gen_id(), "employee_no": "W1018", "email_id": "Tushar.Sukhija@waisldigital.com",
             "status": "Active", "joining_date": "30-09-2025", "exit_date": None,
             "employment_type": "Employee", "employee_name": "Tushar Sukhija",
             "role_zoho": "Head Business Finance", "l1_manager": "W0839", "location": "New Delhi",
             "department": "Finance", "sub_department": "Business Finance", "created_at": now_iso()},
        ])

    # Permanent admin users (cannot be replaced via Excel, cannot be deleted)
    permanent_admins = [
        {"email": "rohit.kataria@waisldigital.com", "name": "Rohit Kataria", "password": "RKataria@121"},
        {"email": "tushar.sukhija@waisldigital.com", "name": "Tushar Sukhija", "password": "TSukhija@121"},
    ]
    for pa in permanent_admins:
        ex = await db.users.find_one({"email": pa["email"]})
        if not ex:
            await db.users.insert_one({
                "id": gen_id(), "email": pa["email"],
                "password_hash": hash_password(pa["password"]),
                "name": pa["name"], "role": "admin",
                "location": "New Delhi", "reporting_manager_email": None,
                "is_active": True, "is_permanent_admin": True,
                "role_id": None, "created_at": now_iso(),
            })
            logger.info("Seeded permanent admin %s", pa["email"])
        else:
            # Ensure they remain permanent admin + correct password
            await db.users.update_one(
                {"email": pa["email"]},
                {"$set": {
                    "role": "admin", "is_permanent_admin": True, "is_active": True,
                    "password_hash": hash_password(pa["password"]),
                }}
            )

    if await db.projects.count_documents({}) == 0:
        cust_list = await db.customers.find({}, {"_id": 0}).to_list(10)
        sample_projects = []
        templates = [
            ("Smart Airside Gate Solution", "WSIN.000136.0001", 65000000, 48000000, 38000000, "Operations", "Pipeline"),
            ("NPT Server Refresh", "WOIN.018.01.0001.0001", 18000000, 18000000, 14500000, "Customer PO", "Pipeline"),
            ("Smart Buggy Management Software", "WSIN.000152.0002", 24000000, 21000000, 18900000, "Deal P&L", "Pipeline"),
            ("Calicut Kiosk Rollout", "WOIN.032.01.0001", 8500000, 8200000, 6100000, "Operations", "Pipeline"),
            ("DIAL O&M Support FY26", "WOIN.040.02.0010", 120000000, 98000000, 75000000, "Pipeline", "Pipeline"),
            ("AGISS Subscription Renewal", "WOIN.018.05.0001", 5500000, 5500000, 3200000, "Closure", "Pipeline"),
        ]
        for i, (name, wbs, po, rev, cost, stage, _) in enumerate(templates):
            cust = cust_list[i % len(cust_list)]
            margin = compute_margin(po, rev, cost)
            sample_projects.append({
                "id": gen_id(), "project_name": name, "wbs_element": wbs,
                "customer_po_number": f"PO-2026-{1000+i}",
                "po_date": (datetime.now(timezone.utc) - timedelta(days=60+i*10)).date().isoformat(),
                "start_date": (datetime.now(timezone.utc) - timedelta(days=30+i*5)).date().isoformat(),
                "end_date": (datetime.now(timezone.utc) + timedelta(days=180+i*15)).date().isoformat(),
                "billing_type": "Milestone" if i % 2 == 0 else "Monthly",
                "milestones": [
                    {"milestone_name": "Kickoff", "due_date": (datetime.now(timezone.utc) - timedelta(days=30)).date().isoformat(), "value": po*0.2, "is_billed": True},
                    {"milestone_name": "Phase 1", "due_date": (datetime.now(timezone.utc) + timedelta(days=30)).date().isoformat(), "value": po*0.4, "is_billed": False},
                    {"milestone_name": "Final", "due_date": (datetime.now(timezone.utc) + timedelta(days=120)).date().isoformat(), "value": po*0.4, "is_billed": False},
                ] if i % 2 == 0 else [],
                "customer_id": cust["id"], "customer_name": cust["customer_name"],
                "description": f"Sample project {name}",
                "currency": "INR", "po_value": po, "revenue_total": rev, "cost_total": cost,
                "vendor_pos": [], "country": "India",
                "pnl_location": cust.get("customer_name", "").split(" ")[0],
                "pnl_region": "North" if i % 2 == 0 else "South",
                "airport_adjacency": "Airport", "project_grouping": "GMR" if i % 2 == 0 else "Non-GMR",
                "location": "Delhi", "category1": "IT Services",
                "category2": "Digital" if i % 2 == 0 else "Non-Digital",
                "business_category": "GMR" if i % 2 == 0 else "Non-GMR",
                "retro_pnl_tagging": "", "ownership_email": "carohitkataria@gmail.com",
                "stakeholders": ["priya.mehta@crackerpro.com"],
                "baseline_remarks": "", "finance_remarks": "",
                "current_stage": stage, "approval_status": "Not Required",
                "margin_total": margin["margin_total"], "margin_pct": margin["margin_pct"],
                "created_at": now_iso(), "updated_at": now_iso(),
                "created_by": admin_email,
            })
        await db.projects.insert_many(sample_projects)

        # seed revenue/cost lines for first project
        first = sample_projects[0]
        await db.revenue_lines.insert_many([
            {"id": gen_id(), "project_id": first["id"], "revenue_code": "R-001",
             "description": "Recognized Q1", "amount": first["po_value"]*0.3,
             "recognition_date": (datetime.now(timezone.utc) - timedelta(days=45)).date().isoformat(),
             "billing_date": (datetime.now(timezone.utc) - timedelta(days=30)).date().isoformat(),
             "is_billed": True, "created_at": now_iso()},
            {"id": gen_id(), "project_id": first["id"], "revenue_code": "R-002",
             "description": "Recognized Q2 unbilled", "amount": first["po_value"]*0.2,
             "recognition_date": (datetime.now(timezone.utc) - timedelta(days=15)).date().isoformat(),
             "billing_date": None, "is_billed": False, "created_at": now_iso()},
        ])
        await db.cost_lines.insert_many([
            {"id": gen_id(), "project_id": first["id"], "vendor_po_ref": "VPO-1",
             "supplier_id": None, "supplier_name": "NPT Servers Pvt Ltd",
             "description": "Hardware procurement", "amount": first["cost_total"]*0.6,
             "expense_date": (datetime.now(timezone.utc) - timedelta(days=40)).date().isoformat(),
             "category": "Hardware", "created_at": now_iso()},
            {"id": gen_id(), "project_id": first["id"], "vendor_po_ref": "VPO-2",
             "supplier_id": None, "supplier_name": "AGISS Services",
             "description": "Manpower subcontracting", "amount": first["cost_total"]*0.4,
             "expense_date": (datetime.now(timezone.utc) - timedelta(days=20)).date().isoformat(),
             "category": "Subcontracting", "created_at": now_iso()},
        ])

    # Seed pipeline (opportunity funnel) sample
    if await db.pipelines.count_documents({}) == 0:
        cust_list = await db.customers.find({}, {"_id": 0}).to_list(10)
        pipe_seeds = [
            {"opportunity_title": "BIAL Smart Gate Expansion Phase 2",
             "current_stage": "Active Discussion", "expected_revenue": 85000000,
             "bd_owner": "priya.mehta@crackerpro.com", "business_category": "GMR",
             "priority": "High", "solution_scope": "Extend airside gate solution to 12 additional gates",
             "expected_timeline": "Q3 FY27", "industry": "Aviation", "source": "Repeat"},
            {"opportunity_title": "Hyderabad Airport Retail Kiosk Rollout",
             "current_stage": "Proposal Submitted", "expected_revenue": 22000000,
             "proposal_value": 21500000, "proposal_submitted_on": (datetime.now(timezone.utc) - timedelta(days=14)).date().isoformat(),
             "bd_owner": "carohitkataria@gmail.com", "business_category": "Non-GMR",
             "priority": "Medium", "industry": "Retail / F&B", "source": "RFP"},
            {"opportunity_title": "Calicut Ops Support Renewal",
             "current_stage": "Evaluation/Negotiation", "expected_revenue": 15000000,
             "negotiated_value": 14200000, "estimated_margin_pct": 18.5,
             "bd_owner": "priya.mehta@crackerpro.com", "business_category": "GMR",
             "priority": "High", "industry": "Aviation Services", "source": "Repeat"},
            {"opportunity_title": "Greenfield Cargo Terminal IT Stack",
             "current_stage": "Prospecting", "expected_revenue": 180000000,
             "bd_owner": "priya.mehta@crackerpro.com", "business_category": "Non-GMR",
             "priority": "High", "industry": "Cargo", "source": "Cold"},
        ]
        now = now_iso()
        docs = []
        for i, s in enumerate(pipe_seeds):
            cust = cust_list[i % len(cust_list)] if cust_list else {}
            docs.append({
                "id": gen_id(),
                "opportunity_title": s["opportunity_title"],
                "customer_name": cust.get("customer_name"),
                "customer_id": cust.get("id"),
                "bd_owner": s.get("bd_owner"),
                "expected_revenue": s.get("expected_revenue", 0),
                "currency": "INR",
                "source": s.get("source"),
                "industry": s.get("industry"),
                "solution_scope": s.get("solution_scope", ""),
                "expected_timeline": s.get("expected_timeline", ""),
                "competitors": "",
                "stakeholders": [],
                "proposal_value": s.get("proposal_value", 0),
                "proposal_submitted_on": s.get("proposal_submitted_on"),
                "proposal_validity": None, "proposal_notes": "",
                "negotiated_value": s.get("negotiated_value", 0),
                "estimated_margin_pct": s.get("estimated_margin_pct", 0),
                "expected_decision_date": None, "negotiation_notes": "",
                "outcome": "Open", "closure_date": None, "win_loss_reason": "",
                "business_category": s.get("business_category"),
                "priority": s.get("priority"),
                "remarks": "",
                "current_stage": s["current_stage"],
                "handoff_status": "Not Applicable",
                "handoff_project_id": None,
                "handoff_requested_by": None, "handoff_requested_at": None,
                "handoff_actioned_by": None, "handoff_actioned_at": None,
                "handoff_comment": "",
                "created_at": now, "updated_at": now, "created_by": admin_email,
            })
        await db.pipelines.insert_many(docs)

    # Backfill opportunity_id for older pipeline rows + remove empty / orphan entries
    async for row in db.pipelines.find({"$or": [
        {"opportunity_id": {"$exists": False}},
        {"opportunity_id": None},
        {"opportunity_title": {"$in": ["", None]}},
    ]}):
        if not (row.get("opportunity_title") or "").strip():
            await db.pipelines.delete_one({"id": row["id"]})
            continue
        if not row.get("opportunity_id"):
            seq = await db.pipelines.count_documents({"opportunity_id": {"$exists": True, "$ne": None}}) + 1
            year = datetime.now(timezone.utc).year
            opp_id = f"OPP-{year}-{seq:06d}"
            await db.pipelines.update_one({"id": row["id"]}, {"$set": {"opportunity_id": opp_id}})


@app.on_event("shutdown")
async def on_shutdown():
    client.close()


# ============================================================
# AUTH
# ============================================================
@api.post("/auth/login")
async def login(payload: LoginInput, request: Request, response: Response):
    email = payload.email.lower().strip()
    identifier = email  # email-only lockout key (k8s ingress rotates client IP)
    # brute force check
    rec = await db.login_attempts.find_one({"identifier": identifier})
    if rec and rec.get("locked_until") and rec["locked_until"] > now_iso():
        raise HTTPException(status_code=429, detail="Too many failed attempts. Try again in 15 minutes.")

    user = await db.users.find_one({"email": email})
    if not user or not user.get("is_active", True) or not verify_password(payload.password, user.get("password_hash", "")):
        # increment attempts
        attempts = (rec.get("attempts", 0) if rec else 0) + 1
        update = {"identifier": identifier, "attempts": attempts, "last_attempt": now_iso()}
        if attempts >= 5:
            update["locked_until"] = (datetime.now(timezone.utc) + timedelta(minutes=15)).isoformat()
            update["attempts"] = 0
        await db.login_attempts.update_one({"identifier": identifier}, {"$set": update}, upsert=True)
        raise HTTPException(status_code=401, detail="Invalid email or password")

    await db.login_attempts.delete_one({"identifier": identifier})
    access = create_access_token(user["id"], user["email"], user["role"])
    refresh = create_refresh_token(user["id"])
    set_auth_cookies(response, access, refresh)
    user.pop("password_hash", None)
    user.pop("_id", None)
    return {"user": user, "access_token": access}


@api.post("/auth/logout")
async def logout(response: Response, _: dict = Depends(get_current_user)):
    clear_auth_cookies(response)
    return {"ok": True}


@api.get("/auth/me", response_model=UserOut)
async def me(user: dict = Depends(get_current_user)):
    return user


@api.post("/auth/refresh")
async def refresh_token(request: Request, response: Response):
    token = request.cookies.get("refresh_token")
    if not token:
        raise HTTPException(status_code=401, detail="No refresh token")
    payload = decode_token(token)
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid token type")
    user = await db.users.find_one({"id": payload["sub"]}, {"_id": 0, "password_hash": 0})
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    access = create_access_token(user["id"], user["email"], user["role"])
    new_refresh = create_refresh_token(user["id"])
    set_auth_cookies(response, access, new_refresh)
    return {"ok": True}


# ============================================================
# ADMIN - USERS
# ============================================================
@api.get("/admin/users", response_model=List[UserOut])
async def list_users(_: dict = Depends(require_role("admin"))):
    rows = await db.users.find({}, {"_id": 0, "password_hash": 0}).to_list(1000)
    return rows


@api.post("/admin/users", response_model=UserOut)
async def create_user(payload: UserCreate, admin: dict = Depends(require_role("admin"))):
    email = payload.email.lower().strip()
    if await db.users.find_one({"email": email}):
        raise HTTPException(status_code=409, detail="Email already exists")
    doc = {
        "id": gen_id(), "email": email, "password_hash": hash_password(payload.password),
        "name": payload.name, "role": payload.role, "location": payload.location,
        "reporting_manager_email": payload.reporting_manager_email,
        "role_id": payload.role_id, "is_permanent_admin": False,
        "is_active": True, "created_at": now_iso(),
    }
    await db.users.insert_one(doc)
    await write_audit(db, entity_type="user", entity_id=doc["id"], action="create", user=admin,
                      field_changes={"email": email, "role": payload.role})
    doc.pop("password_hash", None)
    doc.pop("_id", None)
    return doc


@api.put("/admin/users/{user_id}", response_model=UserOut)
async def update_user(user_id: str, payload: UserUpdate, admin: dict = Depends(require_role("admin"))):
    existing = await db.users.find_one({"id": user_id})
    if not existing:
        raise HTTPException(404, "User not found")
    updates = {k: v for k, v in payload.model_dump(exclude_none=True).items()}
    # Permanent admins cannot be demoted or deactivated
    if existing.get("is_permanent_admin"):
        if "role" in updates and updates["role"] != "admin":
            raise HTTPException(400, "Permanent admin role cannot be changed")
        if "is_active" in updates and not updates["is_active"]:
            raise HTTPException(400, "Permanent admin cannot be deactivated")
    if updates:
        await db.users.update_one({"id": user_id}, {"$set": updates})
        await write_audit(db, entity_type="user", entity_id=user_id, action="update", user=admin,
                          field_changes=updates)
    doc = await db.users.find_one({"id": user_id}, {"_id": 0, "password_hash": 0})
    return doc


@api.post("/admin/users/reset-password")
async def admin_reset_password(payload: PasswordChange, admin: dict = Depends(require_role("admin"))):
    existing = await db.users.find_one({"id": payload.user_id})
    if not existing:
        raise HTTPException(404, "User not found")
    if existing.get("is_permanent_admin"):
        raise HTTPException(400, "Permanent admin password is managed via environment seed only")
    await db.users.update_one(
        {"id": payload.user_id},
        {"$set": {"password_hash": hash_password(payload.new_password)}},
    )
    await write_audit(db, entity_type="user", entity_id=payload.user_id, action="password_reset", user=admin)
    return {"ok": True}


@api.delete("/admin/users/{user_id}")
async def deactivate_user(user_id: str, admin: dict = Depends(require_role("admin"))):
    if user_id == admin["id"]:
        raise HTTPException(400, "Cannot deactivate yourself")
    existing = await db.users.find_one({"id": user_id})
    if existing and existing.get("is_permanent_admin"):
        raise HTTPException(400, "Permanent admin cannot be deactivated")
    await db.users.update_one({"id": user_id}, {"$set": {"is_active": False}})
    await write_audit(db, entity_type="user", entity_id=user_id, action="deactivate", user=admin)
    return {"ok": True}


# ============================================================
# ROLES (workspace section permissions)
# ============================================================
@api.get("/roles", response_model=List[RoleOut])
async def list_roles(_: dict = Depends(get_current_user)):
    return await db.roles.find({}, {"_id": 0}).sort("created_at", 1).to_list(200)


@api.post("/roles", response_model=RoleOut)
async def create_role(payload: RoleIn, admin: dict = Depends(require_role("admin"))):
    if await db.roles.find_one({"name": payload.name}):
        raise HTTPException(409, "Role name already exists")
    doc = payload.model_dump()
    doc["id"] = gen_id()
    doc["is_system"] = False
    doc["created_at"] = now_iso()
    doc["updated_at"] = now_iso()
    # Coerce permissions to dict-of-dicts (Pydantic SectionPermission -> dict)
    perms: Dict[str, Any] = {}
    for k, v in (payload.permissions or {}).items():
        if k in WORKSPACE_SECTIONS:
            perms[k] = {"can_view": bool(v.can_view), "can_edit": bool(v.can_edit)}
    doc["permissions"] = perms
    await db.roles.insert_one(doc)
    await write_audit(db, entity_type="role", entity_id=doc["id"], action="create", user=admin,
                      field_changes={"name": payload.name})
    doc.pop("_id", None)
    return doc


@api.put("/roles/{rid}", response_model=RoleOut)
async def update_role(rid: str, payload: RoleIn, admin: dict = Depends(require_role("admin"))):
    existing = await db.roles.find_one({"id": rid})
    if not existing:
        raise HTTPException(404, "Role not found")
    if existing.get("is_system"):
        raise HTTPException(400, "System role cannot be edited")
    updates = payload.model_dump()
    perms: Dict[str, Any] = {}
    for k, v in (payload.permissions or {}).items():
        if k in WORKSPACE_SECTIONS:
            perms[k] = {"can_view": bool(v.can_view), "can_edit": bool(v.can_edit)}
    updates["permissions"] = perms
    updates["updated_at"] = now_iso()
    await db.roles.update_one({"id": rid}, {"$set": updates})
    await write_audit(db, entity_type="role", entity_id=rid, action="update", user=admin)
    return await db.roles.find_one({"id": rid}, {"_id": 0})


@api.delete("/roles/{rid}")
async def delete_role(rid: str, admin: dict = Depends(require_role("admin"))):
    existing = await db.roles.find_one({"id": rid})
    if not existing:
        raise HTTPException(404, "Role not found")
    if existing.get("is_system"):
        raise HTTPException(400, "System role cannot be deleted")
    in_use = await db.users.count_documents({"role_id": rid})
    if in_use:
        raise HTTPException(400, f"Role is assigned to {in_use} user(s) — reassign first")
    await db.roles.delete_one({"id": rid})
    await write_audit(db, entity_type="role", entity_id=rid, action="delete", user=admin)
    return {"ok": True}


@api.get("/me/permissions")
async def my_permissions(user: dict = Depends(get_current_user)):
    """Returns the workspace permissions for the current user."""
    # Admin role bypasses all checks
    is_admin = user.get("role") == "admin"
    all_perms = {s: {"can_view": True, "can_edit": True, "can_delete": is_admin} for s in WORKSPACE_SECTIONS}
    if is_admin:
        return {"is_admin": True, "is_permanent_admin": bool(user.get("is_permanent_admin")), "permissions": all_perms}

    perms = {s: {"can_view": False, "can_edit": False, "can_delete": False} for s in WORKSPACE_SECTIONS}
    role_id = user.get("role_id")
    if role_id:
        role = await db.roles.find_one({"id": role_id}, {"_id": 0})
        if role:
            for s, p in (role.get("permissions") or {}).items():
                if s in WORKSPACE_SECTIONS:
                    perms[s] = {
                        "can_view": bool(p.get("can_view")),
                        "can_edit": bool(p.get("can_edit")),
                        "can_delete": False,  # only admin can delete
                    }
    else:
        # No role assigned → default: can view dashboard only
        perms["dashboard"] = {"can_view": True, "can_edit": False, "can_delete": False}
    return {"is_admin": False, "is_permanent_admin": False, "permissions": perms}


# ============================================================
# CUSTOMERS
# ============================================================
@api.get("/customers", response_model=List[CustomerOut])
async def list_customers(_: dict = Depends(get_current_user)):
    return await db.customers.find({}, {"_id": 0}).to_list(2000)


@api.post("/customers", response_model=CustomerOut)
async def create_customer(payload: CustomerIn, user: dict = Depends(get_current_user)):
    doc = payload.model_dump()
    doc["id"] = gen_id()
    doc["created_at"] = now_iso()
    await db.customers.insert_one(doc)
    await write_audit(db, entity_type="customer", entity_id=doc["id"], action="create", user=user, field_changes=doc)
    doc.pop("_id", None)
    return doc


@api.put("/customers/{cid}", response_model=CustomerOut)
async def update_customer(cid: str, payload: CustomerIn, user: dict = Depends(get_current_user)):
    existing = await db.customers.find_one({"id": cid})
    if not existing:
        raise HTTPException(404, "Not found")
    updates = payload.model_dump()
    await db.customers.update_one({"id": cid}, {"$set": updates})
    await write_audit(db, entity_type="customer", entity_id=cid, action="update", user=user, field_changes=updates)
    return await db.customers.find_one({"id": cid}, {"_id": 0})


@api.delete("/customers/{cid}")
async def delete_customer(cid: str, user: dict = Depends(require_role("admin"))):
    existing = await db.customers.find_one({"id": cid}, {"_id": 0})
    if not existing:
        raise HTTPException(404, "Customer not found")
    linked = await db.projects.count_documents({"customer_id": cid})
    if linked > 0:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot delete '{existing.get('customer_name', cid)}'. {linked} project(s) are linked to this customer. Reassign or delete those projects first.",
        )
    await db.customers.delete_one({"id": cid})
    await write_audit(db, entity_type="customer", entity_id=cid, action="delete", user=user)
    return {"ok": True}


# ============================================================
# EMPLOYEES
# ============================================================
@api.get("/employees", response_model=List[EmployeeOut])
async def list_employees(_: dict = Depends(get_current_user)):
    return await db.employees.find({}, {"_id": 0}).to_list(2000)


@api.post("/employees", response_model=EmployeeOut)
async def create_employee(payload: EmployeeIn, user: dict = Depends(require_role("admin"))):
    doc = payload.model_dump()
    doc["id"] = gen_id()
    doc["created_at"] = now_iso()
    if await db.employees.find_one({"email_id": doc["email_id"]}):
        raise HTTPException(409, "Employee email already exists")
    await db.employees.insert_one(doc)
    await write_audit(db, entity_type="employee", entity_id=doc["id"], action="create", user=user, field_changes=doc)
    doc.pop("_id", None)
    return doc


@api.put("/employees/{eid}", response_model=EmployeeOut)
async def update_employee(eid: str, payload: EmployeeIn, user: dict = Depends(require_role("admin"))):
    existing = await db.employees.find_one({"id": eid})
    if not existing:
        raise HTTPException(404, "Not found")
    updates = payload.model_dump()
    await db.employees.update_one({"id": eid}, {"$set": updates})
    await write_audit(db, entity_type="employee", entity_id=eid, action="update", user=user, field_changes=updates)
    return await db.employees.find_one({"id": eid}, {"_id": 0})


@api.delete("/employees/{eid}")
async def delete_employee(eid: str, user: dict = Depends(require_role("admin"))):
    await db.employees.delete_one({"id": eid})
    await write_audit(db, entity_type="employee", entity_id=eid, action="delete", user=user)
    return {"ok": True}


# Permanent admin emails (lowercased) — these are NEVER touched by Excel replace
PERMANENT_ADMIN_EMPLOYEES_LOWER = {
    "rohit.kataria@waisldigital.com",
    "tushar.sukhija@waisldigital.com",
}


def _row_to_employee(row: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Normalize an Excel/CSV row into an Employee document. Supports BRD column names."""
    def get(*names):
        for n in names:
            for k, v in row.items():
                if k is None:
                    continue
                if str(k).strip().lower().replace(" ", "_").replace("-", "_") == n.lower().replace(" ", "_").replace("-", "_"):
                    if v is None:
                        return ""
                    return str(v).strip() if not isinstance(v, str) else v.strip()
        return ""

    email = get("Email ID", "email_id", "email")
    if not email:
        return None
    return {
        "employee_no": get("Employee No", "employee_no"),
        "email_id": email,
        "status": get("Status") or "Active",
        "joining_date": get("Joining Date", "joining_date") or None,
        "exit_date": get("Exit Date", "exit_date") or None,
        "employment_type": get("Employement Type", "Employment Type", "employment_type") or "Employee",
        "employee_name": get("Employee Name", "employee_name"),
        "role_zoho": get("Role (as per Zoho)", "role_zoho", "role"),
        "l1_manager": get("L1 Manager", "l1_manager"),
        "location": get("Location"),
        "department": get("Department"),
        "sub_department": get("Sub Department", "sub_department"),
    }


@api.post("/employees/bulk-upload")
async def employees_bulk_upload(
    file: UploadFile = File(...),
    mode: str = Query("append", description="append | replace"),
    user: dict = Depends(require_role("admin")),
):
    if mode not in ("append", "replace"):
        raise HTTPException(400, "mode must be 'append' or 'replace'")
    contents = await file.read()
    fname = (file.filename or "").lower()

    rows: List[Dict[str, Any]] = []
    try:
        if fname.endswith(".csv"):
            import csv
            import io
            text = contents.decode("utf-8-sig", errors="ignore")
            reader = csv.DictReader(io.StringIO(text))
            for r in reader:
                rows.append(dict(r))
        else:
            from openpyxl import load_workbook
            import io
            wb = load_workbook(io.BytesIO(contents), read_only=True, data_only=True)
            ws = wb.active
            headers = []
            for ri, row in enumerate(ws.iter_rows(values_only=True)):
                if ri == 0:
                    headers = [str(h or "").strip() for h in row]
                    continue
                rd = {headers[i]: (row[i] if i < len(row) else None) for i in range(len(headers))}
                rows.append(rd)
    except Exception as e:
        raise HTTPException(400, f"Failed to parse file: {e}")

    parsed: List[Dict[str, Any]] = []
    failures: List[Dict[str, Any]] = []
    seen_emails = set()
    for i, raw in enumerate(rows):
        emp = _row_to_employee(raw)
        if not emp:
            failures.append({"row": i + 2, "reason": "missing email_id"})
            continue
        em_low = emp["email_id"].lower()
        if em_low in seen_emails:
            failures.append({"row": i + 2, "reason": f"duplicate email in file: {emp['email_id']}"})
            continue
        seen_emails.add(em_low)
        if not emp.get("employee_name"):
            failures.append({"row": i + 2, "reason": "missing employee_name"})
            continue
        emp["id"] = gen_id()
        emp["created_at"] = now_iso()
        parsed.append(emp)

    replaced_count = 0
    if mode == "replace":
        # Preserve permanent admin employee rows
        protected = await db.employees.find({}, {"_id": 0}).to_list(5000)
        protected = [p for p in protected if (p.get("email_id") or "").lower() in PERMANENT_ADMIN_EMPLOYEES_LOWER]
        if protected:
            await db.employees.delete_many({"email_id": {"$nin": [p["email_id"] for p in protected]}})
        else:
            await db.employees.delete_many({})
        if parsed:
            # Skip rows that match permanent admin emails — keep the seeded one
            protected_lowers = {p["email_id"].lower() for p in protected}
            kept = [r for r in parsed if r["email_id"].lower() not in protected_lowers]
            if kept:
                await db.employees.insert_many(kept)
            replaced_count = len(kept)
        await write_audit(db, entity_type="employee", entity_id="bulk", action="replace_upload",
                          user=user, field_changes={"rows": replaced_count, "protected": len(protected)})
    else:
        # Append: skip rows whose email already exists
        existing_emails = {(e.get("email_id") or "").lower() async for e in db.employees.find({}, {"_id": 0, "email_id": 1})}
        new_rows = [r for r in parsed if r["email_id"].lower() not in existing_emails]
        if new_rows:
            await db.employees.insert_many(new_rows)
        replaced_count = len(new_rows)
        await write_audit(db, entity_type="employee", entity_id="bulk", action="append_upload",
                          user=user, field_changes={"rows": replaced_count})

    return {
        "mode": mode,
        "total_rows": len(rows),
        "saved": replaced_count,
        "failed": len(failures),
        "failures": failures[:50],
    }


# ============================================================
# SUPPLIERS
# ============================================================
@api.get("/suppliers", response_model=List[SupplierOut])
async def list_suppliers(_: dict = Depends(get_current_user)):
    return await db.suppliers.find({}, {"_id": 0}).to_list(2000)


@api.post("/suppliers", response_model=SupplierOut)
async def create_supplier(payload: SupplierIn, user: dict = Depends(get_current_user)):
    doc = payload.model_dump()
    doc["id"] = gen_id()
    doc["created_at"] = now_iso()
    await db.suppliers.insert_one(doc)
    await write_audit(db, entity_type="supplier", entity_id=doc["id"], action="create", user=user, field_changes=doc)
    doc.pop("_id", None)
    return doc


@api.put("/suppliers/{sid}", response_model=SupplierOut)
async def update_supplier(sid: str, payload: SupplierIn, user: dict = Depends(get_current_user)):
    existing = await db.suppliers.find_one({"id": sid})
    if not existing:
        raise HTTPException(404, "Not found")
    updates = payload.model_dump()
    await db.suppliers.update_one({"id": sid}, {"$set": updates})
    await write_audit(db, entity_type="supplier", entity_id=sid, action="update", user=user, field_changes=updates)
    return await db.suppliers.find_one({"id": sid}, {"_id": 0})


@api.delete("/suppliers/{sid}")
async def delete_supplier(sid: str, user: dict = Depends(require_role("admin"))):
    await db.suppliers.delete_one({"id": sid})
    await write_audit(db, entity_type="supplier", entity_id=sid, action="delete", user=user)
    return {"ok": True}


# ============================================================
# PROJECTS
# ============================================================
@api.get("/projects", response_model=List[ProjectOut])
async def list_projects(
    stage: Optional[str] = None,
    customer_id: Optional[str] = None,
    search: Optional[str] = None,
    _: dict = Depends(get_current_user),
):
    q: Dict[str, Any] = {}
    if stage:
        q["current_stage"] = stage
    if customer_id:
        q["customer_id"] = customer_id
    if search:
        q["$or"] = [
            {"project_name": {"$regex": search, "$options": "i"}},
            {"wbs_element": {"$regex": search, "$options": "i"}},
            {"customer_name": {"$regex": search, "$options": "i"}},
        ]
    rows = await db.projects.find(q, {"_id": 0}).to_list(2000)
    return rows


@api.get("/projects/{pid}", response_model=ProjectOut)
async def get_project(pid: str, _: dict = Depends(get_current_user)):
    doc = await db.projects.find_one({"id": pid}, {"_id": 0})
    if not doc:
        raise HTTPException(404, "Not found")
    return doc


@api.post("/projects/parse-pdf")
async def parse_project_pdf(file: UploadFile = File(...), _: dict = Depends(get_current_user)):
    """Parse a PO PDF and return extracted fields WITHOUT saving anything.
    Used by the New/Edit Project modal so the user can preview and confirm
    before fields are applied to the form."""
    safe_name = (file.filename or "file").lower()
    if not (file.content_type == "application/pdf" or safe_name.endswith(".pdf")):
        raise HTTPException(400, "Only PDF files are supported for auto-parse")
    contents = await file.read()
    if not contents:
        raise HTTPException(400, "Empty file")
    if len(contents) > 25 * 1024 * 1024:  # 25 MB safety cap
        raise HTTPException(413, "PDF too large (max 25 MB)")
    try:
        from pdf_parser import parse_customer_po
        parsed = parse_customer_po(contents)
    except Exception as e:
        raise HTTPException(500, f"Parse failed: {e}")
    return {"file_name": file.filename, "size": len(contents), "parsed": parsed}


@api.post("/projects/parse-excel")
async def parse_project_excel(
    file: UploadFile = File(...),
    wbs: Optional[str] = Query(None, description="WBS Element to look up in the Project Master sheet"),
    _: dict = Depends(get_current_user),
):
    """Parse the unified SAP transactions workbook and return fields suitable
    for pre-filling the New/Edit Project modal.

    The workbook MUST contain a `Project Master` sheet. If `wbs` is provided
    we look up the matching project; otherwise we return the list of
    available WBS Elements so the user can pick one in the UI.
    """
    safe_name = (file.filename or "file").lower()
    if not (safe_name.endswith(".xlsx") or safe_name.endswith(".xls")):
        raise HTTPException(400, "Only Excel files (.xlsx) are supported")
    contents = await file.read()
    if not contents:
        raise HTTPException(400, "Empty file")
    if len(contents) > 30 * 1024 * 1024:
        raise HTTPException(413, "Excel too large (max 30 MB)")
    try:
        result = sap_parser.lookup_project_metadata(contents, wbs_input=wbs)
    except Exception as e:
        raise HTTPException(500, f"Parse failed: {e}")
    # Convert into the same shape ProjectFormModal expects
    metadata = result.get("metadata") or {}
    parsed: Dict[str, Any] = {
        "po_type": "SAP Project Master",
        "po_classification": {
            "po_type": "SAP Project Master",
            "issuer": None, "recipient": None,
            "confidence": "high" if result.get("matched") else "low",
        },
        "matched": result.get("matched", False),
        "candidates": result.get("candidates", []),
        "wbs_element": metadata.get("wbs_element"),
        "project_name": metadata.get("project_name"),
        "pnl_location": metadata.get("pnl_location"),
        "project_grouping": metadata.get("project_grouping"),
        "airport_adjacency": metadata.get("airport_adjacency"),
        "location": metadata.get("location"),
        "category1": metadata.get("category1"),
        "category2": metadata.get("category2"),
        "business_category": metadata.get("business_category"),
        "retro_pnl_tagging": metadata.get("retro_pnl_tagging"),
        "warnings": [] if result.get("matched") else (
            ["No matching WBS in Project Master — pick one from the candidates list"] if wbs else
            ["Provide a WBS Element to auto-fill from Project Master"]
        ),
    }
    return {"file_name": file.filename, "size": len(contents), "parsed": parsed}


@api.post("/projects", response_model=ProjectOut)
async def create_project(payload: ProjectIn, user: dict = Depends(get_current_user)):
    doc = payload.model_dump()
    doc["id"] = gen_id()
    margin = compute_margin(doc.get("po_value", 0), doc.get("revenue_total", 0), doc.get("cost_total", 0))
    doc["margin_total"] = margin["margin_total"]
    doc["margin_pct"] = margin["margin_pct"]
    doc["current_stage"] = "Pipeline"
    doc["approval_status"] = "Not Required"
    doc["created_at"] = now_iso()
    doc["updated_at"] = now_iso()
    doc["created_by"] = user["email"]
    # link customer name if id given
    if doc.get("customer_id") and not doc.get("customer_name"):
        c = await db.customers.find_one({"id": doc["customer_id"]}, {"_id": 0})
        if c:
            doc["customer_name"] = c["customer_name"]
    await db.projects.insert_one(doc)
    await write_audit(db, entity_type="project", entity_id=doc["id"], action="create", user=user, field_changes={
        "project_name": doc["project_name"], "stage": "Pipeline"})
    doc.pop("_id", None)
    return doc


@api.put("/projects/{pid}", response_model=ProjectOut)
async def update_project(pid: str, payload: ProjectIn, user: dict = Depends(get_current_user)):
    existing = await db.projects.find_one({"id": pid})
    if not existing:
        raise HTTPException(404, "Not found")
    updates = payload.model_dump()
    margin = compute_margin(updates.get("po_value", 0), updates.get("revenue_total", 0), updates.get("cost_total", 0))
    updates["margin_total"] = margin["margin_total"]
    updates["margin_pct"] = margin["margin_pct"]
    updates["updated_at"] = now_iso()
    await db.projects.update_one({"id": pid}, {"$set": updates})
    field_changes = {k: {"old": existing.get(k), "new": v} for k, v in updates.items() if existing.get(k) != v}
    await write_audit(db, entity_type="project", entity_id=pid, action="update", user=user, field_changes=field_changes)
    return await db.projects.find_one({"id": pid}, {"_id": 0})


@api.post("/projects/{pid}/transition", response_model=ProjectOut)
async def transition_project(pid: str, payload: StageTransitionIn, user: dict = Depends(get_current_user)):
    project = await db.projects.find_one({"id": pid}, {"_id": 0})
    if not project:
        raise HTTPException(404, "Not found")
    current = project["current_stage"]
    target = payload.target_stage
    if not can_transition(current, target):
        raise HTTPException(400, f"Cannot transition from {current} to {target}")

    # Check pending approvals for target stage
    pending = await db.approval_requests.find_one({"project_id": pid, "target_stage": target, "status": "Pending"})
    if pending:
        raise HTTPException(400, "There is a pending approval request for this transition")

    # If forward, check if approval rule applies
    forward = STAGES.index(target) > STAGES.index(current)
    if forward:
        rule = await find_matching_rule(db, project, target)
        if rule:
            req = await create_approval_request(db, project, rule, target, user)
            await db.projects.update_one({"id": pid}, {"$set": {"approval_status": "Pending", "updated_at": now_iso()}})
            await write_audit(db, entity_type="project", entity_id=pid, action="approval_requested", user=user,
                              field_changes={"target_stage": target, "rule": rule.get("name")},
                              reason=payload.reason or "")
            # Fire-and-forget email notification (Microsoft Graph). Skipped silently
            # when credentials are placeholders or NOTIFY_ENABLED=false.
            try:
                subject, html = tpl_approval_request({**req, "raised_by": user.get("email"), "reason": payload.reason or ""}, project)
                # extra recipients: rule approvers
                cc = [a for a in (rule.get("approver_emails") or []) if a]
                import asyncio as _asyncio
                _asyncio.create_task(mailer.send(subject=subject, html_body=html, cc=cc))
            except Exception as _e:
                logger.warning("Notification dispatch failed: %s", _e)
            return await db.projects.find_one({"id": pid}, {"_id": 0})

    # No approval needed → transition immediately
    await db.projects.update_one({"id": pid}, {"$set": {
        "current_stage": target, "approval_status": "Not Required" if forward else project.get("approval_status"),
        "updated_at": now_iso(),
    }})
    await write_audit(db, entity_type="project", entity_id=pid, action="stage_change", user=user,
                      field_changes={"from": current, "to": target}, reason=payload.reason or "")
    return await db.projects.find_one({"id": pid}, {"_id": 0})


@api.delete("/projects/{pid}")
async def delete_project(pid: str, user: dict = Depends(require_role("admin"))):
    await db.projects.delete_one({"id": pid})
    await db.revenue_lines.delete_many({"project_id": pid})
    await db.cost_lines.delete_many({"project_id": pid})
    await write_audit(db, entity_type="project", entity_id=pid, action="delete", user=user)
    return {"ok": True}


# ============================================================
# REVENUE & COST LINES
# ============================================================
@api.get("/projects/{pid}/revenue", response_model=List[RevenueLineOut])
async def list_revenue(pid: str, _: dict = Depends(get_current_user)):
    return await db.revenue_lines.find({"project_id": pid}, {"_id": 0}).to_list(1000)


@api.post("/projects/{pid}/revenue", response_model=RevenueLineOut)
async def add_revenue(pid: str, payload: RevenueLineIn, user: dict = Depends(get_current_user)):
    doc = payload.model_dump()
    doc["project_id"] = pid
    doc["id"] = gen_id()
    doc["created_at"] = now_iso()
    await db.revenue_lines.insert_one(doc)
    await write_audit(db, entity_type="revenue_line", entity_id=doc["id"], action="create", user=user, field_changes=doc)
    doc.pop("_id", None)
    return doc


@api.delete("/revenue/{rid}")
async def delete_revenue(rid: str, user: dict = Depends(get_current_user)):
    await db.revenue_lines.delete_one({"id": rid})
    await write_audit(db, entity_type="revenue_line", entity_id=rid, action="delete", user=user)
    return {"ok": True}


@api.get("/projects/{pid}/cost", response_model=List[CostLineOut])
async def list_cost(pid: str, _: dict = Depends(get_current_user)):
    return await db.cost_lines.find({"project_id": pid}, {"_id": 0}).to_list(1000)


@api.post("/projects/{pid}/cost", response_model=CostLineOut)
async def add_cost(pid: str, payload: CostLineIn, user: dict = Depends(get_current_user)):
    doc = payload.model_dump()
    doc["project_id"] = pid
    doc["id"] = gen_id()
    doc["created_at"] = now_iso()
    await db.cost_lines.insert_one(doc)
    await write_audit(db, entity_type="cost_line", entity_id=doc["id"], action="create", user=user, field_changes=doc)
    doc.pop("_id", None)
    return doc


@api.delete("/cost/{cid}")
async def delete_cost(cid: str, user: dict = Depends(get_current_user)):
    await db.cost_lines.delete_one({"id": cid})
    await write_audit(db, entity_type="cost_line", entity_id=cid, action="delete", user=user)
    return {"ok": True}


# ============================================================
# APPROVAL MATRIX & QUEUE
# ============================================================
@api.get("/approvals/rules", response_model=List[ApprovalRuleOut])
async def list_rules(_: dict = Depends(get_current_user)):
    return await db.approval_rules.find({}, {"_id": 0}).to_list(500)


@api.post("/approvals/rules", response_model=ApprovalRuleOut)
async def create_rule(payload: ApprovalRuleIn, user: dict = Depends(require_role("admin"))):
    doc = payload.model_dump()
    doc["id"] = gen_id()
    doc["created_at"] = now_iso()
    await db.approval_rules.insert_one(doc)
    await write_audit(db, entity_type="approval_rule", entity_id=doc["id"], action="create", user=user, field_changes=doc)
    doc.pop("_id", None)
    return doc


@api.put("/approvals/rules/{rid}", response_model=ApprovalRuleOut)
async def update_rule(rid: str, payload: ApprovalRuleIn, user: dict = Depends(require_role("admin"))):
    updates = payload.model_dump()
    await db.approval_rules.update_one({"id": rid}, {"$set": updates})
    await write_audit(db, entity_type="approval_rule", entity_id=rid, action="update", user=user, field_changes=updates)
    return await db.approval_rules.find_one({"id": rid}, {"_id": 0})


@api.delete("/approvals/rules/{rid}")
async def delete_rule(rid: str, user: dict = Depends(require_role("admin"))):
    await db.approval_rules.delete_one({"id": rid})
    await write_audit(db, entity_type="approval_rule", entity_id=rid, action="delete", user=user)
    return {"ok": True}


@api.get("/approvals/requests")
async def list_requests(status: Optional[str] = None, user: dict = Depends(get_current_user)):
    q: Dict[str, Any] = {}
    if status:
        q["status"] = status
    rows = await db.approval_requests.find(q, {"_id": 0}).sort("requested_at", -1).to_list(500)
    return rows


@api.post("/approvals/requests/{req_id}/action")
async def action_request(req_id: str, payload: ApprovalActionIn, user: dict = Depends(get_current_user)):
    req = await db.approval_requests.find_one({"id": req_id}, {"_id": 0})
    if not req:
        raise HTTPException(404, "Not found")
    if req["status"] != "Pending":
        raise HTTPException(400, "Request already actioned")
    # Authorization: allow admin, or approver_role match, or email in approver_emails
    if not (user.get("role") == "admin"
            or (req.get("approver_role") and user.get("role") == req["approver_role"])
            or user.get("email") in (req.get("approver_emails") or [])):
        raise HTTPException(403, "You are not authorized to action this request")

    new_status = "Approved" if payload.action == "approve" else "Rejected"
    await db.approval_requests.update_one({"id": req_id}, {"$set": {
        "status": new_status, "comment": payload.comment or "",
        "actioned_at": now_iso(), "actioned_by": user["email"],
    }})

    project = await db.projects.find_one({"id": req["project_id"]})
    if project:
        if new_status == "Approved":
            await db.projects.update_one({"id": project["id"]}, {"$set": {
                "current_stage": req["target_stage"], "approval_status": "Approved",
                "updated_at": now_iso(),
            }})
            await write_audit(db, entity_type="project", entity_id=project["id"], action="stage_change",
                              user=user, field_changes={"from": project["current_stage"], "to": req["target_stage"]},
                              reason=f"Approved via rule '{req.get('rule_name')}'")
        else:
            await db.projects.update_one({"id": project["id"]}, {"$set": {
                "approval_status": "Rejected", "updated_at": now_iso(),
            }})
            await write_audit(db, entity_type="project", entity_id=project["id"], action="approval_rejected",
                              user=user, field_changes={"target_stage": req["target_stage"]},
                              reason=payload.comment or "")

    await write_audit(db, entity_type="approval_request", entity_id=req_id, action=new_status.lower(),
                      user=user, field_changes={"comment": payload.comment})
    return await db.approval_requests.find_one({"id": req_id}, {"_id": 0})


# ============================================================
# DASHBOARD
# ============================================================
@api.get("/dashboard/summary")
async def dashboard_summary(
    section: Optional[str] = Query(None, description="projects | change_requests | pipeline (defaults to all)"),
    customer_ids: Optional[str] = Query(None, description="Comma-separated customer ids"),
    project_ids: Optional[str] = Query(None, description="Comma-separated project ids"),
    business_category: Optional[str] = Query(None, description="GMR | Non-GMR"),
    date_from: Optional[str] = Query(None, description="YYYY-MM-DD"),
    date_to: Optional[str] = Query(None, description="YYYY-MM-DD"),
    user: dict = Depends(get_current_user),
):
    cust_filter = [c for c in (customer_ids or "").split(",") if c]
    proj_filter = [p for p in (project_ids or "").split(",") if p]

    def _project_matches(p: dict) -> bool:
        if cust_filter and p.get("customer_id") not in cust_filter:
            return False
        if proj_filter and p["id"] not in proj_filter:
            return False
        if business_category and (p.get("business_category") or "Non-GMR") != business_category:
            return False
        if section in ("projects", "change_requests"):
            cat = (p.get("category1") or "").strip().lower()
            is_cr = "change request" in cat or "change order" in cat or "amendment" in cat
            if section == "change_requests" and not is_cr:
                return False
            if section == "projects" and is_cr:
                return False
        return True

    all_projects = await db.projects.find({}, {"_id": 0}).to_list(5000)
    projects = [p for p in all_projects if _project_matches(p)]
    pids = {p["id"] for p in projects}

    stage_summary: Dict[str, Dict[str, float]] = {s: {"count": 0, "value": 0.0, "margin": 0.0} for s in STAGES}
    total_po, total_rev, total_cost = 0.0, 0.0, 0.0
    delayed_projects: List[dict] = []
    low_margin_projects: List[dict] = []
    delayed_milestones: List[dict] = []
    today = datetime.now(timezone.utc).date()

    for p in projects:
        st = p.get("current_stage", "Pipeline")
        if st in stage_summary:
            stage_summary[st]["count"] += 1
            stage_summary[st]["value"] += p.get("po_value", 0) or 0
            stage_summary[st]["margin"] += p.get("margin_total", 0) or 0
        total_po += p.get("po_value", 0) or 0
        total_rev += p.get("revenue_total", 0) or 0
        total_cost += p.get("cost_total", 0) or 0
        # delayed: end_date < today and stage != Closure
        end = p.get("end_date")
        if end and st != "Closure":
            try:
                if datetime.fromisoformat(end).date() < today:
                    delayed_projects.append({
                        "id": p["id"], "project_name": p["project_name"], "wbs_element": p.get("wbs_element"),
                        "end_date": end, "current_stage": st, "po_value": p.get("po_value", 0),
                        "customer_name": p.get("customer_name"),
                    })
            except Exception:
                pass
        # delayed milestones — any unbilled milestone past due date
        for m in (p.get("milestones") or []):
            if m.get("is_billed"):
                continue
            due = m.get("due_date")
            if not due:
                continue
            try:
                due_date = datetime.fromisoformat(due).date()
            except Exception:
                continue
            if due_date < today:
                delayed_milestones.append({
                    "project_id": p["id"],
                    "project_name": p["project_name"],
                    "wbs_element": p.get("wbs_element"),
                    "customer_name": p.get("customer_name"),
                    "milestone_name": m.get("milestone_name"),
                    "due_date": due,
                    "value": m.get("value") or 0,
                    "days_overdue": (today - due_date).days,
                })
        # low margin: margin_pct < 15
        if (p.get("margin_pct") or 0) < 15:
            low_margin_projects.append({
                "id": p["id"], "project_name": p["project_name"], "margin_pct": p.get("margin_pct", 0),
                "po_value": p.get("po_value", 0), "customer_name": p.get("customer_name"),
                "current_stage": st,
            })

    # recognized but unbilled (filter to pids in scope)
    rev_q: Dict[str, Any] = {}
    if pids:
        rev_q["project_id"] = {"$in": list(pids)}
    rev_lines = await db.revenue_lines.find(rev_q, {"_id": 0}).to_list(5000)
    if date_from:
        rev_lines = [r for r in rev_lines if (r.get("recognition_date") or "") >= date_from]
    if date_to:
        rev_lines = [r for r in rev_lines if (r.get("recognition_date") or "") <= date_to]
    recognized = sum(r.get("amount", 0) for r in rev_lines)
    billed = sum(r.get("amount", 0) for r in rev_lines if r.get("is_billed"))
    unbilled = recognized - billed

    # top customers
    cust_agg: Dict[str, Dict[str, Any]] = {}
    for p in projects:
        cid = p.get("customer_id") or "_none"
        cname = p.get("customer_name") or "Unknown"
        if cid not in cust_agg:
            cust_agg[cid] = {"customer_id": cid, "customer_name": cname, "po_value": 0, "revenue": 0, "count": 0}
        cust_agg[cid]["po_value"] += p.get("po_value", 0) or 0
        cust_agg[cid]["revenue"] += p.get("revenue_total", 0) or 0
        cust_agg[cid]["count"] += 1
    top_customers = sorted(cust_agg.values(), key=lambda x: -x["po_value"])[:10]

    # vendor exposure (sum of cost lines by supplier_name) — top 10
    cost_q: Dict[str, Any] = {}
    if pids:
        cost_q["project_id"] = {"$in": list(pids)}
    cost_lines = await db.cost_lines.find(cost_q, {"_id": 0}).to_list(5000)
    vendor_agg: Dict[str, float] = {}
    for c in cost_lines:
        sn = c.get("supplier_name") or "Unspecified"
        vendor_agg[sn] = vendor_agg.get(sn, 0) + (c.get("amount", 0) or 0)
    vendor_exposure = sorted(
        [{"supplier_name": k, "amount": v} for k, v in vendor_agg.items()],
        key=lambda x: -x["amount"],
    )[:10]

    # monthly billing status (last 6 months)
    months: List[str] = []
    base = datetime.now(timezone.utc).replace(day=1)
    for i in range(5, -1, -1):
        m = (base - timedelta(days=30 * i))
        months.append(m.strftime("%Y-%m"))
    monthly: List[Dict[str, Any]] = []
    for m in months:
        b = sum(r.get("amount", 0) for r in rev_lines if (r.get("billing_date") or "")[:7] == m and r.get("is_billed"))
        rec = sum(r.get("amount", 0) for r in rev_lines if (r.get("recognition_date") or "")[:7] == m)
        monthly.append({"month": m, "billed": b, "recognized": rec})

    # Cascading filter options — based on current filtered scope
    customer_options: Dict[str, str] = {}
    for p in projects:
        if p.get("customer_id"):
            customer_options[p["customer_id"]] = p.get("customer_name") or "Unknown"
    project_options = [
        {"id": p["id"], "name": p.get("project_name") or "?", "wbs_element": p.get("wbs_element"),
         "customer_id": p.get("customer_id"), "category1": p.get("category1") or ""}
        for p in projects
    ]

    delayed_milestones.sort(key=lambda x: -(x["days_overdue"]))

    return {
        "filters_applied": {
            "section": section, "customer_ids": cust_filter,
            "project_ids": proj_filter, "business_category": business_category,
            "date_from": date_from, "date_to": date_to,
        },
        "filter_options": {
            "customers": [{"id": k, "name": v} for k, v in sorted(customer_options.items(), key=lambda x: x[1])],
            "projects": project_options,
        },
        "stage_summary": [
            {"stage": s, "count": stage_summary[s]["count"],
             "po_value": stage_summary[s]["value"], "margin": stage_summary[s]["margin"]} for s in STAGES
        ],
        "totals": {
            "total_projects": len(projects),
            "total_po_value": total_po,
            "total_revenue": total_rev,
            "total_cost": total_cost,
            "total_margin": total_rev - total_cost,
            "margin_pct": ((total_rev - total_cost) / total_rev * 100) if total_rev else 0,
        },
        "recognized_unbilled": {"recognized": recognized, "billed": billed, "unbilled": unbilled},
        "delayed_projects": delayed_projects[:50],
        "delayed_milestones": delayed_milestones[:50],
        "low_margin_projects": low_margin_projects[:50],
        "top_customers": top_customers,
        "vendor_exposure": vendor_exposure,
        "monthly_billing": monthly,
        "approvals_pending": await db.approval_requests.count_documents({"status": "Pending"}),
    }


# ============================================================
# AUDIT
# ============================================================
@api.get("/audit", response_model=List[AuditLogOut])
async def list_audit(
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    limit: int = Query(200, le=500),
    _: dict = Depends(get_current_user),
):
    q: Dict[str, Any] = {}
    if entity_type:
        q["entity_type"] = entity_type
    if entity_id:
        q["entity_id"] = entity_id
    rows = await db.audit_logs.find(q, {"_id": 0}).sort("timestamp", -1).to_list(limit)
    return rows


# ============================================================
# EXCEL UPLOAD ENGINE
# ============================================================
@api.get("/uploads/template/{entity}")
async def download_template(entity: str, _: dict = Depends(get_current_user)):
    if entity == "sap-transactions":
        data = sap_parser.build_template_xlsx()
        return StreamingResponse(io.BytesIO(data),
                                 media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                 headers={"Content-Disposition": 'attachment; filename="sap_transactions_template.xlsx"'})
    if entity not in SCHEMAS:
        raise HTTPException(404, "Unknown entity")
    data = build_template_xlsx(entity)
    return StreamingResponse(io.BytesIO(data),
                             media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                             headers={"Content-Disposition": f'attachment; filename="{entity}_template.xlsx"'})


@api.get("/uploads/export/{entity}")
async def export_master(entity: str, _: dict = Depends(get_current_user)):
    if entity not in SCHEMAS:
        raise HTTPException(404, "Unknown entity")
    coll_map = {
        "project": "projects", "customer": "customers", "employee": "employees",
        "supplier": "suppliers", "revenue": "revenue_lines", "cost": "cost_lines",
    }
    rows = await db[coll_map[entity]].find({}, {"_id": 0}).to_list(10000)
    # only include columns from schema
    cols = list(SCHEMAS[entity].keys())
    rows = [{c: r.get(c) for c in cols} for r in rows]
    data = build_export_xlsx(rows, entity)
    return StreamingResponse(io.BytesIO(data),
                             media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                             headers={"Content-Disposition": f'attachment; filename="{entity}_export.xlsx"'})


@api.post("/uploads/{entity}")
async def upload_excel(entity: str, file: UploadFile = File(...), user: dict = Depends(get_current_user)):
    if entity not in SCHEMAS:
        raise HTTPException(404, "Unknown entity")
    contents = await file.read()
    try:
        valid, failures = parse_xlsx(contents, entity)
    except Exception as e:
        raise HTTPException(400, f"Failed to parse Excel: {e}")

    success_rows = 0
    coll_map = {
        "project": "projects", "customer": "customers", "employee": "employees",
        "supplier": "suppliers", "revenue": "revenue_lines", "cost": "cost_lines",
    }
    coll = db[coll_map[entity]]
    insert_failures: List[Dict[str, Any]] = []

    for rec in valid:
        try:
            rec["id"] = gen_id()
            rec["created_at"] = now_iso()
            if entity == "project":
                margin = compute_margin(rec.get("po_value", 0), rec.get("revenue_total", 0), rec.get("cost_total", 0))
                rec["margin_total"] = margin["margin_total"]
                rec["margin_pct"] = margin["margin_pct"]
                rec.setdefault("current_stage", "Pipeline")
                rec.setdefault("approval_status", "Not Required")
                rec["updated_at"] = now_iso()
                rec["created_by"] = user["email"]
                # try map customer
                if rec.get("customer_name") and not rec.get("customer_id"):
                    c = await db.customers.find_one({"customer_name": rec["customer_name"]}, {"_id": 0})
                    if c:
                        rec["customer_id"] = c["id"]
            await coll.insert_one(rec)
            success_rows += 1
        except Exception as e:
            insert_failures.append({"row": "?", "errors": [str(e)], "data": rec})

    log = {
        "id": gen_id(), "entity_type": entity, "file_name": file.filename or "upload.xlsx",
        "total_rows": len(valid) + len(failures), "success_rows": success_rows,
        "failed_rows": len(failures) + len(insert_failures),
        "failures": failures + insert_failures,
        "uploaded_by": user["email"], "uploaded_at": now_iso(),
    }
    await db.upload_logs.insert_one(log)
    log.pop("_id", None)
    await write_audit(db, entity_type="upload", entity_id=log["id"], action="bulk_upload", user=user,
                      field_changes={"entity": entity, "success": success_rows, "failed": log["failed_rows"]})
    return log


@api.get("/uploads/logs", response_model=List[UploadLogOut])
async def upload_logs(_: dict = Depends(get_current_user)):
    return await db.upload_logs.find({}, {"_id": 0}).sort("uploaded_at", -1).to_list(200)


# ----- Unified SAP transactions: one workbook covers Revenue + Expense + Suppliers + Project Master -----
@api.post("/projects/{pid}/sap-upload")
async def project_sap_upload(
    pid: str,
    kind: str = Query(..., regex="^(revenue|cost)$"),
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user),
):
    """Import revenue OR cost lines from the unified SAP workbook for a single
    project. Rows are matched to the project's WBS Element (or any prefix of it)
    so that sub-WBS rows like ``WSIN.000136.0001`` flow into the parent project
    ``WSIN.000136``. Returns counts: matched / imported / skipped."""
    project = await db.projects.find_one({"id": pid}, {"_id": 0})
    if not project:
        raise HTTPException(404, "Project not found")
    safe_name = (file.filename or "file").lower()
    if not (safe_name.endswith(".xlsx") or safe_name.endswith(".xls")):
        raise HTTPException(400, "Only Excel files (.xlsx) are supported")
    contents = await file.read()
    if not contents:
        raise HTTPException(400, "Empty file")
    if len(contents) > 60 * 1024 * 1024:
        raise HTTPException(413, "Excel too large (max 60 MB)")

    wbs = project.get("wbs_element")
    if not wbs:
        raise HTTPException(400, "Project has no WBS Element configured — cannot match SAP rows")

    try:
        if kind == "revenue":
            rows = sap_parser.parse_revenue_rows(contents, wbs_filter=wbs)
        else:
            rows = sap_parser.parse_cost_rows(contents, wbs_filter=wbs)
    except Exception as e:
        raise HTTPException(400, f"Failed to parse SAP workbook: {e}")

    coll = db.revenue_lines if kind == "revenue" else db.cost_lines
    imported = 0
    skipped = 0
    batch_id = gen_id()
    for r in rows:
        try:
            r["id"] = gen_id()
            r["project_id"] = pid
            r["created_at"] = now_iso()
            r["import_batch_id"] = batch_id
            r["import_source"] = "sap_excel"
            await coll.insert_one(r)
            imported += 1
        except Exception:
            skipped += 1

    log = {
        "id": gen_id(), "entity_type": f"sap_{kind}", "file_name": file.filename or "sap.xlsx",
        "total_rows": len(rows), "success_rows": imported, "failed_rows": skipped,
        "failures": [],
        "uploaded_by": user["email"], "uploaded_at": now_iso(),
        "batch_id": batch_id, "project_id": pid, "kind": kind,
    }
    await db.upload_logs.insert_one(log)
    await write_audit(db, entity_type="project", entity_id=pid, action=f"sap_{kind}_import", user=user,
                      field_changes={"imported": imported, "skipped": skipped, "wbs": wbs, "batch_id": batch_id})
    return {"matched": len(rows), "imported": imported, "skipped": skipped, "wbs": wbs, "kind": kind, "batch_id": batch_id}


@api.get("/projects/{pid}/sap-last-import")
async def project_sap_last_import(pid: str, kind: str = Query(..., regex="^(revenue|cost)$"), _: dict = Depends(get_current_user)):
    """Most recent SAP import batch for this project+kind (used to show the
    'Undo last import' chip)."""
    log = await db.upload_logs.find_one(
        {"project_id": pid, "kind": kind, "entity_type": f"sap_{kind}", "undone_at": {"$in": [None, ""]}},
        {"_id": 0},
        sort=[("uploaded_at", -1)],
    ) or await db.upload_logs.find_one(
        {"project_id": pid, "kind": kind, "entity_type": f"sap_{kind}", "undone_at": {"$exists": False}},
        {"_id": 0},
        sort=[("uploaded_at", -1)],
    )
    if not log or not log.get("batch_id"):
        return {"has_batch": False}
    coll = db.revenue_lines if kind == "revenue" else db.cost_lines
    count = await coll.count_documents({"project_id": pid, "import_batch_id": log["batch_id"]})
    if count == 0:
        return {"has_batch": False}
    return {
        "has_batch": True,
        "batch_id": log["batch_id"],
        "rows": count,
        "uploaded_at": log["uploaded_at"],
        "uploaded_by": log["uploaded_by"],
        "file_name": log["file_name"],
    }


@api.post("/projects/{pid}/sap-undo-last")
async def project_sap_undo_last(pid: str, kind: str = Query(..., regex="^(revenue|cost)$"), user: dict = Depends(get_current_user)):
    """Reverse the most recent SAP import batch for this project+kind."""
    project = await db.projects.find_one({"id": pid}, {"_id": 0})
    if not project:
        raise HTTPException(404, "Project not found")
    log = await db.upload_logs.find_one(
        {"project_id": pid, "kind": kind, "entity_type": f"sap_{kind}", "undone_at": {"$exists": False}},
        {"_id": 0},
        sort=[("uploaded_at", -1)],
    )
    if not log or not log.get("batch_id"):
        raise HTTPException(404, "No SAP import to undo")
    coll = db.revenue_lines if kind == "revenue" else db.cost_lines
    res = await coll.delete_many({"project_id": pid, "import_batch_id": log["batch_id"]})
    # mark log so we don't undo it twice
    await db.upload_logs.update_one(
        {"id": log["id"]},
        {"$set": {"undone_at": now_iso(), "undone_by": user["email"]}},
    )
    await write_audit(db, entity_type="project", entity_id=pid, action=f"sap_{kind}_undo", user=user,
                      field_changes={"deleted": res.deleted_count, "batch_id": log["batch_id"]})
    return {"deleted": res.deleted_count, "batch_id": log["batch_id"], "kind": kind}


# ============================================================
# FINANCE QUERIES (threaded discussion)
# ============================================================
from pydantic import BaseModel as _BM

class QueryCreate(_BM):
    subject: str
    description: str

class ReplyCreate(_BM):
    content: str


@api.get("/projects/{pid}/queries")
async def list_queries(pid: str, _: dict = Depends(get_current_user)):
    rows = await db.finance_queries.find({"project_id": pid}, {"_id": 0}).sort("created_at", -1).to_list(500)
    return rows


@api.post("/projects/{pid}/queries")
async def create_query(pid: str, payload: QueryCreate, user: dict = Depends(get_current_user)):
    project = await db.projects.find_one({"id": pid}, {"_id": 0})
    if not project:
        raise HTTPException(404, "Project not found")
    doc = {
        "id": gen_id(),
        "project_id": pid,
        "project_name": project.get("project_name"),
        "subject": payload.subject,
        "description": payload.description,
        "status": "Open",
        "raised_by": user["email"],
        "raised_by_name": user.get("name"),
        "created_at": now_iso(),
        "replies": [],
        "attachments": [],
    }
    await db.finance_queries.insert_one(doc)
    await write_audit(db, entity_type="finance_query", entity_id=doc["id"], action="create",
                      user=user, field_changes={"project_id": pid, "subject": payload.subject})
    doc.pop("_id", None)
    return doc


@api.post("/queries/{qid}/replies")
async def reply_query(qid: str, payload: ReplyCreate, user: dict = Depends(get_current_user)):
    q = await db.finance_queries.find_one({"id": qid})
    if not q:
        raise HTTPException(404, "Not found")
    if q.get("status") == "Closed":
        raise HTTPException(400, "Query is closed")
    reply = {
        "id": gen_id(),
        "content": payload.content,
        "replied_by": user["email"],
        "replied_by_name": user.get("name"),
        "replied_at": now_iso(),
    }
    await db.finance_queries.update_one({"id": qid}, {"$push": {"replies": reply}})
    await write_audit(db, entity_type="finance_query", entity_id=qid, action="reply",
                      user=user, field_changes={"reply_id": reply["id"]})
    return reply


@api.patch("/queries/{qid}/status")
async def set_query_status(qid: str, status: str = Query(..., regex="^(Open|Closed)$"),
                            user: dict = Depends(get_current_user)):
    q = await db.finance_queries.find_one({"id": qid})
    if not q:
        raise HTTPException(404, "Not found")
    await db.finance_queries.update_one({"id": qid}, {"$set": {"status": status, "closed_at": now_iso() if status == "Closed" else None}})
    await write_audit(db, entity_type="finance_query", entity_id=qid, action="status_change",
                      user=user, field_changes={"status": status})
    return {"ok": True, "status": status}


# ============================================================
# CUSTOMER PROFILE
# ============================================================
@api.get("/customers/{cid}/profile")
async def customer_profile(cid: str, _: dict = Depends(get_current_user)):
    cust = await db.customers.find_one({"id": cid}, {"_id": 0})
    if not cust:
        raise HTTPException(404, "Customer not found")
    projects = await db.projects.find({"customer_id": cid}, {"_id": 0}).to_list(500)
    pids = [p["id"] for p in projects]
    revenue_lines = await db.revenue_lines.find({"project_id": {"$in": pids}}, {"_id": 0}).to_list(5000) if pids else []
    cost_lines = await db.cost_lines.find({"project_id": {"$in": pids}}, {"_id": 0}).to_list(5000) if pids else []

    total_po = sum((p.get("po_value") or 0) for p in projects)
    total_revenue = sum((p.get("revenue_total") or 0) for p in projects)
    total_cost = sum((p.get("cost_total") or 0) for p in projects)
    total_margin = total_revenue - total_cost
    margin_pct = (total_margin / total_revenue * 100) if total_revenue else 0

    recognized = sum((r.get("amount") or 0) for r in revenue_lines)
    billed = sum((r.get("amount") or 0) for r in revenue_lines if r.get("is_billed"))
    unbilled = recognized - billed

    # Ageing buckets based on billing_date vs today (for unbilled, use recognition_date)
    today = datetime.now(timezone.utc).date()
    buckets = {"0-30": 0.0, "31-60": 0.0, "61-90": 0.0, "90+": 0.0}
    for r in revenue_lines:
        if r.get("is_billed"):
            continue
        d = r.get("recognition_date")
        if not d:
            continue
        try:
            days = (today - datetime.fromisoformat(d).date()).days
        except Exception:
            continue
        amt = r.get("amount") or 0
        if days <= 30:
            buckets["0-30"] += amt
        elif days <= 60:
            buckets["31-60"] += amt
        elif days <= 90:
            buckets["61-90"] += amt
        else:
            buckets["90+"] += amt

    # Stage distribution
    stage_dist: Dict[str, int] = {}
    for p in projects:
        s = p.get("current_stage", "Pipeline")
        stage_dist[s] = stage_dist.get(s, 0) + 1

    # Sort projects by start_date desc
    projects.sort(key=lambda p: p.get("start_date") or "", reverse=True)

    return {
        "customer": cust,
        "totals": {
            "project_count": len(projects),
            "total_po": total_po,
            "total_revenue": total_revenue,
            "total_cost": total_cost,
            "total_margin": total_margin,
            "margin_pct": margin_pct,
        },
        "billing": {"recognized": recognized, "billed": billed, "unbilled": unbilled},
        "ageing_buckets": [{"bucket": k, "amount": v} for k, v in buckets.items()],
        "stage_distribution": [{"stage": k, "count": v} for k, v in stage_dist.items()],
        "projects": projects,
        "revenue_lines": revenue_lines,
        "cost_lines": cost_lines,
    }


# ============================================================
# DOCUMENT ATTACHMENTS (per project, with optional PDF parsing)
# ============================================================
UPLOAD_DIR = ROOT_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@api.get("/projects/{pid}/documents")
async def list_documents(pid: str, _: dict = Depends(get_current_user)):
    docs = await db.documents.find({"project_id": pid}, {"_id": 0, "storage_path": 0}).sort("uploaded_at", -1).to_list(500)
    return docs


@api.post("/projects/{pid}/documents")
async def upload_document(
    pid: str,
    file: UploadFile = File(...),
    name: str = Query(..., min_length=1, description="Document display name (required)"),
    parse: bool = Query(False),
    apply_extracted: bool = Query(False),
    user: dict = Depends(get_current_user),
):
    project = await db.projects.find_one({"id": pid}, {"_id": 0})
    if not project:
        raise HTTPException(404, "Project not found")

    if not (name or "").strip():
        raise HTTPException(400, "Document name is required")

    contents = await file.read()
    doc_id = gen_id()
    safe_name = (file.filename or "file").replace("/", "_")
    path = UPLOAD_DIR / f"{doc_id}__{safe_name}"
    with open(path, "wb") as f:
        f.write(contents)

    parsed: Optional[Dict[str, Any]] = None
    is_pdf = (file.content_type == "application/pdf") or safe_name.lower().endswith(".pdf")
    if parse and is_pdf:
        try:
            from pdf_parser import parse_customer_po
            parsed = parse_customer_po(contents)
        except Exception as e:
            parsed = {"error": str(e), "warnings": [str(e)]}

    doc = {
        "id": doc_id,
        "project_id": pid,
        "name": name.strip(),
        "file_name": safe_name,
        "size": len(contents),
        "content_type": file.content_type or "application/octet-stream",
        "storage_path": str(path),
        "parsed": parsed,
        "uploaded_by": user["email"],
        "uploaded_at": now_iso(),
    }
    await db.documents.insert_one(doc)
    await write_audit(db, entity_type="document", entity_id=doc_id, action="create",
                      user=user, field_changes={"project_id": pid, "file_name": safe_name, "parsed": bool(parsed)})

    # Optionally apply extracted fields to project
    applied = {}
    if apply_extracted and parsed:
        upd = {}
        if parsed.get("customer_po_number") and not project.get("customer_po_number"):
            upd["customer_po_number"] = parsed["customer_po_number"]
        if parsed.get("po_value") and not project.get("po_value"):
            upd["po_value"] = parsed["po_value"]
        if parsed.get("currency") and not project.get("currency"):
            upd["currency"] = parsed["currency"]
        if parsed.get("milestones"):
            upd["milestones"] = parsed["milestones"]
            upd["billing_type"] = "Milestone"
        if upd:
            upd["updated_at"] = now_iso()
            await db.projects.update_one({"id": pid}, {"$set": upd})
            applied = upd
            await write_audit(db, entity_type="project", entity_id=pid, action="auto_extracted",
                              user=user, field_changes=upd, reason=f"From document {safe_name}")

    doc.pop("_id", None)
    doc.pop("storage_path", None)
    return {"document": doc, "applied": applied}


@api.get("/documents/{did}/download")
async def download_document(did: str, _: dict = Depends(get_current_user)):
    d = await db.documents.find_one({"id": did})
    if not d:
        raise HTTPException(404, "Not found")
    p = Path(d["storage_path"])
    if not p.exists():
        raise HTTPException(404, "File missing")
    with open(p, "rb") as f:
        data = f.read()
    return StreamingResponse(io.BytesIO(data),
                             media_type=d.get("content_type") or "application/octet-stream",
                             headers={"Content-Disposition": f'attachment; filename="{d["file_name"]}"'})


@api.delete("/documents/{did}")
async def delete_document(did: str, user: dict = Depends(get_current_user)):
    d = await db.documents.find_one({"id": did})
    if not d:
        raise HTTPException(404, "Not found")
    try:
        Path(d["storage_path"]).unlink(missing_ok=True)
    except Exception:
        pass
    await db.documents.delete_one({"id": did})
    await write_audit(db, entity_type="document", entity_id=did, action="delete", user=user)
    return {"ok": True}


# ============================================================
# PIPELINE (Opportunity funnel — BRD 5 stages with Finance handoff)
# ============================================================
@api.get("/pipeline", response_model=List[PipelineOut])
async def list_pipeline(
    stage: Optional[str] = None,
    outcome: Optional[str] = None,
    search: Optional[str] = None,
    _: dict = Depends(get_current_user),
):
    q: Dict[str, Any] = {}
    if stage:
        q["current_stage"] = stage
    if outcome:
        q["outcome"] = outcome
    if search:
        q["$or"] = [
            {"opportunity_title": {"$regex": search, "$options": "i"}},
            {"customer_name": {"$regex": search, "$options": "i"}},
            {"bd_owner": {"$regex": search, "$options": "i"}},
        ]
    rows = await db.pipelines.find(q, {"_id": 0}).sort("updated_at", -1).to_list(2000)
    return rows


@api.get("/pipeline/summary")
async def pipeline_summary(_: dict = Depends(get_current_user)):
    rows = await db.pipelines.find({}, {"_id": 0}).to_list(2000)
    by_stage = {s: {"count": 0, "value": 0.0} for s in PIPELINE_STAGES}
    total_value = 0.0
    won_value = 0.0
    pending_handoff = 0
    for r in rows:
        s = r.get("current_stage") or "Prospecting"
        v = r.get("negotiated_value") or r.get("proposal_value") or r.get("expected_revenue") or 0
        by_stage.setdefault(s, {"count": 0, "value": 0.0})
        by_stage[s]["count"] += 1
        by_stage[s]["value"] += v
        total_value += v
        if r.get("outcome") == "Won":
            won_value += v
        if r.get("handoff_status") == "Pending Finance":
            pending_handoff += 1
    funnel = [{"stage": s, "count": by_stage[s]["count"], "value": by_stage[s]["value"]} for s in PIPELINE_STAGES]
    return {
        "total_opportunities": len(rows),
        "total_value": total_value,
        "won_value": won_value,
        "pending_handoff": pending_handoff,
        "funnel": funnel,
    }


@api.get("/pipeline/{pid}", response_model=PipelineOut)
async def get_pipeline(pid: str, _: dict = Depends(get_current_user)):
    row = await db.pipelines.find_one({"id": pid}, {"_id": 0})
    if not row:
        raise HTTPException(404, "Opportunity not found")
    return row


@api.post("/pipeline", response_model=PipelineOut)
async def create_pipeline(payload: PipelineIn, user: dict = Depends(get_current_user)):
    doc = payload.model_dump()
    doc["id"] = gen_id()
    # Auto-generate opportunity_id (e.g. OPP-2026-000123)
    if not doc.get("opportunity_id"):
        seq = await db.pipelines.count_documents({}) + 1
        year = datetime.now(timezone.utc).year
        doc["opportunity_id"] = f"OPP-{year}-{seq:06d}"
    doc["current_stage"] = "Prospecting"
    doc["handoff_status"] = "Not Applicable"
    doc["handoff_project_id"] = None
    doc["handoff_requested_by"] = None
    doc["handoff_requested_at"] = None
    doc["handoff_actioned_by"] = None
    doc["handoff_actioned_at"] = None
    doc["handoff_comment"] = ""
    doc["created_at"] = now_iso()
    doc["updated_at"] = now_iso()
    doc["created_by"] = user.get("email")
    await db.pipelines.insert_one(doc)
    await write_audit(db, entity_type="pipeline", entity_id=doc["id"], action="create", user=user,
                      field_changes={"opportunity_title": doc["opportunity_title"], "stage": "Prospecting"})
    doc.pop("_id", None)
    return doc


@api.put("/pipeline/{pid}", response_model=PipelineOut)
async def update_pipeline(pid: str, payload: PipelineIn, user: dict = Depends(get_current_user)):
    existing = await db.pipelines.find_one({"id": pid})
    if not existing:
        raise HTTPException(404, "Opportunity not found")
    updates = payload.model_dump()
    updates["updated_at"] = now_iso()
    await db.pipelines.update_one({"id": pid}, {"$set": updates})
    await write_audit(db, entity_type="pipeline", entity_id=pid, action="update", user=user, field_changes=updates)
    return await db.pipelines.find_one({"id": pid}, {"_id": 0})


@api.post("/pipeline/{pid}/advance", response_model=PipelineOut)
async def advance_pipeline(pid: str, payload: PipelineStageIn, user: dict = Depends(get_current_user)):
    existing = await db.pipelines.find_one({"id": pid})
    if not existing:
        raise HTTPException(404, "Opportunity not found")
    if payload.target_stage not in PIPELINE_STAGES:
        raise HTTPException(400, f"Invalid stage. Allowed: {PIPELINE_STAGES}")
    upd = {"current_stage": payload.target_stage, "updated_at": now_iso()}
    await db.pipelines.update_one({"id": pid}, {"$set": upd})
    await write_audit(db, entity_type="pipeline", entity_id=pid, action="stage_change", user=user,
                      field_changes={"from": existing.get("current_stage"), "to": payload.target_stage},
                      reason=payload.reason or "")
    return await db.pipelines.find_one({"id": pid}, {"_id": 0})


@api.post("/pipeline/{pid}/close", response_model=PipelineOut)
async def close_pipeline(
    pid: str,
    outcome: str = Query(..., description="Won, Lost, or Deferred"),
    reason: Optional[str] = Query("", description="Win/Loss/Deferred reason"),
    user: dict = Depends(get_current_user),
):
    if outcome not in ("Won", "Lost", "Deferred"):
        raise HTTPException(400, "outcome must be 'Won', 'Lost', or 'Deferred'")
    existing = await db.pipelines.find_one({"id": pid})
    if not existing:
        raise HTTPException(404, "Opportunity not found")

    now = now_iso()
    upd = {
        "current_stage": "Closed",
        "outcome": outcome,
        "closure_date": datetime.now(timezone.utc).date().isoformat(),
        "win_loss_reason": reason or existing.get("win_loss_reason", ""),
        "updated_at": now,
    }
    # On Won → create a pending-finance handoff (no Project yet until Finance approves)
    if outcome == "Won":
        upd["handoff_status"] = "Pending Finance"
        upd["handoff_requested_by"] = user.get("email")
        upd["handoff_requested_at"] = now

    await db.pipelines.update_one({"id": pid}, {"$set": upd})
    await write_audit(db, entity_type="pipeline", entity_id=pid, action="close", user=user,
                      field_changes={"outcome": outcome}, reason=reason or "")
    return await db.pipelines.find_one({"id": pid}, {"_id": 0})


@api.post("/pipeline/{pid}/approve-handoff", response_model=PipelineOut)
async def approve_handoff(
    pid: str,
    payload: PipelineHandoffAction,
    user: dict = Depends(require_role("finance", "admin")),
):
    existing = await db.pipelines.find_one({"id": pid})
    if not existing:
        raise HTTPException(404, "Opportunity not found")
    if existing.get("handoff_status") != "Pending Finance":
        raise HTTPException(400, f"Handoff is not pending (current: {existing.get('handoff_status')})")
    if existing.get("outcome") != "Won":
        raise HTTPException(400, "Only Won opportunities can be handed off")

    now = now_iso()
    if payload.action == "reject":
        await db.pipelines.update_one({"id": pid}, {"$set": {
            "handoff_status": "Rejected",
            "handoff_actioned_by": user.get("email"),
            "handoff_actioned_at": now,
            "handoff_comment": payload.comment or "",
            "updated_at": now,
        }})
        await write_audit(db, entity_type="pipeline", entity_id=pid, action="handoff_rejected",
                          user=user, reason=payload.comment or "")
        return await db.pipelines.find_one({"id": pid}, {"_id": 0})

    # Approved → create Project from pipeline (with category routing & flag copy)
    po_value = existing.get("final_commercial_value") or existing.get("negotiated_value") or existing.get("proposal_value") or existing.get("expected_revenue") or 0.0
    margin_pct = existing.get("estimated_margin_pct") or existing.get("expected_gross_margin_pct") or 0.0
    revenue_total = po_value
    cost_total = round(revenue_total * (1 - margin_pct / 100.0), 2) if margin_pct else 0.0
    margin = compute_margin(po_value, revenue_total, cost_total)
    is_change_request = (existing.get("opportunity_category") or "Project") == "Change Request"
    project_doc = {
        "id": gen_id(),
        "project_name": existing["opportunity_title"],
        "wbs_element": None,
        "customer_po_number": existing.get("customer_po_number"),
        "po_date": existing.get("contract_signed_date"),
        "start_date": existing.get("final_revenue_start_date") or existing.get("revenue_start_date"),
        "end_date": existing.get("final_go_live_date") or existing.get("expected_go_live_date"),
        "billing_type": "Milestone" if existing.get("billing_frequency") == "Milestone" else "Monthly",
        "milestones": existing.get("closed_milestones") or [],
        "customer_id": existing.get("customer_id"),
        "customer_name": existing.get("customer_name"),
        "description": existing.get("solution_scope") or existing.get("business_need") or "",
        "currency": existing.get("currency", "INR"),
        "po_value": po_value,
        "revenue_total": revenue_total,
        "cost_total": cost_total,
        "vendor_pos": [],
        "country": "India",
        "pnl_location": None, "pnl_region": None,
        "airport_adjacency": None, "project_grouping": None,
        "location": None,
        "category1": "Change Request" if is_change_request else "Project",
        "category2": existing.get("solution_line"),
        "business_category": existing.get("business_category") or "Non-GMR",
        "retro_pnl_tagging": None,
        "ownership_email": existing.get("bd_owner"),
        "stakeholders": existing.get("stakeholders") or [],
        "baseline_remarks": f"Auto-created from pipeline opportunity {existing.get('opportunity_id') or existing['id']}",
        "finance_remarks": payload.comment or "",
        "md_review_required": bool(existing.get("md_review_required")),
        "cfo_review_required": bool(existing.get("cfo_review_required")),
        "ceo_visibility": bool(existing.get("ceo_visibility")),
        "strategic_deal": bool(existing.get("strategic_deal")),
        "finance_spoc_email": existing.get("finance_contact"),
        "pipeline_id": existing["id"],
        "current_stage": "Deal P&L" if not is_change_request else "Deal P&L",
        "approval_status": "Not Required",
        "margin_total": margin["margin_total"],
        "margin_pct": margin["margin_pct"],
        "created_at": now, "updated_at": now,
        "created_by": user.get("email"),
    }
    await db.projects.insert_one(project_doc)
    project_doc.pop("_id", None)

    await db.pipelines.update_one({"id": pid}, {"$set": {
        "handoff_status": "Approved",
        "handoff_project_id": project_doc["id"],
        "handoff_actioned_by": user.get("email"),
        "handoff_actioned_at": now,
        "handoff_comment": payload.comment or "",
        "updated_at": now,
    }})
    await write_audit(db, entity_type="pipeline", entity_id=pid, action="handoff_approved",
                      user=user, field_changes={"project_id": project_doc["id"]},
                      reason=payload.comment or "")
    await write_audit(db, entity_type="project", entity_id=project_doc["id"], action="create_from_pipeline",
                      user=user, field_changes={"pipeline_id": pid})
    return await db.pipelines.find_one({"id": pid}, {"_id": 0})


@api.delete("/pipeline/{pid}")
async def delete_pipeline(pid: str, user: dict = Depends(require_role("admin"))):
    existing = await db.pipelines.find_one({"id": pid}, {"_id": 0})
    if not existing:
        raise HTTPException(404, "Opportunity not found")
    await db.pipelines.delete_one({"id": pid})
    await write_audit(db, entity_type="pipeline", entity_id=pid, action="delete", user=user)
    return {"ok": True}


# ============================================================
# Health
# ============================================================
@api.get("/")
async def root():
    return {"app": "CRacker Pro API", "status": "ok"}


# ============================================================
# SETTINGS (admin)  - FX rate INR per 1 USD, default currency
# ============================================================
DEFAULT_SETTINGS = {
    "id": "global",
    "inr_per_usd": 83.0,
    "default_currency": "INR",
    "updated_at": now_iso(),
    "updated_by": None,
}


@api.get("/settings")
async def get_settings(_: dict = Depends(get_current_user)):
    s = await db.settings.find_one({"id": "global"}, {"_id": 0})
    if not s:
        await db.settings.insert_one({**DEFAULT_SETTINGS})
        s = {**DEFAULT_SETTINGS}
    return s


@api.put("/settings")
async def update_settings(payload: dict, user: dict = Depends(require_role("admin"))):
    allowed = {"inr_per_usd", "default_currency"}
    upd = {k: v for k, v in payload.items() if k in allowed}
    if "inr_per_usd" in upd:
        try:
            upd["inr_per_usd"] = float(upd["inr_per_usd"])
            if upd["inr_per_usd"] <= 0:
                raise ValueError
        except Exception:
            raise HTTPException(400, "inr_per_usd must be a positive number")
    if "default_currency" in upd and upd["default_currency"] not in ("INR", "USD"):
        raise HTTPException(400, "default_currency must be INR or USD")
    upd["updated_at"] = now_iso()
    upd["updated_by"] = user["email"]
    await db.settings.update_one({"id": "global"}, {"$set": upd, "$setOnInsert": {"id": "global"}}, upsert=True)
    await write_audit(db, entity_type="settings", entity_id="global", action="update", user=user, field_changes=upd)
    s = await db.settings.find_one({"id": "global"}, {"_id": 0})
    return s


# ============================================================
# NOTIFICATIONS (admin) — Microsoft Graph email
# ============================================================
@api.get("/notifications/status")
async def notifications_status(_: dict = Depends(require_role("admin"))):
    """Show current notification configuration (no secrets)."""
    return mailer.status()


@api.post("/notifications/test")
async def notifications_test(payload: dict = None, user: dict = Depends(require_role("admin"))):
    """Send a test email to the configured recipient (or override via {to: ...})."""
    to = None
    if payload and isinstance(payload, dict) and payload.get("to"):
        to = [payload["to"]]
    subject, html = tpl_test_email()
    result = await mailer.send(subject=subject, html_body=html, to_recipients=to)
    return result


# Register router & CORS
app.include_router(api)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
