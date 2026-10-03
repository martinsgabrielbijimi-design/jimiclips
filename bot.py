import sys
import os
import subprocess
import re
import numpy as np
from faster_whisper import WhisperModel

def log(msg):
    print(f"[JimiClips] {msg}", flush=True)

def extract_audio(video_file="uploaded_source.mp4", audio_file="extracted.wav"):
    log("Extracting lossless 16kHz audio stream...")
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

def transcribe_audio_full(audio_file):
    log("Running Whisper transcription (base.en, int8)...")
    model = WhisperModel("base.en", device="cpu", compute_type="int8", cpu_threads=2)

    with open(audio_file, "rb") as f:
        f.seek(44)
        raw_data = f.read()

    audio_np = np.frombuffer(raw_data, dtype=np.int16).astype(np.float32) / 32768.0

    segments_gen, _ = model.transcribe(
        audio_np,
        beam_size=4,
        word_timestamps=True,
        condition_on_previous_text=False
    )

    segments = []
    for s in segments_gen:
        txt = s.text.strip()
        if txt:
            segments.append({
                "start": float(s.start),
                "end": float(s.end),
                "text": txt
            })

    log(f"Transcription complete: {len(segments)} segments mapped.")
    return segments, audio_np

def find_narrative_boundary(segments, audio_np, target_duration=50, min_dur=35, max_dur=58):
    log("Calculating narrative boundary with punctuation lock...")
    sample_rate = 16000
    total_seconds = len(audio_np) / sample_rate

    if total_seconds <= max_dur:
        return 0.0, total_seconds, segments[-1]["text"] if segments else "KEY TAKEAWAY"

    terminal_punct = re.compile(r'[.!?]$')
    best_start = 0.0
    best_end = min(total_seconds, float(target_duration))
    best_verdict = "FOCUS ON THE FUNDAMENTALS."
    highest_score = -1.0

    for i, s_seg in enumerate(segments):
        start_t = max(0.0, s_seg["start"] - 0.1)

        for j in range(i, len(segments)):
            e_seg = segments[j]
            duration = e_seg["end"] - start_t

            if duration < min_dur:
                continue
            if duration > max_dur:
                break

            has_terminal = bool(terminal_punct.search(e_seg["text"]))
            
            s_idx = int(start_t * sample_rate)
            e_idx = int(e_seg["end"] * sample_rate)
            chunk = audio_np[s_idx:e_idx]
            energy = np.sqrt(np.mean(chunk ** 2)) if len(chunk) > 0 else 0.0

            score = energy * 100.0
            if has_terminal:
                score *= 1.6

            if score > highest_score:
                highest_score = score
                best_start = start_t
                best_end = e_seg["end"] + 0.35
                clean_end_text = re.sub(r'[^\w\s]', '', e_seg["text"]).strip().upper()
                if len(clean_end_text.split()) > 7:
                    clean_end_text = " ".join(clean_end_text.split()[-6:])
                best_verdict = clean_end_text if clean_end_text else "KEY TAKEAWAY"

    best_end = min(total_seconds, best_end)
    final_dur = best_end - best_start
    log(f"Locked clip: {best_start:.2f}s to {best_end:.2f}s ({final_dur:.2f}s)")
    return best_start, final_dur, best_verdict

def generate_sleek_ass(segments, clip_start, clip_duration, verdict_text, ass_path="subtitles.ass"):
    header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: CaptionDefault,Impact,72,&H00FFFFFF,&H000000FF,&H00000000,&H90000000,-1,0,0,0,100,100,1,0,1,6,3,2,60,60,480,1
Style: CaptionHighlight,Impact,78,&H002EFAF8,&H000000FF,&H00000000,&H90000000,-1,0,0,0,106,106,1,0,1,7,4,2,60,60,480,1
Style: HUDTag,Arial,28,&H0010B981,&H000000FF,&H00000000,&H00000000,-1,0,0,0,100,100,2,0,1,0,0,2,60,60,260,1
Style: HUDTitle,Impact,58,&H00F8FAFC,&H000000FF,&H00000000,&H00000000,-1,0,0,0,100,100,1,0,1,0,0,2,60,60,180,1
Style: HUDBody,Arial,32,&H0094A3B8,&H000000FF,&H00000000,&H00000000,-1,0,0,0,100,100,1,0,1,0,0,2,60,60,110,1
Style: VerdictCard,Impact,64,&H0034D399,&H000000FF,&H00000000,&H00000000,-1,0,0,0,100,100,1,0,1,5,2,2,60,60,160,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events = []

    def format_time(t):
        hrs = int(t // 3600)
        mins = int((t % 3600) // 60)
        secs = t % 60
        return f"{hrs:01d}:{mins:02d}:{secs:05.2f}"

    rule_filter = re.compile(r'(rule|step|number|point|part)\s+\d+', re.IGNORECASE)
    currency_regex = re.compile(r'(\$\d+[\d,\.]*|\b\d+%\b|\b\d+\s*(?:k|million|billion|thousand)\b)', re.IGNORECASE)

    concept_map = [
        (re.compile(r'(debt|loan|pay off|dues|borrow)', re.IGNORECASE), "FINANCIAL DISCIPLINE", "Eliminating liabilities before scaling"),
        (re.compile(r'(rich|wealth|mindset|lifestyle)', re.IGNORECASE), "MINDSET & BEHAVIOR", "Distinguishing true wealth from fake luxury"),
        (re.compile(r'(means|budget|afford|save|saving|coffee)', re.IGNORECASE), "CASH FLOW REALITY", "Defensive spending vs Offensive growth"),
        (re.compile(r'(skill|make money|income|support|invest)', re.IGNORECASE), "HIGH-INCOME SKILLS", "Upgrading capacity to support lifestyle")
    ]

    clip_end = clip_start + clip_duration
    card_intervals = []

    for seg in segments:
        if seg["end"] < clip_start or seg["start"] > clip_end:
            continue

        s_start = max(0.0, seg["start"] - clip_start)
        s_end = min(clip_duration - 2.5, seg["end"] - clip_start)

        if s_end - s_start < 0.2:
            continue

        text = seg["text"].strip()
        words = text.split()
        if not words:
            continue

        chunk_size = 3
        dur_word = (s_end - s_start) / len(words)

        for i in range(0, len(words), chunk_size):
            chunk = words[i:i + chunk_size]
            w_start = s_start + (i * dur_word)
            w_end = min(s_end, w_start + (len(chunk) * dur_word))

            highlight = max(chunk, key=len)
            formatted = []
            for w in chunk:
                clean_w = re.sub(r'\W+', '', w)
                if clean_w.lower() == re.sub(r'\W+', '', highlight).lower() and len(clean_w) > 3:
                    formatted.append(f"{{\\rCaptionHighlight}}{w.upper()}{{\\rCaptionDefault}}")
                else:
                    formatted.append(w.upper())

            events.append(f"Dialogue: 0,{format_time(w_start)},{format_time(w_end)},CaptionDefault,,0,0,0,,{' '.join(formatted)}")

        clean_text = rule_filter.sub('', text)
        matched_curr = currency_regex.search(clean_text)

        if matched_curr:
            fig = matched_curr.group(1).upper()
            card_intervals.append((s_start, min(s_start + 4.0, clip_duration - 2.8), "METRIC CALLOUT", fig, text[:48] + "..."))
        else:
            for pattern, c_title, c_desc in concept_map:
                if pattern.search(text):
                    card_intervals.append((s_start, min(s_start + 4.5, clip_duration - 2.8), c_title, "CORE PRINCIPLE", c_desc))
                    break

    last_end = 0.0
    for c_start, c_end, header_txt, title_txt, body_txt in card_intervals:
        if c_start < last_end:
            c_start = last_end
        if c_end - c_start < 1.5:
            continue
        events.append(f"Dialogue: 1,{format_time(c_start)},{format_time(c_end)},HUDTag,,0,0,0,,// {header_txt}")
        events.append(f"Dialogue: 1,{format_time(c_start)},{format_time(c_end)},HUDTitle,,0,0,0,,{title_txt}")
        events.append(f"Dialogue: 1,{format_time(c_start)},{format_time(c_end)},HUDBody,,0,0,0,,{body_txt}")
        last_end = c_end

    snap_start = max(0.0, clip_duration - 2.5)
    events.append(f"Dialogue: 2,{format_time(snap_start)},{format_time(clip_duration)},HUDTag,,0,0,0,,// FINAL TAKEAWAY")
    events.append(f"Dialogue: 2,{format_time(snap_start)},{format_time(clip_duration)},VerdictCard,,0,0,0,,{verdict_text}")

    with open(ass_path, "w", encoding="utf-8") as f:
        f.write(header + "\n".join(events) + "\n")

    return ass_path

def render_balanced_cut(input_video, clip_start, clip_duration, ass_file, output_clip="final_clip.mp4"):
    log(f"Rendering 78% video / 22% sleek HUD cut ({clip_duration:.1f}s)...")

    fade_len = 0.35
    fade_start = max(0.0, clip_duration - fade_len)

    filter_complex = (
        f"[0:v]split=2[bg_full][fg_main];"
        f"[bg_full]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=20:5,eq=brightness=-0.25[ambient_bg];"
        f"[fg_main]crop=ih*(9/12.5):ih,scale=1080:1500:flags=bicubic[video_top];"
        f"color=c=0x0B0F19:s=1080x420:d={clip_duration}[hud_bar];"
        f"color=c=0x10B981:s=1080x4:d={clip_duration}[accent_line];"
        f"[ambient_bg][video_top]overlay=0:0[stage1];"
        f"[stage1][hud_bar]overlay=0:1500[stage2];"
        f"[stage2][accent_line]overlay=0:1500[stage3];"
        f"[stage3]ass={ass_file}[vout];"
        f"[0:a]volume=1.2,alimiter=limit=0.92,afade=t=out:st={fade_start}:d={fade_len}[aout]"
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
    log(f"Render completed -> {output_clip}")

def main():
    input_file = sys.argv[1] if len(sys.argv) > 1 else "uploaded_source.mp4"
    target_dur = int(sys.argv[2]) if len(sys.argv) > 2 else 50

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
    segments, audio_np = transcribe_audio_full(audio_path)
    clip_start, clip_duration, verdict_text = find_narrative_boundary(segments, audio_np, target_duration=target_dur)
    generate_sleek_ass(segments, clip_start, clip_duration, verdict_text, ass_path)
    render_balanced_cut(input_file, clip_start, clip_duration, ass_path, output_clip)

    log("Execution finished successfully.")

if __name__ == "__main__":
    main()
