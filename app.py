import sys
import os
import subprocess
import shutil
import streamlit as st

st.set_page_config(
    page_title="JimiClips Studio",
    page_icon="⚡",
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
        font-size: 0.85rem;
    }
    .badge-desc {
        color: #CBD5E1;
        font-size: 0.75rem;
        margin-top: 0.2rem;
    }
</style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/video-editing.png", width=64)
    st.markdown("### 🎛️ Director Settings")

    target_duration = st.slider(
        "Clip Duration (seconds)",
        min_value=30,
        max_value=55,
        value=42,
        help="Target length for high-retention clips."
    )

    st.markdown("---")
    st.markdown("### ⚡ Low-CPU Engine")
    st.caption("✅ **Windowed Whisper:** Only transcribes the exact punchline beat.")
    st.caption("✅ **Single-Core Throttling Shield:** Runs at 1 thread to avoid platform caps.")
    st.caption("✅ **Unified 9:16 Canvas:** Zero split-screen character chopping.")
    st.caption("✅ **Upper Safe-Zone Text:** No collision with bottom captions.")

st.markdown('<div class="main-header">⚡ JimiClips Studio</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-text">High-retention vertical short generator with low-CPU footprint.</div>', unsafe_allow_html=True)

c1, c2, c3 = st.columns(3)
with c1:
    st.markdown('<div class="feature-badge"><div class="badge-title">AI HOOK FINDER</div><div class="badge-desc">Energy envelope scan</div></div>', unsafe_allow_html=True)
with c2:
    st.markdown('<div class="feature-badge"><div class="badge-title">UNIFIED 9:16</div><div class="badge-desc">No severed characters</div></div>', unsafe_allow_html=True)
with c3:
    st.markdown('<div class="feature-badge"><div class="badge-title">SAFE-ZONE TEXT</div><div class="badge-desc">Clean subtitle placement</div></div>', unsafe_allow_html=True)

st.write("")

uploaded_file = st.file_uploader(
    "Upload stream or video file (MP4, MOV, MKV):",
    type=["mp4", "mov", "mkv"],
    help="Upload your video file for processing."
)

if uploaded_file is not None:
    size_mb = uploaded_file.size / (1024 * 1024)
    st.success(f"📁 **VOD Ready:** `{uploaded_file.name}` ({size_mb:.1f} MB)")

    if st.button("🔥 Auto-Cut Viral Clip", type="primary", use_container_width=True):
        save_path = "uploaded_source.mp4"
        output_clip_path = "final_clip.mp4"

        with st.status("🎬 Rendering clip under CPU limits...", expanded=True) as status:
            st.write("📥 Buffering video to storage...")

            uploaded_file.seek(0)
            with open(save_path, "wb") as f:
                shutil.copyfileobj(uploaded_file, f, length=4 * 1024 * 1024)

            status.update(label="🧠 Locating climax beat & generating vertical cut...", state="running")

            log_box = st.empty()

            cmd = [
                sys.executable, "bot.py",
                save_path,
                str(target_duration)
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
                status.update(label="✅ Clip created successfully!", state="complete")
            else:
                status.update(label="❌ Render encountered an error.", state="error")

        if os.path.exists(output_clip_path):
            st.markdown("---")
            st.markdown("### 🏆 Your Vertical Short is Ready")
            v_col, dl_col = st.columns([1.1, 1])

            with v_col:
                st.video(output_clip_path)

            with dl_col:
                st.markdown("""
                **Applied Master Optimizations:**
                - 🎯 **Viral Moment:** Automatically captured high-action climax.
                - 📐 **Format:** 1080x1920 (9:16) portrait.
                - 💬 **Dynamic Subtitles:** Kinetic highlights in upper safe zone.
                - ⚡ **Optimized Render:** Zero CPU throttling penalty.
                """)

                with open(output_clip_path, "rb") as f:
                    st.download_button(
                        label="⬇️️ Download 1080p Clip",
                        data=f,
                        file_name="viral_clip_1080p.mp4",
                        mime="video/mp4",
                        type="primary",
                        use_container_width=True
                    )
