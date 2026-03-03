import os
import uuid
import json
import shutil
import asyncio
from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File, HTTPException

load_dotenv()
from fastapi.responses import FileResponse, JSONResponse
from graph.workflow import build_workflow
from graph.state import JobState

BASE_DIR = Path(__file__).resolve().parent
RUNS_DIR = BASE_DIR / "runs"
RUNS_DIR.mkdir(exist_ok=True)

app = FastAPI(title="Intelligent Audio Layering System")

# In-memory job tracker for MVP demo
JOBS: dict[str, dict] = {}

workflow = build_workflow()

def _job_dir(job_id: str) -> Path:
    d = RUNS_DIR / job_id
    d.mkdir(parents=True, exist_ok=True)
    return d

@app.post("/api/upload")
async def upload_video(file: UploadFile = File(...)):
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
    job = JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job

@app.get("/api/jobs/{job_id}/timeline")
async def job_timeline(job_id: str):
    job_dir = _job_dir(job_id)
    timeline_path = job_dir / "timeline.json"
    if not timeline_path.exists():
        raise HTTPException(status_code=404, detail="Timeline not ready")
    return JSONResponse(json.loads(timeline_path.read_text(encoding="utf-8")))

@app.get("/api/jobs/{job_id}/explain")
async def job_explain(job_id: str):
    job_dir = _job_dir(job_id)
    explain_path = job_dir / "explain.txt"
    if not explain_path.exists():
        raise HTTPException(status_code=404, detail="Explanation not ready")
    return {"text": explain_path.read_text(encoding="utf-8")}

@app.get("/api/jobs/{job_id}/result")
async def job_result(job_id: str):
    job = JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if not job["result"]:
        raise HTTPException(status_code=404, detail="Result not ready")
    return FileResponse(job["result"], media_type="video/mp4", filename="enhanced.mp4")

async def run_job(job_id: str, input_path: str):
    job = JOBS[job_id]
    job["status"] = "running"

    def log(msg: str):
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