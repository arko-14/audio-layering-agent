import subprocess
from pathlib import Path

def run(cmd: list[str]) -> None:
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError(f"FFmpeg error:\nCMD: {' '.join(cmd)}\nSTDERR:\n{p.stderr}")

def extract_audio_wav(input_video: str, output_wav: str) -> None:
    Path(output_wav).parent.mkdir(parents=True, exist_ok=True)
    run([
        "ffmpeg", "-y",
        "-i", input_video,
        "-vn",
        "-ac", "1",
        "-ar", "48000",
        output_wav
    ])

def probe_duration_seconds(input_video: str) -> float:
    p = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", input_video],
        capture_output=True, text=True
    )
    if p.returncode != 0:
        raise RuntimeError(p.stderr)
    return float(p.stdout.strip())

def mux_audio_to_video(input_video: str, mixed_audio_wav: str, output_video: str) -> None:
    Path(output_video).parent.mkdir(parents=True, exist_ok=True)
    run([
        "ffmpeg", "-y",
        "-i", input_video,
        "-i", mixed_audio_wav,
        "-c:v", "copy",
        "-map", "0:v:0",
        "-map", "1:a:0",
        "-shortest",
        output_video
    ])