"""
models.py - Admitly SQLite Database Schema & Data Access Layer
Single source of truth for programs, requirements, applicants, and checklist statuses.
"""

import sqlite3
import os
import uuid
from datetime import datetime, timedelta

DB_FILE = os.environ.get("ADMITLY_DB", "admitly.db")


def get_db(db_path=DB_FILE):
    """
    Returns an SQLite connection with Row factory enabled and foreign keys enforced.
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db(db_path=DB_FILE):
    """
    Initializes the SQLite tables for Admitly.
    """
    conn = get_db(db_path)
    cursor = conn.cursor()

    cursor.executescript("""
    CREATE TABLE IF NOT EXISTS programs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        source_url TEXT,
        deadline TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS requirements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        program_id INTEGER NOT NULL,
        item TEXT NOT NULL,
        description TEXT,
        deadline TEXT,
        FOREIGN KEY (program_id) REFERENCES programs(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS applicants (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        program_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        invite_token TEXT NOT NULL UNIQUE,
        channel TEXT DEFAULT 'gmail',
        destination TEXT DEFAULT '',
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        FOREIGN KEY (program_id) REFERENCES programs(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS applicant_requirements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        applicant_id INTEGER NOT NULL,
        requirement_id INTEGER NOT NULL,
        status TEXT NOT NULL DEFAULT 'Missing', -- 'Missing', 'Pending', 'Received'
        last_evidence_snippet TEXT,
        updated_at TEXT NOT NULL DEFAULT (datetime('now')),
        FOREIGN KEY (applicant_id) REFERENCES applicants(id) ON DELETE CASCADE,
        FOREIGN KEY (requirement_id) REFERENCES requirements(id) ON DELETE CASCADE,
        UNIQUE (applicant_id, requirement_id)
    );
    """)

    conn.commit()
    conn.close()


def add_program(name, source_url, deadline, requirements_list, db_path=DB_FILE):
    """
    Creates a program and inserts its template checklist requirements.
    requirements_list: list of dicts [{'item': '...', 'description': '...', 'deadline': '...'}]
    """
    conn = get_db(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO programs (name, source_url, deadline)
        VALUES (?, ?, ?)
    """, (name, source_url, deadline))
    program_id = cursor.lastrowid

    for req in requirements_list:
        cursor.execute("""
            INSERT INTO requirements (program_id, item, description, deadline)
            VALUES (?, ?, ?, ?)
        """, (program_id, req.get("item"), req.get("description", ""), req.get("deadline") or deadline))

    conn.commit()
    conn.close()
    return program_id


def delete_program(program_id, db_path=DB_FILE):
    """Delete a program and all related applicants and requirement statuses."""
    conn = get_db(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM programs WHERE id = ?", (program_id,))
    program = cursor.fetchone()
    if not program:
        conn.close()
        return None

    cursor.execute("DELETE FROM programs WHERE id = ?", (program_id,))
    conn.commit()
    conn.close()
    return program["name"]


def add_applicant(program_id, name, email, channel="gmail", destination="", db_path=DB_FILE):
    """
    Registers an applicant for a program and generates initial 'Missing' status rows
    for all of that program's requirements.
    """
    conn = get_db(db_path)
    cursor = conn.cursor()

    invite_token = f"tok_{uuid.uuid4().hex[:10]}"

    cursor.execute("""
        INSERT INTO applicants (program_id, name, email, invite_token, channel, destination)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (program_id, name, email, invite_token, channel, destination))
    applicant_id = cursor.lastrowid

    cursor.execute("SELECT id FROM requirements WHERE program_id = ?", (program_id,))
    req_rows = cursor.fetchall()

    for r in req_rows:
        cursor.execute("""
            INSERT INTO applicant_requirements (applicant_id, requirement_id, status)
            VALUES (?, ?, 'Missing')
        """, (applicant_id, r["id"]))

    conn.commit()
    conn.close()
    return {"applicant_id": applicant_id, "invite_token": invite_token}


def update_applicant_status_by_item(email, requirement_item_name, status, evidence_snippet="", db_path=DB_FILE):
    """
    Used by AI Evidence Matcher to flip status when an applicant submits evidence.
    """
    conn = get_db(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT ar.id, a.id as applicant_id, r.id as requirement_id
        FROM applicants a
        JOIN requirements r ON r.program_id = a.program_id
        JOIN applicant_requirements ar ON ar.applicant_id = a.id AND ar.requirement_id = r.id
        WHERE LOWER(a.email) = LOWER(?) AND LOWER(r.item) = LOWER(?)
    """, (email, requirement_item_name))

    match = cursor.fetchone()
    if not match:
        conn.close()
        return False

    cursor.execute("""
        UPDATE applicant_requirements
        SET status = ?, last_evidence_snippet = ?, updated_at = datetime('now')
        WHERE id = ?
    """, (status, evidence_snippet, match["id"]))

    conn.commit()
    conn.close()
    return True


def get_program_board(program_id, db_path=DB_FILE):
    """
    Returns data needed for the Admin Program Detail Matrix (Screen 2):
    - program metadata
    - requirements column headers
    - applicants with their requirement statuses
    """
    conn = get_db(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM programs WHERE id = ?", (program_id,))
    program = dict(cursor.fetchone() or {})

    cursor.execute("SELECT * FROM requirements WHERE program_id = ? ORDER BY id ASC", (program_id,))
    requirements = [dict(r) for r in cursor.fetchall()]

    cursor.execute("SELECT * FROM applicants WHERE program_id = ? ORDER BY id ASC", (program_id,))
    applicants = [dict(a) for a in cursor.fetchall()]

    matrix = []
    for app in applicants:
        cursor.execute("""
            SELECT ar.requirement_id, ar.status, ar.last_evidence_snippet, ar.updated_at
            FROM applicant_requirements ar
            WHERE ar.applicant_id = ?
        """, (app["id"],))
        req_map = {row["requirement_id"]: dict(row) for row in cursor.fetchall()}

        statuses = []
        for req in requirements:
            statuses.append(req_map.get(req["id"], {"status": "Missing", "last_evidence_snippet": ""}))

        matrix.append({
            "applicant": app,
            "statuses": statuses
        })

    conn.close()
    return {
        "program": program,
        "requirements": requirements,
        "matrix": matrix
    }


def get_applicant_portal_data(invite_token, db_path=DB_FILE):
    """
    Returns data needed for Applicant Status Page (Screens 4 & 5).
    """
    conn = get_db(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT a.*, p.name as program_name, p.deadline as program_deadline
        FROM applicants a
        JOIN programs p ON p.id = a.program_id
        WHERE a.invite_token = ?
    """, (invite_token,))
    applicant = cursor.fetchone()
    if not applicant:
        conn.close()
        return None

    app_dict = dict(applicant)

    cursor.execute("""
        SELECT r.id, r.item, r.description, r.deadline, ar.status, ar.last_evidence_snippet, ar.updated_at
        FROM requirements r
        JOIN applicant_requirements ar ON ar.requirement_id = r.id
        WHERE ar.applicant_id = ?
        ORDER BY r.id ASC
    """, (app_dict["id"],))
    checklist = [dict(row) for row in cursor.fetchall()]

    conn.close()
    return {
        "applicant": app_dict,
        "checklist": checklist
    }


def get_urgent_gaps(program_id=None, db_path=DB_FILE):
    """
    Finds applicants who have one or more 'Missing' items for programs.
    Returns payloads formatted ready for Fastn Workflow 1 (nudge delivery).
    """
    conn = get_db(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT a.id as applicant_id, a.name as applicant_name, a.email,
               p.name as program_name, p.deadline as program_deadline,
               GROUP_CONCAT(r.item, '||') as missing_items_str
        FROM applicants a
        JOIN programs p ON p.id = a.program_id
        JOIN applicant_requirements ar ON ar.applicant_id = a.id
        JOIN requirements r ON r.id = ar.requirement_id
        WHERE ar.status = 'Missing'
        AND (? IS NULL OR p.id = ?)
        GROUP BY a.id, p.id
    """, (program_id, program_id))

    results = []
    for row in cursor.fetchall():
        missing_list = row["missing_items_str"].split("||") if row["missing_items_str"] else []
        results.append({
            "applicant_id": str(row["applicant_id"]),
            "applicant_name": row["applicant_name"],
            "email": row["email"],
            "program_name": row["program_name"],
            "missing_items": missing_list,
            "deadline": row["program_deadline"],
        })

    conn.close()
    return results


def get_bi_summary(db_path=DB_FILE):
    """
    Aggregates per-program completion metrics for Fastn Workflow 2 (Google Sheets BI Export).
    """
    conn = get_db(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT p.id as program_id, p.name as program_name,
               COUNT(DISTINCT a.id) as total_applicants
        FROM programs p
        LEFT JOIN applicants a ON a.program_id = p.id
        GROUP BY p.id
    """)
    programs = [dict(row) for row in cursor.fetchall()]

    summary_list = []
    for p in programs:
        pid = p["program_id"]
        total = p["total_applicants"] or 0

        if total == 0:
            summary_list.append({
                "program_name": p["program_name"],
                "total_applicants": 0,
                "complete_count": 0,
                "missing_count": 0,
                "at_risk_count": 0
            })
            continue

        cursor.execute("""
            SELECT COUNT(*) as complete_count
            FROM applicants a
            WHERE a.program_id = ?
            AND NOT EXISTS (
                SELECT 1 FROM applicant_requirements ar
                WHERE ar.applicant_id = a.id AND ar.status != 'Received'
            )
        """, (pid,))
        complete_count = cursor.fetchone()["complete_count"]

        missing_count = total - complete_count
        at_risk_count = missing_count

        summary_list.append({
            "program_name": p["program_name"],
            "total_applicants": total,
            "complete_count": complete_count,
            "missing_count": missing_count,
            "at_risk_count": at_risk_count
        })

    conn.close()
    return summary_list


def seed_demo_data(db_path=DB_FILE):
    """
    Seeds one realistic Program (Mitacs Global Fellowship) with 3 requirements and 3 applicants.
    """
    init_db(db_path)

    program_id = add_program(
        name="Mitacs Global Fellowship",
        source_url="https://www.mitacs.ca/our-programs/globalink-research-award/",
        deadline="2026-10-15",
        requirements_list=[
            {"item": "Official Transcript", "description": "Undergraduate degree certified academic transcript"},
            {"item": "Letter of Recommendation", "description": "Confidential reference letter from a faculty member"},
            {"item": "Research Proposal", "description": "3-page narrative outlining the fellowship project proposal"}
        ],
        db_path=db_path
    )

    app1 = add_applicant(
        program_id=program_id,
        name="Jane Doe",
        email="jane.doe@example.edu",
        channel="gmail",
        destination="jane.doe@example.edu",
        db_path=db_path
    )
    update_applicant_status_by_item("jane.doe@example.edu", "Research Proposal", "Received", "proposal_final_v2.pdf", db_path=db_path)

    app2 = add_applicant(
        program_id=program_id,
        name="John Smith",
        email="john.smith@example.edu",
        channel="slack",
        destination="#general",
        db_path=db_path
    )
    update_applicant_status_by_item("john.smith@example.edu", "Official Transcript", "Received", "transcript_official.pdf", db_path=db_path)
    update_applicant_status_by_item("john.smith@example.edu", "Letter of Recommendation", "Received", "rec_prof_wilson.pdf", db_path=db_path)
    update_applicant_status_by_item("john.smith@example.edu", "Research Proposal", "Received", "john_smith_proposal.pdf", db_path=db_path)

    add_applicant(
        program_id=program_id,
        name="Alice Walker",
        email="alice.walker@example.edu",
        channel="gmail",
        destination="alice.walker@example.edu",
        db_path=db_path
    )

    return {
        "program_id": program_id,
        "applicant_tokens": {
            "jane_doe": app1["invite_token"],
            "john_smith": app2["invite_token"]
        }
    }
