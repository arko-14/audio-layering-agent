import React, { useState } from "react";
import Upload from "./components/Upload.jsx";
import JobProgress from "./components/JobProgress.jsx";
import Timeline from "./components/Timeline.jsx";
import PlayerCompare from "./components/PlayerCompare.jsx";

const styles = {
  container: {
    fontFamily: "'Segoe UI', system-ui, sans-serif",
    maxWidth: 1100,
    margin: "0 auto",
    padding: "24px 20px",
    background: "#fafbfc",
    minHeight: "100vh",
  },
  header: {
    textAlign: "center",
    marginBottom: 32,
    paddingBottom: 20,
    borderBottom: "2px solid #e1e4e8",
  },
  title: {
    fontSize: 28,
    fontWeight: 700,
    color: "#1a1a2e",
    margin: 0,
  },
  subtitle: {
    fontSize: 14,
    color: "#586069",
    marginTop: 8,
  },
  badge: {
    display: "inline-block",
    background: "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
    color: "#fff",
    padding: "4px 12px",
    borderRadius: 20,
    fontSize: 12,
    fontWeight: 600,
    marginTop: 12,
  },
  grid: {
    display: "grid",
    gap: 20,
  },
};

export default function App() {
  const [jobId, setJobId] = useState(null);

  return (
    <div style={styles.container}>
      <header style={styles.header}>
        <h1 style={styles.title}>🎬 Intelligent Audio Layering System</h1>
        <p style={styles.subtitle}>
          Multi-Agent Pipeline: Analyzer → Vibe Director → Music Supervisor → SFX Designer → Mixer → Renderer
        </p>
        <span style={styles.badge}>Powered by LangGraph + Groq LLM</span>
      </header>

      <div style={styles.grid}>
        <Upload onJobCreated={setJobId} />

        {jobId && (
          <>
            <JobProgress jobId={jobId} />
            <Timeline jobId={jobId} />
            <PlayerCompare jobId={jobId} />
          </>
        )}
      </div>
    </div>
  );
}