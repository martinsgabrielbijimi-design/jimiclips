import sys
import os
import subprocess
import shutil
import streamlit as st

st.set_page_config(
    page_title="JimiClips Studio - Viral Funnel",
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
    st.markdown("### 🎛️ Viral Retention Settings")

    target_duration = st.slider(
        "Target Duration (seconds)",
        min_value=25,
        max_value=45,
        value=35,
        help="Optimal range for building tension that leaves viewers wanting the full story."
    )

    st.markdown("---")
    st.markdown("### 🎯 Retention Architecture")
    st.caption("✅ **Story Escalation:** Automatically builds tension toward the cut point.")
    st.caption("✅ **Decrescendo Ending:** Smooth audio/video fade instead of abrupt mid-word stops.")
    st.caption("✅ **Curiosity CTA:** Adds an outro prompt encouraging viewers to check the full video.")
    st.caption("✅ **Single 9:16 Canvas:** Full portrait view without character-slicing splits.")

st.markdown('<div class="main-header">⚡ JimiClips Viral Engine</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-text">Generate hook-driven short-form teasers that drive viewers back to the full video.</div>', unsafe_allow_html=True)

c1, c2, c3 = st.columns(3)
with c1:
    st.markdown('<div class="feature-badge"><div class="badge-title">CURIOUS HOOK</div><div class="badge-desc">Builds stakes from second 1</div></div>', unsafe_allow_html=True)
with c2:
    st.markdown('<div class="feature-badge"><div class="badge-title">CLIFFHANGER CUT</div><div class="badge-desc">Ends right at the climax peak</div></div>', unsafe_allow_html=True)
with c3:
    st.markdown('<div class="feature-badge"><div class="badge-title">SMOOTH OUTRO</div><div class="badge-desc">Fade-out + curiosity prompt</div></div>', unsafe_allow_html=True)

st.write("")

uploaded_file = st.file_uploader(
    "Upload raw footage or VOD (MP4, MOV, MKV):",
    type=["mp4", "mov", "mkv"],
    help="Upload your video file for cliffhanger extraction."
)

if uploaded_file is not None:
    size_mb = uploaded_file.size / (1024 * 1024)
    st.success(f"📁 **VOD Ready:** `{uploaded_file.name}` ({size_mb:.1f} MB)")

    if st.button("🔥 Generate Viral Teaser Short", type="primary", use_container_width=True):
        save_path = "uploaded_source.mp4"
        output_clip_path = "final_clip.mp4"

        with st.status("🎬 Directing teaser arc...", expanded=True) as status:
            st.write("📥 Saving video to buffer...")

            uploaded_file.seek(0)
            with open(save_path, "wb") as f:
                shutil.copyfileobj(uploaded_file, f, length=4 * 1024 * 1024)

            status.update(label="🧠 Pinpointing tension arc, outro fade & subtitles...", state="running")

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
                status.update(label="✅ Viral teaser generated!", state="complete")
            else:
                status.update(label="❌ Render encountered an issue.", state="error")

        if os.path.exists(output_clip_path):
            st.markdown("---")
            st.markdown("### 🏆 Your Funnel Teaser Short is Ready")
            v_col, dl_col = st.columns([1.1, 1])

            with v_col:
                st.video(output_clip_path)

            with dl_col:
                st.markdown("""
                **Applied Master Optimizations:**
                - 🎯 **Curiosity Loop:** Setup and escalation included, with the final resolution held back.
                - 📐 **Unified Canvas:** Natural 1080x1920 portrait without duplicate split screens.
                - 💬 **Safe-Zone Text:** Positioned above bottom UI and original overlays.
                - 🎬 **Polished Fade Out:** Gentle decrescendo and closing prompt rather than an abrupt audio drop.
                """)

                with open(output_clip_path, "rb") as f:
                    st.download_button(
                        label="⬇️ Download Teaser Clip",
                        data=f,
                        file_name="viral_teaser_clip.mp4",
                        mime="video/mp4",
                        type="primary",
                        use_container_width=True
                    )
