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

# Custom Styling for modern dark aesthetic
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;700;800&display=swap');
    
    * {
        font-family: 'Plus Jakarta Sans', sans-serif;
    }
    
    .hero-title {
        font-size: 2.6rem;
        font-weight: 800;
        background: linear-gradient(135deg, #10B981 0%, #6366F1 50%, #EC4899 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        letter-spacing: -0.02em;
        margin-bottom: 0.2rem;
    }
    
    .hero-subtitle {
        color: #94A3B8;
        font-size: 1.1rem;
        margin-bottom: 2rem;
        line-height: 1.5;
    }
    
    .feature-card {
        background: radial-gradient(circle at top left, #1E293B, #0F172A);
        border: 1px solid #334155;
        border-radius: 14px;
        padding: 1.2rem;
        text-align: center;
        box-shadow: 0 4px 20px rgba(0,0,0,0.25);
    }
    
    .feature-icon {
        font-size: 1.6rem;
        margin-bottom: 0.3rem;
    }
    
    .feature-name {
        color: #F8FAFC;
        font-weight: 700;
        font-size: 0.95rem;
    }
    
    .feature-desc {
        color: #64748B;
        font-size: 0.8rem;
        margin-top: 0.2rem;
    }
</style>
""", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/video-editing.png", width=64)
    st.markdown("### 🎛️ Studio Controls")

    target_duration = st.slider(
        "Clip Duration",
        min_value=30,
        max_value=150,
        value=90,
        step=10,
        help="Support for extended cuts up to 2.5 minutes (150s)."
    )

    st.markdown("---")
    st.markdown("### ⚡ Engine Optimizations")
    st.caption("✅ **Extended Cuts:** Process clips up to 2.5 minutes cleanly.")
    st.caption("✅ **Pacing Engine:** Maintains narrative interest with hook & cliffhanger.")
    st.caption("✅ **Decrescendo Ending:** Smooth audio/video fadeout instead of hard drops.")
    st.caption("✅ **Single 9:16 Canvas:** Full portrait frame without horizontal slicing.")

# Main Page
st.markdown('<div class="hero-title">⚡ JimiClips Studio</div>', unsafe_allow_html=True)
st.markdown('<div class="hero-subtitle">Transform long-form footage into high-retention vertical clips (up to 2.5 minutes) with animated captions and curiosity-driven edits.</div>', unsafe_allow_html=True)

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.markdown('<div class="feature-card"><div class="feature-icon">⏱️</div><div class="feature-name">Up to 2.5 Min</div><div class="feature-desc">Longer storyline retention</div></div>', unsafe_allow_html=True)
with col2:
    st.markdown('<div class="feature-card"><div class="feature-icon">🎯</div><div class="feature-name">Curiosity Hook</div><div class="feature-desc">Builds stakes automatically</div></div>', unsafe_allow_html=True)
with col3:
    st.markdown('<div class="feature-card"><div class="feature-icon">💬</div><div class="feature-name">Dynamic ASS Text</div><div class="feature-desc">Upper safe-zone placement</div></div>', unsafe_allow_html=True)
with col4:
    st.markdown('<div class="feature-card"><div class="feature-icon">🎬</div><div class="feature-name">Smooth Decrescendo</div><div class="feature-desc">Gentle fade to black</div></div>', unsafe_allow_html=True)

st.write("")
st.write("")

uploaded_file = st.file_uploader(
    "Upload raw footage or full stream (MP4, MOV, MKV up to 1GB):",
    type=["mp4", "mov", "mkv"],
    help="Upload your video file for processing."
)

if uploaded_file is not None:
    size_mb = uploaded_file.size / (1024 * 1024)
    st.success(f"📁 **Media Ready:** `{uploaded_file.name}` ({size_mb:.1f} MB)")

    if st.button("🚀 Render Extended Clip", type="primary", use_container_width=True):
        save_path = "uploaded_source.mp4"
        output_clip_path = "final_clip.mp4"

        with st.status("🎬 Rendering vertical master cut...", expanded=True) as status:
            st.write("📥 Buffering video to storage...")

            uploaded_file.seek(0)
            with open(save_path, "wb") as f:
                shutil.copyfileobj(uploaded_file, f, length=4 * 1024 * 1024)

            status.update(label=f"🧠 Extracting {target_duration}s narrative beat & rendering subtitles...", state="running")

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
                status.update(label="✅ Master clip created successfully!", state="complete")
            else:
                status.update(label="❌ Pipeline encountered an error.", state="error")

        if os.path.exists(output_clip_path):
            st.markdown("---")
            st.markdown("### 🏆 Your Vertical Short is Ready")
            v_col, dl_col = st.columns([1.1, 1])

            with v_col:
                st.video(output_clip_path)

            with dl_col:
                st.markdown(f"""
                **Applied Master Optimizations:**
                - 🎯 **Story Arc:** Full {target_duration}-second progression with hook and peak.
                - 📐 **Format:** 1080x1920 (9:16) portrait.
                - 💬 **Dynamic Subtitles:** Placed above bottom UI overlays.
                - 🎬 **Decrescendo Ending:** 0.8s smooth audio & video fade.
                """)

                with open(output_clip_path, "rb") as f:
                    st.download_button(
                        label="⬇️ Download High-Res Clip",
                        data=f,
                        file_name="jimiclip_master.mp4",
                        mime="video/mp4",
                        type="primary",
                        use_container_width=True
                    )
