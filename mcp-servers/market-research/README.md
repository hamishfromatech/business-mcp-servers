# Market Research & Customer Feedback MCP Server

A FastMCP server for market research and customer feedback management. Track surveys,
questions, responses, NPS scores, feedback categories, and generate analytics.

## Features

- **Surveys** - Create, manage, and deploy surveys with customizable settings
- **Questions** - Support for multiple question types:
  - Single choice, Multiple choice, Rating, NPS, Likert, Text, Slider
- **Responses** - Collect and manage survey responses with answer tracking
- **NPS** - Net Promoter Score tracking with promoter/passive/detractor analysis
- **Categories** - Organize feedback by category (Product, Support, Pricing, etc.)
- **Analytics** - Comprehensive reporting on survey performance and feedback trends

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run the server
python server.py
```

## Data Models

### Survey
A survey represents a customer feedback questionnaire.

| Field | Type | Description |
|---|---|---|
| id | integer | Unique identifier |
| title | string | Survey title |
| description | string | Survey description |
| language | string | Language code (e.g., "en") |
| is_active | boolean | Whether the survey is active/deployed |
| auto_decline_nps_below | integer | Auto-discard NPS scores below this |
| opt_out_allowed | boolean | Allow respondents to opt out of NPS |
| allow_multiple_responses | boolean | Allow duplicate submissions |
| allow_anonymized | boolean | Allow anonymous responses |
| questions | array | Questions in the survey |
| answer_count | integer | Total number of responses |

### Question
A question within a survey.

| Field | Type | Description |
|---|---|---|
| id | integer | Unique identifier |
| survey_id | integer | The survey this question belongs to |
| question_text | string | The question text |
| question_type | enum | Type of question (see below) |
| is_required | boolean | Whether the question is required |
| options | array | Options for choice/rating questions |
| position | integer | Order in the survey |
| is_active | boolean | Whether the question is active |
| weight | float | Response weight (default 1.0) |

### Response
A submitted response to a survey.

| Field | Type | Description |
|---|---|---|
| id | integer | Unique identifier |
| survey_id | integer | The survey being responded to |
| respondent_id | string | Unique respondent identifier |
| respondent_email | string | Respondent email (optional) |
| category_id | integer | Feedback category ID (optional) |
| answers | object | Question ID → answer mapping |
| nps_raw_score | integer | NPS score 0-10 (optional) |
| is_follow_up | boolean | Whether this is a follow-up |
| follow_up_notes | string | Notes about follow-up |
| status | enum | Current status (submitted/draft/discard) |
| submitted_date | string | Submission date (ISO) |

### Feedback Category
A category for organizing feedback.

| Field | Type | Description |
|---|---|---|
| id | integer | Unique identifier |
| name | string | Category name |
| slug | string | URL-friendly identifier |
| description | string | Category description |
| color | string | Hex color code |
| is_active | boolean | Whether the category is active |

## Question Types

| Type | Description |
|---|---|
| `single_choice` | One option selected |
| `multiple_choice` | Zero or more options |
| `rating` | 1-5 star rating |
| `nps` | Net Promoter Score 0-10 |
| `likert` | Likert scale (yes/no/maybe) |
| `text` | Single-line text |
| `text_area` | Multi-line text |
| `rating_likert` | Rating with custom labels |
| `date` | Date selection |
| `slider` | Linear slider 0-100 |

## Usage

### Create a Survey
```python
create_survey(
    title="Product Feedback Survey",
    description="Please share your thoughts about our product.",
    language="en",
    is_active=True,
    auto_decline_nps_below=6,
    allow_multiple_responses=False,
)
```

### Add Questions
```python
create_question(
    survey_id=1,
    question_text="How likely are you to recommend our product?",
    question_type="nps",
    is_required=True,
)

create_question(
    survey_id=1,
    question_text="How satisfied are you with our support?",
    question_type="rating",
    is_required=False,
    options=[
        QuestionOption(value="1", display_text="Very Unsatisfied"),
        QuestionOption(value="5", display_text="Very Satisfied"),
    ],
)
```

### Submit a Response
```python
submit_response(
    survey_id=1,
    respondent_id="user-123",
    respondent_email="user@example.com",
    category_id=1,
    answers={
        "1": "9",           # NPS score
        "2": "4",           # Satisfaction rating
    },
    nps_raw_score=9,
    follow_up=False,
)
```

### Get NPS Summary
```python
get_nps_summary(survey_id=1)
# Returns:
# {
#     "survey_id": 1,
#     "respondents": 42,
#     "nps_score": 23.8,
#     "distribution_buckets": {
#         "promoter": 30,
#         "passive": 8,
#         "detractor": 4,
#     },
#     "raw_scores": [2,3,4,5,6,7,8,9,9,9,9,10,...]
# }
```

### Get Survey Overview
```python
get_survey_overview(survey_id=1)
# Returns:
# {
#     "survey_id": 1,
#     "total_responses": 42,
#     "completion_rate": 98.5,
#     "category_breakdown": {1: 15, 2: 12, 3: 15},
#     "nps_score": 23.8,
#     "questions": [...]
# }
```

## Feedback Categories

Available pre-defined categories:

| Category | Use Case |
|---|---|
| `product` | Product-related feedback |
| `support` | Support ticket feedback |
| `pricing` | Pricing concerns |
| `feature_request` | New feature requests |
| `bug_report` | Bug reports |
| `general` | General comments |
| `onboarding` | Onboarding experience |
| `user_experience` | UX feedback |
| `communication` | Communication feedback |
| `remote` | Remote work related |
| `other` | Other |

## Backup & Restore

```bash
# Backup the database
python -c "from server import backup_data; print(backup_data())"

# Restore a backup
python -c "from server import restore_backup; print(restore_backup('backup-name.json'))"
```

## NPS Scoring

NPS is calculated as: **%Promoters - %Detractors**

- **Promoters (9-10)**: Loyal enthusiasts who will keep buying and refer others
- **Passives (7-8)**: Satisfied but not actively loyal
- **Detractors (0-6)**: Unhappy customers who may spread negative word

## Resources

- `surveys://all` - List of all surveys
- `surveys://active` - Active surveys only
- `surveys://nps` - NPS summary
- `responses://all` - All responses
- `categories://all` - All categories
- `analytics://overview` - Analytics overview

## Configuration

### MCP_DATA_DIR

Set `MCP_DATA_DIR` to customize the data directory location:

```bash
export MCP_DATA_DIR=/path/to/custom/data
python server.py
```

### MCP_WRITE_DEBOUNCE_MS

Set write debounce for reduced disk I/O:

```bash
export MCP_WRITE_DEBOUNCE_MS=1000
```

## Testing

```bash
pip install -r requirements-dev.txt
pytest
```

## License

MIT - Created by hamishfromatech