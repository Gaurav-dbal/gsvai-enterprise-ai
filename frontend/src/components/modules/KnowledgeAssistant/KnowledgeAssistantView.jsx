import React, { useState, useRef } from "react";
import {
  Search,
  BookOpen,
  FileText,
  Sparkles,
  Filter,
  Upload,
  RefreshCw,
  CheckCircle2,
  AlertCircle,
} from "lucide-react";
import { SectionHeader } from "../../common/SectionHeader";
import { StatusBadge } from "../../common/Badge";
import { sendChatMessage, uploadDocument } from "../../../api/client";

const MOCK_COLLECTIONS = [
  "All Repositories",
  "Legal & Compliance",
  "Procurement & Invoicing",
  "HR & Governance",
  "Cloud Infrastructure",
];

const INITIAL_DOCS = [
  {
    id: 1,
    document_id: 1,
    name: "Enterprise_SLA_Master_Agreement.pdf",
    category: "Legal & Compliance",
    pages: 32,
    chunks: 48,
    status: "Indexed",
    lastUpdated: "Yesterday",
  },
  {
    id: 2,
    document_id: 2,
    name: "Procurement_Governance_Policy_2026.pdf",
    category: "Procurement & Invoicing",
    pages: 48,
    chunks: 72,
    status: "Indexed",
    lastUpdated: "3 days ago",
  },
  {
    id: 3,
    document_id: 3,
    name: "OCI_Cloud_Security_Standards_v2.pdf",
    category: "Cloud Infrastructure",
    pages: 74,
    chunks: 110,
    status: "Indexed",
    lastUpdated: "Aug 18, 2026",
  },
  {
    id: 4,
    document_id: 4,
    name: "Global_Vendor_Onboarding_Manual.pdf",
    category: "HR & Governance",
    pages: 22,
    chunks: 35,
    status: "Indexed",
    lastUpdated: "Aug 12, 2026",
  },
];

export function KnowledgeAssistantView() {
  const [selectedCollection, setSelectedCollection] = useState("All Repositories");
  const [searchQuery, setSearchQuery] = useState("");
  const [activeQuestion, setActiveQuestion] = useState(
    "How do I create a supplier invoice in Oracle Fusion Payables?"
  );
  const [displayedAnswer, setDisplayedAnswer] = useState({
    question: "How do I create a supplier invoice in Oracle Fusion Payables?",
    answer:
      "To create a supplier invoice in Oracle Fusion Payables, navigate to the Payables Work Area and select Invoices > Create Invoice. Enter required header fields including Business Unit, Supplier, Invoice Number, and Amount, then enter line item distribution details matching the associated Purchase Order for automated 3-way matching validation.",
    confidence: "OCI Vector Match",
    citations: [
      {
        id: 1,
        docName: "Procurement_Governance_Policy_2026.pdf",
        page: 14,
        relevance: "99%",
        snippet:
          "...invoices exceeding $50,000 USD require secondary sign-off by the relevant Cost Center Director and 3-way matching in Oracle Fusion...",
      },
    ],
  });

  const [isSearching, setIsSearching] = useState(false);
  const [searchError, setSearchError] = useState(null);

  // PDF Upload & Indexing state
  const [indexedDocs, setIndexedDocs] = useState(INITIAL_DOCS);
  const [uploadProgressState, setUploadProgressState] = useState(null); // 'Uploading...' | 'Processing PDF...' | 'Creating embeddings...' | 'Indexing in Oracle...' | 'Indexed successfully.'
  const [uploadError, setUploadError] = useState(null);
  const fileInputRef = useRef(null);

  // Handle Real Knowledge Search via POST /chat
  const handleAsk = async () => {
    const query = searchQuery.trim();
    if (!query || isSearching) return;

    setIsSearching(true);
    setSearchError(null);
    setActiveQuestion(query);

    try {
      // Real API call to FastAPI backend POST /chat -> Oracle Vector Semantic Search + OCI Cohere LLM
      const response = await sendChatMessage(query);
      
      setDisplayedAnswer({
        question: query,
        answer: response.answer || "No response received from RAG pipeline.",
        confidence: "Live OCI Vector RAG",
        citations: [
          {
            id: Date.now(),
            docName: "Oracle Vector Knowledge Base",
            page: 1,
            relevance: "Top Similarity",
            snippet: "Retrieved via cosine distance ranking in GSVAI_DOCUMENT_CHUNKS vector table.",
          },
        ],
      });
    } catch (err) {
      console.error("Knowledge Assistant Search Error:", err);
      const errMsg = err.message || "Failed to communicate with FastAPI backend.";
      setSearchError(errMsg);
      setDisplayedAnswer({
        question: query,
        answer: `⚠️ **Connection Error**: Could not retrieve response from backend.\n\n*Details*: \`${errMsg}\`\n\nPlease ensure the FastAPI server is running on \`http://127.0.0.1:8000\`.`,
        confidence: "Disconnected",
        citations: [],
      });
    } finally {
      setIsSearching(false);
    }
  };

  // Trigger file picker
  const handleUploadButtonClick = () => {
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
      fileInputRef.current.click();
    }
  };

  // Handle PDF file selection & upload
  const handleFileChange = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (!file.name.toLowerCase().endsWith(".pdf")) {
      setUploadError("Only PDF files (.pdf) are supported.");
      setTimeout(() => setUploadError(null), 4000);
      return;
    }

    setUploadError(null);
    setUploadProgressState("Uploading...");

    // Simulated progress stage transitions while backend processes
    const t1 = setTimeout(() => setUploadProgressState("Processing PDF..."), 600);
    const t2 = setTimeout(() => setUploadProgressState("Creating embeddings..."), 1200);
    const t3 = setTimeout(() => setUploadProgressState("Indexing in Oracle..."), 1800);

    try {
      // Real API call: POST /documents/upload
      const result = await uploadDocument(file);

      clearTimeout(t1);
      clearTimeout(t2);
      clearTimeout(t3);

      setUploadProgressState("Indexed successfully.");

      const newDoc = {
        id: result.document_id || Date.now(),
        document_id: result.document_id || Math.floor(Math.random() * 900) + 100,
        name: result.filename || file.name,
        category: selectedCollection === "All Repositories" ? "Enterprise Documents" : selectedCollection,
        pages: result.pages || 1,
        chunks: result.chunks || 1,
        status: "Indexed",
        lastUpdated: "Just now",
      };

      setIndexedDocs((prev) => [newDoc, ...prev]);

      setTimeout(() => {
        setUploadProgressState(null);
      }, 4000);
    } catch (err) {
      clearTimeout(t1);
      clearTimeout(t2);
      clearTimeout(t3);
      console.error("Document upload failed:", err);
      setUploadProgressState(null);
      setUploadError(err.message || "Failed to upload and index document.");
      setTimeout(() => setUploadError(null), 5000);
    }
  };

  return (
    <div className="animate-fade-in" style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
      <SectionHeader
        title="Knowledge Assistant (Enterprise RAG)"
        description="Semantic question answering over indexed enterprise documentation and compliance policies with verbatim source citations."
        isLive={true}
        badgeText="LIVE OCI + ORACLE VECTOR RAG"
      />

      {/* Hidden File Input for PDF Upload */}
      <input
        ref={fileInputRef}
        type="file"
        accept=".pdf,application/pdf"
        style={{ display: "none" }}
        onChange={handleFileChange}
      />

      {/* Search & Collection Selector */}
      <div className="card" style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
        <div style={{ display: "flex", gap: "10px", alignItems: "center", flexWrap: "wrap" }}>
          <div style={{ display: "flex", gap: "6px", alignItems: "center" }}>
            <Filter size={14} style={{ color: "var(--text-secondary)" }} />
            <span style={{ fontSize: "12px", color: "var(--text-secondary)", fontWeight: "500" }}>Repository:</span>
          </div>

          <div style={{ display: "flex", gap: "6px", flexWrap: "wrap" }}>
            {MOCK_COLLECTIONS.map((c) => (
              <button
                key={c}
                onClick={() => setSelectedCollection(c)}
                style={{
                  fontSize: "12px",
                  padding: "3px 10px",
                  borderRadius: "var(--radius-sm)",
                  backgroundColor: selectedCollection === c ? "var(--color-primary)" : "var(--bg-surface-subtle)",
                  color: selectedCollection === c ? "#FFFFFF" : "var(--text-secondary)",
                  border: `1px solid ${selectedCollection === c ? "var(--color-primary)" : "var(--border-subtle)"}`,
                  fontWeight: selectedCollection === c ? "600" : "500",
                }}
              >
                {c}
              </button>
            ))}
          </div>
        </div>

        {/* Input bar */}
        <div style={{ display: "flex", gap: "10px" }}>
          <div style={{ position: "relative", flex: 1 }}>
            <Search size={16} style={{ position: "absolute", left: "12px", top: "13px", color: "var(--text-muted)" }} />
            <input
              type="text"
              style={{ width: "100%", height: "42px", paddingLeft: "38px" }}
              placeholder="Ask a question across enterprise documents (e.g. How do I create a supplier invoice?)..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleAsk()}
              disabled={isSearching}
            />
          </div>
          <button
            className="btn btn-primary"
            onClick={handleAsk}
            style={{ padding: "0 20px" }}
            disabled={!searchQuery.trim() || isSearching}
          >
            {isSearching ? <RefreshCw size={15} className="animate-spin" /> : <Sparkles size={15} />}
            {isSearching ? "Searching..." : "Search Knowledge"}
          </button>
        </div>
      </div>

      {/* Main Content: Answer + Citations & Doc Index */}
      <div className="grid-3">
        {/* Answer Area (2 cols) */}
        <div style={{ gridColumn: "span 2", display: "flex", flexDirection: "column", gap: "16px" }}>
          <div className="card">
            <div className="card-header">
              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <div style={{ width: "28px", height: "28px", borderRadius: "var(--radius-sm)", background: "var(--color-primary-light)", display: "flex", alignItems: "center", justifyContent: "center", color: "var(--color-primary)" }}>
                  <Sparkles size={15} />
                </div>
                <div>
                  <h3 className="card-title">AI Synthesized Knowledge Response</h3>
                  <p className="card-subtitle">Question: "{activeQuestion}"</p>
                </div>
              </div>
              <span style={{ fontSize: "11px", fontWeight: "600", color: "var(--color-success-text)", background: "var(--color-success-bg)", border: "1px solid var(--color-success-border)", padding: "2px 8px", borderRadius: "var(--radius-sm)" }}>
                {displayedAnswer.confidence}
              </span>
            </div>

            {isSearching ? (
              <div style={{ display: "flex", alignItems: "center", gap: "10px", padding: "16px 0", color: "var(--text-secondary)" }}>
                <RefreshCw size={16} className="animate-spin" style={{ color: "var(--color-primary)" }} />
                <span style={{ fontSize: "13.5px" }}>
                  Performing semantic vector search and synthesizing answer with OCI Cohere...
                </span>
              </div>
            ) : (
              <div style={{ fontSize: "13.5px", lineHeight: "1.65", color: "var(--text-primary)", whiteSpace: "pre-wrap", padding: "4px 0" }}>
                {displayedAnswer.answer}
              </div>
            )}
          </div>

          {/* Citations & Source Evidence */}
          <div className="card">
            <div className="card-header">
              <h3 className="card-title">
                <BookOpen size={16} style={{ color: "var(--color-info-text)" }} />
                Source Citations & Evidentiary Excerpts
              </h3>
              <span style={{ fontSize: "11.5px", color: "var(--text-secondary)" }}>
                {displayedAnswer.citations.length} Sources
              </span>
            </div>

            {displayedAnswer.citations.length === 0 ? (
              <div style={{ fontSize: "12.5px", color: "var(--text-secondary)", fontStyle: "italic", padding: "6px 0" }}>
                No explicit citations available for this query.
              </div>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
                {displayedAnswer.citations.map((cite) => (
                  <div
                    key={cite.id}
                    style={{
                      backgroundColor: "var(--bg-surface-subtle)",
                      border: "1px solid var(--border-subtle)",
                      borderRadius: "var(--radius-md)",
                      padding: "12px 14px",
                      display: "flex",
                      flexDirection: "column",
                      gap: "6px",
                    }}
                  >
                    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                      <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                        <FileText size={14} style={{ color: "var(--color-primary)" }} />
                        <span style={{ fontSize: "12.5px", fontWeight: "600", color: "var(--text-primary)" }}>
                          {cite.docName}
                        </span>
                        {cite.page && (
                          <span style={{ fontSize: "11px", color: "var(--text-secondary)", backgroundColor: "#FFFFFF", border: "1px solid var(--border-subtle)", padding: "1px 6px", borderRadius: "var(--radius-sm)" }}>
                            Page {cite.page}
                          </span>
                        )}
                      </div>
                      <span style={{ fontSize: "11px", color: "var(--color-success-text)", fontWeight: "600" }}>
                        {cite.relevance}
                      </span>
                    </div>

                    <p style={{ fontSize: "12.5px", color: "var(--text-secondary)", fontStyle: "italic", borderLeft: "2px solid var(--color-primary)", paddingLeft: "8px", margin: 0 }}>
                      "{cite.snippet}"
                    </p>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Right column: Document Repository with PDF Upload Button */}
        <div className="card" style={{ height: "fit-content", display: "flex", flexDirection: "column", gap: "12px" }}>
          <div className="card-header" style={{ marginBottom: "4px" }}>
            <h3 className="card-title">
              <FileText size={16} style={{ color: "var(--color-primary)" }} />
              Indexed Documents
            </h3>
            
            {/* Small Upload PDF Button */}
            <button
              className="btn btn-secondary"
              style={{ padding: "4px 8px", fontSize: "11.5px" }}
              onClick={handleUploadButtonClick}
              title="Upload and index a PDF in Oracle Vector"
            >
              <Upload size={13} style={{ color: "var(--color-primary)" }} />
              Upload PDF
            </button>
          </div>

          {/* Upload Progress Status Banner */}
          {uploadProgressState && (
            <div
              style={{
                backgroundColor: uploadProgressState.includes("successfully")
                  ? "var(--color-success-bg)"
                  : "var(--color-primary-light)",
                border: `1px solid ${
                  uploadProgressState.includes("successfully")
                    ? "var(--color-success-border)"
                    : "var(--color-primary-border)"
                }`,
                borderRadius: "var(--radius-md)",
                padding: "8px 10px",
                fontSize: "12px",
                display: "flex",
                alignItems: "center",
                gap: "8px",
                color: uploadProgressState.includes("successfully")
                  ? "var(--color-success-text)"
                  : "var(--color-primary)",
              }}
            >
              {uploadProgressState.includes("successfully") ? (
                <CheckCircle2 size={15} />
              ) : (
                <RefreshCw size={14} className="animate-spin" />
              )}
              <span style={{ fontWeight: "500" }}>{uploadProgressState}</span>
            </div>
          )}

          {/* Upload Error Banner */}
          {uploadError && (
            <div
              style={{
                backgroundColor: "var(--color-danger-bg)",
                border: "1px solid var(--color-danger-border)",
                borderRadius: "var(--radius-md)",
                padding: "8px 10px",
                fontSize: "12px",
                display: "flex",
                alignItems: "center",
                gap: "8px",
                color: "var(--color-danger-text)",
              }}
            >
              <AlertCircle size={15} />
              <span>{uploadError}</span>
            </div>
          )}

          {/* Documents List */}
          <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
            {indexedDocs.map((doc) => (
              <div
                key={doc.id}
                style={{
                  padding: "9px 11px",
                  borderRadius: "var(--radius-md)",
                  backgroundColor: "var(--bg-surface-subtle)",
                  border: "1px solid var(--border-subtle)",
                  display: "flex",
                  flexDirection: "column",
                  gap: "4px",
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "6px" }}>
                  <div
                    style={{
                      fontSize: "12.5px",
                      fontWeight: "600",
                      color: "var(--text-primary)",
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                      whiteSpace: "nowrap",
                      flex: 1,
                    }}
                    title={doc.name}
                  >
                    {doc.name}
                  </div>
                  <StatusBadge status={doc.status || "Indexed"} />
                </div>

                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    fontSize: "11px",
                    color: "var(--text-secondary)",
                  }}
                >
                  <span style={{ fontFamily: "var(--font-mono)", color: "var(--color-primary)" }}>
                    Doc #{doc.document_id || doc.id}
                  </span>
                  <div style={{ display: "flex", gap: "8px" }}>
                    <span>{doc.pages} pgs</span>
                    {doc.chunks && <span>• {doc.chunks} chunks</span>}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
