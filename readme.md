# IT & Curriculum Desk Assistant

An automated, full-stack AI-enabled triage dashboard built to streamline K-12 IT helpdesk operations and curriculum software provisioning. The application uses a two-component AI inference pipeline to ingest cryptic error screenshots (or pasted error text), match them against a local persistent knowledge base, and generate a technical resolution runbook alongside a polished, jargon-free email draft for the teacher.

## 🚀 System Architecture & Data Flow

The application is a single-tier data pipeline where visual extraction feeds contextual text generation. The reasoning step leads with the error actually shown in the screenshot, and treats the knowledge base as supporting reference rather than a rigid override.

```
                  ┌──────────────────────────────┐
                  │   UI Intake Terminal (Web)   │
                  └──────────────┬───────────────┘
                                 │
         ┌───────────────────────┴───────────────────────┐
         ▼ (Screenshot Upload)                           ▼ (Manual Text Fallback)
┌─────────────────────────────────┐             ┌─────────────────────────────────┐
│     Pillow Graphics Engine      │             │      Direct String Bypass       │
│  • Programmatic RGBA -> RGB     │             └────────────────┬────────────────┘
│  • Aspect-aware 1080p scaling   │                              │
└────────────────┬────────────────┘                              │
                 │                                               │
                 ▼ (Base64 ASCII String)                         │
┌─────────────────────────────────┐                              │
│   Component 1: Llama 4 Scout    │                              │
│  • Multimodal Vision Extraction │                              │
│  • JSON-mode output             │                              │
└────────────────┬────────────────┘                              │
                 │                                               │
                 └───────────────────────┬───────────────────────┘
                                         │
                                         ▼ (Structured Platform Target JSON)
                        ┌─────────────────────────────────┐
                        │      Knowledge Base Lookup      │◄─── [ local helpdesk.db ]
                        │  • Two-way platform name match  │     Persistent SQLite Store
                        └────────────────┬────────────────┘
                                         │
                                         ▼ (Matched reference runbooks)
                        ┌─────────────────────────────────┐
                        │    Component 2: Llama 3.3 70B   │
                        │  • Image-led diagnosis          │
                        │  • Tone-split Text Generation   │
                        └────────────────┬────────────────┘
                                         │
                                         ▼ (Final Output payload)
                        ┌─────────────────────────────────┐
                        │    Tabbed UI Workspace Panel    │
                        │  • 🛠️ Internal Tech Runbook     │
                        │  • 📧 Parent/Teacher Response   │
                        └─────────────────────────────────┘
```

1. **Intake Terminal:** The operator drops a technical error image into the interface (or pastes the error text via the fallback).
2. **Graphics Sanitization:** The Pillow engine flattens any transparency channels (RGBA -> RGB) to prevent encoding crashes, and downscales the image to a maximum of 1920x1080 to keep prompt token usage in check.
3. **Component 1 (Vision Tier):** The sanitized image is converted to a Base64 string and passed to `meta-llama/llama-4-scout-17b-16e-instruct` on Groq in JSON-output mode. It returns a clean schema with the target `platform_name` and a `log_summary` describing exactly what error is visible on screen.
4. **Knowledge Base Match (RAG Layer):** The extracted platform name is looked up in the local persistent `helpdesk.db` file using a case-insensitive, two-way name match (the stored platform contains the query, or the query contains the stored platform — so "Clever Portal Login" still matches "Clever"). A blank or unknown platform deliberately matches **no** rows, so the model is never accidentally fed the entire table.
5. **Component 2 (Reasoning Tier):** The extracted error summary leads; any matched runbooks are attached as **supporting reference material**. `llama-3.3-70b-versatile` is instructed to diagnose the specific problem shown in the screenshot and use the reference docs only where they genuinely apply — it will not force-fit an unrelated runbook. It returns two text blocks: a step-by-step admin runbook and an empathetic teacher email. If no reference docs apply, it synthesizes from common curriculum-support patterns (SSO loops, cache/cookie conflicts, rostering/sync delays, seat-cap limits).

The deterministic pieces of step 4 and 5 (lookup, context framing, prompt construction, the model-call wrapper, and cache-key derivation) live in `core.py` so they can be unit tested independently of the UI — see [Running the Tests](#-running-the-tests).

## 🛠️ Tech Stack & Dependencies

- **Runtime Environment:** Python 3.11+
- **User Interface:** Streamlit (reactive single-page application engine)
- **AI Infrastructure Layer:** Groq Cloud LPU (Lightning Processing Unit) hardware
- **Models:** `meta-llama/llama-4-scout-17b-16e-instruct` (vision), `llama-3.3-70b-versatile` (reasoning + `.txt` ingestion)
- **Relational Storage:** SQLite (local persistent storage)
- **Graphics Handling:** Pillow (PIL fork) for image encoding and downscaling
- **Testing:** Pytest (unit tests for the core pipeline logic)

## 🗂️ Project Structure

```
.
├── app.py            # Streamlit UI + orchestration (entry point)
├── core.py           # Testable Stage-2 logic: lookup, prompt, model call, cache key
├── tests/
│   └── test_core.py  # Pytest unit tests for core.py (Groq client mocked)
├── conftest.py       # Lets pytest import `core` from the repo root
├── requirements.txt  # Python dependencies
├── helpdesk.db       # Local SQLite knowledge base (git-ignored, auto-created)
└── .env              # GROQ_API_KEY (git-ignored)
```

## 📦 Local Installation & Setup Instructions

Follow these step-by-step instructions to configure and launch the platform on your local machine.

### 1. Get the Project

Clone or download the repository, then move into it:

```bash
cd ai-it-debugger
```

### 2. Configure a Virtual Environment

Isolate your package dependencies to prevent global module conflicts:

```bash
# Create the virtual environment
python -m venv venv

# Activate the environment (Mac/Linux)
source venv/bin/activate

# Activate the environment (Windows PowerShell)
.\venv\Scripts\Activate.ps1
```

### 3. Install Package Dependencies

Install everything (app + test deps) from the pinned requirements file:

```bash
pip install -r requirements.txt
```

### 4. Inject Environment Credentials

Create a hidden environment file named exactly `.env` in the root folder to store your API key:

```bash
touch .env
```

Open the `.env` file and provide your Groq credentials:

```
GROQ_API_KEY=gsk_your_secret_api_key_here
```

> The `.env` file and the `helpdesk.db` database are already listed in `.gitignore`, so your secrets and local data are never committed.

### 5. Launch the Server Dashboard

Start the local Streamlit instance:

```bash
streamlit run app.py
```

The console boots a local server and opens the dashboard in a browser tab at `http://localhost:8501`. On first run the app auto-creates `helpdesk.db` and seeds a few default runbooks (Clever, Amplify, McGraw-Hill).

## 🧪 Running the Tests

The core pipeline logic is covered by unit tests that run without launching Streamlit or making real Groq calls (the Groq client is mocked, and an in-memory SQLite database is used):

```bash
python -m pytest
```

The 14 tests cover, among other things:

- Blank/whitespace platform names match **no** runbooks (never the whole table).
- Verbose vision output (e.g. `"Clever Portal Login"`) still matches the stored `"Clever"` row.
- The generation prompt leads with the screenshot's actual error and does **not** force-fit the database runbook.
- A new screenshot/text input produces a new cache signature, so results regenerate instead of going stale.

## 📋 Operational Manual & Features Guide

### 📂 Managing the Knowledge Base

Use the sidebar on the left to manage the active database:

- **📝 Paste Tab:** Enter a platform name and paste internal district remediation steps directly into the form.
- **📂 Upload Tab:** Drop flat text files (`.txt`) of IT support notes. `llama-3.3-70b-versatile` parses the unstructured text into a `{platform, fix}` row and writes it to the database.
- **📊 View DB Tab:** Expandable cards showing the current runbooks, so you can audit what the AI has access to.

### 📸 Triage Processing

- Drop a curriculum error screenshot (e.g., Clever sync timeouts, LMS access failures, gradebook errors) into the Intake Panel.
- If an image is blurry or unreadable, check the **Toggle Manual Text Fallback** box to paste the error text directly, bypassing the vision engine.
- Changing the uploaded screenshot or fallback text automatically regenerates the output — no manual reset required.
- Review the split-screen workspace outputs:
  - **🛠️ IT Tech Runbook:** Procedural steps to resolve accounts and rosters in administrative consoles.
  - **📧 Teacher Email Draft:** A non-technical, copy-ready correspondence template.
  - **📦 Combined System Metrics:** A raw view of the full data object (vision extraction + resolution report) for auditing.
