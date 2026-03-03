"""
Vibe Director Agent
===================

Classifies the overall mood/tone of the video to guide music and SFX selection.
Uses a hybrid approach: rule-based detection first, then LLM fallback.

Supported Vibe Labels:
    - educational: Teaching, tutorials, explanations (DEFAULT for speech-heavy)
    - calm: Meditation, relaxation, ASMR, nature content
    - energetic: Hype, excitement, celebrations, fast-paced content
    - serious: Warnings, alerts, negative news, urgent content

The agent is biased toward 'educational' because most speech-heavy videos
are tutorials, explainers, or presentations. This prevents the LLM from
over-classifying calm videos as 'calm' (which would use wrong music).

Outputs:
    vibe.json with:
    - segments: [{s, e, label, energy}, ...] - Vibe timeline
    - notes: Reasoning for classification
"""
from pathlib import Path
from graph.groq_client import groq_chat_json
from utils.json_utils import read_json, write_json
from utils.audio_features import compute_speech_features
import re

# =======================
# CUE WORD PATTERNS
# =======================
# These regex patterns detect content type from speech patterns
# (In a full system, you'd extract transcript and check these)

# Teaching/presentation cue words - forces educational
TEACHING_CUES = [
    r"today we",
    r"let's understand",
    r"in this video",
    r"let me explain",
    r"let me show",
    r"i'm going to",
    r"we're going to",
    r"step by step",
    r"first[,.]* second",
    r"how to",
    r"what is",
    r"why is",
    r"this is called",
    r"for example",
    r"basically",
    r"essentially",
    r"the reason",
    r"notice how",
    r"as you can see",
    r"welcome to",
    r"hi everyone",
    r"hey guys",
    r"hello and welcome",
]

# Energetic/hype cue words - only these override educational to energetic
ENERGETIC_CUES = [
    r"let's go",
    r"let's goo+",
    r"awesome",
    r"insane",
    r"amazing",
    r"incredible",
    r"game changer",
    r"mind blown",
    r"crazy",
    r"unbelievable",
    r"you won't believe",
    r"smash that",
    r"drop a like",
]

# Serious/urgent cue words
SERIOUS_CUES = [
    r"warning",
    r"critical",
    r"urgent",
    r"important alert",
    r"danger",
    r"risk",
    r"emergency",
    r"breaking news",
    r"must know",
    r"immediately",
]


def detect_vibe_from_cues(speech_segments: list, duration: float) -> tuple:
    """
    Rule-based vibe detection from speech patterns.
    
    Uses speech ratio (speech time / total time) as a heuristic:
    - >50% speech = likely educational/presentation
    - 30-50% speech = probably educational
    - <30% speech = let LLM decide (could be music-focused content)
    
    Args:
        speech_segments: List of {s: start, e: end} dicts
        duration: Total video duration in seconds
    
    Returns:
        (label, confidence, reason) tuple
    """
    # Calculate speech ratio
    total_speech = sum(s["e"] - s["s"] for s in speech_segments)
    speech_ratio = total_speech / max(duration, 1e-6)
    
    # High speech = educational content (tutorials, explanations)
    if speech_ratio > 0.5:
        return ("educational", 0.8, "high speech ratio suggests presentation/explainer")
    elif speech_ratio > 0.3:
        return ("educational", 0.6, "moderate speech ratio, likely educational")
    else:
        return (None, 0.0, "low speech, let LLM decide")


# LLM system prompt - guides classification behavior
SYSTEM = """You are a senior audio/video editor classifying video mood for background music.

LABEL DEFINITIONS (follow strictly):
- educational: Teaching, explaining, demonstrating, tutorials, how-to content, informational voiceovers. THIS IS THE DEFAULT for any calm/normal speech.
- calm: ONLY for meditation, relaxation, nature sounds, ASMR, explicitly soothing content.
- energetic: ONLY for hype, excited, fast-paced, celebrations with words like "awesome", "insane", "let's go".
- serious: ONLY for warnings, alerts, negative news with words like "warning", "critical", "urgent".

CRITICAL RULE:
- If someone is speaking normally/calmly explaining anything = educational (99% of videos)
- educational is the DEFAULT. Only use other labels if there are STRONG cues.

Output only JSON."""

# Expected JSON response schema
SCHEMA = """
{
  "segments":[{"s":0.0,"e":10.0,"label":"educational|calm|energetic|serious","energy":0.0}],
  "notes":[ "string" ]
}
"""


def vibe_director_node(state: dict) -> dict:
    """
    Classify video mood/vibe to guide music and SFX selection.
    
    Pipeline Stage: 2 of 7
    Input: state.artifacts['analysis_json']
    Output: state.artifacts['vibe_json']
    
    Strategy:
    1. Rule-based check first (speech ratio heuristic)
    2. If confident (>70%), skip LLM and save cost
    3. Otherwise, call Groq LLM with audio features
    4. Post-process to override bad LLM classifications
    """
    job_dir = Path(state["job_dir"])
    analysis = read_json(state["artifacts"]["analysis_json"])
    wav_path = str(job_dir / "audio.wav")
    duration = analysis["duration"]

    # === RULE-BASED PRE-CHECK ===
    rule_label, rule_confidence, rule_reason = detect_vibe_from_cues(
        analysis["speech_segments"], duration
    )
    
    state["progress_log"].append(f"Vibe Director: rule check -> {rule_label} ({rule_confidence:.0%}) - {rule_reason}")
    
    # If high confidence from rules, skip LLM entirely
    if rule_confidence >= 0.7:
        vibe = {
            "segments": [{"s": 0.0, "e": duration, "label": rule_label, "energy": 0.5}],
            "notes": [f"Rule-based: {rule_reason}"]
        }
        state["progress_log"].append(f"Vibe Director: using rule-based label '{rule_label}' (skipped LLM)")
    else:
        # Compute audio features for LLM
        audio_features = compute_speech_features(wav_path, analysis["speech_segments"])
        
        speech_ratio = sum(s["e"]-s["s"] for s in analysis["speech_segments"]) / max(duration, 1e-6)
        energy_vals = [p["rms"] for p in analysis["energy_curve"]]
        e_mean = float(sum(energy_vals)/max(len(energy_vals),1))
        
        import math
        rms_db = 20 * math.log10(e_mean + 1e-9)

        user = f"""
Video duration: {duration:.2f}s
Speech ratio: {speech_ratio:.2f}
Loudness: {rms_db:.1f} dB
Speech rate: {audio_features['speech_rate_wps']:.1f} words/sec
Pitch variability: {audio_features['pitch_variability']}
Content hint: {audio_features['likely_type']}

REMINDER: Default to 'educational' for normal speech. Only use other labels if VERY clear cues.
Create exactly 1 segment for the full duration.
"""

        state["progress_log"].append("Vibe Director (Groq): inferring tone/vibe")
        vibe = groq_chat_json(system=SYSTEM, user=user, schema_hint=SCHEMA)

        # === POST-LLM OVERRIDE ===
        # Force educational if LLM picked calm/serious but speech ratio is high
        if vibe.get("segments"):
            llm_label = vibe["segments"][0].get("label", "educational")
            if llm_label in ["calm", "serious"] and speech_ratio > 0.4:
                state["progress_log"].append(f"Vibe Director: overriding '{llm_label}' -> 'educational' (high speech ratio)")
                vibe["segments"][0]["label"] = "educational"
                vibe["notes"] = vibe.get("notes", []) + [f"Override: {llm_label} -> educational"]

    # Fallback
    if not vibe.get("segments"):
        vibe = {"segments": [{"s": 0.0, "e": duration, "label": "educational", "energy": 0.5}], "notes": ["fallback"]}

    vibe_path = job_dir / "vibe.json"
    write_json(str(vibe_path), vibe)
    state["artifacts"]["vibe_json"] = str(vibe_path)
    return state