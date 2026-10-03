import sys
import os
import subprocess
import re
import numpy as np
from faster_whisper import WhisperModel

def log(msg):
    print(f"[JimiClips Transformative] {msg}", flush=True)

def extract_audio(video_file="uploaded_source.mp4", audio_file="extracted.wav"):
    log("Extracting lossless 16kHz PCM audio stream...")
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

def find_retention_window(audio_file, target_duration=54):
    """
    Locates the highest-energy 50-55s narrative window.
    """
    log("Scanning audio for narrative build...")
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
    max_score = -1.0

    for s in range(0, len(rms_profile) - window_len, 2):
        chunk = rms_profile[s : s + window_len]
        early_energy = float(np.mean(chunk[:int(window_len * 0.25)]))
        climax_energy = float(np.mean(chunk[-int(window_len * 0.25):]))
        
        escalation = (climax_energy + 1e-4) / (early_energy + 1e-4)
        total_energy = float(np.sum(chunk))
        score = total_energy * min(escalation, 2.5)

        if score > max_score:
            max_score = score
            best_start = s

    return float(best_start), float(target_duration)

def transcribe_clip_window(audio_file, clip_start, clip_duration):
    log("Transcribing targeted dialogue window with base.en...")
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

def generate_transformative_ass(segments, clip_duration, ass_path="subtitles.ass"):
    """
    Generates:
    1. Kinetic captions in the Context Zone (top/middle safe margin).
    2. Dynamic Financial Data Cards in the Data Zone (bottom 55%) whenever numbers/money appear.
    3. Terminal Snap Verdict during the final 3 seconds.
    """
    log("Building transformative data-board overlays & kinetic subtitles (.ass)...")

    # 1080x1920 layout coordinate reference:
    # Speaker Zone: Y=0 to Y=864 (Top 45%)
    # Data Board Zone: Y=864 to Y=1920 (Bottom 55%)
    header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: CaptionDefault,Impact,64,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,1,0,1,5,2,2,60,60,1080,1
Style: CaptionHighlight,Impact,68,&H0010E010,&H000000FF,&H00000000,&H80000000,-1,0,0,0,105,105,1,0,1,6,3,2,60,60,1080,1
Style: BoardHeader,Arial,34,&H0094A3B8,&H000000FF,&H00000000,&H00000000,-1,0,0,0,100,100,2,0,1,0,0,2,60,60,780,1
Style: DataMetricPos,Impact,108,&H0034D399,&H000000FF,&H00000000,&H00000000,-1,0,0,0,100,100,1,0,1,0,0,2,60,60,650,1
Style: DataMetricNeg,Impact,108,&H003838EF,&H000000FF,&H00000000,&H00000000,-1,0,0,0,100,100,1,0,1,0,0,2,60,60,650,1
Style: DataLabel,Arial,38,&H00F8FAFC,&H000000FF,&H00000000,&H00000000,-1,0,0,0,100,100,1,0,1,0,0,2,60,60,560,1
Style: TerminalVerdict,Impact,80,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,-1,0,0,0,100,100,1,0,1,6,4,2,80,80,620,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events = []

    def format_time(t):
        hrs = int(t // 3600)
        mins = int((t % 3600) // 60)
        secs = t % 60
        return f"{hrs:01d}:{mins:02d}:{secs:05.2f}"

    number_regex = re.compile(r'(\$?\d+[\d,\.]*\s?(?:thousand|million|percent|k|m|%|dollars)?)', re.IGNORECASE)
    negative_trigger = re.compile(r'(cost|drop|spent|loss|debt|tax|rent|loan|fail|lost|expensive|-)', re.IGNORECASE)

    active_cards = []

    for seg in segments:
        s_start = max(0.0, seg["start"])
        s_end = min(clip_duration - 3.0, seg["end"])  # Leave last 3s for terminal snap

        if s_end - s_start < 0.2:
            continue

        words = seg["text"].split()
        if not words:
            continue

        # Check for financial figures to trigger bottom-deck metric cards
        match = number_regex.search(seg["text"])
        if match:
            raw_metric = match.group(1).upper()
            is_neg = bool(negative_trigger.search(seg["text"]))
            style_name = "DataMetricNeg" if is_neg else "DataMetricPos"
            prefix = "-" if is_neg and not raw_metric.startswith("-") else ("+" if not is_neg and not raw_metric.startswith("$") else "")
            
            # Format display value
            metric_display = f"{prefix}{raw_metric}"
            active_cards.append((s_start, min(s_start + 3.8, clip_duration - 3.2), style_name, metric_display, seg["text"][:36] + "..."))

        # Paced kinetic captions (max 3-4 words)
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
                    formatted.append(f"{{\\rCaptionHighlight}}{w.upper()}{{\\rCaptionDefault}}")
                else:
                    formatted.append(w.upper())

            events.append(f"Dialogue: 0,{format_time(sub_start)},{format_time(sub_end)},CaptionDefault,,0,0,0,,{' '.join(formatted)}")

    # Add dynamic financial cards to Data Deck
    for card_start, card_end, card_style, card_metric, card_desc in active_cards:
        events.append(f"Dialogue: 1,{format_time(card_start)},{format_time(card_end)},BoardHeader,,0,0,0,,DATA LEDGER // REAL-TIME CALCULATION")
        events.append(f"Dialogue: 1,{format_time(card_start)},{format_time(card_end)},{card_style},,0,0,0,,{card_metric}")
        events.append(f"Dialogue: 1,{format_time(card_start)},{format_time(card_end)},DataLabel,,0,0,0,,{card_desc.upper()}")

    # Phase 5: The Terminal Snap (Final 2.5s)
    snap_start = max(0.0, clip_duration - 2.5)
    events.append(f"Dialogue: 2,{format_time(snap_start)},{format_time(clip_duration)},BoardHeader,,0,0,0,,FINAL VERDICT")
    events.append(f"Dialogue: 2,{format_time(snap_start)},{format_time(clip_duration)},TerminalVerdict,,0,0,0,,CALCULATE THE NET FIRST.")

    with open(ass_path, "w", encoding="utf-8") as f:
        f.write(header + "\n".join(events) + "\n")

    return ass_path

def render_transformative_cut(input_video, clip_start, clip_duration, ass_file, output_clip="final_clip.mp4"):
    log(f"Rendering transformative 9:16 layout ({clip_duration:.1f}s)...")

    # Layout Blueprint:
    # 1. Base Slate Canvas: 1080x1920 in deep slate (#0F172A).
    # 2. Speaker Window: Cropped to 1080x864 (Top 45%), placed at (0, 0).
    # 3. Accent Line: Vibrant 4px emerald line (#10B981) separating Speaker Window from Data Board.
    # 4. Data Board: 1080x1056 (Bottom 55%) host for dynamic charts/cards.
    # 5. Terminal Snap Cut: Instant visual/audio snap to black on final syllable (no slow fade).

    filter_complex = (
        f"color=c=0x0F172A:s=1080x1920:d={clip_duration}[canvas];"
        f"[0:v]crop=ih*(16/9)*0.75:ih*0.75:in_w/2-(ih*(16/9)*0.75)/2:in_h*0.1,scale=1080:860:flags=bicubic[speaker];"
        f"color=c=0x10B981:s=1080x4:d={clip_duration}[border];"
        f"[canvas][speaker]overlay=0:0[stage1];"
        f"[stage1][border]overlay=0:860[stage2];"
        f"[stage2]ass={ass_file}[vout];"
        f"[0:a]volume=1.25,alimiter=limit=0.92[aout]"
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
        "-crf", "18",
        "-preset", "ultrafast",
        "-threads", "1",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "192k",
        "-ar", "44100",
        output_clip
    ]

    subprocess.run(cmd, check=True)
    log(f"Render completed: {output_clip}")

def main():
    input_file = sys.argv[1] if len(sys.argv) > 1 else "uploaded_source.mp4"
    target_dur = int(sys.argv[2]) if len(sys.argv) > 2 else 54

    audio_path = "extracted.wav"
    ass_path = "subtitles.ass"
    output_clip = "final_clip.mp4"

    for tmp in [audio_path, ass_path, output_clip]:
        if os.path.exists(tmp):
            try:
                os.remove(tmp)
            except Exception:
                pass

    extract_audio(input_file, audio_path)
    clip_start, clip_duration = find_retention_window(audio_path, target_duration=target_dur)
    segments = transcribe_clip_window(audio_path, clip_start, clip_duration)
    generate_transformative_ass(segments, clip_duration, ass_path)
    render_transformative_cut(input_file, clip_start, clip_duration, ass_path, output_clip)

    log("Transformative rendering complete.")

if __name__ == "__main__":
    main()
