import React from "react";
import {
  LayoutDashboard,
  Bot,
  BookOpen,
  FileText,
  Receipt,
  Database,
  Mail,
  ShieldCheck,
  Settings,
  ChevronLeft,
  ChevronRight,
  Cpu,
} from "lucide-react";

export const NAV_ITEMS = [
  { id: "overview", label: "Overview", icon: LayoutDashboard, isLive: false },
  { id: "ai-workspace", label: "AI Workspace", icon: Bot, isLive: true },
  { id: "invoice-automation", label: "Invoice Automation", icon: Receipt, isLive: false },
  { id: "data-assistant", label: "Data Assistant", icon: Database, isLive: false },
  { id: "email-automation", label: "Email Automation", icon: Mail, isLive: false },
  { id: "settings", label: "Settings", icon: Settings, isLive: false },
];

export function Sidebar({ activeTab, setActiveTab, isCollapsed, setIsCollapsed, backendStatus }) {
  return (
    <aside className={`sidebar ${isCollapsed ? "collapsed" : ""}`}>
      {/* Sidebar Header / Brand */}
      <div className="sidebar-header">
        <div className="brand-wrapper">
          <div className="brand-icon">
            <Cpu size={18} />
          </div>
          {!isCollapsed && (
            <div className="brand-text">
              <div className="brand-name">
                GSVAI
              </div>
              <span className="brand-sub">Enterprise AI Platform</span>
            </div>
          )}
        </div>

        <button
          className="sidebar-toggle-btn"
          onClick={() => setIsCollapsed(!isCollapsed)}
          title={isCollapsed ? "Expand Sidebar" : "Collapse Sidebar"}
        >
          {isCollapsed ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}
        </button>
      </div>

      {/* Navigation Links */}
      <nav className="sidebar-nav">
        {!isCollapsed && <div className="nav-section-title">Navigation</div>}

        {NAV_ITEMS.map((item) => {
          const Icon = item.icon;
          const isActive = activeTab === item.id;

          return (
            <button
              key={item.id}
              className={`nav-item ${isActive ? "active" : ""}`}
              onClick={() => setActiveTab(item.id)}
              title={isCollapsed ? item.label : undefined}
            >
              <div className="nav-item-icon">
                <Icon size={18} />
              </div>

              {!isCollapsed && (
                <>
                  <span className="nav-item-text">{item.label}</span>
                  {item.isLive && (
                    <span
                      style={{
                        fontSize: "10px",
                        fontWeight: "600",
                        padding: "1px 6px",
                        borderRadius: "var(--radius-sm)",
                        backgroundColor: "var(--color-success-bg)",
                        color: "var(--color-success-text)",
                        border: "1px solid var(--color-success-border)",
                      }}
                    >
                      LIVE
                    </span>
                  )}
                  {item.count && (
                    <span className="badge-count">
                      {item.count}
                    </span>
                  )}
                </>
              )}
            </button>
          );
        })}
      </nav>

      {/* Sidebar Footer with OCI POC Status info */}
      {!isCollapsed && (
        <div className="sidebar-footer">
          <div className="oci-badge-card">
            <div className={`oci-badge-icon ${backendStatus === "connected" ? "" : "disconnected"}`} />
            <div className="oci-badge-info">
              <div className="oci-badge-title">OCI GenAI On-Demand</div>
              <div className="oci-badge-sub">Cohere Command A • ap-hyderabad-1</div>
            </div>
          </div>
        </div>
      )}
    </aside>
  );
}
