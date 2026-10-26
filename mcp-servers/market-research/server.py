"""
Market Research & Customer Feedback MCP Server
A FastMCP server for surveys, questions, responses, NPS, feedback categories,
and analytics.
"""

from datetime import datetime, date, timedelta
from typing import Optional
from pathlib import Path
from enum import Enum
import json
import os
import shutil
import atexit
import tempfile
import threading
from pydantic import BaseModel
from fastmcp import FastMCP

mcp = FastMCP(
    name="Market Research",
    instructions=(
        "A market research server for managing surveys, questions, responses, "
        "NPS scores, feedback categories, and analytics."
    ),
)

# Enums
class QuestionType(str, Enum):
    SINGLE_CHOICE = "single_choice"
    MULTIPLE_CHOICE = "multiple_choice"
    RATING = "rating"
    NPS = "nps"
    LIKERT = "likert"
    TEXT = "text"
    TEXT_AREA = "text_area"
    RATING_LIKERT = "rating_likert"
    DATE = "date"
    SLIDER = "slider"


class ResponseStatus(str, Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    DISCARD = "discard"
    ANOMALY = "anomaly"


class FeedbackCategory(str, Enum):
    PRODUCT = "product"
    SUPPORT = "support"
    PRICING = "pricing"
    FEATURE_REQUEST = "feature_request"
    BUG_REPORT = "bug_report"
    GENERAL = "general"
    ONBOARDING = "onboarding"
    USER_EXPERIENCE = "user_experience"
    COMMUNICATION = "communication"
    REMOTE = "remote"
    OTHER = "other"


class NPSPromoter(str, Enum):
    PROMOTER = "promoter"
    PASSIVE = "passive"
    DETRACTOR = "detractor"


# Data Models
class QuestionOption(BaseModel):
    value: str
    display_text: str = ""
    weight: float = 1.0
    required: bool = False

    @property
    def is_default(self) -> bool:
        return self.weight == 1.0 and self.required


class Question(BaseModel):
    id: int
    survey_id: int
    question_text: str
    question_type: QuestionType
    is_required: bool = False
    options: Optional[list] = None
    position: int = 0
    is_active: bool = True
    weight: float = 1.0
    created_at: str
    updated_at: str


class FeedbackCategoryModel(BaseModel):
    id: int
    name: str
    slug: str
    description: Optional[str] = None
    color: str = "#6B7280"
    is_active: bool = True
    created_at: str


class SurveyResponse(BaseModel):
    id: int
    survey_id: int
    respondent_id: str
    respondent_email: Optional[str] = None
    category_id: Optional[int] = None
    answers: dict
    nps_raw_score: Optional[int] = None
    is_follow_up: bool = False
    follow_up_notes: Optional[str] = None
    status: str = ResponseStatus.SUBMITTED.value
    submitted_at: Optional[str] = None
    submitted_date: Optional[str] = None
    created_at: str
    updated_at: str


# Data Persistence
mcp_data_dir = Path(os.environ.get("MCP_DATA_DIR") or (Path(__file__).parent / "data"))
data_file = mcp_data_dir / "market_research.json"

_write_lock = threading.Lock()
_last_payload: Optional[str] = None
_pending_payload: Optional[str] = None
_flush_timer: Optional[threading.Timer] = None
_WRITE_DEBOUNCE_MS = int(os.environ.get("MCP_WRITE_DEBOUNCE_MS", "0") or "0")


def _load_data() -> dict:
    if data_file.exists():
        with open(data_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "surveys": {}, "questions": {}, "responses": {}, "categories": {},
        "next_survey_id": 1, "next_question_id": 1, "next_response_id": 1,
        "next_category_id": 1,
    }


def _write_payload(payload: str) -> None:
    global _last_payload
    mcp_data_dir.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=str(mcp_data_dir), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(payload)
        os.replace(tmp_path, data_file)
        _last_payload = payload
    except BaseException:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise


def _flush_pending() -> None:
    global _pending_payload
    with _write_lock:
        if _pending_payload is not None:
            payload, _pending_payload = _pending_payload, None
            _write_payload(payload)


def _save_data(data: dict) -> None:
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


# Backup / Restore Tools
@mcp.tool()
def flush_data() -> dict:
    _flush_pending()
    return {"flushed": True, "path": str(data_file), "debounce_ms": _WRITE_DEBOUNCE_MS}


@mcp.tool()
def backup_data() -> dict:
    _flush_pending()
    if not data_file.exists():
        raise ValueError("No data file to back up yet")
    backup_dir = mcp_data_dir / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    target = backup_dir / f"{data_file.stem}-{stamp}.json"
    shutil.copy2(data_file, target)
    return {"backup": str(target), "bytes": target.stat().st_size}


@mcp.tool()
def list_backups() -> list:
    backup_dir = mcp_data_dir / "backups"
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


@mcp.tool()
def restore_backup(name: str) -> dict:
    source = mcp_data_dir / "backups" / name
    if not source.exists():
        raise ValueError(f"Unknown backup: {name}")
    with _write_lock:
        _write_payload(source.read_text(encoding="utf-8"))
    return {"restored": name, "note": "Restart the MCP server to load the restored data"}


# Core Helpers
def _now() -> str:
    return datetime.now().isoformat()


def _today() -> str:
    return date.today().isoformat()


# Initialize data
_data = _load_data()
surveys: dict = {int(k): v for k, v in _data.get("surveys", {}).items()}
questions: dict = {int(k): v for k, v in _data.get("questions", {}).items()}
responses: dict = {int(k): v for k, v in _data.get("responses", {}).items()}
categories: dict = {int(k): v for k, v in _data.get("categories", {}).items()}

_next_survey_id = _data.get("next_survey_id", 1)
_next_question_id = _data.get("next_question_id", 1)
_next_response_id = _data.get("next_response_id", 1)
_next_category_id = _data.get("next_category_id", 1)


def _get_next_survey_id() -> int:
    global _next_survey_id
    id_ = _next_survey_id
    _next_survey_id += 1
    return id_


def _get_next_category_id() -> int:
    global _next_category_id
    id_ = _next_category_id
    _next_category_id += 1
    return id_


def _save() -> None:
    _save_data(
        {
            "surveys": surveys,
            "questions": questions,
            "responses": responses,
            "categories": categories,
            "next_survey_id": _next_survey_id,
            "next_question_id": _next_question_id,
            "next_response_id": _next_response_id,
            "next_category_id": _next_category_id,
        }
    )


def _get_survey_responses_by_survey_id(sid: int) -> list:
    return [r for r in responses.values() if int(r.get("survey_id", 0)) == sid and r.get("status") == "submitted"]


# Survey Tools
@mcp.tool()
def create_survey(
    title: str,
    description: str = "",
    language: str = "en",
    is_active: bool = True,
    auto_decline_nps_below: int = 6,
    opt_out_allowed: bool = True,
    allow_multiple_responses: bool = False,
    allow_anonymized: bool = False,
) -> dict:
    survey_id = _get_next_survey_id()
    survey = {
        "id": survey_id,
        "title": title,
        "description": description,
        "language": language,
        "is_active": is_active,
        "auto_decline_nps_below": auto_decline_nps_below,
        "opt_out_allowed": opt_out_allowed,
        "allow_multiple_responses": allow_multiple_responses,
        "allow_anonymized": allow_anonymized,
        "questions": [],
        "created_at": _now(),
        "updated_at": _now(),
    }
    surveys[survey_id] = survey
    _save()
    return survey


@mcp.tool()
def get_survey(survey_id: int) -> Optional[dict]:
    survey = surveys.get(survey_id)
    if survey is None:
        return None
    survey_copy = survey.copy()
    survey_copy["answer_count"] = len(_get_survey_responses_by_survey_id(survey_id))
    return survey_copy


@mcp.tool()
def list_surveys(
    status: Optional[str] = None,
    language: Optional[str] = None,
    is_active: Optional[bool] = None,
    limit: int = 100,
    offset: int = 0,
) -> list:
    results = []
    for s in surveys.values():
        if status is not None and s.get("title", "").lower() != status.lower():
            continue
        if language is not None and s.get("language") != language:
            continue
        if is_active is not None and s.get("is_active") != is_active:
            continue
        answered = len(_get_survey_responses_by_survey_id(s["id"]))
        results.append({**s, "answer_count": answered})
    results.sort(key=lambda s: s.get("created_at", ""), reverse=True)
    return results[offset:offset + limit]


@mcp.tool()
def update_survey(
    survey_id: int,
    title: Optional[str] = None,
    description: Optional[str] = None,
    language: Optional[str] = None,
    is_active: Optional[bool] = None,
    auto_decline_nps_below: Optional[int] = None,
    opt_out_allowed: Optional[bool] = None,
    allow_multiple_responses: Optional[bool] = None,
    allow_anonymized: Optional[bool] = None,
) -> Optional[dict]:
    survey = surveys.get(survey_id)
    if survey is None:
        return None
    if survey.get("is_active"):
        raise ValueError("Cannot modify a deployed survey; de-activate first")
    for field, value in (
        ("title", title), ("description", description), ("language", language),
        ("is_active", is_active), ("auto_decline_nps_below", auto_decline_nps_below),
        ("opt_out_allowed", opt_out_allowed), ("allow_multiple_responses",
         allow_multiple_responses), ("allow_anonymized", allow_anonymized),
    ):
        if value is not None:
            survey[field] = value
    survey["updated_at"] = _now()
    _save()
    return get_survey(survey_id)


@mcp.tool()
def delete_survey(survey_id: int) -> bool:
    if survey_id not in surveys:
        return False
    del surveys[survey_id]
    _save()
    return True


@mcp.tool()
def add_question_to_survey(
    survey_id: int,
    question_text: str,
    question_type: QuestionType,
    is_required: bool = False,
    position: int = 0,
    options: Optional[list] = None,
) -> dict:
    survey = surveys.get(survey_id)
    if survey is None:
        raise ValueError(f"Unknown survey: {survey_id}")
    question_id = _next_question_id
    question = {
        "id": question_id, "survey_id": survey_id, "question_text": question_text,
        "question_type": question_type.value, "is_required": is_required,
        "options": options or [], "position": position, "is_active": True,
        "weight": 1.0, "created_at": _now(), "updated_at": _now(),
    }
    survey["questions"].append(question)
    _save()
    return question


@mcp.tool()
def remove_question_from_survey(survey_id: int, question_id: int) -> bool:
    survey = surveys.get(survey_id)
    if survey is None:
        return False
    question_ids = {q["id"] for q in survey.get("questions", [])}
    if question_id not in question_ids:
        return False
    survey["questions"] = [q for q in survey["questions"] if q["id"] != question_id]
    _save()
    return True


# Question Tools
@mcp.tool()
def create_question(
    survey_id: int,
    question_text: str,
    question_type: QuestionType,
    is_required: bool = False,
    options: Optional[list] = None,
    position: int = 0,
) -> dict:
    return add_question_to_survey(survey_id, question_text, question_type, is_required, position, options)


@mcp.tool()
def get_question(question_id: int) -> Optional[dict]:
    return questions.get(question_id)


@mcp.tool()
def list_questions(
    survey_id: Optional[int] = None,
    status: Optional[str] = None,
    question_type: Optional[str] = None,
    limit: int = 100,
) -> list:
    results = []
    for q in questions.values():
        if survey_id is not None and int(q.get("survey_id", 0)) != survey_id:
            continue
        if status is not None and str(q.get("is_active", True)).lower() != status.lower():
            continue
        if question_type is not None and q.get("question_type") != question_type:
            continue
        results.append(q)
    results.sort(key=lambda q: q.get("position", 0))
    return results[:limit]


@mcp.tool()
def update_question(
    question_id: int,
    question_text: Optional[str] = None,
    is_required: Optional[bool] = None,
    is_active: Optional[bool] = None,
    weight: Optional[float] = None,
) -> Optional[dict]:
    question = questions.get(question_id)
    if question is None:
        return None
    survey = surveys.get(question.get("survey_id"))
    if survey and survey.get("is_active"):
        raise ValueError("Cannot edit a question in a deployed survey")
    for field, value in (
        ("question_text", question_text), ("is_required", is_required),
        ("is_active", is_active), ("weight", weight),
    ):
        if value is not None:
            question[field] = value
    question["updated_at"] = _now()
    _save()
    return get_question(question_id)


@mcp.tool()
def delete_question(question_id: int) -> bool:
    if question_id not in questions:
        return False
    q = questions[question_id]
    survey_id = q.get("survey_id")
    if survey_id:
        for i, sq in enumerate(surveys.get(survey_id, {}).get("questions", [])):
            if sq["id"] == question_id:
                surveys[survey_id]["questions"].pop(i)
                break
    _save()
    return True


# Category Tools
@mcp.tool()
def create_category(name: str, slug: str, description: Optional[str] = None, color: str = "#6B7280") -> FeedbackCategoryModel:
    category_id = _get_next_category_id()
    category = FeedbackCategoryModel(
        id=category_id, name=name, slug=slug, description=description,
        color=color, is_active=True, created_at=_now(),
    )
    categories[category_id] = category.model_dump()
    _save()
    return category


@mcp.tool()
def get_category(category_id: int) -> Optional[FeedbackCategoryModel]:
    c = categories.get(category_id)
    if c is None:
        return None
    return FeedbackCategoryModel(**c)


@mcp.tool()
def list_categories(is_active: Optional[bool] = None) -> list:
    results = []
    for c in categories.values():
        if is_active is not None and c.get("is_active") != is_active:
            continue
        results.append(FeedbackCategoryModel(**c))
    results.sort(key=lambda c: c.name.lower())
    return results


@mcp.tool()
def update_category(
    category_id: int, name: Optional[str] = None, slug: Optional[str] = None,
    description: Optional[str] = None, color: Optional[str] = None,
    is_active: Optional[bool] = None,
) -> Optional[FeedbackCategoryModel]:
    c = categories.get(category_id)
    if c is None:
        return None
    for field, value in (
        ("name", name), ("slug", slug), ("description", description),
        ("color", color), ("is_active", is_active),
    ):
        if value is not None:
            c[field] = value
    c["updated_at"] = _now()
    _save()
    return FeedbackCategoryModel(**c)


@mcp.tool()
def delete_category(category_id: int) -> bool:
    if category_id not in categories:
        return False
    categories[category_id]["is_active"] = False
    categories[category_id]["updated_at"] = _now()
    _save()
    return True


# NPS Tools
@mcp.tool()
def get_nps_summary(survey_id: Optional[int] = None, as_of: Optional[str] = None) -> dict:
    cutoff = datetime.fromisoformat(as_of or _now())
    if survey_id:
        responses_subset = [r for r in responses.values() if int(r.get("survey_id", 0)) == survey_id]
    else:
        responses_subset = list(responses.values())
    submitted = [r for r in responses_subset if r.get("status") == "submitted" and r.get("submitted_date")]
    submitted = [r for r in submitted if datetime.fromisoformat(r.get("submitted_date")) <= cutoff]

    scores = []
    survey_settings = {}
    for r in submitted:
        raw = r.get("nps_raw_score")
        if raw is not None:
            survey_settings[id(r)] = surveys.get(r.get("survey_id"))
            if raw < 7:
                s = survey_settings.get(id(r))
                if s and int(s.get("auto_decline_nps_below", 6)) <= raw:
                    continue
            scores.append(raw)

    def nps_score(scores_list: list) -> int:
        if not scores_list:
            return 0
        promoters = sum(1 for s in scores_list if s >= 9)
        detractors = sum(1 for s in scores_list if s <= 6)
        total = len(scores_list)
        return round((promoters / total) * 100 - (detractors / total) * 100, 1)

    nps_score_val = nps_score(scores)
    promoter_pf = round(sum(1 for s in scores if s >= 9) / len(scores) * 100, 1) if scores else 0
    passive_pf = round(sum(1 for s in scores if 7 <= s <= 8) / len(scores) * 100, 1) if scores else 0
    detractor_pf = round(sum(1 for s in scores if s <= 6) / len(scores) * 100, 1) if scores else 0

    return {
        "survey_id": survey_id,
        "as_of": as_of or _now(),
        "respondents": len(submitted),
        "nps_score": nps_score_val,
        "nps_summary": {
            "promoters": sum(1 for s in scores if s >= 9),
            "passives": sum(1 for s in scores if 7 <= s <= 8),
            "detractors": sum(1 for s in scores if s <= 6),
            "promoter_pct": promoter_pf,
            "passive_pct": passive_pf,
            "detractor_pct": detractor_pf,
        },
        "distribution_buckets": {
            "promoter": sum(1 for s in scores if s >= 9),
            "passive": sum(1 for s in scores if 7 <= s <= 8),
            "detractor": sum(1 for s in scores if s <= 6),
        },
        "raw_scores": sorted(scores) if scores else [],
    }


@mcp.tool()
def get_nps_distribution(survey_id: Optional[int] = None, as_of: Optional[str] = None) -> list:
    summary = get_nps_summary(survey_id, as_of)
    return summary.get("distribution_buckets", {})


# Response Tools
@mcp.tool()
def submit_response(
    survey_id: int,
    respondent_id: str,
    respondent_email: Optional[str] = None,
    category_id: Optional[int] = None,
    answers: Optional[dict] = None,
    nps_raw_score: Optional[int] = None,
    follow_up: bool = False,
    follow_up_notes: Optional[str] = None,
    opt_out_nps: Optional[bool] = None,
) -> dict:
    survey = surveys.get(survey_id)
    if survey is None:
        raise ValueError(f"Unknown survey: {survey_id}")

    existing_responses = [r for r in responses.values() if int(r.get("survey_id", 0)) == survey_id and r.get("status") == "submitted"]

    if not survey.get("allow_multiple_responses") and respondent_id:
        for r in existing_responses:
            if r.get("respondent_id") == respondent_id:
                raise ValueError(f"Respondent {respondent_id} already submitted")

    response_id = _next_response_id
    parsed_answers = {}
    if answers:
        for qid, val in answers.items():
            if not isinstance(qid, str):
                qid = str(qid)
            parsed_answers[qid] = val

    response = {
        "id": response_id,
        "survey_id": survey_id,
        "respondent_id": respondent_id,
        "respondent_email": respondent_email,
        "category_id": category_id,
        "answers": parsed_answers,
        "nps_raw_score": nps_raw_score,
        "is_follow_up": follow_up,
        "follow_up_notes": follow_up_notes,
        "status": ResponseStatus.SUBMITTED.value,
        "submitted_at": _now(),
        "submitted_date": _today(),
        "created_at": _now(),
        "updated_at": _now(),
    }
    responses[response_id] = response
    _save()
    return response


@mcp.tool()
def get_response(response_id: int) -> Optional[dict]:
    return responses.get(response_id)


@mcp.tool()
def list_responses(
    survey_id: Optional[int] = None,
    category_id: Optional[int] = None,
    status: Optional[str] = None,
    respondent_id: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
) -> list:
    results = []
    for r in responses.values():
        if survey_id is not None and int(r.get("survey_id", 0)) != survey_id:
            continue
        if category_id is not None and int(r.get("category_id", 0)) != category_id:
            continue
        if status is not None and r.get("status") != status:
            continue
        if respondent_id is not None and r.get("respondent_id") != respondent_id:
            continue
        results.append(r)
    results.sort(key=lambda r: r.get("submitted_date") or r.get("created_at"))
    return results[offset:offset + limit]


@mcp.tool()
def update_response(
    response_id: int,
    status: Optional[str] = None,
    nps_raw_score: Optional[int] = None,
    answers: Optional[dict] = None,
) -> Optional[dict]:
    r = responses.get(response_id)
    if r is None:
        return None
    for field, value in (
        ("status", status), ("nps_raw_score", nps_raw_score), ("answers", answers),
    ):
        if value is not None:
            r[field] = value
    r["updated_at"] = _now()
    _save()
    return get_response(response_id)


@mcp.tool()
def delete_response(response_id: int) -> bool:
    if response_id not in responses:
        return False
    del responses[response_id]
    _save()
    return True


@mcp.tool()
def check_duplicate(
    survey_id: int,
    respondent_id: str,
    respondent_email: Optional[str] = None,
) -> bool:
    survey = surveys.get(survey_id)
    if survey is None:
        raise ValueError(f"Unknown survey: {survey_id}")

    existing = _get_survey_responses_by_survey_id(survey_id)
    for r in existing:
        if r.get("respondent_id") == respondent_id:
            if survey.get("allow_multiple_responses"):
                return False
        if respondent_email and r.get("respondent_email") == respondent_email:
            if survey.get("allow_multiple_responses"):
                return False
    return True  # No duplicates found


# Analytics Tools
@mcp.tool()
def get_survey_overview(survey_id: int) -> dict:
    survey = surveys.get(survey_id)
    if survey is None:
        raise ValueError(f"Unknown survey: {survey_id}")

    total_responses = len(_get_survey_responses_by_survey_id(survey_id))
    submitted = total_responses
    completion_rate = 0.0
    question_counts = {}

    for q in survey.get("questions", []):
        qid = str(q["id"])
        ans_count = sum(1 for r in _get_survey_responses_by_survey_id(survey_id) if r.get("answers", {}).get(qid) is not None)
        question_counts[qid] = {
            "question_text": q.get("question_text"),
            "question_type": q.get("question_type"),
            "is_required": q.get("is_required"),
            "answers": ans_count,
            "total": total_responses,
            "completion_rate": round(ans_count / total_responses * 100, 1) if total_responses else 0,
        }

    category_counts = {}
    for r in _get_survey_responses_by_survey_id(survey_id):
        cat_id = r.get("category_id")
        if cat_id:
            category_counts[cat_id] = category_counts.get(cat_id, 0) + 1

    return {
        "survey_id": survey_id,
        "title": survey.get("title"),
        "description": survey.get("description"),
        "total_responses": total_responses,
        "submitted_responses": submitted,
        "completion_rate": round(submitted / total_responses * 100, 1) if total_responses else 0,
        "questions": question_counts,
        "category_breakdown": category_counts,
        "nps_score": get_nps_summary(survey_id)["nps_score"],
        "nps_respondents": get_nps_summary(survey_id)["respondents"],
        "created_at": survey.get("created_at"),
        "language": survey.get("language"),
    }


@mcp.tool()
def get_analytics_overview() -> dict:
    survey_stats = []
    for s in surveys.values():
        if not s.get("is_active"):
            continue
        ans = _get_survey_responses_by_survey_id(s["id"])
        submitted = len(ans)
        survey_stats.append({
            "survey_id": s["id"],
            "title": s.get("title"),
            "total_responses": len(ans),
            "submitted": submitted,
            "completion_rate": round(submitted / len(ans) * 100, 1) if ans else 0,
            "language": s.get("language"),
        })

    return {
        "total_surveys": len(surveys),
        "active_surveys": len([s for s in surveys.values() if s.get("is_active")]),
        "total_responses": len(responses),
        "submitted_responses": sum(1 for r in responses.values() if r.get("status") == "submitted"),
        "surveys": sorted(survey_stats, key=lambda x: x.get("total_responses", 0), reverse=True),
    }


@mcp.tool()
def get_question_analytics(survey_id: int) -> dict:
    survey = surveys.get(survey_id)
    if survey is None:
        raise ValueError(f"Unknown survey: {survey_id}")

    answers_by_question = {}
    for q in survey.get("questions", []):
        qid = str(q["id"])
        answers_by_question[qid] = {
            "question_text": q.get("question_text"),
            "question_type": q.get("question_type"),
            "is_required": q.get("is_required"),
            "options": q.get("options"),
            "responses_per_question_type": {},
        }

    for r in _get_survey_responses_by_survey_id(survey_id):
        for qid, val in r.get("answers", {}).items():
            answers_by_question[qid]["responses_per_question_type"][qid] = {"value": val, "count": 1}

    return answers_by_question


@mcp.tool()
def get_feedback_by_category(baseline_date: Optional[str] = None) -> list:
    cutoff = datetime.fromisoformat(baseline_date or _now())
    recent = [r for r in responses.values() if r.get("submitted_date") and datetime.fromisoformat(r.get("submitted_date")) <= cutoff]
    baseline_cutoff = datetime.fromisoformat(baseline_date or (datetime.now() - timedelta(days=30)).isoformat())
    baseline = [r for r in responses.values() if r.get("submitted_date") and datetime.fromisoformat(r.get("submitted_date")) <= baseline_cutoff]

    category_counts = {}
    for r in recent:
        cat_id = r.get("category_id")
        if cat_id:
            category_counts[cat_id] = category_counts.get(cat_id, 0) + 1

    recent_total = len(recent)
    return [
        {
            "category_id": cat_id,
            "recent": cnt,
            "baseline": category_counts.get(cat_id, 0),
            "percent": round(cnt / recent_total * 100, 1) if recent_total else 0,
        }
        for cat_id, cnt in category_counts.items()
    ]


# Resources
@mcp.resource("surveys://all")
def get_all_surveys_resource() -> str:
    if not surveys:
        return "No surveys found."
    lines = ["# All Surveys\n"]
    for s in sorted(surveys.values(), key=lambda x: x.get("created_at", "")):
        status = "[DEPLOYED]" if s.get("is_active") else "[ARCHIVED]"
        lines.append(f"## {status} {s['title']} (ID: {s['id']})")
        lines.append(f"- Description: {s.get('description', '')}")
        lines.append(f"- Language: {s.get('language', 'N/A')}")
        lines.append(f"- Created: {s.get('created_at')}")
        lines.append(f"- Questions: {len(s.get('questions', []))}")
        lines.append("")
    return "\n".join(lines)


@mcp.resource("surveys://all")
def get_active_surveys_resource() -> str:
    active = [s for s in surveys.values() if s.get("is_active")]
    if not active:
        return "No active surveys found."
    lines = ["# Active Surveys\n"]
    for s in sorted(active, key=lambda x: x.get("created_at", "")):
        lines.append(f"- **{s['title']}** (ID: {s['id']}) - Language: {s.get('language')}")
    return "\n".join(lines)


@mcp.resource("surveys://all")
def get_nps_resource() -> str:
    overall = get_nps_summary()
    lines = [
        f"# NPS Summary\n",
        f"- Survey: {overall.get('survey_id', 'all')} | As of: {overall.get('as_of')}",
        f"- Respondents: {overall.get('respondents', 0)}",
        f"- **NPS Score: {overall.get('nps_score', 0)}**,",
    ]
    if overall.get("nps_summary"):
        ns = overall["nps_summary"]
        lines.extend([
            f"- Promoters: {ns.get('promoters', 0)} ({ns.get('promoter_pct', 0)}%)",
            f"- Passives: {ns.get('passives', 0)} ({ns.get('passive_pct', 0)}%)",
            f"- Detractors: {ns.get('detractors', 0)} ({ns.get('detractor_pct', 0)}%)",
        ])
    return "\n".join(lines)


@mcp.resource("surveys://all")
def get_all_responses_resource() -> str:
    all_responses = [r for r in responses.values() if r.get("status") == "submitted"]
    if not all_responses:
        return "No responses found."
    lines = ["# All Responses\n"]
    for r in sorted(all_responses, key=lambda x: x.get("submitted_date") or x.get("created_at", "")):
        lines.append(f"## Response {r['id']}")
        lines.append(f"- Survey ID: {r.get('survey_id')}")
        lines.append(f"- Respondent: {r.get('respondent_id')}")
        lines.append(f"- Email: {r.get('respondent_email') or '---'}")
        lines.append(f"- Category: {r.get('category_id') or '---'}")
        lines.append(f"- NPS Score: {r.get('nps_raw_score') or 'N/A'}")
        lines.append(f"- Submitted: {r.get('submitted_date') or '---'}")
        lines.append("")
    return "\n".join(lines)


@mcp.resource("surveys://all")
def get_all_categories_resource() -> str:
    active = [c for c in categories.values() if c.get("is_active")]
    if not active:
        return "No categories found."
    lines = ["# Feedback Categories\n"]
    for c in sorted(active, key=lambda x: x.name):
        lines.append(f"- **{c.name}** (ID: {c.id}, slug: {c.slug})")
        if c.description:
            lines.append(f"- Description: {c.description}")
    return "\n".join(lines)


@mcp.resource("surveys://all")
def get_analytics_overview_resource() -> str:
    overview = get_analytics_overview()
    lines = [
        "# Analytics Overview\n",
        f"- Total Surveys: {overview.get('total_surveys', 0)}",
        f"- Active Surveys: {overview.get('active_surveys', 0)}",
        f"- Total Responses: {overview.get('total_responses', 0)}",
        f"- Submitted Responses: {overview.get('submitted_responses', 0)}",
    ]
    if overview.get("surveys"):
        lines.append("\n## Survey Performance")
        for s in overview["surveys"][:10]:
            lines.append(
                f"- {s.get('title', 'Unknown')} - {s.get('total_responses', 0)} responses "
                f"({s.get('completion_rate', 0)}%)"
            )
    lines.append("")
    return "\n".join(lines)


# Main
if __name__ == "__main__":
    mcp.run()