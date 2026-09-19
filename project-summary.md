# Admitly for Institutions — Project Handoff & Progress Brief

> **Hackathon:** Fastn Hackathon, NUST SEECS (September 18–19, 2026)  
> **Team:** Rotten Figs  
> **Project:** Admitly (Institutional Scholarship & Grant Requirement Tracker)  
> **GitHub Repository:** [github.com/eiman-fatimaa/Admitly](https://github.com/eiman-fatimaa/Admitly)

---

## 1. Executive Summary & The Product Pivot

### The Original Idea vs. The Winning B2B2C Model
- **The Old Model (B2C Student Tool):** An individual student tracks their own applications by polling their personal Gmail/Drive and writing to Notion.  
  *Why we changed it:* Individual students are not B2B SaaS buyers, and Notion cannot enforce row-level privacy for multiple users.
- **The New Model (B2B2C Institutional Platform):** Sold to **scholarship foundations, grant programs, and university financial aid offices** to stop staff from manually chasing hundreds of applicants for missing documents.
  - **The Business Customer (Staff):** Pastes a scholarship URL → AI extracts the checklist → Staff views an aggregate status matrix and exports completion metrics to **Google Sheets**.
  - **The End Customer (Applicant):** Receives an invite link to their personal status portal → Receives Gmail reminders when items are missing near deadlines, while staff also receive Slack alerts and Google Sheets completion metrics update through Fastn.

---

## 2. Fastn Platform Components (Already Built, Tested & Live)

We used the **Fastn Platform Agent** to create, test, and publish all cloud integration resources. Nothing needs to be rebuilt on Fastn.

| Asset Name | Type / Slug | ID / URL | Purpose |
|---|---|---|---|
| **Workflow 1: Applicant Notification Delivery** | Workflow | `wf_f9f509207910` | Dispatches targeted Gmail reminders naming missing items and corresponding Slack alerts. |
| **Workflow 1 Webhook Trigger** | Inbound Webhook (`POST`) | `https://webhooks.fastn.dev/prod/triggers/personal_537f9cad7efa339e78b6/webhooks/953464ae-66c7-4105-9e07-8bde695de631` | Endpoint your backend calls when an applicant has missing items near deadline. |
| **Workflow 2: Institution BI & Funnel Export** | Workflow | `wf_98ce0494c1fd` | Computes program completion percentages and appends clean summary rows to Google Sheets. |
| **Workflow 2 Scheduled Trigger** | Cron Schedule | `0 * * * *` (Hourly) | Automated background sync of application completion analytics. |
| **Workflow 2 On-Demand Webhook** | Inbound Webhook (`POST`) | `https://webhooks.fastn.dev/prod/triggers/personal_537f9cad7efa339e78b6/webhooks/c37b085a-6e73-436b-9989-4fc0589cfe22` | Endpoint triggered when staff clicks "Export Now" on the dashboard. |
| **Widget 1: Applicant Notification Hub** | Embed Widget | `wgt_d2d615ad90d2` | Embedded on applicant portal for self-serve Gmail/Slack channel setup (Track 03 compliant). |
| **Widget 2: Institution BI Export Hub** | Embed Widget | `wgt_aabbd2eabb93` | Embedded on admin dashboard for one-click Google Sheets OAuth connection (Track 04 compliant). |

---

## 3. Direct Fastn Authentication Links (For Live Demo)

To demonstrate real Gmail messages or live Google Sheet rows during your presentation:
- **Gmail:** Connected in Fastn.
- **Slack Connect Link:** [Connect Workspace](https://app.fastn.dev/connect/8de5d696-5289-4c9c-ade4-de918d019d06#t=emb_mUBsQ_MHHitcWmT7ZQpwdTnzmdzJuyXVFHgQS5zqJ5g)
- **Google Sheets Connect Link:** [Connect Google Sheets](https://app.fastn.dev/connect/38d254e2-b92e-44f4-81cd-8251fd9373d9#t=emb_1llJKnHgjrbTD6vx0oft0rlxwKm2sQi5KHPLbduYAE0)

---

## 4. Repository Cleanup & File Migration

### Files to REMOVE from the old `Admitly` repository:
```bash
rm -rf sources alert.py config.py extractor.py main.py notion_sync.py seed_notion.py
```
*(Removes outdated personal Gmail/Drive polling and Notion rate-limit bottlenecks).*

### Files to ADD to the repository (already generated in scratchpad):
1. **`models.py`**: SQLite database models and query helpers (`programs`, `requirements`, `applicants`, `applicant_requirements`). Enforces relational foreign keys.
2. **`fastn_client.py`**: Outbound HTTP client that dispatches JSON payloads to Fastn's live webhooks.
3. **`ai_engine.py`**: Webpage scraper + Gemini AI integration for URL checklist extraction and applicant evidence matching.
4. **`app.py`**: Complete Flask application rendering all 5 screens with modern Tailwind CSS and FontAwesome icons.
5. **`requirements.txt`**: Minimal dependencies (`flask`, `requests`, `beautifulsoup4`).
6. **`.env`**: Configuration for `SECRET_KEY` and optional `GEMINI_API_KEY`.
7. **`README.md`**: Complete runbook and demo instructions.

---

## 5. The 5 Application Screens

1. **Screen 1: Programs List (`/admin/programs`)**
   - Displays all active scholarship programs, applicant counts, and deadlines.
   - Includes "+ New Program" modal where pasting any scholarship URL prompts Gemini to scrape requirements.
2. **Screen 2: Program Detail / Matrix Board (`/admin/programs/<id>`)**
   - Core administrative board: rows of applicants vs. columns of requirements.
   - Live color-coded status pills: **Missing (Red)**, **Received (Green)**.
   - "Dispatch Urgent Nudges" button triggering Fastn Workflow 1.
3. **Screen 3: BI & Reporting Hub (`/admin/reporting`)**
   - Shows live completion percentages per program.
   - Embeds Fastn's Google Sheets connector card with an "Export Now" button triggering Fastn Workflow 2.
4. **Screen 4: Applicant Status Page (`/applicant/<token>`)**
   - Passwordless personal portal showing the applicant's checklist items and deadline countdown.
   - Document upload simulator with real-time AI matching that flips items to **Received**.
5. **Screen 5: Applicant Notification Settings (`/applicant/<token>/notifications`)**
   - Fastn Notification Hub where applicants toggle between Gmail and Slack.

---

## 6. How to Run Locally

```bash
# 1. Clone repository
git clone https://github.com/eiman-fatimaa/Admitly.git
cd Admitly

# 2. Install dependencies
pip install flask requests beautifulsoup4

# 3. Start the application
python app.py
```

Open **`http://localhost:5000/seed`** in your browser to seed **Mitacs Global Fellowship** with pre-populated test data.

---

## 7. 2-Minute Demo Script (For Video Submission)

- **0:00–0:25 (The Problem & The Platform):** Open `http://localhost:5000/seed`. Show Mitacs Global Fellowship. Explain that staff pasted a single URL and AI generated the entire checklist automatically.
- **0:25–0:55 (Applicant Experience):** Open Jane Doe's portal link (`/applicant/<token>`). Show her checklist with missing documents. Click into Notification Settings to show Fastn's channel hub where she opts into Gmail alerts.
- **0:55–1:20 (Fastn Nudge Trigger):** Return to the Admin Board. Click **"Fastn: Dispatch Urgent Nudges"**. Show that Fastn Workflow 1 triggered a Gmail/Slack alert detailing Jane's missing items.
- **1:20–1:40 (AI Evidence Matching):** On Jane's portal, upload `transcript_mitacs.pdf`. The AI Evidence Matcher confirms the match, and the badge instantly flips from **Missing (Red)** to **Received (Green)**.
- **1:40–2:00 (Google Sheets BI Export):** Switch to `/admin/reporting`. Click **"Export Now"**. Fastn Workflow 2 appends live summary metrics to the foundation's Google Sheet. Conclude: *"Every notification and every export ran through Fastn's embedded integration layer."*

---

## 8. What's Next / Immediate Checklist for Teammates

- [ ] Delete legacy files (`notion_sync.py`, `sources/`, `alert.py`, etc.) from the git repo.
- [ ] Copy the 5 core files (`models.py`, `fastn_client.py`, `ai_engine.py`, `app.py`, `README.md`) into your local repo.
- [ ] Run `python app.py` and test the flow at `http://localhost:5000/seed`.
- [ ] *(Optional)* Confirm the connected Gmail, Slack, and Google Sheets accounts in Fastn before recording live video.
- [ ] Rehearse and record the 2-minute demo video following Section 7.
