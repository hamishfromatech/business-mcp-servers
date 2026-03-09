"""
Web UI for Career Manager - Simple HTTP server using Python standard library.
"""

import json
import os
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs, urlparse
import webbrowser
import threading

# Import storage functions
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from career_manager.storage import load_data, save_data, ensure_data_dir


# HTML Templates
HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Career Manager</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
        }}
        .header {{
            text-align: center;
            color: white;
            margin-bottom: 30px;
        }}
        .header h1 {{
            font-size: 2.5rem;
            margin-bottom: 10px;
        }}
        .header p {{
            opacity: 0.9;
        }}
        .tabs {{
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
            flex-wrap: wrap;
        }}
        .tab {{
            padding: 12px 24px;
            background: rgba(255,255,255,0.2);
            border: none;
            border-radius: 8px;
            color: white;
            cursor: pointer;
            font-size: 1rem;
            transition: all 0.3s;
        }}
        .tab:hover, .tab.active {{
            background: white;
            color: #667eea;
        }}
        .card {{
            background: white;
            border-radius: 16px;
            padding: 30px;
            margin-bottom: 20px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.1);
        }}
        .card h2 {{
            color: #333;
            margin-bottom: 20px;
            font-size: 1.5rem;
        }}
        .form-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
        }}
        .form-group {{
            margin-bottom: 15px;
        }}
        .form-group label {{
            display: block;
            margin-bottom: 5px;
            color: #555;
            font-weight: 500;
        }}
        .form-group input, .form-group textarea, .form-group select {{
            width: 100%;
            padding: 12px;
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            font-size: 1rem;
            transition: border-color 0.3s;
        }}
        .form-group input:focus, .form-group textarea:focus, .form-group select:focus {{
            outline: none;
            border-color: #667eea;
        }}
        .form-group textarea {{
            min-height: 100px;
            resize: vertical;
        }}
        .btn {{
            padding: 12px 24px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-size: 1rem;
            font-weight: 600;
            transition: transform 0.2s, box-shadow 0.2s;
        }}
        .btn:hover {{
            transform: translateY(-2px);
            box-shadow: 0 5px 20px rgba(102, 126, 234, 0.4);
        }}
        .btn-secondary {{
            background: #6c757d;
        }}
        .btn-danger {{
            background: #dc3545;
        }}
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 20px;
        }}
        .stat-card {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 12px;
            text-align: center;
        }}
        .stat-card .number {{
            font-size: 2rem;
            font-weight: 700;
        }}
        .stat-card .label {{
            opacity: 0.9;
            font-size: 0.9rem;
        }}
        .list-item {{
            background: #f8f9fa;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 10px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .list-item .title {{
            font-weight: 600;
            color: #333;
        }}
        .list-item .meta {{
            color: #666;
            font-size: 0.9rem;
        }}
        .tag {{
            display: inline-block;
            padding: 4px 12px;
            background: #e9ecef;
            border-radius: 20px;
            font-size: 0.8rem;
            color: #495057;
        }}
        .tag.active {{ background: #28a745; color: white; }}
        .tag.interview {{ background: #ffc107; color: #333; }}
        .tag.offer {{ background: #17a2b8; color: white; }}
        .tag.rejected {{ background: #dc3545; color: white; }}
        .hidden {{ display: none; }}
        .alert {{
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 20px;
        }}
        .alert-success {{
            background: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
        }}
        .alert-error {{
            background: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
        }}
        @media (max-width: 768px) {{
            .header h1 {{ font-size: 1.8rem; }}
            .card {{ padding: 20px; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 Career Manager</h1>
            <p>Your all-in-one career management dashboard</p>
        </div>

        <div class="tabs">
            <button class="tab active" onclick="showTab('dashboard')">Dashboard</button>
            <button class="tab" onclick="showTab('profile')">Profile</button>
            <button class="tab" onclick="showTab('resume')">Resume</button>
            <button class="tab" onclick="showTab('applications')">Applications</button>
            <button class="tab" onclick="showTab('interviews')">Interviews</button>
            <button class="tab" onclick="showTab('skills')">Skills</button>
            <button class="tab" onclick="showTab('network')">Network</button>
            <button class="tab" onclick="showTab('goals')">Goals</button>
        </div>

        <div id="alert-container"></div>

        <div id="dashboard" class="tab-content">
            {dashboard_content}
        </div>

        <div id="profile" class="tab-content hidden">
            {profile_content}
        </div>

        <div id="resume" class="tab-content hidden">
            {resume_content}
        </div>

        <div id="applications" class="tab-content hidden">
            {applications_content}
        </div>

        <div id="interviews" class="tab-content hidden">
            {interviews_content}
        </div>

        <div id="skills" class="tab-content hidden">
            {skills_content}
        </div>

        <div id="network" class="tab-content hidden">
            {network_content}
        </div>

        <div id="goals" class="tab-content hidden">
            {goals_content}
        </div>
    </div>

    <script>
        function showTab(tabId) {{
            document.querySelectorAll('.tab-content').forEach(el => el.classList.add('hidden'));
            document.querySelectorAll('.tab').forEach(el => el.classList.remove('active'));
            document.getElementById(tabId).classList.remove('hidden');
            event.target.classList.add('active');
        }}

        function showAlert(message, type) {{
            const container = document.getElementById('alert-container');
            container.innerHTML = `<div class="alert alert-${{type}}">${{message}}</div>`;
            setTimeout(() => container.innerHTML = '', 3000);
        }}

        async function saveData(type, data) {{
            try {{
                const response = await fetch('/api/' + type, {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify(data)
                }});
                const result = await response.json();
                if (result.success) {{
                    showAlert('Saved successfully!', 'success');
                }} else {{
                    showAlert('Error saving data', 'error');
                }}
            }} catch (error) {{
                showAlert('Error saving data: ' + error.message, 'error');
            }}
        }}

        // Form handlers
        document.getElementById('profile-form')?.addEventListener('submit', async (e) => {{
            e.preventDefault();
            const formData = new FormData(e.target);
            const data = Object.fromEntries(formData);
            await saveData('profile', data);
        }});

        document.getElementById('application-form')?.addEventListener('submit', async (e) => {{
            e.preventDefault();
            const formData = new FormData(e.target);
            const data = Object.fromEntries(formData);
            await saveData('application', data);
        }});
    </script>
</body>
</html>
"""


def get_dashboard_content(stats: dict) -> str:
    """Generate dashboard content."""
    return f"""
    <div class="card">
        <h2>📊 Career Overview</h2>
        <div class="stats-grid">
            <div class="stat-card">
                <div class="number">{stats.get('total_applications', 0)}</div>
                <div class="label">Applications</div>
            </div>
            <div class="stat-card">
                <div class="number">{stats.get('total_interviews', 0)}</div>
                <div class="label">Interviews</div>
            </div>
            <div class="stat-card">
                <div class="number">{stats.get('total_skills', 0)}</div>
                <div class="label">Skills</div>
            </div>
            <div class="stat-card">
                <div class="number">{stats.get('network_contacts', 0)}</div>
                <div class="label">Contacts</div>
            </div>
            <div class="stat-card">
                <div class="number">{stats.get('active_goals', 0)}</div>
                <div class="label">Active Goals</div>
            </div>
        </div>
    </div>

    <div class="card">
        <h2>📈 Application Pipeline</h2>
        <div class="stats-grid">
            <div class="stat-card" style="background: #6c757d;">
                <div class="number">{stats.get('application_stats', {}).get('applied', 0)}</div>
                <div class="label">Applied</div>
            </div>
            <div class="stat-card" style="background: #17a2b8;">
                <div class="number">{stats.get('application_stats', {}).get('screening', 0)}</div>
                <div class="label">Screening</div>
            </div>
            <div class="stat-card" style="background: #ffc107;">
                <div class="number">{stats.get('application_stats', {}).get('interview', 0)}</div>
                <div class="label">Interview</div>
            </div>
            <div class="stat-card" style="background: #28a745;">
                <div class="number">{stats.get('application_stats', {}).get('offer', 0)}</div>
                <div class="label">Offers</div>
            </div>
        </div>
    </div>
    """


def get_profile_content(profile: dict) -> str:
    """Generate profile form content."""
    personal = profile.get('personal_info', {})
    social = profile.get('social_links', {})
    prefs = profile.get('preferences', {})

    return f"""
    <div class="card">
        <h2>👤 Personal Information</h2>
        <form id="profile-form">
            <div class="form-grid">
                <div class="form-group">
                    <label>Full Name</label>
                    <input type="text" name="name" value="{personal.get('name', '')}" placeholder="John Doe">
                </div>
                <div class="form-group">
                    <label>Email</label>
                    <input type="email" name="email" value="{personal.get('email', '')}" placeholder="john@example.com">
                </div>
                <div class="form-group">
                    <label>Phone</label>
                    <input type="tel" name="phone" value="{personal.get('phone', '')}" placeholder="+1 234 567 8900">
                </div>
                <div class="form-group">
                    <label>Location</label>
                    <input type="text" name="location" value="{personal.get('location', '')}" placeholder="San Francisco, CA">
                </div>
                <div class="form-group">
                    <label>Current Title</label>
                    <input type="text" name="title" value="{personal.get('title', '')}" placeholder="Software Engineer">
                </div>
                <div class="form-group">
                    <label>Professional Summary</label>
                    <textarea name="summary" placeholder="Brief professional summary...">{personal.get('summary', '')}</textarea>
                </div>
            </div>

            <h3 style="margin-top: 20px; margin-bottom: 15px; color: #333;">Social Links</h3>
            <div class="form-grid">
                <div class="form-group">
                    <label>LinkedIn</label>
                    <input type="text" name="linkedin" value="{social.get('linkedin', '')}" placeholder="linkedin.com/in/johndoe">
                </div>
                <div class="form-group">
                    <label>GitHub</label>
                    <input type="text" name="github" value="{social.get('github', '')}" placeholder="github.com/johndoe">
                </div>
                <div class="form-group">
                    <label>Portfolio</label>
                    <input type="text" name="portfolio" value="{social.get('portfolio', '')}" placeholder="johndoe.com">
                </div>
                <div class="form-group">
                    <label>Website</label>
                    <input type="text" name="website" value="{social.get('website', '')}" placeholder="personal-site.com">
                </div>
            </div>

            <h3 style="margin-top: 20px; margin-bottom: 15px; color: #333;">Job Search Preferences</h3>
            <div class="form-grid">
                <div class="form-group">
                    <label>Job Search Status</label>
                    <select name="job_search_status">
                        <option value="open" {'selected' if prefs.get('job_search_status') == 'open' else ''}>Actively Looking</option>
                        <option value="casually_looking" {'selected' if prefs.get('job_search_status') == 'casually_looking' else ''}>Casually Looking</option>
                        <option value="not_looking" {'selected' if prefs.get('job_search_status') == 'not_looking' else ''}>Not Looking</option>
                    </select>
                </div>
                <div class="form-group">
                    <label>Preferred Work Type</label>
                    <select name="preferred_work_type">
                        <option value="remote" {'selected' if prefs.get('preferred_work_type') == 'remote' else ''}>Remote</option>
                        <option value="hybrid" {'selected' if prefs.get('preferred_work_type') == 'hybrid' else ''}>Hybrid</option>
                        <option value="onsite" {'selected' if prefs.get('preferred_work_type') == 'onsite' else ''}>On-site</option>
                    </select>
                </div>
                <div class="form-group">
                    <label>Salary Min</label>
                    <input type="number" name="salary_min" value="{prefs.get('salary_range', {}).get('min', '')}" placeholder="80000">
                </div>
                <div class="form-group">
                    <label>Salary Max</label>
                    <input type="number" name="salary_max" value="{prefs.get('salary_range', {}).get('max', '')}" placeholder="120000">
                </div>
            </div>

            <button type="submit" class="btn" style="margin-top: 20px;">Save Profile</button>
        </form>
    </div>
    """


def get_resume_content(resume: dict) -> str:
    """Generate resume content."""
    sections = resume.get('sections', {})
    experience = sections.get('experience', [])
    education = sections.get('education', [])
    skills = sections.get('skills', [])

    exp_html = ""
    for exp in experience:
        exp_html += f"""
        <div class="list-item">
            <div>
                <div class="title">{exp.get('title', 'Position')}</div>
                <div class="meta">{exp.get('company', 'Company')} • {exp.get('start_date', '')} - {exp.get('end_date', 'Present')}</div>
            </div>
            <span class="tag">Experience</span>
        </div>
        """

    skills_html = ", ".join([s.get('name', '') for s in skills]) if skills else "No skills added yet"

    return f"""
    <div class="card">
        <h2>📄 Resume Overview</h2>
        <p style="color: #666; margin-bottom: 20px;">Manage your resume through the MCP tools or use the API.</p>

        <h3 style="margin-bottom: 15px; color: #333;">Summary</h3>
        <p style="background: #f8f9fa; padding: 15px; border-radius: 8px;">{sections.get('summary', 'No summary added yet.')}</p>

        <h3 style="margin: 20px 0 15px; color: #333;">Experience</h3>
        {exp_html if exp_html else '<p style="color: #666;">No experience entries yet.</p>'}

        <h3 style="margin: 20px 0 15px; color: #333;">Skills</h3>
        <p style="background: #f8f9fa; padding: 15px; border-radius: 8px;">{skills_html}</p>

        <button class="btn btn-secondary" style="margin-top: 20px;" onclick="showAlert('Use MCP tools to edit resume details', 'success')">Edit via MCP</button>
    </div>
    """


def get_applications_content(applications: dict) -> str:
    """Generate applications content."""
    apps = applications.get('applications', [])

    apps_html = ""
    for app in apps[:10]:  # Show last 10
        status = app.get('status', 'saved')
        apps_html += f"""
        <div class="list-item">
            <div>
                <div class="title">{app.get('position', 'Position')}</div>
                <div class="meta">{app.get('company', 'Company')} • Updated: {app.get('updated_at', 'N/A')[:10]}</div>
            </div>
            <span class="tag {status}">{status.title()}</span>
        </div>
        """

    return f"""
    <div class="card">
        <h2>💼 Job Applications</h2>

        <h3 style="margin-bottom: 15px; color: #333;">Add New Application</h3>
        <form id="application-form">
            <div class="form-grid">
                <div class="form-group">
                    <label>Company *</label>
                    <input type="text" name="company" required placeholder="Company name">
                </div>
                <div class="form-group">
                    <label>Position *</label>
                    <input type="text" name="position" required placeholder="Job title">
                </div>
                <div class="form-group">
                    <label>Location</label>
                    <input type="text" name="location" placeholder="Job location">
                </div>
                <div class="form-group">
                    <label>URL</label>
                    <input type="url" name="url" placeholder="Job posting URL">
                </div>
                <div class="form-group">
                    <label>Salary</label>
                    <input type="text" name="salary" placeholder="Salary range">
                </div>
                <div class="form-group">
                    <label>Status</label>
                    <select name="status">
                        <option value="saved">Saved</option>
                        <option value="applied">Applied</option>
                        <option value="screening">Screening</option>
                        <option value="interview">Interview</option>
                        <option value="offer">Offer</option>
                        <option value="rejected">Rejected</option>
                    </select>
                </div>
            </div>
            <div class="form-group">
                <label>Notes</label>
                <textarea name="notes" placeholder="Any notes about this application..."></textarea>
            </div>
            <button type="submit" class="btn">Add Application</button>
        </form>

        <h3 style="margin: 30px 0 15px; color: #333;">Recent Applications</h3>
        {apps_html if apps_html else '<p style="color: #666;">No applications yet. Add your first one above!</p>'}
    </div>
    """


def get_interviews_content(interviews: dict) -> str:
    """Generate interviews content."""
    sessions = interviews.get('sessions', [])
    questions = interviews.get('questions_bank', [])

    sessions_html = ""
    for session in sessions[:5]:
        sessions_html += f"""
        <div class="list-item">
            <div>
                <div class="title">{session.get('company', 'Company')}</div>
                <div class="meta">{session.get('position', 'Position')} • {session.get('date', 'Date')} • {session.get('round_type', 'Round')}</div>
            </div>
            <span class="tag">{session.get('round_type', 'Interview')}</span>
        </div>
        """

    return f"""
    <div class="card">
        <h2>🎯 Interview Preparation</h2>

        <h3 style="margin-bottom: 15px; color: #333;">Recent Interview Sessions</h3>
        {sessions_html if sessions_html else '<p style="color: #666;">No interview sessions logged yet.</p>'}

        <h3 style="margin: 30px 0 15px; color: #333;">Practice Questions</h3>
        <p style="color: #666; margin-bottom: 20px;">Use MCP tools to generate interview questions and practice.</p>

        <button class="btn" onclick="showAlert('Use MCP interview tools for practice sessions', 'success')">Start Practice</button>
    </div>
    """


def get_skills_content(skills: dict) -> str:
    """Generate skills content."""
    technical = skills.get('technical', [])
    soft = skills.get('soft', [])
    learning = skills.get('learning', [])

    tech_html = ""
    for skill in technical[:10]:
        tech_html += f'<span class="tag" style="margin: 5px;">{skill.get("name", "Skill")} ({skill.get("level", "")})</span>'

    soft_html = ""
    for skill in soft[:10]:
        soft_html += f'<span class="tag" style="margin: 5px;">{skill.get("name", "Skill")}</span>'

    learning_html = ""
    for skill in learning[:5]:
        learning_html += f"""
        <div class="list-item">
            <div>
                <div class="title">{skill.get('skill', 'Skill')}</div>
                <div class="meta">Priority: {skill.get('priority', 'medium')} • Progress: {skill.get('progress', 0)}%</div>
            </div>
            <span class="tag">{skill.get('status', 'in_progress')}</span>
        </div>
        """

    return f"""
    <div class="card">
        <h2>🛠️ Skills Inventory</h2>

        <h3 style="margin-bottom: 15px; color: #333;">Technical Skills</h3>
        <div style="background: #f8f9fa; padding: 15px; border-radius: 8px;">
            {tech_html if tech_html else '<span style="color: #666;">No technical skills added yet.</span>'}
        </div>

        <h3 style="margin: 20px 0 15px; color: #333;">Soft Skills</h3>
        <div style="background: #f8f9fa; padding: 15px; border-radius: 8px;">
            {soft_html if soft_html else '<span style="color: #666;">No soft skills added yet.</span>'}
        </div>

        <h3 style="margin: 20px 0 15px; color: #333;">Learning Goals</h3>
        {learning_html if learning_html else '<p style="color: #666;">No learning goals set yet.</p>'}

        <button class="btn btn-secondary" style="margin-top: 20px;" onclick="showAlert('Use MCP tools to manage skills', 'success')">Manage Skills</button>
    </div>
    """


def get_network_content(network: dict) -> str:
    """Generate network content."""
    contacts = network.get('contacts', [])

    contacts_html = ""
    for contact in contacts[:10]:
        contacts_html += f"""
        <div class="list-item">
            <div>
                <div class="title">{contact.get('name', 'Name')}</div>
                <div class="meta">{contact.get('title', 'Title')} at {contact.get('company', 'Company')}</div>
            </div>
            <span class="tag">Contact</span>
        </div>
        """

    return f"""
    <div class="card">
        <h2>🤝 Network</h2>

        <h3 style="margin-bottom: 15px; color: #333;">Contacts ({len(contacts)} total)</h3>
        {contacts_html if contacts_html else '<p style="color: #666;">No contacts added yet.</p>'}

        <button class="btn btn-secondary" style="margin-top: 20px;" onclick="showAlert('Use MCP tools to manage contacts', 'success')">Manage Contacts</button>
    </div>
    """


def get_goals_content(goals: dict) -> str:
    """Generate goals content."""
    short_term = goals.get('short_term', [])
    long_term = goals.get('long_term', [])
    achievements = goals.get('achievements', [])

    active_short = [g for g in short_term if g.get('status') == 'active']

    goals_html = ""
    for goal in active_short[:5]:
        goals_html += f"""
        <div class="list-item">
            <div>
                <div class="title">{goal.get('goal', 'Goal')}</div>
                <div class="meta">Progress: {goal.get('progress', 0)}% • Target: {goal.get('target_date', 'No date')}</div>
            </div>
            <span class="tag {goal.get('priority', 'medium')}">{goal.get('priority', 'medium').title()}</span>
        </div>
        """

    achievements_html = ""
    for achievement in achievements[:5]:
        achievements_html += f"""
        <div class="list-item">
            <div>
                <div class="title">{achievement.get('goal', 'Achievement')}</div>
                <div class="meta">Completed: {achievement.get('completed_at', 'Date')[:10]}</div>
            </div>
            <span class="tag active">✓ Done</span>
        </div>
        """

    return f"""
    <div class="card">
        <h2>🎯 Goals & Achievements</h2>

        <h3 style="margin-bottom: 15px; color: #333;">Active Goals</h3>
        {goals_html if goals_html else '<p style="color: #666;">No active goals. Set some goals to track your progress!</p>'}

        <h3 style="margin: 30px 0 15px; color: #333;">Achievements</h3>
        {achievements_html if achievements_html else '<p style="color: #666;">No achievements yet. Complete goals to see them here!</p>'}

        <button class="btn btn-secondary" style="margin-top: 20px;" onclick="showAlert('Use MCP tools to manage goals', 'success')">Manage Goals</button>
    </div>
    """


class WebUIHandler(SimpleHTTPRequestHandler):
    """Custom handler for the Web UI."""

    def do_GET(self):
        """Handle GET requests."""
        parsed_path = urlparse(self.path)

        if parsed_path.path == '/' or parsed_path.path == '/index.html':
            self.serve_dashboard()
        elif parsed_path.path.startswith('/api/'):
            self.handle_api_get(parsed_path.path[5:])
        else:
            self.send_error(404, "Not Found")

    def do_POST(self):
        """Handle POST requests."""
        parsed_path = urlparse(self.path)

        if parsed_path.path.startswith('/api/'):
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)
            self.handle_api_post(parsed_path.path[5:], body)
        else:
            self.send_error(404, "Not Found")

    def serve_dashboard(self):
        """Serve the main dashboard."""
        ensure_data_dir()

        stats = get_stats()
        profile = load_data('profile')
        resume = load_data('resume')
        applications = load_data('applications')
        interviews = load_data('interviews')
        skills = load_data('skills')
        network = load_data('network')
        goals = load_data('goals')

        html = HTML_TEMPLATE.format(
            dashboard_content=get_dashboard_content(stats),
            profile_content=get_profile_content(profile),
            resume_content=get_resume_content(resume),
            applications_content=get_applications_content(applications),
            interviews_content=get_interviews_content(interviews),
            skills_content=get_skills_content(skills),
            network_content=get_network_content(network),
            goals_content=get_goals_content(goals),
        )

        self.send_response(200)
        self.send_header('Content-Type', 'text/html')
        self.end_headers()
        self.wfile.write(html.encode())

    def handle_api_get(self, endpoint):
        """Handle API GET requests."""
        ensure_data_dir()

        if endpoint == 'stats':
            data = get_stats()
        elif endpoint in ['profile', 'resume', 'applications', 'interviews', 'skills', 'network', 'goals']:
            data = load_data(endpoint)
        else:
            self.send_error(404, "Not Found")
            return

        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def handle_api_post(self, endpoint, body):
        """Handle API POST requests."""
        ensure_data_dir()

        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            self.send_error(400, "Invalid JSON")
            return

        if endpoint == 'profile':
            profile = load_data('profile')

            # Update personal info
            if 'name' in data or 'email' in data or 'phone' in data or 'location' in data or 'title' in data or 'summary' in data:
                profile['personal_info'] = profile.get('personal_info', {})
                for field in ['name', 'email', 'phone', 'location', 'title', 'summary']:
                    if field in data:
                        profile['personal_info'][field] = data[field]

            # Update social links
            if any(k in data for k in ['linkedin', 'github', 'portfolio', 'website']):
                profile['social_links'] = profile.get('social_links', {})
                for field in ['linkedin', 'github', 'portfolio', 'website']:
                    if field in data:
                        profile['social_links'][field] = data[field]

            # Update preferences
            if any(k in data for k in ['job_search_status', 'preferred_work_type', 'salary_min', 'salary_max']):
                profile['preferences'] = profile.get('preferences', {})
                if 'job_search_status' in data:
                    profile['preferences']['job_search_status'] = data['job_search_status']
                if 'preferred_work_type' in data:
                    profile['preferences']['preferred_work_type'] = data['preferred_work_type']
                if 'salary_min' in data or 'salary_max' in data:
                    profile['preferences']['salary_range'] = profile['preferences'].get('salary_range', {})
                    if 'salary_min' in data:
                        profile['preferences']['salary_range']['min'] = int(data['salary_min']) if data['salary_min'] else None
                    if 'salary_max' in data:
                        profile['preferences']['salary_range']['max'] = int(data['salary_max']) if data['salary_max'] else None

            save_data('profile', profile)
            self.send_json_response({'success': True, 'data': profile})

        elif endpoint == 'application':
            import uuid
            from datetime import datetime

            applications = load_data('applications')
            apps = applications.get('applications', [])

            app = {
                'id': str(uuid.uuid4())[:8],
                'company': data.get('company'),
                'position': data.get('position'),
                'location': data.get('location'),
                'url': data.get('url'),
                'salary': data.get('salary'),
                'notes': data.get('notes'),
                'status': data.get('status', 'saved'),
                'status_history': [{'status': data.get('status', 'saved'), 'date': datetime.now().isoformat()}],
                'timeline': [{'event': 'Application created', 'date': datetime.now().isoformat()}],
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat(),
            }

            apps.append(app)
            applications['applications'] = apps
            applications['stats'] = applications.get('stats', {})
            applications['stats']['total'] = len(apps)
            applications['stats'][app['status']] = applications['stats'].get(app['status'], 0) + 1

            save_data('applications', applications)
            self.send_json_response({'success': True, 'data': app})

        else:
            self.send_error(404, "Not Found")

    def send_json_response(self, data):
        """Send a JSON response."""
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def log_message(self, format, *args):
        """Suppress default logging."""
        pass


def run_webui(port: int = 8080, open_browser: bool = True):
    """Run the Web UI server."""
    ensure_data_dir()

    server = HTTPServer(('localhost', port), WebUIHandler)

    url = f"http://localhost:{port}"
    print(f"🚀 Career Manager Web UI running at {url}")

    if open_browser:
        threading.Timer(1, lambda: webbrowser.open(url)).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n👋 Shutting down...")
        server.shutdown()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Career Manager Web UI")
    parser.add_argument("--port", type=int, default=8080, help="Port to run on")
    parser.add_argument("--no-browser", action="store_true", help="Don't open browser")

    args = parser.parse_args()
    run_webui(port=args.port, open_browser=not args.no_browser)