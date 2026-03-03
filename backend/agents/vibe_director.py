from pathlib import Path
from graph.groq_client import groq_chat_json
from utils.json_utils import read_json, write_json
from utils.audio_features import compute_speech_features
import re

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
    Returns (label, confidence, reason)
    """
    # For now we don't have transcript, so use speech patterns
    # In a full system, you'd extract transcript and check cue words
    
    # Default to educational for speech-heavy content
    total_speech = sum(s["e"] - s["s"] for s in speech_segments)
    speech_ratio = total_speech / max(duration, 1e-6)
    
    # If >50% speech, it's likely educational/presentation
    if speech_ratio > 0.5:
        return ("educational", 0.8, "high speech ratio suggests presentation/explainer")
    elif speech_ratio > 0.3:
        return ("educational", 0.6, "moderate speech ratio, likely educational")
    else:
        return (None, 0.0, "low speech, let LLM decide")


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

SCHEMA = """
{
  "segments":[{"s":0.0,"e":10.0,"label":"educational|calm|energetic|serious","energy":0.0}],
  "notes":[ "string" ]
}
"""

def vibe_director_node(state: dict) -> dict:
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