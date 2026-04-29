"""Pydantic models for CRacker Pro."""
from pydantic import BaseModel, Field, ConfigDict, EmailStr
from typing import List, Optional, Dict, Any, Literal
from datetime import datetime, timezone
import uuid


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def gen_id() -> str:
    return str(uuid.uuid4())


# ---------- USER ----------
ROLES = ["admin", "finance", "sales", "delivery", "leadership", "approver"]


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    name: str
    role: Literal["admin", "finance", "sales", "delivery", "leadership", "approver"]
    location: Optional[str] = None
    reporting_manager_email: Optional[str] = None


class UserUpdate(BaseModel):
    name: Optional[str] = None
    role: Optional[str] = None
    location: Optional[str] = None
    reporting_manager_email: Optional[str] = None
    is_active: Optional[bool] = None


class UserOut(BaseModel):
    id: str
    email: str
    name: str
    role: str
    location: Optional[str] = None
    reporting_manager_email: Optional[str] = None
    is_active: bool = True
    created_at: str


class LoginInput(BaseModel):
    email: EmailStr
    password: str


class PasswordChange(BaseModel):
    user_id: str
    new_password: str


# ---------- CUSTOMER ----------
class CustomerIn(BaseModel):
    customer_name: str
    sap_customer_code: Optional[str] = None
    balance_outstanding_sap: float = 0.0
    risk_notes: Optional[str] = ""
    contact_person: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    country: Optional[str] = None
    # Enriched profile (BRD)
    industry: Optional[str] = None
    sector: Optional[str] = None
    address_billing: Optional[str] = None
    address_shipping: Optional[str] = None
    secondary_contact_person: Optional[str] = None
    secondary_email: Optional[str] = None
    secondary_phone: Optional[str] = None
    website: Optional[str] = None
    account_owner_email: Optional[str] = None


class CustomerOut(CustomerIn):
    id: str
    created_at: str


# ---------- EMPLOYEE ----------
class EmployeeIn(BaseModel):
    employee_code: str
    employee_name: str
    email_id: EmailStr
    designation: Optional[str] = None
    department: Optional[str] = None
    l1_manager_email: Optional[str] = None
    location: Optional[str] = None


class EmployeeOut(EmployeeIn):
    id: str
    created_at: str


# ---------- SUPPLIER ----------
class SupplierIn(BaseModel):
    supplier_code: Optional[str] = None
    supplier_name: str
    contact_person: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None


class SupplierOut(SupplierIn):
    id: str
    created_at: str


# ---------- PROJECT ----------
STAGES = ["Pipeline", "Deal P&L", "Customer PO", "Operations", "Closure"]
APPROVAL_STATUSES = ["Not Required", "Pending", "Approved", "Rejected"]


class Milestone(BaseModel):
    milestone_name: str
    due_date: Optional[str] = None
    value: float = 0.0
    is_billed: bool = False


class VendorPO(BaseModel):
    vendor_po_number: str
    supplier_id: Optional[str] = None
    supplier_name: Optional[str] = None
    amount: float = 0.0


class ProjectIn(BaseModel):
    project_name: str
    wbs_element: Optional[str] = None
    customer_po_number: Optional[str] = None
    po_date: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    billing_type: Literal["Monthly", "Milestone"] = "Monthly"
    milestones: List[Milestone] = []
    customer_id: Optional[str] = None
    customer_name: Optional[str] = None
    description: Optional[str] = None
    currency: str = "INR"
    po_value: float = 0.0
    revenue_total: float = 0.0
    cost_total: float = 0.0
    vendor_pos: List[VendorPO] = []
    country: Optional[str] = None
    pnl_location: Optional[str] = None
    pnl_region: Optional[str] = None
    airport_adjacency: Optional[str] = None
    project_grouping: Optional[str] = None
    location: Optional[str] = None
    category1: Optional[str] = None
    category2: Optional[str] = None
    business_category: Optional[str] = "Non-GMR"  # GMR / Non-GMR
    retro_pnl_tagging: Optional[str] = None
    ownership_email: Optional[str] = None
    stakeholders: List[str] = []
    baseline_remarks: Optional[str] = ""
    finance_remarks: Optional[str] = ""


class ProjectOut(ProjectIn):
    id: str
    current_stage: str = "Pipeline"
    approval_status: str = "Not Required"
    margin_total: float = 0.0
    margin_pct: float = 0.0
    created_at: str
    updated_at: str
    created_by: Optional[str] = None


class StageTransitionIn(BaseModel):
    target_stage: Literal["Pipeline", "Deal P&L", "Customer PO", "Operations", "Closure"]
    reason: Optional[str] = ""


# ---------- REVENUE / COST ----------
class RevenueLineIn(BaseModel):
    project_id: Optional[str] = None
    revenue_code: Optional[str] = None
    description: Optional[str] = None
    amount: float
    recognition_date: Optional[str] = None
    billing_date: Optional[str] = None
    is_billed: bool = False


class RevenueLineOut(RevenueLineIn):
    id: str
    created_at: str


class CostLineIn(BaseModel):
    project_id: Optional[str] = None
    vendor_po_ref: Optional[str] = None
    supplier_id: Optional[str] = None
    supplier_name: Optional[str] = None
    description: Optional[str] = None
    amount: float
    expense_date: Optional[str] = None
    category: Optional[str] = None


class CostLineOut(CostLineIn):
    id: str
    created_at: str


# ---------- APPROVAL ----------
class ApprovalRuleIn(BaseModel):
    name: str
    business_category: Optional[str] = None  # GMR / Non-GMR / Any
    min_revenue: Optional[float] = None
    max_revenue: Optional[float] = None
    min_margin_pct: Optional[float] = None
    max_margin_pct: Optional[float] = None
    target_stage: Optional[str] = None  # which stage triggers
    approver_emails: List[str] = []
    approver_role: Optional[str] = None
    is_active: bool = True


class ApprovalRuleOut(ApprovalRuleIn):
    id: str
    created_at: str


class ApprovalActionIn(BaseModel):
    action: Literal["approve", "reject"]
    comment: Optional[str] = ""


class ApprovalRequestOut(BaseModel):
    id: str
    project_id: str
    project_name: str
    target_stage: str
    rule_id: Optional[str] = None
    rule_name: Optional[str] = None
    approver_email: Optional[str] = None
    approver_role: Optional[str] = None
    status: str  # Pending / Approved / Rejected
    comment: Optional[str] = ""
    requested_by: Optional[str] = None
    requested_at: str
    actioned_at: Optional[str] = None
    actioned_by: Optional[str] = None


# ---------- AUDIT ----------
class AuditLogOut(BaseModel):
    id: str
    entity_type: str
    entity_id: str
    action: str  # create/update/delete/stage_change/approval
    field_changes: Optional[Dict[str, Any]] = None
    user_email: Optional[str] = None
    user_id: Optional[str] = None
    reason: Optional[str] = ""
    timestamp: str


# ---------- UPLOAD LOG ----------
class UploadLogOut(BaseModel):
    id: str
    entity_type: str  # project / customer / employee / supplier / revenue / cost
    file_name: str
    total_rows: int
    success_rows: int
    failed_rows: int
    failures: List[Dict[str, Any]] = []
    uploaded_by: Optional[str] = None
    uploaded_at: str


# ---------- PIPELINE (Opportunity funnel, BRD 5 stages) ----------
PIPELINE_STAGES = [
    "Prospecting",
    "Active Discussion",
    "Proposal Submitted",
    "Evaluation/Negotiation",
    "Closed",
]
PIPELINE_OUTCOMES = ["Open", "Won", "Lost"]
HANDOFF_STATUSES = ["Not Applicable", "Pending Finance", "Approved", "Rejected"]


class PipelineIn(BaseModel):
    # Stage 1 — Prospecting
    opportunity_title: str
    customer_name: Optional[str] = None
    customer_id: Optional[str] = None
    bd_owner: Optional[str] = None
    expected_revenue: float = 0.0
    currency: str = "INR"
    source: Optional[str] = None  # referral / cold / RFP / repeat
    industry: Optional[str] = None

    # Stage 2 — Active Discussion
    solution_scope: Optional[str] = None
    expected_timeline: Optional[str] = None
    competitors: Optional[str] = None
    stakeholders: List[str] = []

    # Stage 3 — Proposal Submitted
    proposal_value: float = 0.0
    proposal_submitted_on: Optional[str] = None
    proposal_validity: Optional[str] = None
    proposal_notes: Optional[str] = ""

    # Stage 4 — Evaluation / Negotiation
    negotiated_value: float = 0.0
    estimated_margin_pct: float = 0.0
    expected_decision_date: Optional[str] = None
    negotiation_notes: Optional[str] = ""

    # Stage 5 — Closed
    outcome: Literal["Open", "Won", "Lost"] = "Open"
    closure_date: Optional[str] = None
    win_loss_reason: Optional[str] = ""

    # Management flags
    business_category: Optional[str] = "Non-GMR"  # GMR / Non-GMR
    priority: Optional[str] = "Medium"  # High / Medium / Low
    remarks: Optional[str] = ""


class PipelineOut(PipelineIn):
    id: str
    current_stage: str = "Prospecting"
    handoff_status: str = "Not Applicable"  # Not Applicable / Pending Finance / Approved / Rejected
    handoff_project_id: Optional[str] = None
    handoff_requested_by: Optional[str] = None
    handoff_requested_at: Optional[str] = None
    handoff_actioned_by: Optional[str] = None
    handoff_actioned_at: Optional[str] = None
    handoff_comment: Optional[str] = ""
    created_at: str
    updated_at: str
    created_by: Optional[str] = None


class PipelineStageIn(BaseModel):
    target_stage: Literal[
        "Prospecting", "Active Discussion", "Proposal Submitted",
        "Evaluation/Negotiation", "Closed",
    ]
    reason: Optional[str] = ""


class PipelineHandoffAction(BaseModel):
    action: Literal["approve", "reject"]
    comment: Optional[str] = ""
