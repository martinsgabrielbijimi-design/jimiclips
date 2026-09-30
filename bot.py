import sys
import os
import subprocess
import re
import numpy as np
from faster_whisper import WhisperModel

def log(msg):
    print(f"[JimiClips 4K] {msg}", flush=True)

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
    log("Scanning speech & semantic structure via Faster-Whisper...")
    model = WhisperModel("tiny.en", device="cpu", compute_type="int8")
    
    with open(audio_file, "rb") as f:
        f.seek(44)
        raw_data = f.read()
    audio_np = np.frombuffer(raw_data, dtype=np.int16).astype(np.float32) / 32768.0
    
    segments_gen, _ = model.transcribe(audio_np, beam_size=3)
    
    segments = []
    for s in segments_gen:
        segments.append({
            "start": float(s.start),
            "end": float(s.end),
            "text": s.text.strip()
        })
    log(f"Transcription complete: {len(segments)} narrative segments detected.")
    return segments, audio_np

def find_narrative_climax(segments, audio_np, target_duration=45, min_dur=30, max_dur=55):
    """
    Finds a complete story beat:
    - Starts on a strong sentence start (hook)
    - Captures high emotional energy & dialogue density
    - Ends naturally at a terminal punctuation mark (. ! ?) so punchline is never cut off
    """
    log("Analyzing dialogue beats to lock complete setup -> punchline narrative...")
    sample_rate = 16000
    total_seconds = len(audio_np) / sample_rate

    if total_seconds <= max_dur:
        log("Video is naturally short-form; preserving entire narrative arc.")
        return 0.0, total_seconds

    if not segments:
        # Fallback if no speech is detected: find peak audio energy window
        log("No speech segments detected; using energy envelope.")
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

    terminal_pattern = re.compile(r'[.!?]$')

    for i, start_seg in enumerate(segments):
        start_time = max(0.0, start_seg["start"] - 0.2)
        
        # Look ahead for a candidate end segment that falls within the duration window
        for j in range(i, len(segments)):
            end_seg = segments[j]
            duration = end_seg["end"] - start_time
            
            if duration < min_dur:
                continue
            if duration > max_dur:
                break
            
            # Bonus score for ending on terminal punctuation (natural punchline payoff)
            has_clean_finish = bool(terminal_pattern.search(end_seg["text"]))
            
            # Compute energy over this candidate window
            s_idx = int(start_time * sample_rate)
            e_idx = int(end_seg["end"] * sample_rate)
            chunk = audio_np[s_idx:e_idx]
            energy = np.sqrt(np.mean(chunk ** 2)) if len(chunk) > 0 else 0.0
            
            # Word density: words per second
            word_count = sum(len(s["text"].split()) for s in segments[i:j+1])
            speech_density = word_count / duration
            
            score = (energy * 100.0) + (speech_density * 1.5)
            if has_clean_finish:
                score *= 1.4  # strong preference for a finished thought
                
            if score > highest_score:
                highest_score = score
                best_start = start_time
                best_end = end_seg["end"] + 0.4  # slight breathing room for reaction payoff

    # Ensure bounds
    best_end = min(total_seconds, best_end)
    final_dur = best_end - best_start
    log(f"Locked punchline window: {best_start:.2f}s to {best_end:.2f}s (Duration: {final_dur:.2f}s)")
    return best_start, final_dur

def generate_ass_subtitles(segments, clip_start, clip_duration, ass_path="subtitles.ass"):
    """
    Builds mobile safe-zone kinetic subtitles scaled for a 4K vertical canvas (2160x3840).
    """
    log("Building 4K kinetic subtitles with pop accents (.ass)...")
    
    header = """[Script Info]
ScriptType: v4.00+
PlayResX: 2160
PlayResY: 3840

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Impact,160,&H00FFFFFF,&H000000FF,&H00000000,&H90000000,-1,0,0,0,100,100,2,0,1,12,6,2,120,120,840,1
Style: Highlight,Impact,172,&H002EFAF8,&H000000FF,&H00000000,&H90000000,-1,0,0,0,108,108,2,0,1,14,8,2,120,120,840,1

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
        duration_per_word = (end_rel - start_rel) / len(words)

        for i in range(0, len(words), chunk_size):
            chunk = words[i:i + chunk_size]
            sub_start = start_rel + (i * duration_per_word)
            sub_end = min(end_rel, sub_start + (len(chunk) * duration_per_word))
            
            highlight_word = max(chunk, key=len)
            formatted_words = []
            for w in chunk:
                # Strip non-alphanumeric characters for clean comparison
                clean_w = re.sub(r'\W+', '', w)
                if clean_w.lower() == re.sub(r'\W+', '', highlight_word).lower() and len(clean_w) > 3:
                    formatted_words.append(f"{{\\rHighlight}}{w.upper()}{{\\rDefault}}")
                else:
                    formatted_words.append(w.upper())
            
            line_text = " ".join(formatted_words)
            events.append(f"Dialogue: 0,{format_time(sub_start)},{format_time(sub_end)},Default,,0,0,0,,{line_text}")

    with open(ass_path, "w", encoding="utf-8") as f:
        f.write(header + "\n".join(events) + "\n")

    return ass_path

def render_master_4k_vertical(input_video, clip_start, clip_duration, ass_file, framing_mode="smart_center", output_clip="final_clip.mp4"):
    log(f"Rendering 4K Vertical UHD (2160x3840) [{framing_mode}]...")

    # Filtergraph options:
    # 1. smart_center: Focuses on the primary character/action without slicing them in half.
    #    Uses a blurred ambient background fill so widescreen media fills 9:16 portrait naturally without distortion.
    # 2. tight_crop: Direct 9:16 center zoom for videos where the character stays dead center.
    # 3. stacked: Only used when explicitly selected for streamer webcam + screen setups.
    
    if framing_mode == "smart_center":
        filter_complex = (
            f"[0:v]split=2[bg_raw][fg_raw];"
            f"[bg_raw]scale=2160:3840:force_original_aspect_ratio=increase,crop=2160:3840,boxblur=25:5,eq=brightness=-0.18[bg];"
            f"[fg_raw]scale=2160:-1:flags=bicubic[fg];"
            f"[bg][fg]overlay=(W-w)/2:(H-h)/2,"
            f"eq=saturation=1.12:contrast=1.05,"
            f"unsharp=5:5:0.7:5:5:0.0,"
            f"ass={ass_file}[vout];"
            f"[0:a]volume=1.25,alimiter=limit=0.92[aout]"
        )
    elif framing_mode == "tight_crop":
        filter_complex = (
            f"[0:v]crop=ih*(9/16):ih,scale=2160:3840:flags=bicubic,"
            f"eq=saturation=1.12:contrast=1.05,"
            f"unsharp=5:5:0.7:5:5:0.0,"
            f"ass={ass_file}[vout];"
            f"[0:a]volume=1.25,alimiter=limit=0.92[aout]"
        )
    else:  # stacked
        filter_complex = (
            f"[0:v]split=2[cam_raw][game_raw];"
            f"[cam_raw]crop=in_w*0.4:in_h*0.45:0:0,scale=2160:1344:flags=bicubic[cam];"
            f"[game_raw]crop=in_h*(9/16)*0.85:in_h*0.65:in_w/2-(in_h*(9/16)*0.85)/2:in_h*0.35,scale=2160:2496:flags=bicubic[game];"
            f"[cam][game]vstack=inputs=2,"
            f"eq=saturation=1.12:contrast=1.05,"
            f"unsharp=5:5:0.7:5:5:0.0,"
            f"ass={ass_file}[vout];"
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
        "-level:v", "5.1",
        "-crf", "17",             # Visually lossless 4K mastering
        "-preset", "veryfast",    # Balances quality and cloud CPU constraints
        "-threads", "2",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "320k",
        "-ar", "48000",
        output_clip
    ]

    subprocess.run(cmd, check=True)
    log(f"4K Master render complete -> {output_clip}")

def main():
    input_file = sys.argv[1] if len(sys.argv) > 1 else "uploaded_source.mp4"
    target_dur = int(sys.argv[2]) if len(sys.argv) > 2 else 45
    framing_mode = sys.argv[3] if len(sys.argv) > 3 else "smart_center"

    audio_path = "extracted.wav"
    ass_path = "subtitles.ass"
    output_clip = "final_clip.mp4"

    # 1. Audio stream extraction
    extract_audio(input_file, audio_path)

    # 2. Transcription with timestamp mapping
    segments, audio_np = transcribe_audio_segments(audio_path)

    # 3. Semantic dialogue scan for full beat (starts at hook, ends at punchline)
    clip_start, clip_duration = find_narrative_climax(segments, audio_np, target_duration=target_dur)

    # 4. Generate 4K kinetic word-burst subtitles with highlights
    generate_ass_subtitles(segments, clip_start, clip_duration, ass_path)

    # 5. Render 4K (2160x3840) Vertical Master
    render_master_4k_vertical(input_file, clip_start, clip_duration, ass_path, framing_mode, output_clip)

if __name__ == "__main__":
    main()
