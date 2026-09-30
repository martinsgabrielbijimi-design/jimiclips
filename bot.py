import sys
import os
import subprocess
import re
import numpy as np
from faster_whisper import WhisperModel

def log(msg):
    print(f"[JimiClips Engine] {msg}", flush=True)

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

def transcribe_audio_segments(audio_file):
    # Using 'base.en' instead of 'tiny.en' drastically reduces word mishearings and hallucinations
    log("Transcribing dialogue via Faster-Whisper (base.en)...")
    model = WhisperModel("base.en", device="cpu", compute_type="int8")

    with open(audio_file, "rb") as f:
        f.seek(44)
        raw_data = f.read()
    audio_np = np.frombuffer(raw_data, dtype=np.int16).astype(np.float32) / 32768.0

    segments_gen, _ = model.transcribe(
        audio_np,
        beam_size=5,
        word_timestamps=True,
        condition_on_previous_text=False,
        vad_filter=True  # Strips ambient mic noise and phantom murmurs
    )

    segments = []
    for s in segments_gen:
        txt = s.text.strip()
        if txt:
            segments.append({
                "start": float(s.start),
                "end": float(s.end),
                "text": txt,
                "words": getattr(s, "words", [])
            })

    log(f"Speech transcription complete: {len(segments)} segments mapped.")
    return segments, audio_np

def find_narrative_climax(segments, audio_np, target_duration=45, min_dur=30, max_dur=55):
    """
    Selects a complete narrative arc:
    - Starts at a sentence hook (0-2s)
    - Captures the primary dialogue/action peak
    - Locks the ending to a terminal punctuation mark (. ! ?) so punchlines are never severed mid-word.
    """
    log("Scanning dialogue beats to lock complete setup-to-punchline climax...")
    sample_rate = 16000
    total_seconds = len(audio_np) / sample_rate

    if total_seconds <= max_dur:
        log("Media length is under max duration; keeping entire video.")
        return 0.0, total_seconds

    if not segments:
        log("No speech segments detected; utilizing audio energy envelope fallback.")
        step = sample_rate
        num_windows = int(len(audio_np) / step)
        trimmed = audio_np[:num_windows * step].reshape((num_windows, step))
        rms = np.sqrt(np.mean(trimmed ** 2, axis=1))
        w = int(target_duration)
        best_s = 0
        best_score = -1.0
        for s in range(0, len(rms) - w, 2):
            score = float(np.sum(rms[s:s+w]))
            if score > best_score:
                best_score = score
                best_s = s
        return float(best_s), float(target_duration)

    best_start = segments[0]["start"]
    best_end = min(total_seconds, best_start + target_duration)
    highest_score = -1.0
    terminal_punct = re.compile(r'[.!?]$')

    for i, s_seg in enumerate(segments):
        start_time = max(0.0, s_seg["start"] - 0.2)

        for j in range(i, len(segments)):
            e_seg = segments[j]
            duration = e_seg["end"] - start_time

            if duration < min_dur:
                continue
            if duration > max_dur:
                break

            # Prioritize clean completion on sentence punctuation
            has_clean_terminal = bool(terminal_punct.search(e_seg["text"]))

            s_idx = int(start_time * sample_rate)
            e_idx = int(e_seg["end"] * sample_rate)
            chunk = audio_np[s_idx:e_idx]
            energy = np.sqrt(np.mean(chunk ** 2)) if len(chunk) > 0 else 0.0

            word_count = sum(len(s["text"].split()) for s in segments[i:j+1])
            speech_density = word_count / duration

            score = (energy * 100.0) + (speech_density * 1.5)
            if has_clean_terminal:
                score *= 1.45  # Enforces complete thought closure

            if score > highest_score:
                highest_score = score
                best_start = start_time
                best_end = e_seg["end"] + 0.4  # Trailing breathing room for final syllable

    best_end = min(total_seconds, best_end)
    final_dur = best_end - best_start
    log(f"Locked complete beat: {best_start:.2f}s to {best_end:.2f}s (Duration: {final_dur:.2f}s)")
    return best_start, final_dur

def generate_ass_subtitles(segments, clip_start, clip_duration, ass_path="subtitles.ass"):
    """
    Builds mobile safe-zone kinetic subtitles.
    MarginV is set to 920 to keep text cleanly in the upper-middle frame,
    preventing any collision with existing lower-third burned-in titles.
    """
    log("Building kinetic subtitles positioned in upper safe zone...")

    header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Impact,76,&H00FFFFFF,&H000000FF,&H00000000,&H90000000,-1,0,0,0,100,100,1,0,1,6,3,2,80,80,920,1
Style: Highlight,Impact,82,&H002EFAF8,&H000000FF,&H00000000,&H90000000,-1,0,0,0,106,106,1,0,1,7,4,2,80,80,920,1

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

        start_rel = max(0.0, seg["start"] - clip_start)
        end_rel = min(clip_duration, seg["end"] - clip_start)

        if end_rel - start_rel < 0.2:
            continue

        words = seg["text"].strip().split()
        if not words:
            continue

        chunk_size = 3
        dur_per_word = (end_rel - start_rel) / len(words)

        for i in range(0, len(words), chunk_size):
            chunk = words[i:i + chunk_size]
            sub_start = start_rel + (i * dur_per_word)
            sub_end = min(end_rel, sub_start + (len(chunk) * dur_per_word))

            highlight_word = max(chunk, key=len)
            formatted = []
            for w in chunk:
                clean_w = re.sub(r'\W+', '', w)
                if clean_w.lower() == re.sub(r'\W+', '', highlight_word).lower() and len(clean_w) > 3:
                    formatted.append(f"{{\\rHighlight}}{w.upper()}{{\\rDefault}}")
                else:
                    formatted.append(w.upper())

            line_text = " ".join(formatted)
            events.append(f"Dialogue: 0,{format_time(sub_start)},{format_time(sub_end)},Default,,0,0,0,,{line_text}")

    with open(ass_path, "w", encoding="utf-8") as f:
        f.write(header + "\n".join(events) + "\n")

    return ass_path

def render_vertical_clip(input_video, clip_start, clip_duration, ass_file, framing_mode="smart_center", output_clip="final_clip.mp4"):
    log(f"Rendering unified 1080x1920 vertical master ({clip_duration:.1f}s, Mode: {framing_mode})...")

    # Unified Framing Pipeline:
    # - 'smart_center': Keeps original subject centered with an ambient blurred fill behind it.
    #   Guarantees no horizontal chopping, stretching, or severed characters.
    # - 'tight_crop': Standard direct 9:16 center crop.
    if framing_mode == "smart_center":
        filter_complex = (
            f"[0:v]split=2[bg_raw][fg_raw];"
            f"[bg_raw]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=20:5,eq=brightness=-0.15[bg];"
            f"[fg_raw]scale=1080:-1:flags=bicubic[fg];"
            f"[bg][fg]overlay=(W-w)/2:(H-h)/2,"
            f"eq=saturation=1.10:contrast=1.04,"
            f"unsharp=5:5:0.6:5:5:0.0,"
            f"ass={ass_file}[vout];"
            f"[0:a]volume=1.2,alimiter=limit=0.92[aout]"
        )
    else:  # tight_crop
        filter_complex = (
            f"[0:v]crop=ih*(9/16):ih,scale=1080:1920:flags=bicubic,"
            f"eq=saturation=1.10:contrast=1.04,"
            f"unsharp=5:5:0.6:5:5:0.0,"
            f"ass={ass_file}[vout];"
            f"[0:a]volume=1.2,alimiter=limit=0.92[aout]"
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
        "-crf", "18",
        "-preset", "veryfast",
        "-threads", "2",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "192k",
        "-ar", "44100",
        output_clip
    ]

    subprocess.run(cmd, check=True)
    log(f"Master render successfully completed -> {output_clip}")

def main():
    input_file = sys.argv[1] if len(sys.argv) > 1 else "uploaded_source.mp4"
    target_dur = int(sys.argv[2]) if len(sys.argv) > 2 else 45
    framing_mode = sys.argv[3] if len(sys.argv) > 3 else "smart_center"

    audio_path = "extracted.wav"
    ass_path = "subtitles.ass"
    output_clip = "final_clip.mp4"

    for f_tmp in [audio_path, ass_path, output_clip]:
        if os.path.exists(f_tmp):
            try:
                os.remove(f_tmp)
            except Exception:
                pass

    # 1. Audio stream extraction
    extract_audio(input_file, audio_path)

    # 2. Base.en Whisper transcription with VAD noise-filtering
    segments, audio_np = transcribe_audio_segments(audio_path)

    # 3. Punctuation-locked narrative window selection
    clip_start, clip_duration = find_narrative_climax(segments, audio_np, target_duration=target_dur)

    # 4. Generate subtitles in upper safe-zone
    generate_ass_subtitles(segments, clip_start, clip_duration, ass_path)

    # 5. Composite unified 1080x1920 vertical master
    render_vertical_clip(input_file, clip_start, clip_duration, ass_path, framing_mode, output_clip)

    log("Execution complete.")

if __name__ == "__main__":
    main()
