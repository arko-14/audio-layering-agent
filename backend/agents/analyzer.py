"""
Media Analyzer Agent
====================

First agent in the pipeline. Responsible for:
1. Extracting audio from the input video (mono WAV @ 48kHz)
2. Running Voice Activity Detection (VAD) to find speech segments
3. Computing RMS energy curve for loudness analysis
4. Identifying silence gaps (potential music/SFX placement points)

Outputs:
    analysis.json with:
    - duration: Video length in seconds
    - speech_segments: [{s: start, e: end}, ...]
    - silence_segments: [{s: start, e: end}, ...]
    - energy_curve: [{t: time, rms: value}, ...]
    - cut_points: (placeholder for future scene detection)
"""
from pathlib import Path
from utils.ffmpeg_utils import extract_audio_wav, probe_duration_seconds
from utils.audio_features import rms_energy_curve
from utils.vad_webrtc import speech_segments_webrtc, invert_to_silence
from utils.json_utils import write_json


def analyzer_node(state: dict) -> dict:
    """
    Analyze input video to extract audio features for downstream agents.
    
    Pipeline Stage: 1 of 7
    Input: state.input_video_path
    Output: state.artifacts['analysis_json']
    """
    job_dir = Path(state["job_dir"])
    inp = state["input_video_path"]

    # Step 1: Extract audio track as mono WAV
    state["progress_log"].append("Media Analyzer: extracting audio")
    wav_path = job_dir / "audio.wav"
    extract_audio_wav(inp, str(wav_path))

    # Get video duration for downstream calculations
    duration = probe_duration_seconds(inp)

    # Step 2: Run WebRTC VAD to detect speech segments
    # These segments inform where to duck music and avoid placing SFX
    state["progress_log"].append("Media Analyzer: running VAD (WebRTC)")
    speech = speech_segments_webrtc(
        str(wav_path),
        aggressiveness=2,   # 0-3: higher = stricter speech detection
        frame_ms=30,        # Analysis frame size
        merge_gap_s=0.35,   # Merge segments within this gap
        min_len_s=0.2       # Ignore blips shorter than this
    )
    
    # Invert speech to get silence segments (good for music prominence)
    silence = invert_to_silence(speech, duration)

    # Step 3: Compute energy curve for loudness visualization
    state["progress_log"].append("Media Analyzer: computing energy curve")
    energy = rms_energy_curve(str(wav_path), hop_s=0.5)

    # Package analysis results
    analysis = {
        "duration": duration,
        "speech_segments": speech,      # Where voice is detected
        "silence_segments": silence,    # Gaps between speech
        "energy_curve": energy,         # Loudness over time
        "cut_points": []                # Placeholder for scene detection
    }

    # Save to job directory
    analysis_path = job_dir / "analysis.json"
    write_json(str(analysis_path), analysis)

    state["artifacts"]["analysis_json"] = str(analysis_path)
    return state