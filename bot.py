import sys
import os
import subprocess
from faster_whisper import WhisperModel
import yt_dlp

def log(msg):
    print(f"[JimiClips] {msg}", flush=True)

def download_video(url, output_filename="source.mp4"):
    log("Fetching video stream via direct HTTPS stream (HLS disabled)...")
    
    # Locate cookies.txt in the same directory as this script
    base_dir = os.path.dirname(os.path.abspath(__file__))
    cookie_path = os.path.join(base_dir, "cookies.txt")
    
    ydl_opts = {
        # Strictly forbid HLS/m3u8 streams that return empty fragments on cloud IPs
        'format': (
            'bv*[protocol^=http][height<=1080]+ba[protocol^=http]/'
            'b[protocol^=http][height<=1080]/'
            'bv*[height<=1080]+ba/'
            'b[height<=1080]/best'
        ),
        'outtmpl': output_filename,
        'merge_output_format': 'mp4',
        'overwrites': True,
        'quiet': False,
        'no_warnings': True,
        'geo_bypass': True,
        # Ban HLS manifests; use android and web direct streams
        'extractor_args': {
            'youtube': {
                'player_client': ['android', 'web'],
                'player_skip': ['hls'],
            }
        },
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
            'Accept': '*/*',
            'Accept-Encoding': 'gzip, deflate, br',
        }
    }
    
    # Attach cookies if found
    if os.path.exists(cookie_path) and os.path.getsize(cookie_path) > 0:
        log(f"Found cookies file at: {cookie_path}")
        ydl_opts['cookiefile'] = cookie_path
    else:
        log("No valid cookies.txt detected. Attempting unauthenticated direct stream.")
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
        
    if not os.path.exists(output_filename) or os.path.getsize(output_filename) == 0:
        raise RuntimeError("Downloaded file is empty. Check cookies or use the direct upload tab.")
        
    log("Source download complete.")
    return output_filename

def extract_audio(video_file="source.mp4", audio_file="extracted.wav"):
    log("Extracting audio stream for transcription...")
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
    log("Loading Faster-Whisper model (tiny.en)...")
    model = WhisperModel("tiny.en", device="cpu", compute_type="int8")
    log("Transcribing audio...")
    segments, info = model.transcribe(audio_file, beam_size=5)
    
    transcript = []
    for s in segments:
        transcript.append({"start": s.start, "end": s.end, "text": s.text})
    
    log(f"Transcription complete: {len(transcript)} segments processed.")
    return transcript

def process_vertical_clip(input_video="source.mp4", output_clip="final_clip.mp4", start_sec=0, duration_sec=30):
    log("Rendering 1080x1920 vertical video (Lanczos scaling + CRF 18)...")
    
    # 9:16 Center crop + Lanczos scaling + visually lossless CRF 18
    vf_filter = (
        "crop=ih*(9/16):ih,scale=1080:1920:flags=lanczos,"
        "setsar=1"
    )
    
    cmd = [
        "ffmpeg", "-y",
        "-ss", str(start_sec),
        "-i", input_video,
        "-t", str(duration_sec),
        "-vf", vf_filter,
        "-c:v", "libx264",
        "-crf", "18",
        "-preset", "fast",
        "-c:a", "aac",
        "-b:a", "192k",
        output_clip
    ]
    
    subprocess.run(cmd, check=True)
    log(f"Render complete: {output_clip}")

def main():
    if len(sys.argv) < 2:
        print("Usage: python bot.py <url_or_filepath>")
        sys.exit(1)

    target = sys.argv[1]
    
    # Clean up artifacts from prior executions
    for old_file in ["source.mp4", "extracted.wav", "final_clip.mp4"]:
        if os.path.exists(old_file) and target != old_file:
            try:
                os.remove(old_file)
            except Exception:
                pass

    if target.startswith("http://") or target.startswith("https://"):
        video_path = download_video(target, "source.mp4")
    else:
        video_path = target

    audio_path = extract_audio(video_path, "extracted.wav")
    transcribe_audio(audio_path)
    process_vertical_clip(
        input_video=video_path,
        output_clip="final_clip.mp4",
        start_sec=0,
        duration_sec=30
    )
    
    log("All tasks finished successfully.")

if __name__ == "__main__":
    main()
