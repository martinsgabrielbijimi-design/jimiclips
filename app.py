import sys
import os
import subprocess
import shutil
import streamlit as st

st.set_page_config(
    page_title="JimiClips Elite Stream Editor",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 800;
        background: linear-gradient(90deg, #10B981, #6366F1);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.2rem;
    }
    .sub-text {
        color: #94A3B8;
        font-size: 1rem;
        margin-bottom: 1.8rem;
    }
    .feature-badge {
        background: #1E293B;
        border: 1px solid #334155;
        border-radius: 8px;
        padding: 0.8rem;
        text-align: center;
    }
    .badge-title {
        color: #10B981;
        font-weight: 700;
        font-size: 0.9rem;
    }
    .badge-desc {
        color: #CBD5E1;
        font-size: 0.8rem;
        margin-top: 0.2rem;
    }
</style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/video-editing.png", width=64)
    st.markdown("### 🎛️ Elite Director Settings")

    target_duration = st.slider(
        "Target Duration (seconds)",
        min_value=30,
        max_value=55,
        value=42,
        help="Strictly optimized under 58s for maximum Shorts/TikTok completion rates."
    )

    layout_mode = st.selectbox(
        "Composition Framing",
        ["Stacked Streamer (Cam Top 35% / Screen 65%)", "Dynamic Center Punch (Full Screen)"],
        index=0
    )

    st.markdown("---")
    st.markdown("### ⚡ Retention Rules Active")
    st.caption("✅ **Auto-Hook Detection:** Scans full VOD for loudest scream/punchline/play.")
    st.caption("✅ **Kinetic Typography:** Bold Impact font with neon accent pops.")
    st.caption("✅ **True Peak Normalization:** Loudnorm audio clamped to -1.5 dB.")
    st.caption("✅ **Mobile Saturation Boost:** +12% color depth.")

st.markdown('<div class="main-header">🎬 JimiClips Elite Shorts Engine</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-text">Transform raw stream recordings into punchy, high-retention 1080x1920 60FPS vertical clips.</div>', unsafe_allow_html=True)

c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown('<div class="feature-badge"><div class="badge-title">AI MOMENT PICKER</div><div class="badge-desc">Zero dead air detection</div></div>', unsafe_allow_html=True)
with c2:
    st.markdown('<div class="feature-badge"><div class="badge-title">STACKED COMPOSITION</div><div class="badge-desc">Webcam + Gameplay split</div></div>', unsafe_allow_html=True)
with c3:
    st.markdown('<div class="feature-badge"><div class="badge-title">DYNAMIC CAPTIONS</div><div class="badge-desc">Word-burst neon highlights</div></div>', unsafe_allow_html=True)
with c4:
    st.markdown('<div class="feature-badge"><div class="badge-title">MASTER BITRATE</div><div class="badge-desc">16 Mbps @ 60 FPS crisp</div></div>', unsafe_allow_html=True)

st.write("")
st.write("")

uploaded_file = st.file_uploader(
    "Upload raw stream recording or VOD (MP4, MOV, MKV up to 1GB):",
    type=["mp4", "mov", "mkv"],
    help="Upload your video file. The engine will scan the timeline to find the best viral moment."
)

if uploaded_file is not None:
    size_mb = uploaded_file.size / (1024 * 1024)
    st.success(f"📁 **VOD Ready:** `{uploaded_file.name}` ({size_mb:.1f} MB)")

    if st.button("🔥 Auto-Cut Viral Clip", type="primary", use_container_width=True):
        save_path = "uploaded_source.mp4"
        output_clip_path = "final_clip.mp4"

        with st.status("🎬 Directing elite short-form cut...", expanded=True) as status:
            st.write("📥 Streaming file to local storage...")
            
            # Reset seek pointer and write in 4MB chunks to prevent memory spikes
            uploaded_file.seek(0)
            with open(save_path, "wb") as f:
                shutil.copyfileobj(uploaded_file, f, length=4 * 1024 * 1024)

            status.update(label="🧠 Scanning timeline for energy peaks & captions...", state="running")

            log_box = st.empty()

            cmd = [
                sys.executable, "bot.py",
                save_path,
                str(target_duration),
                "stacked" if "Stacked" in layout_mode else "full"
            ]

            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )

            full_logs = ""
            for line in iter(process.stdout.readline, ''):
                full_logs += line
                log_box.code(full_logs[-1200:], language="bash")

            process.stdout.close()
            process.wait()

            if process.returncode == 0 and os.path.exists(output_clip_path):
                status.update(label="✅ Viral clip generated!", state="complete")
            else:
                status.update(label="❌ Render failed. Check logs above.", state="error")

        if os.path.exists(output_clip_path):
            st.markdown("---")
            st.markdown("### 🏆 Your Retention-Engineered Short is Ready")
            v_col, dl_col = st.columns([1.1, 1])

            with v_col:
                st.video(output_clip_path)

            with dl_col:
                st.markdown("""
                **Applied Master Optimizations:**
                - 🎯 **Viral Climax Extraction:** Hook triggered in first 2 seconds.
                - 📐 **Format:** 1080x1920 (9:16), 60 FPS, 16 Mbps.
                - 💬 **Dynamic Subtitles:** Neon highlighted kinetic word-bursts in safe zone.
                - 🔊 **Audio Mastering:** EBU R128 Loudnorm -1.5 dB True Peak.
                """)

                with open(output_clip_path, "rb") as f:
                    st.download_button(
                        label="⬇️ Download Ready-To-Post Short",
                        data=f,
                        file_name="viral_stream_clip_1080p.mp4",
                        mime="video/mp4",
                        type="primary",
                        use_container_width=True
                    )
