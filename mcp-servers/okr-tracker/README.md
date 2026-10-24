# OKR Tracker MCP Server

A FastMCP server for objectives, key results, check-ins, and progress rollups.

## Installation

```bash
pip install -r requirements.txt
```

## Running the Server

```bash
python server.py
```

## What It Does

- **Objectives** — title, owner, period (e.g. `2026-Q4`), status
- **Key results** — measurable targets with start/current/target values
- **Progress math** — handles increasing and decreasing targets, clamped 0–100%
- **Rollups** — objective progress is the mean of its key results
- **Check-ins** — periodic value + confidence updates with notes
- **Summary** — health across a period, including objectives at risk

## Available Tools

### Objectives

| Tool | Description |
|------|-------------|
| `create_objective` | Create an objective |
| `get_objective` / `list_objectives` | Read with computed progress |
| `update_objective` | Update metadata or status |
| `delete_objective` | Delete an objective and its check-ins |

### Key Results

| Tool | Description |
|------|-------------|
| `add_key_result` | Add a measurable key result |
| `update_key_result` | Update definition, value, or confidence |
| `delete_key_result` | Remove a key result |

### Check-ins

| Tool | Description |
|------|-------------|
| `check_in` | Record a check-in and optionally update a key result |
| `list_check_ins` | Check-in history |

### Reporting

| Tool | Description |
|------|-------------|
| `get_progress` | Per-key-result and overall progress |
| `get_okr_summary` | Rollup for a period, with at-risk objectives |

## Progress Model

```
progress = clamp((current - start) / (target - start), 0, 1)
```

This automatically handles "decrease" goals — e.g. churn from 100 → 0 with a
current value of 25 yields 75%.

## Resources

| Resource | Description |
|----------|-------------|
| `okr://summary` | OKR summary as text |
| `okr://objectives` | All objectives with progress as text |

## Example Usage

```python
objective = create_objective("Grow recurring revenue", owner="Hamish", period="2026-Q4")

mrr = add_key_result(objective.id, "New MRR", target_value=20000, start_value=0,
                     metric_unit="AUD")
add_key_result(objective.id, "Churn rate", target_value=2, start_value=8,
               metric_unit="%")

check_in(objective.id, value=9000, key_result_id=mrr.id, confidence=60,
         note="Week 3 — two new retainers signed")

get_progress(objective.id)
get_okr_summary("2026-Q4")
```

## Storage

Data lives in `data/okrs.json` (override with `MCP_DATA_DIR`). Writes are atomic
and thread-safe.

## Tests

```bash
pip install -r requirements-dev.txt
pytest tests/
```

---

## Feedback & Community

Found this MCP server genuinely useful? I'd love to hear from you.

- **Email**: [hamish@atech.industries](mailto:hamish@atech.industries)
- **Join our free Open Source AI Builders Club on Skool**: [https://www.skool.com/open-source-ai-builders-club/about?ref=da946a67c5c646e991b96ea9ce7ad9e4](https://www.skool.com/open-source-ai-builders-club/about?ref=da946a67c5c646e991b96ea9ce7ad9e4)
