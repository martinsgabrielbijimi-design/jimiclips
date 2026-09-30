import sys
import os
import subprocess
import shutil
import streamlit as st

st.set_page_config(
    page_title="JimiClips 4K AI Studio",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling for modern dark aesthetic
st.markdown("""
<style>
    .main-header {
        font-size: 2.3rem;
        font-weight: 800;
        background: linear-gradient(90deg, #10B981, #6366F1, #EC4899);
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
        help="The engine targets complete setup-to-punchline narrative arcs within this window."
    )

    framing_mode_label = st.selectbox(
        "Character & Framing Mode",
        [
            "Smart Portrait (Ambient Blur Fill - Never Slices Character)",
            "Tight Center Zoom (Full 9:16 Crop)",
            "Stacked Streamer (Webcam Top 35% / Screen 65%)"
        ],
        index=0,
        help="Smart Portrait guarantees characters/subjects are never chopped or cut in half."
    )

    framing_map = {
        "Smart Portrait (Ambient Blur Fill - Never Slices Character)": "smart_center",
        "Tight Center Zoom (Full 9:16 Crop)": "tight_crop",
        "Stacked Streamer (Webcam Top 35% / Screen 65%)": "stacked"
    }
    selected_framing = framing_map[framing_mode_label]

    st.markdown("---")
    st.markdown("### 💎 Visual & Audio Specs")
    st.caption("✅ **Master Canvas:** 2160 × 3840 (4K Vertical UHD)")
    st.caption("✅ **Narrative Engine:** Closes on sentence terminals (`. ! ?`)")
    st.caption("✅ **Kinetic Captions:** 4K-scaled Impact with neon punch pop")
    st.caption("✅ **Audio Profile:** 320 kbps studio stereo with peak limiter")

st.markdown('<div class="main-header">⚡ JimiClips 4K AI Studio</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-text">Transform long-form footage into narrative-complete 4K vertical clips with zero character slicing.</div>', unsafe_allow_html=True)

c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown('<div class="feature-badge"><div class="badge-title">Narrative Climax</div><div class="badge-desc">Full setup & punchline finish</div></div>', unsafe_allow_html=True)
with c2:
    st.markdown('<div class="feature-badge"><div class="badge-title">Smart Framing</div><div class="badge-desc">Zero character chopping</div></div>', unsafe_allow_html=True)
with c3:
    st.markdown('<div class="feature-badge"><div class="badge-title">4K Canvas</div><div class="badge-desc">2160 × 3840 ultra-clarity</div></div>', unsafe_allow_html=True)
with c4:
    st.markdown('<div class="feature-badge"><div class="badge-title">Kinetic Typography</div><div class="badge-desc">Neon accents in safe zone</div></div>', unsafe_allow_html=True)

st.write("")
st.write("")

uploaded_file = st.file_uploader(
    "Upload raw footage, stream, or video file (MP4, MOV, MKV up to 1GB):",
    type=["mp4", "mov", "mkv"],
    help="Upload your video file. The AI scans dialogue to deliver a complete punchline beat."
)

if uploaded_file is not None:
    size_mb = uploaded_file.size / (1024 * 1024)
    st.success(f"📁 **Source Loaded:** `{uploaded_file.name}` ({size_mb:.1f} MB)")

    if st.button("🚀 Render 4K Narrative Clip", type="primary", use_container_width=True):
        save_path = "uploaded_source.mp4"
        output_clip_path = "final_clip.mp4"

        with st.status("🎬 Directing 4K vertical master...", expanded=True) as status:
            st.write("📥 Streaming upload to local buffer...")
            
            uploaded_file.seek(0)
            with open(save_path, "wb") as f:
                shutil.copyfileobj(uploaded_file, f, length=4 * 1024 * 1024)

            status.update(label="🧠 Analyzing dialogue flow, punchline finish & rendering 4K canvas...", state="running")

            log_box = st.empty()

            cmd = [
                sys.executable, "bot.py",
                save_path,
                str(target_duration),
                selected_framing
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
                status.update(label="✅ 4K clip rendered successfully!", state="complete")
            else:
                status.update(label="❌ Render encountered an issue. See logs above.", state="error")

        if os.path.exists(output_clip_path):
            st.markdown("---")
            st.markdown("### 🏆 Your 4K Master Short is Ready")
            v_col, dl_col = st.columns([1.1, 1])

            with v_col:
                st.video(output_clip_path)

            with dl_col:
                st.markdown("""
                **Applied Master Optimizations:**
                - 🎯 **Narrative Beat:** Hook at start, clean punchline finish without mid-sentence cuts.
                - 📐 **Format:** 2160 × 3840 (4K UHD), 9:16 portrait.
                - 👤 **Character Framing:** Subject kept intact and framed naturally.
                - 💬 **4K Subtitles:** Scaled kinetic pop captions centered above bottom UI safe zones.
                - 🔊 **Studio Sound:** 320 kbps AAC stereo with dynamic limiter.
                """)

                with open(output_clip_path, "rb") as f:
                    st.download_button(
                        label="⬇️ Download 4K Master Clip",
                        data=f,
                        file_name="jimiclip_4k_master.mp4",
                        mime="video/mp4",
                        type="primary",
                        use_container_width=True
                    )
