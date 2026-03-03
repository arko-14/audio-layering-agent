from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional

class JobState(BaseModel):
    job_id: str
    input_video_path: str
    job_dir: str

    # artifacts paths + structured outputs
    artifacts: Dict[str, Any] = Field(default_factory=dict)

    # outputs
    output_video_path: Optional[str] = None

    # progress
    progress_log: List[str] = Field(default_factory=list)