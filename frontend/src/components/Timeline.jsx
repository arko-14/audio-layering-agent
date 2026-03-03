/**
 * Timeline Component
 * ==================
 * 
 * Visual representation of the audio layers in the video.
 * 
 * Displays three tracks:
 * 1. Speech Detection - Green segments where voice was detected (VAD)
 * 2. Background Music - Blue bars showing music placement
 * 3. Sound Effects - Orange markers at SFX timestamps
 * 
 * Features:
 * - Proportional width based on segment duration
 * - Hover tooltips with exact timestamps
 * - Time markers at 0%, 25%, 50%, 75%, 100%
 * - Legend explaining each track color
 * 
 * Polls /api/jobs/{jobId}/timeline every 1.5 seconds until data arrives.
 */
import React, { useEffect, useState } from "react";

// Timeline visualization styles
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
  track: {
    marginBottom: 20,
  },
  trackLabel: {
    display: "flex",
    alignItems: "center",
    gap: 8,
    marginBottom: 8,
  },
  trackName: {
    fontSize: 14,
    fontWeight: 600,
    color: "#24292e",
  },
  trackHint: {
    fontSize: 12,
    color: "#8b949e",
  },
  trackBar: {
    position: "relative",
    height: 28,
    background: "#f6f8fa",
    borderRadius: 8,
    overflow: "hidden",
    border: "1px solid #e1e4e8",
  },
  legend: {
    display: "flex",
    gap: 20,
    marginTop: 16,
    paddingTop: 16,
    borderTop: "1px solid #e1e4e8",
    flexWrap: "wrap",
  },
  legendItem: {
    display: "flex",
    alignItems: "center",
    gap: 6,
    fontSize: 13,
    color: "#586069",
  },
  legendDot: {
    width: 12,
    height: 12,
    borderRadius: 4,
  },
  timeMarkers: {
    display: "flex",
    justifyContent: "space-between",
    marginTop: 4,
    fontSize: 11,
    color: "#8b949e",
    fontFamily: "'Consolas', monospace",
  },
};

const COLORS = {
  speech: "#22c55e",
  music: "#3b82f6",
  sfx: "#f59e0b",
};

export default function Timeline({ jobId }) {
  const [tl, setTl] = useState(null);

  useEffect(() => {
    async function load() {
      try {
        const res = await fetch(`/api/jobs/${jobId}/timeline`);
        if (!res.ok) return;
        const data = await res.json();
        setTl(data);
      } catch {}
    }
    const t = setInterval(load, 1500);
    load();
    return () => clearInterval(t);
  }, [jobId]);

  if (!tl) return null;

  const dur = tl.duration || 1;

  function renderSegment(seg, color) {
    const left = `${(seg.s / dur) * 100}%`;
    const width = `${((seg.e - seg.s) / dur) * 100}%`;
    return (
      <div
        key={`${seg.s}-${seg.e}`}
        style={{
          position: "absolute",
          left,
          width,
          top: 4,
          bottom: 4,
          background: color,
          borderRadius: 4,
          opacity: 0.85,
        }}
        title={`${seg.s.toFixed(2)}s - ${seg.e.toFixed(2)}s`}
      />
    );
  }

  function renderMarker(t, color, label) {
    const left = `${(t / dur) * 100}%`;
    return (
      <div
        key={`marker-${t}`}
        style={{
          position: "absolute",
          left,
          top: 2,
          bottom: 2,
          width: 8,
          background: color,
          borderRadius: 4,
          transform: "translateX(-50%)",
        }}
        title={`${label} @ ${t.toFixed(2)}s`}
      />
    );
  }

  const timeMarkers = [0, dur * 0.25, dur * 0.5, dur * 0.75, dur].map(t => t.toFixed(1) + "s");

  return (
    <div style={styles.card}>
      <div style={styles.cardTitle}>
        <span>📊</span> Audio Timeline Visualization
      </div>

      <div style={styles.track}>
        <div style={styles.trackLabel}>
          <span style={styles.trackName}>🎤 Speech Detection</span>
          <span style={styles.trackHint}>VAD-detected voice segments</span>
        </div>
        <div style={styles.trackBar}>
          {(tl.speech_segments || []).map(s => renderSegment(s, COLORS.speech))}
        </div>
      </div>

      <div style={styles.track}>
        <div style={styles.trackLabel}>
          <span style={styles.trackName}>🎵 Background Music</span>
          <span style={styles.trackHint}>Selected & ducked tracks</span>
        </div>
        <div style={styles.trackBar}>
          {(tl.music_tracks || []).map((m, i) =>
            renderSegment({ s: m.from, e: m.to }, COLORS.music)
          )}
        </div>
      </div>

      <div style={styles.track}>
        <div style={styles.trackLabel}>
          <span style={styles.trackName}>✨ Sound Effects</span>
          <span style={styles.trackHint}>Transition markers</span>
        </div>
        <div style={styles.trackBar}>
          {(tl.sfx_events || []).map((ev, i) =>
            renderMarker(ev.t, COLORS.sfx, ev.id || ev.type || "SFX")
          )}
        </div>
      </div>

      <div style={styles.timeMarkers}>
        {timeMarkers.map((t, i) => <span key={i}>{t}</span>)}
      </div>

      <div style={styles.legend}>
        <div style={styles.legendItem}>
          <div style={{ ...styles.legendDot, background: COLORS.speech }} />
          <span>Voice Activity</span>
        </div>
        <div style={styles.legendItem}>
          <div style={{ ...styles.legendDot, background: COLORS.music }} />
          <span>Background Music</span>
        </div>
        <div style={styles.legendItem}>
          <div style={{ ...styles.legendDot, background: COLORS.sfx }} />
          <span>SFX Events</span>
        </div>
      </div>
    </div>
  );
}