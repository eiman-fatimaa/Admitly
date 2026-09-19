"""
ai_engine.py - Admitly AI Extraction & Evidence Matching Engine
Powered by Gemini API + BeautifulSoup.
"""

import os
import re
import json
import logging
import requests
from bs4 import BeautifulSoup
from google import genai
from google.genai import types

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ai_engine")

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.8-flash")
GEMINI_CLIENT = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None


def extract_requirements_from_url(url):
    """
    Step 1 of the customer journey:
    Fetches the public requirements page, strips markup, and prompts Gemini
    to generate a structured JSON checklist of items and descriptions.
    """
    logger.info(f"Fetching requirements page: {url}")
    try:
        resp = requests.get(url, timeout=10, headers={"User-Agent": "Admitly-RequirementsBot/1.0"})
        soup = BeautifulSoup(resp.text, "html.parser")

        # Strip scripts, styles, and navigational elements
        for element in soup(["script", "style", "nav", "footer", "header", "noscript"]):
            element.decompose()

        page_text = soup.get_text(separator="\n", strip=True)
        # Bounded slice for LLM prompt context
        content_snippet = page_text[:8000]
    except Exception as e:
        logger.warning(f"Could not scrape live URL ({e}). Using sample text.")
        content_snippet = f"Requirements for Fellowship at {url}. Applicants must submit an Official Transcript, a Faculty Letter of Recommendation, and a Research Proposal by Oct 15, 2026."

    if not GEMINI_CLIENT:
        logger.info("No GEMINI_API_KEY set. Using deterministic fallback extraction.")
        return {
            "program_name": "Mitacs Global Research Fellowship",
            "deadline": "2026-10-15",
            "requirements": [
                {"item": "Official Transcript", "description": "Certified university academic transcript"},
                {"item": "Letter of Recommendation", "description": "Confidential letter from a supervising faculty member"},
                {"item": "Research Proposal", "description": "3-page project overview outlining research objectives"}
            ]
        }

    # Call Gemini with JSON-only output.
    prompt = f"""
You are an admissions requirement parser. Read this scholarship/grant webpage text and extract:
1. Program name
2. Deadline (YYYY-MM-DD or empty string)
3. List of required applicant documents/items, each with a clear concise item name and 1-sentence description.

Return ONLY valid JSON matching this schema:
{{
  "program_name": "string",
  "deadline": "YYYY-MM-DD",
  "requirements": [
    {{"item": "string", "description": "string", "deadline": "YYYY-MM-DD or null"}}
  ]
}}

Webpage Content:
{content_snippet}
"""
    try:
        response = GEMINI_CLIENT.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                max_output_tokens=1024,
            ),
        )
        raw_text = response.text.strip()
        return json.loads(raw_text)
    except Exception as err:
        logger.error(f"Gemini extraction failed ({err}). Falling back to structured default.")
        return {
            "program_name": "Global Research Award",
            "deadline": "2026-10-15",
            "requirements": [
                {"item": "Official Transcript", "description": "Certified university academic transcript"},
                {"item": "Letter of Recommendation", "description": "Confidential letter from a supervising faculty member"},
                {"item": "Research Proposal", "description": "3-page project overview"}
            ]
        }


def match_evidence_to_requirement(evidence_text, filename, requirements_list):
    """
    Step 2 of customer journey:
    Matches uploaded document or forwarded email snippet to exactly one checklist item.
    """
    items = [r["item"] for r in requirements_list]

    def no_match():
        return {
            "matched_item": None,
            "status": "Unclear",
            "confidence": 0.0,
            "snippet": f"Uploaded file: {filename}",
        }

    def keyword_match():
        """Match only when the file name or note contains document-specific evidence."""
        submission = f"{filename} {evidence_text}".lower()
        aliases = {
            "transcript": {"transcript", "marksheet", "grade report", "academic record"},
            "recommendation": {"recommendation", "reference", "referee", "recommend", "endorsement"},
            "proposal": {"proposal", "research plan", "project plan", "research outline"},
            "cv": {"cv", "resume", "curriculum vitae"},
            "passport": {"passport"},
            "identity": {"identity", "id card", "national id"},
        }
        scores = []
        for requirement in requirements_list:
            requirement_text = f"{requirement.get('item', '')} {requirement.get('description', '')}".lower()
            score = 0
            for category, terms in aliases.items():
                if category in requirement_text:
                    score += sum(1 for term in terms if term in submission)
            # Also match distinctive terms explicitly shared by the item and submission.
            item_terms = set(re.findall(r"[a-z]{4,}", requirement.get("item", "").lower()))
            ignored = {"official", "letter", "document", "application", "required"}
            score += len((item_terms - ignored) & set(re.findall(r"[a-z]{4,}", submission)))
            scores.append((score, requirement["item"]))

        best_score = max((score for score, _ in scores), default=0)
        best_items = [item for score, item in scores if score == best_score]
        if best_score == 0 or len(best_items) != 1:
            return no_match()
        return {
            "matched_item": best_items[0],
            "status": "Received",
            "confidence": min(0.95, 0.7 + (best_score * 0.1)),
            "snippet": f"Matched from document name or note: {filename}",
        }

    if not GEMINI_CLIENT:
        return keyword_match()

    prompt = f"""
Match this applicant submission (filename: '{filename}', text excerpt: '{evidence_text}') to exactly one requirement from this list:
{json.dumps(items)}

Only choose a requirement when the filename or excerpt gives direct, document-specific evidence. If the submission is generic, ambiguous, or does not identify a listed requirement, return null and status "Unclear". Never guess based on checklist order.

Return ONLY JSON:
{{
  "matched_item": "exact item string from list or null",
  "status": "Received | Unclear",
  "confidence": 0.0 to 1.0,
  "reason": "short explanation"
}}
"""
    try:
        response = GEMINI_CLIENT.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                max_output_tokens=256,
            ),
        )
        raw_text = response.text.strip()
        result = json.loads(raw_text)
        if result.get("matched_item") not in items or result.get("status") != "Received":
            return no_match()
        result["snippet"] = filename or evidence_text[:60]
        return result
    except Exception as err:
        logger.error(f"Gemini evidence matching failed ({err}).")
        return keyword_match()


def match_drive_files_to_requirements(drive_files, checklist_items):
    """Return only high-confidence, one-to-one Drive filename matches."""
    unmatched_requirements = [item for item in checklist_items if item.get("status") != "Received"]
    matches = []
    used_requirements = set()

    for drive_file in drive_files:
        result = match_evidence_to_requirement(
            evidence_text=drive_file.get("description", ""),
            filename=drive_file.get("name", ""),
            requirements_list=unmatched_requirements,
        )
        requirement = result.get("matched_item")
        if (
            requirement
            and requirement not in used_requirements
            and result.get("status") == "Received"
            and result.get("confidence", 0) >= 0.7
        ):
            matches.append({
                "requirement": requirement,
                "file_name": drive_file.get("name", "Google Drive file"),
                "file_url": drive_file.get("webViewLink") or drive_file.get("link") or "",
            })
            used_requirements.add(requirement)
    return matches
