from pathlib import Path
from utils.json_utils import read_json, write_json

def mixing_engineer_node(state: dict) -> dict:
    job_dir = Path(state["job_dir"])
    vibe = read_json(state["artifacts"]["vibe_json"])
    music_plan = read_json(state["artifacts"]["music_plan_json"])
    
    # Get primary vibe
    primary_vibe = "educational"
    if vibe.get("segments") and len(vibe["segments"]) > 0:
        primary_vibe = vibe["segments"][0].get("label", "educational")
    
    # Get music gain from plan (already set by music supervisor)
    music_gain = -18  # Default
    if music_plan.get("tracks") and len(music_plan["tracks"]) > 0:
        music_gain = music_plan["tracks"][0].get("gain_db", -18)

    # === DUCKING SETTINGS ===
    # These control how much music is reduced DURING speech
    # The base music level is set by music_supervisor (gain_db)
    # Ducking FURTHER reduces music when voice is detected
    
    # Ducking amounts (additional reduction during speech)
    duck_amount_by_vibe = {
        "educational": -8,   # Duck extra 8dB during speech (clear voice)
        "calm": -6,          # Moderate extra ducking
        "serious": -10,      # Heavy ducking for serious
        "energetic": -4,     # Light ducking, music stays present
    }
    
    duck_amount = duck_amount_by_vibe.get(primary_vibe, -8)

    ducking = {
        # Sidechain compressor settings
        "threshold": 0.015,          # Voice detection threshold (lower = more sensitive)
        "ratio": 10,                 # Compression ratio when voice detected
        "attack_ms": 50,             # Quick attack to catch speech start
        "release_ms": 400,           # Moderate release for natural feel
        "makeup_gain": 1.0,          # No makeup gain
        
        # Target levels
        "voice_target_lufs": -14,    # Voice loudness target
        "music_base_db": music_gain,  # Base music level (from music supervisor)
        "music_speech_db": music_gain + duck_amount,  # Music level during speech
        "music_gap_db": music_gain + 3,  # Music level in gaps (slightly louder)
        
        # Per-vibe settings
        "duck_amount_db": duck_amount,
        "vibe": primary_vibe,
        
        "notes": [
            f"Vibe: {primary_vibe}",
            f"Music base level: {music_gain} dB",
            f"Music during speech: {music_gain + duck_amount} dB (ducked {duck_amount} dB)",
            f"Music in gaps: {music_gain + 3} dB",
            "Using sidechain compression for natural ducking"
        ]
    }

    duck_path = job_dir / "ducking.json"
    write_json(str(duck_path), ducking)
    state["artifacts"]["ducking_json"] = str(duck_path)

    state["progress_log"].append(f"Mixing Engineer: ducking set ({duck_amount} dB during speech)")
    return state