import React, { useState, useRef, useEffect, useCallback } from "react";
import {
  Bot,
  Send,
  User,
  Sparkles,
  Copy,
  Check,
  RefreshCw,
  Trash2,
  UploadCloud,
  FileText,
  CheckCircle2,
  MinusCircle,
  AlertCircle,
  ChevronDown,
  ChevronUp,
  X,
  BookOpen,
  Layers,
  Search,
  Clock,
  FileCheck,
  Database,
  Info,
} from "lucide-react";
import { SectionHeader } from "../../common/SectionHeader";
import {
  sendAIWorkspaceChat,
  uploadWorkspaceDocument,
  fetchAIWorkspaceDocuments,
} from "../../../api/client";

const GENERAL_SUGGESTIONS = [
  "What is Generative AI and how does it transform enterprise workflows?",
  "How do I create a supplier invoice in Oracle Fusion Payables?",
  "Summarize the documents uploaded today.",
  "Which documents discuss procurement and vendor approval?",
];

const DOC_SUGGESTIONS = [
  "Summarize this document.",
  "What is the target salary mentioned in this document?",
  "What are the core milestones and timelines?",
  "Explain the key responsibilities described in this document.",
];

// =========================================================
// AI Execution Trace Component (Educational Telemetry)
// =========================================================
function AIExecutionTrace({ trace, isExpanded, onToggleExpand, isLoading }) {
  if (!trace && !isLoading) return null;

  if (isLoading) {
    return (
      <div className="ai-execution-trace-container loading">
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "7px 12px", fontSize: "12px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "8px", color: "var(--color-primary)" }}>
            <RefreshCw size={13} className="animate-spin" />
            <span style={{ fontWeight: "600" }}>AI Execution Trace</span>
            <span style={{ color: "var(--text-muted)", fontSize: "11px" }}>• Tracing pipeline execution in real-time...</span>
          </div>
        </div>
      </div>
    );
  }

  const { steps = [], total_duration_ms = 0, route_label, rag_used, query } = trace;
  const formattedDuration = total_duration_ms >= 1000 
    ? `${(total_duration_ms / 1000).toFixed(2)}s` 
    : `${Math.round(total_duration_ms)}ms`;

  return (
    <div className="ai-execution-trace-container">
      {/* Compact Header Bar */}
      <div 
        className="ai-execution-trace-header"
        onClick={onToggleExpand}
        title="Click to expand/collapse full execution breakdown"
      >
        <div style={{ display: "flex", alignItems: "center", gap: "8px", flexWrap: "wrap" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "5px", color: "var(--color-primary)", fontWeight: "700", fontSize: "12.5px" }}>
            <Sparkles size={14} />
            <span>AI Execution Trace</span>
          </div>
          <span style={{ color: "var(--text-muted)", fontSize: "11.5px" }}>•</span>
          <span style={{ color: "var(--text-secondary)", fontSize: "11.5px", fontWeight: "500" }}>
            {steps.length} steps • {formattedDuration}
          </span>
          {route_label && (
            <span className="trace-route-badge">
              {route_label}
            </span>
          )}
          <span className={`trace-rag-badge ${rag_used ? "rag-on" : "rag-off"}`}>
            {rag_used ? "RAG: USED" : "RAG: NOT USED"}
          </span>
        </div>

        <button
          type="button"
          className="trace-toggle-btn"
          onClick={(e) => {
            e.stopPropagation();
            onToggleExpand();
          }}
        >
          <span>{isExpanded ? "Hide details" : "View details"}</span>
          {isExpanded ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
        </button>
      </div>

      {/* Expanded Educational Trace Flow */}
      {isExpanded && (
        <div className="ai-execution-trace-details">
          {query && (
            <div className="trace-query-banner">
              <span style={{ fontWeight: "600", color: "var(--text-secondary)" }}>Query:</span>
              <span style={{ color: "var(--text-primary)", fontStyle: "italic" }}>"{query}"</span>
            </div>
          )}

          <div className="trace-steps-list">
            {steps.map((stepItem) => {
              const isCompleted = stepItem.status === "completed";
              const isSkipped = stepItem.status === "skipped";
              const isFailed = stepItem.status === "failed";

              return (
                <div key={stepItem.step} className={`trace-step-item ${stepItem.status}`}>
                  <div className="trace-step-indicator">
                    <span className="trace-step-num">{stepItem.step}.</span>
                    {isCompleted && <CheckCircle2 size={14} style={{ color: "var(--color-success-text)" }} />}
                    {isSkipped && <MinusCircle size={14} style={{ color: "var(--text-muted)" }} />}
                    {isFailed && <AlertCircle size={14} style={{ color: "var(--color-danger-text)" }} />}
                  </div>

                  <div className="trace-step-content">
                    <div className="trace-step-header-row">
                      <span className="trace-step-name" style={{ color: isSkipped ? "var(--text-muted)" : "var(--text-primary)" }}>
                        {stepItem.name}
                      </span>
                      <span className="trace-step-duration" style={{ color: isSkipped ? "var(--text-muted)" : "var(--text-secondary)" }}>
                        {isSkipped ? "SKIPPED" : `${stepItem.duration_ms} ms`}
                      </span>
                    </div>

                    {stepItem.explanation && (
                      <div className="trace-step-explanation">
                        "{stepItem.explanation}"
                      </div>
                    )}

                    {stepItem.details && Object.keys(stepItem.details).length > 0 && (
                      <div className="trace-step-details-grid">
                        {Object.entries(stepItem.details).map(([key, val]) => {
                          if (val === null || val === undefined) return null;
                          let displayVal = typeof val === "object" ? JSON.stringify(val) : String(val);
                          const cleanKey = key.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
                          return (
                            <div key={key} className="trace-detail-tag">
                              <span className="trace-detail-key">{cleanKey}:</span>
                              <span className="trace-detail-val">{displayVal}</span>
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

export function AIWorkspaceView({ backendStatus, backendLatency }) {
  const [messages, setMessages] = useState([
    {
      id: "welcome-1",
      sender: "assistant",
      text: "Welcome to **GSVAI AI Workspace** — your unified enterprise intelligence environment.\n\nHere you can:\n- **Ask general AI questions** powered by OCI Generative AI (Cohere Command A).\n- **Upload documents** for instant OCI OCR extraction, entity parsing, and Oracle Vector DB indexing.\n- **Select a document** from the right panel to ask document-specific questions or request executive summaries.\n- **Search across All Documents** to synthesize insights across your enterprise repository.",
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      sourceType: "general_ai",
    },
  ]);

  const [inputQuery, setInputQuery] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadStage, setUploadStage] = useState(null); // 'uploading' | 'ocr' | 'indexing' | 'ready' | 'failed'
  const [uploadError, setUploadError] = useState(null);
  const [lastUploadPipeline, setLastUploadPipeline] = useState(null);
  
  const [documents, setDocuments] = useState([]);
  const [isLoadingDocs, setIsLoadingDocs] = useState(false);
  const [docSearchQuery, setDocSearchQuery] = useState("");
  const [activeDocument, setActiveDocument] = useState(null); // null means "All Documents / General AI"
  const [showDocInsights, setShowDocInsights] = useState(false);
  
  // Real-time AI Execution Trace state
  const [currentTrace, setCurrentTrace] = useState(null);
  const [isTraceExpanded, setIsTraceExpanded] = useState(false);

  const [copiedId, setCopiedId] = useState(null);
  const [errorMessage, setErrorMessage] = useState(null);

  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);
  const fileInputRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading, isUploading]);

  // Load documents from backend
  const loadDocuments = useCallback(async () => {
    setIsLoadingDocs(true);
    try {
      const docs = await fetchAIWorkspaceDocuments();
      setDocuments(docs);
    } catch (err) {
      console.error("Failed to load workspace documents:", err);
    } finally {
      setIsLoadingDocs(false);
    }
  }, []);

  useEffect(() => {
    loadDocuments();
  }, [loadDocuments]);

  // Handle Sending a Question in the Unified Workspace Chat
  const handleSendMessage = async (textToSend, forcedQueryMode = null) => {
    const query = (textToSend || inputQuery).trim();
    if (!query || isLoading || isUploading) return;

    setErrorMessage(null);
    setCurrentTrace({ isLoading: true, query });
    const userMsgId = `user-${Date.now()}`;
    const userMsg = {
      id: userMsgId,
      sender: "user",
      text: query,
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      documentContext: activeDocument ? activeDocument.document_name || activeDocument.filename : null,
    };

    setMessages((prev) => [...prev, userMsg]);
    setInputQuery("");
    setIsLoading(true);

    try {
      const docId = activeDocument ? activeDocument.document_id : null;
      const scope = activeDocument ? "document" : "all";
      const mode = forcedQueryMode || (activeDocument && query.toLowerCase().includes("summarize") ? "summary" : null);

      const response = await sendAIWorkspaceChat(
        query,
        docId,
        scope,
        mode
      );

      // Attach actual real-time execution trace from backend
      if (response.trace) {
        setCurrentTrace(response.trace);
      }

      const assistantMsg = {
        id: `assistant-${Date.now()}`,
        sender: "assistant",
        text: response.answer || "No response generated.",
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        sourceType: response.source_type || (activeDocument ? "document_context" : "general_ai"),
        sources: response.sources || [],
      };

      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err) {
      console.error("AI Workspace Chat Error:", err);
      const errMsg = err.message || "Failed to communicate with backend.";
      setErrorMessage(errMsg);

      // Update trace with safe error telemetry
      setCurrentTrace({
        enabled: true,
        query,
        route: "ERROR",
        route_label: "Request Failed",
        rag_used: false,
        total_duration_ms: 0,
        steps: [
          {
            step: 1,
            name: "Query Received",
            status: "completed",
            duration_ms: 1,
            explanation: "User query was received by the client.",
            details: { query }
          },
          {
            step: 2,
            name: "AI Workspace API",
            status: "failed",
            duration_ms: 0,
            explanation: `API request failed: ${errMsg}`,
            details: { error: errMsg }
          }
        ]
      });

      const errorBotMsg = {
        id: `error-${Date.now()}`,
        sender: "assistant",
        isError: true,
        text: `⚠️ **Error**: Could not retrieve response from backend.\n\n*Details*: \`${errMsg}\``,
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      };
      setMessages((prev) => [...prev, errorBotMsg]);
    } finally {
      setIsLoading(false);
      setTimeout(() => inputRef.current?.focus(), 100);
    }
  };

  // Handle Document Upload & Processing Pipeline
  const handleFileUpload = async (file) => {
    if (!file) return;

    if (!file.name.toLowerCase().endsWith(".pdf")) {
      setErrorMessage("Only PDF files (.pdf) are supported for AI Workspace.");
      setTimeout(() => setErrorMessage(null), 4000);
      return;
    }

    setErrorMessage(null);
    setUploadError(null);
    setIsUploading(true);
    setUploadStage("uploading");
    setLastUploadPipeline(null);

    // Realistic progressive stage cues
    const t1 = setTimeout(() => setUploadStage("ocr"), 1200);
    const t2 = setTimeout(() => setUploadStage("indexing"), 3500);

    try {
      const result = await uploadWorkspaceDocument(file);

      clearTimeout(t1);
      clearTimeout(t2);
      setUploadStage("ready");

      const docInfo = {
        document_id: result.document_id,
        analysis_id: result.analysis_id,
        document_name: result.filename || file.name,
        filename: result.filename || file.name,
        document_type: result.document_type || "PDF",
        page_count: result.pages || 1,
        pages: result.pages || 1,
        text_pages: result.text_pages || 1,
        chunk_count: result.chunks || 1,
        chunks: result.chunks || 1,
        ocr_status: result.ocr_status || "completed",
        status: result.indexing_status || "INDEXED",
        entities: result.entities || [],
        tables: result.tables || [],
        full_text: result.full_text || "",
        preview: result.extracted_text_preview || "",
        formatted_date: "Just now",
        pipeline: result.pipeline || {},
      };

      setLastUploadPipeline(result.pipeline || {});
      setActiveDocument(docInfo);

      // Refresh documents list from backend
      await loadDocuments();

      // Add system confirmation card to chat
      const uploadEventMsg = {
        id: `doc-event-${Date.now()}`,
        sender: "system_doc",
        document: docInfo,
        text: `📄 **Document Ingested & Indexed Successfully**\n\n**${docInfo.document_name}** (${docInfo.page_count} pages, ${docInfo.chunk_count} chunks)\n- **OCI Document Understanding OCR**: Completed\n- **Entity Extraction**: ${docInfo.pipeline?.key_value_extraction || "Completed"}\n- **Oracle Vector Knowledge Indexing**: Ready for Grounded Q&A\n\nActive context set to **${docInfo.document_name}**. You can now ask questions about this document or request a summary.`,
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      };

      setMessages((prev) => [...prev, uploadEventMsg]);
    } catch (err) {
      clearTimeout(t1);
      clearTimeout(t2);
      console.error("Document Processing Error:", err);
      setUploadStage("failed");
      setUploadError(err.message || "Failed to process and index document.");
      setErrorMessage(err.message || "Failed to process and index document.");
    } finally {
      setIsUploading(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const handleCopyText = (id, text) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const handleClearHistory = () => {
    setCurrentTrace(null);
    setIsTraceExpanded(false);
    setMessages([
      {
        id: `welcome-${Date.now()}`,
        sender: "assistant",
        text: "Conversation reset. Ask anything about enterprise knowledge, uploaded documents, or general AI.",
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        sourceType: "general_ai",
      },
    ]);
    setActiveDocument(null);
    setShowDocInsights(false);
    setErrorMessage(null);
  };

  // Filter documents by search
  const filteredDocuments = documents.filter((doc) =>
    (doc.document_name || "").toLowerCase().includes(docSearchQuery.toLowerCase())
  );

  return (
    <div className="animate-fade-in" style={{ display: "flex", flexDirection: "column", height: "100%", gap: "14px" }}>
      {/* Hidden File Input */}
      <input
        ref={fileInputRef}
        type="file"
        accept=".pdf"
        style={{ display: "none" }}
        onChange={(e) => {
          if (e.target.files && e.target.files[0]) {
            handleFileUpload(e.target.files[0]);
          }
          e.target.value = "";
        }}
      />

      {/* Header */}
      <SectionHeader
        title="GSVAI AI Workspace"
        description="Unified Enterprise Intelligence: General AI + Document Understanding OCR + Oracle Vector RAG."
        isLive={true}
        badgeText="LIVE UNIFIED WORKSPACE"
        actions={
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <button
              className="btn btn-secondary"
              onClick={handleClearHistory}
              title="Clear conversation history"
            >
              <Trash2 size={14} />
              Clear Chat
            </button>
            <button
              className="btn btn-secondary"
              onClick={loadDocuments}
              disabled={isLoadingDocs}
              title="Refresh Document Repository"
            >
              <RefreshCw size={14} className={isLoadingDocs ? "animate-spin" : ""} />
              Refresh
            </button>
          </div>
        }
      />

      {/* Error Alert */}
      {errorMessage && (
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "8px",
            padding: "10px 14px",
            borderRadius: "var(--radius-md)",
            backgroundColor: "var(--color-danger-bg)",
            border: "1px solid var(--color-danger-border)",
            color: "var(--color-danger-text)",
            fontSize: "13px",
          }}
        >
          <AlertCircle size={16} style={{ flexShrink: 0 }} />
          <span>{errorMessage}</span>
          <button
            onClick={() => setErrorMessage(null)}
            style={{ marginLeft: "auto", background: "none", color: "inherit", padding: "2px" }}
          >
            <X size={14} />
          </button>
        </div>
      )}

      {/* Unified Split Workspace Container */}
      <div style={{ display: "flex", gap: "16px", flex: 1, minHeight: 0 }}>
        
        {/* ========================================================= */}
        {/* LEFT / MAIN AREA: AI Conversation & Grounded Citations   */}
        {/* ========================================================= */}
        <div
          style={{
            flex: 1,
            display: "flex",
            flexDirection: "column",
            minWidth: 0,
            height: "100%",
          }}
        >
          <div className="chat-container" style={{ height: "100%", display: "flex", flexDirection: "column" }}>
            
            {/* Active Context Banner */}
            <div
              style={{
                padding: "8px 16px",
                backgroundColor: activeDocument ? "var(--color-primary-light)" : "var(--bg-surface-subtle)",
                borderBottom: "1px solid var(--border-subtle)",
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                fontSize: "12px",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: "8px", overflow: "hidden" }}>
                {activeDocument ? (
                  <>
                    <FileText size={15} style={{ color: "var(--color-primary)", flexShrink: 0 }} />
                    <span style={{ color: "var(--text-secondary)" }}>Active Context:</span>
                    <strong
                      style={{
                        color: "var(--text-primary)",
                        whiteSpace: "nowrap",
                        overflow: "hidden",
                        textOverflow: "ellipsis",
                        maxWidth: "280px",
                      }}
                      title={activeDocument.document_name || activeDocument.filename}
                    >
                      {activeDocument.document_name || activeDocument.filename}
                    </strong>
                    <span
                      style={{
                        backgroundColor: "var(--color-primary)",
                        color: "#FFFFFF",
                        padding: "1px 6px",
                        borderRadius: "var(--radius-xs)",
                        fontSize: "10px",
                        fontWeight: "600",
                      }}
                    >
                      DOCUMENT RAG
                    </span>
                  </>
                ) : (
                  <>
                    <Database size={15} style={{ color: "var(--color-success-text)", flexShrink: 0 }} />
                    <span style={{ color: "var(--text-secondary)" }}>Active Context:</span>
                    <strong style={{ color: "var(--text-primary)" }}>
                      All Documents / General Enterprise Knowledge
                    </strong>
                  </>
                )}
              </div>

              {activeDocument && (
                <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                  <button
                    className="btn btn-secondary"
                    style={{ fontSize: "11px", padding: "2px 8px", height: "24px" }}
                    onClick={() => handleSendMessage("Summarize this document.", "summary")}
                    disabled={isLoading || isUploading}
                    title="Generate executive summary of active document"
                  >
                    <Sparkles size={11} style={{ color: "var(--color-primary)" }} />
                    Summarize
                  </button>
                  <button
                    className="btn btn-secondary"
                    style={{ fontSize: "11px", padding: "2px 6px", height: "24px" }}
                    onClick={() => {
                      setActiveDocument(null);
                      setShowDocInsights(false);
                    }}
                    title="Switch to All Documents"
                  >
                    <X size={12} />
                    All Docs
                  </button>
                </div>
              )}
            </div>

            {/* Messages Scroll Area */}
            <div className="chat-messages" style={{ flex: 1, overflowY: "auto", padding: "18px" }}>
              {messages.map((msg) => {
                const isUser = msg.sender === "user";
                const isSystemDoc = msg.sender === "system_doc";
                const isCopied = copiedId === msg.id;

                if (isSystemDoc) {
                  return (
                    <div key={msg.id} style={{ display: "flex", justifyContent: "center", margin: "6px 0" }}>
                      <div
                        style={{
                          backgroundColor: "var(--color-primary-light)",
                          border: "1px solid var(--color-primary-border)",
                          borderRadius: "var(--radius-md)",
                          padding: "10px 16px",
                          maxWidth: "88%",
                          fontSize: "12px",
                          lineHeight: "1.5",
                          color: "var(--text-primary)",
                          display: "flex",
                          flexDirection: "column",
                          gap: "4px",
                        }}
                      >
                        <div style={{ whiteSpace: "pre-wrap" }}>{msg.text}</div>
                        <div style={{ fontSize: "10.5px", color: "var(--text-muted)", textAlign: "right" }}>
                          {msg.timestamp}
                        </div>
                      </div>
                    </div>
                  );
                }

                return (
                  <div key={msg.id} className={`chat-bubble-row ${isUser ? "user" : "assistant"}`}>
                    <div className={`chat-avatar ${isUser ? "user" : "assistant"}`}>
                      {isUser ? <User size={15} /> : <Bot size={15} />}
                    </div>

                    <div style={{ display: "flex", flexDirection: "column", gap: "5px", maxWidth: "100%" }}>
                      <div className={`chat-bubble ${isUser ? "user" : "assistant"}`}>
                        <div style={{ whiteSpace: "pre-wrap", wordBreak: "break-word" }}>
                          {msg.text}
                        </div>

                        {/* Source Citations & Evidence */}
                        {!isUser && msg.sources && msg.sources.length > 0 && (
                          <div
                            style={{
                              marginTop: "12px",
                              paddingTop: "10px",
                              borderTop: "1px solid rgba(0, 0, 0, 0.08)",
                              display: "flex",
                              flexDirection: "column",
                              gap: "8px",
                            }}
                          >
                            <div
                              style={{
                                fontSize: "11.5px",
                                fontWeight: "700",
                                color: "var(--color-primary)",
                                display: "flex",
                                alignItems: "center",
                                gap: "5px",
                              }}
                            >
                              <BookOpen size={13} />
                              <span>Sources & Verbatim Citations ({msg.sources.length}):</span>
                            </div>

                            <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                              {msg.sources.map((src, sIdx) => (
                                <div
                                  key={sIdx}
                                  style={{
                                    backgroundColor: "rgba(255, 255, 255, 0.85)",
                                    border: "1px solid var(--border-subtle)",
                                    borderRadius: "var(--radius-sm)",
                                    padding: "6px 10px",
                                    fontSize: "11.5px",
                                  }}
                                >
                                  <div
                                    style={{
                                      fontWeight: "600",
                                      color: "var(--text-primary)",
                                      display: "flex",
                                      justifyContent: "space-between",
                                      alignItems: "center",
                                      fontSize: "11.5px",
                                    }}
                                  >
                                    <span style={{ display: "flex", alignItems: "center", gap: "4px" }}>
                                      📄 {src.document_name || "Enterprise Document"}
                                    </span>
                                    {src.page_number && (
                                      <span
                                        style={{
                                          color: "var(--color-primary)",
                                          backgroundColor: "var(--color-primary-light)",
                                          padding: "1px 6px",
                                          borderRadius: "var(--radius-xs)",
                                          fontSize: "10.5px",
                                        }}
                                      >
                                        Page {src.page_number}
                                      </span>
                                    )}
                                  </div>

                                  {src.text && (
                                    <div
                                      style={{
                                        fontSize: "11px",
                                        color: "var(--text-secondary)",
                                        marginTop: "4px",
                                        fontStyle: "italic",
                                        whiteSpace: "pre-wrap",
                                        borderLeft: "2px solid var(--color-primary-border)",
                                        paddingLeft: "6px",
                                      }}
                                    >
                                      "{src.text.length > 220 ? src.text.slice(0, 220) + "..." : src.text}"
                                    </div>
                                  )}
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>

                      {/* Message Meta / Badges */}
                      <div
                        style={{
                          display: "flex",
                          alignItems: "center",
                          gap: "8px",
                          fontSize: "11px",
                          color: "var(--text-muted)",
                          padding: "0 4px",
                          justifyContent: isUser ? "flex-end" : "flex-start",
                        }}
                      >
                        <span>{msg.timestamp}</span>

                        {isUser && msg.documentContext && (
                          <span
                            style={{
                              fontSize: "10px",
                              padding: "1px 6px",
                              borderRadius: "var(--radius-xs)",
                              backgroundColor: "var(--bg-surface)",
                              color: "var(--text-secondary)",
                            }}
                          >
                            Context: {msg.documentContext}
                          </span>
                        )}

                        {!isUser && msg.sourceType && (
                          <span
                            style={{
                              fontSize: "10px",
                              fontWeight: "600",
                              padding: "1px 6px",
                              borderRadius: "var(--radius-xs)",
                              backgroundColor:
                                msg.sourceType === "knowledge_rag" ||
                                msg.sourceType === "document_context" ||
                                msg.sourceType === "document_summary" ||
                                msg.sourceType === "date_summary"
                                  ? "var(--color-success-bg)"
                                  : "var(--color-primary-light)",
                              color:
                                msg.sourceType === "knowledge_rag" ||
                                msg.sourceType === "document_context" ||
                                msg.sourceType === "document_summary" ||
                                msg.sourceType === "date_summary"
                                  ? "var(--color-success-text)"
                                  : "var(--color-primary)",
                            }}
                          >
                            {msg.sourceType === "document_context"
                              ? "DOCUMENT RAG"
                              : msg.sourceType === "document_summary"
                              ? "DOCUMENT SUMMARY"
                              : msg.sourceType === "date_summary"
                              ? "DATE SUMMARY"
                              : msg.sourceType === "knowledge_rag"
                              ? "ORACLE VECTOR RAG"
                              : "OCI GENAI"}
                          </span>
                        )}

                        {!isUser && !msg.isError && (
                          <button
                            onClick={() => handleCopyText(msg.id, msg.text)}
                            style={{
                              background: "transparent",
                              color: "var(--text-secondary)",
                              display: "inline-flex",
                              alignItems: "center",
                              gap: "3px",
                              fontSize: "11px",
                              padding: "1px 4px",
                              borderRadius: "var(--radius-xs)",
                            }}
                            title="Copy answer"
                          >
                            {isCopied ? (
                              <Check size={11} style={{ color: "var(--color-success-text)" }} />
                            ) : (
                              <Copy size={11} />
                            )}
                            <span>{isCopied ? "Copied" : "Copy"}</span>
                          </button>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })}

              {/* Loading Indicator */}
              {isLoading && (
                <div className="chat-bubble-row assistant">
                  <div className="chat-avatar assistant">
                    <Bot size={15} />
                  </div>
                  <div className="chat-bubble assistant" style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                    <RefreshCw size={14} className="animate-spin" style={{ color: "var(--color-primary)" }} />
                    <span style={{ fontSize: "13px", color: "var(--text-secondary)" }}>
                      GSVAI is synthesizing intelligence response...
                    </span>
                  </div>
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>

            {/* Input & Suggestions Footer */}
            <div className="chat-footer">
              {/* Compact Expandable AI Execution Trace */}
              <AIExecutionTrace
                trace={currentTrace}
                isExpanded={isTraceExpanded}
                onToggleExpand={() => setIsTraceExpanded((prev) => !prev)}
                isLoading={isLoading && currentTrace?.isLoading}
              />

              {/* Quick suggestions chips */}
              <div className="prompt-chips">
                <span
                  style={{
                    fontSize: "11.5px",
                    color: "var(--text-secondary)",
                    display: "flex",
                    alignItems: "center",
                    gap: "4px",
                    flexShrink: 0,
                  }}
                >
                  <Sparkles size={12} style={{ color: "var(--color-primary)" }} /> Suggested:
                </span>
                {(activeDocument ? DOC_SUGGESTIONS : GENERAL_SUGGESTIONS).map((sug, idx) => (
                  <button
                    key={idx}
                    className="prompt-chip"
                    onClick={() => handleSendMessage(sug)}
                    disabled={isLoading || isUploading}
                  >
                    {sug}
                  </button>
                ))}
              </div>

              {/* Chat Input Row */}
              <div className="chat-input-row">
                <button
                  className="btn btn-secondary"
                  style={{ height: "42px", padding: "0 12px" }}
                  onClick={() => fileInputRef.current?.click()}
                  disabled={isLoading || isUploading}
                  title="Upload PDF Document"
                >
                  <UploadCloud size={16} style={{ color: "var(--color-primary)" }} />
                </button>

                <input
                  ref={inputRef}
                  type="text"
                  className="chat-input"
                  placeholder={
                    isLoading
                      ? "Generating response..."
                      : isUploading
                      ? "Processing and indexing document..."
                      : activeDocument
                      ? `Ask questions about ${activeDocument.document_name || activeDocument.filename}...`
                      : "Ask anything about enterprise documents, knowledge, or General AI..."
                  }
                  value={inputQuery}
                  onChange={(e) => setInputQuery(e.target.value)}
                  onKeyDown={handleKeyDown}
                  disabled={isLoading || isUploading}
                />

                <button
                  className="btn btn-primary"
                  style={{ height: "42px", padding: "0 18px" }}
                  onClick={() => handleSendMessage()}
                  disabled={!inputQuery.trim() || isLoading || isUploading}
                >
                  {isLoading ? <RefreshCw size={16} className="animate-spin" /> : <Send size={16} />}
                  <span>Send</span>
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* ========================================================= */}
        {/* RIGHT / SMALL PANEL: Compact Documents Panel              */}
        {/* ========================================================= */}
        <div
          style={{
            width: "360px",
            flexShrink: 0,
            display: "flex",
            flexDirection: "column",
            height: "100%",
            backgroundColor: "var(--bg-card)",
            border: "1px solid var(--border-card)",
            borderRadius: "var(--radius-lg)",
            overflow: "hidden",
            boxShadow: "var(--shadow-xs)",
          }}
        >
          {/* Panel Header */}
          <div
            style={{
              padding: "14px 16px",
              borderBottom: "1px solid var(--border-subtle)",
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              backgroundColor: "var(--bg-surface-subtle)",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <FileText size={16} style={{ color: "var(--color-primary)" }} />
              <span style={{ fontWeight: "700", fontSize: "14px", color: "var(--text-primary)" }}>
                Documents
              </span>
              <span
                style={{
                  fontSize: "11px",
                  fontWeight: "600",
                  backgroundColor: "var(--bg-surface)",
                  color: "var(--text-secondary)",
                  padding: "1px 6px",
                  borderRadius: "var(--radius-full)",
                  border: "1px solid var(--border-subtle)",
                }}
              >
                {documents.length}
              </span>
            </div>

            <button
              className="btn btn-primary"
              style={{ fontSize: "12px", padding: "5px 12px", height: "30px" }}
              onClick={() => fileInputRef.current?.click()}
              disabled={isUploading || isLoading}
              title="Upload new PDF document"
            >
              <UploadCloud size={13} />
              + Upload Document
            </button>
          </div>

          {/* Panel Scrollable Content */}
          <div
            style={{
              flex: 1,
              overflowY: "auto",
              padding: "14px",
              display: "flex",
              flexDirection: "column",
              gap: "14px",
            }}
          >
            {/* 1. Real-time Ingestion / Processing Status */}
            {(isUploading || uploadStage || uploadError) && (
              <div
                style={{
                  padding: "12px",
                  borderRadius: "var(--radius-md)",
                  backgroundColor: uploadError ? "var(--color-danger-bg)" : "var(--bg-surface-subtle)",
                  border: `1px solid ${uploadError ? "var(--color-danger-border)" : "var(--color-primary-border)"}`,
                  display: "flex",
                  flexDirection: "column",
                  gap: "10px",
                }}
              >
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "12px", fontWeight: "700" }}>
                    {isUploading ? (
                      <RefreshCw size={14} className="animate-spin" style={{ color: "var(--color-primary)" }} />
                    ) : uploadError ? (
                      <AlertCircle size={14} style={{ color: "var(--color-danger)" }} />
                    ) : (
                      <CheckCircle2 size={14} style={{ color: "var(--color-success)" }} />
                    )}
                    <span style={{ color: "var(--text-primary)" }}>Processing Status</span>
                  </div>

                  <span
                    style={{
                      fontSize: "10px",
                      fontWeight: "700",
                      padding: "1px 6px",
                      borderRadius: "var(--radius-xs)",
                      backgroundColor: uploadError
                        ? "var(--color-danger)"
                        : uploadStage === "ready"
                        ? "var(--color-success)"
                        : "var(--color-primary)",
                      color: "#FFFFFF",
                      textTransform: "uppercase",
                    }}
                  >
                    {uploadError
                      ? "FAILED"
                      : uploadStage === "uploading"
                      ? "UPLOADING..."
                      : uploadStage === "ocr"
                      ? "OCR EXTRACTING..."
                      : uploadStage === "indexing"
                      ? "INDEXING..."
                      : "INDEXED"}
                  </span>
                </div>

                {/* Real pipeline checklist */}
                <div style={{ display: "flex", flexDirection: "column", gap: "5px", fontSize: "11px" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "6px", color: "var(--text-primary)" }}>
                    <CheckCircle2
                      size={12}
                      style={{
                        color: uploadStage ? "var(--color-success)" : "var(--text-muted)",
                      }}
                    />
                    <span>Uploaded to OCI Object Storage</span>
                  </div>

                  <div style={{ display: "flex", alignItems: "center", gap: "6px", color: "var(--text-primary)" }}>
                    <CheckCircle2
                      size={12}
                      style={{
                        color:
                          uploadStage === "ocr" || uploadStage === "indexing" || uploadStage === "ready"
                            ? "var(--color-success)"
                            : "var(--text-muted)",
                      }}
                    />
                    <span>OCR / Text Extraction (OCI Document Understanding)</span>
                  </div>

                  <div style={{ display: "flex", alignItems: "center", gap: "6px", color: "var(--text-secondary)" }}>
                    <CheckCircle2
                      size={12}
                      style={{
                        color:
                          uploadStage === "indexing" || uploadStage === "ready"
                            ? "var(--color-success)"
                            : "var(--text-muted)",
                      }}
                    />
                    <span>
                      Entity Processing{" "}
                      {lastUploadPipeline?.key_value_extraction
                        ? `(${lastUploadPipeline.key_value_extraction})`
                        : ""}
                    </span>
                  </div>

                  <div style={{ display: "flex", alignItems: "center", gap: "6px", color: "var(--text-secondary)" }}>
                    <CheckCircle2
                      size={12}
                      style={{
                        color:
                          uploadStage === "indexing" || uploadStage === "ready"
                            ? "var(--color-success)"
                            : "var(--text-muted)",
                      }}
                    />
                    <span>Validation Completed</span>
                  </div>

                  <div style={{ display: "flex", alignItems: "center", gap: "6px", color: "var(--text-primary)" }}>
                    <CheckCircle2
                      size={12}
                      style={{
                        color: uploadStage === "ready" ? "var(--color-success)" : "var(--text-muted)",
                      }}
                    />
                    <span>Knowledge Indexing (Oracle Vector DB)</span>
                  </div>
                </div>

                {uploadError && (
                  <div style={{ fontSize: "11px", color: "var(--color-danger-text)", marginTop: "2px" }}>
                    {uploadError}
                  </div>
                )}
              </div>
            )}

            {/* 2. Active Document Card (if selected) */}
            {activeDocument && (
              <div
                style={{
                  display: "flex",
                  flexDirection: "column",
                  gap: "8px",
                  padding: "12px",
                  borderRadius: "var(--radius-md)",
                  backgroundColor: "var(--color-primary-light)",
                  border: "1.5px solid var(--color-primary)",
                }}
              >
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                  <span
                    style={{
                      fontSize: "10.5px",
                      fontWeight: "700",
                      color: "var(--color-primary)",
                      letterSpacing: "0.04em",
                      textTransform: "uppercase",
                    }}
                  >
                    ACTIVE DOCUMENT
                  </span>
                  <span
                    style={{
                      fontSize: "10px",
                      fontWeight: "700",
                      padding: "1px 6px",
                      borderRadius: "var(--radius-xs)",
                      backgroundColor: "var(--color-success)",
                      color: "#FFFFFF",
                    }}
                  >
                    INDEXED
                  </span>
                </div>

                <div>
                  <div
                    style={{
                      fontSize: "13px",
                      fontWeight: "700",
                      color: "var(--text-primary)",
                      wordBreak: "break-word",
                    }}
                  >
                    {activeDocument.document_name || activeDocument.filename}
                  </div>
                  <div style={{ fontSize: "11.5px", color: "var(--text-secondary)", marginTop: "2px" }}>
                    {activeDocument.page_count || activeDocument.pages || 1} pages •{" "}
                    {activeDocument.chunk_count || activeDocument.chunks || 1} chunks • OCR Completed
                  </div>
                </div>

                {/* Quick actions for active doc */}
                <div style={{ display: "flex", gap: "6px", flexWrap: "wrap", marginTop: "4px" }}>
                  <button
                    className="btn btn-primary"
                    style={{ fontSize: "11px", padding: "4px 8px", height: "26px", flex: 1 }}
                    onClick={() => handleSendMessage("Summarize this document.", "summary")}
                    disabled={isLoading || isUploading}
                  >
                    <Sparkles size={11} />
                    Summarize
                  </button>

                  <button
                    className="btn btn-secondary"
                    style={{ fontSize: "11px", padding: "4px 8px", height: "26px" }}
                    onClick={() => setShowDocInsights(!showDocInsights)}
                  >
                    <Layers size={11} style={{ color: "var(--color-primary)" }} />
                    {showDocInsights ? "Hide Insights" : "Insights"}
                    {showDocInsights ? <ChevronUp size={10} /> : <ChevronDown size={10} />}
                  </button>
                </div>

                {/* Collapsible Document Insights */}
                {showDocInsights && (
                  <div
                    style={{
                      marginTop: "6px",
                      paddingTop: "8px",
                      borderTop: "1px solid var(--color-primary-border)",
                      fontSize: "11.5px",
                      display: "flex",
                      flexDirection: "column",
                      gap: "6px",
                    }}
                  >
                    <div style={{ display: "flex", justifyContent: "space-between" }}>
                      <span>Document ID:</span>
                      <strong>#{activeDocument.document_id}</strong>
                    </div>
                    {activeDocument.analysis_id && (
                      <div style={{ display: "flex", justifyContent: "space-between" }}>
                        <span>Analysis ID:</span>
                        <strong>#{activeDocument.analysis_id}</strong>
                      </div>
                    )}
                    {activeDocument.entities && (
                      <div style={{ display: "flex", justifyContent: "space-between" }}>
                        <span>Entities Extracted:</span>
                        <strong>{activeDocument.entities.length}</strong>
                      </div>
                    )}
                    {activeDocument.preview && (
                      <div>
                        <span style={{ fontWeight: "600", color: "var(--text-secondary)" }}>Preview:</span>
                        <div
                          style={{
                            marginTop: "3px",
                            maxHeight: "80px",
                            overflowY: "auto",
                            padding: "4px 6px",
                            backgroundColor: "rgba(255,255,255,0.7)",
                            borderRadius: "var(--radius-xs)",
                            fontSize: "10.5px",
                            fontFamily: "var(--font-mono)",
                            whiteSpace: "pre-wrap",
                          }}
                        >
                          {activeDocument.preview}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}

            {/* 3. All Documents Selection Option */}
            <div
              onClick={() => {
                setActiveDocument(null);
                setShowDocInsights(false);
              }}
              style={{
                padding: "10px 12px",
                borderRadius: "var(--radius-md)",
                border: activeDocument === null ? "1.5px solid var(--color-primary)" : "1px solid var(--border-subtle)",
                backgroundColor: activeDocument === null ? "var(--color-primary-light)" : "var(--bg-surface-subtle)",
                cursor: "pointer",
                display: "flex",
                alignItems: "center",
                gap: "10px",
                transition: "all 0.12s ease",
              }}
              title="Search across all indexed documents"
            >
              <div
                style={{
                  width: "28px",
                  height: "28px",
                  borderRadius: "var(--radius-sm)",
                  backgroundColor: activeDocument === null ? "var(--color-primary)" : "var(--bg-surface)",
                  color: activeDocument === null ? "#FFFFFF" : "var(--text-secondary)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  flexShrink: 0,
                }}
              >
                <Database size={14} />
              </div>

              <div style={{ flex: 1, overflow: "hidden" }}>
                <div
                  style={{
                    fontSize: "12.5px",
                    fontWeight: activeDocument === null ? "700" : "600",
                    color: "var(--text-primary)",
                  }}
                >
                  All Documents (Enterprise RAG)
                </div>
                <div style={{ fontSize: "11px", color: "var(--text-secondary)" }}>
                  Search & synthesize across all {documents.length} indexed files
                </div>
              </div>

              {activeDocument === null && (
                <span
                  style={{
                    fontSize: "10px",
                    fontWeight: "700",
                    backgroundColor: "var(--color-primary)",
                    color: "#FFFFFF",
                    padding: "1px 6px",
                    borderRadius: "var(--radius-xs)",
                  }}
                >
                  ACTIVE
                </span>
              )}
            </div>

            {/* 4. Document List Section */}
            <div style={{ display: "flex", flexDirection: "column", gap: "8px", flex: 1 }}>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                <span
                  style={{
                    fontSize: "11px",
                    fontWeight: "700",
                    textTransform: "uppercase",
                    letterSpacing: "0.04em",
                    color: "var(--text-muted)",
                  }}
                >
                  ALL DOCUMENTS
                </span>
                <span style={{ fontSize: "11px", color: "var(--text-muted)" }}>
                  {filteredDocuments.length} files
                </span>
              </div>

              {/* Search Filter */}
              <div style={{ position: "relative" }}>
                <Search
                  size={12}
                  style={{
                    position: "absolute",
                    left: "8px",
                    top: "50%",
                    transform: "translateY(-50%)",
                    color: "var(--text-muted)",
                  }}
                />
                <input
                  type="text"
                  placeholder="Filter documents..."
                  value={docSearchQuery}
                  onChange={(e) => setDocSearchQuery(e.target.value)}
                  style={{
                    width: "100%",
                    height: "30px",
                    fontSize: "12px",
                    paddingLeft: "26px",
                    paddingRight: "8px",
                    backgroundColor: "var(--bg-surface-subtle)",
                    border: "1px solid var(--border-subtle)",
                    borderRadius: "var(--radius-sm)",
                  }}
                />
              </div>

              {/* Documents List */}
              <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                {isLoadingDocs ? (
                  <div
                    style={{
                      padding: "24px",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      color: "var(--text-muted)",
                      gap: "6px",
                      fontSize: "12px",
                    }}
                  >
                    <RefreshCw size={13} className="animate-spin" />
                    <span>Loading indexed documents...</span>
                  </div>
                ) : filteredDocuments.length === 0 ? (
                  <div
                    style={{
                      padding: "20px 10px",
                      textAlign: "center",
                      color: "var(--text-muted)",
                      fontSize: "12px",
                    }}
                  >
                    {docSearchQuery
                      ? "No matching documents found."
                      : "No documents indexed yet. Upload a PDF to start."}
                  </div>
                ) : (
                  filteredDocuments.map((doc) => {
                    const isSelected =
                      activeDocument && activeDocument.document_id === doc.document_id;

                    return (
                      <div
                        key={doc.document_id}
                        onClick={() => {
                          setActiveDocument(doc);
                          setShowDocInsights(false);
                        }}
                        style={{
                          padding: "8px 10px",
                          borderRadius: "var(--radius-md)",
                          backgroundColor: isSelected ? "var(--color-primary-light)" : "var(--bg-card)",
                          border: isSelected
                            ? "1.5px solid var(--color-primary)"
                            : "1px solid var(--border-subtle)",
                          cursor: "pointer",
                          display: "flex",
                          alignItems: "center",
                          gap: "8px",
                          transition: "all 0.12s ease",
                        }}
                        className="doc-list-item"
                        title={`Click to set ${doc.document_name} as active context`}
                      >
                        <div
                          style={{
                            width: "26px",
                            height: "26px",
                            borderRadius: "var(--radius-xs)",
                            backgroundColor: isSelected
                              ? "var(--color-primary)"
                              : "var(--color-primary-light)",
                            color: isSelected ? "#FFFFFF" : "var(--color-primary)",
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "center",
                            flexShrink: 0,
                          }}
                        >
                          <FileText size={13} />
                        </div>

                        <div style={{ flex: 1, minWidth: 0 }}>
                          <div
                            style={{
                              fontSize: "12px",
                              fontWeight: isSelected ? "700" : "600",
                              color: "var(--text-primary)",
                              whiteSpace: "nowrap",
                              overflow: "hidden",
                              textOverflow: "ellipsis",
                            }}
                          >
                            {doc.document_name}
                          </div>
                          <div
                            style={{
                              fontSize: "10.5px",
                              color: "var(--text-secondary)",
                              display: "flex",
                              alignItems: "center",
                              gap: "4px",
                              marginTop: "1px",
                            }}
                          >
                            <span>{doc.page_count || 1} pages</span>
                            <span>•</span>
                            <span style={{ color: "var(--color-success-text)", fontWeight: "600" }}>
                              {doc.status || "Indexed"}
                            </span>
                            {doc.formatted_date && (
                              <>
                                <span>•</span>
                                <span>{doc.formatted_date.split(",")[0]}</span>
                              </>
                            )}
                          </div>
                        </div>

                        {isSelected && (
                          <CheckCircle2 size={14} style={{ color: "var(--color-primary)", flexShrink: 0 }} />
                        )}
                      </div>
                    );
                  })
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
