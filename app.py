"""
app.py - ApplyIQ Flask Web Application
Runs the Admin Dashboard, Applicant Portal, and integrates Fastn workflows & widgets.
"""

import os
from flask import Flask, render_template_string, request, redirect, url_for, flash, jsonify
import models
import ai_engine
import fastn_client

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "applyiq-hackathon-2026-secret")

# Fastn Embed Widget IDs
WIDGET_APPLICANT_NOTIFICATIONS = "wgt_d2d615ad90d2"
WIDGET_INSTITUTION_BI_EXPORT = "wgt_aabbd2eabb93"

# Initialize DB on startup
models.init_db()


# -------------------------------------------------------------
# BASE HTML STYLING (Clean modern Tailwind CSS via CDN)
# -------------------------------------------------------------
BASE_HEAD = """
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{{ title }} - ApplyIQ for Institutions</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
</head>
"""

NAV_BAR = """
<nav class="bg-indigo-900 text-white shadow-md">
  <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
    <div class="flex justify-between h-16">
      <div class="flex items-center space-x-3">
        <i class="fa-solid fa-graduation-cap text-2xl text-indigo-300"></i>
        <span class="font-bold text-xl tracking-tight">ApplyIQ</span>
        <span class="bg-indigo-800 text-indigo-200 text-xs px-2 py-0.5 rounded font-mono">Institution Portal</span>
      </div>
      <div class="flex items-center space-x-4">
        <a href="/admin/programs" class="text-sm font-medium hover:text-indigo-200 px-3 py-2">Programs</a>
        <a href="/admin/reporting" class="text-sm font-medium hover:text-indigo-200 px-3 py-2">BI & Reporting</a>
        <a href="/seed" class="text-xs bg-indigo-700 hover:bg-indigo-600 px-3 py-1.5 rounded text-indigo-100"><i class="fa-solid fa-database mr-1"></i>Reset Demo Data</a>
      </div>
    </div>
  </div>
</nav>
"""


# -------------------------------------------------------------
# ADMIN ROUTES (Screens 1, 2, 3)
# -------------------------------------------------------------

@app.route("/")
def home():
    return redirect("/admin/programs")


@app.route("/admin/programs", methods=["GET"])
def admin_programs():
    """Screen 1: Programs List & URL Scraper Form"""
    conn = models.get_db()
    programs = conn.execute("""
        SELECT p.*, COUNT(DISTINCT a.id) as applicant_count
        FROM programs p
        LEFT JOIN applicants a ON a.program_id = p.id
        GROUP BY p.id
        ORDER BY p.id DESC
    """).fetchall()
    conn.close()

    html = f"""
    <!DOCTYPE html>
    <html>
    {BASE_HEAD}
    <body class="bg-slate-50 min-h-screen text-slate-800">
      {NAV_BAR}
      <main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">

        <div class="flex justify-between items-center mb-6">
          <div>
            <h1 class="text-2xl font-bold text-slate-900">Scholarship & Grant Programs</h1>
            <p class="text-sm text-slate-500">Manage application checklists and track applicant document status.</p>
          </div>
          <button onclick="document.getElementById('new-modal').classList.remove('hidden')" class="bg-indigo-600 hover:bg-indigo-700 text-white font-medium text-sm px-4 py-2.5 rounded-lg shadow-sm flex items-center">
            <i class="fa-solid fa-plus mr-2"></i>New Program (from URL)
          </button>
        </div>

        {{% with messages = get_flashed_messages(with_categories=true) %}}
          {{% if messages %}}
            {{% for category, message in messages %}}
              <div class="mb-4 p-4 rounded-md {{% if category == 'success' %}}bg-emerald-50 text-emerald-800 border border-emerald-200{{% else %}}bg-indigo-50 text-indigo-800 border border-indigo-200{{% endif %}}">
                <i class="fa-solid fa-circle-check mr-1.5"></i> {{{{ message }}}}
              </div>
            {{% endfor %}}
          {{% endif %}}
        {{% endwith %}}

        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {{% for p in programs %}}
            <div class="bg-white rounded-xl border border-slate-200 shadow-sm p-6 hover:shadow-md transition">
              <div class="flex justify-between items-start mb-3">
                <span class="text-xs font-semibold px-2.5 py-1 bg-indigo-50 text-indigo-700 rounded-full">Deadline: {{{{ p.deadline }}}}</span>
                <span class="text-xs text-slate-400 font-mono">ID: #{{{{ p.id }}}}</span>
              </div>
              <h2 class="font-bold text-lg text-slate-900 mb-1">{{{{ p.name }}}}</h2>
              <p class="text-xs text-slate-500 mb-4 truncate"><i class="fa-solid fa-link mr-1"></i>{{{{ p.source_url or 'Manual Entry' }}}}</p>

              <div class="flex items-center justify-between pt-4 border-t border-slate-100">
                <div class="text-sm text-slate-600 font-medium">
                  <i class="fa-solid fa-users mr-1 text-slate-400"></i> {{{{ p.applicant_count }}}} Applicants
                </div>
                <a href="/admin/programs/{{{{ p.id }}}}" class="text-sm font-semibold text-indigo-600 hover:text-indigo-800 flex items-center">
                  Open Board <i class="fa-solid fa-arrow-right ml-1 text-xs"></i>
                </a>
              </div>
            </div>
          {{% else %}}
            <div class="col-span-3 text-center py-12 bg-white rounded-xl border border-dashed border-slate-300 p-8">
              <i class="fa-solid fa-folder-open text-4xl text-slate-300 mb-3"></i>
              <h3 class="font-medium text-slate-700">No programs registered yet</h3>
              <p class="text-sm text-slate-500 mt-1 mb-4">Click "Reset Demo Data" in the nav bar or paste a scholarship URL to create one.</p>
              <a href="/seed" class="inline-flex items-center px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700">
                <i class="fa-solid fa-wand-magic-sparkles mr-2"></i>Seed Mitacs Fellowship Demo
              </a>
            </div>
          {{% endfor %}}
        </div>

        <!-- NEW PROGRAM MODAL (URL Scraper) -->
        <div id="new-modal" class="hidden fixed inset-0 bg-slate-900/50 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <div class="bg-white rounded-2xl max-w-lg w-full p-6 shadow-xl border border-slate-200">
            <div class="flex justify-between items-center mb-4">
              <h3 class="font-bold text-lg text-slate-900"><i class="fa-solid fa-robot text-indigo-600 mr-2"></i>Extract Requirements with AI</h3>
              <button onclick="document.getElementById('new-modal').classList.add('hidden')" class="text-slate-400 hover:text-slate-600">&times;</button>
            </div>
            <p class="text-xs text-slate-500 mb-4">Paste any scholarship or grant webpage URL. Claude AI will scrape the page and automatically build your program's checklist requirements.</p>
            <form action="/admin/programs/new" method="POST" class="space-y-4">
              <div>
                <label class="block text-xs font-semibold text-slate-700 mb-1">Scholarship Page URL</label>
                <input type="url" name="source_url" required placeholder="https://www.mitacs.ca/our-programs/globalink/..." class="w-full text-sm px-3 py-2 border rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none" value="https://www.mitacs.ca/our-programs/globalink-research-award/">
              </div>
              <div class="flex justify-end space-x-2 pt-2">
                <button type="button" onclick="document.getElementById('new-modal').classList.add('hidden')" class="px-4 py-2 text-sm text-slate-600 hover:bg-slate-100 rounded-lg">Cancel</button>
                <button type="submit" class="px-4 py-2 text-sm bg-indigo-600 hover:bg-indigo-700 text-white font-medium rounded-lg flex items-center">
                  <i class="fa-solid fa-sparkles mr-1.5"></i> Extract & Create Program
                </button>
              </div>
            </form>
          </div>
        </div>

      </main>
    </body>
    </html>
    """
    return render_template_string(html, programs=programs, title="Programs List")


@app.route("/admin/programs/new", methods=["POST"])
def admin_create_program_from_url():
    """Extracts checklist via AI and creates Program + Requirement rows"""
    source_url = request.form.get("source_url")
    extracted = ai_engine.extract_requirements_from_url(source_url)

    program_id = models.add_program(
        name=extracted.get("program_name", "New Scholarship Program"),
        source_url=source_url,
        deadline=extracted.get("deadline", "2026-10-31"),
        requirements_list=extracted.get("requirements", [])
    )

    flash(f"AI successfully extracted {len(extracted.get('requirements', []))} checklist requirements for {extracted.get('program_name')}!", "success")
    return redirect(f"/admin/programs/{program_id}")


@app.route("/admin/programs/<int:program_id>", methods=["GET"])
def admin_program_board(program_id):
    """Screen 2: Applicant Requirement Matrix Board"""
    board_data = models.get_program_board(program_id)

    html = """
    <!DOCTYPE html>
    <html>
    """ + BASE_HEAD + """
    <body class="bg-slate-50 min-h-screen text-slate-800">
      """ + NAV_BAR + """
      <main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">

        <div class="mb-6 flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div>
            <div class="flex items-center space-x-2">
              <a href="/admin/programs" class="text-xs text-indigo-600 hover:underline"><i class="fa-solid fa-arrow-left mr-1"></i>All Programs</a>
              <span class="text-slate-300">/</span>
              <span class="text-xs text-slate-500 font-mono">Deadline: {{ board.program.deadline }}</span>
            </div>
            <h1 class="text-2xl font-bold text-slate-900 mt-1">{{ board.program.name }}</h1>
          </div>
          <div class="flex items-center space-x-3">
            <form action="/admin/programs/{{ board.program.id }}/nudge-urgent" method="POST">
              <button type="submit" class="bg-amber-600 hover:bg-amber-700 text-white font-medium text-xs px-3.5 py-2 rounded-lg shadow-sm flex items-center">
                <i class="fa-solid fa-bell mr-1.5"></i>Fastn: Dispatch Urgent Nudges
              </button>
            </form>
            <button onclick="document.getElementById('add-app-modal').classList.remove('hidden')" class="bg-indigo-600 hover:bg-indigo-700 text-white font-medium text-xs px-3.5 py-2 rounded-lg shadow-sm flex items-center">
              <i class="fa-solid fa-user-plus mr-1.5"></i>Add Applicant
            </button>
          </div>
        </div>

        {% with messages = get_flashed_messages(with_categories=true) %}
          {% if messages %}
            {% for category, message in messages %}
              <div class="mb-4 p-4 rounded-md {% if category == 'success' %}bg-emerald-50 text-emerald-800 border border-emerald-200{% else %}bg-indigo-50 text-indigo-800 border border-indigo-200{% endif %}">
                <i class="fa-solid fa-circle-info mr-1.5"></i> {{ message }}
              </div>
            {% endfor %}
          {% endif %}
        {% endwith %}

        <!-- THE REQUIREMENT MATRIX -->
        <div class="bg-white rounded-xl border border-slate-200 shadow-sm overflow-x-auto">
          <table class="w-full text-left border-collapse">
            <thead>
              <tr class="bg-slate-100/75 border-b border-slate-200 text-xs font-semibold text-slate-700">
                <th class="p-4 min-w-[200px]">Applicant</th>
                <th class="p-4 min-w-[120px]">Notification Channel</th>
                {% for req in board.requirements %}
                  <th class="p-4 min-w-[160px]">
                    <div class="font-bold text-slate-900">{{ req.item }}</div>
                    <div class="text-[10px] text-slate-500 font-normal truncate max-w-[150px]">{{ req.description }}</div>
                  </th>
                {% endfor %}
                <th class="p-4 text-right">Applicant Link</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-100 text-sm">
              {% for row in board.matrix %}
                <tr class="hover:bg-slate-50/50">
                  <td class="p-4">
                    <div class="font-semibold text-slate-900">{{ row.applicant.name }}</div>
                    <div class="text-xs text-slate-500 font-mono">{{ row.applicant.email }}</div>
                  </td>
                  <td class="p-4">
                    <span class="inline-flex items-center text-xs px-2.5 py-1 rounded font-medium {% if row.applicant.channel == 'sms' %}bg-emerald-50 text-emerald-700{% else %}bg-blue-50 text-blue-700{% endif %}">
                      <i class="fa-solid {% if row.applicant.channel == 'sms' %}fa-comment-sms{% else %}fa-hashtag{% endif %} mr-1.5"></i>
                      {{ row.applicant.channel|upper }}
                    </span>
                  </td>
                  {% for s in row.statuses %}
                    <td class="p-4">
                      {% if s.status == 'Received' %}
                        <span class="inline-flex items-center text-xs font-semibold px-2.5 py-1 rounded-full bg-emerald-100 text-emerald-800" title="{{ s.last_evidence_snippet }}">
                          <i class="fa-solid fa-check mr-1"></i>Received
                        </span>
                      {% elif s.status == 'Pending' %}
                        <span class="inline-flex items-center text-xs font-semibold px-2.5 py-1 rounded-full bg-amber-100 text-amber-800">
                          <i class="fa-solid fa-clock mr-1"></i>Pending
                        </span>
                      {% else %}
                        <span class="inline-flex items-center text-xs font-semibold px-2.5 py-1 rounded-full bg-rose-100 text-rose-800">
                          <i class="fa-solid fa-xmark mr-1"></i>Missing
                        </span>
                      {% endif %}
                      {% if s.last_evidence_snippet %}
                        <div class="text-[10px] text-slate-400 mt-1 truncate max-w-[130px]" title="{{ s.last_evidence_snippet }}">
                          {{ s.last_evidence_snippet }}
                        </div>
                      {% endif %}
                    </td>
                  {% endfor %}
                  <td class="p-4 text-right">
                    <a href="/applicant/{{ row.applicant.invite_token }}" target="_blank" class="text-xs font-medium text-indigo-600 hover:text-indigo-800 bg-indigo-50 hover:bg-indigo-100 px-2.5 py-1.5 rounded-lg inline-flex items-center">
                      <i class="fa-solid fa-arrow-up-right-from-square mr-1 text-[10px]"></i>View Portal
                    </a>
                  </td>
                </tr>
              {% else %}
                <tr>
                  <td colspan="{{ board.requirements|length + 3 }}" class="text-center py-8 text-slate-500">
                    No applicants added to this program yet.
                  </td>
                </tr>
              {% endfor %}
            </tbody>
          </table>
        </div>

        <!-- ADD APPLICANT MODAL -->
        <div id="add-app-modal" class="hidden fixed inset-0 bg-slate-900/50 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <div class="bg-white rounded-2xl max-w-md w-full p-6 shadow-xl border border-slate-200">
            <h3 class="font-bold text-lg text-slate-900 mb-3"><i class="fa-solid fa-user-plus text-indigo-600 mr-2"></i>Add Applicant</h3>
            <form action="/admin/programs/{{ board.program.id }}/applicants" method="POST" class="space-y-3">
              <div>
                <label class="block text-xs font-semibold text-slate-700 mb-1">Full Name</label>
                <input type="text" name="name" required placeholder="Jane Doe" class="w-full text-sm px-3 py-2 border rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none">
              </div>
              <div>
                <label class="block text-xs font-semibold text-slate-700 mb-1">Email</label>
                <input type="email" name="email" required placeholder="student@example.edu" class="w-full text-sm px-3 py-2 border rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none">
              </div>
              <div>
                <label class="block text-xs font-semibold text-slate-700 mb-1">Notification Channel</label>
                <select name="channel" class="w-full text-sm px-3 py-2 border rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none">
                  <option value="sms">Twilio SMS</option>
                  <option value="slack">Slack Workspace</option>
                </select>
              </div>
              <div>
                <label class="block text-xs font-semibold text-slate-700 mb-1">Destination (Phone or Channel)</label>
                <input type="text" name="destination" required value="+15559876543" class="w-full text-sm px-3 py-2 border rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none">
              </div>
              <div class="flex justify-end space-x-2 pt-3">
                <button type="button" onclick="document.getElementById('add-app-modal').classList.add('hidden')" class="px-4 py-2 text-sm text-slate-600 hover:bg-slate-100 rounded-lg">Cancel</button>
                <button type="submit" class="px-4 py-2 text-sm bg-indigo-600 hover:bg-indigo-700 text-white font-medium rounded-lg">Add Applicant</button>
              </div>
            </form>
          </div>
        </div>

      </main>
    </body>
    </html>
    """
    return render_template_string(html, board=board_data, title=board_data["program"]["name"])


@app.route("/admin/programs/<int:program_id>/applicants", methods=["POST"])
def admin_add_applicant(program_id):
    name = request.form.get("name")
    email = request.form.get("email")
    channel = request.form.get("channel", "sms")
    destination = request.form.get("destination", "+15559876543")

    models.add_applicant(program_id, name, email, channel, destination)
    flash(f"Added applicant {name}. Checklist instantiated with 'Missing' status.", "success")
    return redirect(f"/admin/programs/{program_id}")


@app.route("/admin/programs/<int:program_id>/nudge-urgent", methods=["POST"])
def admin_dispatch_urgent_nudges(program_id):
    """Scans for missing requirements and calls Fastn Workflow 1"""
    urgent_applicants = models.get_urgent_gaps()
    dispatched_count = 0

    for item in urgent_applicants:
        res = fastn_client.dispatch_applicant_nudge(
            applicant_id=item["applicant_id"],
            applicant_name=item["applicant_name"],
            program_name=item["program_name"],
            missing_items=item["missing_items"],
            deadline=item["deadline"],
            channel=item["channel"],
            destination=item["destination"]
        )
        if res.get("success"):
            dispatched_count += 1

    flash(f"Fastn Workflow 1 Triggered: Dispatched missing requirement notifications to {dispatched_count} applicant(s) via Twilio SMS / Slack!", "success")
    return redirect(f"/admin/programs/{program_id}")


# -------------------------------------------------------------
# REPORTING & BI EXPORT (Screen 3)
# -------------------------------------------------------------

@app.route("/admin/reporting", methods=["GET"])
def admin_reporting():
    """Screen 3: Fastn Google Sheets BI Export Hub"""
    bi_stats = models.get_bi_summary()

    html = """
    <!DOCTYPE html>
    <html>
    """ + BASE_HEAD + """
    <body class="bg-slate-50 min-h-screen text-slate-800">
      """ + NAV_BAR + """
      <main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">

        <div class="flex justify-between items-center mb-6">
          <div>
            <h1 class="text-2xl font-bold text-slate-900">Foundation BI & Google Sheets Export</h1>
            <p class="text-sm text-slate-500">Automate real-time application completion analytics to your organization's spreadsheet via Fastn.</p>
          </div>
        </div>

        {% with messages = get_flashed_messages(with_categories=true) %}
          {% if messages %}
            {% for category, message in messages %}
              <div class="mb-4 p-4 rounded-md {% if category == 'success' %}bg-emerald-50 text-emerald-800 border border-emerald-200{% else %}bg-indigo-50 text-indigo-800 border border-indigo-200{% endif %}">
                <i class="fa-solid fa-circle-check mr-1.5"></i> {{ message }}
              </div>
            {% endfor %}
          {% endif %}
        {% endwith %}

        <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">

          <!-- LEFT 2 COLS: METRICS SUMMARY -->
          <div class="lg:col-span-2 space-y-6">
            <div class="bg-white rounded-xl border border-slate-200 shadow-sm p-6">
              <h2 class="font-bold text-lg text-slate-900 mb-4">Current Aggregate Funnel Stats</h2>
              <table class="w-full text-left border-collapse text-sm">
                <thead>
                  <tr class="bg-slate-50 border-b border-slate-200 text-xs text-slate-500">
                    <th class="p-3">Program</th>
                    <th class="p-3">Applicants</th>
                    <th class="p-3">Complete</th>
                    <th class="p-3">Incomplete</th>
                    <th class="p-3">Completion Rate</th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-slate-100">
                  {% for s in stats %}
                    <tr>
                      <td class="p-3 font-semibold text-slate-900">{{ s.program_name }}</td>
                      <td class="p-3">{{ s.total_applicants }}</td>
                      <td class="p-3 text-emerald-600 font-semibold">{{ s.complete_count }}</td>
                      <td class="p-3 text-rose-600 font-semibold">{{ s.missing_count }}</td>
                      <td class="p-3">
                        <span class="inline-flex px-2 py-0.5 rounded text-xs font-bold {% if s.total_applicants > 0 and s.complete_count == s.total_applicants %}bg-emerald-100 text-emerald-800{% else %}bg-amber-100 text-amber-800{% endif %}">
                          {% if s.total_applicants > 0 %}
                            {{ ((s.complete_count / s.total_applicants) * 100)|round|int }}%
                          {% else %}
                            0%
                          {% endif %}
                        </span>
                      </td>
                    </tr>
                  {% endfor %}
                </tbody>
              </table>
            </div>

            <!-- EXPORT ACTION FORM -->
            <div class="bg-white rounded-xl border border-slate-200 shadow-sm p-6">
              <h3 class="font-bold text-base text-slate-900 mb-2">Export to Google Sheets via Fastn</h3>
              <p class="text-xs text-slate-500 mb-4">Fastn Workflow 2 (`applyiq-institution-bi-export`) runs on an automated hourly cron schedule, or you can trigger an on-demand sync now.</p>

              <form action="/admin/reporting/export" method="POST" class="flex flex-col sm:flex-row gap-3">
                <input type="text" name="spreadsheet_id" required value="1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms" placeholder="Google Spreadsheet ID" class="flex-1 text-sm px-3.5 py-2 border rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none">
                <button type="submit" class="bg-indigo-600 hover:bg-indigo-700 text-white font-medium text-sm px-5 py-2 rounded-lg flex items-center justify-center">
                  <i class="fa-solid fa-file-excel mr-2"></i>Export Now
                </button>
              </form>
            </div>
          </div>

          <!-- RIGHT 1 COL: FASTN EMBEDDED CONNECTOR WIDGET -->
          <div class="bg-white rounded-xl border border-slate-200 shadow-sm p-6">
            <div class="flex items-center space-x-2 mb-3">
              <span class="p-2 bg-indigo-50 text-indigo-600 rounded-lg"><i class="fa-solid fa-plug text-sm"></i></span>
              <h3 class="font-bold text-base text-slate-900">Fastn Integration Hub</h3>
            </div>
            <p class="text-xs text-slate-500 mb-4">
              Institution administrators connect their Google Sheets destination via Fastn's embedded connector without sharing OAuth secrets.
            </p>

            <div class="border border-slate-200 rounded-xl p-4 bg-slate-50/50 text-center">
              <img src="https://www.gstatic.com/images/branding/product/1x/sheets_2020q4_48dp.png" class="w-10 h-10 mx-auto mb-2" alt="Sheets">
              <div class="font-bold text-sm text-slate-900">Google Sheets Connector</div>
              <div class="text-[11px] text-slate-500 mb-4">Widget ID: """ + WIDGET_INSTITUTION_BI_EXPORT + """</div>
              <a href="https://app.fastn.dev/connect/38d254e2-b92e-44f4-81cd-8251fd9373d9#t=emb_1llJKnHgjrbTD6vx0oft0rlxwKm2sQi5KHPLbduYAE0" target="_blank" class="block w-full py-2 bg-white border border-slate-300 hover:bg-slate-50 rounded-lg text-xs font-semibold text-slate-700 shadow-sm">
                <i class="fa-solid fa-arrow-up-right-from-square mr-1"></i>Connect Google Sheets
              </a>
            </div>

            <div class="mt-6 text-[11px] text-slate-400 border-t border-slate-100 pt-3">
              <i class="fa-solid fa-clock mr-1"></i>Automated Scheduler: Hourly (`0 * * * *`)
            </div>
          </div>

        </div>

      </main>
    </body>
    </html>
    """
    return render_template_string(html, stats=bi_stats, title="Reporting & BI Export")


@app.route("/admin/reporting/export", methods=["POST"])
def admin_export_sheets():
    """Calls Fastn Workflow 2 via Webhook"""
    spreadsheet_id = request.form.get("spreadsheet_id", "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms")
    bi_stats = models.get_bi_summary()

    res = fastn_client.export_bi_summary(
        spreadsheet_id=spreadsheet_id,
        institution_id="inst_nust_01",
        programs_summary=bi_stats
    )

    if res.get("success"):
        flash(f"Fastn Workflow 2 triggered! Successfully pushed {len(bi_stats)} program completion rows to Google Sheets ({spreadsheet_id}).", "success")
    else:
        flash(f"Export failed: {res.get('error')}", "error")

    return redirect("/admin/reporting")


# -------------------------------------------------------------
# APPLICANT PORTAL ROUTES (Screens 4 & 5)
# -------------------------------------------------------------

@app.route("/applicant/<token>", methods=["GET"])
def applicant_portal(token):
    """Screen 4: Applicant Personal Status & Checklist Page"""
    data = models.get_applicant_portal_data(token)
    if not data:
        return "Invalid applicant invite token", 404

    # Calculate overall completion
    total = len(data["checklist"])
    received = sum(1 for item in data["checklist"] if item["status"] == "Received")
    pct = int((received / total) * 100) if total > 0 else 0

    html = """
    <!DOCTYPE html>
    <html>
    """ + BASE_HEAD + """
    <body class="bg-slate-50 min-h-screen text-slate-800">

      <!-- APPLICANT HEADER -->
      <header class="bg-white border-b border-slate-200">
        <div class="max-w-4xl mx-auto px-4 py-4 flex justify-between items-center">
          <div class="flex items-center space-x-2">
            <span class="font-bold text-lg text-indigo-900">ApplyIQ</span>
            <span class="text-xs text-slate-400">/ Applicant Status Portal</span>
          </div>
          <a href="/applicant/""" + token + """/notifications" class="text-xs bg-indigo-50 hover:bg-indigo-100 text-indigo-700 px-3 py-1.5 rounded-lg font-medium">
            <i class="fa-solid fa-bell mr-1"></i>Notification Settings
          </a>
        </div>
      </header>

      <main class="max-w-4xl mx-auto px-4 py-8">

        <!-- WELCOME BANNER -->
        <div class="bg-indigo-900 text-white rounded-2xl p-6 sm:p-8 shadow-sm mb-6">
          <span class="text-xs font-semibold uppercase tracking-wider text-indigo-300">Application Checklist</span>
          <h1 class="text-2xl sm:text-3xl font-bold mt-1 mb-2">{{ data.applicant.program_name }}</h1>
          <p class="text-sm text-indigo-200">Applicant: <span class="font-semibold text-white">{{ data.applicant.name }}</span> ({{ data.applicant.email }})</p>

          <div class="mt-6 pt-6 border-t border-indigo-800/80 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <div class="text-xs text-indigo-300">Completion Status</div>
              <div class="text-2xl font-bold">""" + str(pct) + """% Complete (""" + str(received) + """/""" + str(total) + """ Requirements)</div>
            </div>
            <div class="bg-indigo-800 px-4 py-2 rounded-xl text-xs font-mono">
              <i class="fa-solid fa-calendar-day mr-1.5 text-indigo-300"></i>Deadline: {{ data.applicant.program_deadline }}
            </div>
          </div>
        </div>

        {% with messages = get_flashed_messages(with_categories=true) %}
          {% if messages %}
            {% for category, message in messages %}
              <div class="mb-6 p-4 rounded-xl bg-emerald-50 text-emerald-800 border border-emerald-200">
                <i class="fa-solid fa-circle-check mr-1.5"></i> {{ message }}
              </div>
            {% endfor %}
          {% endif %}
        {% endwith %}

        <!-- REQUIREMENTS LIST -->
        <div class="bg-white rounded-2xl border border-slate-200 shadow-sm p-6 mb-6">
          <h2 class="font-bold text-lg text-slate-900 mb-4">Required Documents & Evidence</h2>

          <div class="space-y-4">
            {% for item in data.checklist %}
              <div class="flex items-start justify-between p-4 rounded-xl border {% if item.status == 'Received' %}bg-emerald-50/40 border-emerald-200{% else %}bg-slate-50/50 border-slate-200{% endif %}">
                <div class="flex items-start space-x-3">
                  <div class="mt-0.5">
                    {% if item.status == 'Received' %}
                      <span class="w-6 h-6 rounded-full bg-emerald-600 text-white flex items-center justify-center text-xs"><i class="fa-solid fa-check"></i></span>
                    {% else %}
                      <span class="w-6 h-6 rounded-full bg-rose-100 text-rose-600 flex items-center justify-center text-xs font-bold">!</span>
                    {% endif %}
                  </div>
                  <div>
                    <h3 class="font-bold text-sm text-slate-900">{{ item.item }}</h3>
                    <p class="text-xs text-slate-500 mt-0.5">{{ item.description }}</p>
                    {% if item.last_evidence_snippet %}
                      <div class="mt-2 text-[11px] font-mono text-emerald-700 bg-emerald-100/60 px-2 py-0.5 rounded inline-block">
                        <i class="fa-solid fa-file-circle-check mr-1"></i>{{ item.last_evidence_snippet }}
                      </div>
                    {% endif %}
                  </div>
                </div>
                <div>
                  {% if item.status == 'Received' %}
                    <span class="text-xs font-bold text-emerald-700 bg-emerald-100 px-3 py-1 rounded-full">Received</span>
                  {% else %}
                    <span class="text-xs font-bold text-rose-700 bg-rose-100 px-3 py-1 rounded-full">Missing</span>
                  {% endif %}
                </div>
              </div>
            {% endfor %}
          </div>
        </div>

        <!-- EVIDENCE UPLOAD SIMULATOR (Screen 4 Intake) -->
        <div class="bg-white rounded-2xl border border-slate-200 shadow-sm p-6">
          <div class="flex items-center space-x-2 mb-2">
            <i class="fa-solid fa-cloud-arrow-up text-indigo-600"></i>
            <h3 class="font-bold text-base text-slate-900">Submit Document Evidence</h3>
          </div>
          <p class="text-xs text-slate-500 mb-4">Upload a document file or paste your confirmation text. Claude AI will match it to your missing checklist item and update your status in real time.</p>

          <form action="/applicant/""" + token + """/upload" method="POST" class="space-y-3">
            <div>
              <label class="block text-xs font-semibold text-slate-700 mb-1">Document File Name or Reference</label>
              <input type="text" name="filename" required placeholder="official_transcript_verified.pdf" class="w-full text-sm px-3.5 py-2 border rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none">
            </div>
            <div>
              <label class="block text-xs font-semibold text-slate-700 mb-1">Evidence Excerpt / Note</label>
              <textarea name="evidence_text" rows="2" placeholder="Attached certified copy from University Registrar..." class="w-full text-sm px-3.5 py-2 border rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none"></textarea>
            </div>
            <button type="submit" class="w-full bg-indigo-600 hover:bg-indigo-700 text-white font-medium text-sm py-2.5 rounded-lg flex items-center justify-center">
              <i class="fa-solid fa-wand-magic-sparkles mr-2"></i>Match Evidence with AI
            </button>
          </form>
        </div>

      </main>
    </body>
    </html>
    """
    return render_template_string(html, data=data, title="Applicant Checklist")


@app.route("/applicant/<token>/upload", methods=["POST"])
def applicant_upload_evidence(token):
    """Processes uploaded evidence with AI Matcher and updates SQLite"""
    data = models.get_applicant_portal_data(token)
    if not data:
        return "Not found", 404

    filename = request.form.get("filename", "")
    evidence_text = request.form.get("evidence_text", "")

    # Run AI Evidence Matcher
    match_result = ai_engine.match_evidence_to_requirement(
        evidence_text=evidence_text,
        filename=filename,
        requirements_list=data["checklist"]
    )

    matched_item = match_result.get("matched_item")
    if matched_item:
        models.update_applicant_status_by_item(
            email=data["applicant"]["email"],
            requirement_item_name=matched_item,
            status="Received",
            evidence_snippet=match_result.get("snippet", filename)
        )
        flash(f"AI Evidence Matcher confirmed '{filename}' matches requirement: '{matched_item}'! Status flipped to Received.", "success")
    else:
        flash("AI could not match this evidence confidently. Flagged for manual review.", "error")

    return redirect(f"/applicant/{token}")


@app.route("/applicant/<token>/notifications", methods=["GET", "POST"])
def applicant_notifications(token):
    """Screen 5: Fastn Notification Preference Hub"""
    data = models.get_applicant_portal_data(token)
    if not data:
        return "Not found", 404

    if request.method == "POST":
        channel = request.form.get("channel", "sms")
        destination = request.form.get("destination", "+15559876543")

        conn = models.get_db()
        conn.execute("""
            UPDATE applicants
            SET channel = ?, destination = ?
            WHERE invite_token = ?
        """, (channel, destination, token))
        conn.commit()
        conn.close()

        flash("Notification channel preferences updated successfully!", "success")
        return redirect(f"/applicant/{token}/notifications")

    html = """
    <!DOCTYPE html>
    <html>
    """ + BASE_HEAD + """
    <body class="bg-slate-50 min-h-screen text-slate-800">

      <header class="bg-white border-b border-slate-200">
        <div class="max-w-3xl mx-auto px-4 py-4 flex justify-between items-center">
          <a href="/applicant/""" + token + """" class="text-xs text-indigo-600 hover:underline"><i class="fa-solid fa-arrow-left mr-1"></i>Back to Checklist</a>
          <span class="text-xs text-slate-400">Applicant: {{ data.applicant.name }}</span>
        </div>
      </header>

      <main class="max-w-3xl mx-auto px-4 py-8">

        <div class="mb-6">
          <h1 class="text-2xl font-bold text-slate-900">Notification Preferences</h1>
          <p class="text-sm text-slate-500">Choose how ApplyIQ alerts you if requirements are missing as deadlines approach.</p>
        </div>

        {% with messages = get_flashed_messages(with_categories=true) %}
          {% if messages %}
            {% for category, message in messages %}
              <div class="mb-4 p-4 rounded-xl bg-emerald-50 text-emerald-800 border border-emerald-200">
                <i class="fa-solid fa-circle-check mr-1.5"></i> {{ message }}
              </div>
            {% endfor %}
          {% endif %}
        {% endwith %}

        <div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">

          <!-- CHANNEL PREFERENCE FORM -->
          <div class="bg-white rounded-2xl border border-slate-200 shadow-sm p-6">
            <h3 class="font-bold text-base text-slate-900 mb-3">Choose Your Channel</h3>
            <form action="/applicant/""" + token + """/notifications" method="POST" class="space-y-4">
              <div>
                <label class="block text-xs font-semibold text-slate-700 mb-1">Channel</label>
                <select name="channel" class="w-full text-sm px-3.5 py-2 border rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none">
                  <option value="sms" {% if data.applicant.channel == 'sms' %}selected{% endif %}>Twilio SMS Text Message</option>
                  <option value="slack" {% if data.applicant.channel == 'slack' %}selected{% endif %}>Slack Channel / Direct Message</option>
                </select>
              </div>
              <div>
                <label class="block text-xs font-semibold text-slate-700 mb-1">Phone Number or Slack Channel</label>
                <input type="text" name="destination" value="{{ data.applicant.destination }}" required class="w-full text-sm px-3.5 py-2 border rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none">
              </div>
              <button type="submit" class="w-full bg-indigo-600 hover:bg-indigo-700 text-white font-medium text-sm py-2 rounded-lg">
                Save Preferences
              </button>
            </form>
          </div>

          <!-- FASTN EMBEDDED CONNECTOR WIDGET -->
          <div class="bg-white rounded-2xl border border-slate-200 shadow-sm p-6 flex flex-col justify-between">
            <div>
              <div class="flex items-center space-x-2 mb-2">
                <span class="p-2 bg-indigo-50 text-indigo-600 rounded-lg"><i class="fa-solid fa-shield-halved text-sm"></i></span>
                <h3 class="font-bold text-base text-slate-900">Fastn Embedded Auth</h3>
              </div>
              <p class="text-xs text-slate-500 mb-4">
                Fastn manages your communication destination securely. You can connect or disconnect your account anytime.
              </p>
              <div class="space-y-2">
                <a href="https://app.fastn.dev/connect/3d271a90-a3c8-468f-8825-0a942e373d71#t=emb_m-M_Ev2fB-yVBJaGB_05xLkomEVcfC3tktSM2H3bRV0" target="_blank" class="block w-full py-2 bg-slate-50 border border-slate-200 hover:bg-slate-100 rounded-lg text-xs font-medium text-slate-700 text-center">
                  <i class="fa-solid fa-mobile-screen mr-1.5 text-emerald-600"></i>Connect Phone via Twilio
                </a>
                <a href="https://app.fastn.dev/connect/8de5d696-5289-4c9c-ade4-de918d019d06#t=emb_mUBsQ_MHHitcWmT7ZQpwdTnzmdzJuyXVFHgQS5zqJ5g" target="_blank" class="block w-full py-2 bg-slate-50 border border-slate-200 hover:bg-slate-100 rounded-lg text-xs font-medium text-slate-700 text-center">
                  <i class="fa-brands fa-slack mr-1.5 text-indigo-600"></i>Connect Slack Workspace
                </a>
              </div>
            </div>
            <div class="mt-4 pt-4 border-t border-slate-100 text-[10px] text-slate-400">
              Widget ID: """ + WIDGET_APPLICANT_NOTIFICATIONS + """ (Track 03 Compliant)
            </div>
          </div>

        </div>

      </main>
    </body>
    </html>
    """
    return render_template_string(html, data=data, title="Notification Preferences")


# -------------------------------------------------------------
# QUICK DEMO SEED ROUTE
# -------------------------------------------------------------

@app.route("/seed")
def seed_route():
    seed_info = models.seed_demo_data()
    flash(f"Seeded Mitacs Global Fellowship with 3 applicants (Jane Doe token: {seed_info['applicant_tokens']['jane_doe']})!", "success")
    return redirect(f"/admin/programs/{seed_info['program_id']}")


if __name__ == "__main__":
    print("Starting ApplyIQ on http://localhost:5000 ...")
    app.run(host="0.0.0.0", port=5000, debug=True)
