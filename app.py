import os
from dotenv import load_dotenv
import streamlit as st
import base64
import json
from io import BytesIO
from PIL import Image
from groq import Groq

load_dotenv()

# --- 1. CONFIGURATION & CORE INITIALIZATION ---
st.set_page_config(page_title="IT Assistant - Phase 1", layout="wide")
st.title("🤖 IT Desk Assistant: Phase 1 Intake Terminal")
st.caption("Testing Phase: Image Upload -> Base64 Encoding -> Groq Vision JSON Extraction")

# Initialize the Groq SDK client
# Note: For production or grading, you can set the environment variable GROQ_API_KEY
GROQ_API_KEY = os.getenv("GROQ_API_KEY") 
client = Groq(api_key=GROQ_API_KEY)

# --- 2. LAYOUT SETUP ---
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("📸 Upload Screenshot")
    uploaded_file = st.file_uploader(
        "Drag and drop or browse for an IT error message screenshot", 
        type=["png", "jpg", "jpeg"]
    )
    
    # Text fallback mitigation layout feature
    st.write("---")
    st.markdown("### ⌨️ Fallback Entry Terminal")
    fallback_active = st.checkbox("Toggle Manual Text Fallback (If image fails/blurry)")
    manual_text = st.text_area("Paste manual log error string here:", disabled=not fallback_active)

# --- 3. CORE PROCESSING PIPELINE ---
if uploaded_file is not None and not fallback_active:
    with col1:
        # Display the target image natively in the Streamlit UI
        st.image(uploaded_file, caption="Target Support Screenshot", use_container_width=True)

    with col2:
        st.subheader("⚡ Groq Vision Extraction Result")
        
        with st.spinner("Processing image via Llama 3.2 Vision on Groq LPUs..."):
            try:
                # STEP A: Open the image using Pillow for downscaling protection
                img = Image.open(uploaded_file)
                
                # Mitigation: Downscale to a max bound of 1080p to keep token counts tight
                img.thumbnail((1920, 1080))
                
                # STEP B: Convert the in-memory Pillow image into a Base64 text string
                buffered = BytesIO()
                # Save optimized image back to the memory stream buffer
                img.save(buffered, format="JPEG", quality=85) 
                base64_image = base64.b64encode(buffered.getvalue()).decode('utf-8')
                
                # STEP C: Define the prompt and structural JSON blueprint required by the UI
                system_prompt = (
                    "You are a specialized IT helpdesk data extraction parser. "
                    "Analyze the provided screenshot. Extract the technical information "
                    "and output it into a clean, valid JSON object. "
                    "Do not include any chat formatting, markdown blocks, text descriptions, or conversational pleasantries. "
                    "The output must strictly be a raw stringified JSON object matching this schema:\n"
                    "{\n"
                    '  "platform_name": "Name of the app/system seen (e.g. Clever, Amplify, Windows)",\n'
                    '  "error_code": "The literal alphanumeric error code or core short error title string",\n'
                    '  "log_summary": "A brief, highly dense technical summary explaining what exactly failed in the UI Layout"\n'
                    "}"
                )
                
                # STEP D: Fire the multimodal payload across the Groq infrastructure API
                # Using meta-llama/llama-3.2-11b-vision-preview as declared in your plan
                completion = client.chat.completions.create(
                    model="meta-llama/llama-3.2-11b-vision-preview",
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": system_prompt},
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/jpeg;base64,{base64_image}"
                                    }
                                }
                            ]
                        }
                    ],
                    # Enforce hard token execution constraints to guarantee flawless JSON formatting
                    response_format={"type": "json_object"}
                )
                
                # STEP E: Extract the string block and safely parse it into native Python dict
                raw_json_string = completion.choices[0].message.content
                parsed_data = json.loads(raw_json_string)
                
                # Display structural success cards to show off the parsing data
                st.success("JSON Extraction Successful!")
                
                # Display metrics visually
                st.metric(label="Detected Platform", value=parsed_data.get("platform_name", "Unknown"))
                st.code(f"Error Code: {parsed_data.get('error_code', 'N/A')}")
                
                # Render the final raw structural payload out onto the dashboard container
                st.write("#### Structured Object Payload:")
                st.json(parsed_data)
                
            except Exception as e:
                st.error(f"Execution Error encountered during analysis: {e}")

# --- 4. FALLBACK LOGIC ENGINE ---
elif fallback_active and manual_text:
    with col2:
        st.subheader("⚡ Manual Extraction Output")
        st.info("Bypassing Vision Engine. Creating structural JSON dictionary from manual text input string.")
        
        # Simulating what the dictionary will look like so the pipeline stays uniform
        simulated_json = {
            "platform_name": "Manual Tech Entry",
            "error_code": "MANUAL_INPUT",
            "log_summary": manual_text
        }
        st.json(simulated_json)