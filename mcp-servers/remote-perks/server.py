"""
Remote Work Perks Manager MCP Server
A FastMCP server for remote work benefits, reimbursements, access requests,
and policy tracking.
"""

from datetime import datetime, timedelta
from typing import Optional
from pathlib import Path
import json, os, threading, tempfile
from fastmcp import FastMCP

mcp = FastMCP(
    name="Remote Work Perks Manager",
    instructions=(
        "Manages remote work benefits, tool approvals, reimbursements, "
        "access requests, and policy tracking. Supports approval "
        "workflows: submitted -> manager_review -> approved/rejected. "
        "Tracks policy compliance, eligible benefits, and reimbursement "
        "status across remote workers."
    ),
)

DATA_DIR = Path(os.environ.get("MCP_DATA_DIR") or (Path(__file__).parent / "data"))
DATA_FILE = DATA_DIR / "remote-perks.json"


def _load_data():
    if DATA_FILE.exists():
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "remote_workers": [],
        "benefits_plans": [],
        "benefit_enrollments": [],
        "reimbursement_requests": [],
        "access_requests": [],
        "access_grants": [],
        "policies": [],
        "next_id": 1,
    }


_write_lock = threading.Lock()
_last_payload = None
_pending_payload = None
_flush_timer = None


def _write_payload(payload):
    global _last_payload
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=str(DATA_DIR), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(payload)
        os.replace(tmp_path, DATA_FILE)
        _last_payload = payload
    except BaseException:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise


def _save_data(data):
    global _pending_payload, _flush_timer
    payload = json.dumps(data, indent=2, default=str)
    with _write_lock:
        if payload == _last_payload:
            return
        _pending_payload = payload
        if _flush_timer is not None:
            _flush_timer.cancel()
        _flush_timer = threading.Timer(0.001, _flush_pending)
        _flush_timer.daemon = True
        _flush_timer.start()


def _flush_pending():
    global _pending_payload
    with _write_lock:
        if _pending_payload is not None:
            p, _pending_payload = _pending_payload, None
            _write_payload(p)


@mcp.tool
def flush_data():
    _flush_pending()
    return {"flushed": True, "path": str(DATA_FILE)}


@mcp.tool
def backup_data():
    _flush_pending()
    if not DATA_FILE.exists():
        raise ValueError("No data file to back up yet")
    backup_dir = DATA_DIR / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    target = backup_dir / f"{DATA_FILE.stem}-{stamp}.json"
    import shutil
    shutil.copy2(DATA_FILE, target)
    return {"backup": str(target), "bytes": target.stat().st_size}


@mcp.tool
def list_backups():
    backup_dir = DATA_DIR / "backups"
    if not backup_dir.exists():
        return []
    items = []
    for p in sorted(backup_dir.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True):
        items.append(
            {
                "name": p.name,
                "bytes": p.stat().st_size,
                "modified_at": datetime.fromtimestamp(p.stat().st_mtime).isoformat(),
            }
        )
    return items


@mcp.tool
def restore_backup(name):
    source = DATA_DIR / "backups" / name
    if not source.exists():
        raise ValueError(f"Unknown backup: {name}")
    with _write_lock:
        _write_payload(source.read_text(encoding="utf-8"))
    return {"restored": name, "note": "Restart the MCP server to load the restored data"}


_data = _load_data()
remote_workers = _data.get("remote_workers", [])
benefits_plans = _data.get("benefits_plans", [])
benefit_enrollments = _data.get("benefit_enrollments", [])
reimbursement_requests = _data.get("reimbursement_requests", [])
access_requests = _data.get("access_requests", [])
access_grants = _data.get("access_grants", [])
policies = _data.get("policies", [])
_next_id = _data.get("next_id", 1)


def _save():
    _save_data(
        {
            "remote_workers": remote_workers,
            "benefits_plans": benefits_plans,
            "benefit_enrollments": benefit_enrollments,
            "reimbursement_requests": reimbursement_requests,
            "access_requests": access_requests,
            "access_grants": access_grants,
            "policies": policies,
            "next_id": _next_id,
        }
    )


def _get_next_id():
    global _next_id
    result = _next_id
    _next_id += 1
    return result


def _to_date(d):
    if not d:
        return None
    return datetime.fromisoformat(str(d)).date()


# ============================================================
# Remote Worker Management
# ============================================================
@mcp.tool
def add_remote_worker(
    employee_id: str,
    name: str,
    department: str,
    role: str,
    start_date: Optional[str] = None,
    location: Optional[str] = None,
    equipment_provided: bool = True,
    home_office_approved: bool = False,
    internet_allowance: Optional[float] = None,
    laptop_allowance: Optional[float] = None,
    monitor_allowance: Optional[float] = None,
    ergo_allowance: Optional[float] = None,
) -> dict:
    worker = {
        "id": employee_id,
        "employee_id": employee_id,
        "name": name,
        "department": department,
        "role": role,
        "start_date": start_date or datetime.now().isoformat(),
        "location": location,
        "equipment_provided": equipment_provided,
        "home_office_approved": home_office_approved,
        "internet_allowance": internet_allowance or 0.0,
        "laptop_allowance": laptop_allowance or 0.0,
        "monitor_allowance": monitor_allowance or 0.0,
        "ergo_allowance": ergo_allowance or 0.0,
        "registered_at": datetime.now().isoformat(),
        "status": "active",
    }
    remote_workers.append(worker)
    _save()
    return worker


@mcp.tool
def get_remote_worker(employee_id: str) -> Optional[dict]:
    for w in remote_workers:
        if w.get("employee_id") == employee_id:
            return w
    return None


@mcp.tool
def list_remote_workers(
    department: Optional[str] = None,
    status: Optional[str] = None,
) -> list:
    results = remote_workers[:]
    if department:
        results = [w for w in results if w.get("department") == department]
    if status:
        results = [w for w in results if w.get("status") == status]
    return results


@mcp.tool
def get_remote_worker_summary() -> dict:
    total = len(remote_workers)
    active = sum(1 for w in remote_workers if w.get("status") == "active")
    equipment_provided = sum(1 for w in remote_workers if w.get("equipment_provided"))
    home_approved = sum(1 for w in remote_workers if w.get("home_office_approved"))
    return {
        "total": total,
        "active": active,
        "inactive": total - active,
        "equipment_provided": equipment_provided,
        "home_office_approved": home_approved,
    }


# ============================================================
# Benefits Plans & Enrollments
# ============================================================
@mcp.tool
def add_benefit_plan(
    plan_id: str,
    plan_name: str,
    category: str,
    tier: str,
    description: str = "",
    effective_date: Optional[str] = None,
    ends_date: Optional[str] = None,
) -> dict:
    plan = {
        "id": plan_id,
        "plan_id": plan_id,
        "name": plan_name,
        "category": category,
        "tier": tier,
        "description": description,
        "effective_date": effective_date or datetime.now().isoformat(),
        "ends_date": ends_date,
        "created_at": datetime.now().isoformat(),
        "status": "active",
    }
    benefits_plans.append(plan)
    _save()
    return plan


@mcp.tool
def get_benefit_plan(plan_id: str) -> Optional[dict]:
    for p in benefits_plans:
        if p.get("id") == plan_id:
            return p
    return None


@mcp.tool
def add_benefit_enrollment(
    employee_id: str,
    plan_id: str,
    coverage_start: Optional[str] = None,
    coverage_end: Optional[str] = None,
    designation: str = "full",
    employer_acknowledged: bool = True,
    notes: Optional[str] = None,
) -> dict:
    enrollment = {
        "id": str(_get_next_id()),
        "employee_id": employee_id,
        "plan_id": plan_id,
        "coverage_start": coverage_start or datetime.now().isoformat(),
        "coverage_end": coverage_end or datetime.now().isoformat(),
        "designation": designation,
        "employer_acknowledged": employer_acknowledged,
        "notes": notes,
        "created_at": datetime.now().isoformat(),
        "status": "active",
    }
    benefit_enrollments.append(enrollment)
    _save()
    return enrollment


@mcp.tool
def get_benefit_enrollment(enrollment_id: str) -> Optional[dict]:
    for e in benefit_enrollments:
        if e.get("id") == enrollment_id:
            return e
    return None


@mcp.tool
def list_benefit_enrollments(
    employee_id: Optional[str] = None,
    status: Optional[str] = None,
) -> list:
    results = benefit_enrollments[:]
    if employee_id:
        results = [e for e in results if e.get("employee_id") == employee_id]
    if status:
        results = [e for e in results if e.get("status") == status]
    return results


# ============================================================
# Reimbursement Requests
# ============================================================
@mcp.tool
def submit_remote_reimbursement(
    request_id: Optional[str] = None,
    employee_id: str = "",
    title: str = "",
    description: str = "",
    category: str = "",
    amount: float = 0.0,
    date: Optional[str] = None,
    reimbursement_type: str = "onetime",
    receipt_attached: bool = False,
    reimbursement_code: Optional[str] = None,
    manager_id: int = 1,
    notes: Optional[str] = None,
) -> dict:
    rid = request_id or str(_get_next_id())
    request = {
        "request_id": rid,
        "id": rid,
        "employee_id": employee_id,
        "title": title,
        "description": description,
        "category": category,
        "amount": amount,
        "date": date or datetime.now().isoformat(),
        "reimbursement_type": reimbursement_type,
        "receipt_attached": receipt_attached,
        "reimbursement_code": reimbursement_code,
        "manager_id": manager_id,
        "approval_status": "submitted",
        "approved_by": None,
        "approved_at": None,
        "rejected_reason": None,
        "approved_amount": None,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    }
    reimbursement_requests.append(request)
    _save()
    return request


@mcp.tool
def get_reimbursement_request(request_id: str) -> Optional[dict]:
    for r in reimbursement_requests:
        if r.get("request_id") == request_id:
            return r
    return None


@mcp.tool
def list_reimbursement_requests(
    status: Optional[str] = None,
    employee_id: Optional[str] = None,
) -> list:
    results = reimbursement_requests[:]
    if status:
        results = [r for r in results if r.get("approval_status") == status]
    if employee_id:
        results = [r for r in results if r.get("employee_id") == employee_id]
    return results


@mcp.tool
def approve_reimbursement(request_id: str, reason: Optional[str] = None, approved_amount: Optional[float] = None):
    for r in reimbursement_requests:
        if r.get("request_id") == request_id:
            r["approval_status"] = "approved"
            r["approved_by"] = "manager"
            r["approved_at"] = datetime.now().isoformat()
            r["approved_amount"] = approved_amount if approved_amount is not None else r["amount"]
            r["rejected_reason"] = None
            r["updated_at"] = datetime.now().isoformat()
            _save()
            return {"approved": True, "request_id": request_id, "approved_amount": r["approved_amount"]}
    raise ValueError(f"Request not found: {request_id}")


@mcp.tool
def reject_reimbursement(request_id: str, reason: str):
    for r in reimbursement_requests:
        if r.get("request_id") == request_id:
            r["approval_status"] = "rejected"
            r["approved_by"] = "manager"
            r["approved_at"] = datetime.now().isoformat()
            r["rejected_reason"] = reason
            r["updated_at"] = datetime.now().isoformat()
            _save()
            return {"rejected": True, "request_id": request_id, "reason": reason}
    raise ValueError(f"Request not found: {request_id}")


# ============================================================
# Access Requests
# ============================================================
@mcp.tool
def submit_access_request(
    request_id: Optional[str] = None,
    employee_id: str = "",
    resource_type: str = "",
    resource_name: str = "",
    request_reason: str = "",
    priority: str = "normal",
    requested_by: str = "",
    manager_id: int = 1,
    effective_date: Optional[str] = None,
    expiry_date: Optional[str] = None,
    notes: Optional[str] = None,
) -> dict:
    rid = request_id or str(_get_next_id())
    request = {
        "request_id": rid,
        "id": rid,
        "employee_id": employee_id,
        "resource_type": resource_type,
        "resource_name": resource_name,
        "request_reason": request_reason,
        "priority": priority,
        "requested_by": requested_by,
        "manager_id": manager_id,
        "effective_date": effective_date or datetime.now().isoformat(),
        "expiry_date": expiry_date,
        "status": "pending",
        "notes": notes,
        "created_at": datetime.now().isoformat(),
        "approved_by": None,
        "approved_at": None,
        "approved_reason": None,
        "revoked_reason": None,
    }
    access_requests.append(request)
    _save()
    return request


@mcp.tool
def get_access_request(request_id: str) -> Optional[dict]:
    for r in access_requests:
        if r.get("request_id") == request_id:
            return r
    return None


@mcp.tool
def list_access_requests(
    status: Optional[str] = None,
    employee_id: Optional[str] = None,
    resource_type: Optional[str] = None,
) -> list:
    results = access_requests[:]
    if status:
        results = [r for r in results if r.get("status") == status]
    if employee_id:
        results = [r for r in results if r.get("employee_id") == employee_id]
    if resource_type:
        results = [r for r in results if r.get("resource_type") == resource_type]
    return results


@mcp.tool
def grant_access(
    request_id: str,
    resource_type: str,
    resource_name: str,
    effective_date: Optional[str] = None,
    expiry_date: Optional[str] = None,
    reason: Optional[str] = None,
) -> dict:
    request = None
    for r in access_requests:
        if r.get("request_id") == request_id:
            request = r
            break
    if not request:
        raise ValueError(f"Request not found: {request_id}")
    if request.get("resource_type") != resource_type or request.get("resource_name") != resource_name:
        raise ValueError("Grant resource does not match request")
    request["status"] = "granted"
    request["approved_by"] = "manager"
    request["approved_at"] = effective_date or datetime.now().isoformat()
    request["approved_reason"] = reason or request.get("request_reason", "")
    request["expiry_date"] = expiry_date or request.get("expiry_date")
    _save()
    return request


@mcp.tool
def revoke_access(request_id: str, reason: str, revoke_date: Optional[str] = None):
    for r in access_requests:
        if r.get("request_id") == request_id:
            r["status"] = "revoked"
            r["revoked_reason"] = reason
            r["approved_at"] = revoke_date or datetime.now().isoformat()
            r["updated_at"] = datetime.now().isoformat()
            _save()
            return {"revoked": True, "request_id": request_id, "reason": reason}
    raise ValueError(f"Request not found: {request_id}")


# ============================================================
# Policy Management
# ============================================================
@mcp.tool
def add_policy(
    policy_id: str,
    policy_name: str,
    category: str,
    version: str = "1.0",
    effective_date: Optional[str] = None,
    review_date: Optional[str] = None,
    superseded_by: Optional[str] = None,
    description: str = "",
) -> dict:
    policy = {
        "id": policy_id,
        "policy_id": policy_id,
        "name": policy_name,
        "category": category,
        "version": version,
        "effective_date": effective_date or datetime.now().isoformat(),
        "review_date": review_date or datetime.now().isoformat(),
        "superseded_by": superseded_by,
        "description": description,
        "status": "active",
        "created_at": datetime.now().isoformat(),
    }
    policies.append(policy)
    _save()
    return policy


@mcp.tool
def get_policy(policy_id: str) -> Optional[dict]:
    for p in policies:
        if p.get("id") == policy_id:
            return p
    return None


@mcp.tool
def list_policies(active_only: bool = True) -> list:
    results = policies[:]
    if active_only:
        results = [p for p in results if p.get("status") == "active"]
    return results


# ============================================================
# Remote Work Perks Analytics
# ============================================================
@mcp.tool
def get_reimbursement_summary() -> dict:
    total = sum(r.get("amount", 0) for r in reimbursement_requests)
    # Handle approved amounts that may be None
    def amount_value(r):
        found = r.get("approved_amount")
        if found is not None:
            return found
        return r.get("amount", 0)

    total_approved = sum(amount_value(r) for r in reimbursement_requests if r.get("approval_status") == "approved")
    total_pending = sum(r.get("amount", 0) for r in reimbursement_requests if r.get("approval_status") == "submitted")
    total_rejected = sum(r.get("amount", 0) for r in reimbursement_requests if r.get("approval_status") == "rejected")
    by_category = {}
    for r in reimbursement_requests:
        cat = r.get("category", "uncategorized")
        by_category[cat] = by_category.get(cat, 0) + r.get("amount", 0)
    return {
        "total_requested": total,
        "total_approved": total_approved,
        "total_pending": total_pending,
        "total_rejected": total_rejected,
        "by_category": by_category,
        "by_type": {
            "onetime": sum(r.get("amount", 0) for r in reimbursement_requests if r.get("reimbursement_type") == "onetime"),
            "monthly": sum(r.get("amount", 0) for r in reimbursement_requests if r.get("reimbursement_type") == "monthly"),
            "bulk": sum(r.get("amount", 0) for r in reimbursement_requests if r.get("reimbursement_type") == "bulk"),
        },
    }


@mcp.tool
def get_access_summary() -> dict:
    requests = access_requests
    granted = sum(1 for r in requests if r.get("status") == "granted")
    pending = sum(1 for r in requests if r.get("status") == "pending")
    revoked = sum(1 for r in requests if r.get("status") == "revoked")
    active_grants = []
    now = datetime.now().isoformat()
    for r in requests:
        if r.get("status") == "granted":
            expiry = r.get("expiry_date")
            if not expiry or expiry > now:
                active_grants.append(r)
    by_type = {}
    for r in requests:
        t = r.get("resource_type", "other")
        by_type[t] = by_type.get(t, 0) + 1
    return {
        "total_requests": len(requests),
        "granted": granted,
        "pending": pending,
        "revoked": revoked,
        "active_grants": len(active_grants),
        "by_resource_type": by_type,
    }


@mcp.tool
def get_benefit_enrollment_summary() -> dict:
    enrollments = benefit_enrollments
    active = sum(1 for e in enrollments if e.get("status") == "active")
    by_designation = {}
    for e in enrollments:
        d = e.get("designation", "other")
        by_designation[d] = by_designation.get(d, 0) + 1
    return {
        "total": len(enrollments),
        "active": active,
        "by_designation": by_designation,
    }


@mcp.tool
def get_policy_compliance_summary() -> dict:
    now = datetime.now().isoformat()
    active_policies = [p for p in policies if p.get("status") == "active" and p.get("effective_date") <= now]
    reviewed = sum(1 for p in active_policies if p.get("review_date") and p.get("review_date") <= now)
    return {
        "total_active_policies": len(active_policies),
        "reviewed": reviewed,
        "overdue_reviews": sum(1 for p in active_policies if p.get("review_date") and p.get("review_date") < now),
    }


if __name__ == "__main__":
    mcp.run()
