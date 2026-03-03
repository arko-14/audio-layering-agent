/**
 * Upload Component
 * ================
 * 
 * Drag-and-drop video upload interface.
 * 
 * Features:
 * - Drag & drop support with visual feedback
 * - Click-to-browse file picker
 * - Loading state while uploading
 * - Shows pipeline stages for user awareness
 * 
 * Supported formats: MP4, MOV, MKV, WebM
 * 
 * On successful upload, calls onJobCreated(job_id) to trigger
 * the parent to start polling for job status.
 */
import React, { useState, useRef } from "react";

// Inline styles - kept in component for MVP simplicity
const styles = {
  card: {
    background: "#fff",
    borderRadius: 12,
    padding: 24,
    boxShadow: "0 2px 8px rgba(0,0,0,0.08)",
    border: "1px solid #e1e4e8",
  },
  cardTitle: {
    fontSize: 16,
    fontWeight: 600,
    color: "#1a1a2e",
    marginBottom: 16,
    display: "flex",
    alignItems: "center",
    gap: 8,
  },
  dropzone: {
    border: "2px dashed #d0d7de",
    borderRadius: 10,
    padding: "40px 20px",
    textAlign: "center",
    cursor: "pointer",
    transition: "all 0.2s ease",
    background: "#fafbfc",
  },
  dropzoneHover: {
    borderColor: "#667eea",
    background: "#f0f4ff",
  },
  dropzoneIcon: {
    fontSize: 48,
    marginBottom: 12,
  },
  dropzoneText: {
    fontSize: 15,
    color: "#586069",
    marginBottom: 8,
  },
  dropzoneHint: {
    fontSize: 13,
    color: "#8b949e",
  },
  loading: {
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    gap: 12,
    padding: 20,
    color: "#667eea",
    fontWeight: 500,
  },
  spinner: {
    width: 20,
    height: 20,
    border: "3px solid #e1e4e8",
    borderTopColor: "#667eea",
    borderRadius: "50%",
    animation: "spin 1s linear infinite",
  },
  pipeline: {
    marginTop: 20,
    padding: 16,
    background: "#f6f8fa",
    borderRadius: 8,
    fontSize: 13,
    color: "#586069",
  },
  pipelineTitle: {
    fontWeight: 600,
    color: "#1a1a2e",
    marginBottom: 8,
  },
  pipelineSteps: {
    display: "flex",
    flexWrap: "wrap",
    gap: 8,
  },
  step: {
    background: "#fff",
    padding: "4px 10px",
    borderRadius: 6,
    border: "1px solid #e1e4e8",
    fontSize: 12,
  },
};

export default function Upload({ onJobCreated }) {
  const [loading, setLoading] = useState(false);
  const [hover, setHover] = useState(false);
  const inputRef = useRef();

  async function handleUpload(e) {
    const file = e.target.files?.[0];
    if (!file) return;

    setLoading(true);
    const fd = new FormData();
    fd.append("file", file);

    try {
      const res = await fetch("/api/upload", { method: "POST", body: fd });
      const data = await res.json();
      onJobCreated(data.job_id);
    } catch (err) {
      alert("Upload failed: " + err.message);
    }
    setLoading(false);
  }

  return (
    <div style={styles.card}>
      <div style={styles.cardTitle}>
        <span>📤</span> Upload Video
      </div>

      {loading ? (
        <div style={styles.loading}>
          <div style={styles.spinner} />
          Processing upload...
        </div>
      ) : (
        <div
          style={{ ...styles.dropzone, ...(hover ? styles.dropzoneHover : {}) }}
          onDragOver={(e) => { e.preventDefault(); setHover(true); }}
          onDragLeave={() => setHover(false)}
          onDrop={(e) => {
            e.preventDefault();
            setHover(false);
            const file = e.dataTransfer.files[0];
            if (file) {
              const dt = new DataTransfer();
              dt.items.add(file);
              inputRef.current.files = dt.files;
              handleUpload({ target: { files: dt.files } });
            }
          }}
          onClick={() => inputRef.current?.click()}
        >
          <div style={styles.dropzoneIcon}>🎥</div>
          <div style={styles.dropzoneText}>
            Drag & drop your video here, or click to browse
          </div>
          <div style={styles.dropzoneHint}>
            Supports MP4, MOV, MKV, WebM
          </div>
          <input
            ref={inputRef}
            type="file"
            accept="video/*"
            onChange={handleUpload}
            style={{ display: "none" }}
          />
        </div>
      )}

      <div style={styles.pipeline}>
        <div style={styles.pipelineTitle}>🤖 Agent Pipeline</div>
        <div style={styles.pipelineSteps}>
          <span style={styles.step}>1. Media Analyzer</span>
          <span style={styles.step}>2. Vibe Director</span>
          <span style={styles.step}>3. Music Supervisor</span>
          <span style={styles.step}>4. SFX Designer</span>
          <span style={styles.step}>5. Mixing Engineer</span>
          <span style={styles.step}>6. Renderer</span>
          <span style={styles.step}>7. Explainer</span>
        </div>
      </div>

      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}