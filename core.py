"""Testable core logic for the IT & Curriculum Desk Assistant.

This module holds the deterministic pieces of the Stage-2 generation pipeline
(database retrieval, context framing, prompt construction, the model-call
wrapper, and cache-key derivation) so they can be unit tested without spinning
up Streamlit or making real network calls. app.py imports from here.
"""

import hashlib
import json

REASONING_MODEL = "llama-3.3-70b-versatile"

# Seed records used when the database is first created.
DEFAULT_RUNBOOKS = [
    ("Clever", "The student account lacks an active enrollment sync link mapping. "
               "Resolution: Open Clever Admin Console -> Nav to Sync Settings -> "
               "Run a Manual Delta Sync on the targeted Student ID record."),
    ("Amplify", "Chronic browser session state cache conflict with federated "
                "Single Sign-On tokens. Resolution: Instruct the teacher to clear "
                "Chrome site cookies specifically for Amplify, or launch via a "
                "secure Incognito window."),
    ("McGraw-Hill", "School building roster seat caps are maxed out. Resolution: "
                    "Open District Curriculum Provisioning Suite, unassign inactive "
                    "student records from the prior semester, and assign the seat "
                    "allocation to the new user."),
]

NO_RECORDS_NOTICE = (
    "No matching internal district runbook records were found for this platform."
)


def init_db(conn):
    """Create the runbooks table and seed defaults exactly once (idempotent)."""
    conn.execute(
        """CREATE TABLE IF NOT EXISTS runbooks (
               id INTEGER PRIMARY KEY AUTOINCREMENT,
               platform TEXT NOT NULL UNIQUE,
               resolution_steps TEXT NOT NULL
           )"""
    )
    conn.commit()
    count = conn.execute("SELECT COUNT(*) FROM runbooks").fetchone()[0]
    if count == 0:
        conn.executemany(
            "INSERT OR IGNORE INTO runbooks (platform, resolution_steps) VALUES (?, ?)",
            DEFAULT_RUNBOOKS,
        )
        conn.commit()


def search_runbooks(conn, platform_name):
    """Return runbook rows relevant to the extracted platform name.

    Matching is a two-way, case-insensitive substring test: a row matches when
    the stored platform name contains the query OR the query contains the stored
    name. This fixes two prior bugs:
      * an empty/blank name no longer matches every row (it now matches none);
      * a verbose vision result like "Clever Portal Login" still matches "Clever".
    The runbook table is small, so filtering in Python is fine and keeps the SQL
    free of user-controlled wildcards.
    """
    name = (platform_name or "").strip().lower()
    if not name:
        return []
    rows = conn.execute("SELECT platform, resolution_steps FROM runbooks").fetchall()
    matches = []
    for platform, steps in rows:
        p = platform.lower()
        if p in name or name in p:
            matches.append({"platform": platform, "resolution_steps": steps})
    return matches


def build_retrieved_context(rows):
    """Frame matched rows as supporting reference material (not an override)."""
    if not rows:
        return NO_RECORDS_NOTICE
    blocks = [
        f"Reference runbook for {row['platform']}:\n{row['resolution_steps']}"
        for row in rows
    ]
    return "\n\n".join(blocks)


def build_generation_prompt(platform_name, log_summary, context):
    """Build the Stage-2 prompt that leads with the image's actual error.

    The internal docs are presented as supporting reference, and the model is
    explicitly told not to force-fit an unrelated runbook -- this is the fix for
    output that always parroted the database regardless of the screenshot.
    """
    return f"""You are a Senior K-12 District Enterprise System Support Specialist.

Diagnose the SPECIFIC problem shown in the intake evidence below and write a
resolution for THAT problem. Lead with the visual evidence.

INTAKE EVIDENCE (the actual reported problem -- treat this as primary):
- Platform target: {platform_name}
- Visual evidence summary: {log_summary}

INTERNAL DISTRICT REFERENCE DOCS (supporting material only):
\"\"\"
{context}
\"\"\"

Use the internal reference docs ONLY where they genuinely address the specific
problem in the intake evidence. If a reference doc describes a different issue
than the one shown, do not force-fit it -- diagnose from the visual evidence and
cite the reference only when it is actually relevant. If no reference docs apply,
build a high-quality resolution from common curriculum-support patterns (SSO
loops, cache/cookie conflicts, rostering/sync delays, seat-cap limits).

Return a valid JSON object matching exactly this structure:
{{
    "runbook_steps": "Numbered technical resolution checklist for the IT admin interface.",
    "teacher_email": "Empathetic, non-technical email draft addressed to the teacher."
}}
"""


def generate_resolution(client, platform_name, log_summary, context, model=REASONING_MODEL):
    """Call the reasoning model in JSON mode and return the parsed payload."""
    prompt = build_generation_prompt(platform_name, log_summary, context)
    completion = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
    )
    return json.loads(completion.choices[0].message.content)


def input_signature(image_bytes, manual_text):
    """Stable fingerprint of the current intake input, for cache invalidation.

    The Stage-2 result is cached in session state; keying that cache on this
    signature means a new screenshot or new manual text regenerates the report
    instead of reusing the previous one.
    """
    h = hashlib.sha256()
    if image_bytes:
        h.update(b"img:")
        h.update(image_bytes)
    if manual_text:
        h.update(b"txt:")
        h.update(manual_text.encode("utf-8"))
    return h.hexdigest()
