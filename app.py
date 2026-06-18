import streamlit as st
import base64
import json
import os
import sqlite3
from io import BytesIO
from PIL import Image
from groq import Groq
from dotenv import load_dotenv

import core

# --- 0. ENVIRONMENT & SECURITY SETUP ---
load_dotenv()

# --- 1. PERSISTENT DATABASE ARCHITECTURE INITIALIZATION ---
# Changed from ":memory:" to a local file name "helpdesk.db".
# This will automatically create a real database file in your project directory.
DB_FILE = "helpdesk.db"

def get_db_connection():
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    return conn

# Run database setup once at application startup (create table + seed defaults)
conn = get_db_connection()
core.init_db(conn)
conn.close()

# --- 2. APPLICATION INITIALIZATION ---
st.set_page_config(page_title="IT Desk Assistant", layout="wide")
st.title("🤖 IT & Curriculum Desk Assistant")
st.caption("Persistent Build: Local File-Based SQLite Database + Multimodal Inference Pipeline")

groq_api_key = os.getenv("GROQ_API_KEY")
if not groq_api_key:
    st.error("Missing GROQ_API_KEY variable! Please verify your local .env file profile configuration settings.")
    st.stop()

client = Groq(api_key=groq_api_key)

# --- 3. SIDEBAR: KNOWLEDGE BASE CONTROLLER ---
st.sidebar.header("📋 Knowledge Base Store")
st.sidebar.caption("Ingest active district technical runbooks into your local persistent SQLite file.")

db_tab1, db_tab2, db_tab3 = st.sidebar.tabs(["📝 Paste", "📂 Upload", "📊 View DB"])

with db_tab1:
    with st.sidebar.form("paste_form", clear_on_submit=True):
        st.write("#### Manual Data Entry")
        p_platform = st.text_input("System Platform Name (e.g. Schoology)")
        p_fix = st.text_area("Administrative Fix Instructions")
        submit_paste = st.form_submit_button("Commit to DB Table")
        
        if submit_paste and p_platform and p_fix:
            try:
                db_conn = get_db_connection()
                cursor = db_conn.cursor()
                cursor.execute(
                    "INSERT OR REPLACE INTO runbooks (platform, resolution_steps) VALUES (?, ?)",
                    (p_platform.strip(), p_fix.strip())
                )
                db_conn.commit()
                db_conn.close()
                st.sidebar.success(f"Successfully recorded data for {p_platform}!")
                st.author = "System"
                st.rerun() 
            except Exception as ex:
                st.sidebar.error(f"Write failure: {ex}")

with db_tab2:
    st.write("#### File Ingestion Stream")
    uploaded_docs = st.file_uploader(
        "Upload standard district text configuration files (.txt only)", 
        type=["txt"], 
        accept_multiple_files=True,
        key="file_uploader_sidebar"
    )
    
    if uploaded_docs:
        has_new_uploads = False
        for doc in uploaded_docs:
            file_cache_key = f"processed_{doc.name}"
            if file_cache_key not in st.session_state:
                try:
                    raw_text = doc.read().decode("utf-8")
                    
                    parse_prompt = f"""
                    You are a data validation compiler. Parse the following document text into a single JSON object.
                    Identify the primary platform name or curriculum software app name, and the full remediation actions.
                    
                    DOCUMENT TEXT CONTENT:
                    {raw_text}
                    
                    Output layout must rigidly match this structural schema:
                    {{
                      "platform": "String extracted (e.g. Schoology, Seesaw)",
                      "fix": "Full remediation text instructions extracted from the document"
                    }}
                    """
                    
                    with st.sidebar.spinner(f"Compiling raw asset layout: {doc.name}..."):
                        parse_completion = client.chat.completions.create(
                            model="llama-3.3-70b-versatile",
                            messages=[{"role": "user", "content": parse_prompt}],
                            response_format={"type": "json_object"}
                        )
                        parsed_file_data = json.loads(parse_completion.choices[0].message.content)
                        
                        db_conn = get_db_connection()
                        cursor = db_conn.cursor()
                        cursor.execute(
                            "INSERT OR REPLACE INTO runbooks (platform, resolution_steps) VALUES (?, ?)",
                            (parsed_file_data.get("platform"), parsed_file_data.get("fix"))
                        )
                        db_conn.commit()
                        db_conn.close()
                        
                        st.session_state[file_cache_key] = True
                        has_new_uploads = True
                except Exception as ex:
                    st.sidebar.error(f"Failed parsing asset {doc.name}: {ex}")
        
        if has_new_uploads:
            st.rerun() 

with db_tab3:
    st.write("#### Active SQLite Records")
    db_conn = get_db_connection()
    cursor = db_conn.cursor()
    cursor.execute("SELECT platform, resolution_steps FROM runbooks")
    records = cursor.fetchall()
    db_conn.close()
    
    if records:
        for rec in records:
            with st.expander(f"⚙️ {rec[0]}"):
                st.markdown(f"**Remediation Steps:**\n{rec[1]}")
    else:
        st.caption("No diagnostic instructions logged inside database tables.")

# --- 4. MAIN INTERFACE SYSTEM LAYOUT ---
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("📸 Intake Panel")
    uploaded_screenshot = st.file_uploader("Upload technical support screenshot grab", type=["png", "jpg", "jpeg"])
    
    st.write("---")
    st.markdown("### ⌨️ Fallback Entry Terminal")
    fallback_active = st.checkbox("Toggle Manual Text Fallback (If image fails/blurry)")
    manual_text = st.text_area("Paste manual details or errors directly here:", disabled=not fallback_active)

# --- INPUT-CHANGE CACHE INVALIDATION ---
# Regenerate vision + resolution whenever the actual intake input changes,
# instead of reusing a stale result from a previous upload until the user
# manually clicks "Reset Operational Workspace".
screenshot_bytes = (
    uploaded_screenshot.getvalue()
    if uploaded_screenshot is not None and not fallback_active
    else None
)
active_text = manual_text if fallback_active else None
current_sig = core.input_signature(screenshot_bytes, active_text)
if st.session_state.get("last_input_sig") != current_sig:
    st.session_state.pop("cached_vision_metrics", None)
    st.session_state.pop("cached_resolution_reports", None)
    st.session_state["last_input_sig"] = current_sig

# --- 5. VISION EXTRACTION LAYER ---
parsed_metrics = None

if uploaded_screenshot is not None and not fallback_active:
    with col1:
        st.image(uploaded_screenshot, caption="Target Incident Workspace Canvas", use_container_width=True)
        
    if "cached_vision_metrics" not in st.session_state:
        with col1:
            with st.spinner("Component 1: Extracting text features via Llama 4 Scout..."):
                try:
                    img = Image.open(uploaded_screenshot)
                    img.thumbnail((1920, 1080))
                    
                    if img.mode in ("RGBA", "P"):
                        img = img.convert("RGB")
                        
                    buffered = BytesIO()
                    img.save(buffered, format="JPEG", quality=85)
                    base64_image = base64.b64encode(buffered.getvalue()).decode('utf-8')
                    
                    vision_prompt = (
                        "Analyze the attached software interface screenshot. Extrapolate context "
                        "and output into a valid JSON schema conforming exactly to these properties:\n"
                        "{\n"
                        '  "platform_name": "App or platform name text identifier (e.g. Clever, Amplify, D2L)",\n'
                        '  "log_summary": "Technical narrative summarizing exactly what error messages or layout issues are visible on the screen"\n'
                        "}"
                    )
                    
                    completion = client.chat.completions.create(
                        model="meta-llama/llama-4-scout-17b-16e-instruct",
                        messages=[{
                            "role": "user",
                            "content": [
                                {"type": "text", "text": vision_prompt},
                                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                            ]
                        }],
                        response_format={"type": "json_object"}
                    )
                    st.session_state.cached_vision_metrics = json.loads(completion.choices[0].message.content)
                except Exception as ex:
                    st.error(f"Vision Engine Failure: {ex}")
                    
    parsed_metrics = st.session_state.get("cached_vision_metrics")

elif fallback_active and manual_text:
    parsed_metrics = {
        "platform_name": "Manual Entry Source",
        "log_summary": manual_text
    }

# --- 6. DATABASE QUERY & LLM GENERATION TIER ---
if parsed_metrics:
    with col2:
        st.subheader("⚡ Resolution Processing Engine")
        st.info(f"**Extracted Target System:** {parsed_metrics.get('platform_name')}")
        
        if "cached_resolution_reports" not in st.session_state:
            with st.spinner("Component 2: Scanning local SQLite repositories & generating runbooks..."):
                try:
                    db_conn = get_db_connection()
                    matching_rows = core.search_runbooks(db_conn, parsed_metrics.get("platform_name"))
                    db_conn.close()

                    retrieved_context = core.build_retrieved_context(matching_rows)

                    st.session_state.cached_resolution_reports = core.generate_resolution(
                        client,
                        platform_name=parsed_metrics.get("platform_name"),
                        log_summary=parsed_metrics.get("log_summary"),
                        context=retrieved_context,
                    )
                except Exception as ex:
                    st.error(f"Resolution Generation Error encountered: {ex}")
                    
        reports = st.session_state.get("cached_resolution_reports")
        
        if reports:
            t1, t2, t3 = st.tabs(["🛠️ IT Tech Runbook", "📧 Teacher Email Draft", "📦 Combined System Metrics"])
            
            with t1:
                st.markdown("### Internal Helpdesk Administrative Checklist")
                st.markdown(reports.get("runbook_steps"))
            with t2:
                st.markdown("### Client Correspondence Communication Workspace")
                st.text_area(label="Email Body Frame", value=reports.get("teacher_email"), height=300)
            with t3:
                st.write("#### Full Stack System Payload Metadata Mapping:")
                st.json({
                    "vision_extracted_metrics": parsed_metrics,
                    "resolution_report_metrics": reports
                })

# --- 7. WORKSPACE SANITIZATION ENGINE ---
if parsed_metrics:
    if st.button("Reset Operational Workspace"):
        if "cached_vision_metrics" in st.session_state:
            del st.session_state.cached_vision_metrics
        if "cached_resolution_reports" in st.session_state:
            del st.session_state.cached_resolution_reports
        keys_to_del = [k for k in st.session_state.keys() if k.startswith("processed_")]
        for k in keys_to_del:
            del st.session_state[k]
        st.rerun()