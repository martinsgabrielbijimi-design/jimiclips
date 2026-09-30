import sys
import os
import subprocess
from faster_whisper import WhisperModel
import yt_dlp

def log(msg):
    print(f"[JimiClips] {msg}", flush=True)

def find_cookie_file():
    """Look for cookies.txt in multiple common working paths."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(base_dir, "cookies.txt"),
        os.path.join(os.getcwd(), "cookies.txt"),
        "cookies.txt"
    ]
    for path in candidates:
        if os.path.exists(path) and os.path.getsize(path) > 0:
            return path
    return None

def download_video(url, output_filename="source.mp4"):
    log("Initializing download pipeline...")
    
    cookie_file = find_cookie_file()
    
    ydl_opts = {
        # Select best available pre-merged stream or separate streams up to 1080p
        'format': 'bestvideo[height<=1080]+bestaudio/best[height<=1080]/best',
        'outtmpl': output_filename,
        'merge_output_format': 'mp4',
        'overwrites': True,
        'quiet': False,
        'no_warnings': True,
        'geo_bypass': True,
        # Allow yt-dlp to manage matching client headers natively (avoids CDN 403)
        'extractor_args': {
            'youtube': {
                'player_client': ['android_creator', 'android', 'web'],
            }
        },
        # Mitigate cloud IP throttling
        'socket_timeout': 30,
        'retries': 5,
        'fragment_retries': 5,
    }
    
    if cookie_file:
        log(f"Authenticated session loaded from: {cookie_file}")
        ydl_opts['cookiefile'] = cookie_file
    else:
        log("No cookies.txt detected. Running unauthenticated request.")

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
    except yt_dlp.utils.DownloadError as err:
        log(f"Download failed: {err}")
        raise RuntimeError(
            "YouTube blocked the datacenter IP (HTTP 403). "
            "To resolve: provide a fresh cookies.txt or upload the video directly via the Upload tab."
        ) from err
        
    if not os.path.exists(output_filename) or os.path.getsize(output_filename) == 0:
        raise RuntimeError("Output file is empty after download completed.")
        
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
    
    # Clean previous run temporary files
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
