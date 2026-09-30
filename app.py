import streamlit as st
import os
import subprocess

st.set_page_config(
    page_title="AI Short-Form Video Clipper",
    page_icon="🎬",
    layout="centered"
)

st.title("🎬 AI Video Clipper Studio")
st.markdown("Transform long YouTube videos into crisp, vertical 9:16 shorts with automated hook selection and synced captions.")

# Clean input interface
url = st.text_input("YouTube URL", placeholder="https://www.youtube.com/watch?v=...")

col1, col2 = st.columns([1, 1])
with col1:
    force_fresh = st.checkbox("Download fresh video (clear old cache)", value=True)

if st.button("Generate Short ⚡", type="primary", use_container_width=True):
    if not url.strip():
        st.warning("Please paste a valid YouTube video link first.")
    else:
        # Wipe old temp cache if requested
        if force_fresh:
            for file_path in ["source.mp4", "audio.wav", os.path.join("renderer", "public", "cropped_clip.mp4"), os.path.join("renderer", "final_short.mp4")]:
                if os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                    except Exception:
                        pass

        log_container = st.empty()
        with st.status("🎬 Processing your short...", expanded=True) as status:
            st.write("1. Downloading high-res source & extracting audio...")
            # Run bot.py as subprocess
            proc = subprocess.Popen(
                ["python", "bot.py", url.strip()],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )

            # Stream live console logs into the dashboard
            logs = []
            for line in iter(proc.stdout.readline, ''):
                logs.append(line)
                log_container.code("".join(logs[-12:]))  # Display last 12 lines
            
            proc.stdout.close()
            return_code = proc.wait()

            if return_code == 0:
                status.update(label="Short rendered successfully!", state="complete", expanded=False)
            else:
                status.update(label="Rendering encountered an error.", state="error")

        final_mp4 = os.path.join("renderer", "final_short.mp4")
        if os.path.exists(final_mp4):
            st.subheader("Your Generated 9:16 Short")
            st.video(final_mp4)

            with open(final_mp4, "rb") as f:
                st.download_button(
                    label="⬇️ Download Finished Short",
                    data=f,
                    file_name="viral_short_1080p.mp4",
                    mime="video/mp4",
                    use_container_width=True
                )