"""
Employee Directory MCP Server
A FastMCP server for managing employees with roles, departments,
org charts, onboarding, and offboarding lifecycle events.
"""

from datetime import datetime
from typing import Optional
from pathlib import Path
import json, os, threading, tempfile
from fastmcp import FastMCP

mcp = FastMCP(
    name="Employee Directory",
    instructions=(
        "Manages employees, roles, departments, positions, employment types"
        " (full-time, part-time, contractor, intern), onboarding/offboarding"
        " dates, and org chart relationships."
    ),
)

DATA_DIR = Path(os.environ.get("MCP_DATA_DIR") or (Path(__file__).parent / "data"))
DATA_FILE = DATA_DIR / "employees.json"


def _load_data():
    if DATA_FILE.exists():
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"employees": {}, "departments": {}, "roles": {}, "positions": {}, "next_id": 1}


_write_lock = threading.Lock()
_last_payload: Optional[str] = None
_pending_payload: Optional[str] = None
_flush_timer: Optional[threading.Timer] = None


def _write_payload(payload: str):
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


def _save_data(data: dict):
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
def flush_data() -> dict:
    _flush_pending()
    return {"flushed": True, "path": str(DATA_FILE)}


@mcp.tool
def backup_data() -> dict:
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
def list_backups() -> list:
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
    source = DATA_DIR / "backups" / name
    if not source.exists():
        raise ValueError(f"Unknown backup: {name}")
    with _write_lock:
        _write_payload(source.read_text(encoding="utf-8"))
    return {"restored": name, "note": "Restart the MCP server to load the restored data"}


_data = _load_data()
employees: dict = {int(k): v for k, v in _data.get("employees", {}).items()}
_departments: dict = {int(k): v for k, v in _data.get("departments", {}).items()}
_roles: dict = {k: v for k, v in _data.get("roles", {}).items()}
_positions: dict = {k: v for k, v in _data.get("positions", {}).items()}
_next_id = _data.get("next_id", 1)


def _save():
    _save_data({"employees": employees, "departments": _departments, "roles": _roles, "positions": _positions, "next_id": _next_id})


def _get_next_id():
    global _next_id
    result = _next_id
    _next_id += 1
    return result


def _search_employees(query: str):
    q = query.lower()
    results = []
    for e in employees.values():
        if any(q in str(v).lower() for k, v in e.items() if v is not None and k != "id"):
            results.append(e)
    return results


@mcp.tool
def add_employee(
    first_name: str, last_name: str, email: str,
    phone: Optional[str] = None, role_id: str = "",
    department_id: int = 1, position_id: Optional[str] = None,
    employment_type: str = "full-time", start_date: str = "",
    status: str = "active", manager_id: Optional[int] = None,
    notes: Optional[str] = None
):
    """Add a new employee."""
    emp = {
        "id": _get_next_id(),
        "first_name": first_name,
        "last_name": last_name,
        "email": email,
        "phone": phone,
        "role_id": role_id,
        "department_id": department_id,
        "position_id": position_id,
        "employment_type": employment_type,
        "start_date": start_date or datetime.now().isoformat(),
        "status": status,
        "manager_id": manager_id,
        "notes": notes,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    }
    employees[emp["id"]] = emp
    _save()
    return emp


@mcp.tool
def get_employee(employee_id: int):
    """Retrieve an employee by ID."""
    return employees.get(employee_id)


@mcp.tool
def search_employees(query: str):
    """Search employees by name, email, or role."""
    return _search_employees(query)


@mcp.tool
def update_employee(
    employee_id: int,
    first_name: Optional[str] = None, last_name: Optional[str] = None,
    email: Optional[str] = None, phone: Optional[str] = None,
    role_id: Optional[str] = None, department_id: Optional[int] = None,
    position_id: Optional[str] = None, employment_type: Optional[str] = None,
    start_date: Optional[str] = None, status: Optional[str] = None,
    manager_id: Optional[int] = None, notes: Optional[str] = None
):
    """Update an employee. Returns None if not found."""
    if employee_id not in employees:
        return None
    for k, v in [
        ("first_name", first_name), ("last_name", last_name), ("email", email),
        ("phone", phone), ("role_id", role_id), ("department_id", department_id),
        ("position_id", position_id), ("employment_type", employment_type),
        ("start_date", start_date), ("status", status), ("manager_id", manager_id),
        ("notes", notes)
    ]:
        if v is not None:
            employees[employee_id][k] = v
    employees[employee_id]["updated_at"] = datetime.now().isoformat()
    _save()
    return employees[employee_id]


@mcp.tool
def delete_employee(employee_id: int) -> bool:
    """Delete an employee by ID. Returns False if not found."""
    if employee_id not in employees:
        return False
    del employees[employee_id]
    _save()
    return True


@mcp.tool
def list_employees():
    """List all employees, sorted by name."""
    return sorted(employees.values(), key=lambda e: str(e.get("first_name", "")))


@mcp.tool
def get_employee_count() -> int:
    """Total employee count."""
    return len(employees)


@mcp.tool
def add_department(name: str, slug: str = "", manager_id: Optional[int] = None):
    """Add a new department."""
    slug = slug or name.lower().replace(" ", "-")
    dept = {
        "id": _get_next_id(),
        "name": name,
        "slug": slug,
        "manager_id": manager_id,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    }
    _departments[dept["id"]] = dept
    _save()
    return dept


@mcp.tool
def get_department(department_id: int):
    """Retrieve a department by ID."""
    return _departments.get(department_id)


@mcp.tool
def list_departments():
    """List all departments."""
    return sorted(_departments.values(), key=lambda d: d["name"])


@mcp.tool
def get_department_count() -> int:
    """Total department count."""
    return len(_departments)


@mcp.tool
def add_role(name: str, slug: str = "", department: Optional[str] = None):
    """Add a new role (title)."""
    slug = slug or name.lower().replace(" ", "-")
    role = {
        "id": _get_next_id(),
        "name": name,
        "slug": slug,
        "department": department,
        "created_at": datetime.now().isoformat(),
    }
    _roles[role["id"]] = role
    return role


@mcp.tool
def get_role(role_id: str):
    """Retrieve a role by ID."""
    return _roles.get(role_id)


@mcp.tool
def list_roles():
    """List all roles."""
    return sorted(_roles.values(), key=lambda r: r["name"])


@mcp.tool
def add_position(name: str, level: str = "", salary_band: Optional[str] = None):
    """Add a new position level."""
    pos = {
        "id": _get_next_id(),
        "name": name,
        "level": level,
        "salary_band": salary_band,
        "created_at": datetime.now().isoformat(),
    }
    _positions[pos["id"]] = pos
    return pos


@mcp.tool
def get_position(position_id: str):
    """Retrieve a position by ID."""
    return _positions.get(position_id)


@mcp.tool
def list_positions():
    """List all positions."""
    return sorted(_positions.values(), key=lambda p: p["name"])


@mcp.resource("employees://org-chart")
def org_chart_resource():
    """Organizational chart: departments with employees."""
    lines = ["# Organizational Chart\n"]
    for dept in sorted(_departments.values(), key=lambda d: d["name"]):
        dept_employees = [
            e for e in employees.values()
            if e.get("department_id") == dept["id"] and e.get("status") == "active"
        ]
        if dept_employees:
            lines.append(
                "\n## " + dept["name"] +
                " (Manager: " + ("Employee #" + str(dept.get("manager_id")) or "N/A") + ")"
            )
            for e in sorted(dept_employees, key=lambda x: str(x.get("first_name", ""))):
                lines.append(f"- **{e['first_name']} {e['last_name']}** ({e['email']}) — {e.get('role_id', 'N/A')}")
    if not any(employees.values()):
        lines.append("No employees in the directory.")
    return "\n".join(lines)


if __name__ == "__main__":
    mcp.run()
