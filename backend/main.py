"""
Intelligent Audio Layering System - FastAPI Backend
===================================================

This is the main entry point for the audio layering API. It provides:
- Video upload endpoint that triggers the processing pipeline
- Job status polling for real-time progress updates
- Artifact retrieval (timeline, explanation, result video)

The pipeline uses LangGraph to orchestrate multiple AI agents:
1. Media Analyzer   - Extracts audio, detects speech/silence segments
2. Vibe Director    - Classifies video mood (educational, calm, energetic, serious)
3. Music Supervisor - Selects background music based on vibe
4. SFX Designer     - Places subtle sound effects at transitions
5. Mixing Engineer  - Configures ducking/compression settings
6. Renderer         - Mixes all audio layers and muxes to video
7. Explainer        - Generates human-readable decision summary

"""

import os
import uuid
import json
import shutil
import asyncio
from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File, HTTPException

load_dotenv()  # Load GROQ_API_KEY and other env vars from .env
from fastapi.responses import FileResponse, JSONResponse
from graph.workflow import build_workflow
from graph.state import JobState

# Directory setup
BASE_DIR = Path(__file__).resolve().parent
RUNS_DIR = BASE_DIR / "runs"  # Each job gets a unique folder under runs/
RUNS_DIR.mkdir(exist_ok=True)

app = FastAPI(title="Intelligent Audio Layering System")

# In-memory job tracker (MVP - not persisted across restarts)
# Structure: { job_id: { status, progress, artifacts, result, error, input_filename } }
JOBS: dict[str, dict] = {}

# Build the LangGraph workflow once at startup
workflow = build_workflow()


def _job_dir(job_id: str) -> Path:
    """Get or create the job-specific directory for storing artifacts."""
    d = RUNS_DIR / job_id
    d.mkdir(parents=True, exist_ok=True)
    return d


# ===========================
# API ENDPOINTS
# ===========================

@app.post("/api/upload")
async def upload_video(file: UploadFile = File(...)):
    """
    Upload a video file and start the audio layering pipeline.
    
    Accepts: MP4, MOV, MKV, WebM files
    Returns: { job_id: str } - Use this ID to poll for status
    
    The pipeline runs asynchronously - poll /api/jobs/{job_id} for progress.
    """
    if not file.filename.lower().endswith((".mp4", ".mov", ".mkv", ".webm")):
        raise HTTPException(status_code=400, detail="Upload a video file (mp4/mov/mkv/webm).")

    job_id = str(uuid.uuid4())
    job_dir = _job_dir(job_id)
    in_path = job_dir / "input" / file.filename
    in_path.parent.mkdir(parents=True, exist_ok=True)

    with open(in_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    JOBS[job_id] = {
        "status": "queued",
        "progress": [],
        "artifacts": {},
        "result": None,
        "error": None,
        "input_filename": file.filename,
    }

    asyncio.create_task(run_job(job_id, str(in_path)))
    return {"job_id": job_id}

@app.get("/api/jobs/{job_id}")
async def job_status(job_id: str):
    """
    Get the current status and progress of a job.
    
    Returns:
        - status: "queued" | "running" | "done" | "error"
        - progress: List of agent activity messages
        - artifacts: Paths to generated JSON files
        - result: Path to enhanced video (when done)
        - error: Error message (if failed)
    """
    job = JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@app.get("/api/jobs/{job_id}/timeline")
async def job_timeline(job_id: str):
    """Get the audio timeline visualization data (speech, music, SFX segments)."""
    job_dir = _job_dir(job_id)
    timeline_path = job_dir / "timeline.json"
    if not timeline_path.exists():
        raise HTTPException(status_code=404, detail="Timeline not ready")
    return JSONResponse(json.loads(timeline_path.read_text(encoding="utf-8")))

@app.get("/api/jobs/{job_id}/explain")
async def job_explain(job_id: str):
    """Get the AI-generated explanation of audio decisions."""
    job_dir = _job_dir(job_id)
    explain_path = job_dir / "explain.txt"
    if not explain_path.exists():
        raise HTTPException(status_code=404, detail="Explanation not ready")
    return {"text": explain_path.read_text(encoding="utf-8")}


@app.get("/api/jobs/{job_id}/result")
async def job_result(job_id: str):
    """Download the enhanced video with layered audio."""
    job = JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if not job["result"]:
        raise HTTPException(status_code=404, detail="Result not ready")
    return FileResponse(job["result"], media_type="video/mp4", filename="enhanced.mp4")


# ===========================
# BACKGROUND JOB RUNNER
# ===========================

async def run_job(job_id: str, input_path: str):
    """
    Execute the full audio layering pipeline for a job.
    
    This runs asynchronously and updates the JOBS dict in-place.
    The LangGraph workflow handles the sequential agent execution.
    """
    job = JOBS[job_id]
    job["status"] = "running"

    def log(msg: str):
        """Append a progress message to the job log."""
        job["progress"].append(msg)

    job_dir = _job_dir(job_id)
    state = JobState(
        job_id=job_id,
        input_video_path=input_path,
        job_dir=str(job_dir),
        progress_log=[],
    )

    try:
        log("Orchestrator: starting workflow")
        # run LangGraph (sync invoke inside async task)
        result_state = workflow.invoke(state.model_dump())

        # Save final pointers
        out_path = Path(result_state["output_video_path"])
        job["result"] = str(out_path)
        job["status"] = "done"
        job["progress"] = result_state.get("progress_log", job["progress"])
        job["artifacts"] = result_state.get("artifacts", {})
        log("Orchestrator: done")

    except Exception as e:
        job["status"] = "error"
        job["error"] = str(e)
        log(f"ERROR: {e}")