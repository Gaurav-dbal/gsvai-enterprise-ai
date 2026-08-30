import React, { useState } from "react";
import {
  ShieldCheck,
  CheckCircle,
  XCircle,
  Sparkles,
  Clock,
  RotateCcw,
} from "lucide-react";
import { SectionHeader } from "../../common/SectionHeader";
import { StatusBadge } from "../../common/Badge";

const MOCK_APPROVALS = [
  {
    id: "APP-401",
    title: "Supplier Contract Renewal: Apex Cloud Services",
    category: "Contract Sign-off",
    requester: "DevOps Infrastructure Team",
    amount: "$180,000.00",
    urgency: "High",
    aiRecommendation: {
      action: "Approve with Notice",
      confidence: "97.4%",
      riskLevel: "Low",
      reasoning:
        "All terms comply with standard corporate indemnity thresholds. Pricing represents a 4.5% discount versus standard retail list. No non-standard liabilities detected in Section 14.",
    },
    details: {
      vendor: "Apex Infrastructure Solutions Ltd.",
      term: "36 Months",
      sla: "99.99% Uptime Commitment",
    },
  },
  {
    id: "APP-402",
    title: "Invoice #INV-2026-8820 Variance Exception",
    category: "Invoice Exception",
    requester: "Accounts Payable Bot",
    amount: "$18,920.00",
    urgency: "Medium",
    aiRecommendation: {
      action: "Manual Review Required",
      confidence: "91.2%",
      riskLevel: "Medium",
      reasoning:
        "Line item unit rate for Direct Connect port is $9,460 vs PO baseline $9,350 (1.2% variance). Variance is within 2.5% automated tolerance, but supplier has not provided rate escalation notice.",
    },
    details: {
      vendor: "Nexus Global Networks",
      poNumber: "PO-9924",
      variance: "+$220.00 total",
    },
  },
  {
    id: "APP-403",
    title: "Oracle Fusion ERP API Access Provisioning",
    category: "Security & Access",
    requester: "Integration Engineering",
    amount: "N/A",
    urgency: "Low",
    aiRecommendation: {
      action: "Approve",
      confidence: "99.0%",
      riskLevel: "Low",
      reasoning:
        "Read-only REST role scoping strictly adheres to Principle of Least Privilege for autonomous invoice matching bot.",
    },
    details: {
      vendor: "Internal System",
      role: "ORA_FND_AP_INVOICE_READ_DUTY",
      environment: "Production ERP",
    },
  },
];

export function ApprovalsView() {
  const [approvalsList, setApprovalsList] = useState(MOCK_APPROVALS);
  const [selectedApproval, setSelectedApproval] = useState(MOCK_APPROVALS[0]);
  const [actionLog, setActionLog] = useState([]);

  const handleAction = (decision) => {
    if (!selectedApproval) return;

    const logEntry = {
      id: Date.now(),
      itemTitle: selectedApproval.title,
      decision,
      timestamp: new Date().toLocaleTimeString(),
    };

    setActionLog((prev) => [logEntry, ...prev]);

    const remaining = approvalsList.filter((a) => a.id !== selectedApproval.id);
    setApprovalsList(remaining);
    setSelectedApproval(remaining[0] || null);
  };

  return (
    <div className="animate-fade-in" style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
      <SectionHeader
        title="Human-in-the-Loop Governance & Approvals"
        description="Review AI risk assessments, resolve compliance exceptions, and provide human governance authorization."
        isLive={false}
        badgeText="DEMO / HUMAN-IN-THE-LOOP"
      />

      <div className="grid-3">
        {/* Pending Queue */}
        <div className="card" style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
          <div className="card-header">
            <h3 className="card-title">
              <Clock size={16} style={{ color: "var(--color-warning-text)" }} />
              Pending Queue
            </h3>
            <span className="badge badge-demo">{approvalsList.length} Pending</span>
          </div>

          {approvalsList.length === 0 ? (
            <div style={{ textAlign: "center", padding: "28px 14px", color: "var(--text-secondary)", fontSize: "13px" }}>
              <CheckCircle size={28} style={{ color: "var(--color-success)", margin: "0 auto 8px" }} />
              All pending governance approvals are cleared!
            </div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
              {approvalsList.map((app) => {
                const isSelected = selectedApproval?.id === app.id;
                return (
                  <div
                    key={app.id}
                    onClick={() => setSelectedApproval(app)}
                    style={{
                      backgroundColor: isSelected ? "var(--color-primary-light)" : "var(--bg-surface-subtle)",
                      border: `1px solid ${isSelected ? "var(--color-primary-border)" : "var(--border-subtle)"}`,
                      borderRadius: "var(--radius-md)",
                      padding: "10px 12px",
                      cursor: "pointer",
                      display: "flex",
                      flexDirection: "column",
                      gap: "4px",
                    }}
                  >
                    <div style={{ display: "flex", justifyContent: "space-between" }}>
                      <span style={{ fontSize: "11px", fontFamily: "var(--font-mono)", color: "var(--color-primary)", fontWeight: "600" }}>
                        {app.id}
                      </span>
                      <StatusBadge status={app.urgency} />
                    </div>

                    <div style={{ fontSize: "12.5px", fontWeight: "600", color: "var(--text-primary)" }}>
                      {app.title}
                    </div>

                    <div style={{ display: "flex", justifyContent: "space-between", fontSize: "11.5px", color: "var(--text-secondary)" }}>
                      <span>{app.category}</span>
                      <span style={{ color: "var(--text-primary)", fontWeight: "600" }}>{app.amount}</span>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Detailed Inspection & AI Recommendation */}
        {selectedApproval ? (
          <div style={{ gridColumn: "span 2", display: "flex", flexDirection: "column", gap: "16px" }}>
            {/* Header / Info */}
            <div className="card">
              <div className="card-header">
                <div>
                  <h3 className="card-title">{selectedApproval.title}</h3>
                  <p className="card-subtitle">
                    Requested by {selectedApproval.requester} • Value: {selectedApproval.amount}
                  </p>
                </div>
                <StatusBadge status={selectedApproval.category} />
              </div>

              {/* Item Details Grid */}
              <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "10px", margin: "12px 0" }}>
                {Object.entries(selectedApproval.details).map(([key, val]) => (
                  <div key={key} style={{ backgroundColor: "var(--bg-surface-subtle)", border: "1px solid var(--border-subtle)", padding: "8px 10px", borderRadius: "var(--radius-sm)" }}>
                    <div style={{ fontSize: "11px", color: "var(--text-secondary)", textTransform: "capitalize" }}>{key}</div>
                    <div style={{ fontSize: "12.5px", fontWeight: "600", color: "var(--text-primary)", marginTop: "2px" }}>{val}</div>
                  </div>
                ))}
              </div>

              {/* AI Risk Assessment */}
              <div
                style={{
                  backgroundColor: "var(--color-primary-light)",
                  border: "1px solid var(--color-primary-border)",
                  borderRadius: "var(--radius-md)",
                  padding: "14px",
                  display: "flex",
                  flexDirection: "column",
                  gap: "6px",
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                    <Sparkles size={15} style={{ color: "var(--color-primary)" }} />
                    <span style={{ fontSize: "12.5px", fontWeight: "600", color: "var(--color-primary)" }}>
                      AI Recommendation: {selectedApproval.aiRecommendation.action}
                    </span>
                  </div>
                  <span style={{ fontSize: "11.5px", color: "var(--color-success-text)", fontWeight: "600" }}>
                    Confidence: {selectedApproval.aiRecommendation.confidence}
                  </span>
                </div>

                <p style={{ fontSize: "13px", color: "var(--text-primary)", lineHeight: "1.5", margin: 0 }}>
                  {selectedApproval.aiRecommendation.reasoning}
                </p>
              </div>

              {/* Action Buttons */}
              <div style={{ display: "flex", gap: "10px", marginTop: "16px", justifyContent: "flex-end" }}>
                <button className="btn btn-secondary" onClick={() => handleAction("Requested Changes")}>
                  <RotateCcw size={14} />
                  Request Changes
                </button>
                <button className="btn btn-danger" onClick={() => handleAction("Rejected")}>
                  <XCircle size={14} />
                  Reject
                </button>
                <button className="btn btn-success" onClick={() => handleAction("Approved")}>
                  <CheckCircle size={14} />
                  Approve & Authorize
                </button>
              </div>
            </div>

            {/* Audit Trail Log */}
            {actionLog.length > 0 && (
              <div className="card">
                <div className="card-header">
                  <h3 className="card-title">
                    <ShieldCheck size={16} style={{ color: "var(--color-success)" }} />
                    Session Audit Decision History
                  </h3>
                </div>

                <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                  {actionLog.map((log) => (
                    <div
                      key={log.id}
                      style={{
                        display: "flex",
                        justifyContent: "space-between",
                        alignItems: "center",
                        padding: "8px 12px",
                        backgroundColor: "var(--bg-surface-subtle)",
                        border: "1px solid var(--border-subtle)",
                        borderRadius: "var(--radius-sm)",
                        fontSize: "12px",
                      }}
                    >
                      <span style={{ color: "var(--text-primary)", fontWeight: "500" }}>{log.itemTitle}</span>
                      <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                        <StatusBadge status={log.decision} />
                        <span style={{ color: "var(--text-secondary)", fontSize: "11px" }}>{log.timestamp}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        ) : null}
      </div>
    </div>
  );
}
