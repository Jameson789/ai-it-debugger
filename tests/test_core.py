"""Tests for the testable core logic extracted from app.py.

These cover the Stage-2 generation pipeline that was over-anchoring to the
database: retrieval matching, context framing, prompt construction, and the
model-call wrapper. The LLM itself is non-deterministic, so we test the
deterministic inputs we hand it (the prompt) and mock the Groq client.
"""

import json
import sqlite3
from unittest.mock import MagicMock

import core


def make_db(rows=None):
    """In-memory DB seeded with the given (platform, steps) rows."""
    conn = sqlite3.connect(":memory:")
    conn.execute(
        """CREATE TABLE runbooks (
               id INTEGER PRIMARY KEY AUTOINCREMENT,
               platform TEXT NOT NULL UNIQUE,
               resolution_steps TEXT NOT NULL
           )"""
    )
    for platform, steps in (rows or []):
        conn.execute(
            "INSERT INTO runbooks (platform, resolution_steps) VALUES (?, ?)",
            (platform, steps),
        )
    conn.commit()
    return conn


# --- init_db -----------------------------------------------------------------

def test_init_db_creates_table_and_seeds_defaults_once():
    conn = sqlite3.connect(":memory:")
    core.init_db(conn)
    first = conn.execute("SELECT COUNT(*) FROM runbooks").fetchone()[0]
    assert first > 0
    # Idempotent: running again does not duplicate the seed rows.
    core.init_db(conn)
    second = conn.execute("SELECT COUNT(*) FROM runbooks").fetchone()[0]
    assert first == second


# --- search_runbooks ---------------------------------------------------------

def test_search_finds_exact_platform():
    conn = make_db([("Clever", "do the sync thing")])
    matches = core.search_runbooks(conn, "Clever")
    assert len(matches) == 1
    assert matches[0]["platform"] == "Clever"
    assert matches[0]["resolution_steps"] == "do the sync thing"


def test_search_is_case_insensitive():
    conn = make_db([("Clever", "steps")])
    assert len(core.search_runbooks(conn, "clever")) == 1


def test_search_empty_name_matches_nothing():
    # BUG A: LIKE '%%' used to return every row when vision returned "".
    conn = make_db([("Clever", "a"), ("Amplify", "b"), ("McGraw-Hill", "c")])
    assert core.search_runbooks(conn, "") == []


def test_search_whitespace_name_matches_nothing():
    conn = make_db([("Clever", "a"), ("Amplify", "b")])
    assert core.search_runbooks(conn, "   ") == []


def test_search_none_name_matches_nothing():
    conn = make_db([("Clever", "a")])
    assert core.search_runbooks(conn, None) == []


def test_search_handles_verbose_vision_output():
    # BUG B: a verbose platform like "Clever Portal Login" used to match
    # nothing because the DB value "Clever" is not a substring of it.
    conn = make_db([("Clever", "steps")])
    matches = core.search_runbooks(conn, "Clever Portal Login")
    assert len(matches) == 1
    assert matches[0]["platform"] == "Clever"


def test_search_unknown_platform_matches_nothing():
    conn = make_db([("Clever", "a")])
    assert core.search_runbooks(conn, "Schoology") == []


# --- build_retrieved_context -------------------------------------------------

def test_context_includes_rows_as_reference_not_override():
    rows = [{"platform": "Clever", "resolution_steps": "run a delta sync"}]
    ctx = core.build_retrieved_context(rows)
    assert "Clever" in ctx
    assert "run a delta sync" in ctx
    # The forcing/override framing was the root cause of the symptom.
    assert "OVERRIDE" not in ctx.upper()


def test_context_empty_returns_no_records_notice():
    ctx = core.build_retrieved_context([])
    assert "No matching internal" in ctx


# --- build_generation_prompt -------------------------------------------------

def test_prompt_leads_with_visual_evidence_and_drops_forcing_language():
    prompt = core.build_generation_prompt(
        platform_name="Clever",
        log_summary="Student cannot reset their password; reset link 404s",
        context="Reference: Clever -> run a delta sync",
    )
    # The actual extracted error must be present and central.
    assert "Student cannot reset their password" in prompt
    assert "Clever" in prompt
    assert "run a delta sync" in prompt
    # The two phrases that forced DB-parroting must be gone.
    assert "MUST align" not in prompt
    assert "OVERRIDE" not in prompt.upper()
    # Output contract preserved for the UI tabs.
    assert "runbook_steps" in prompt
    assert "teacher_email" in prompt


# --- generate_resolution -----------------------------------------------------

def test_generate_resolution_returns_parsed_json_from_model():
    fake_payload = {"runbook_steps": "1. do x", "teacher_email": "Hi teacher"}
    client = MagicMock()
    client.chat.completions.create.return_value.choices = [
        MagicMock(message=MagicMock(content=json.dumps(fake_payload)))
    ]

    result = core.generate_resolution(
        client, platform_name="Clever", log_summary="error", context="ctx"
    )

    assert result == fake_payload
    # Calls the reasoning model in JSON mode.
    _, kwargs = client.chat.completions.create.call_args
    assert kwargs["model"] == "llama-3.3-70b-versatile"
    assert kwargs["response_format"] == {"type": "json_object"}


# --- input_signature (cache invalidation, BUG C) -----------------------------

def test_input_signature_is_stable_for_same_input():
    assert core.input_signature(b"abc", None) == core.input_signature(b"abc", None)


def test_input_signature_changes_with_different_input():
    assert core.input_signature(b"abc", None) != core.input_signature(b"xyz", None)
    assert core.input_signature(None, "hello") != core.input_signature(None, "world")
