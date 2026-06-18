# IT & Curriculum Desk Assistant
 
An automated, full-stack AI-enabled triage dashboard built to streamline K-12 IT helpdesk operations and curriculum software provisioning. The application utilizes a multi-stage, two-component AI inference pipeline to ingest raw teacher support requests or cryptic error screenshots, match them against a local persistent knowledge base, and generate technical resolution runbooks alongside polished, jargon-free correspondence drafts.
 
## 🚀 System Architecture & Data Flow
 
The application is structured as a single-tier data pipeline where visual extraction directly feeds contextual text generation, minimizing network overhead and optimizing token efficiency.
 
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
│  • Hardware-enforced JSON Mode  │                              │
└────────────────┬────────────────┘                              │
                 │                                               │
                 └───────────────────────┬───────────────────────┘
                                         │
                                         ▼ (Structured Platform Target JSON)
                        ┌─────────────────────────────────┐
                        │   Relational Wildcard Search    │◄─── [ local helpdesk.db ]
                        │  • SQL LIKE %platform% Query    │     Persistent SQLite Store
                        └────────────────┬────────────────┘
                                         │
                                         ▼ (Aggregated Context Vector Payload)
                        ┌─────────────────────────────────┐
                        │    Component 2: Llama 3.3 70B   │
                        │  • Contextual Runbook Alignment │
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
 
1. **Intake Terminal:** The operator drops a technical error image into the interface.
2. **Graphics Sanitization:** The Pillow engine intercepts the data stream, flattens any transparency channels (converting RGBA to RGB) to prevent encoding crashes, and programmatically downscales the image bounds to a maximum of 1080p to defend against prompt token bloat.
3. **Component 1 (Vision Tier):** The sanitized image is converted to a Base64 ASCII string and passed to `meta-llama/llama-4-scout-17b-16e-instruct` on Groq. Enforced by hardware-level JSON grammar validation, it outputs a clean schema identifying the target application platform.
4. **Relational Context Match (RAG Layer):** The application reads the platform key and fires a parameterized SQL wildcard query (`LIKE ?`) against a local persistent `helpdesk.db` file to extract specific support documentation rows.
5. **Component 2 (Reasoning Tier):** The extracted platform data and matched database rows are bundled into a dynamic system prompt and processed by `llama-3.3-70b-versatile`. It builds two distinct text blocks: an advanced step-by-step runbook for the admin interface, and an empathetic email reply template for the teacher.
## 🛠️ Tech Stack & Dependencies
 
- **Runtime Environment:** Python 3.11+
- **User Interface:** Streamlit (Reactive single-page application engine)
- **AI Infrastructure Layer:** Groq Cloud LPU (Lightning Processing Unit) Hardware Architecture
- **Relational Storage:** SQLite Engine (Local persistent storage subsystem)
- **Graphics Handling:** Pillow (PIL Fork) for data stream encoding and downscaling
## 📦 Local Installation & Setup Instructions
 
Follow these step-by-step instructions to clone, configure, and launch the platform on your local machine.
 
### 1. Initialize Your Project Workspace
 
Open your terminal application and map out a directory structure:
 
```bash
mkdir it-desk-assistant
cd it-desk-assistant
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
 
Install the verified libraries required to run the pipeline:
 
```bash
pip install streamlit groq pillow python-dotenv
```
 
### 4. Inject Environment Credentials
 
Create a hidden environment file named exactly `.env` in the root folder of your project to securely store your API keys:
 
```bash
touch .env
```
 
Open the `.env` file in a text editor and provide your Groq credentials:
 
```
GROQ_API_KEY=gsk_your_secret_api_key_here
```
 
### 5. Secure Your Git Tracking Configuration
 
Create a `.gitignore` file to ensure database logs, local secrets, and compiled Python bytecaches are never leaked or committed to public source control repositories:
 
```bash
touch .gitignore
```
 
Add the following layout configurations into your `.gitignore`:
 
```
# Local Environment Secrets
.env
.env.local
 
# Local Persistent Database File
helpdesk.db
 
# Python Runtimes & Cache Blocks
__pycache__/
*.pyc
*.pyo
*.pyd
.venv/
venv/
.streamlit/
```
 
### 6. Launch the Server Dashboard
 
Initialize your local web engine instance:
 
```bash
streamlit run app.py
```
 
The console will boot up a local background proxy and automatically mount the web panel dashboard interface inside a fresh browser tab at `http://localhost:8501`.
 
## 📋 Operational Manual & Features Guide
 
### 📂 Managing the Knowledge Base
 
Navigate to the sidebar dashboard area on the left panel to manipulate the active database layers:
 
- **📝 Paste Tab:** Enter a manual application target and copy-paste internal district remediation workflows directly into the interactive form fields.
- **📂 Upload Tab:** Drag and drop flat text files (`.txt`) containing general IT support notes. Llama 3.3 70B will intercept the upload stream, compile and restructure the unorganized text data into rows, and write it straight to your persistent database file.
- **📊 View DB Tab:** View expandable cards showing your active database tables to audit what information the AI currently has access to.
### 📸 Triage Processing
 
- Drop a curriculum error graphic or screenshot (e.g., Clever sync timeouts, LMS access failures, or database exceptions) into the Intake Panel.
- If an image is blurry or has unreadable text, check the **Toggle Manual Text Fallback** box to copy-paste the error log as text strings, bypassing the vision engine.
- Review your split-screen terminal workspace outputs:
  - **🛠️ IT Tech Runbook:** Procedural walkthroughs to resolve accounts and rosters in administrative consoles.
  - **📧 Teacher Email Draft:** Comforting, non-technical correspondence templates, ready to copy-paste back to your users.
  - **📦 Combined System Metrics:** A raw view of the full data object for tracking and auditing purposes.
 

