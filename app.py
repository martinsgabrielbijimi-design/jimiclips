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
        font-size: 2.3rem;
        font-weight: 800;
        background: linear-gradient(90deg, #10B981, #6366F1);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.2rem;
    }
    .sub-text {
        color: #94A3B8;
        font-size: 1.05rem;
        margin-bottom: 1.8rem;
    }
    .feature-badge {
        background: #1E293B;
        border: 1px solid #334155;
        border-radius: 10px;
        padding: 0.9rem;
        text-align: center;
    }
    .badge-title {
        color: #10B981;
        font-weight: 700;
        font-size: 0.85rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    .badge-desc {
        color: #CBD5E1;
        font-size: 0.8rem;
        margin-top: 0.25rem;
    }
</style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/video-editing.png", width=64)
    st.markdown("### 🎛️ Director Settings")

    target_duration = st.slider(
        "Target Duration (seconds)",
        min_value=30,
        max_value=55,
        value=45,
        help="Locks to complete setup-to-punchline sentences within this window."
    )

    framing_mode_label = st.selectbox(
        "Framing Composition",
        [
            "Smart Portrait (Ambient Fill - Never Slices Subject)",
            "Direct Center Crop (Full 9:16 Frame)"
        ],
        index=0,
        help="Smart Portrait preserves full subject proportions with zero splitting or distortion."
    )

    framing_mode = "smart_center" if "Smart" in framing_mode_label else "tight_crop"

    st.markdown("---")
    st.markdown("### ⚡ Error Prevention Engine")
    st.caption("✅ **No Split Stacking:** Eliminates accidental dual-screens.")
    st.caption("✅ **Anti-Collision Captions:** Positions text above lower-third graphics.")
    st.caption("✅ **Whisper Base Engine:** Prevents word mishearing and phantom murmurs.")
    st.caption("✅ **Punchline Lock:** Concludes strictly on sentence terminals (`. ! ?`).")

st.markdown('<div class="main-header">⚡ JimiClips Studio</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-text">Automated high-retention short-form video generator with punctuation-locked punchline endings.</div>', unsafe_allow_html=True)

c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown('<div class="feature-badge"><div class="badge-title">Punchline Lock</div><div class="badge-desc">Zero mid-sentence cuts</div></div>', unsafe_allow_html=True)
with c2:
    st.markdown('<div class="feature-badge"><div class="badge-title">Unified Canvas</div><div class="badge-desc">No split-screen distortion</div></div>', unsafe_allow_html=True)
with c3:
    st.markdown('<div class="feature-badge"><div class="badge-title">Safe-Zone Text</div><div class="badge-desc">Zero subtitle overlap</div></div>', unsafe_allow_html=True)
with c4:
    st.markdown('<div class="feature-badge"><div class="badge-title">Whisper Base</div><div class="badge-desc">High dialogue fidelity</div></div>', unsafe_allow_html=True)

st.write("")
st.write("")

uploaded_file = st.file_uploader(
    "Upload raw footage or VOD (MP4, MOV, MKV up to 1GB):",
    type=["mp4", "mov", "mkv"],
    help="Upload your video file. The AI scans dialogue to find complete viral beats."
)

if uploaded_file is not None:
    size_mb = uploaded_file.size / (1024 * 1024)
    st.success(f"📁 **Source Loaded:** `{uploaded_file.name}` ({size_mb:.1f} MB)")

    if st.button("🚀 Render High-Retention Short", type="primary", use_container_width=True):
        save_path = "uploaded_source.mp4"
        output_clip_path = "final_clip.mp4"

        with st.status("🎬 Directing vertical master cut...", expanded=True) as status:
            st.write("📥 Saving video buffer...")

            uploaded_file.seek(0)
            with open(save_path, "wb") as f:
                shutil.copyfileobj(uploaded_file, f, length=4 * 1024 * 1024)

            status.update(label="🧠 Analyzing dialogue structure, punchlines & rendering...", state="running")

            log_box = st.empty()

            cmd = [
                sys.executable, "bot.py",
                save_path,
                str(target_duration),
                framing_mode
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
                status.update(label="✅ Short rendered successfully!", state="complete")
            else:
                status.update(label="❌ Render encountered an issue.", state="error")

        if os.path.exists(output_clip_path):
            st.markdown("---")
            st.markdown("### 🏆 Your Vertical Short is Ready")
            v_col, dl_col = st.columns([1.1, 1])

            with v_col:
                st.video(output_clip_path)

            with dl_col:
                st.markdown("""
                **Applied Master Optimizations:**
                - 🎯 **Narrative Beat:** Hook at start, clean punchline finish without mid-sentence cuts.
                - 📐 **Format:** 1080x1920 (9:16) portrait.
                - 👤 **Framing:** Single unified canvas (no horizontal chopping).
                - 💬 **Safe-Zone Text:** Positioned above bottom UI and original graphics.
                - 🔊 **Master Sound:** Peak limiting and dialogue compression.
                """)

                with open(output_clip_path, "rb") as f:
                    st.download_button(
                        label="⬇️ Download Ready-To-Post Short",
                        data=f,
                        file_name="viral_clip_1080p.mp4",
                        mime="video/mp4",
                        type="primary",
                        use_container_width=True
                    )
