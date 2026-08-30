import React from "react";
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

const AI_QUERY_DATA = [
  { time: "08:00", queries: 45, latency: 1.2 },
  { time: "10:00", queries: 120, latency: 0.9 },
  { time: "12:00", queries: 210, latency: 1.1 },
  { time: "14:00", queries: 185, latency: 1.4 },
  { time: "16:00", queries: 260, latency: 1.0 },
  { time: "18:00", queries: 140, latency: 0.8 },
  { time: "20:00", queries: 80, latency: 0.7 },
];

const DOC_DISTRIBUTION_DATA = [
  { name: "Vendor Invoices", processed: 342, pending: 18 },
  { name: "Contracts & NDAs", processed: 185, pending: 7 },
  { name: "Purchase Orders", processed: 290, pending: 12 },
  { name: "Bank Statements", processed: 94, pending: 3 },
  { name: "Tax Filings", processed: 130, pending: 5 },
];

const WORKFLOW_STATUS_DATA = [
  { name: "Completed / Synced", value: 68, color: "#12B76A" },
  { name: "Pending Review", value: 14, color: "#F79009" },
  { name: "In Extraction", value: 12, color: "#2563EB" },
  { name: "Flagged Exceptions", value: 6, color: "#F04438" },
];

const RECENT_ACTIVITIES = [
  {
    id: 1,
    title: "Invoice #INV-2026-8819 Validated",
    desc: "Acme Cloud Services - $42,500.00 matched PO-9921",
    time: "4 mins ago",
    status: "Validated",
  },
  {
    id: 2,
    title: "Live Chat Query Processed",
    desc: "Cohere Command A generated synthesis",
    time: "12 mins ago",
    status: "Completed",
  },
  {
    id: 3,
    title: "Pending Approval Escalated",
    desc: "Oracle Fusion PO-4001 requires director sign-off",
    time: "25 mins ago",
    status: "Pending",
  },
  {
    id: 4,
    title: "Contract OCR Extraction",
    desc: "Master Services Agreement - Global Tech Logistics",
    time: "1 hour ago",
    status: "Completed",
  },
];

export function OverviewView({ onNavigate, backendStatus, latency }) {
  return (
    <div className="animate-fade-in" style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
      {/* Header */}
      <SectionHeader
        title="GSVAI Executive AI & Automation Dashboard"
        description="Unified operational telemetry, AI model throughput, document processing pipelines, and enterprise automation."
        isLive={backendStatus === "connected"}
        badgeText="TELEMETRY ACTIVE"
        actions={
          <div style={{ display: "flex", gap: "8px" }}>
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

      {/* KPI Stats Grid */}
      <div className="grid-4">
        <StatCard
          title="Total Documents"
          value="1,041"
          change="+14.2%"
          icon={FileText}
          color="blue"
          subtitle="Processed this billing cycle"
        />
        <StatCard
          title="Invoices Automated"
          value="482"
          change="+28.5%"
          icon={Receipt}
          color="green"
          subtitle="94.8% auto-match rate"
        />
        <StatCard
          title="Invoices in Review Queue"
          value="4"
          change="Awaiting Action"
          isPositive={false}
          icon={CheckSquare}
          color="amber"
          subtitle="Human review in Invoice Automation"
        />
        <StatCard
          title="AI Queries (Live OCI)"
          value="1,248"
          change={backendStatus === "connected" ? `${latency || 120}ms avg` : "Offline"}
          icon={Sparkles}
          color="purple"
          subtitle="Cohere Command A • ap-hyderabad-1"
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
              <p className="card-subtitle">Real-time hourly query requests</p>
            </div>
            <span style={{ fontSize: "11.5px", color: "var(--text-secondary)", backgroundColor: "var(--bg-surface-subtle)", padding: "2px 8px", borderRadius: "var(--radius-sm)", border: "1px solid var(--border-subtle)" }}>
              Today
            </span>
          </div>

          <div style={{ height: "210px", width: "100%" }}>
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={AI_QUERY_DATA} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <defs>
                  <linearGradient id="queryGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#2563EB" stopOpacity={0.18} />
                    <stop offset="95%" stopColor="#2563EB" stopOpacity={0.0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#F2F4F7" />
                <XAxis dataKey="time" stroke="#98A2B3" fontSize={11} tickLine={false} />
                <YAxis stroke="#98A2B3" fontSize={11} tickLine={false} />
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
                <Area type="monotone" dataKey="queries" stroke="#2563EB" strokeWidth={2} fillOpacity={1} fill="url(#queryGrad)" />
              </AreaChart>
            </ResponsiveContainer>
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
              <p className="card-subtitle">Extracted vs Pending by category</p>
            </div>
            <span style={{ fontSize: "11.5px", color: "var(--text-secondary)", backgroundColor: "var(--bg-surface-subtle)", padding: "2px 8px", borderRadius: "var(--radius-sm)", border: "1px solid var(--border-subtle)" }}>
              By Category
            </span>
          </div>

          <div style={{ height: "210px", width: "100%" }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={DOC_DISTRIBUTION_DATA} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#F2F4F7" />
                <XAxis dataKey="name" stroke="#98A2B3" fontSize={10} tickLine={false} />
                <YAxis stroke="#98A2B3" fontSize={11} tickLine={false} />
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
                <Bar dataKey="processed" fill="#12B76A" radius={[3, 3, 0, 0]} name="Processed" />
                <Bar dataKey="pending" fill="#F79009" radius={[3, 3, 0, 0]} name="Pending" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Bottom Row: Recent Activity & Quick Action Launchpad */}
      <div className="grid-2">
        {/* Recent Activity Stream */}
        <div className="card">
          <div className="card-header">
            <h3 className="card-title">
              <Clock size={16} style={{ color: "var(--color-info)" }} />
              Recent Operational Activity
            </h3>
            <span style={{ fontSize: "11.5px", color: "var(--text-secondary)" }}>Mock telemetry</span>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
            {RECENT_ACTIVITIES.map((act) => (
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
                <div style={{ display: "flex", flexDirection: "column", gap: "2px" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                    <span style={{ fontSize: "13px", fontWeight: "600", color: "var(--text-primary)" }}>
                      {act.title}
                    </span>
                    <StatusBadge status={act.status} />
                  </div>
                  <span style={{ fontSize: "12px", color: "var(--text-secondary)" }}>
                    {act.desc}
                  </span>
                </div>
                <span style={{ fontSize: "11px", color: "var(--text-secondary)", whiteSpace: "nowrap" }}>
                  {act.time}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Workflow & Quick Launchpad */}
        <div className="card" style={{ display: "flex", flexDirection: "column", justifyContent: "space-between" }}>
          <div>
            <div className="card-header">
              <h3 className="card-title">
                <TrendingUp size={16} style={{ color: "var(--color-purple)" }} />
                Platform Workflow Health
              </h3>
              <span className="badge badge-demo">Simulated</span>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px", marginBottom: "16px" }}>
              {WORKFLOW_STATUS_DATA.map((item, index) => (
                <div
                  key={index}
                  style={{
                    backgroundColor: "var(--bg-surface-subtle)",
                    padding: "10px 12px",
                    borderRadius: "var(--radius-md)",
                    border: "1px solid var(--border-subtle)",
                  }}
                >
                  <div style={{ display: "flex", alignItems: "center", gap: "6px", marginBottom: "2px" }}>
                    <div style={{ width: "7px", height: "7px", borderRadius: "50%", backgroundColor: item.color }} />
                    <span style={{ fontSize: "12px", color: "var(--text-secondary)" }}>{item.name}</span>
                  </div>
                  <div style={{ fontSize: "18px", fontWeight: "700", color: "var(--text-primary)" }}>{item.value}%</div>
                </div>
              ))}
            </div>
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
