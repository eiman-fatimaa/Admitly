python
import json
import anthropic

claude = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from env

EXTRACTION_PROMPT = """You are reviewing content related to a graduate school application
(an email or a document). Extract the following as a single JSON object, nothing else:

{{
  "school": "string, the school name, or null if not identifiable",
  "document_type": "one of: transcript, recommendation_letter, test_scores, sop, confirmation, other",
  "status": "one of: received, submitted, requested, pending",
  "deadline_mentioned": "an ISO date (YYYY-MM-DD) if a deadline is explicitly mentioned, else null",
  "notes": "one short sentence summarizing what happened, for a human reviewing the board"
}}

If this content is unrelated to a grad school application, return exactly: {{"school": null}}

Content to analyze:
---
{content}
---
"""

def extract_application_event(content: str) -> dict:
    response = claude.messages.create(
        model="claude-sonnet-4-5",  # check docs.claude.com for the current recommended model string before you build
        max_tokens=500,
        messages=[{"role": "user", "content": EXTRACTION_PROMPT.format(content=content)}],
    )
    raw = response.content[0].text.strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # AI didn't return clean JSON — log it and skip this item rather than crash
        print(f"[extractor] Could not parse response: {raw}")
        return {"school": None}