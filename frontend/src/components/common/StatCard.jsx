import React from "react";
import { Info } from "lucide-react";

export function StatCard({ title, value, change, isPositive = true, icon: Icon, color = "blue", subtitle, sourceInfo }) {
  const colorMap = {
    blue: {
      bg: "var(--color-primary-light)",
      border: "var(--color-primary-border)",
      text: "var(--color-primary)",
    },
    green: {
      bg: "var(--color-success-bg)",
      border: "var(--color-success-border)",
      text: "var(--color-success-text)",
    },
    purple: {
      bg: "var(--color-purple-bg)",
      border: "var(--color-purple-border)",
      text: "var(--color-purple-text)",
    },
    amber: {
      bg: "var(--color-warning-bg)",
      border: "var(--color-warning-border)",
      text: "var(--color-warning-text)",
    },
    cyan: {
      bg: "var(--color-info-bg)",
      border: "var(--color-info-border)",
      text: "var(--color-info-text)",
    },
  };

  const scheme = colorMap[color] || colorMap.blue;

  return (
    <div className="card" style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
          <span style={{ fontSize: "13px", fontWeight: "500", color: "var(--text-secondary)" }}>
            {title}
          </span>
          {sourceInfo && (
            <span
              title={sourceInfo}
              style={{
                display: "inline-flex",
                alignItems: "center",
                cursor: "help",
                color: "var(--text-tertiary)",
              }}
            >
              <Info size={12} />
            </span>
          )}
        </div>
        {Icon && (
          <div
            style={{
              width: "32px",
              height: "32px",
              borderRadius: "var(--radius-md)",
              backgroundColor: scheme.bg,
              border: `1px solid ${scheme.border}`,
              color: scheme.text,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <Icon size={16} />
          </div>
        )}
      </div>

      <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between" }}>
        <span style={{ fontSize: "24px", fontWeight: "700", color: "var(--text-primary)", letterSpacing: "-0.02em" }}>
          {value}
        </span>
        {change && (
          <span
            style={{
              fontSize: "11.5px",
              fontWeight: "600",
              color: isPositive ? "var(--color-success-text)" : "var(--color-danger-text)",
              backgroundColor: isPositive ? "var(--color-success-bg)" : "var(--color-danger-bg)",
              padding: "2px 6px",
              borderRadius: "var(--radius-sm)",
            }}
          >
            {change}
          </span>
        )}
      </div>

      {subtitle && (
        <span style={{ fontSize: "11.5px", color: "var(--text-secondary)", marginTop: "-2px" }}>
          {subtitle}
        </span>
      )}
    </div>
  );
}
