"""
SFX Designer Agent
==================

Places subtle sound effects at strategic moments (transitions, silence gaps).
Uses Groq LLM to decide WHERE and WHICH SFX to place based on context.

Design Philosophy:
    - Less is more: Max 3 SFX for videos under 90 seconds
    - Avoid overuse: Minimum gaps between similar SFX types
    - Context-aware: Serious content = no SFX (distraction)
    - Transition-focused: SFX mark scene changes, not random moments

SFX Types (from library):
    - whoosh: Smooth transitions, topic changes
    - impact: Emphasis on key points
    - notification: Alerts, important info

Outputs:
    sfx_plan.json with:
    - events: [{t: timestamp, id: sfx_id, gain_db}, ...]
    - limits: Minimum gaps between SFX types
    - notes: Placement reasoning
"""
from pathlib import Path
from graph.groq_client import groq_chat_json
from utils.json_utils import read_json, write_json

# LLM system prompt for subtle SFX placement
SYSTEM = """You are a subtle SFX designer for social videos.
Place minimal SFX only when it increases engagement.
Avoid overuse. Avoid serious segments unless extremely subtle.
Output only JSON."""

# Expected JSON response schema
SCHEMA = """
{
  "events":[{"t":12.3,"id":"sfx-id-from-library","gain_db":-14.0}],
  "limits":{"whoosh_min_gap_s":10,"impact_min_gap_s":18},
  "notes":["string"]
}
"""


def sfx_designer_node(state: dict) -> dict:
    """
    Plan subtle sound effect placements using LLM.
    
    Pipeline Stage: 4 of 7
    Input: state.artifacts['analysis_json'], state.artifacts['vibe_json']
    Output: state.artifacts['sfx_plan_json']
    
    Strategy:
    1. Find silence->speech boundaries as transition candidates
    2. Send candidates + SFX library to LLM
    3. LLM decides which transitions deserve SFX emphasis
    """
    job_dir = Path(state["job_dir"])
    analysis = read_json(state["artifacts"]["analysis_json"])
    vibe = read_json(state["artifacts"]["vibe_json"])

    # Use speech->silence boundaries as "transition candidates" for MVP
    candidates = []
    for seg in analysis["silence_segments"]:
        dur = seg["e"] - seg["s"]
        if dur >= 0.9:
            candidates.append(round(seg["s"], 2))  # entering a long pause is a good moment

    # Load local sfx library
    lib_path = Path(__file__).resolve().parents[1] / "media" / "sfx_library" / "index.json"
    sfx_lib = read_json(str(lib_path))
    
    # Build summary of available SFX for LLM
    sfx_summary = [{"id": s["id"], "tags": s["tags"], "impact": s.get("impact", 0.5)} for s in sfx_lib["sfx"]]

    user = f"""
Duration: {analysis["duration"]:.2f}s
Vibe segments: {vibe["segments"]}
Candidate transition times (limit yourself): {candidates[:12]}
SFX library available: {sfx_summary}

Rules:
- Max 3 total SFX for < 90s video.
- Use whoosh only on meaningful transitions.
- Add 0 SFX if the content is serious overall.
- Use the exact 'id' from the library in your response.
"""

    state["progress_log"].append("SFX Designer (Groq): planning subtle SFX")
    plan = groq_chat_json(system=SYSTEM, user=user, schema_hint=SCHEMA)

    sfx_path = job_dir / "sfx_plan.json"
    write_json(str(sfx_path), plan)
    state["artifacts"]["sfx_plan_json"] = str(sfx_path)
    return state