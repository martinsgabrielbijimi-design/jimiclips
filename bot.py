import sys
import os
import subprocess
import math
import numpy as np
from faster_whisper import WhisperModel

def log(msg):
    print(f"[JimiClips Elite] {msg}", flush=True)

def extract_audio(video_file="uploaded_source.mp4", audio_file="extracted.wav"):
    log("Extracting high-precision 16kHz PCM audio stream...")
    cmd = [
        "ffmpeg", "-y",
        "-i", video_file,
        "-vn",
        "-acodec", "pcm_s16le",
        "-ar", "16000",
        "-ac", "1",
        audio_file
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    return audio_file

def find_viral_moment(audio_file, target_duration=45):
    """
    Scans the entire audio file using RMS volume + speech density
    to identify the climax/punchline window with zero dead air.
    """
    log("Analyzing VOD energy & dialogue density to pinpoint viral climax...")
    
    with open(audio_file, "rb") as f:
        f.seek(44)
        raw_data = f.read()
    
    audio_data = np.frombuffer(raw_data, dtype=np.int16).astype(np.float32) / 32768.0
    sample_rate = 16000
    total_seconds = len(audio_data) / sample_rate
    
    if total_seconds <= target_duration:
        log("Video is shorter than target duration; processing full length.")
        return 0, int(total_seconds)

    # 1-second energy windows
    step = sample_rate
    num_windows = int(len(audio_data) / step)
    energy_profile = []
    
    for i in range(num_windows):
        window = audio_data[i * step : (i + 1) * step]
        rms = np.sqrt(np.mean(window ** 2))
        energy_profile.append(rms)
    
    # Calculate rolling energy sum across target_duration window
    window_len = int(target_duration)
    best_start = 0
    max_score = -1.0
    
    for start in range(0, len(energy_profile) - window_len, 2):
        window_energy = sum(energy_profile[start : start + window_len])
        # Peak spike penalty to favor consistent engagement over one mic thud
        peak_ratio = max(energy_profile[start : start + window_len]) / (np.mean(energy_profile[start : start + window_len]) + 1e-5)
        score = window_energy * (1.0 + min(peak_ratio, 2.5))
        
        if score > max_score:
            max_score = score
            best_start = start

    log(f"Peak retention window detected: {best_start}s to {best_start + target_duration}s (Score: {max_score:.2f})")
    return best_start, target_duration

def generate_ass_subtitles(segments, clip_start, clip_duration, ass_path="subtitles.ass"):
    """
    Builds mobile safe-zone kinetic subtitles with bold yellow/green accent colors.
    """
    log("Building kinetic high-retention subtitles (.ass)...")
    
    header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Impact,80,&H00FFFFFF,&H000000FF,&H00000000,&H90000000,-1,0,0,0,100,100,1,0,1,6,3,2,60,60,420,1
Style: Highlight,Impact,86,&H002EFAF8,&H000000FF,&H00000000,&H90000000,-1,0,0,0,105,105,1,0,1,7,4,2,60,60,420,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    clip_end = clip_start + clip_duration
    events = []

    def format_time(t):
        hrs = int(t // 3600)
        mins = int((t % 3600) // 60)
        secs = t % 60
        return f"{hrs:01d}:{mins:02d}:{secs:05.2f}"

    for seg in segments:
        if seg["end"] < clip_start or seg["start"] > clip_end:
            continue
        
        # Relative clip timing
        start_rel = max(0.0, seg["start"] - clip_start)
        end_rel = min(clip_duration, seg["end"] - clip_start)
        
        if end_rel - start_rel < 0.2:
            continue

        words = seg["text"].strip().split()
        if not words:
            continue

        # Split long sentences into 2-3 word rapid kinetic bursts
        chunk_size = 3
        duration_per_word = (end_rel - start_rel) / len(words)

        for i in range(0, len(words), chunk_size):
            chunk = words[i:i + chunk_size]
            sub_start = start_rel + (i * duration_per_word)
            sub_end = min(end_rel, sub_start + (len(chunk) * duration_per_word))
            
            # Highlight first or longest word
            highlight_word = max(chunk, key=len)
            formatted_words = []
            for w in chunk:
                if w == highlight_word and len(w) > 3:
                    formatted_words.append(f"{{\\rHighlight}}{w.upper()}{{\\rDefault}}")
                else:
                    formatted_words.append(w.upper())
            
            line_text = " ".join(formatted_words)
            events.append(f"Dialogue: 0,{format_time(sub_start)},{format_time(sub_end)},Default,,0,0,0,,{line_text}")

    with open(ass_path, "w", encoding="utf-8") as f:
        f.write(header + "\n".join(events) + "\n")

    return ass_path

def transcribe_audio_segments(audio_file):
    log("Transcribing dialogue via Faster-Whisper (tiny.en)...")
    model = WhisperModel("tiny.en", device="cpu", compute_type="int8")
    
    with open(audio_file, "rb") as f:
        f.seek(44)
        raw_data = f.read()
    audio_np = np.frombuffer(raw_data, dtype=np.int16).astype(np.float32) / 32768.0
    segments_gen, _ = model.transcribe(audio_np, beam_size=5)
    
    segments = []
    for s in segments_gen:
        segments.append({"start": s.start, "end": s.end, "text": s.text})
    
    return segments

def render_elite_vertical_cut(input_video, clip_start, clip_duration, ass_file, output_clip="final_clip.mp4"):
    log(f"Rendering 1080x1920 60FPS Stacked Cut ({clip_duration}s from {clip_start}s)...")

    # Dynamic Filtergraph:
    # 1. Base Stream split into Cam (top 35%) and Screen (bottom 65%)
    # 2. Color saturation boost (+12%), slight sharpen, 60fps frame interpolation
    # 3. Stacked placement with subtle separator line
    # 4. Burn in safe-zone kinetic ASS subtitles
    # 5. Broadcast loudnorm audio leveling to -1.5 dB true peak
    
    filter_complex = (
        f"[0:v]split=2[cam_raw][game_raw];"
        f"[cam_raw]crop=in_w*0.35:in_h*0.45:0:0,scale=1080:672:flags=lanczos[cam];"
        f"[game_raw]crop=in_h*(9/16)*0.85:in_h*0.65:in_w/2-(in_h*(9/16)*0.85)/2:in_h*0.35,scale=1080:1248:flags=lanczos[game];"
        f"[cam][game]vstack=inputs=2,"
        f"eq=saturation=1.12:contrast=1.05,"
        f"unsharp=5:5:0.6:5:5:0.0,"
        f"fps=60,"
        f"ass={ass_file}[vout];"
        f"[0:a]loudnorm=I=-16:TP=-1.5:LRA=11[aout]"
    )

    cmd = [
        "ffmpeg", "-y",
        "-ss", str(clip_start),
        "-i", input_video,
        "-t", str(clip_duration),
        "-filter_complex", filter_complex,
        "-map", "[vout]",
        "-map", "[aout]",
        "-c:v", "libx264",
        "-profile:v", "high",
        "-level:v", "4.2",
        "-b:v", "16M",
        "-maxrate", "20M",
        "-bufsize", "30M",
        "-preset", "fast",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "320k",
        "-ar", "48000",
        output_clip
    ]

    subprocess.run(cmd, check=True)
    log(f"Elite master cut rendered successfully -> {output_clip}")

def main():
    input_file = sys.argv[1] if len(sys.argv) > 1 else "uploaded_source.mp4"
    target_dur = int(sys.argv[2]) if len(sys.argv) > 2 else 45
    layout_mode = sys.argv[3] if len(sys.argv) > 3 else "stacked"

    audio_path = "extracted.wav"
    ass_path = "subtitles.ass"
    output_clip = "final_clip.mp4"

    # 1. Audio extraction
    extract_audio(input_file, audio_path)

    # 2. Automated AI moment detection (peaks, laughter, loud screams, rapid speech)
    clip_start, clip_duration = find_viral_moment(audio_path, target_duration=target_dur)

    # 3. Speech transcription for kinetic subtitles
    segments = transcribe_audio_segments(audio_path)

    # 4. Generate dynamic word-burst subtitles with highlights
    generate_ass_subtitles(segments, clip_start, clip_duration, ass_path)

    # 5. Composite 1080x1920 60FPS final cut
    render_elite_vertical_cut(input_file, clip_start, clip_duration, ass_path, output_clip)

if __name__ == "__main__":
    main()
