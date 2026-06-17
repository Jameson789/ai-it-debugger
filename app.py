import streamlit as st
import base64
import json
import os
from io import BytesIO
from PIL import Image
from groq import Groq
from dotenv import load_dotenv

# --- 0. ENVIRONMENT & SECURITY SETUP ---
load_dotenv()

# --- 1. CONFIGURATION & CORE INITIALIZATION ---
st.set_page_config(page_title="IT Desk Assistant - Full Build", layout="wide")
st.title("🤖 IT & Curriculum Desk Assistant")
st.caption("Complete Phase 1 & Phase 2 Pipeline: Screen Vision Parsing ──► Local Context Alignment ──► Runbook Generation")

groq_api_key = os.getenv("GROQ_API_KEY")
if not groq_api_key:
    st.error("Missing GROQ_API_KEY! Please verify that your local .env file is set up correctly.")
    st.stop()

client = Groq(api_key=groq_api_key)

# --- 2. SIDEBAR KNOWLEDGE BASE (Your District Documentation) ---
st.sidebar.header("📋 District Knowledge Base")
st.sidebar.info(
    "Modify these internal runbooks to simulate your helpdesk repository. "
    "The generation model will read these text strings to align the technical fix."
)

# Pre-populating some common district tech solutions
district_documentation = st.sidebar.text_area(
    label="Active IT Support Manuals",
    value=(
        "PLATFORM: Clever\n"
        "ERROR: ERR_403_ACCESS\n"
        "FIX: The student profile is missing an active enrollment sync link. "
        "Open Clever Admin Console -> Sync Settings -> Run Manual Nightly Delta Sync on Student ID.\n\n"
        
        "PLATFORM: Amplify\n"
        "ERROR: ERR_AUTH_REJECTED\n"
        "FIX: Chronic browser cache conflict with Single Sign-On tokens. "
        "Instruct user to open Chrome Settings -> Site Data -> Clear Amplify Cookies, or deploy the web app via a dedicated Incognito window.\n\n"
        
        "PLATFORM: McGraw-Hill\n"
        "ERROR: LICENSE_MAX_REACHED\n"
        "FIX: School building roster seat caps are maxed out. "
        "Access District Curriculum Provisioning Suite, unassign inactive students from previous semester, and move current student to active group."
    ),
    height=400
)

# --- 3. LAYOUT SETUP ---
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("📸 Intake Panel")
    uploaded_file = st.file_uploader(
        "Upload a technical error screen grab", 
        type=["png", "jpg", "jpeg"]
    )
    
    st.write("---")
    st.markdown("### ⌨️ Fallback Entry Terminal")
    fallback_active = st.checkbox("Toggle Manual Text Fallback (If image fails/blurry)")
    manual_text = st.text_area("Paste manual text details here:", disabled=not fallback_active)

# --- 4. DATA EXTRACTION LAYER ---
parsed_data = None

if uploaded_file is not None and not fallback_active:
    with col1:
        st.image(uploaded_file, caption="Target Support Screenshot", use_container_width=True)
    
    # We use Streamlit session state to cache the Vision engine's results.
    # This prevents your app from spending tokens re-analyzing the same image every time you click a tab.
    if "cached_vision_data" not in st.session_state:
        with col1:
            with st.spinner("Component 1: Extracting text metrics via Llama Vision..."):
                try:
                    img = Image.open(uploaded_file)
                    img.thumbnail((1920, 1080))

                    if img.mode in ("RGBA", "P"):
                        img = img.convert("RGB")

                    buffered = BytesIO()
                    img.save(buffered, format="JPEG", quality=85) 
                    base64_image = base64.b64encode(buffered.getvalue()).decode('utf-8')
                    
                    vision_prompt = (
                        "Analyze the provided screenshot. Extract the technical information "
                        "and output it into a clean, valid JSON object matching this schema:\n"
                        "{\n"
                        '  "platform_name": "Name of the app (e.g. Clever, Amplify, Windows)",\n'
                        '  "error_code": "The clear alphanumeric error code or title phrase string",\n'
                        '  "log_summary": "A brief summary detailing the visible failure layout"\n'
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
                    
                    st.session_state.cached_vision_data = json.loads(completion.choices[0].message.content)
                except Exception as e:
                    st.error(f"Vision Engine Failure: {e}")
                    
    parsed_data = st.session_state.get("cached_vision_data")

elif fallback_active and manual_text:
    # Set up matching dictionary schema for manual entries so the downstream engine works identically
    parsed_data = {
        "platform_name": "Identified from Text Details",
        "error_code": "MANUAL_LOG_ENTRY",
        "log_summary": manual_text
    }

# --- 5. LOGICAL RESOLUTION & GENERATION TIER ---
if parsed_data:
    with col2:
        st.subheader("⚡ Resolution Console")
        
        # Display the parsed summary of what was found
        st.info(f"**Target System:** {parsed_data.get('platform_name')} | **Error String:** {parsed_data.get('error_code')}")
        
        # Define a secondary session key to hold our processed textual analysis reports
        if "cached_resolution_text" not in st.session_state:
            with st.spinner("Component 2: Matching against district manuals & generating solutions..."):
                try:
                    # Construct the composite text prompt combining Phase 1 outputs with Phase 2 documentation data
                    generation_prompt = f"""
                    You are an advanced Tier 2 K-12 School District IT Specialist. Your task is to look at an extracted technical error case, 
                    cross-reference it with our internal district support documentation, and output two highly specific outputs.
                    
                    EXTRACTED CASE METRICS:
                    - Platform: {parsed_data.get('platform_name')}
                    - Code: {parsed_data.get('error_code')}
                    - Raw Log Summary: {parsed_data.get('log_summary')}
                    
                    OUR ACTIVE DISTRICT SUPPORT MANUALS:
                    \"\"\"
                    {district_documentation}
                    \"\"\"
                    
                    If a match exists in the manuals for the platform and error, use that specific policy. 
                    If no exact match exists, apply standard curriculum software best practices (e.g. checking SSO logs, rosters, caching issues) to synthesize a safe fix plan.
                    
                    You must return a valid JSON object matching this exact structure:
                    {{
                        "runbook_steps": "A clear, numbered step-by-step checklist of administrative steps for the IT technician to follow to fix this in the backend console.",
                        "teacher_email": "A professional, polite, and completely jargon-free email draft addressed to the teacher. Thank them for reporting it, explain what happened in comforting, plain English, and provide clear directions if they need to do anything on their end."
                    }}
                    """
                    
                    # Fire execution block against the 70B reasoning model
                    resolution_completion = client.chat.completions.create(
                        model="llama-3.3-70b-versatile",
                        messages=[{"role": "user", "content": generation_prompt}],
                        response_format={"type": "json_object"}
                    )
                    
                    st.session_state.cached_resolution_text = json.loads(resolution_completion.choices[0].message.content)
                except Exception as e:
                    st.error(f"Resolution Generator Failure: {e}")
                    
        # Render the final deliverables side by side using layout tabs
        resolution_reports = st.session_state.get("cached_resolution_text")
        
        if resolution_reports:
            tab1, tab2, tab3 = st.tabs(["🛠️ IT Tech Runbook", "📧 Teacher Email Draft", "📦 Raw JSON Output"])
            
            with tab1:
                st.markdown("### Internal Technical Checklist")
                st.write("Follow these administrative instructions to handle the case backend:")
                st.markdown(resolution_reports.get("runbook_steps"))
                
            with tab2:
                st.markdown("### Client Communication Template")
                st.write("Copy and paste this message directly into your email platform or helpdesk ticketing suite:")
                st.text_area(
                    label="Email Body Target",
                    value=resolution_reports.get("teacher_email"),
                    height=300
                )
                
            with tab3:
                st.write("#### Combined System Output Vector Schema:")
                st.json({
                    "vision_tier_metrics": parsed_data,
                    "resolution_tier_metrics": resolution_reports
                })

# --- 6. STATE LIFECYCLE RECOVERY ---
if parsed_data:
    if st.button("Reset Assistant Panel"):
        # Clear out session state trackers completely to allow clean fresh operations
        if "cached_vision_data" in st.session_state:
            del st.session_state.cached_vision_data
        if "cached_resolution_text" in st.session_state:
            del st.session_state.cached_resolution_text
        st.rerun()