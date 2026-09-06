import React from "react";
import { Search, RefreshCw, Palette } from "lucide-react";
import { StatusIndicator } from "../common/StatusIndicator";

export const THEMES = [
  { id: "default", label: "Default Light", icon: "☀️" },
  { id: "soft-gray", label: "Soft Gray", icon: "🏢" },
  { id: "cool-blue", label: "Cool Blue", icon: "🌊" },
  { id: "slate", label: "Slate Neutral", icon: "🏛️" },
  { id: "dark", label: "Obsidian Dark", icon: "🌙" },
  { id: "high-contrast", label: "High Contrast", icon: "⚡" },
];

export function Header({
  activeTitle,
  backendStatus,
  latency,
  onRefreshHealth,
  isRefreshing,
  currentTheme = "default",
  onThemeChange,
}) {
  return (
    <header className="header">
      {/* Left side: View title */}
      <div className="header-left">
        <div className="header-title-group">
          <h1 className="header-title">
            {activeTitle}
          </h1>
          <span className="header-subtitle">
            GSVAI Enterprise AI Platform / {activeTitle}
          </span>
        </div>
      </div>

      {/* Right side: Search, Live Status, Theme Switcher, Actions, Profile */}
      <div className="header-right">
        {/* Search bar */}
        <div className="search-input-wrapper">
          <Search size={14} className="search-icon" />
          <input
            type="text"
            className="search-input"
            placeholder="Search documents, invoices, queries..."
          />
        </div>

        {/* Live Backend Connection Indicator (GET /health) */}
        <StatusIndicator
          status={backendStatus}
          latency={latency}
        />

        {/* Quick Health Refresh button */}
        <button
          className="btn-icon"
          onClick={onRefreshHealth}
          title="Check Backend Health (GET /health)"
        >
          <RefreshCw size={14} className={isRefreshing ? "animate-spin" : ""} />
        </button>

        {/* Enterprise Appearance / Theme Selector */}
        {onThemeChange && (
          <div
            className="theme-selector-wrapper"
            style={{
              display: "flex",
              alignItems: "center",
              gap: "6px",
              padding: "4px 8px",
              borderRadius: "var(--radius-md)",
              backgroundColor: "var(--bg-surface)",
              border: "1px solid var(--border-card)",
            }}
          >
            <Palette size={14} style={{ color: "var(--text-secondary)", flexShrink: 0 }} />
            <select
              value={currentTheme}
              onChange={(e) => onThemeChange(e.target.value)}
              title="Select Enterprise Application Theme"
              style={{
                border: "none",
                background: "transparent",
                color: "var(--text-primary)",
                fontSize: "12px",
                fontWeight: "500",
                padding: "2px 4px",
                cursor: "pointer",
                outline: "none",
              }}
            >
              {THEMES.map((t) => (
                <option key={t.id} value={t.id} style={{ background: "var(--bg-card)", color: "var(--text-primary)" }}>
                  {t.icon} {t.label}
                </option>
              ))}
            </select>
          </div>
        )}

        {/* User Profile */}
        <div className="user-profile-badge">
          <div className="user-avatar">EA</div>
          <span className="user-name">Enterprise Admin</span>
        </div>
      </div>
    </header>
  );
}
