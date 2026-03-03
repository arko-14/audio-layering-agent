"""
FFmpeg Utility Functions
========================

Wrapper functions for common FFmpeg/FFprobe operations used throughout
the audio layering pipeline.

Requirements:
    - FFmpeg and FFprobe must be installed and in system PATH
    - Typically included with: `winget install FFmpeg` or `apt install ffmpeg`

Functions:
    - extract_audio_wav: Extract audio track from video as mono WAV
    - probe_duration_seconds: Get video/audio duration
    - mux_audio_to_video: Replace video's audio with new audio file
    - run: Low-level subprocess wrapper with error handling
"""
import subprocess
from pathlib import Path


def run(cmd: list[str]) -> None:
    """
    Execute an FFmpeg command and raise on failure.
    
    Args:
        cmd: Command as list of strings, e.g. ['ffmpeg', '-i', 'in.mp4', ...]
    
    Raises:
        RuntimeError: If FFmpeg returns non-zero exit code
    """
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError(f"FFmpeg error:\nCMD: {' '.join(cmd)}\nSTDERR:\n{p.stderr}")


def extract_audio_wav(input_video: str, output_wav: str) -> None:
    """
    Extract audio from video as mono WAV at 48kHz.
    
    Args:
        input_video: Path to source video file
        output_wav: Path for output WAV file
    
    The output is forced to mono (-ac 1) at 48000 Hz (-ar 48000)
    for consistency across the pipeline and WebRTC VAD compatibility.
    """
    Path(output_wav).parent.mkdir(parents=True, exist_ok=True)
    run([
        "ffmpeg", "-y",        # Overwrite output
        "-i", input_video,      # Input file
        "-vn",                  # No video (audio only)
        "-ac", "1",             # Mono
        "-ar", "48000",         # 48kHz sample rate
        output_wav
    ])


def probe_duration_seconds(input_video: str) -> float:
    """
    Get the duration of a video/audio file in seconds.
    
    Args:
        input_video: Path to media file
    
    Returns:
        Duration in seconds as float
    
    Uses FFprobe to extract duration from container metadata.
    """
    p = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", input_video],
        capture_output=True, text=True
    )
    if p.returncode != 0:
        raise RuntimeError(p.stderr)
    return float(p.stdout.strip())


def mux_audio_to_video(input_video: str, mixed_audio_wav: str, output_video: str) -> None:
    """
    Replace a video's audio track with a new audio file.
    
    Args:
        input_video: Original video (video track is preserved)
        mixed_audio_wav: New audio to use
        output_video: Output path for remuxed video
    
    Uses stream copy (-c:v copy) for video to avoid re-encoding.
    The -shortest flag ensures output duration matches the shorter input.
    """
    Path(output_video).parent.mkdir(parents=True, exist_ok=True)
    run([
        "ffmpeg", "-y",
        "-i", input_video,       # Video source
        "-i", mixed_audio_wav,   # Audio source
        "-c:v", "copy",          # Copy video codec (no re-encode)
        "-map", "0:v:0",         # Take video from first input
        "-map", "1:a:0",         # Take audio from second input
        "-shortest",             # Match shortest stream duration
        output_video
    ])