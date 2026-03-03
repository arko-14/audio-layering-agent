from pathlib import Path
from graph.groq_client import groq_chat_json
from utils.json_utils import read_json, write_json

SYSTEM = """You are a subtle SFX designer for social videos.
Place minimal SFX only when it increases engagement.
Avoid overuse. Avoid serious segments unless extremely subtle.
Output only JSON."""

SCHEMA = """
{
  "events":[{"t":12.3,"id":"sfx-id-from-library","gain_db":-14.0}],
  "limits":{"whoosh_min_gap_s":10,"impact_min_gap_s":18},
  "notes":["string"]
}
"""

def sfx_designer_node(state: dict) -> dict:
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