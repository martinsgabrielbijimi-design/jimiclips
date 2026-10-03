import sys
import os
import subprocess
import shutil
import streamlit as st

st.set_page_config(
    page_title="JimiClips Studio // Transformative Engine",
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
    st.markdown("### 🎛️ Transformative Settings")

    target_duration = st.slider(
        "Target Duration (seconds)",
        min_value=35,
        max_value=58,
        value=50,
        help="Locks duration to complete narrative sentences within this window."
    )

    st.markdown("---")
    st.markdown("### 🛡️ Error Prevention Engine")
    st.caption("✅ **Dynamic Data Deck:** No blank black box on bottom.")
    st.caption("✅ **Rule Filtering:** Excludes 'Rule 3' or 'Step 1' from number callouts.")
    st.caption("✅ **Non-Obstructive Captions:** Shifted to safe boundary.")
    st.caption("✅ **Sentence Boundary Lock:** Prevents mid-word audio cutoff.")

st.markdown('<div class="hero-title">⚡ JimiClips Studio // Transformative Short Engine</div>', unsafe_allow_html=True)
st.markdown('<div class="hero-sub">Transform video clips into monetizable educational assets with live semantic concept cards and zero dead space.</div>', unsafe_allow_html=True)

c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown('<div class="spec-card"><div class="spec-title">Layout Architecture</div><div class="spec-desc">Speaker + Data Deck</div></div>', unsafe_allow_html=True)
with c2:
    st.markdown('<div class="spec-card"><div class="spec-title">Data Cards</div><div class="spec-desc">Active Concept Deck</div></div>', unsafe_allow_html=True)
with c3:
    st.markdown('<div class="spec-card"><div class="spec-title">Subtitle Placement</div><div class="spec-desc">Safe-Zone Centered</div></div>', unsafe_allow_html=True)
with c4:
    st.markdown('<div class="spec-card"><div class="spec-title">Pacing Physics</div><div class="spec-desc">Sentence-Locked Cut</div></div>', unsafe_allow_html=True)

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

    if st.button("🚀 Render Transformative Short", type="primary", use_container_width=True):
        save_path = "uploaded_source.mp4"
        output_clip_path = "final_clip.mp4"

        with st.status("🎬 Directing transformative cut...", expanded=True) as status:
            st.write("📥 Saving buffer to disk...")

            uploaded_file.seek(0)
            with open(save_path, "wb") as f:
                shutil.copyfileobj(uploaded_file, f, length=4 * 1024 * 1024)

            status.update(label="🧠 Analyzing dialogue, generating semantic cards & locking sentence boundary...", state="running")
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
                status.update(label="✅ Transformative short complete!", state="complete")
            else:
                status.update(label="❌ Pipeline failed. Check console logs.", state="error")

        if os.path.exists(output_clip_path):
            st.markdown("---")
            st.markdown("### 🏆 Ready-To-Monetize Output")
            v_col, dl_col = st.columns([1.1, 1])

            with v_col:
                st.video(output_clip_path)

            with dl_col:
                st.markdown("""
                **Applied Master Optimizations:**
                - 📐 **Dual-Zone Canvas:** Top 45% speaker window bounded by an emerald accent line.
                - 📊 **Active Data Deck:** Bottom 55% continuously populated with relevant concepts.
                - 💬 **Safe-Zone Text:** Positioned away from speaker interaction areas.
                - ⚡ **Sentence-Boundary Lock:** No truncated final words.
                """)

                with open(output_clip_path, "rb") as f:
                    st.download_button(
                        label="⬇️ Download Transformative Short",
                        data=f,
                        file_name="transformative_short_1080p.mp4",
                        mime="video/mp4",
                        type="primary",
                        use_container_width=True
                    )
