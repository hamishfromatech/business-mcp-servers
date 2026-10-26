"""
Training and Development (LMS) MCP Server
A FastMCP server for employee training, courses, enrollments,
completions, certifications, and skill tracking.
"""

from datetime import datetime, timedelta
from typing import Optional
from pathlib import Path
import json, os, threading, tempfile
from fastmcp import FastMCP

mcp = FastMCP(
    name="Training and Development (LMS)",
    instructions=(
        "Manages employee training, courses, enrollments, completions, "
        "certifications, and skill tracking. Provides course catalog, "
        "enrollment management, completion tracking, certification "
        "issuance, and skill gap analysis."
    ),
)

DATA_DIR = Path(os.environ.get("MCP_DATA_DIR") or (Path(__file__).parent / "data"))
DATA_FILE = DATA_DIR / "training.json"


def _load_data():
    if DATA_FILE.exists():
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"courses": [], " enrollments": [], "certifications": [],
            "skills": [], "next_id": 1}


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
        items.append({"name": p.name, "bytes": p.stat().st_size,
                       "modified_at": datetime.fromtimestamp(p.stat().st_mtime).isoformat()})
    return items


@mcp.tool
def restore_backup(name):
    source = DATA_DIR / "backups" / name
    if not source.exists():
        raise ValueError("Unknown backup: {name}")
    with _write_lock:
        _write_payload(source.read_text(encoding="utf-8"))
    return {"restored": name, "note": "Restart the MCP server to load the restored data"}


_data = _load_data()
courses = _data.get("courses", [])
enrollments = _data.get("enrollments", [])
certifications = _data.get("certifications", [])
skills = _data.get("skills", [])
_next_id = _data.get("next_id", 1)


def _save():
    _save_data({"courses": courses, "enrollments": enrollments,
                "certifications": certifications, "skills": skills, "next_id": _next_id})


def _get_next_id():
    global _next_id
    result = _next_id
    _next_id += 1
    return result


@mcp.tool
def add_course(title, category, duration_hours, certificate_template=None,
               author=None):
    course = {
        "id": _get_next_id(), "title": title, "category": category,
        "duration_hours": duration_hours, "certificate_template": certificate_template or "default",
        "author": author,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    }
    courses.append(course)
    _save()
    return course


@mcp.tool
def get_course(course_id):
    for i in courses:
        if i["id"] == course_id:
            return i
    return None


@mcp.tool
def search_courses(query):
    q = query.lower()
    results = [c for c in courses if q in c.get("title", "").lower() or q in c.get("category", "").lower()]
    return results


@mcp.tool
def list_courses():
    return sorted(courses, key=lambda c: c.get("title", ""))


@mcp.tool
def get_course_count():
    return len(courses)


@mcp.tool
def enroll_employee(employee_id, course_id, enrollment_status="active"):
    enrollment = {
        "id": _get_next_id(), "employee_id": employee_id,
        "course_id": course_id, "enrollment_status": enrollment_status,
        "start_date": datetime.now().isoformat(),
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    }
    enrollments.append(enrollment)
    _save()
    return enrollment


@mcp.tool
def get_enrollment(enrollment_id):
    for i in enrollments:
        if i["id"] == enrollment_id:
            return i
    return None


@mcp.tool
def search_enrollments(query):
    q = query.lower()
    results = []
    for e in enrollments:
        if q in e.get("employee_id", "").lower() or q in e.get("course_id", "").lower():
            results.append(e)
    return results


@mcp.tool
def update_enrollment(enrollment_id, **kwargs):
    for i, e in enumerate(enrollments):
        if e["id"] == enrollment_id:
            for k, v in kwargs.items():
                if v is not None:
                    e[k] = v
            e["updated_at"] = datetime.now().isoformat()
            _save()
            return e
    return None


@mcp.tool
def complete_enrollment(enrollment_id, completion_date=None, grade=None):
    for i, e in enumerate(enrollments):
        if e["id"] == enrollment_id:
            e["completion_date"] = completion_date or datetime.now().isoformat()
            e["status"] = "completed"
            e["grade"] = grade
            e["updated_at"] = datetime.now().isoformat()
            _save()
            return e
    return None


@mcp.tool
def delete_enrollment(enrollment_id):
    for i, e in enumerate(enrollments):
        if e["id"] == enrollment_id:
            del enrollments[i]
            _save()
            return True
    return False


@mcp.tool
def list_enrollments():
    return sorted(enrollments, key=lambda e: e.get("created_at", ""))


@mcp.tool
def get_enrollment_count():
    return len(enrollments)


@mcp.tool
def add_certification(employee_id, course_id, certification_type, issuer=None):
    cert = {
        "id": _get_next_id(), "employee_id": employee_id,
        "course_id": course_id, "certification_type": certification_type,
        "issuer": issuer,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    }
    certifications.append(cert)
    _save()
    return cert


@mcp.tool
def get_certification(cert_id):
    for i in certifications:
        if i["id"] == cert_id:
            return i
    return None


@mcp.tool
def list_certifications():
    return sorted(certifications, key=lambda c: c.get("created_at", ""))


@mcp.tool
def get_certification_count():
    return len(certifications)


@mcp.tool
def add_skill(employee_id, skill_name, level="beginner", category="technical"):
    skill = {
        "id": _get_next_id(), "employee_id": employee_id,
        "skill_name": skill_name, "level": level,
        "category": category,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    }
    skills.append(skill)
    _save()
    return skill


@mcp.tool
def get_skill(skill_id):
    for i in skills:
        if i["id"] == skill_id:
            return i
    return None


@mcp.tool
def list_skills():
    return sorted(skills, key=lambda s: s.get("skill_name", ""))


@mcp.tool
def get_skill_count():
    return len(skills)


@mcp.tool
def get_employee_skills(employee_id):
    return [s for s in skills if s.get("employee_id") == employee_id]


@mcp.tool
def get_skill_gap_analysis(employee_id):
    skills = get_employee_skills(employee_id)
    by_level = {"beginner": 0, "intermediate": 0, "advanced": 0}
    for s in skills:
        by_level[s.get("level", "beginner")] += 1
    return {"total_skills": len(skills), **by_level}


@mcp.resource("training://dashboard")
def dashboard_resource():
    lines = ["# Training Dashboard"]
    courses_count = len(courses)
    enrollments_count = len(enrollments)
    completed = sum(1 for e in enrollments if e.get("status") == "completed")
    lines.append("Courses: {} | Enrollments: {} | Completed: {}"
                 .format(courses_count, enrollments_count, completed))
    if not courses:
        lines.append("")
    return "\n".join(lines)


@mcp.resource("training://summary")
def summary_resource():
    lines = ["# Training Summary"]
    certs_count = len(certifications)
    skills_count = len(skills)
    lines.append("Certifications: {} | Skills: {}".format(certs_count, skills_count))
    if not certifications:
        lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    mcp.run()
