"""
fastn_client.py - Admitly outbound HTTP client for Fastn workflows
Handles calling Workflow 1 (Applicant Nudge) and Workflow 2 (BI Export).
"""

import requests
import json
import logging
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("fastn_client")

# Live webhook URLs generated on the Fastn platform for this workspace
FASTN_NUDGE_WEBHOOK = os.environ.get(
    "FASTN_NUDGE_WEBHOOK",
    "https://webhooks.fastn.dev/prod/triggers/personal_537f9cad7efa339e78b6/webhooks/953464ae-66c7-4105-9e07-8bde695de631",
)
FASTN_BI_WEBHOOK = os.environ.get(
    "FASTN_BI_WEBHOOK",
    "https://webhooks.fastn.dev/prod/triggers/personal_537f9cad7efa339e78b6/webhooks/c37b085a-6e73-436b-9989-4fc0589cfe22",
)


def _response_data(response):
    """Return a useful success payload even when Fastn responds without JSON."""
    if not response.text:
        return {}
    try:
        return response.json()
    except ValueError:
        return {"response_text": response.text[:500]}


def dispatch_applicant_nudge(
    applicant_id,
    applicant_name,
    program_name,
    missing_items,
    deadline,
    channel="gmail",
    destination=None,
    portal_url=None,
    notification_type="nudge",
):
    """
    Calls Fastn Workflow 1. Fastn routes the message through Gmail or Slack
    based on the applicant's selected channel.
    """
    if destination is None:
        destination = {"email_address": "applicant@example.edu"}

    payload = {
        "applicant_id": str(applicant_id),
        "applicant_name": applicant_name,
        "program_name": program_name,
        "missing_items": missing_items,
        "deadline": deadline,
        "channel": channel.lower(),
        "destination": destination
    }
    # These fields let the same Fastn workflow distinguish an invitation from a
    # reminder. Existing reminder mappings can continue using the fields above.
    if portal_url:
        payload["portal_url"] = portal_url
    if notification_type:
        payload["notification_type"] = notification_type

    try:
        logger.info(f"Dispatching nudge via Fastn to {applicant_name} ({channel})...")
        response = requests.post(
            FASTN_NUDGE_WEBHOOK,
            headers={"Content-Type": "application/json"},
            json=payload,
            timeout=10
        )
        response.raise_for_status()
        logger.info(f"Fastn nudge dispatched successfully. Status: {response.status_code}")
        return {"success": True, "status_code": response.status_code, "data": _response_data(response)}
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to dispatch Fastn nudge: {e}")
        return {"success": False, "error": str(e)}


def dispatch_applicant_welcome(applicant_id, applicant_name, applicant_email, program_name,
                               requirements, deadline, portal_url):
    """Queue the password-free applicant invitation through the Gmail workflow."""
    return dispatch_applicant_nudge(
        applicant_id=applicant_id,
        applicant_name=applicant_name,
        program_name=program_name,
        missing_items=requirements,
        deadline=deadline,
        channel="gmail",
        destination={"email_address": applicant_email},
        portal_url=portal_url,
        notification_type="welcome",
    )


def export_bi_summary(spreadsheet_id, institution_id="inst_nust_01", programs_summary=None, sheet_range="Summary!A1"):
    """
    Calls Fastn Workflow 2.
    Fastn appends the aggregate applicant progress metrics into the institution's Google Sheet.
    """
    if programs_summary is None:
        programs_summary = []

    payload = {
        "spreadsheetId": spreadsheet_id,
        "sheetRange": sheet_range,
        "institution_id": institution_id,
        "programs": programs_summary
    }

    try:
        logger.info(f"Exporting BI metrics to Google Sheet {spreadsheet_id} via Fastn...")
        response = requests.post(
            FASTN_BI_WEBHOOK,
            headers={"Content-Type": "application/json"},
            json=payload,
            timeout=15
        )
        response.raise_for_status()
        logger.info(f"Fastn BI export dispatched successfully. Status: {response.status_code}")
        return {"success": True, "status_code": response.status_code, "data": _response_data(response)}
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to dispatch Fastn BI export: {e}")
        return {"success": False, "error": str(e)}
