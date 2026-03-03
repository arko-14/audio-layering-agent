"""
Job State Schema for Audio Layering Pipeline
=============================================

Defines the Pydantic model that represents the shared state passed between
all agents in the LangGraph workflow. Each agent reads from and writes to
this state to coordinate the pipeline.

Key State Fields:
    - job_id: Unique identifier for tracking
    - input_video_path: Source video to process
    - job_dir: Working directory for all artifacts
    - artifacts: Dict mapping artifact names to file paths
    - output_video_path: Final enhanced video path (set by renderer)
    - progress_log: List of status messages for UI display
"""
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional


class JobState(BaseModel):
    """Shared state object that flows through the LangGraph pipeline."""
    
    # === Job Identification ===
    job_id: str  # UUID for this processing job
    input_video_path: str  # Absolute path to uploaded video
    job_dir: str  # Directory for storing all job artifacts (runs/<job_id>/)

    # === Artifact Storage ===
    # Maps artifact names to their file paths, e.g.:
    #   analysis_json: path to analysis.json
    #   vibe_json: path to vibe.json
    #   music_plan_json: path to music_plan.json
    #   sfx_plan_json: path to sfx_plan.json
    #   ducking_json: path to ducking.json
    #   timeline_json: path to timeline.json
    artifacts: Dict[str, Any] = Field(default_factory=dict)

    # === Output ===
    output_video_path: Optional[str] = None  # Set by renderer agent

    # === Progress Tracking ===
    # List of status messages displayed in UI ("Agent: doing X...")
    progress_log: List[str] = Field(default_factory=list)