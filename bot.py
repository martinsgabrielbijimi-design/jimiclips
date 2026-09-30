import sys
import os
import subprocess
import numpy as np
from faster_whisper import WhisperModel

def log(msg):
    print(f"[JimiClips Studio] {msg}", flush=True)

def extract_audio(video_file="uploaded_source.mp4", audio_file="extracted.wav"):
    log("Extracting lossless 16kHz PCM audio stream for transcription...")
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

def transcribe_audio(audio_file="extracted.wav"):
    log("Spinning up Faster-Whisper (tiny.en engine)...")
    model = WhisperModel("tiny.en", device="cpu", compute_type="int8")
    
    log("Scanning speech timestamps across video...")
    
    # Read the raw 16kHz PCM audio with numpy to bypass PyAV/metadata_errors bug
    try:
        with open(audio_file, "rb") as f:
            f.seek(44)  # Skip 44-byte WAV header
            raw_data = f.read()
        audio_np = np.frombuffer(raw_data, dtype=np.int16).astype(np.float32) / 32768.0
        segments, _ = model.transcribe(audio_np, beam_size=5)
    except Exception as e:
        log(f"Falling back to direct file reader ({e})...")
        segments, _ = model.transcribe(audio_file, beam_size=5)
    
    transcript = []
    for s in segments:
        transcript.append({"start": s.start, "end": s.end, "text": s.text})
    
    log(f"Speech analysis complete: {len(transcript)} dialogue fragments mapped.")
    return transcript

def process_vertical_clip(input_video="uploaded_source.mp4", output_clip="final_clip.mp4", start_sec=0, duration_sec=130, crf="17"):
    log(f"Starting master render: 1080x1920 9:16 ({duration_sec}s duration, CRF {crf}, Lanczos filter, 320k Audio)...")
    
    # 9:16 Center crop + Lanczos scaling + SAR 1:1
    vf_filter = (
        "crop=ih*(9/16):ih,"
        "scale=1080:1920:flags=lanczos,"
        "setsar=1"
    )
    
    cmd = [
        "ffmpeg", "-y",
        "-ss", str(start_sec),
        "-i", input_video,
        "-t", str(duration_sec),
        "-vf", vf_filter,
        "-c:v", "libx264",
        "-profile:v", "high",
        "-level:v", "4.2",
        "-crf", str(crf),
        "-preset", "medium",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "320k",
        output_clip
    ]
    
    subprocess.run(cmd, check=True)
    log(f"Master render complete: {output_clip}")

def main():
    # Arguments: <input_path> <start_sec> <duration_sec> <crf>
    input_file = sys.argv[1] if len(sys.argv) > 1 else "uploaded_source.mp4"
    start_sec = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    duration_sec = int(sys.argv[3]) if len(sys.argv) > 3 else 130
    crf = sys.argv[4] if len(sys.argv) > 4 else "17"

    output_clip = "final_clip.mp4"
    audio_path = "extracted.wav"

    for old in [audio_path, output_clip]:
        if os.path.exists(old):
            try:
                os.remove(old)
            except Exception:
                pass

    extract_audio(input_file, audio_path)
    transcribe_audio(audio_path)
    process_vertical_clip(
        input_video=input_file,
        output_clip=output_clip,
        start_sec=start_sec,
        duration_sec=duration_sec,
        crf=crf
    )
    
    log("All tasks finished successfully. Returning video to dashboard.")

if __name__ == "__main__":
    main()
