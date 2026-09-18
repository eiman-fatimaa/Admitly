python
from fastn import FastnClient
from config import NOTION_DATABASE_ID

fastn = FastnClient()

def find_existing_row(school: str, document_type: str):
    """
    ⚠️ VERIFY: exact query/filter shape — Notion's own API uses this structure
    (database query with a filter object), Fastn's connector likely mirrors it,
    but confirm with: fastn connector ls notion
    """
    results = fastn.notion.query_database(
        database_id=NOTION_DATABASE_ID,
        filter={
            "and": [
                {"property": "School", "title": {"equals": school}},
                {"property": "Document", "rich_text": {"equals": document_type}},
            ]
        },
    )
    pages = results.get("results", [])
    return pages[0] if pages else None

def upsert_requirement(school: str, document_type: str, status: str, deadline: str, notes: str):
    existing = find_existing_row(school, document_type)

    properties = {
        "School": {"title": [{"text": {"content": school}}]},
        "Document": {"rich_text": [{"text": {"content": document_type}}]},
        "Status": {"select": {"name": status.capitalize()}},
        "Notes": {"rich_text": [{"text": {"content": notes or ""}}]},
    }
    if deadline:
        properties["Deadline"] = {"date": {"start": deadline}}

    if existing:
        fastn.notion.update_page(page_id=existing["id"], properties=properties)
        return "updated", existing["id"]
    else:
        new_page = fastn.notion.create_page(database_id=NOTION_DATABASE_ID, properties=properties)
        return "created", new_page.get("id")