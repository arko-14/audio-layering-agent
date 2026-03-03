import React, { useEffect, useState } from "react";

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
  statusBar: {
    display: "flex",
    alignItems: "center",
    gap: 12,
    padding: "12px 16px",
    borderRadius: 8,
    marginBottom: 16,
  },
  statusRunning: {
    background: "#fff8e6",
    border: "1px solid #ffc107",
  },
  statusDone: {
    background: "#e6f9ed",
    border: "1px solid #28a745",
  },
  statusError: {
    background: "#ffeef0",
    border: "1px solid #dc3545",
  },
  statusDot: {
    width: 10,
    height: 10,
    borderRadius: "50%",
  },
  statusText: {
    fontWeight: 600,
    textTransform: "capitalize",
  },
  logSection: {
    marginTop: 16,
  },
  logTitle: {
    fontSize: 14,
    fontWeight: 600,
    color: "#586069",
    marginBottom: 8,
  },
  logList: {
    background: "#1a1a2e",
    borderRadius: 8,
    padding: 16,
    maxHeight: 200,
    overflow: "auto",
    fontFamily: "'Consolas', 'Monaco', monospace",
    fontSize: 13,
  },
  logItem: {
    color: "#98c379",
    marginBottom: 4,
    display: "flex",
    gap: 8,
  },
  logPrefix: {
    color: "#61afef",
  },
  explainSection: {
    marginTop: 20,
    padding: 20,
    background: "linear-gradient(135deg, #f6f8fa 0%, #e9ecef 100%)",
    borderRadius: 10,
    border: "1px solid #e1e4e8",
  },
  explainTitle: {
    fontSize: 15,
    fontWeight: 600,
    color: "#1a1a2e",
    marginBottom: 12,
    display: "flex",
    alignItems: "center",
    gap: 8,
  },
  explainText: {
    fontSize: 14,
    color: "#24292e",
    lineHeight: 1.7,
    whiteSpace: "pre-wrap",
  },
  actions: {
    marginTop: 20,
    display: "flex",
    gap: 12,
    flexWrap: "wrap",
  },
  button: {
    padding: "10px 20px",
    borderRadius: 8,
    border: "none",
    fontWeight: 600,
    cursor: "pointer",
    fontSize: 14,
    transition: "all 0.2s ease",
    textDecoration: "none",
    display: "inline-flex",
    alignItems: "center",
    gap: 8,
  },
  primaryButton: {
    background: "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
    color: "#fff",
  },
  secondaryButton: {
    background: "#fff",
    color: "#667eea",
    border: "2px solid #667eea",
  },
  errorMsg: {
    color: "#dc3545",
    marginTop: 8,
    fontSize: 14,
  },
};

export default function JobProgress({ jobId }) {
  const [job, setJob] = useState(null);
  const [explain, setExplain] = useState(null);

  useEffect(() => {
    let t = null;
    async function poll() {
      try {
        const res = await fetch(`/api/jobs/${jobId}`);
        const data = await res.json();
        setJob(data);

        if (data.status === "done") {
          // Fetch explanation once done
          try {
            const expRes = await fetch(`/api/jobs/${jobId}/explain`);
            const expData = await expRes.json();
            setExplain(expData.text);
          } catch {}
        }

        if (data.status !== "done" && data.status !== "error") {
          t = setTimeout(poll, 1200);
        }
      } catch {
        t = setTimeout(poll, 2000);
      }
    }
    poll();
    return () => t && clearTimeout(t);
  }, [jobId]);

  if (!job) return null;

  const statusStyle = job.status === "done" ? styles.statusDone 
    : job.status === "error" ? styles.statusError 
    : styles.statusRunning;
  
  const dotColor = job.status === "done" ? "#28a745" 
    : job.status === "error" ? "#dc3545" 
    : "#ffc107";

  return (
    <div style={styles.card}>
      <div style={styles.cardTitle}>
        <span>⚙️</span> Processing Status
      </div>

      <div style={{ ...styles.statusBar, ...statusStyle }}>
        <div style={{ ...styles.statusDot, background: dotColor }} />
        <span style={styles.statusText}>{job.status}</span>
        {job.status === "running" && <span style={{ color: "#856404" }}>— agents are working...</span>}
      </div>

      {job.error && <div style={styles.errorMsg}>❌ Error: {job.error}</div>}

      <div style={styles.logSection}>
        <div style={styles.logTitle}>Agent Activity Log</div>
        <div style={styles.logList}>
          {(job.progress || []).map((p, idx) => (
            <div key={idx} style={styles.logItem}>
              <span style={styles.logPrefix}>▸</span>
              <span>{p}</span>
            </div>
          ))}
        </div>
      </div>

      {explain && (
        <div style={styles.explainSection}>
          <div style={styles.explainTitle}>
            <span>💡</span> AI Explanation — Why These Decisions?
          </div>
          <div style={styles.explainText}>{explain}</div>
        </div>
      )}

      {job.status === "done" && (
        <div style={styles.actions}>
          <a
            href={`/api/jobs/${jobId}/result`}
            download="enhanced.mp4"
            style={{ ...styles.button, ...styles.primaryButton }}
          >
            ⬇️ Download Enhanced Video
          </a>
        </div>
      )}
    </div>
  );
}