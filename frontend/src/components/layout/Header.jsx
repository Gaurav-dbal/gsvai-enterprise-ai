import React from "react";
import { Search, RefreshCw } from "lucide-react";
import { StatusIndicator } from "../common/StatusIndicator";

export function Header({
  activeTitle,
  backendStatus,
  latency,
  onRefreshHealth,
  isRefreshing,
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

      {/* Right side: Search, Live Status, Actions, Profile */}
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

        {/* User Profile */}
        <div className="user-profile-badge">
          <div className="user-avatar">EA</div>
          <span className="user-name">Enterprise Admin</span>
        </div>
      </div>
    </header>
  );
}
