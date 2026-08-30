import React, { useState } from "react";
import {
  Send,
  Sparkles,
  Inbox,
  Edit3,
} from "lucide-react";
import { SectionHeader } from "../../common/SectionHeader";
import { StatusBadge } from "../../common/Badge";

const MOCK_EMAILS = [
  {
    id: 1,
    sender: "billing@apexinfra.com",
    subject: "Payment Status for Invoice #INV-2026-8819 ($42,500)",
    date: "10:30 AM",
    priority: "High",
    category: "Payment Inquiry",
    summary:
      "Vendor is requesting payment confirmation for Invoice #INV-2026-8819 due on Aug 28. Mentions that early payment discount applies if paid by Aug 25.",
    extractedEntities: {
      invoiceNo: "INV-2026-8819",
      amount: "$42,500.00",
      dueDate: "2026-08-28",
      supplier: "Apex Infrastructure Solutions",
    },
    suggestedReply:
      "Dear Apex Billing Team,\n\nThank you for reaching out. We have verified Invoice #INV-2026-8819 ($42,500.00). The 3-way matching validation has passed and payment dispatch is scheduled for processing on Aug 24 via Oracle Fusion.\n\nBest regards,\nGSV Global Accounts Payable",
    status: "Needs Review",
  },
  {
    id: 2,
    sender: "procurement@supplier-nexus.com",
    subject: "Updated Certificate of Insurance for PO-9924",
    date: "08:15 AM",
    priority: "Medium",
    category: "Compliance",
    summary:
      "Supplier attached renewed liability insurance certificate valid through Dec 2027 for ongoing data center cross-connect contract.",
    extractedEntities: {
      poNo: "PO-9924",
      docType: "Certificate of Insurance",
      validUntil: "2027-12-31",
    },
    suggestedReply:
      "Hello Nexus Procurement,\n\nWe have received and archived your updated Certificate of Insurance for PO-9924 in our compliance registry.\n\nThank you,\nGSV Procurement Operations",
    status: "Auto-routed",
  },
];

export function EmailAutomationView() {
  const [selectedEmail, setSelectedEmail] = useState(MOCK_EMAILS[0]);
  const [draftReply, setDraftReply] = useState(MOCK_EMAILS[0].suggestedReply);
  const [sendConfirmation, setSendConfirmation] = useState(null);

  const handleSelect = (email) => {
    setSelectedEmail(email);
    setDraftReply(email.suggestedReply);
    setSendConfirmation(null);
  };

  const handleSend = () => {
    setSendConfirmation(`Reply dispatched to ${selectedEmail.sender} via Enterprise Mail Gateway.`);
    setTimeout(() => setSendConfirmation(null), 3000);
  };

  return (
    <div className="animate-fade-in" style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
      <SectionHeader
        title="Email Automation & AI Triage"
        description="Automated email classification, entity recognition, priority tagging, and one-click smart response drafting."
        isLive={false}
        badgeText="DEMO / EMAIL AGENT"
      />

      {/* Main Inbox + Email Inspector */}
      <div className="grid-3">
        {/* Left Column: Email List */}
        <div className="card" style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
          <div className="card-header">
            <h3 className="card-title">
              <Inbox size={16} style={{ color: "var(--color-primary)" }} />
              Enterprise Inbox
            </h3>
            <span style={{ fontSize: "11.5px", color: "var(--text-secondary)" }}>{MOCK_EMAILS.length} Messages</span>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
            {MOCK_EMAILS.map((email) => {
              const isSelected = selectedEmail.id === email.id;
              return (
                <div
                  key={email.id}
                  onClick={() => handleSelect(email)}
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
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <span style={{ fontSize: "12px", fontWeight: "600", color: isSelected ? "var(--color-primary)" : "var(--text-primary)" }}>
                      {email.sender}
                    </span>
                    <span style={{ fontSize: "11px", color: "var(--text-secondary)" }}>{email.date}</span>
                  </div>

                  <div style={{ fontSize: "12.5px", fontWeight: "500", color: "var(--text-primary)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                    {email.subject}
                  </div>

                  <div style={{ display: "flex", gap: "6px", marginTop: "2px" }}>
                    <StatusBadge status={email.priority} />
                    <StatusBadge status={email.category} />
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Right 2 Columns: Email Analysis & Smart Reply */}
        <div style={{ gridColumn: "span 2", display: "flex", flexDirection: "column", gap: "16px" }}>
          {/* Email Content & AI Summary */}
          <div className="card">
            <div className="card-header">
              <div>
                <h3 className="card-title">{selectedEmail.subject}</h3>
                <p className="card-subtitle">From: {selectedEmail.sender} • Received {selectedEmail.date}</p>
              </div>
              <StatusBadge status={selectedEmail.status} />
            </div>

            {/* AI Summary Box */}
            <div
              style={{
                backgroundColor: "var(--color-primary-light)",
                border: "1px solid var(--color-primary-border)",
                borderRadius: "var(--radius-md)",
                padding: "12px 14px",
                display: "flex",
                flexDirection: "column",
                gap: "6px",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "12px", fontWeight: "600", color: "var(--color-primary)" }}>
                <Sparkles size={14} />
                AI Executive Summary & Intent
              </div>
              <p style={{ fontSize: "13px", color: "var(--text-primary)", lineHeight: "1.5", margin: 0 }}>
                {selectedEmail.summary}
              </p>
            </div>
          </div>

          {/* Suggested Smart Reply */}
          <div className="card">
            <div className="card-header">
              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <Edit3 size={16} style={{ color: "var(--color-success)" }} />
                <h3 className="card-title">AI Suggested Response (Editable Draft)</h3>
              </div>
              <span className="badge badge-live">Context-Aware</span>
            </div>

            <textarea
              style={{ width: "100%", height: "120px", fontSize: "13px", lineHeight: "1.55" }}
              value={draftReply}
              onChange={(e) => setDraftReply(e.target.value)}
            />

            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: "12px" }}>
              <span style={{ fontSize: "12px", color: "var(--text-secondary)" }}>
                Draft generated from AP ERP Ledger state
              </span>

              <button className="btn btn-primary" onClick={handleSend}>
                <Send size={14} />
                Approve & Send Reply
              </button>
            </div>

            {sendConfirmation && (
              <div style={{ marginTop: "8px", fontSize: "12px", color: "var(--color-success-text)", textAlign: "right" }}>
                {sendConfirmation}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
