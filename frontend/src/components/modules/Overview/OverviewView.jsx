import React, { useState, useEffect } from "react";
import {
  FileText,
  CheckSquare,
  Receipt,
  Clock,
  Sparkles,
  Zap,
  TrendingUp,
  ArrowRight,
  Bot,
  Settings,
  RefreshCw,
  AlertCircle,
  Database,
  Layers,
} from "lucide-react";
import {
  AreaChart,
  Area,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { SectionHeader } from "../../common/SectionHeader";
import { StatCard } from "../../common/StatCard";
import { StatusBadge } from "../../common/Badge";
import { fetchDashboardStats } from "../../../api/client";

export function OverviewView({ onNavigate, backendStatus, latency }) {
  const [dashboardData, setDashboardData] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [period, setPeriod] = useState("today"); // 'today' | 'all'
  const [lastUpdated, setLastUpdated] = useState(null);

  useEffect(() => {
    loadLiveStats(period);
  }, [period]);

  const loadLiveStats = async (selectedPeriod = period) => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await fetchDashboardStats(selectedPeriod);
      if (data && data.status === "success") {
        setDashboardData(data);
        const now = new Date();
        setLastUpdated(now.toLocaleTimeString());
      } else if (data && data.status === "error") {
        setError(data.error_message || "Failed to load database telemetry");
      }
    } catch (err) {
      console.warn("Failed to fetch live dashboard telemetry:", err);
      setError(err.message || "Backend telemetry service unavailable");
    } finally {
      setIsLoading(false);
    }
  };

  const handleRefresh = () => {
    loadLiveStats(period);
  };

  // Derive metrics safely from live backend payload (zero mock defaults)
  const summary = dashboardData?.summary || {
    total_documents: 0,
    total_documents_source: "Oracle Vector DB (GSVAI_DOCUMENTS & GSVAI_DOCUMENT_CHUNKS)",
    invoices_automated: 0,
    invoices_automated_source: "GSVAI_INVOICES (Status: APPROVED, FUSION_CREATED)",
    invoices_in_review: 0,
    invoices_in_review_source: "GSVAI_INVOICES (Status: REVIEW_REQUIRED)",
    ai_queries_count: 0,
    ai_queries_source: "GSVAI_AUDIT_LOGS (Action: DATA_ASSISTANT_QUERY)",
    ai_model_name: "Cohere Command A",
    avg_latency_ms: 0.0,
  };

  const aiThroughput = dashboardData?.ai_throughput || [];
  const documentPipeline = dashboardData?.document_pipeline || [];
  const recentActivities = dashboardData?.recent_activities || [];
  const workflowHealth = dashboardData?.workflow_health || { has_data: false, items: [] };

  return (
    <div className="animate-fade-in" style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
      {/* Header with Live Status and Actions */}
      <SectionHeader
        title="GSVAI Executive AI & Automation Dashboard"
        description="Unified operational telemetry, AI model throughput, document processing pipelines, and enterprise automation."
        isLive={backendStatus === "connected" && !error}
        badgeText={backendStatus === "connected" && !error ? "LIVE DATABASE TELEMETRY" : "BACKEND DISCONNECTED"}
        actions={
          <div style={{ display: "flex", alignItems: "center", gap: "8px", flexWrap: "wrap" }}>
            {lastUpdated && (
              <span style={{ fontSize: "11.5px", color: "var(--text-secondary)", marginRight: "4px" }}>
                Last updated: <strong>{lastUpdated}</strong>
              </span>
            )}
            <button
              className="btn btn-secondary"
              onClick={handleRefresh}
              disabled={isLoading}
              style={{ fontSize: "12px", padding: "6px 12px", gap: "5px" }}
              title="Refresh live telemetry from Oracle DB"
            >
              <RefreshCw size={13} className={isLoading ? "spin" : ""} />
              Refresh
            </button>
            <button className="btn btn-secondary" onClick={() => onNavigate("data-assistant")}>
              <Sparkles size={15} />
              Data Assistant
            </button>
            <button className="btn btn-secondary" onClick={() => onNavigate("invoice-automation")}>
              <Receipt size={15} />
              Invoice Review
            </button>
            <button className="btn btn-secondary" onClick={() => onNavigate("settings")}>
              <Settings size={15} />
              Admin Settings
            </button>
            <button className="btn btn-primary" onClick={() => onNavigate("ai-workspace")}>
              <Bot size={15} />
              Launch AI Workspace
            </button>
          </div>
        }
      />

      {/* Disconnected / Error Banner */}
      {(backendStatus === "disconnected" || error) && (
        <div
          className="card"
          style={{
            padding: "16px 20px",
            borderLeft: "4px solid var(--color-danger)",
            backgroundColor: "var(--color-danger-bg)",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            flexWrap: "wrap",
            gap: "12px",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <AlertCircle size={20} style={{ color: "var(--color-danger-text)" }} />
            <div>
              <div style={{ fontWeight: "700", fontSize: "13px", color: "var(--color-danger-text)" }}>
                Backend Telemetry Unavailable
              </div>
              <div style={{ fontSize: "12px", color: "var(--text-secondary)" }}>
                {error || "Cannot connect to FastAPI backend at http://127.0.0.1:8000. Displaying zero operational data."}
              </div>
            </div>
          </div>
          <button className="btn btn-secondary" onClick={handleRefresh} style={{ fontSize: "12px" }}>
            <RefreshCw size={13} /> Retry Connection
          </button>
        </div>
      )}

      {/* KPI Stats Grid */}
      <div className="grid-4">
        <StatCard
          title="Total Documents"
          value={String(summary.total_documents)}
          change="Live DB Count"
          icon={FileText}
          color="blue"
          subtitle="Indexed in Oracle Vector DB"
          sourceInfo={summary.total_documents_source || "Oracle Vector DB (GSVAI_DOCUMENTS & GSVAI_DOCUMENT_CHUNKS)"}
        />
        <StatCard
          title="Invoices Automated"
          value={String(summary.invoices_automated)}
          change="Synced & Approved"
          icon={Receipt}
          color="green"
          subtitle="Processed through pipeline"
          sourceInfo={summary.invoices_automated_source || "GSVAI_INVOICES (Status: APPROVED, FUSION_CREATED)"}
        />
        <StatCard
          title="Invoices in Review Queue"
          value={String(summary.invoices_in_review)}
          change={summary.invoices_in_review > 0 ? "Awaiting Action" : "Queue Clear"}
          isPositive={summary.invoices_in_review === 0}
          icon={CheckSquare}
          color="amber"
          subtitle="Human review in Invoice Automation"
          sourceInfo={summary.invoices_in_review_source || "GSVAI_INVOICES (Status: REVIEW_REQUIRED)"}
        />
        <StatCard
          title="AI & SQL Queries"
          value={String(summary.ai_queries_count)}
          change={summary.avg_latency_ms > 0 ? `${summary.avg_latency_ms}ms avg` : (backendStatus === "connected" ? "Live Telemetry" : "Offline")}
          icon={Sparkles}
          color="purple"
          subtitle={`${summary.ai_model_name || "Cohere Command A"} • Live Telemetry`}
          sourceInfo={summary.ai_queries_source || "GSVAI_AUDIT_LOGS (Action: DATA_ASSISTANT_QUERY)"}
        />
      </div>

      {/* Analytics Charts Grid */}
      <div className="grid-2">
        {/* AI Query Load Chart */}
        <div className="card">
          <div className="card-header">
            <div>
              <h3 className="card-title">
                <Zap size={16} style={{ color: "var(--color-primary)" }} />
                AI Inference Volume & Throughput
              </h3>
              <p className="card-subtitle">Real-time hourly query requests from audit logs</p>
            </div>
            <div style={{ display: "flex", gap: "4px" }}>
              <button
                className={`btn ${period === "today" ? "btn-primary" : "btn-secondary"}`}
                style={{ fontSize: "11px", padding: "2px 8px" }}
                onClick={() => setPeriod("today")}
              >
                Today
              </button>
              <button
                className={`btn ${period === "all" ? "btn-primary" : "btn-secondary"}`}
                style={{ fontSize: "11px", padding: "2px 8px" }}
                onClick={() => setPeriod("all")}
              >
                All Time
              </button>
            </div>
          </div>

          <div style={{ height: "210px", width: "100%" }}>
            {aiThroughput.length === 0 ? (
              <div
                style={{
                  height: "100%",
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  justifyContent: "center",
                  color: "var(--text-secondary)",
                  textAlign: "center",
                  padding: "20px",
                }}
              >
                <Zap size={24} style={{ opacity: 0.3, marginBottom: "8px" }} />
                <p style={{ margin: 0, fontWeight: "600", fontSize: "13px" }}>
                  {period === "today" ? "No AI inference activity today." : "No AI inference activity recorded."}
                </p>
                <p style={{ fontSize: "11.5px", color: "var(--text-tertiary)", marginTop: "4px" }}>
                  Execute natural-language questions in Data Assistant to view live query throughput and latency telemetry.
                </p>
              </div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={aiThroughput} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                  <defs>
                    <linearGradient id="queryGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#2563EB" stopOpacity={0.18} />
                      <stop offset="95%" stopColor="#2563EB" stopOpacity={0.0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#F2F4F7" />
                  <XAxis dataKey="time" stroke="#98A2B3" fontSize={11} tickLine={false} />
                  <YAxis stroke="#98A2B3" fontSize={11} tickLine={false} allowDecimals={false} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "#FFFFFF",
                      borderColor: "#E4E7EC",
                      borderRadius: "6px",
                      boxShadow: "0 4px 6px -2px rgba(16, 24, 40, 0.08)",
                      color: "#172033",
                      fontSize: "12px",
                    }}
                    formatter={(val, name) => [
                      name === "queries" ? `${val} queries` : `${val}s`,
                      name === "queries" ? "Queries Executed" : "Avg Latency",
                    ]}
                  />
                  <Area
                    type="monotone"
                    dataKey="queries"
                    stroke="#2563EB"
                    strokeWidth={2}
                    fillOpacity={1}
                    fill="url(#queryGrad)"
                    name="queries"
                  />
                </AreaChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>

        {/* Document Processing by Type */}
        <div className="card">
          <div className="card-header">
            <div>
              <h3 className="card-title">
                <FileText size={16} style={{ color: "var(--color-success)" }} />
                Document Processing Pipeline
              </h3>
              <p className="card-subtitle">Real document categories stored in Oracle Autonomous DB</p>
            </div>
            <span style={{ fontSize: "11px", color: "var(--text-secondary)", backgroundColor: "var(--bg-surface-subtle)", padding: "2px 8px", borderRadius: "var(--radius-sm)", border: "1px solid var(--border-subtle)" }}>
              Live Categories
            </span>
          </div>

          <div style={{ height: "210px", width: "100%" }}>
            {documentPipeline.length === 0 ? (
              <div
                style={{
                  height: "100%",
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  justifyContent: "center",
                  color: "var(--text-secondary)",
                  textAlign: "center",
                  padding: "20px",
                }}
              >
                <FileText size={24} style={{ opacity: 0.3, marginBottom: "8px" }} />
                <p style={{ margin: 0, fontWeight: "600", fontSize: "13px" }}>No document processing records found.</p>
                <p style={{ fontSize: "11.5px", color: "var(--text-tertiary)", marginTop: "4px" }}>
                  Upload invoice documents or ingest knowledge files to view pipeline distribution.
                </p>
              </div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={documentPipeline} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#F2F4F7" />
                  <XAxis dataKey="name" stroke="#98A2B3" fontSize={10} tickLine={false} />
                  <YAxis stroke="#98A2B3" fontSize={11} tickLine={false} allowDecimals={false} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "#FFFFFF",
                      borderColor: "#E4E7EC",
                      borderRadius: "6px",
                      boxShadow: "0 4px 6px -2px rgba(16, 24, 40, 0.08)",
                      color: "#172033",
                      fontSize: "12px",
                    }}
                  />
                  <Bar dataKey="processed" fill="#12B76A" radius={[3, 3, 0, 0]} name="Processed / Indexed" />
                  <Bar dataKey="pending" fill="#F79009" radius={[3, 3, 0, 0]} name="Pending Review" />
                  <Bar dataKey="failed" fill="#F04438" radius={[3, 3, 0, 0]} name="Flagged / Exceptions" />
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>
      </div>

      {/* Bottom Row: Recent Activity & Workflow Health */}
      <div className="grid-2">
        {/* Recent Activity Stream */}
        <div className="card">
          <div className="card-header">
            <div>
              <h3 className="card-title">
                <Clock size={16} style={{ color: "var(--color-info)" }} />
                Recent Operational Activity
              </h3>
              <p className="card-subtitle">Live events from GSVAI_AUDIT_LOGS</p>
            </div>
            <span style={{ fontSize: "11.5px", color: "var(--text-secondary)" }}>Audit Log Telemetry</span>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
            {recentActivities.length === 0 ? (
              <div style={{ padding: "30px 16px", textAlign: "center", color: "var(--text-secondary)" }}>
                <Clock size={22} style={{ opacity: 0.3, margin: "0 auto 6px" }} />
                <p style={{ margin: 0, fontWeight: "600", fontSize: "13px" }}>No operational activity yet.</p>
                <p style={{ fontSize: "11.5px", color: "var(--text-tertiary)", marginTop: "4px" }}>
                  All user actions, OCR extractions, and ERP syncs will be logged here.
                </p>
              </div>
            ) : (
              recentActivities.map((act) => (
                <div
                  key={act.id}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    padding: "10px 12px",
                    borderRadius: "var(--radius-md)",
                    backgroundColor: "var(--bg-surface-subtle)",
                    border: "1px solid var(--border-subtle)",
                  }}
                >
                  <div style={{ display: "flex", flexDirection: "column", gap: "2px", maxWidth: "78%" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                      <span style={{ fontSize: "13px", fontWeight: "600", color: "var(--text-primary)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                        {act.title}
                      </span>
                      <StatusBadge status={act.status} />
                    </div>
                    <span style={{ fontSize: "12px", color: "var(--text-secondary)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                      {act.desc}
                    </span>
                  </div>
                  <span style={{ fontSize: "11px", color: "var(--text-secondary)", whiteSpace: "nowrap", fontFamily: "var(--font-mono)" }}>
                    {act.time}
                  </span>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Workflow Health & Quick Launchpad */}
        <div className="card" style={{ display: "flex", flexDirection: "column", justifyContent: "space-between" }}>
          <div>
            <div className="card-header">
              <div>
                <h3 className="card-title">
                  <TrendingUp size={16} style={{ color: "var(--color-purple)" }} />
                  Platform Workflow Health
                </h3>
                <p className="card-subtitle">Calculated from actual invoice & document records</p>
              </div>
              <span className="badge badge-live">Live Database Telemetry</span>
            </div>

            {workflowHealth.has_data && workflowHealth.items.length > 0 ? (
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px", marginBottom: "16px" }}>
                {workflowHealth.items.map((item, index) => (
                  <div
                    key={index}
                    style={{
                      backgroundColor: "var(--bg-surface-subtle)",
                      padding: "10px 12px",
                      borderRadius: "var(--radius-md)",
                      border: "1px solid var(--border-subtle)",
                    }}
                  >
                    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "2px" }}>
                      <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                        <div style={{ width: "7px", height: "7px", borderRadius: "50%", backgroundColor: item.color }} />
                        <span style={{ fontSize: "12px", color: "var(--text-secondary)" }}>{item.name}</span>
                      </div>
                      <span style={{ fontSize: "11px", color: "var(--text-tertiary)" }}>
                        {item.count} items
                      </span>
                    </div>
                    <div style={{ fontSize: "18px", fontWeight: "700", color: "var(--text-primary)" }}>
                      {item.value}%
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div style={{ padding: "24px 16px", textAlign: "center", color: "var(--text-secondary)", backgroundColor: "var(--bg-surface-subtle)", borderRadius: "var(--radius-md)", marginBottom: "16px" }}>
                <TrendingUp size={22} style={{ opacity: 0.3, margin: "0 auto 6px" }} />
                <p style={{ margin: 0, fontWeight: "600", fontSize: "13px" }}>No workflow data available.</p>
                <p style={{ fontSize: "11.5px", color: "var(--text-tertiary)", marginTop: "4px" }}>
                  Workflow metrics will compute automatically as invoices progress through extraction and review.
                </p>
              </div>
            )}
          </div>

          {/* Quick Launch Buttons */}
          <div style={{ display: "flex", flexDirection: "column", gap: "8px", paddingTop: "12px", borderTop: "1px solid var(--border-subtle)" }}>
            <span style={{ fontSize: "11px", fontWeight: "600", color: "var(--text-secondary)", textTransform: "uppercase" }}>
              Quick Navigation
            </span>
            <div style={{ display: "flex", gap: "8px" }}>
              <button
                className="btn btn-secondary"
                style={{ flex: 1, fontSize: "12.5px" }}
                onClick={() => onNavigate("ai-workspace")}
              >
                AI Workspace <ArrowRight size={13} />
              </button>
              <button
                className="btn btn-secondary"
                style={{ flex: 1, fontSize: "12.5px" }}
                onClick={() => onNavigate("invoice-automation")}
              >
                Invoices & Review <ArrowRight size={13} />
              </button>
              <button
                className="btn btn-secondary"
                style={{ flex: 1, fontSize: "12.5px" }}
                onClick={() => onNavigate("settings")}
              >
                Admin Settings <ArrowRight size={13} />
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
