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
)
from services import (
    can_transition, write_audit, compute_margin, find_matching_rule, create_approval_request,
)
from excel_utils import (
    build_template_xlsx, parse_xlsx, build_export_xlsx, SCHEMAS,
)

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
            {"id": gen_id(), "employee_code": "E0001", "employee_name": "Rohit Kataria",
             "email_id": "carohitkataria@gmail.com", "designation": "Finance Manager",
             "department": "Business Finance", "l1_manager_email": admin_email,
             "location": "Delhi", "created_at": now_iso()},
            {"id": gen_id(), "employee_code": "E0002", "employee_name": "Priya Mehta",
             "email_id": "priya.mehta@crackerpro.com", "designation": "Sales Lead",
             "department": "Sales", "l1_manager_email": admin_email,
             "location": "Mumbai", "created_at": now_iso()},
        ])

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
    await db.users.update_one({"id": user_id}, {"$set": {"is_active": False}})
    await write_audit(db, entity_type="user", entity_id=user_id, action="deactivate", user=admin)
    return {"ok": True}


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
async def create_employee(payload: EmployeeIn, user: dict = Depends(get_current_user)):
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
async def update_employee(eid: str, payload: EmployeeIn, user: dict = Depends(get_current_user)):
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
            await create_approval_request(db, project, rule, target, user)
            await db.projects.update_one({"id": pid}, {"$set": {"approval_status": "Pending", "updated_at": now_iso()}})
            await write_audit(db, entity_type="project", entity_id=pid, action="approval_requested", user=user,
                              field_changes={"target_stage": target, "rule": rule.get("name")},
                              reason=payload.reason or "")
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
async def dashboard_summary(user: dict = Depends(get_current_user)):
    projects = await db.projects.find({}, {"_id": 0}).to_list(5000)
    stage_summary: Dict[str, Dict[str, float]] = {s: {"count": 0, "value": 0.0, "margin": 0.0} for s in STAGES}
    total_po, total_rev, total_cost = 0.0, 0.0, 0.0
    delayed_projects: List[dict] = []
    low_margin_projects: List[dict] = []
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
        # low margin: margin_pct < 15
        if (p.get("margin_pct") or 0) < 15:
            low_margin_projects.append({
                "id": p["id"], "project_name": p["project_name"], "margin_pct": p.get("margin_pct", 0),
                "po_value": p.get("po_value", 0), "customer_name": p.get("customer_name"),
                "current_stage": st,
            })

    # recognized but unbilled
    rev_lines = await db.revenue_lines.find({}, {"_id": 0}).to_list(5000)
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
    top_customers = sorted(cust_agg.values(), key=lambda x: -x["po_value"])[:5]

    # vendor exposure (sum of cost lines by supplier_name)
    cost_lines = await db.cost_lines.find({}, {"_id": 0}).to_list(5000)
    vendor_agg: Dict[str, float] = {}
    for c in cost_lines:
        sn = c.get("supplier_name") or "Unspecified"
        vendor_agg[sn] = vendor_agg.get(sn, 0) + (c.get("amount", 0) or 0)
    vendor_exposure = sorted(
        [{"supplier_name": k, "amount": v} for k, v in vendor_agg.items()],
        key=lambda x: -x["amount"],
    )[:5]

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

    return {
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
    parse: bool = Query(False),
    apply_extracted: bool = Query(False),
    user: dict = Depends(get_current_user),
):
    project = await db.projects.find_one({"id": pid}, {"_id": 0})
    if not project:
        raise HTTPException(404, "Project not found")

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


# Register router & CORS
app.include_router(api)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
