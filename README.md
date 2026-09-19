# Admitly
<img width="1024" height="559" alt="image" src="https://github.com/user-attachments/assets/f00400cd-1e2f-4930-a6d5-d0f169df0953" />

A requirement-tracking and notification orchestration platform for any organization that has to collect documents from a large group of people, on a deadline, without losing track of who's missing what.

Built for the Fastn Hackathon at NUST SEECS, September 18–19, 2026.

**Live at: https://admitly.onrender.com/**
---

## The Problem

Universities, financial aid offices, and scholarship or research grant programs all run the same process every cycle: define what documents an applicant needs, collect them from a large pool of people, and track who's done and who isn't before a hard deadline. A large share of applications stall out for a completely avoidable reason — someone missed one form and nobody caught it in time.

Today that tracking almost always lives in a spreadsheet, and the follow-up almost always means a coordinator manually writing the same reminder email to dozens of applicants, separately pinging the review team on Slack about who's still short, and separately updating a report for the department head or the funding body. It doesn't scale past a small cohort, and it breaks down exactly when volume is highest — the week before a deadline, across every review cycle a financial aid or grants office runs in a year.

## What Admitly Does

Admitly is a requirement-tracking and applicant-communication platform built for this market — university financial aid offices, scholarship foundations, and grant-making programs — and built as a reusable engine rather than a one-off tool, so it holds up as a product a financial aid office can actually run every cycle, not just a demo for one fellowship:

1. **Checklist generation, automated.** An admin points Admitly at a program page — a scholarship listing, a fellowship announcement, a grant call — and Gemini AI extracts a structured requirement checklist. Admins can also define or edit requirements directly, so the platform doesn't depend on there being a scrapeable page.
2. **Applicant tracking at scale.** Every applicant gets a private, token-based portal showing exactly what they still owe and when it's due — no account or password to manage, which matters when an office is running hundreds of applicants through several programs at once.
3. **Automated verification.** When an applicant uploads a document, an AI evidence matcher checks it against the outstanding requirement and updates their status without a staff member opening every file.
4. **Multi-channel orchestration, handled by Fastn.** This is the part that actually solves the coordination problem for a financial aid or grants team, and it's entirely built on the Fastn platform rather than hand-rolled integration code. See below.

Because the data model separates programs, requirements, and applicants cleanly, one Admitly deployment can serve a university's entire aid office — undergraduate scholarships, graduate fellowships, and externally funded grants — as separate programs with their own requirements, applicants, and notification destinations, rather than needing a separate tool per program.

## How the System Is Connected

```
        Requirement source (URL, policy doc, or manual entry)
                        |
                        v
        Gemini AI extracts a structured requirement checklist
                        |
                        v
        Admitly core (Flask + SQLite)
        tracks programs, requirements, people, and status
                        |
        +---------------+----------------+
        |                                |
   Person uploads a document        Admin triggers a nudge
        |                                |
        v                                v
   Gemini evidence matcher      Fastn workflow: outbound dispatch
   verifies + updates status            |
                              +----------+----------+
                              |                     |
                              v                     v
                            Gmail                 Slack
                        (person gets a         (staff gets an
                         reminder + link)        alert)

        Separately, on a schedule or on demand:
        Admitly -> Fastn workflow -> Google Sheets
        (completion metrics kept current for reporting)
```

The application itself only ever talks to Fastn's webhook endpoints. It has no direct Gmail, Slack, or Google Sheets integration code — all of that routing, formatting, and delivery logic lives inside Fastn workflows. That separation is deliberate: adding a new notification channel (SMS, Microsoft Teams, a CRM, another spreadsheet) means adding a step inside Fastn, not shipping a new version of the application.

## Where Fastn Does the Work

The Fastn Platform Agent was used to build every connector, trigger, and workflow in this project — none of it is hand-written integration code sitting inside the Flask app. Concretely:

| Fastn Component | Type | ID | What it does |
|---|---|---|---|
| Workflow 1 | Workflow | `wf_f9f509207910` | Takes a payload of people with missing requirements, formats a per-person reminder, and fans it out to Gmail and Slack in the same run |
| Workflow 1 webhook | Inbound webhook | `.../webhooks/953464ae-66c7-4105-9e07-8bde695de631` | Entry point Admitly calls when an admin dispatches a nudge |
| Workflow 2 | Workflow | `wf_98ce0494c1fd` | Aggregates completion rates across a program and appends a row to Google Sheets |
| Workflow 2 scheduler | Cron trigger | `0 * * * *` (hourly) | Keeps the Sheets export current without anyone asking for it |
| Workflow 2 webhook | Inbound webhook | `.../webhooks/c37b085a-6e73-436b-9989-4fc0589cfe22` | Lets an admin force an immediate sync or retry a failed one |
| Widget 1 | Embedded widget | `wgt_d2d615ad90d2` | Lets a person set their own notification preferences without touching admin config |
| Widget 2 | Embedded widget | `wgt_aabbd2eabb93` | One-click OAuth connection flow for Google Sheets, built and embedded through Fastn |

**Live connections used in this build:** Gmail, Slack, Google Sheets — each authenticated and tested through Fastn's connection layer, not through separately managed API keys in the application.

**Fastn workspace:** `personal_537f9cad7efa339e78b6`

The reason this matters for a production reading of the product: the notification and reporting layer — the part every financial aid office will want pointed at its own tools (its own Slack workspace, its own reporting spreadsheet, eventually its own CRM or student information system) — is the part built entirely on Fastn. Onboarding a new university or foundation doesn't mean a code change or a redeploy; it means pointing the same Fastn workflow at their Gmail, their Slack, their Sheets, which is exactly the kind of per-customer configuration Fastn is built to make fast.

## Market and Customers

Admitly is aimed at institutions that run applicant-facing document collection on a deadline:

- **University financial aid and scholarship offices**, running multiple award cycles a year across undergraduate and graduate programs.
- **Scholarship and grant-making foundations** that manage applicants outside a university's own systems.
- **Research grant programs** (fellowships, research awards) that need the same checklist-and-deadline tracking with an academic audience.

The buyer is the office coordinating the program — a financial aid director, a scholarship program manager, a grants administrator — and the beneficiary on the other side is the applicant, which is what makes this a B2B2C platform: sold to the institution, used daily by the people applying to it.

## Why This Is a Product, Not a Script

- **Multi-program by design.** Programs, requirements, and applicants are all scoped, so one deployment can serve a university's entire aid office — separate scholarships, fellowships, and grants — without data crossing between them.
- **Channel-agnostic notification layer.** Because delivery is delegated to Fastn workflows, adding a channel a given institution already uses doesn't require touching Admitly's codebase.
- **Deduplication and conflict handling.** Database constraints prevent duplicate invitations or double-counted statuses, and a manual retry path exists for when an external sync fails partway through.
- **Fails safe.** If the Gemini API key is missing or rate-limited, a deterministic keyword-matching fallback keeps the checklist and matching features working — the product degrades gracefully instead of breaking during a busy admissions cycle.
- **No account sprawl for applicants.** Applicants get a token-linked portal, not a password to manage, which is what actually makes tracking hundreds of applicants across several programs practical for a small aid office staff.

## Team

- **Team name:** Rotten Figs
- **Members:** Eiman Fatima, Tatheer Aima Naqvi

## Live Demo

| | |
|---|---|
| **Live app** | https://admitly.onrender.com |
| **Admin login** | Username: `admin` (any value works) · Password: `admin123` |
| **Demo video** | [Add Google Drive link here — sharing set to "anyone with the link"] |

## Screenshots

**1. Admin requirement matrix**

<img width="1746" height="745" alt="image" src="https://github.com/user-attachments/assets/392fa91b-d05d-492a-9ef4-fe0e22ad9a3b" />

**2. Applicant portal**

<img width="1600" height="968" alt="image" src="https://github.com/user-attachments/assets/c7f8ebf2-405f-42f1-98ba-c793a1740040" />
<img width="1600" height="969" alt="image" src="https://github.com/user-attachments/assets/2c23fdf6-9cf4-4be1-b436-4c023769a06f" />

**3. Student - Auto Email notification + portal link**
<img width="1600" height="966" alt="image" src="https://github.com/user-attachments/assets/85837607-3612-4d83-9d46-50905221fc1f" />

**4. Slack Notification + Sheets Log**
<img width="1600" height="842" alt="image" src="https://github.com/user-attachments/assets/9515bc35-df1e-483b-9891-ec2b20a4c0d6" />
<img width="1357" height="575" alt="image" src="https://github.com/user-attachments/assets/d73a1561-eaa9-40b2-9943-fd255e3b7c0a" />

## Technical Notes

- SQLite data layer with foreign-key relationships across programs, requirements, applicants, and per-applicant requirement status.
- Notification dispatch and reporting sync run on a thread pool so triggering a nudge doesn't block the request that started it.
- Unique constraints on email and on (applicant, requirement) pairs prevent duplicate invites and conflicting status writes.
- A manual "Retry Export" action covers cases where a Sheets sync fails partway through.
- Admin routes are protected with HTTP Basic Auth via the `ADMIN_PASSWORD` environment variable.

---

Built by Team Rotten Figs for the Fastn Hackathon, September 2026.
