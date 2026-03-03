"""
Music Supervisor Agent
======================

Selects background music based on the detected vibe. Uses random selection
from vibe-matched tracks to ensure variety across different videos.

Key Responsibilities:
1. Filter music library by vibe (educational, calm, energetic, serious)
2. Randomly select a track (seeded by job_id for reproducibility in testing)
3. Set appropriate gain levels (quieter for voice-heavy content)
4. Configure fade in/out for smooth transitions

Gain Strategy:
    - Educational: -20 to -16 dB (very quiet, voice is priority)
    - Calm: -18 to -14 dB (quiet but atmospheric)
    - Serious: -22 to -18 dB (minimal, voice is critical)
    - Energetic: -14 to -10 dB (music can be more present)

Outputs:
    music_plan.json with:
    - tracks: [{id, from, to, gain_db, crossfade_s}, ...]
    - global_fade_in_s, global_fade_out_s
    - notes: Selection reasoning
"""
import random
import hashlib
import time
from pathlib import Path
from utils.json_utils import read_json, write_json

# Gain settings by vibe (in dB) - LOWER = quieter music, clearer voice
# Each tuple is (min_gain, max_gain) - actual value randomized within range
GAIN_BY_VIBE = {
    "educational": (-20, -16),  # Very quiet, voice is king
    "calm": (-18, -14),         # Quiet but present
    "serious": (-22, -18),      # Super quiet, serious = voice dominant
    "energetic": (-14, -10),    # Louder music for energy
}


def music_supervisor_node(state: dict) -> dict:
    """
    Select and configure background music for the video.
    
    Pipeline Stage: 3 of 7
    Input: state.artifacts['analysis_json'], state.artifacts['vibe_json']
    Output: state.artifacts['music_plan_json']
    
    Uses pure random selection (no LLM) because:
    1. Faster execution, no API call needed
    2. More variety - different videos get different tracks
    3. Vibe filtering ensures appropriate mood match
    """
    job_dir = Path(state["job_dir"])
    job_id = state.get("job_id", str(time.time()))
    analysis = read_json(state["artifacts"]["analysis_json"])
    vibe = read_json(state["artifacts"]["vibe_json"])
    duration = analysis["duration"]

    # Load music library
    lib_path = Path(__file__).resolve().parents[1] / "media" / "music_library" / "index.json"
    library = read_json(str(lib_path))
    tracks = library.get("tracks", [])
    
    if not tracks:
        raise RuntimeError("No tracks in music library!")

    # Get vibe label
    primary_vibe = "educational"  # Default
    if vibe.get("segments") and len(vibe["segments"]) > 0:
        primary_vibe = vibe["segments"][0].get("label", "educational")
    
    state["progress_log"].append(f"Music Supervisor: vibe = {primary_vibe}")

    # === FILTER TRACKS BY VIBE ===
    def matches_vibe(track):
        tags = track.get("tags", [])
        energy = track.get("energy", 0.5)
        
        if primary_vibe == "educational":
            # Prefer calm/ambient with low-mid energy
            return ("calm" in tags or "ambient" in tags or "educational" in tags) and energy < 0.65
        elif primary_vibe == "calm":
            return ("calm" in tags or "ambient" in tags) and energy < 0.5
        elif primary_vibe == "energetic":
            return ("energetic" in tags or "upbeat" in tags) and energy > 0.5
        elif primary_vibe == "serious":
            return ("serious" in tags or "dramatic" in tags or "calm" in tags)
        return True  # Fallback: any track
    
    matching_tracks = [t for t in tracks if matches_vibe(t)]
    
    # If no matches, use all tracks
    if not matching_tracks:
        matching_tracks = tracks
        state["progress_log"].append("Music Supervisor: no vibe-matched tracks, using all")
    
    # === TRUE RANDOM SELECTION ===
    # Seed with job_id + timestamp for uniqueness per run
    seed_str = f"{job_id}_{time.time_ns()}"
    seed = int(hashlib.sha256(seed_str.encode()).hexdigest(), 16) % (2**32)
    rng = random.Random(seed)
    
    # Pick a random track
    selected_track = rng.choice(matching_tracks)
    track_id = selected_track["id"]
    
    state["progress_log"].append(f"Music Supervisor: selected '{track_id}' (from {len(matching_tracks)} candidates)")
    
    # === GAIN STAGING ===
    gain_range = GAIN_BY_VIBE.get(primary_vibe, (-18, -14))
    gain_db = rng.uniform(gain_range[0], gain_range[1])
    
    # Fade settings
    fade_in = min(1.5, duration * 0.1)
    fade_out = min(2.0, duration * 0.15)
    
    plan = {
        "tracks": [{
            "id": track_id,
            "from": 0.0,
            "to": duration,
            "gain_db": round(gain_db, 1),
            "crossfade_s": 0.0
        }],
        "global_fade_in_s": round(fade_in, 1),
        "global_fade_out_s": round(fade_out, 1),
        "notes": [
            f"Vibe: {primary_vibe}",
            f"Track: {track_id}",
            f"Gain: {gain_db:.1f} dB (range: {gain_range})"
        ]
    }
    
    plan_path = job_dir / "music_plan.json"
    write_json(str(plan_path), plan)
    state["artifacts"]["music_plan_json"] = str(plan_path)
    return state