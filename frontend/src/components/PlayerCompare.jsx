/**
 * PlayerCompare Component
 * =======================
 * 
 * Video player with enhanced/original toggle (A/B comparison).
 * 
 * Features:
 * - Tab switcher between "Enhanced Output" and "Original Input"
 * - HTML5 video player with native controls
 * - Streams enhanced video from /api/jobs/{jobId}/result
 * - Footer explaining what enhancements were applied
 * 
 * Note: Original video preview is placeholder in MVP.
 * Full implementation would serve the original input for comparison.
 */
import React, { useState } from "react";

// Player card styles
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
    marginBottom: 20,
    display: "flex",
    alignItems: "center",
    gap: 8,
  },
  tabs: {
    display: "flex",
    gap: 8,
    marginBottom: 20,
  },
  tab: {
    padding: "10px 20px",
    borderRadius: 8,
    border: "2px solid #e1e4e8",
    background: "#fff",
    cursor: "pointer",
    fontWeight: 600,
    fontSize: 14,
    transition: "all 0.2s ease",
    color: "#586069",
  },
  activeTab: {
    borderColor: "#667eea",
    background: "#f0f4ff",
    color: "#667eea",
  },
  videoContainer: {
    background: "#000",
    borderRadius: 10,
    overflow: "hidden",
    display: "flex",
    justifyContent: "center",
    alignItems: "center",
    minHeight: 400,
  },
  video: {
    maxWidth: "100%",
    maxHeight: 500,
  },
  placeholder: {
    color: "#8b949e",
    textAlign: "center",
    padding: 40,
  },
  footer: {
    marginTop: 16,
    padding: 12,
    background: "#f6f8fa",
    borderRadius: 8,
    fontSize: 13,
    color: "#586069",
    display: "flex",
    alignItems: "center",
    gap: 8,
  },
};

export default function PlayerCompare({ jobId }) {
  const [mode, setMode] = useState("enhanced");

  return (
    <div style={styles.card}>
      <div style={styles.cardTitle}>
        <span>🎬</span> Video Preview
      </div>

      <div style={styles.tabs}>
        <button
          style={{ ...styles.tab, ...(mode === "enhanced" ? styles.activeTab : {}) }}
          onClick={() => setMode("enhanced")}
        >
          ✨ Enhanced Output
        </button>
        <button
          style={{ ...styles.tab, ...(mode === "original" ? styles.activeTab : {}) }}
          onClick={() => setMode("original")}
        >
          📹 Original Input
        </button>
      </div>

      <div style={styles.videoContainer}>
        {mode === "enhanced" ? (
          <video
            controls
            style={styles.video}
            src={`/api/jobs/${jobId}/result`}
            type="video/mp4"
          />
        ) : (
          <div style={styles.placeholder}>
            <div style={{ fontSize: 48, marginBottom: 12 }}>📹</div>
            <p>Original video preview not available in MVP</p>
            <p style={{ fontSize: 12, marginTop: 8 }}>
              (Feature: Store & serve original input for A/B comparison)
            </p>
          </div>
        )}
      </div>

      <div style={styles.footer}>
        <span>💡</span>
        <span>
          The enhanced video includes: auto-selected background music, sidechain ducking during speech,
          and strategically placed transition SFX.
        </span>
      </div>
    </div>
  );
}