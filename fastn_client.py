"""
fastn_client.py - Outbound HTTP Client for Fastn Workflows
Handles calling Workflow 1 (Applicant Nudge) and Workflow 2 (BI Export).
"""

import requests
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("fastn_client")

# Live webhook URLs generated on the Fastn platform for this workspace
FASTN_NUDGE_WEBHOOK = "https://webhooks.fastn.dev/prod/triggers/personal_537f9cad7efa339e78b6/webhooks/953464ae-66c7-4105-9e07-8bde695de631"
FASTN_BI_WEBHOOK = "https://webhooks.fastn.dev/prod/triggers/personal_537f9cad7efa339e78b6/webhooks/c37b085a-6e73-436b-9989-4fc0589cfe22"


def dispatch_applicant_nudge(applicant_id, applicant_name, program_name, missing_items, deadline, channel="sms", destination=None):
    """
    Calls Fastn Workflow 1 (applyiq-applicant-nudge-delivery).
    Fastn routes the message to Twilio (SMS) or Slack based on the applicant's channel.
    """
    if destination is None:
        destination = {"phone_number": "+15559876543"}

    payload = {
        "applicant_id": str(applicant_id),
        "applicant_name": applicant_name,
        "program_name": program_name,
        "missing_items": missing_items,
        "deadline": deadline,
        "channel": channel.lower(),
        "destination": destination
    }

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
        return {"success": True, "status_code": response.status_code, "data": response.json() if response.text else {}}
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to dispatch Fastn nudge: {e}")
        return {"success": False, "error": str(e)}


def export_bi_summary(spreadsheet_id, institution_id="inst_nust_01", programs_summary=None, sheet_range="Summary!A1"):
    """
    Calls Fastn Workflow 2 (applyiq-institution-bi-export).
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
        return {"success": True, "status_code": response.status_code, "data": response.json() if response.text else {}}
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to dispatch Fastn BI export: {e}")
        return {"success": False, "error": str(e)}
