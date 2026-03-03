# Intelligent Audio Layering Agent

Multi-agent system that automatically adds background music, ducking, and SFX to talking-head videos.

## Quick Start

```bash
# Backend
cd backend
python -m venv .venv
.venv\Scripts\activate  # Windows
pip install -r requirements.txt
cp .env.example .env    # Add your GROQ_API_KEY
uvicorn main:app --reload --port 8000

# Frontend (new terminal)
cd frontend
npm install
npm run dev
```

Open http://localhost:5173

## Requirements

- Python 3.10+
- Node.js 18+
- FFmpeg (in PATH)
- Groq API key

## Project Structure

```
backend/
├── main.py                 # FastAPI server
├── agents/                 # LangGraph agent nodes
│   ├── analyzer.py         # VAD + energy extraction
│   ├── vibe_director.py    # Mood classification
│   ├── music_supervisor.py # Track selection
│   ├── sfx_designer.py     # SFX placement
│   ├── mixing_engineer.py  # Ducking config
│   ├── renderer.py         # FFmpeg mixing
│   └── explainer.py        # AI summary
├── graph/
│   ├── workflow.py         # LangGraph DAG
│   ├── state.py            # Shared state schema
│   └── groq_client.py      # LLM client
├── media/
│   ├── music_library/      # BGM tracks + index.json
│   └── sfx_library/        # SFX files + index.json
└── runs/                   # Job outputs (gitignored)

frontend/
├── src/
│   ├── App.jsx
│   └── components/
│       ├── Upload.jsx
│       ├── JobProgress.jsx
│       ├── Timeline.jsx
│       └── PlayerCompare.jsx
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/upload` | Upload video, returns job_id |
| GET | `/api/jobs/{id}` | Job status + progress log |
| GET | `/api/jobs/{id}/result` | Download enhanced video |
| GET | `/api/jobs/{id}/timeline` | Timeline visualization data |
| GET | `/api/jobs/{id}/explain` | AI explanation |

## Pipeline Flow

```
Upload → Analyzer → Vibe Director → Music Supervisor → SFX Designer → Mixing Engineer → Renderer → Explainer
```

## Configuration

### Environment Variables

```env
GROQ_API_KEY=your_key_here
```

### Music Library

Add tracks to `backend/media/music_library/tracks/` and run:
```bash
cd backend
python analyze_tracks.py
```

### SFX Library

Add SFX to `backend/media/sfx_library/sfx/` and run:
```bash
cd backend
python analyze_sfx.py
```

## Output Files

Each job creates in `backend/runs/{job_id}/`:
- `enhanced.mp4` - Final video
- `report.json` - Full decision log
- `explain.txt` - AI explanation
- `timeline.json` - Visualization data
- `analysis.json`, `vibe.json`, `music_plan.json`, `sfx_plan.json`, `ducking.json`

## License

MIT