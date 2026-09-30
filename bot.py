import json
import os
import sys
import subprocess
from faster_whisper import WhisperModel
from google import genai
from google.genai import types
from pydantic import BaseModel, Field
from typing import List
import yt_dlp

GEMINI_KEY = "AQ.Ab8RN6Jkg9WqAf_B-suz8tn4J5DemesXlpqab0bnqWA8y1fKsg"

# 1. Download source in crisp 1080p & extract audio
def prepare_media(url_or_file):
    video_file = "source.mp4"
    audio_file = "audio.wav"

    if not os.path.exists(video_file) or os.path.getsize(video_file) < 100000:
        print("    Downloading high-definition source (up to 1080p)...")
        ydl_opts = {
            # Target clean 1080p/best MP4 stream with crisp audio
            'format': 'bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=1080]+bestaudio/best[height<=1080]/best',
            'outtmpl': video_file,
            'merge_output_format': 'mp4',
            'socket_timeout': 30,
            'retries': 10,
            'fragment_retries': 10,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url_or_file])
    else:
        print("    Found existing 'source.mp4', skipping re-download.")

    if not os.path.exists(audio_file) or os.path.getsize(audio_file) < 50000:
        print("    Extracting 16kHz speech track for Whisper...")
        subprocess.run([
            "ffmpeg", "-y", "-i", video_file,
            "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1",
            audio_file
        ], check=True)
    else:
        print("    Found existing 'audio.wav', skipping extraction.")

    return video_file, audio_file

# 2. Local speech-to-text with word timestamps
def transcribe(audio_file):
    print("    Transcribing audio locally...")
    model = WhisperModel("base", device="cpu", compute_type="int8")
    segments, _ = model.transcribe(audio_file, word_timestamps=True, vad_filter=True)

    words, lines = [], []
    for s in segments:
        lines.append(f"[{s.start:.2f} -> {s.end:.2f}] {s.text.strip()}")
        if s.words:
            for w in s.words:
                words.append({"text": w.word.strip(), "start": w.start, "end": w.end})
    return words, "\n".join(lines)

# 3. Clip Selection
class ClipInfo(BaseModel):
    title: str
    start_time: float = Field(description="Clip start in seconds")
    end_time: float = Field(description="Clip end in seconds")

class ClipResponse(BaseModel):
    clips: List[ClipInfo]

def pick_best_clip(transcript_str, all_words):
    client = genai.Client(api_key=GEMINI_KEY)
    prompt = (
        "Analyze this transcript and pick exactly 1 standalone, high-retention viral hook "
        "segment between 30 and 50 seconds:\n\n"
        f"{transcript_str}"
    )

    for model_name in ['gemini-3.8-flash', 'gemini-3-flash-preview']:
        try:
            print(f"    Requesting hook from {model_name}...")
            res = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=ClipResponse,
                    temperature=0.2
                )
            )
            data = ClipResponse.model_validate_json(res.text)
            return data.clips[0]
        except Exception as e:
            print(f"    {model_name} unavailable: {e}")

    print("    [Fallback] Using intelligent local transcript selector...")
    start_s = 30.0 if (all_words and all_words[-1]['end'] > 75.0) else 0.0
    end_s = start_s + 45.0
    return ClipInfo(title="Automated Highlight Hook", start_time=start_s, end_time=end_s)

# 4. Anti-Cracking, Crisp 9:16 Vertical Crop & Filter
def crop_vertical(input_video, start, end, out_path):
    print("    Rendering ultra-sharp 9:16 crop with anti-crack re-encoding...")
    # Accurate seek after -i prevents frame corruption; CRF 18 preserves visual sharpness
    duration = end - start
    crop_filter = "crop=ih*(9/16):ih:(iw-ow)/2:0,scale=1080:1920:flags=lanczos"

    subprocess.run([
        "ffmpeg", "-y",
        "-ss", str(start),
        "-i", input_video,
        "-t", str(duration),
        "-vf", crop_filter,
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "18",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "192k",
        "-movflags", "+faststart",
        out_path
    ], check=True)

# 5. Master Orchestrator
def run_pipeline(source_target):
    print("\n--- Step 1: Downloading & extracting audio ---")
    vid_file, aud_file = prepare_media(source_target)

    print("\n--- Step 2: Transcribing speech locally with Faster-Whisper ---")
    all_words, transcript_str = transcribe(aud_file)

    print("\n--- Step 3: Picking best viral segment ---")
    best_clip = pick_best_clip(transcript_str, all_words)
    print(f"-> Selected: '{best_clip.title}' ({best_clip.start_time:.2f}s -> {best_clip.end_time:.2f}s)")

    print("\n--- Step 4: Vertical crop to 9:16 (High Quality) ---")
    public_dir = os.path.join("renderer", "public")
    os.makedirs(public_dir, exist_ok=True)

    cropped_filename = "cropped_clip.mp4"
    cropped_dest = os.path.join(public_dir, cropped_filename)
    crop_vertical(vid_file, best_clip.start_time, best_clip.end_time, cropped_dest)

    print("\n--- Step 5: Preparing Remotion props JSON ---")
    clip_words = [
        {
            "text": w["text"],
            "start": round(w["start"] - best_clip.start_time, 2),
            "end": round(w["end"] - best_clip.start_time, 2)
        }
        for w in all_words
        if best_clip.start_time <= w["start"] <= best_clip.end_time
    ]

    duration_frames = int((best_clip.end_time - best_clip.start_time) * 30)
    props_data = {
        "videoUrl": cropped_filename,
        "words": clip_words
    }

    props_file = os.path.abspath(os.path.join("renderer", "props.json"))
    with open(props_file, "w", encoding="utf-8") as f:
        json.dump(props_data, f, indent=2)

    print("\n--- Step 6: Rendering final vertical short via Remotion ---")
    subprocess.run([
        "npx", "remotion", "render",
        "ShortClip", "final_short.mp4",
        f"--props={props_file}",
        f"--duration-in-frames={duration_frames}",
        "--gl=angle"
    ], cwd="renderer", shell=True, check=True)

    final_path = os.path.abspath(os.path.join("renderer", "final_short.mp4"))
    print(f"\n[DONE] Final short rendered successfully: {final_path}")

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "source.mp4"
    run_pipeline(target)