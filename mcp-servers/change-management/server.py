"""
CHANGE MANAGEMENT TRACKER MCP SERVER
A FastMCP server for IT change request management: change requests,
approvals, deployments, rollback tracking, notified parties, and status tracking.
"""

from datetime import datetime, timedelta
from pathlib import Path
import json, os, shutil, atexit, tempfile, threading
from enum import Enum
from typing import Optional
from fastmcp import FastMCP
from pydantic import BaseModel, BeforeValidator

# JSON-stringified list params
def _coerce_json_list(value):
    if isinstance(value, str):
        try:
            p = json.loads(value)
            return p if isinstance(p, list) else [p]
        except:
            return [value]
    return value

StrList = BeforeValidator(_coerce_json_list)
IntList = BeforeValidator(_coerce_json_list)

# Main MCP setup
mcp = FastMCP(
    name="Change Management Tracker",
    instructions="Manages IT change requests: submission, approval workflows, "
                  "deployment tracking, rollback handling, notified parties, and status.",
)

# Enums
class ChangeRequestStatus(str, Enum):
    DRAFT = "draft"
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    ON_HOLD = "on_hold"
    APPROVED = "approved"
    REJECTED = "rejected"
    DEPLOYED = "deployed"
    RETRACTED = "retracted"
    DEPRECATED = "deprecated"
    CLOSED = "closed"
    ROLLED_BACK = "rolled_back"

class ApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    WAIVED = "waived"

class DeploymentStatus(str, Enum):
    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ROLLED_BACK = "rolled_back"
    FAILED = "failed"

class ChangeCategory(str, Enum):
    STANDARD = "standard"
    NORMAL = "normal"
    EXCEPTION = "exception"
    EMERGENCY = "emergency"

class ChangeImpact(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class ApprovalAuthority(str, Enum):
    INDIVIDUAL = "individual"
    TEAM = "team"
    MULTI_LEVEL = "multi_level"

# Data models
class AnyChangeRequest(BaseModel):
    id: int
    reference: str
    title: str
    description: str
    change_category: str
    impact: str
    change_type: str
    proposed_by: Optional[str] = None
    proposed_by_role: Optional[str] = None
    submit_date: str
    status: str
    approval_authority: str
    required_approvers: list = []
    approving_roles: Optional[list] = None
    priority: str = "medium"
    business_justification: Optional[str] = None
    risk_assessment: Optional[str] = None
    risk_rating: Optional[str] = None
    business_continuity_plan: Optional[str] = None
    rollback_plan: Optional[str] = None
    tested: Optional[bool] = None
    testing_notes: Optional[str] = None
    scheduled_start: Optional[str] = None
    scheduled_end: Optional[str] = None
    windows: Optional[list] = None
    affected_systems: Optional[list] = None
    affected_users: Optional[list] = None
    communicated_to: Optional[list] = None
    tickets: Optional[list] = None
    metadata: Optional[dict] = None
    created_at: str
    updated_at: str
    submitted_at: Optional[str] = None
    closed_at: Optional[str] = None
    closed_by: Optional[str] = None
    closed_notes: Optional[str] = None
    approved_by: list = []
    rejected_by: list = []
    waived_by: list = []
    approvals: list = []
    deployments: list = []
    rollbacks: list = []

class Approval(BaseModel):
    id: int
    change_id: int
    approver_id: str
    approver_name: str
    approver_role: str
    approval_status: str
    decision_notes: Optional[str] = None
    submitted_at: str

class Deployment(BaseModel):
    id: int
    change_id: int
    change_ref: str
    deployment_number: str
    deployment_type: str
    environment: str
    state: str
    planned_by: Optional[str] = None
    planned_date: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    deployer: Optional[str] = None
    deployer_role: Optional[str] = None
    changelog: Optional[list] = None
    confirmation_signoff: Optional[str] = None
    rollback_plan: Optional[str] = None
    rollback_executed: bool = False
    rollback_notes: Optional[str] = None
    rollback_completed_at: Optional[str] = None
    rollback_reason: Optional[str] = None
    notes: Optional[str] = None
    tokens: Optional[dict] = None
    metadata: Optional[dict] = None
    created_at: str

class Rollback(BaseModel):
    id: int
    deployment_id: Optional[int] = None
    change_id: Optional[int] = None
    triggered_by: str
    trigger_method: str
    reason: str
    description: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    status: str = "in_progress"
    steps_taken: Optional[list] = None
    verification_notes: Optional[str] = None
    metadata: Optional[dict] = None

class NotifiedParty(BaseModel):
    id: int
    party_identifier: str
    party_type: str
    party_name: Optional[str] = None
    notified: bool = False
    notified_at: Optional[str] = None
    notification_count: int = 0
    notifications: Optional[list] = None

class ChangeMetric(BaseModel):
    id: int
    metric_name: str
    metric_value: float
    unit: str
    category: str
    timeframe: Optional[str] = None
    notes: Optional[str] = None
    created_at: str

# Data persistence
DATA_DIR = Path(os.environ.get("MCP_DATA_DIR") or (Path(__file__).parent / "data"))
DATA_FILE = DATA_DIR / "change_management.json"


def _load_data():
    if DATA_FILE.exists():
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"change_requests": {}, "approvals": {}, "deployments": {},
            "rollbacks": {}, "notified_parties": {}, "change_metrics": {},
            "next_request_id": 1, "next_approval_id": 1, "next_deployment_id": 1,
            "next_rollback_id": 1, "next_party_id": 1, "next_metric_id": 1}


_write_lock = threading.Lock()
_last_payload = None
_pending_payload = None
_flush_timer = None
_WRITE_DEBOUNCE_MS = int(os.environ.get("MCP_WRITE_DEBOUNCE_MS", "0") or 0)


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


def _flush_pending():
    global _pending_payload
    with _write_lock:
        if _pending_payload is not None:
            payload, _pending_payload = _pending_payload, None
            _write_payload(payload)


def _save_data(data):
    global _pending_payload, _flush_timer
    payload = json.dumps(data, indent=2, default=str)
    if _WRITE_DEBOUNCE_MS <= 0:
        with _write_lock:
            if payload != _last_payload:
                _write_payload(payload)
        return
    with _write_lock:
        if payload == _last_payload:
            return
        _pending_payload = payload
        if _flush_timer is not None:
            _flush_timer.cancel()
        _flush_timer = threading.Timer(_WRITE_DEBOUNCE_MS / 1000.0, _flush_pending)
        _flush_timer.daemon = True
        _flush_timer.start()


atexit.register(_flush_pending)


@mcp.tool
def flush_data():
    """Flush any deferred writes to disk immediately."""
    _flush_pending()
    return {"flushed": True, "path": str(DATA_FILE), "debounce_ms": _WRITE_DEBOUNCE_MS}


@mcp.tool
def backup_data():
    """Copy the current data file into data/backups/ with a timestamp."""
    _flush_pending()
    if not DATA_FILE.exists():
        raise ValueError("No data file to back up yet")
    backup_dir = DATA_DIR / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    target = backup_dir / f"{DATA_FILE.stem}-{stamp}.json"
    shutil.copy2(DATA_FILE, target)
    return {"backup": str(target), "bytes": target.stat().st_size}


@mcp.tool
def list_backups():
    """List available data backups, newest first."""
    backup_dir = DATA_DIR / "backups"
    if not backup_dir.exists():
        return []
    items = []
    for path in sorted(backup_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        items.append({
            "name": path.name,
            "bytes": path.stat().st_size,
            "modified_at": datetime.fromtimestamp(path.stat().st_mtime).isoformat(),
        })
    return items


@mcp.tool
def restore_backup(name: str) -> dict:
    """Restore a backup, replacing current data. Restart the server to load it."""
    source = DATA_DIR / "backups" / name
    if not source.exists():
        raise ValueError(f"Unknown backup: {name}")
    with _write_lock:
        _write_payload(source.read_text(encoding="utf-8"))
    return {"restored": name, "note": "Restart the MCP server to load the restored data"}


# Initialize data
_data = _load_data()
change_requests: dict = {int(k): v for k, v in _data.get("change_requests", {}).items()}
approvals: dict = {int(k): v for k, v in _data.get("approvals", {}).items()}
deployments: dict = {int(k): v for k, v in _data.get("deployments", {}).items()}
rollbacks: dict = {int(k): v for k, v in _data.get("rollbacks", {}).items()}
notified_parties: dict = {int(k): v for k, v in _data.get("notified_parties", {}).items()}
change_metrics: dict = {int(k): v for k, v in _data.get("change_metrics", {}).items()}

_next_request_id = _data.get("next_request_id", 1)
_next_approval_id = _data.get("next_approval_id", 1)
_next_deployment_id = _data.get("next_deployment_id", 1)
_next_rollback_id = _data.get("next_rollback_id", 1)
_next_party_id = _data.get("next_party_id", 1)
_next_metric_id = _data.get("next_metric_id", 1)


def _save():
    """Save current state to disk."""
    _save_data({
        "change_requests": change_requests,
        "approvals": approvals,
        "deployments": deployments,
        "rollbacks": rollbacks,
        "notified_parties": notified_parties,
        "change_metrics": change_metrics,
        "next_request_id": _next_request_id,
        "next_approval_id": _next_approval_id,
        "next_deployment_id": _next_deployment_id,
        "next_rollback_id": _next_rollback_id,
        "next_party_id": _next_party_id,
        "next_metric_id": _next_metric_id,
    })


def _next_id(kind: str) -> int:
    """Allocate the next integer id by kind."""
    global _next_request_id, _next_approval_id, _next_deployment_id, \
           _next_rollback_id, _next_party_id, _next_metric_id
    mapping = {
        "change_request": _next_request_id,
        "approval": _next_approval_id,
        "deployment": _next_deployment_id,
        "rollback": _next_rollback_id,
        "party": _next_party_id,
        "metric": _next_metric_id,
    }
    value = mapping.get(kind)
    mapping[kind] = value + 1
    return value


def _now() -> str:
    return datetime.now().isoformat()


def _add_days(date_str: str, days: int) -> str:
    d = datetime.fromisoformat(date_str).date()
    return (d + timedelta(days=days)).isoformat()


def _is_within_range(d, start, end):
    """Check if date d is within [start, end] range."""
    if d is None:
        return True
    d = datetime.fromisoformat(str(d)).date()
    start_date = datetime.fromisoformat(str(start)).date() if start else None
    end_date = datetime.fromisoformat(str(end)).date() if end else None
    if start_date and d < start_date:
        return False
    if end_date and d > end_date:
        return False
    return True

# === CHANGE REQUEST TOOLS ===

@mcp.tool
def create_change_request(
    reference: str,
    title: str,
    description: str,
    change_category: str = ChangeCategory.STANDARD.value,
    impact: str = ChangeImpact.MEDIUM.value,
    change_type: str = "maintenance",
    proposed_by: Optional[str] = None,
    proposed_by_role: Optional[str] = None,
    priority: str = "medium",
    business_justification: Optional[str] = None,
    risk_assessment: Optional[str] = None,
    risk_rating: Optional[str] = None,
    business_continuity_plan: Optional[str] = None,
    rollback_plan: Optional[str] = None,
    tested: Optional[bool] = None,
    testing_notes: Optional[str] = None,
    scheduled_start: Optional[str] = None,
    scheduled_end: Optional[str] = None,
    windows: Optional[list] = None,
    affected_systems: Optional[list] = None,
    affected_users: Optional[list] = None,
    communicated_to: Optional[list] = None,
    tickets: Optional[list] = None,
    metadata: Optional[dict] = None,
    approval_authority: str = ApprovalAuthority.INDIVIDUAL.value,
    required_approvers: Optional[list] = None,
    approving_roles: Optional[list] = None,
) -> AnyChangeRequest:
    """Create a new change request.

    Args:
        reference: Change request reference (e.g., CHANGE-2025-001)
        title: Change request title
        description: Detailed description
        change_category: standard | normal | exception | emergency
        impact: low | medium | high | critical
        change_type: maintenance | upgrade | replacement | addition | security
        proposed_by: Submitter name
        proposed_by_role: Submitter role
        priority: low | medium | high | critical
        business_justification: Business justification
        risk_assessment: Risk assessment summary
        risk_rating: Risk rating
        business_continuity_plan: Business continuity plan
        rollback_plan: Rollback plan description
        tested: Whether change has been tested
        testing_notes: Testing notes
        scheduled_start: Scheduled start date
        scheduled_end: Scheduled end date
        windows: Maintenance window definitions
        affected_systems: List of affected systems
        affected_users: List of affected users
        communicated_to: Notified parties (emails/roles)
        tickets: Related ticket IDs
        metadata: Additional metadata
        approval_authority: individual | team | multi_level
        required_approvers: List of approver identifiers
        approving_roles: Required approval roles

    Returns:
        The created change request
    """
    rid = _next_id("change_request")
    ws = windows or []
    ts = tickets or []
    ras = required_approvers or []
    ar = approving_roles or []

    cr = {
        "id": rid, "reference": reference, "title": title, "description": description,
        "change_category": change_category, "impact": impact, "change_type": change_type,
        "proposed_by": proposed_by, "proposed_by_role": proposed_by_role,
        "submit_date": _now(), "status": ChangeRequestStatus.DRAFT.value,
        "approval_authority": approval_authority, "required_approvers": ras,
        "approving_roles": ar, "priority": priority,
        "business_justification": business_justification, "risk_assessment": risk_assessment,
        "risk_rating": risk_rating, "business_continuity_plan": business_continuity_plan,
        "rollback_plan": rollback_plan, "tested": tested, "testing_notes": testing_notes,
        "scheduled_start": scheduled_start, "scheduled_end": scheduled_end,
        "windows": windows if windows else [], "affected_systems": affected_systems,
        "affected_users": affected_users, "communicated_to": communicated_to,
        "tickets": ts, "metadata": metadata,
        "submitted_at": None, "closed_at": None, "closed_by": None, "closed_notes": None,
        "approved_by": [], "rejected_by": [], "waived_by": [], "approvals": [],
        "deployments": [], "rollbacks": [],
    }
    change_requests[str(rid)] = cr
    _save()
    return AnyChangeRequest(**cr)


@mcp.tool
def get_change_request(change_id: int) -> Optional[AnyChangeRequest]:
    """Get a change request by ID.

    Args:
        change_id: The change request ID

    Returns:
        The change request or None if not found
    """
    rc = change_requests.get(change_id)
    return None if rc is None else AnyChangeRequest(**rc)


@mcp.tool
def list_change_requests(
    status: Optional[str] = None,
    category: Optional[str] = None,
    priority: Optional[str] = None,
    impact: Optional[str] = None,
    proposed_by: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> list:
    """List change requests with optional filters.

    Args:
        status: Filter by status
        category: Filter by category
        priority: Filter by priority
        impact: Filter by impact level
        proposed_by: Filter by submitter
        limit: Maximum number of results
        offset: Number of results to skip

    Returns:
        List of matching change requests
    """
    result = list(change_requests.values())

    if status:
        result = [r for r in result if r.get("status") == status]
    if category:
        result = [r for r in result if r.get("change_category") == category]
    if priority:
        result = [r for r in result if r.get("priority") == priority]
    if impact:
        result = [r for r in result if r.get("impact") == impact]
    if proposed_by:
        result = [r for r in result if proposed_by.lower() in (r.get("proposed_by") or "").lower()]

    result.sort(key=lambda r: r.get("created_at", ""), reverse=True)
    return [AnyChangeRequest(**r) for r in result[offset:offset + limit]]


@mcp.tool
def update_change_request(
    change_id: int,
    reference: Optional[str] = None,
    title: Optional[str] = None,
    description: Optional[str] = None,
    change_category: Optional[str] = None,
    impact: Optional[str] = None,
    change_type: Optional[str] = None,
    priority: Optional[str] = None,
    business_justification: Optional[str] = None,
    risk_assessment: Optional[str] = None,
    risk_rating: Optional[str] = None,
    business_continuity_plan: Optional[str] = None,
    rollback_plan: Optional[str] = None,
    tested: Optional[bool] = None,
    testing_notes: Optional[str] = None,
    scheduled_start: Optional[str] = None,
    scheduled_end: Optional[str] = None,
    windows: Optional[list] = None,
    affected_systems: Optional[list] = None,
    affected_users: Optional[list] = None,
    communicated_to: Optional[list] = None,
    tickets: Optional[list] = None,
    metadata: Optional[dict] = None,
    status: Optional[str] = None,
    submitted_at: Optional[str] = None,
    approved_by: Optional[list] = None,
) -> Optional[AnyChangeRequest]:
    """Update a change request.

    Args:
        change_id: The change request ID
        Any other optional field to update

    Returns:
        The updated change request or None if not found
    """
    if change_id not in change_requests:
        return None

    rc = change_requests[change_id]
    for k, v in locals().items():
        if v is not None and k != "update_change_request":
            rc[k] = v

    # Handle status-based submit
    if status == ChangeRequestStatus.OPEN.value and submitted_at is not None:
        rc["submitted_at"] = submitted_at

    if status is None and submitted_at is None:
        rc["updated_at"] = _now()

    _save()
    return AnyChangeRequest(**rc)


@mcp.tool
def delete_change_request(change_id: int, soft: bool = True) -> bool:
    """Delete a change request (soft delete by default).

    Args:
        change_id: The change request ID
        soft: If True, mark as closed/deprecated; if False, hard delete

    Returns:
        True if deleted, False if not found
    """
    if change_id not in change_requests:
        return False
    if not soft:
        del change_requests[change_id]
        _save()
        return True
    change_requests[change_id]["status"] = ChangeRequestStatus.CLOSED.value
    change_requests[change_id]["closed_at"] = _now()
    change_requests[change_id]["closed_by"] = "system"
    change_requests[change_id]["closed_notes"] = "Soft deleted"
    _save()
    return True

# === APPROVAL TOOLS ===

@mcp.tool
def submit_change_request(change_id: int, approver_id: str, decision_notes: Optional[str] = None) -> Optional[AnyChangeRequest]:
    """Submit a change request for approval by an approver.

    Args:
        change_id: The change request ID
        approver_id: The approver's identifier
        decision_notes: Optional initial notes

    Returns:
        The updated change request or None if not found
    """
    if change_id not in change_requests:
        return None
    rc = change_requests[change_id]
    if rc.get("submitted_at"):
        return rc

    rc["submitted_at"] = _now()
    rc["updated_at"] = _now()

    aid = _next_id("approval")
    ap = {
        "id": aid, "change_id": change_id, "approver_id": approver_id,
        "approver_name": approver_id, "approver_role": "approver",
        "approval_status": ApprovalStatus.PENDING.value,
        "decision_notes": decision_notes, "submitted_at": _now(),
    }
    approvals[str(aid)] = ap
    rc.setdefault("approvals", []).append(ap)
    _save()
    return AnyChangeRequest(**rc)


@mcp.tool
def approve_change_request(
    change_id: int,
    approver_id: str,
    approval_status: str = ApprovalStatus.APPROVED.value,
    decision_notes: Optional[str] = None,
) -> Optional[AnyChangeRequest]:
    """Approve, reject, or waive a change request.

    Args:
        change_id: The change request ID
        approver_id: The approver's identifier
        approval_status: pending | approved | rejected | waived
        decision_notes: Reason for the decision

    Returns:
        The updated change request or None if not found
    """
    if change_id not in change_requests:
        return None
    rc = change_requests[change_id]

    if approval_status == ApprovalStatus.PENDING.value:
        raise ValueError("PENDING is not a valid decision status; use APPROVED, REJECTED, or WAIVED instead")

    aid = _next_id("approval")
    ap = {
        "id": aid, "change_id": change_id, "approver_id": approver_id,
        "approver_name": approver_id, "approver_role": "approver",
        "approval_status": approval_status, "decision_notes": decision_notes,
        "submitted_at": _now(),
    }
    approvals[str(aid)] = ap
    rc.setdefault("approvals", []).append(ap)

    # Update approved_by/rejected_by/waived_by lists
    if approval_status == ApprovalStatus.APPROVED.value:
        rc.setdefault("approved_by", []).append(approver_id)
        # Status transition: approved -> approved (ready for testing) or in_progress
        if rc.get("tested") is None:
            rc["status"] = ChangeRequestStatus.APPROVED.value
            rc.setdefault("tested", True)
            rc["updated_at"] = _now()
        else:
            rc["status"] = ChangeRequestStatus.IN_PROGRESS.value
    elif approval_status == ApprovalStatus.REJECTED.value:
        if approver_id not in rc.get("rejected_by", []):
            rc["rejected_by"].append(approver_id)
        rc["status"] = ChangeRequestStatus.REJECTED.value
        rc["updated_at"] = _now()
    elif approval_status == ApprovalStatus.WAIVED.value:
        if approver_id not in rc.get("waived_by", []):
            rc["waived_by"].append(approver_id)
        rc["status"] = ChangeRequestStatus.APPROVED.value
        rc["updated_at"] = _now()

    _save()
    return AnyChangeRequest(**rc)


@mcp.tool
def reject_change_request(change_id: int, approver_id: str, decision_notes: Optional[str] = None) -> Optional[AnyChangeRequest]:
    """Reject a change request.

    Args:
        change_id: The change request ID
        approver_id: The approver's identifier
        decision_notes: Reason for rejection

    Returns:
        The updated change request or None if not found
    """
    return approve_change_request(change_id, approver_id, ApprovalStatus.REJECTED.value, decision_notes)


@mcp.tool
def waive_change_request(change_id: int, approver_id: str, decision_notes: Optional[str] = None) -> Optional[AnyChangeRequest]:
    """Waive approval for a change request.

    Args:
        change_id: The change request ID
        approver_id: The approver's identifier
        decision_notes: Reason for the waiver

    Returns:
        The updated change request or None if not found
    """
    return approve_change_request(change_id, approver_id, ApprovalStatus.WAIVED.value, decision_notes)


@mcp.tool
def get_approval_history(change_id: int) -> list:
    """Get the approval history for a change request.

    Args:
        change_id: The change request ID

    Returns:
        List of approvals
    """
    if change_id not in change_requests:
        return []
    approvs = [a for a in approvals.values() if a.get("change_id") == change_id]
    approvs.sort(key=lambda a: a.get("submitted_at", ""), reverse=True)
    return [Approval(**a) for a in approvs]

# === DEPLOYMENT TOOLS ===

@mcp.tool
def create_deployment(
    change_id: int,
    deployment_number: str,
    deployment_type: str = DeploymentStatus.PLANNAED.value,
    environment: str = "production",
    planned_by: Optional[str] = None,
    planned_date: Optional[str] = None,
    deployer: Optional[str] = None,
    deployer_role: Optional[str] = None,
    changelog: Optional[list] = None,
    confirmation_signoff: Optional[str] = None,
    rollback_plan: Optional[str] = None,
    rollback_executed: bool = False,
    rollback_reason: Optional[str] = None,
) -> Deployment:
    """Create a deployment record for a change.

    Args:
        change_id: The change request ID
        deployment_number: e.g., DEP-2025-001
        deployment_type: production | staging | nonprod
        environment: Deployment environment
        planned_by: Who planned it
        planned_date: Planned date
        deployer: Who deployed it
        deployer_role: Role of deployer
        changelog: Change log entries
        confirmation_signoff: Signoff confirmation
        rollback_plan: Rollback plan description
        rollback_executed: Whether rollback was executed
        rollback_reason: Reason for rollback

    Returns:
        The created deployment
    """
    did = _next_id("deployment")
    cr = change_requests.get(change_id)
    ep = {
        "id": did, "change_id": change_id, "change_ref": cr.get("reference", "") if cr else "",
        "deployment_number": deployment_number, "deployment_type": deployment_type,
        "environment": environment, "state": DeploymentStatus.PLANNAED.value,
        "planned_by": planned_by, "planned_date": planned_date,
        "started_at": None, "completed_at": None, "deployer": deployer,
        "deployer_role": deployer_role, "changelog": changelog or [],
        "confirmation_signoff": confirmation_signoff, "rollback_plan": rollback_plan,
        "rollback_executed": rollback_executed, "rollback_notes": None,
        "rollback_completed_at": None, "rollback_reason": rollback_reason,
        "notes": None, "tokens": None, "metadata": None, "created_at": _now(),
    }
    deployments[str(did)] = ep
    cr = change_requests.get(change_id)
    if cr:
        cr.setdefault("deployments", []).append(ep)
    _save()
    return Deployment(**ep)


@mcp.tool
def get_deployment(deployment_id: int) -> Optional[Deployment]:
    """Get a deployment by ID.

    Args:
        deployment_id: The deployment ID

    Returns:
        The deployment or None if not found
    """
    ep = deployments.get(deployment_id)
    return None if ep is None else Deployment(**ep)


@mcp.tool
def list_deployments(
    change_id: Optional[int] = None,
    type: Optional[str] = None,
    environment: Optional[str] = None,
    limit: int = 20,
) -> list:
    """List deployments with optional filters.

    Args:
        change_id: Filter by change request
        type: Filter by deployment type
        environment: Filter by environment
        limit: Maximum number of results

    Returns:
        List of matching deployments
    """
    if not change_id:
        result = list(deployments.values())
    else:
        result = [x for x in deployments.values() if x.get("change_id") == change_id]

    if type:
        result = [x for x in result if x.get("deployment_type") == type]
    if environment:
        result = [x for x in result if x.get("environment") == environment]
    result.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return [Deployment(**x) for x in result[:limit]]


@mcp.tool
def update_deployment(
    deployment_id: int,
    state: Optional[str] = None,
    started_at: Optional[str] = None,
    completed_at: Optional[str] = None,
    deployer: Optional[str] = None,
    deployer_role: Optional[str] = None,
    changelog: Optional[list] = None,
    confirmation_signoff: Optional[str] = None,
    rollback_plan: Optional[str] = None,
    rollback_executed: Optional[bool] = None,
    rollback_reason: Optional[str] = None,
    notes: Optional[str] = None,
) -> Optional[Deployment]:
    """Update a deployment.

    Args:
        deployment_id: The deployment ID
        Any other optional field

    Returns:
        The updated deployment or None if not found
    """
    if deployment_id not in deployments:
        return None

    ep = deployments[deployment_id]
    for k, v in locals().items():
        if v is not None and k != "update_deployment":
            ep[k] = v

    # Handle state-based changes
    if state is not None:
        ep["state"] = state
        if state == DeploymentStatus.IN_PROGRESS.value and not ep.get("started_at"):
            ep["started_at"] = _now()
        if state == DeploymentStatus.COMPLETED.value:
            ep["completed_at"] = _now()

    if completed_at is not None:
        ep["completed_at"] = completed_at

    ep["updated_at"] = _now()
    _save()
    return Deployment(**ep)


@mcp.tool
def rollback_deployment(deployment_id: int, rollback_reason: str, triggered_by: str = "manual") -> Optional[Deployment]:
    """Roll back a deployment.

    Args:
        deployment_id: The deployment ID
        rollback_reason: Reason for the rollback
        triggered_by: Who triggered the rollback

    Returns:
        The updated deployment or None if not found
    """
    if deployment_id not in deployments:
        return None

    ep = deployments[deployment_id]
    ep["state"] = DeploymentStatus.ROLLED_BACK.value
    ep["rollback_executed"] = True
    ep["rollback_reason"] = rollback_reason
    ep["rollback_completed_at"] = _now()
    ep["updated_at"] = _now()

    # Update change request status
    cr = change_requests.get(ep.get("change_id"))
    if cr:
        curr = cr.get("deployments", "deployments", [])
        for dep in curr:
            if dep.get("id") == deployment_id:
                if dep.get("state") == DeploymentStatus.ROLLED_BACK.value:
                    cr["status"] = ChangeRequestStatus.ROLLED_BACK.value
                cr.setdefault("rollbacks", []).append({
                    "deployment_id": deployment_id,
                    "deployment_number": dep.get("deployment_number", ""),
                    "status": ChangeRequestStatus.ROLLED_BACK.value,
                    "trigger_method": triggered_by,
                    "reason": rollback_reason,
                    "rollback_completed_at": _now(),
                })
                break

    _save()
    return Deployment(**ep)

# === ROLLBACK TOOLS ===

@mcp.tool
def create_rollback(
    change_id: Optional[int] = None,
    deployment_id: Optional[int] = None,
    triggered_by: str = "manual",
    trigger_method: str = "manual",
    reason: str = "",
    description: Optional[str] = None,
    started_at: Optional[str] = None,
    status: str = "in_progress",
    steps_taken: Optional[list] = None,
    verification_notes: Optional[str] = None,
) -> Rollback:
    """Create a rollback record.

    Args:
        change_id: The change request ID
        deployment_id: The deployment ID
        triggered_by: Who triggered the rollback
        trigger_method: manual | automated | detection
        reason: Reason for rollback
        description: Detailed description
        started_at: When rollback started
        status: in_progress | completed | failed
        steps_taken: Steps taken during rollback
        verification_notes: Post-rollback verification notes

    Returns:
        The created rollback
    """
    rid = _next_id("rollback")
    rb = {
        "id": rid, "deployment_id": deployment_id, "change_id": change_id,
        "triggered_by": triggered_by, "trigger_method": trigger_method, "reason": reason,
        "description": description, "started_at": started_at, "completed_at": None,
        "status": status, "steps_taken": steps_taken or [],
        "verification_notes": verification_notes, "metadata": None,
    }
    rollbacks[str(rid)] = rb
    _save()
    return Rollback(**rb)


@mcp.tool
def get_rollback(rollback_id: int) -> Optional[Rollback]:
    """Get a rollback by ID.

    Args:
        rollback_id: The rollback ID

    Returns:
        The rollback or None if not found
    """
    rb = rollbacks.get(rollback_id)
    return None if rb is None else Rollback(**rb)


@mcp.tool
def complete_rollback(rollback_id: int, verification_notes: str, completed_by: Optional[str] = None) -> Optional[Rollback]:
    """Complete a rollback.

    Args:
        rollback_id: The rollback ID
        verification_notes: Verification notes
        completed_by: Who completed it

    Returns:
        The completed rollback or None if not found
    """
    if rollback_id not in rollbacks:
        return None

    rb = rollbacks[rollback_id]
    if rb.get("status") in ("completed", "failed"):
        raise ValueError("Rollback must be in_progress to complete")

    rb["status"] = "completed"
    rb["completed_at"] = _now()
    rb["verification_notes"] = verification_notes
    rb["metadata"] = {"completed_by": completed_by}
    _save()
    return Rollback(**rb)


# === NOTIFIED PARTY TOOLS ===

@mcp.tool
def add_notified_party(party_identifier: str, party_type: str, party_name: Optional[str] = None) -> NotifiedParty:
    """Add a party to notify about a change/deployment.

    Args:
        party_identifier: Email, role, or user identifier
        party_type: email | approver | reporter | subscriber
        party_name: Party name

    Returns:
        The created party
    """
    pid = _next_id("party")
    np = {
        "id": pid, "party_identifier": party_identifier, "party_type": party_type,
        "party_name": party_name, "notified": False, "notified_at": None,
        "notification_count": 0, "notifications": None,
    }
    notified_parties[str(pid)] = np
    _save()
    return NotifiedParty(**np)


@mcp.tool
def get_notified_party(party_id: int) -> Optional[NotifiedParty]:
    """Get a notified party by ID.

    Args:
        party_id: The party ID

    Returns:
        The party or None if not found
    """
    np = notified_parties.get(party_id)
    return None if np is None else NotifiedParty(**np)


@mcp.tool
def mark_notified(party_id: int, method: str = "email") -> NotifiedParty:
    """Mark a party as notified.

    Args:
        party_id: The party ID
        method: Notification method

    Returns:
        The updated party
    """
    if party_id not in notified_parties:
        raise ValueError(f"Party {party_id} not found")

    np = notified_parties[party_id]
    np["notified"] = True
    np["notified_at"] = _now()
    np["notification_count"] = np.get("notification_count", 0) + 1
    np.setdefault("notifications", []).append({
        "method": method, "timestamp": _now(), "status": "sent",
    })
    _save()
    return NotifiedParty(**np)


# === CHANGE METRIC TOOLS ===

@mcp.tool
def post_change_metric(
    metric_name: str,
    metric_value: float,
    unit: str,
    category: str,
    timeframe: Optional[str] = None,
    notes: Optional[str] = None,
) -> ChangeMetric:
    """Post a change metric for analytics.

    Args:
        metric_name: Name of the metric
        metric_value: Numeric value
        unit: Unit of measurement
        category: Category - by_category | by_priority | by_status | by_system | trend
        timeframe: Timeframe for the metric
        notes: Additional notes

    Returns:
        The created metric
    """
    mid = _next_id("metric")
    mt = {
        "id": mid, "metric_name": metric_name, "metric_value": metric_value,
        "unit": unit, "category": category, "timeframe": timeframe,
        "notes": notes, "created_at": _now(),
    }
    change_metrics[str(mid)] = mt
    _save()
    return ChangeMetric(**mt)

# === ANALYTICS TOOLS ===

@mcp.tool
def get_change_summary() -> dict:
    """Get a summary of change requests."""
    total = len(change_requests)
    by_status = {}
    by_category = {}
    by_priority = {}
    by_impact = {}
    by_system = {}
    in_progress = 0

    for rc in change_requests.values():
        s = rc.get("status", "unknown")
        cat = rc.get("change_category", "unknown")
        pri = rc.get("priority", "medium")
        imp = rc.get("impact", "medium")
        sys = rc.get("affected_systems", "unknown")

        by_status[s] = by_status.get(s, 0) + 1
        by_category[cat] = by_category.get(cat, 0) + 1
        by_priority[pri] = by_priority.get(pri, 0) + 1
        by_impact[imp] = by_impact.get(imp, 0) + 1
        if sys and isinstance(sys, list):
            for s in sys:
                by_system[s] = by_system.get(s, 0) + 1
        elif sys:
            by_system[sys] = by_system.get(sys, 0) + 1

        if s == ChangeRequestStatus.IN_PROGRESS.value:
            in_progress += 1

    return {
        "total_requests": total,
        "in_progress": in_progress,
        "by_status": by_status,
        "by_category": by_category,
        "by_priority": by_priority,
        "by_impact": by_impact,
        "by_system": by_system,
        "open_and_pending": by_status.get(ChangeRequestStatus.OPEN.value, 0) + by_status.get("draft", 0),
        "deployed_and_closed": by_status.get(ChangeRequestStatus.DEPLOYED.value, 0) + by_status.get(ChangeRequestStatus.CLOSED.value, 0),
    }


@mcp.tool
def get_change_status_dashboard() -> dict:
    """Get a dashboard of change request status."""
    status_counts = {}
    for rc in change_requests.values():
        s = rc.get("status", "unknown")
        status_counts[s] = status_counts.get(s, 0) + 1

    # Calculate approval rates
    with_approvals = [r for r in change_requests.values() if r.get("approvals")]
    approved_count = sum(1 for r in with_approvals if "approved_by" in r and r["approved_by"])
    rejected_count = sum(1 for r in with_approvals if "rejected_by" in r and r["rejected_by"])

    return {
        "total": len(change_requests),
        "by_status": status_counts,
        "approved_count": approved_count,
        "rejected_count": rejected_count,
        "pending_approvals": len(with_approvals) - approved_count - rejected_count,
    }


@mcp.tool
def get_change_statistics() -> dict:
    """Get comprehensive change statistics."""
    summary = get_change_summary()
    dashboard = get_change_status_dashboard()

    # Trend analysis
    recent = sorted(
        [r for r in change_requests.values() if r.get("created_at")],
        key=lambda r: r.get("created_at", ""),
        reverse=True,
    )[:30]
    monthly = {}
    for rc in recent:
        date = rc.get("created_at", "")[:7]
        monthly[date] = monthly.get(date, 0) + 1

    return {
        "summary": summary,
        "dashboard": dashboard,
        "recent_activity": monthly,
        "total_deployments": len(deployments),
        "total_rollbacks": len(rollbacks),
        "total_notified_parties": len(notified_parties),
    }


# === RESOURCES ===

@mcp.resource("change://dashboard")
def dashboard() -> str:
    """Change dashboard as formatted text."""
    lines = ["# Change Management Dashboard"]
    lines.append("")

    summary = get_change_summary()
    dashboard = get_change_status_dashboard()

    lines.append(f"- **Total Requests:** {summary['total_requests']}")
    lines.append(f"- **In Progress:** {summary['in_progress']}")
    lines.append(f"- **Open/Draft:** {summary['open_and_pending']}")
    lines.append(f"- **Deployed/Closed:** {summary['deployed_and_closed']}")
    lines.append("")

    lines.append("## Status Distribution")
    for status, count in sorted(summary["by_status"].items(), key=lambda x: -x[1]):
        bar = "█" * min(count, 20)
        lines.append(f"- {status}: {bar} {count}")
    lines.append("")

    lines.append("## Approval Summary")
    lines.append(f"- Approved: {dashboard['approved_count']}")
    lines.append(f"- Rejected: {dashboard['rejected_count']}")
    lines.append(f"- Pending: {dashboard['pending_approvals']}")
    lines.append("")

    if change_requests:
        recent = sorted(
            change_requests.values(), key=lambda r: r.get("created_at", ""), reverse=True
        )[:10]
        lines.append("## Recent Changes")
        for rc in recent:
            lines.append(f"- **{rc.get('title', 'Untitled')}** (#{rc.get('reference', '')}) - {rc.get('status')}")
        lines.append("")

    return "\n".join(lines)


@mcp.resource("change://requests")
def requests() -> str:
    """All change requests as formatted text."""
    if not change_requests:
        return "No change requests yet."

    lines = ["# Change Requests", ""]
    for rc in sorted(change_requests.values(), key=lambda r: r.get("created_at", ""), reverse=True)[:20]:
        lines.append(f"## {rc.get('title', 'Untitled')} (#{rc.get('reference', '')})")
        lines.append(f"- Status: {rc.get('status')}")
        lines.append(f"- Category: {rc.get('change_category')}")
        lines.append(f"- Impact: {rc.get('impact')}")
        lines.append(f"- Priority: {rc.get('priority')}")
        lines.append(f"- Proposed by: {rc.get('proposed_by', 'N/A')}")
        lines.append(f"- Description: {rc.get('description', 'No description')}")
        if rc.get("approved_by"):
            lines.append(f"- Approved by: {', '.join(rc['approved_by'])}")
        if rc.get("rejected_by"):
            lines.append(f"- Rejected by: {', '.join(rc['rejected_by'])}")
        lines.append("---")
        lines.append("")
    return "\n".join(lines)


@mcp.resource("change://approvals")
def approvals() -> str:
    """Approval history as formatted text."""
    lines = ["# Approval History", ""]
    if not approvals:
        return "No approval records yet."
    for ap in sorted(approvals.values(), key=lambda x: x.get("submitted_at", ""), reverse=True)[:20]:
        lines.append(f"## Approval #{ap.get('id')}")
        lines.append(f"- Change ID: {ap.get('change_id')}")
        lines.append(f"- Approver: {ap.get('approver_name')} ({ap.get('approver_role')})")
        lines.append(f"- Status: {ap.get('approval_status')}")
        if ap.get("decision_notes"):
            lines.append(f"- Notes: {ap.get('decision_notes')}")
        lines.append(f"- Submitted: {ap.get('submitted_at')}")
        lines.append("")
    return "\n".join(lines)


@mcp.resource("change://deployments")
def deployments() -> str:
    """Deployments as formatted text."""
    lines = ["# Deployments", ""]
    if not deployments:
        return "No deployments yet."
    for ep in sorted(deployments.values(), key=lambda x: x.get("created_at", ""), reverse=True)[:20]:
        lines.append(f"## {ep.get('deployment_number')}")
        lines.append(f"- Change ID: {ep.get('change_id')}")
        lines.append(f"- Environment: {ep.get('environment')}")
        lines.append(f"- Type: {ep.get('deployment_type')}")
        lines.append(f"- State: {ep.get('state')}")
        if ep.get("deployer"):
            lines.append(f"- Deployer: {ep.get('deployer')}")
        if ep.get("completed_at"):
            lines.append(f"- Completed: {ep.get('completed_at')}")
        if ep.get("notes"):
            lines.append(f"- Notes: {ep.get('notes')}")
        lines.append("")
    return "\n".join(lines)


@mcp.resource("change://rollbacks")
def rollbacks() -> str:
    """Rollbacks as formatted text."""
    lines = ["# Rollbacks", ""]
    if not rollbacks:
        return "No rollbacks yet."
    for rb in sorted(rollbacks.values(), key=lambda x: x.get("completed_at", ""), reverse=True)[:20]:
        lines.append(f"## Rollback #{rb.get('id')}")
        lines.append(f"- Deployment/Change: {rb.get('deployment_id')} / {rb.get('change_id')}")
        lines.append(f"- Triggered by: {rb.get('triggered_by')}")
        lines.append(f"- Method: {rb.get('trigger_method')}")
        lines.append(f"- Status: {rb.get('status')}")
        if rb.get("reason"):
            lines.append(f"- Reason: {rb.get('reason')}")
        if rb.get("verification_notes"):
            lines.append(f"- Verification: {rb.get('verification_notes')[:100]}")
        lines.append("")
    return "\n".join(lines)


@mcp.resource("change://parties")
def parties() -> str:
    """Notified parties as formatted text."""
    lines = ["# Notified Parties", ""]
    if not notified_parties:
        return "No notified parties yet."
    for np in sorted(notified_parties.values(), key=lambda x: x.get("notified_at", ""), reverse=True)[:20]:
        lines.append(f"## Party #{np.get('id')}")
        lines.append(f"- Identifier: {np.get('party_identifier')}")
        lines.append(f"- Type: {np.get('party_type')}")
        lines.append(f"- Name: {np.get('party_name')}")
        lines.append(f"- Notified: {'Yes' if np.get('notified') else 'No'}")
        lines.append("")
    return "\n".join(lines)


@mcp.resource("change://metrics")
def metrics() -> str:
    """Change metrics as formatted text."""
    lines = ["# Change Metrics", ""]
    if not change_metrics:
        return "No metrics recorded yet."
    for mt in sorted(change_metrics.values(), key=lambda x: x.get("created_at", ""), reverse=True)[:20]:
        lines.append(f"- **{mt.get('metric_name')}**: {mt.get('metric_value')} {mt.get('unit')}")
        lines.append(f"  Category: {mt.get('category')}")
        if mt.get("timeframe"):
            lines.append(f"  Timeframe: {mt.get('timeframe')}")
        if mt.get("notes"):
            lines.append(f"  Notes: {mt.get('notes')}")
        lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    mcp.run()
