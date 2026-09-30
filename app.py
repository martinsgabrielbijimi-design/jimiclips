import sys
import os
import subprocess
import faster_whisper
import streamlit as st

st.set_page_config(
    page_title="JimiClips Studio",
    page_icon="🎬",
    layout="centered"
)

# Automatically write cookies.txt from Streamlit Secrets if configured
if "YOUTUBE_COOKIES" in st.secrets:
    cookie_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cookies.txt")
    with open(cookie_file_path, "w", encoding="utf-8") as f:
        f.write(st.secrets["YOUTUBE_COOKIES"])

st.title("🎬 JimiClips AI Video Studio")
st.markdown("Transform long-form content into high-definition vertical shorts (1080p, Lanczos, CRF 18).")

tab_upload, tab_url = st.tabs(["📁 Upload Local Video File (Recommended)", "🔗 Paste YouTube URL"])

target_input = None

with tab_upload:
    st.caption("Direct upload is immune to YouTube's cloud datacenter IP blocks.")
    uploaded_file = st.file_uploader("Upload an MP4, MOV, or MKV file:", type=["mp4", "mov", "mkv"])
    if uploaded_file is not None:
        save_path = "uploaded_source.mp4"
        with open(save_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        target_input = save_path
        st.success("File uploaded and ready for processing.")

with tab_url:
    st.caption("Works if your cookies.txt is valid or YouTube has not flagged the current cloud node.")
    url_val = st.text_input("YouTube Video URL:", placeholder="https://www.youtube.com/watch?v=...")
    if url_val.strip() and not target_input:
        target_input = url_val.strip()

if st.button("Generate Clip", type="primary"):
    if not target_input:
        st.warning("Please provide a video file or YouTube URL first.")
    else:
        status_box = st.empty()
        log_box = st.empty()
        status_box.info("Running JimiClips pipeline...")

        cmd = [sys.executable, "bot.py", target_input]
        
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )

        full_logs = ""
        output_clip_path = "final_clip.mp4"

        for line in iter(process.stdout.readline, ''):
            full_logs += line
            log_box.code(full_logs[-1500:], language="bash")
        
        process.stdout.close()
        process.wait()

        if process.returncode == 0 and os.path.exists(output_clip_path):
            status_box.success("Clip created successfully!")
            st.video(output_clip_path)
            
            with open(output_clip_path, "rb") as f:
                st.download_button(
                    label="⬇️ Download High-Res Vertical Clip",
                    data=f,
                    file_name="jimiclip_final.mp4",
                    mime="video/mp4"
                )
        else:
            if "YOUTUBE_IP_BLOCK" in full_logs or "HTTP Error 403" in full_logs:
                status_box.error(
                    "YouTube blocked this cloud server instance (403 Forbidden). "
                    "Switch to the '📁 Upload Local Video File' tab to process your video directly without restrictions."
                )
            else:
                status_box.error("Processing failed. Review the terminal logs above.")
