# System Design

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Frontend (React)                         │
│  Upload → Progress → Timeline Viz → Video Player → Explanation  │
└─────────────────────────────────────────────────────────────────┘
                              │ HTTP
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     FastAPI Backend                              │
│  POST /upload → async task → GET /jobs/{id} polling             │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                   LangGraph Workflow                             │
│                                                                  │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐     │
│  │ Analyzer │ → │  Vibe    │ → │  Music   │ → │   SFX    │     │
│  │  (VAD)   │   │ Director │   │Supervisor│   │ Designer │     │
│  └──────────┘   └──────────┘   └──────────┘   └──────────┘     │
│                                      │              │            │
│                                      ▼              ▼            │
│                              ┌──────────┐   ┌──────────┐        │
│                              │ Mixing   │ → │ Renderer │        │
│                              │ Engineer │   │ (FFmpeg) │        │
│                              └──────────┘   └──────────┘        │
│                                                   │              │
│                                                   ▼              │
│                                            ┌──────────┐         │
│                                            │Explainer │         │
│                                            │  (LLM)   │         │
│                                            └──────────┘         │
└─────────────────────────────────────────────────────────────────┘
```

## Decision Log

### 1. LangGraph over LangChain Agents

**Choice:** LangGraph with explicit node functions  
**Reason:** Deterministic DAG execution. Each agent is a pure function with clear inputs/outputs. No unpredictable agent loops.

### 2. Groq LLM

**Choice:** Groq (llama-3.3-70b-versatile)  
**Reason:** Fast inference (~200ms), free tier, JSON mode support. Sufficient for classification tasks.

### 3. WebRTC VAD over ML-based

**Choice:** `webrtcvad` library  
**Reason:** CPU-only, <50ms latency, no model downloads. Production-proven (used in Chrome/Firefox).

### 4. FFmpeg for Audio Processing

**Choice:** FFmpeg filtergraph (sidechaincompress, amix, loudnorm)  
**Reason:** No Python audio processing overhead. Single subprocess call. Handles all mixing in one pass.

### 5. Rule-based Vibe Classification

**Choice:** Rule-based defaults + LLM fallback  
**Reason:** LLMs misclassify "calm explanation" as "serious". Speech ratio >50% → force `educational`. Reduces API calls.

### 6. Random Track Selection (No LLM)

**Choice:** Pure random with vibe-based filtering  
**Reason:** LLM always picked first track. Random selection with `job_id + timestamp` seed ensures variety.

### 7. Sidechain Compression for Ducking

**Choice:** FFmpeg `sidechaincompress` filter  
**Reason:** Real-time voice detection. Music automatically ducks when voice present. No pre-computed segments needed.

### 8. Pre-indexed Media Libraries

**Choice:** `index.json` with pre-computed energy/tags  
**Reason:** No runtime analysis. Instant track lookup. Energy scores enable vibe matching.

## Agent Responsibilities

| Agent | Input | Output | LLM? |
|-------|-------|--------|------|
| Analyzer | Video file | `analysis.json` (VAD, energy curve) | No |
| Vibe Director | Analysis | `vibe.json` (label, energy) | Conditional |
| Music Supervisor | Vibe, Library | `music_plan.json` (track, gain, fades) | No |
| SFX Designer | Analysis, Vibe | `sfx_plan.json` (events, times) | Yes |
| Mixing Engineer | Vibe, Music Plan | `ducking.json` (attack, release, amounts) | No |
| Renderer | All plans | `enhanced.mp4` | No |
| Explainer | All artifacts | `explain.txt`, `report.json` | Yes |

## Gain Staging

```
Voice:  -14 LUFS (loudnorm target)
Music:  -20 to -14 dB base (vibe-dependent)
        -8 dB additional ducking during speech (educational)
        -4 dB additional ducking (energetic)
SFX:    -14 to -10 dB
```

## State Schema

```python
class JobState:
    job_id: str
    input_video_path: str
    job_dir: str
    artifacts: Dict[str, str]  # paths to JSON artifacts
    output_video_path: Optional[str]
    progress_log: List[str]
```

## Error Handling

- Each agent catches exceptions → logs to `progress_log`
- Job status transitions: `queued → running → done | error`
- Frontend polls `/jobs/{id}` until terminal state

## Scalability Notes

**Current:** Single-worker, in-memory job store  
**Production path:**
- Redis for job queue
- Celery workers for parallel processing
- S3 for media storage
- PostgreSQL for job metadata

## Performance

| Stage | Time (30s video) |
|-------|------------------|
| Upload + Extract | ~2s |
| VAD Analysis | ~1s |
| LLM Calls (2x) | ~1s |
| FFmpeg Render | ~5s |
| **Total** | **~10s** |
