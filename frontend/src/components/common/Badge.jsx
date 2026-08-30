import React from "react";

export function LiveBadge({ text = "LIVE" }) {
  return (
    <span className="badge badge-live">
      <span
        style={{
          width: "5px",
          height: "5px",
          borderRadius: "50%",
          backgroundColor: "var(--color-success)",
        }}
      />
      {text}
    </span>
  );
}

export function DemoBadge({ text = "DEMO" }) {
  return (
    <span className="badge badge-demo">
      <span
        style={{
          width: "5px",
          height: "5px",
          borderRadius: "50%",
          backgroundColor: "var(--color-warning)",
        }}
      />
      {text}
    </span>
  );
}

export function StatusBadge({ status }) {
  let style = {
    background: "var(--bg-surface)",
    color: "var(--text-secondary)",
    border: "1px solid var(--border-subtle)",
  };

  const s = String(status || "").toLowerCase();

  if (s.includes("success") || s.includes("approved") || s.includes("synced") || s.includes("active") || s.includes("completed") || s.includes("passed")) {
    style = {
      background: "var(--color-success-bg)",
      color: "var(--color-success-text)",
      border: "1px solid var(--color-success-border)",
    };
  } else if (s.includes("pending") || s.includes("processing") || s.includes("review") || s.includes("in progress") || s.includes("medium")) {
    style = {
      background: "var(--color-warning-bg)",
      color: "var(--color-warning-text)",
      border: "1px solid var(--color-warning-border)",
    };
  } else if (s.includes("failed") || s.includes("rejected") || s.includes("error") || s.includes("high") || s.includes("variance alert")) {
    style = {
      background: "var(--color-danger-bg)",
      color: "var(--color-danger-text)",
      border: "1px solid var(--color-danger-border)",
    };
  } else if (s.includes("validated") || s.includes("info") || s.includes("low") || s.includes("auto-routed")) {
    style = {
      background: "var(--color-primary-light)",
      color: "var(--color-primary)",
      border: "1px solid var(--color-primary-border)",
    };
  }

  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        padding: "2px 7px",
        borderRadius: "var(--radius-sm)",
        fontSize: "11.5px",
        fontWeight: "500",
        letterSpacing: "0.01em",
        textTransform: "capitalize",
        ...style,
      }}
    >
      {status}
    </span>
  );
}
