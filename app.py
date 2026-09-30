import sys
import faster_whisper
import streamlit as st
import os
import subprocess

st.set_page_config(
    page_title="JimiClips Studio",
    page_icon="🎬",
    layout="centered"
)

st.title("🎬 JimiClips AI Video Studio")
st.markdown("Transform long-form content into high-definition vertical shorts (1080p, Lanczos, CRF 18).")

tab_url, tab_upload = st.tabs(["🔗 Paste YouTube URL", "📁 Upload Local Video File"])

target_input = None

with tab_url:
    url_val = st.text_input("YouTube or Direct Video URL:", placeholder="https://www.youtube.com/watch?v=...")
    if url_val.strip():
        target_input = url_val.strip()

with tab_upload:
    uploaded_file = st.file_uploader("Upload an MP4, MOV, or MKV directly:", type=["mp4", "mov", "mkv"])
    if uploaded_file is not None:
        save_path = "uploaded_source.mp4"
        with open(save_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        target_input = save_path
        st.success("File uploaded and ready for processing.")

if st.button("Generate Clip", type="primary"):
    if not target_input:
        st.warning("Please provide a URL or upload a video file first.")
    else:
        status_box = st.empty()
        log_box = st.empty()
        status_box.info("Running JimiClips pipeline...")

        # Explicitly run using Streamlit's internal python virtual environment
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
            status_box.error("Processing failed. Review the terminal logs above.")
