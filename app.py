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
st.markdown("Transform long-form videos into high-quality vertical shorts (CRF 18, Lanczos scaling).")

# Input field
video_url = st.text_input("Enter YouTube or Direct Video URL:", placeholder="https://www.youtube.com/watch?v=...")

if st.button("Generate Clip", type="primary"):
    if not video_url.strip():
        st.warning("Please enter a valid URL first.")
    else:
        status_box = st.empty()
        log_box = st.empty()
        status_box.info("Starting JimiClips pipeline...")

        # Run bot.py using the exact virtualenv Python executable
        cmd = [sys.executable, "bot.py", video_url.strip()]
        
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )

        full_logs = ""
        output_clip_path = "final_clip.mp4"

        # Stream output in real time
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
