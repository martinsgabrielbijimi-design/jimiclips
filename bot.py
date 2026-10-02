import sys
import os
import subprocess
import re
import numpy as np
from faster_whisper import WhisperModel

def log(msg):
    print(f"[JimiClips Studio] {msg}", flush=True)

def extract_audio(video_file="uploaded_source.mp4", audio_file="extracted.wav"):
    log("Extracting lossless audio stream...")
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

def find_cliffhanger_window(audio_file, target_duration=90):
    log(f"Scanning audio waveform for narrative arc ({target_duration}s)...")
    sample_rate = 16000

    with open(audio_file, "rb") as f:
        f.seek(44)
        raw_data = f.read()

    audio_data = np.frombuffer(raw_data, dtype=np.int16).astype(np.float32) / 32768.0
    total_sec = len(audio_data) / sample_rate

    if total_sec <= target_duration:
        return 0.0, total_sec

    step = sample_rate
    num_buckets = int(len(audio_data) / step)
    reshaped = audio_data[:num_buckets * step].reshape((num_buckets, step))
    rms_profile = np.sqrt(np.mean(reshaped ** 2, axis=1))

    window_len = int(target_duration)
    best_start = 0
    max_escalation_score = -1.0

    # Scan for sections with strong opening hook and sustained escalation
    for s in range(0, len(rms_profile) - window_len, 2):
        chunk = rms_profile[s : s + window_len]
        early_energy = float(np.mean(chunk[:int(window_len * 0.25)]))
        climax_energy = float(np.mean(chunk[-int(window_len * 0.25):]))
        
        escalation = (climax_energy + 1e-4) / (early_energy + 1e-4)
        total_energy = float(np.sum(chunk))
        score = total_energy * min(escalation, 2.5)

        if score > max_escalation_score:
            max_escalation_score = score
            best_start = s

    log(f"Locked story arc: {best_start}s to {best_start + target_duration}s")
    return float(best_start), float(target_duration)

def transcribe_window_only(audio_file, clip_start, clip_duration):
    log("Running Whisper AI on selected moment (int8 engine)...")
    sample_rate = 16000
    start_byte = 44 + int(clip_start * sample_rate * 2)
    len_bytes = int(clip_duration * sample_rate * 2)

    with open(audio_file, "rb") as f:
        f.seek(start_byte)
        raw_data = f.read(len_bytes)

    clip_audio = np.frombuffer(raw_data, dtype=np.int16).astype(np.float32) / 32768.0

    model = WhisperModel("base.en", device="cpu", compute_type="int8", cpu_threads=2)
    segments_raw, _ = model.transcribe(
        clip_audio,
        beam_size=3,
        word_timestamps=True,
        condition_on_previous_text=False
    )

    segments = []
    for s in segments_raw:
        txt = s.text.strip()
        if txt:
            segments.append({
                "start": float(s.start),
                "end": float(s.end),
                "text": txt
            })

    return segments

def generate_safe_subtitles(segments, clip_duration, ass_path="subtitles.ass"):
    header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Impact,76,&H00FFFFFF,&H000000FF,&H00000000,&H90000000,-1,0,0,0,100,100,1,0,1,6,3,2,80,80,920,1
Style: Highlight,Impact,82,&H002EFAF8,&H000000FF,&H00000000,&H90000000,-1,0,0,0,106,106,1,0,1,7,4,2,80,80,920,1
Style: OutroCTA,Impact,70,&H0000FFFF,&H000000FF,&H00000000,&HB0000000,-1,0,0,0,100,100,1,0,1,6,4,2,60,60,820,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events = []

    def format_time(t):
        hrs = int(t // 3600)
        mins = int((t % 3600) // 60)
        secs = t % 60
        return f"{hrs:01d}:{mins:02d}:{secs:05.2f}"

    dialogue_cutoff = max(0.0, clip_duration - 1.8)

    for seg in segments:
        s_start = max(0.0, seg["start"])
        s_end = min(dialogue_cutoff, seg["end"])

        if s_end - s_start < 0.2:
            continue

        words = seg["text"].split()
        if not words:
            continue

        chunk_size = 3
        dur_word = (s_end - s_start) / len(words)

        for i in range(0, len(words), chunk_size):
            chunk = words[i:i + chunk_size]
            sub_start = s_start + (i * dur_word)
            sub_end = min(s_end, sub_start + (len(chunk) * dur_word))

            highlight = max(chunk, key=len)
            formatted = []
            for w in chunk:
                clean_w = re.sub(r'\W+', '', w)
                if clean_w.lower() == re.sub(r'\W+', '', highlight).lower() and len(clean_w) > 3:
                    formatted.append(f"{{\\rHighlight}}{w.upper()}{{\\rDefault}}")
                else:
                    formatted.append(w.upper())

            events.append(f"Dialogue: 0,{format_time(sub_start)},{format_time(sub_end)},Default,,0,0,0,,{' '.join(formatted)}")

    # Ending callout hook
    cta_start = max(0.0, clip_duration - 2.0)
    events.append(f"Dialogue: 1,{format_time(cta_start)},{format_time(clip_duration)},OutroCTA,,0,0,0,,WATCH FULL VIDEO FOR PART 2...")

    with open(ass_path, "w", encoding="utf-8") as f:
        f.write(header + "\n".join(events) + "\n")

    return ass_path

def render_vertical_clip(input_video, clip_start, clip_duration, ass_file, output_clip="final_clip.mp4"):
    log(f"Rendering 1080x1920 portrait master ({clip_duration:.1f}s)...")
    
    fade_len = 0.8
    fade_start = max(0.0, clip_duration - fade_len)

    filter_complex = (
        f"[0:v]crop=ih*(9/16):ih,scale=1080:1920:flags=bicubic,"
        f"eq=saturation=1.08:contrast=1.03,"
        f"ass={ass_file},"
        f"fade=t=out:st={fade_start}:d={fade_len}[vout];"
        f"[0:a]volume=1.2,alimiter=limit=0.92,"
        f"afade=t=out:st={fade_start}:d={fade_len}[aout]"
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
        "-crf", "19",
        "-preset", "ultrafast",
        "-threads", "1",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "192k",
        "-ar", "44100",
        output_clip
    ]

    subprocess.run(cmd, check=True)
    log(f"Export successful -> {output_clip}")

def main():
    input_file = sys.argv[1] if len(sys.argv) > 1 else "uploaded_source.mp4"
    target_dur = int(sys.argv[2]) if len(sys.argv) > 2 else 90

    audio_path = "extracted.wav"
    ass_path = "subtitles.ass"
    output_clip = "final_clip.mp4"

    for f_tmp in [audio_path, ass_path, output_clip]:
        if os.path.exists(f_tmp):
            try:
                os.remove(f_tmp)
            except Exception:
                pass

    extract_audio(input_file, audio_path)
    clip_start, clip_duration = find_cliffhanger_window(audio_path, target_duration=target_dur)
    segments = transcribe_window_only(audio_path, clip_start, clip_duration)
    generate_safe_subtitles(segments, clip_duration, ass_path)
    render_vertical_clip(input_file, clip_start, clip_duration, ass_path, output_clip)

    log("Workflow finished.")

if __name__ == "__main__":
    main()
