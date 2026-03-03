from pathlib import Path
from datetime import datetime
from graph.groq_client import groq_chat_json
from utils.json_utils import read_json, write_json

SYSTEM = """You are a helpful assistant explaining editorial audio decisions.
Keep it short and concrete. Mention vibe, music choice, ducking behavior, and SFX restraint.
Format as bullet points starting with •"""

SCHEMA = """{ "text": "string" }"""

def explainer_node(state: dict) -> dict:
    job_dir = Path(state["job_dir"])
    job_id = state.get("job_id", "unknown")
    
    analysis = read_json(state["artifacts"]["analysis_json"])
    vibe = read_json(state["artifacts"]["vibe_json"])
    music = read_json(state["artifacts"]["music_plan_json"])
    sfx = read_json(state["artifacts"]["sfx_plan_json"])
    ducking = read_json(state["artifacts"]["ducking_json"])

    # Get key details for explanation
    duration = analysis["duration"]
    speech_count = len(analysis["speech_segments"])
    vibe_label = vibe["segments"][0]["label"] if vibe.get("segments") else "educational"
    track_id = music["tracks"][0]["id"] if music.get("tracks") else "none"
    track_gain = music["tracks"][0].get("gain_db", -18) if music.get("tracks") else -18
    sfx_count = len(sfx.get("events", []))
    duck_amount = ducking.get("duck_amount_db", -8)

    user = f"""
Video Analysis:
- Duration: {duration:.1f}s
- Speech segments: {speech_count}
- Detected vibe: {vibe_label}

Audio Decisions:
- Music track: {track_id}
- Music level: {track_gain} dB
- Ducking during speech: {duck_amount} dB extra reduction
- SFX events: {sfx_count}

Write a concise explanation (4-6 bullet points) explaining WHY these choices were made.
Focus on: vibe classification reason, music selection logic, ducking approach, and SFX restraint.
"""

    state["progress_log"].append("Explainer (Groq): generating 'why this edit' summary")
    out = groq_chat_json(system=SYSTEM, user=user, schema_hint=SCHEMA)
    explanation_text = out.get("text", "No explanation generated.")

    # === SAVE PLAIN TEXT EXPLANATION ===
    explain_path = job_dir / "explain.txt"
    explain_path.write_text(explanation_text, encoding="utf-8")
    state["artifacts"]["explain_txt"] = str(explain_path)

    # === SAVE DETAILED JSON REPORT ===
    report = {
        "job_id": job_id,
        "timestamp": datetime.now().isoformat(),
        "input_video": state.get("input_video_path", ""),
        "duration_seconds": round(duration, 2),
        
        "analysis": {
            "speech_segments": speech_count,
            "speech_ratio": round(sum(s["e"]-s["s"] for s in analysis["speech_segments"]) / max(duration, 1), 2),
            "silence_segments": len(analysis["silence_segments"]),
        },
        
        "vibe": {
            "label": vibe_label,
            "notes": vibe.get("notes", []),
        },
        
        "music": {
            "track_id": track_id,
            "gain_db": track_gain,
            "fade_in_s": music.get("global_fade_in_s", 1.0),
            "fade_out_s": music.get("global_fade_out_s", 1.5),
            "notes": music.get("notes", []),
        },
        
        "ducking": {
            "duck_amount_db": duck_amount,
            "attack_ms": ducking.get("attack_ms", 50),
            "release_ms": ducking.get("release_ms", 400),
            "music_base_db": ducking.get("music_base_db", track_gain),
            "music_during_speech_db": ducking.get("music_speech_db", track_gain + duck_amount),
        },
        
        "sfx": {
            "event_count": sfx_count,
            "events": sfx.get("events", []),
            "notes": sfx.get("notes", []),
        },
        
        "explanation": explanation_text,
        
        "output_video": str(job_dir / "enhanced.mp4"),
    }
    
    report_path = job_dir / "report.json"
    write_json(str(report_path), report)
    state["artifacts"]["report_json"] = str(report_path)
    
    state["progress_log"].append(f"Explainer: saved report to {report_path.name}")
    return state