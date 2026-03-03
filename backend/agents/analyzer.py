from pathlib import Path
from utils.ffmpeg_utils import extract_audio_wav, probe_duration_seconds
from utils.audio_features import rms_energy_curve
from utils.vad_webrtc import speech_segments_webrtc, invert_to_silence
from utils.json_utils import write_json

def analyzer_node(state: dict) -> dict:
    job_dir = Path(state["job_dir"])
    inp = state["input_video_path"]

    state["progress_log"].append("Media Analyzer: extracting audio")
    wav_path = job_dir / "audio.wav"
    extract_audio_wav(inp, str(wav_path))

    duration = probe_duration_seconds(inp)

    state["progress_log"].append("Media Analyzer: running VAD (WebRTC)")
    speech = speech_segments_webrtc(
        str(wav_path),
        aggressiveness=2,   # 0..3 (higher = more strict)
        frame_ms=30,
        merge_gap_s=0.35,
        min_len_s=0.2
    )
    silence = invert_to_silence(speech, duration)

    state["progress_log"].append("Media Analyzer: computing energy curve")
    energy = rms_energy_curve(str(wav_path), hop_s=0.5)

    analysis = {
        "duration": duration,
        "speech_segments": speech,
        "silence_segments": silence,
        "energy_curve": energy,
        "cut_points": []
    }

    analysis_path = job_dir / "analysis.json"
    write_json(str(analysis_path), analysis)

    state["artifacts"]["analysis_json"] = str(analysis_path)
    return state