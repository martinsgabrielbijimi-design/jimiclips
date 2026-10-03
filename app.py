import sys
import os
import subprocess
import shutil
import streamlit as st

st.set_page_config(
    page_title="JimiClips Studio // Pro Shorts",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;700;800&family=JetBrains+Mono:wght@600&display=swap');
    
    * {
        font-family: 'Plus Jakarta Sans', sans-serif;
    }
    
    .hero-title {
        font-size: 2.3rem;
        font-weight: 800;
        background: linear-gradient(135deg, #10B981 0%, #3B82F6 50%, #EC4899 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        letter-spacing: -0.02em;
        margin-bottom: 0.2rem;
    }
    
    .hero-sub {
        color: #94A3B8;
        font-size: 1.05rem;
        margin-bottom: 1.8rem;
    }
    
    .spec-card {
        background: #0F172A;
        border: 1px solid #1E293B;
        border-radius: 12px;
        padding: 1.1rem;
        text-align: center;
    }
    
    .spec-title {
        color: #10B981;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.8rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    
    .spec-desc {
        color: #F8FAFC;
        font-size: 1.15rem;
        font-weight: 700;
        margin-top: 0.3rem;
    }
</style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/combo-chart.png", width=64)
    st.markdown("### 🎛️ Director Settings")

    target_duration = st.slider(
        "Clip Duration (seconds)",
        min_value=35,
        max_value=55,
        value=48,
        help="Locks duration to complete narrative sentences within this window."
    )

    st.markdown("---")
    st.markdown("### ⚡ Visual Balance")
    st.caption("✅ **Video First:** Video occupies 78% of the frame.")
    st.caption("✅ **Compact Lower HUD:** Only 22% dedicated to clean ticker notes.")
    st.caption("✅ **No Giant Blue Block:** Replaced with full video presence.")
    st.caption("✅ **Punctuation Lock:** Concludes strictly on finished sentences.")

st.markdown('<div class="hero-title">⚡ JimiClips Studio // Balanced Layout</div>', unsafe_allow_html=True)
st.markdown('<div class="hero-sub">Generate full-frame vertical clips with sleek lower-third insight bars and kinetic captions.</div>', unsafe_allow_html=True)

c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown('<div class="spec-card"><div class="spec-title">Video Presence</div><div class="spec-desc">78% Screen Real-Estate</div></div>', unsafe_allow_html=True)
with c2:
    st.markdown('<div class="spec-card"><div class="spec-title">HUD Ticker</div><div class="spec-desc">Compact 22% Lower Bar</div></div>', unsafe_allow_html=True)
with c3:
    st.markdown('<div class="spec-card"><div class="spec-title">Captions</div><div class="spec-desc">Center-Action Safe Zone</div></div>', unsafe_allow_html=True)
with c4:
    st.markdown('<div class="spec-card"><div class="spec-title">Pacing</div><div class="spec-desc">Sentence-Boundary Lock</div></div>', unsafe_allow_html=True)

st.write("")
st.write("")

uploaded_file = st.file_uploader(
    "Upload raw footage or VOD (MP4, MOV, MKV up to 1GB):",
    type=["mp4", "mov", "mkv"],
    help="Upload source video."
)

if uploaded_file is not None:
    size_mb = uploaded_file.size / (1024 * 1024)
    st.success(f"📁 **Source Ready:** `{uploaded_file.name}` ({size_mb:.1f} MB)")

    if st.button("🚀 Render Balanced Short", type="primary", use_container_width=True):
        save_path = "uploaded_source.mp4"
        output_clip_path = "final_clip.mp4"

        with st.status("🎬 Rendering balanced vertical short...", expanded=True) as status:
            st.write("📥 Saving buffer to disk...")

            uploaded_file.seek(0)
            with open(save_path, "wb") as f:
                shutil.copyfileobj(uploaded_file, f, length=4 * 1024 * 1024)

            status.update(label="🧠 Analyzing dialogue, formatting 78/22 balanced canvas & locking ending...", state="running")
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
                status.update(label="✅ Balanced short complete!", state="complete")
            else:
                status.update(label="❌ Pipeline failed. Check console logs.", state="error")

        if os.path.exists(output_clip_path):
            st.markdown("---")
            st.markdown("### 🏆 Your Balanced Vertical Short is Ready")
            v_col, dl_col = st.columns([1.1, 1])

            with v_col:
                st.video(output_clip_path)

            with dl_col:
                st.markdown("""
                **Applied Master Optimizations:**
                - 📐 **78/22 Pro Layout:** Video dominates the top 78% of the vertical frame.
                - 📊 **Compact HUD Bar:** Bottom 22% holds clean real-time financial insight notes.
                - 💬 **Dynamic Subtitles:** Centered cleanly in the active visual zone.
                - ⚡ **Sentence-Boundary Lock:** No truncated final words or mid-sentence drops.
                """)

                with open(output_clip_path, "rb") as f:
                    st.download_button(
                        label="⬇️ Download Balanced Short",
                        data=f,
                        file_name="balanced_short_1080p.mp4",
                        mime="video/mp4",
                        type="primary",
                        use_container_width=True
                    )
