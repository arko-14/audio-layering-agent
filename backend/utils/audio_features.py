"""
Audio Feature Extraction Utilities
==================================

Functions for analyzing audio characteristics to help classify video mood
and inform mixing decisions.

Features Computed:
    - RMS Energy Curve: Loudness over time for visualization
    - Speech Rate: Estimated words per second
    - Pitch Variability: How expressive/monotone the speaker is
    - Content Type Hints: Heuristic classification of content

These features are used by the Vibe Director to make better mood
classifications without needing full speech-to-text transcription.
"""
import numpy as np
import soundfile as sf
from typing import List, Dict


def rms_energy_curve(wav_path: str, hop_s: float = 0.5) -> List[Dict]:
    """
    Compute RMS (Root Mean Square) energy curve for audio visualization.
    
    Args:
        wav_path: Path to WAV file
        hop_s: Time step between measurements in seconds
    
    Returns:
        List of {t: timestamp, rms: energy_value} dicts
    
    RMS represents perceived loudness - higher values = louder audio.
    Used for the energy curve visualization in the timeline UI.
    """
    x, sr = sf.read(wav_path)
    # Convert stereo to mono if needed
    if x.ndim > 1:
        x = x.mean(axis=1)

    hop = int(hop_s * sr)  # Hop size in samples
    win = hop              # Window size = hop size (no overlap)
    out = []
    
    for i in range(0, len(x), hop):
        chunk = x[i:i+win]
        if len(chunk) == 0:
            break
        # RMS = sqrt(mean(x^2)), add small epsilon to avoid log(0) issues
        rms = float(np.sqrt(np.mean(chunk.astype(np.float32) ** 2)) + 1e-9)
        t = float(i / sr)
        out.append({"t": t, "rms": rms})
    return out


def compute_speech_features(wav_path: str, speech_segments: List[Dict]) -> Dict:
    """
    Compute audio features to help LLM classify mood better.
    
    Args:
        wav_path: Path to extracted audio WAV
        speech_segments: List of {s: start, e: end} speech segments
    
    Returns:
        Dict with:
        - speech_rate_wps: Estimated words per second
        - pitch_variability: "low" | "medium" | "high"
        - rms_db: Average loudness in dB
        - likely_type: Hint about content type
    """
    try:
        x, sr = sf.read(wav_path)
        if x.ndim > 1:
            x = x.mean(axis=1)
        x = x.astype(np.float32)
        
        duration = len(x) / sr
        
        # Estimate speech rate from segment density
        # More segments with short gaps = faster speech
        total_speech_time = sum(s["e"] - s["s"] for s in speech_segments)
        num_segments = len(speech_segments)
        
        # Rough estimate: ~2.5 words per second of speech is normal
        # More segments = more pauses = slower perceived rate
        if total_speech_time > 0:
            # Estimate based on segment count and gaps
            avg_segment_len = total_speech_time / max(num_segments, 1)
            # Shorter segments with more pauses = slower, methodical speech
            if avg_segment_len < 1.5:
                speech_rate = 2.0  # Slower, more pauses
            elif avg_segment_len < 3.0:
                speech_rate = 2.5  # Normal
            else:
                speech_rate = 3.0  # Continuous, faster
        else:
            speech_rate = 2.5
        
        # Compute zero-crossing rate variance as proxy for pitch variability
        chunk_size = int(sr * 0.5)  # 500ms chunks
        zcr_values = []
        for i in range(0, len(x) - chunk_size, chunk_size):
            chunk = x[i:i+chunk_size]
            zero_crossings = np.sum(np.abs(np.diff(np.sign(chunk)))) / 2
            zcr = zero_crossings / len(chunk)
            zcr_values.append(zcr)
        
        if zcr_values:
            zcr_std = np.std(zcr_values)
            if zcr_std < 0.01:
                pitch_var = "low"  # Monotone
            elif zcr_std < 0.03:
                pitch_var = "medium"
            else:
                pitch_var = "high"  # Expressive
        else:
            pitch_var = "medium"
        
        # RMS in dB
        rms = np.sqrt(np.mean(x ** 2))
        rms_db = 20 * np.log10(rms + 1e-9)
        
        # Determine likely content type
        speech_ratio = total_speech_time / max(duration, 1e-6)
        if speech_ratio > 0.6 and pitch_var in ["low", "medium"]:
            likely_type = "voiceover/explanation (educational content likely)"
        elif speech_ratio > 0.6 and pitch_var == "high":
            likely_type = "energetic speech/presentation"
        elif speech_ratio < 0.3:
            likely_type = "ambient/music-focused content"
        else:
            likely_type = "mixed content with speech"
        
        return {
            "speech_rate_wps": round(speech_rate, 1),
            "pitch_variability": pitch_var,
            "rms_db": round(float(rms_db), 1),
            "likely_type": likely_type
        }
        
    except Exception as e:
        return {
            "speech_rate_wps": 2.5,
            "pitch_variability": "medium",
            "rms_db": -20.0,
            "likely_type": "unknown (analysis failed)"
        }