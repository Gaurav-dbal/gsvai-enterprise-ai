import React from "react";

export function StatusIndicator({ status, latency }) {
  const isConnected = status === "connected";

  return (
    <div
      className={`status-pill ${isConnected ? "connected" : "disconnected"}`}
      title={`Backend Status: ${isConnected ? "Connected (http://127.0.0.1:8000/health)" : "Disconnected"}`}
    >
      <span className={`status-dot ${isConnected ? "connected" : "disconnected"}`} />
      <span>
        {isConnected ? "Backend Connected" : "Backend Disconnected"}
      </span>
      {isConnected && latency !== null && (
        <span style={{ fontSize: "11px", opacity: 0.8, borderLeft: "1px solid var(--color-success-border)", paddingLeft: "6px", marginLeft: "2px" }}>
          {latency}ms
        </span>
      )}
    </div>
  );
}
