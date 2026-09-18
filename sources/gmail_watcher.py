python
from fastn import FastnClient

fastn = FastnClient()  # reads FASTN_API_KEY / FASTN_PROJECT_ID from env

def fetch_recent_emails():
    """
    ⚠️ VERIFY: method name and parameters below are illustrative — confirm the
    real tool name/shape with: fastn connector ls gmail
    """
    messages = fastn.gmail.list_messages(query="newer_than:1d")
    results = []
    for m in messages.get("messages", []):
        full = fastn.gmail.get_message(message_id=m["id"])
        results.append({
            "id": m["id"],
            "subject": full.get("subject", ""),
            "body": full.get("body_text", full.get("snippet", "")),
            "from": full.get("from", ""),
        })
    return results