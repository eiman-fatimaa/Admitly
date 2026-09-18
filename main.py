python
from datetime import datetime, timedelta

from sources.gmail_watcher import fetch_recent_emails
from sources.drive_watcher import fetch_recent_files
from extractor import extract_application_event
from notion_sync import upsert_requirement, fastn
from alert import send_alert
from config import NOTION_DATABASE_ID

URGENCY_WINDOW_DAYS = 5

def process_item(content: str):
    event = extract_application_event(content)
    if not event.get("school"):
        return  # not application-related, skip

    action, page_id = upsert_requirement(
        school=event["school"],
        document_type=event["document_type"],
        status=event["status"],
        deadline=event.get("deadline_mentioned"),
        notes=event.get("notes", ""),
    )
    print(f"[main] {action} row for {event['school']} / {event['document_type']}")

def check_urgent_gaps():
    """
    Pull the full board, group by school, and alert on any school with
    missing items inside the urgency window.
    ⚠️ VERIFY: query_database call shape — same caveat as notion_sync.py
    """
    all_rows = fastn.notion.query_database(database_id=NOTION_DATABASE_ID, filter={})
    by_school = {}
    for row in all_rows.get("results", []):
        props = row["properties"]
        school = props["School"]["title"][0]["text"]["content"]
        status = props["Status"]["select"]["name"]
        deadline_prop = props.get("Deadline", {}).get("date")
        deadline = deadline_prop["start"] if deadline_prop else None

        by_school.setdefault(school, {"missing": [], "deadline": deadline})
        if status == "Missing":
            by_school[school]["missing"].append(props["Document"]["rich_text"][0]["text"]["content"])

    today = datetime.now().date()
    for school, info in by_school.items():
        if not info["missing"] or not info["deadline"]:
            continue
        deadline_date = datetime.fromisoformat(info["deadline"]).date()
        days_left = (deadline_date - today).days
        if 0 <= days_left <= URGENCY_WINDOW_DAYS:
            send_alert(school, info["missing"], days_left)

def run_once():
    for email in fetch_recent_emails():
        process_item(f"Subject: {email['subject']}\n\n{email['body']}")
    for file in fetch_recent_files():
        process_item(f"Filename: {file['name']}\n\n{file['content']}")
    check_urgent_gaps()

if __name__ == "__main__":
    run_once()