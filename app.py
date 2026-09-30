import sys
import os
import subprocess
import streamlit as st

st.set_page_config(
    page_title="JimiClips AI Studio",
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
        background: linear-gradient(90deg, #6366F1, #EC4899);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        color: #94A3B8;
        font-size: 1.05rem;
        margin-bottom: 2rem;
    }
    .metric-card {
        background: #1E293B;
        border-radius: 12px;
        padding: 1.2rem;
        border: 1px solid #334155;
        text-align: center;
    }
    .metric-title {
        color: #64748B;
        font-size: 0.85rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    .metric-val {
        color: #F8FAFC;
        font-size: 1.3rem;
        font-weight: 700;
        margin-top: 0.3rem;
    }
</style>
""", unsafe_allow_html=True)

# Sidebar: Studio Configuration
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/film-reel.png", width=64)
    st.markdown("### ⚙️ Video Engine Settings")
    
    # Clip duration: up to 300 seconds (5 minutes), default 120 seconds (2 minutes)
    clip_duration = st.slider(
        "Clip Duration (seconds)",
        min_value=30,
        max_value=300,
        value=130,
        step=10,
        help="Supports long clips over 2 minutes."
    )
    start_offset = st.number_input("Start Time Offset (seconds)", min_value=0, value=0, step=5)
    
    st.markdown("---")
    st.markdown("### 🎨 Visual Fidelity")
    quality_profile = st.selectbox(
        "Quality Preset",
        ["Ultra-Clear (CRF 17, Pristine)", "Balanced (CRF 18, Fast)", "Compact (CRF 22)"],
        index=0
    )
    
    crf_map = {
        "Ultra-Clear (CRF 17, Pristine)": "17",
        "Balanced (CRF 18, Fast)": "18",
        "Compact (CRF 22)": "22"
    }
    selected_crf = crf_map[quality_profile]
    
    st.caption("⚡ Powered by FFmpeg Lanczos 9:16 Resampling & Faster-Whisper.")

# Main Dashboard
st.markdown('<div class="main-header">⚡ JimiClips AI Studio</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Convert high-bitrate landscape master files into cinema-grade 1080x1920 vertical shorts.</div>', unsafe_allow_html=True)

# Highlight Metrics
col1, col2, col3 = st.columns(3)
with col1:
    st.markdown('<div class="metric-card"><div class="metric-title">Max Upload</div><div class="metric-val">1024 MB (1 GB)</div></div>', unsafe_allow_html=True)
with col2:
    st.markdown('<div class="metric-card"><div class="metric-title">Clip Range</div><div class="metric-val">Up to 5 Minutes</div></div>', unsafe_allow_html=True)
with col3:
    st.markdown('<div class="metric-card"><div class="metric-title">Scaling Engine</div><div class="metric-val">Lanczos 1080×1920</div></div>', unsafe_allow_html=True)

st.write("")
st.write("")

# Upload Container
uploaded_file = st.file_uploader(
    "Drag and drop your long-form video file (MP4, MOV, MKV)",
    type=["mp4", "mov", "mkv", "avi"],
    help="Supports master files up to 1GB."
)

if uploaded_file is not None:
    file_size_mb = uploaded_file.size / (1024 * 1024)
    st.info(f"📁 **Source Loaded:** `{uploaded_file.name}` ({file_size_mb:.1f} MB)")
    
    col_btn, _ = st.columns([1, 3])
    with col_btn:
        generate_clicked = st.button("🚀 Render 1080p Vertical Clip", type="primary", use_container_width=True)

    if generate_clicked:
        save_path = "uploaded_source.mp4"
        output_clip_path = "final_clip.mp4"
        
        with st.status("📥 Saving source to disk buffer...", expanded=True) as status:
            with open(save_path, "wb") as f:
                while chunk := uploaded_file.read(8 * 1024 * 1024):
                    f.write(chunk)
            
            status.update(label=f"⚙️ Rendering {clip_duration}s vertical clip (Whisper + FFmpeg Lanczos)...", state="running")
            
            log_container = st.empty()
            
            cmd = [
                sys.executable, "bot.py",
                save_path,
                str(start_offset),
                str(clip_duration),
                str(selected_crf)
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
                log_container.code(full_logs[-1200:], language="bash")
            
            process.stdout.close()
            process.wait()
            
            if process.returncode == 0 and os.path.exists(output_clip_path):
                status.update(label="✅ Render completed successfully!", state="complete")
            else:
                status.update(label="❌ Pipeline encountered an error.", state="error")
        
        # Display Results
        if os.path.exists(output_clip_path):
            st.markdown("### 🎬 Your 1080p Master Clip is Ready")
            res_col1, res_col2 = st.columns([1.2, 1])
            
            with res_col1:
                st.video(output_clip_path)
            
            with res_col2:
                st.success(
                    f"✨ **Encoding Details:**\n"
                    f"- Length: {clip_duration} seconds\n"
                    f"- Resolution: 1080x1920 (9:16)\n"
                    f"- Audio: 320kbps AAC stereo\n"
                    f"- Quality Profile: CRF {selected_crf}"
                )
                with open(output_clip_path, "rb") as f:
                    st.download_button(
                        label="⬇️ Download High-Bitrate Clip",
                        data=f,
                        file_name="jimiclip_master.mp4",
                        mime="video/mp4",
                        type="primary",
                        use_container_width=True
                    )
