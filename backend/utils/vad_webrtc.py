"""
Voice Activity Detection (VAD) using WebRTC
===========================================

Detects speech segments in audio using Google's WebRTC VAD algorithm.
This is a key preprocessing step that informs:
    - Where to duck background music
    - Where to avoid placing SFX
    - How to classify video content

WebRTC VAD operates on fixed-size frames (10/20/30ms) and outputs
a binary speech/non-speech decision per frame. We post-process to:
    1. Merge nearby speech frames into segments
    2. Filter out very short blips (noise)
    3. Invert to find silence/gap segments

Requirements:
    - webrtcvad package: pip install webrtcvad
    - Input must be 16-bit mono PCM at 8/16/32/48 kHz
"""
from typing import List, Dict
import webrtcvad
import soundfile as sf
import numpy as np


def _to_int16_pcm(x: np.ndarray) -> np.ndarray:
    """
    Convert float audio [-1, 1] to 16-bit PCM format.
    
    WebRTC VAD requires 16-bit signed integer samples.
    """
    x = np.clip(x, -1.0, 1.0)  # Clamp to prevent overflow
    return (x * 32767.0).astype(np.int16)


def _frame_generator(pcm16: np.ndarray, sr: int, frame_ms: int):
    """
    Generate fixed-size frames for VAD processing.
    
    Args:
        pcm16: Audio as 16-bit PCM array
        sr: Sample rate in Hz
        frame_ms: Frame duration (must be 10, 20, or 30 ms)
    
    Yields:
        Fixed-size numpy arrays of samples
    """
    frame_len = int(sr * frame_ms / 1000)
    n = len(pcm16)
    i = 0
    while i + frame_len <= n:
        yield pcm16[i:i+frame_len]
        i += frame_len


def speech_segments_webrtc(
    wav_path: str,
    aggressiveness: int = 2,
    frame_ms: int = 30,
    merge_gap_s: float = 0.35,
    min_len_s: float = 0.2,
) -> List[Dict]:
    """
    Detect speech segments in audio using WebRTC VAD.
    
    Args:
        wav_path: Path to mono WAV file at 48kHz
        aggressiveness: VAD sensitivity 0-3 (higher = stricter, filters more non-speech)
        frame_ms: Frame size in ms (10, 20, or 30)
        merge_gap_s: Merge segments with gaps smaller than this
        min_len_s: Discard segments shorter than this (noise filter)
    
    Returns:
        List of {"s": start_sec, "e": end_sec} dicts
    """
    x, sr = sf.read(wav_path)
    if x.ndim > 1:
        x = x.mean(axis=1)

    pcm16 = _to_int16_pcm(x.astype(np.float32))
    vad = webrtcvad.Vad(int(aggressiveness))

    speech_flags = []
    times = []  # start time per frame
    frame_len = int(sr * frame_ms / 1000)

    t = 0.0
    for frame in _frame_generator(pcm16, sr, frame_ms):
        is_speech = vad.is_speech(frame.tobytes(), sr)
        speech_flags.append(is_speech)
        times.append(t)
        t += frame_ms / 1000.0

    # Convert speech_flags -> segments
    segs = []
    in_speech = False
    start_t = 0.0

    for i, flag in enumerate(speech_flags):
        if flag and not in_speech:
            in_speech = True
            start_t = times[i]
        elif not flag and in_speech:
            in_speech = False
            end_t = times[i]
            segs.append({"s": start_t, "e": end_t})

    if in_speech:
        segs.append({"s": start_t, "e": times[-1] + frame_ms/1000.0})

    # Merge close segments
    segs = sorted(segs, key=lambda z: z["s"])
    merged = []
    for seg in segs:
        if not merged:
            merged.append(seg)
            continue
        prev = merged[-1]
        if seg["s"] - prev["e"] <= merge_gap_s:
            prev["e"] = max(prev["e"], seg["e"])
        else:
            merged.append(seg)

    # Drop very short blips
    merged = [s for s in merged if (s["e"] - s["s"]) >= min_len_s]
    return merged

def invert_to_silence(speech: List[Dict], duration: float) -> List[Dict]:
    silence = []
    t = 0.0
    for seg in speech:
        if seg["s"] > t:
            silence.append({"s": t, "e": seg["s"]})
        t = seg["e"]
    if t < duration:
        silence.append({"s": t, "e": duration})
    return silence