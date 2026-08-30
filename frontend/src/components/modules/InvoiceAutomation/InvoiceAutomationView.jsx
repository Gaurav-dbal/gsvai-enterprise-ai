import React, { useState, useEffect, useRef } from "react";
import {
  Receipt,
  Layers,
  ArrowRight,
  UploadCloud,
  FileText,
  CheckCircle2,
  AlertCircle,
  Loader2,
  RefreshCw,
  Sparkles,
  ShieldCheck,
  Building2,
  Calendar,
  DollarSign,
  Tag,
  FileSpreadsheet,
  Check,
  Copy,
  Clock,
  Send,
  Eye,
  Edit3,
  XCircle,
  Filter,
  Search,
  ExternalLink,
  ChevronRight,
  Database,
  ArrowUpRight,
  Save,
  HelpCircle,
} from "lucide-react";
import { SectionHeader } from "../../common/SectionHeader";
import { StatusBadge } from "../../common/Badge";
import {
  uploadInvoicePdf,
  getInvoiceProcessingStatus,
  getInvoiceProcessingResult,
  getReviewQueue,
  getInvoiceForReview,
  updateInvoiceReview,
  approveInvoice,
  rejectInvoice,
  getFusionConnections,
  getFusionConnectionMetadata,
  getInvoiceFusionMapping,
  saveInvoiceFusionMapping,
  getFusionPayloadPreview,
  submitInvoiceToFusion,
  getFusionSubmissionHistory,
} from "../../../api/client";

const PIPELINE_STAGES = [
  { key: "UPLOADING", label: "Upload to Backend", threshold: 10 },
  { key: "UPLOADED", label: "Object Storage Sync", threshold: 20 },
  { key: "CREATING_JOB", label: "OCI Processor Job", threshold: 25 },
  { key: "OCI_DOCUMENT_UNDERSTANDING", label: "Document Understanding", threshold: 80 },
  { key: "DOWNLOADING_RESULT", label: "Download Result JSON", threshold: 90 },
  { key: "EXTRACTING_FIELDS", label: "Field Extraction & DB Persist", threshold: 95 },
  { key: "COMPLETED", label: "Saved in Review Queue", threshold: 100 },
];

export function InvoiceAutomationView() {
  // Top-level View Mode: 'upload' | 'queue' | 'review' | 'fusion'
  const [activeView, setActiveView] = useState("upload");

  // --- Upload State ---
  const [appState, setAppState] = useState("IDLE"); // 'IDLE' | 'FILE_SELECTED' | 'UPLOADING' | 'PROCESSING' | 'COMPLETED' | 'FAILED'
  const [selectedFile, setSelectedFile] = useState(null);
  const [isDragging, setIsDragging] = useState(false);
  const [processingStatus, setProcessingStatus] = useState(null);
  const [invoiceResult, setInvoiceResult] = useState(null);
  const [errorMessage, setErrorMessage] = useState(null);

  // --- Review Queue State ---
  const [reviewQueue, setReviewQueue] = useState([]);
  const [queueLoading, setQueueLoading] = useState(false);
  const [queueFilter, setQueueFilter] = useState("ALL"); // 'ALL' | 'REVIEW_REQUIRED' | 'APPROVED' | 'REJECTED' | 'FUSION_CREATED'
  const [searchQuery, setSearchQuery] = useState("");

  // --- Detailed Review State ---
  const [currentInvoiceId, setCurrentInvoiceId] = useState(null);
  const [reviewData, setReviewData] = useState(null);
  const [reviewLoading, setReviewLoading] = useState(false);
  const [editForm, setEditForm] = useState({});
  const [editLines, setEditLines] = useState([]);
  const [saveSuccessMsg, setSaveSuccessMsg] = useState(null);

  // --- Rejection Modal State ---
  const [isRejectModalOpen, setIsRejectModalOpen] = useState(false);
  const [rejectReason, setRejectReason] = useState("");

  // --- Oracle Fusion State ---
  const [availableConnections, setAvailableConnections] = useState([]);
  const [selectedConnectionId, setSelectedConnectionId] = useState(null);
  const [fusionMappingData, setFusionMappingData] = useState(null);
  const [fusionPreviewPayload, setFusionPreviewPayload] = useState(null);
  const [isPreviewModalOpen, setIsPreviewModalOpen] = useState(false);
  const [isConfirmSubmitModalOpen, setIsConfirmSubmitModalOpen] = useState(false);
  const [fusionSubmitting, setFusionSubmitting] = useState(false);
  const [fusionSubmissionReceipt, setFusionSubmissionReceipt] = useState(null);
  const [fusionSubmissionsList, setFusionSubmissionsList] = useState([]);
  const [fusionSubView, setFusionSubView] = useState("mapping"); // 'mapping' | 'history'
  const [copiedField, setCopiedField] = useState(null);

  // Derived Fusion connection & status
  const selectedConnection = availableConnections.find((c) => c.connection_id === selectedConnectionId) || null;
  const isFusionConnected = Boolean(selectedConnection && selectedConnection.status === "CONNECTED" && selectedConnection.is_active);

  const fileInputRef = useRef(null);
  const pollingRef = useRef(null);

  // Clean up polling interval on unmount
  useEffect(() => {
    return () => {
      if (pollingRef.current) clearInterval(pollingRef.current);
    };
  }, []);

  // Fetch initial queue and Fusion connections on mount
  useEffect(() => {
    loadReviewQueue();
    loadFusionConnectionsList();
  }, []);

  const loadReviewQueue = async (status = null) => {
    setQueueLoading(true);
    try {
      const data = await getReviewQueue(status === "ALL" ? null : status);
      setReviewQueue(data || []);
    } catch (err) {
      console.error("Failed to load review queue:", err);
    } finally {
      setQueueLoading(false);
    }
  };

  const loadFusionConnectionsList = async () => {
    try {
      const data = await getFusionConnections();
      const conns = data || [];
      setAvailableConnections(conns);
      // Auto-select first connected/active connection if available
      const connectedOne = conns.find((c) => c.status === "CONNECTED" && c.is_active);
      if (connectedOne) {
        setSelectedConnectionId(connectedOne.connection_id);
      } else if (conns.length > 0) {
        setSelectedConnectionId(conns[0].connection_id);
      }
    } catch (err) {
      console.warn("Failed to load Fusion connections:", err);
    }
  };

  const loadFusionSubmissionsList = async () => {
    try {
      const data = await getFusionSubmissionHistory();
      setFusionSubmissionsList(data || []);
    } catch (err) {
      console.warn("Failed to load submission history:", err);
    }
  };

  const loadInvoiceForReview = async (invoiceId) => {
    setCurrentInvoiceId(invoiceId);
    setReviewLoading(true);
    setSaveSuccessMsg(null);
    setErrorMessage(null);
    setFusionSubmissionReceipt(null);
    try {
      const data = await getInvoiceForReview(invoiceId);
      setReviewData(data);
      setEditForm({
        vendor_name: data.vendor_name || "",
        invoice_number: data.invoice_number || "",
        invoice_date: data.invoice_date || "",
        due_date: data.due_date || "",
        total_amount: data.total_amount !== null && data.total_amount !== undefined ? String(data.total_amount) : "",
        subtotal: data.subtotal !== null && data.subtotal !== undefined ? String(data.subtotal) : "",
        tax_amount: data.tax_amount !== null && data.tax_amount !== undefined ? String(data.tax_amount) : "",
        currency: data.currency || "USD",
        payment_terms: data.payment_terms || "",
        po_number: data.po_number || "",
      });
      setEditLines(data.line_items || []);
      setActiveView("review");

      // Pre-load Fusion mapping for this invoice
      loadFusionMappingForInvoice(invoiceId);
    } catch (err) {
      setErrorMessage(err.message || "Failed to load invoice for review.");
    } finally {
      setReviewLoading(false);
    }
  };

  const loadFusionMappingForInvoice = async (invoiceId, connId = null) => {
    try {
      const targetConnId = connId !== null ? connId : selectedConnectionId;
      const mapData = await getInvoiceFusionMapping(invoiceId, targetConnId);
      setFusionMappingData(mapData);
    } catch (err) {
      console.warn("Failed to load Fusion mapping:", err);
    }
  };

  // Format numbers & currency
  const formatAmount = (val, currency = null) => {
    if (val === null || val === undefined || val === "") return "—";
    const num = typeof val === "number" ? val : parseFloat(val);
    if (isNaN(num)) return String(val);
    const formatted = new Intl.NumberFormat("en-US", {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(num);
    return currency ? `${currency} ${formatted}` : formatted;
  };

  const formatFileSize = (bytes) => {
    if (!bytes || bytes === 0) return "0 KB";
    const k = 1024;
    const sizes = ["Bytes", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + " " + sizes[i];
  };

  // --- Upload Handlers ---
  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    const files = e.dataTransfer.files;
    if (files && files.length > 0) validateAndSelectFile(files[0]);
  };

  const handleFileInputChange = (e) => {
    const files = e.target.files;
    if (files && files.length > 0) validateAndSelectFile(files[0]);
  };

  const validateAndSelectFile = (file) => {
    setErrorMessage(null);
    if (!file.name.toLowerCase().endsWith(".pdf")) {
      setErrorMessage("Only PDF documents (.pdf) are supported for Invoice Automation.");
      return;
    }
    if (file.size > 50 * 1024 * 1024) {
      setErrorMessage("File size exceeds the 50MB limit.");
      return;
    }
    setSelectedFile(file);
    setAppState("FILE_SELECTED");
  };

  const handleStartUpload = async () => {
    if (!selectedFile) return;
    setAppState("UPLOADING");
    setErrorMessage(null);
    try {
      const uploadResp = await uploadInvoicePdf(selectedFile);
      setProcessingStatus(uploadResp);
      setAppState("PROCESSING");
      startStatusPolling(uploadResp.processing_id);
    } catch (err) {
      setErrorMessage(err.message || "Failed to upload invoice PDF.");
      setAppState("FAILED");
    }
  };

  const startStatusPolling = (procId) => {
    if (pollingRef.current) clearInterval(pollingRef.current);
    let attempts = 0;
    pollingRef.current = setInterval(async () => {
      attempts += 1;
      if (attempts > 120) {
        clearInterval(pollingRef.current);
        setErrorMessage("Processing timed out.");
        setAppState("FAILED");
        return;
      }
      try {
        const statusData = await getInvoiceProcessingStatus(procId);
        setProcessingStatus(statusData);
        if (statusData.status === "COMPLETED") {
          clearInterval(pollingRef.current);
          const resultData = await getInvoiceProcessingResult(procId);
          setInvoiceResult(resultData);
          setAppState("COMPLETED");
          loadReviewQueue(); // Refresh review queue
        } else if (statusData.status === "FAILED") {
          clearInterval(pollingRef.current);
          setErrorMessage(statusData.error || "OCI Processing failed.");
          setAppState("FAILED");
        }
      } catch (err) {
        console.warn("Polling glitch:", err);
      }
    }, 2500);
  };

  const handleResetFlow = () => {
    if (pollingRef.current) clearInterval(pollingRef.current);
    setSelectedFile(null);
    setProcessingStatus(null);
    setInvoiceResult(null);
    setErrorMessage(null);
    setAppState("IDLE");
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  // --- Save Corrections Handler ---
  const handleSaveCorrections = async () => {
    if (!currentInvoiceId) return;
    setErrorMessage(null);
    setSaveSuccessMsg(null);
    try {
      const payload = {
        header_fields: {
          vendor_name: editForm.vendor_name,
          invoice_number: editForm.invoice_number,
          invoice_date: editForm.invoice_date,
          due_date: editForm.due_date,
          total_amount: editForm.total_amount ? parseFloat(editForm.total_amount) : null,
          subtotal: editForm.subtotal ? parseFloat(editForm.subtotal) : null,
          tax_amount: editForm.tax_amount ? parseFloat(editForm.tax_amount) : null,
          currency: editForm.currency,
          payment_terms: editForm.payment_terms,
          po_number: editForm.po_number,
        },
        line_items: editLines,
        reviewer: "Senior AP Reviewer",
        comments: "Reviewed and updated by user",
      };
      await updateInvoiceReview(currentInvoiceId, payload);
      setSaveSuccessMsg("Corrections saved successfully to Oracle DB.");
      loadInvoiceForReview(currentInvoiceId);
      loadReviewQueue();
    } catch (err) {
      setErrorMessage(err.message || "Failed to save corrections.");
    }
  };

  // --- Approve Handler ---
  const handleApproveInvoice = async () => {
    if (!currentInvoiceId) return;
    setErrorMessage(null);
    try {
      await approveInvoice(currentInvoiceId, {
        reviewer: "AP Reviewer",
        comments: "Approved for Oracle Fusion submission",
      });
      setSaveSuccessMsg("Invoice approved! You can now proceed to Oracle Fusion mapping and submission.");
      loadInvoiceForReview(currentInvoiceId);
      loadReviewQueue();
    } catch (err) {
      setErrorMessage(err.message || "Failed to approve invoice.");
    }
  };

  // --- Reject Handler ---
  const handleRejectInvoice = async () => {
    if (!currentInvoiceId || !rejectReason.trim()) {
      setErrorMessage("Please enter a reason for rejection.");
      return;
    }
    setErrorMessage(null);
    try {
      await rejectInvoice(currentInvoiceId, {
        reviewer: "AP Reviewer",
        comments: rejectReason.trim(),
      });
      setIsRejectModalOpen(false);
      setRejectReason("");
      loadInvoiceForReview(currentInvoiceId);
      loadReviewQueue();
    } catch (err) {
      setErrorMessage(err.message || "Failed to reject invoice.");
    }
  };

  // --- Oracle Fusion Preview & Submit ---
  const handleOpenFusionPreview = async () => {
    if (!currentInvoiceId) return;
    if (!selectedConnectionId) {
      setErrorMessage("Please select a target Oracle Fusion connection before previewing.");
      return;
    }
    try {
      const preview = await getFusionPayloadPreview(currentInvoiceId, selectedConnectionId);
      setFusionPreviewPayload(preview);
      setIsPreviewModalOpen(true);
    } catch (err) {
      setErrorMessage(err.message || "Failed to generate Fusion payload preview.");
    }
  };

  const handleConfirmFusionSubmit = async () => {
    if (!currentInvoiceId) return;
    if (!selectedConnectionId) {
      setErrorMessage("Please select a target Oracle Fusion connection before submitting.");
      return;
    }
    setFusionSubmitting(true);
    setErrorMessage(null);
    try {
      const receipt = await submitInvoiceToFusion(currentInvoiceId, selectedConnectionId, false);
      setFusionSubmissionReceipt(receipt);
      setIsConfirmSubmitModalOpen(false);
      setSaveSuccessMsg(`Successfully created AP Invoice #${receipt.fusion_invoice_id} in Oracle Fusion (${receipt.connection_name}).`);
      loadInvoiceForReview(currentInvoiceId);
      loadReviewQueue();
      loadFusionSubmissionsList();
    } catch (err) {
      setErrorMessage(err.message || "Fusion submission failed.");
    } finally {
      setFusionSubmitting(false);
    }
  };

  const handleCopyText = (text, key) => {
    navigator.clipboard.writeText(text);
    setCopiedField(key);
    setTimeout(() => setCopiedField(null), 2000);
  };

  const renderConfidenceBadge = (confidence) => {
    if (confidence === null || confidence === undefined) {
      return <span style={{ fontSize: "11px", padding: "2px 8px", borderRadius: "12px", backgroundColor: "var(--bg-surface-subtle)", color: "var(--text-muted)", border: "1px solid var(--border-subtle)" }}>N/A</span>;
    }
    const pct = Math.round(confidence * 1000) / 10;
    let color = "#059669", bg = "rgba(16, 185, 129, 0.12)", border = "rgba(16, 185, 129, 0.25)";
    if (pct < 75) { color = "#d97706"; bg = "rgba(245, 158, 11, 0.12)"; border = "rgba(245, 158, 11, 0.25)"; }
    else if (pct < 85) { color = "#2563eb"; bg = "rgba(59, 130, 246, 0.12)"; border = "rgba(59, 130, 246, 0.25)"; }
    return (
      <span style={{ fontSize: "11px", padding: "2px 8px", borderRadius: "12px", backgroundColor: bg, color, border: `1px solid ${border}`, fontWeight: "600", display: "inline-flex", alignItems: "center", gap: "4px" }}>
        <ShieldCheck size={11} /> {pct.toFixed(1)}%
      </span>
    );
  };

  // Filter review queue items
  const filteredQueue = reviewQueue.filter((inv) => {
    if (queueFilter !== "ALL" && inv.status !== queueFilter) return false;
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      const matchName = inv.vendor_name && inv.vendor_name.toLowerCase().includes(q);
      const matchNum = inv.invoice_number && inv.invoice_number.toLowerCase().includes(q);
      const matchDoc = inv.document_name && inv.document_name.toLowerCase().includes(q);
      return matchName || matchNum || matchDoc;
    }
    return true;
  });

  return (
    <div className="animate-fade-in" style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
      {/* Module Title Header */}
      <SectionHeader
        title="Enterprise Invoice Automation & Oracle Fusion ERP Integration"
        description="Autonomous invoice lifecycle: OCI extraction, Oracle DB persistence, human review with editable corrections, visual Oracle Fusion field mapping, and direct Payables creation."
        isLive={isFusionConnected}
        badgeText={isFusionConnected ? `FUSION ${selectedConnection?.environment || "ERP"} READY` : "OCI + ORACLE DB"}
      />

      {/* Sub-Navigation Tabs */}
      <div
        className="card"
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "8px 14px",
          flexWrap: "wrap",
          gap: "10px",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "8px", flexWrap: "wrap" }}>
          <button
            className={`btn ${activeView === "upload" ? "btn-primary" : "btn-secondary"}`}
            onClick={() => setActiveView("upload")}
            style={{ fontSize: "12.5px", padding: "6px 14px" }}
          >
            <UploadCloud size={14} />
            Upload & Process
          </button>

          <button
            className={`btn ${activeView === "queue" ? "btn-primary" : "btn-secondary"}`}
            onClick={() => {
              setActiveView("queue");
              loadReviewQueue();
            }}
            style={{ fontSize: "12.5px", padding: "6px 14px" }}
          >
            <Layers size={14} />
            Review Queue
            <span
              style={{
                marginLeft: "6px",
                padding: "1px 6px",
                borderRadius: "10px",
                backgroundColor: activeView === "queue" ? "rgba(255,255,255,0.25)" : "var(--bg-surface-subtle)",
                fontSize: "11px",
                fontWeight: "700",
              }}
            >
              {reviewQueue.length}
            </span>
          </button>

          {currentInvoiceId && (
            <button
              className={`btn ${activeView === "review" ? "btn-primary" : "btn-secondary"}`}
              onClick={() => setActiveView("review")}
              style={{ fontSize: "12.5px", padding: "6px 14px" }}
            >
              <Edit3 size={14} />
              Review #{currentInvoiceId}
            </button>
          )}

          {currentInvoiceId && (
            <button
              className={`btn ${activeView === "fusion" ? "btn-primary" : "btn-secondary"}`}
              onClick={() => {
                setActiveView("fusion");
                loadFusionMappingForInvoice(currentInvoiceId);
              }}
              style={{ fontSize: "12.5px", padding: "6px 14px" }}
            >
              <Send size={14} />
              Oracle Fusion Integration
            </button>
          )}
        </div>

        {/* Fusion Connection Indicator */}
        {selectedConnection ? (
          <div style={{ display: "flex", alignItems: "center", gap: "8px", fontSize: "11.5px" }}>
            <span
              style={{
                width: "8px",
                height: "8px",
                borderRadius: "50%",
                backgroundColor: isFusionConnected ? "var(--color-success)" : "var(--color-warning)",
                display: "inline-block",
              }}
            />
            <span style={{ color: "var(--text-secondary)" }}>Fusion ERP:</span>
            <span style={{ fontWeight: "600", color: "var(--text-primary)" }}>
              {selectedConnection.connection_name} ({selectedConnection.environment})
            </span>
          </div>
        ) : (
          <div style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "11.5px", color: "var(--text-muted)" }}>
            <Database size={13} />
            <span>No Fusion Destination Configured</span>
          </div>
        )}
      </div>

      {/* Global Alert / Success Banners */}
      {errorMessage && (
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            padding: "12px 18px",
            borderRadius: "var(--radius-md)",
            backgroundColor: "rgba(239, 68, 68, 0.08)",
            border: "1px solid rgba(239, 68, 68, 0.3)",
            color: "#b91c1c",
            fontSize: "13px",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <AlertCircle size={16} />
            <span>{errorMessage}</span>
          </div>
          <button
            onClick={() => setErrorMessage(null)}
            style={{ background: "none", border: "none", color: "#b91c1c", cursor: "pointer" }}
          >
            ✕
          </button>
        </div>
      )}

      {saveSuccessMsg && (
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            padding: "12px 18px",
            borderRadius: "var(--radius-md)",
            backgroundColor: "rgba(16, 185, 129, 0.08)",
            border: "1px solid rgba(16, 185, 129, 0.3)",
            color: "#047857",
            fontSize: "13px",
            fontWeight: "600",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <CheckCircle2 size={16} />
            <span>{saveSuccessMsg}</span>
          </div>
          <button
            onClick={() => setSaveSuccessMsg(null)}
            style={{ background: "none", border: "none", color: "#047857", cursor: "pointer" }}
          >
            ✕
          </button>
        </div>
      )}

      {/* ============================================================= */}
      {/* VIEW 1: UPLOAD & OCI PROCESSING                               */}
      {/* ============================================================= */}
      {activeView === "upload" && (
        <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
          {/* Upload Card */}
          <div className="card" style={{ padding: "28px" }}>
            <div className="card-header" style={{ marginBottom: "18px", paddingBottom: "12px", borderBottom: "1px solid var(--border-subtle)" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                <div
                  style={{
                    width: "36px",
                    height: "36px",
                    borderRadius: "var(--radius-md)",
                    backgroundColor: "rgba(79, 70, 229, 0.1)",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    color: "var(--color-primary)",
                  }}
                >
                  <UploadCloud size={20} />
                </div>
                <div>
                  <h3 className="card-title" style={{ fontSize: "16px", fontWeight: "700" }}>Upload Invoice PDF</h3>
                  <p className="card-subtitle" style={{ fontSize: "12.5px" }}>Upload vendor invoice for automated OCI extraction and Oracle DB persistence</p>
                </div>
              </div>
              <span className="badge badge-live">PDF Format (Max 50MB)</span>
            </div>

            {/* Drag & Drop Zone */}
            <div
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current && fileInputRef.current.click()}
              style={{
                border: `2px dashed ${isDragging ? "var(--color-primary)" : "var(--border-subtle)"}`,
                backgroundColor: isDragging ? "rgba(79, 70, 229, 0.04)" : "var(--bg-surface-subtle)",
                borderRadius: "var(--radius-lg)",
                padding: "40px 24px",
                textAlign: "center",
                cursor: "pointer",
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                gap: "12px",
              }}
            >
              <input type="file" ref={fileInputRef} onChange={handleFileInputChange} accept=".pdf,application/pdf" style={{ display: "none" }} />
              <div
                style={{
                  width: "50px",
                  height: "50px",
                  borderRadius: "50%",
                  backgroundColor: "var(--bg-surface)",
                  border: "1px solid var(--border-subtle)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  color: "var(--color-primary)",
                }}
              >
                <FileText size={24} />
              </div>
              <div>
                <p style={{ fontSize: "14px", fontWeight: "600", color: "var(--text-primary)", marginBottom: "4px" }}>
                  {isDragging ? "Drop your invoice PDF here" : "Drag & drop your invoice PDF here"}
                </p>
                <p style={{ fontSize: "12px", color: "var(--text-secondary)" }}>
                  or <span style={{ color: "var(--color-primary)", fontWeight: "600", textDecoration: "underline" }}>browse files</span>
                </p>
              </div>
            </div>

            {/* Selected File Details */}
            {selectedFile && (
              <div
                style={{
                  marginTop: "18px",
                  padding: "14px 18px",
                  backgroundColor: "var(--bg-surface-subtle)",
                  border: "1px solid var(--border-subtle)",
                  borderRadius: "var(--radius-md)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  flexWrap: "wrap",
                  gap: "12px",
                }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                  <Receipt size={18} style={{ color: "var(--color-success)" }} />
                  <div>
                    <div style={{ fontWeight: "700", fontSize: "13px", color: "var(--text-primary)" }}>{selectedFile.name}</div>
                    <div style={{ fontSize: "11.5px", color: "var(--text-secondary)" }}>Size: {formatFileSize(selectedFile.size)}</div>
                  </div>
                </div>

                <div style={{ display: "flex", gap: "10px" }}>
                  <button className="btn btn-secondary" onClick={handleResetFlow} style={{ fontSize: "12px" }}>Clear</button>
                  <button className="btn btn-primary" onClick={handleStartUpload} disabled={appState === "UPLOADING"} style={{ fontSize: "12px" }}>
                    {appState === "UPLOADING" ? <><Loader2 size={14} className="spin" /> Uploading...</> : <><Sparkles size={14} /> Process Invoice</>}
                  </button>
                </div>
              </div>
            )}
          </div>

          {/* Processing Progress Panel */}
          {appState === "PROCESSING" && processingStatus && (
            <div className="card" style={{ padding: "24px" }}>
              <div className="card-header" style={{ marginBottom: "16px" }}>
                <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                  <Loader2 size={18} className="spin" style={{ color: "var(--color-primary)" }} />
                  <h3 className="card-title" style={{ fontSize: "15px", fontWeight: "700" }}>Autonomous OCI Analysis in Progress</h3>
                </div>
                <span className="badge badge-live">{processingStatus.progress || 20}% Complete</span>
              </div>

              {/* Progress bar */}
              <div style={{ width: "100%", height: "8px", backgroundColor: "var(--bg-surface-subtle)", borderRadius: "4px", overflow: "hidden", marginBottom: "14px" }}>
                <div style={{ width: `${processingStatus.progress || 20}%`, height: "100%", backgroundColor: "var(--color-primary)", transition: "width 0.4s ease" }} />
              </div>

              <div style={{ fontSize: "13px", color: "var(--text-secondary)", marginBottom: "18px" }}>
                {processingStatus.message || "OCI analyzing invoice document..."}
              </div>

              {/* Stages Visualizer */}
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))", gap: "10px" }}>
                {PIPELINE_STAGES.map((stage, idx) => {
                  const prog = processingStatus.progress || 0;
                  const isDone = prog >= stage.threshold;
                  return (
                    <div
                      key={stage.key}
                      style={{
                        padding: "10px 12px",
                        borderRadius: "var(--radius-sm)",
                        border: `1px solid ${isDone ? "rgba(16, 185, 129, 0.3)" : "var(--border-subtle)"}`,
                        backgroundColor: isDone ? "rgba(16, 185, 129, 0.05)" : "var(--bg-surface-subtle)",
                        display: "flex",
                        alignItems: "center",
                        gap: "8px",
                        fontSize: "11.5px",
                        fontWeight: isDone ? "700" : "500",
                        color: isDone ? "var(--color-success)" : "var(--text-secondary)",
                      }}
                    >
                      {isDone ? <Check size={12} /> : idx + 1}
                      <span>{stage.label}</span>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Success Summary after Upload */}
          {appState === "COMPLETED" && invoiceResult && (
            <div className="card" style={{ padding: "24px", borderLeft: "4px solid var(--color-success)" }}>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: "14px" }}>
                <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                  <CheckCircle2 size={24} style={{ color: "var(--color-success)" }} />
                  <div>
                    <h3 style={{ fontSize: "16px", fontWeight: "700", color: "var(--text-primary)", margin: 0 }}>
                      Invoice Extracted & Persisted to Oracle DB
                    </h3>
                    <p style={{ fontSize: "12px", color: "var(--text-secondary)", margin: "2px 0 0 0" }}>
                      Invoice #{invoiceResult.invoice_id || "Saved"} • Vendor: <strong>{invoiceResult.invoice?.vendor_name || "—"}</strong> • Status: <strong>REVIEW REQUIRED</strong>
                    </p>
                  </div>
                </div>

                <div style={{ display: "flex", gap: "10px" }}>
                  {invoiceResult.invoice_id && (
                    <button
                      className="btn btn-primary"
                      onClick={() => loadInvoiceForReview(invoiceResult.invoice_id)}
                      style={{ fontSize: "12.5px" }}
                    >
                      <Eye size={14} />
                      Open in Review Workspace
                    </button>
                  )}
                  <button className="btn btn-secondary" onClick={handleResetFlow} style={{ fontSize: "12.5px" }}>
                    Upload Another
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* ============================================================= */}
      {/* VIEW 2: INVOICE REVIEW QUEUE                                  */}
      {/* ============================================================= */}
      {activeView === "queue" && (
        <div className="card" style={{ padding: "20px" }}>
          <div className="card-header" style={{ marginBottom: "16px", flexWrap: "wrap", gap: "12px" }}>
            <div>
              <h3 className="card-title" style={{ fontSize: "16px", fontWeight: "700" }}>Invoice Review Queue</h3>
              <p className="card-subtitle" style={{ fontSize: "12.5px" }}>All processed invoices stored in Oracle DB awaiting review or sync</p>
            </div>

            {/* Filter & Search Bar */}
            <div style={{ display: "flex", alignItems: "center", gap: "10px", flexWrap: "wrap" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "6px", backgroundColor: "var(--bg-surface-subtle)", padding: "4px 10px", borderRadius: "var(--radius-md)", border: "1px solid var(--border-subtle)" }}>
                <Search size={14} style={{ color: "var(--text-muted)" }} />
                <input
                  type="text"
                  placeholder="Search vendor or invoice #..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  style={{ border: "none", background: "transparent", outline: "none", fontSize: "12.5px", width: "180px" }}
                />
              </div>

              <div style={{ display: "flex", gap: "4px" }}>
                {["ALL", "REVIEW_REQUIRED", "APPROVED", "FUSION_CREATED", "REJECTED"].map((st) => (
                  <button
                    key={st}
                    className={`btn ${queueFilter === st ? "btn-primary" : "btn-secondary"}`}
                    onClick={() => {
                      setQueueFilter(st);
                      loadReviewQueue(st);
                    }}
                    style={{ fontSize: "11px", padding: "4px 10px" }}
                  >
                    {st.replace("_", " ")}
                  </button>
                ))}
              </div>

              <button className="btn btn-secondary" onClick={() => loadReviewQueue(queueFilter)} style={{ padding: "5px 8px" }} title="Refresh Queue">
                <RefreshCw size={13} className={queueLoading ? "spin" : ""} />
              </button>
            </div>
          </div>

          {/* Queue Table */}
          <div className="table-container">
            <table className="enterprise-table">
              <thead>
                <tr>
                  <th style={{ width: "60px" }}>ID</th>
                  <th>Vendor Name</th>
                  <th>Invoice Number</th>
                  <th>Invoice Date</th>
                  <th style={{ textAlign: "right" }}>Total Amount</th>
                  <th>Status</th>
                  <th>Fusion Status</th>
                  <th style={{ width: "110px", textAlign: "center" }}>Action</th>
                </tr>
              </thead>
              <tbody>
                {queueLoading ? (
                  <tr>
                    <td colSpan={8} style={{ textAlign: "center", padding: "30px", color: "var(--text-secondary)" }}>
                      <Loader2 size={20} className="spin" style={{ margin: "0 auto 8px" }} />
                      Loading Review Queue from Oracle Database...
                    </td>
                  </tr>
                ) : filteredQueue.length === 0 ? (
                  <tr>
                    <td colSpan={8} style={{ textAlign: "center", padding: "30px", color: "var(--text-secondary)" }}>
                      No invoices found matching current filter.
                    </td>
                  </tr>
                ) : (
                  filteredQueue.map((inv) => (
                    <tr
                      key={inv.invoice_id}
                      onClick={() => loadInvoiceForReview(inv.invoice_id)}
                      style={{ cursor: "pointer", backgroundColor: currentInvoiceId === inv.invoice_id ? "var(--color-primary-light)" : undefined }}
                    >
                      <td style={{ fontFamily: "var(--font-mono)", fontWeight: "700", color: "var(--color-primary)" }}>
                        #{inv.invoice_id}
                      </td>
                      <td style={{ fontWeight: "600", color: "var(--text-primary)", maxWidth: "240px" }}>
                        {inv.vendor_name || "—"}
                      </td>
                      <td style={{ fontFamily: "var(--font-mono)" }}>
                        {inv.invoice_number || "—"}
                      </td>
                      <td style={{ color: "var(--text-secondary)", fontSize: "12px" }}>
                        {inv.invoice_date || "—"}
                      </td>
                      <td style={{ textAlign: "right", fontFamily: "var(--font-mono)", fontWeight: "700" }}>
                        {formatAmount(inv.total_amount, inv.currency)}
                      </td>
                      <td>
                        <StatusBadge status={inv.status} />
                      </td>
                      <td>
                        {inv.fusion_invoice_id ? (
                          <span style={{ fontSize: "11px", color: "var(--color-success)", fontWeight: "600", display: "inline-flex", alignItems: "center", gap: "4px" }}>
                            <CheckCircle2 size={12} /> {inv.fusion_invoice_id}
                          </span>
                        ) : inv.fusion_status ? (
                          <StatusBadge status={inv.fusion_status} />
                        ) : (
                          <span style={{ fontSize: "11px", color: "var(--text-muted)" }}>Not Submitted</span>
                        )}
                      </td>
                      <td style={{ textAlign: "center" }}>
                        <button
                          className="btn btn-secondary"
                          style={{ padding: "3px 10px", fontSize: "11.5px" }}
                          onClick={(e) => {
                            e.stopPropagation();
                            loadInvoiceForReview(inv.invoice_id);
                          }}
                        >
                          Review <ChevronRight size={12} />
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* ============================================================= */}
      {/* VIEW 3: INVOICE REVIEW WORKSPACE (HUMAN REVIEW & EDITING)     */}
      {/* ============================================================= */}
      {activeView === "review" && reviewData && (
        <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
          {/* Header Bar */}
          <div
            className="card"
            style={{
              padding: "16px 20px",
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              flexWrap: "wrap",
              gap: "12px",
            }}
          >
            <div>
              <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                <h3 style={{ fontSize: "17px", fontWeight: "800", color: "var(--text-primary)", margin: 0 }}>
                  Invoice Review: #{reviewData.invoice_id} ({reviewData.document_name})
                </h3>
                <StatusBadge status={reviewData.status} />
              </div>
              <div style={{ fontSize: "12px", color: "var(--text-secondary)", marginTop: "4px" }}>
                Extracted via OCI • Created: {reviewData.created_at || "—"} • Reviewed By: {reviewData.reviewed_by || "Pending Review"}
              </div>
            </div>

            <div style={{ display: "flex", alignItems: "center", gap: "10px", flexWrap: "wrap" }}>
              <button
                className="btn btn-secondary"
                onClick={handleSaveCorrections}
                style={{ fontSize: "12.5px" }}
              >
                <Save size={14} />
                Save Corrections
              </button>

              {reviewData.status === "REVIEW_REQUIRED" && (
                <>
                  <button
                    className="btn btn-secondary"
                    onClick={() => setIsRejectModalOpen(true)}
                    style={{ fontSize: "12.5px", color: "#b91c1c" }}
                  >
                    <XCircle size={14} />
                    Reject
                  </button>

                  <button
                    className="btn btn-primary"
                    onClick={handleApproveInvoice}
                    style={{ fontSize: "12.5px", backgroundColor: "#059669" }}
                  >
                    <CheckCircle2 size={14} />
                    Approve Invoice
                  </button>
                </>
              )}

              <button
                className="btn btn-primary"
                onClick={() => setActiveView("fusion")}
                style={{ fontSize: "12.5px" }}
              >
                Oracle Fusion Mapping <ArrowRight size={14} />
              </button>
            </div>
          </div>

          {/* Side-by-Side: Left = Editable Header Fields, Right = Audit / Confidence Snapshot */}
          <div className="grid-3" style={{ gap: "20px" }}>
            {/* Left 2 Cols: Editable Header Form */}
            <div className="card" style={{ gridColumn: "span 2", padding: "20px" }}>
              <div className="card-header" style={{ marginBottom: "16px" }}>
                <h3 className="card-title" style={{ fontSize: "15px", fontWeight: "700" }}>
                  <Edit3 size={15} style={{ color: "var(--color-primary)" }} />
                  Invoice Header Data (Editable Corrections)
                </h3>
                <span style={{ fontSize: "11.5px", color: "var(--text-secondary)" }}>
                  Changes are saved separately to preserve original OCI audit trail
                </span>
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px" }}>
                {/* Vendor Name */}
                <div style={{ gridColumn: "span 2" }}>
                  <label style={{ fontSize: "12px", fontWeight: "600", color: "var(--text-secondary)", display: "block", marginBottom: "4px" }}>
                    Vendor Name
                  </label>
                  <input
                    type="text"
                    className="input"
                    value={editForm.vendor_name}
                    onChange={(e) => setEditForm({ ...editForm, vendor_name: e.target.value })}
                    style={{ width: "100%", fontWeight: "600" }}
                  />
                </div>

                {/* Invoice Number */}
                <div>
                  <label style={{ fontSize: "12px", fontWeight: "600", color: "var(--text-secondary)", display: "block", marginBottom: "4px" }}>
                    Invoice Number
                  </label>
                  <input
                    type="text"
                    className="input"
                    value={editForm.invoice_number}
                    onChange={(e) => setEditForm({ ...editForm, invoice_number: e.target.value })}
                    style={{ width: "100%", fontFamily: "var(--font-mono)" }}
                  />
                </div>

                {/* Invoice Date */}
                <div>
                  <label style={{ fontSize: "12px", fontWeight: "600", color: "var(--text-secondary)", display: "block", marginBottom: "4px" }}>
                    Invoice Date (YYYY-MM-DD)
                  </label>
                  <input
                    type="date"
                    className="input"
                    value={editForm.invoice_date}
                    onChange={(e) => setEditForm({ ...editForm, invoice_date: e.target.value })}
                    style={{ width: "100%" }}
                  />
                </div>

                {/* Due Date */}
                <div>
                  <label style={{ fontSize: "12px", fontWeight: "600", color: "var(--text-secondary)", display: "block", marginBottom: "4px" }}>
                    Due Date (YYYY-MM-DD)
                  </label>
                  <input
                    type="date"
                    className="input"
                    value={editForm.due_date}
                    onChange={(e) => setEditForm({ ...editForm, due_date: e.target.value })}
                    style={{ width: "100%" }}
                  />
                </div>

                {/* Currency */}
                <div>
                  <label style={{ fontSize: "12px", fontWeight: "600", color: "var(--text-secondary)", display: "block", marginBottom: "4px" }}>
                    Currency
                  </label>
                  <input
                    type="text"
                    className="input"
                    value={editForm.currency}
                    onChange={(e) => setEditForm({ ...editForm, currency: e.target.value })}
                    style={{ width: "100%" }}
                  />
                </div>

                {/* Subtotal */}
                <div>
                  <label style={{ fontSize: "12px", fontWeight: "600", color: "var(--text-secondary)", display: "block", marginBottom: "4px" }}>
                    Subtotal Amount
                  </label>
                  <input
                    type="number"
                    step="0.01"
                    className="input"
                    value={editForm.subtotal}
                    onChange={(e) => setEditForm({ ...editForm, subtotal: e.target.value })}
                    style={{ width: "100%", fontFamily: "var(--font-mono)" }}
                  />
                </div>

                {/* Tax Amount */}
                <div>
                  <label style={{ fontSize: "12px", fontWeight: "600", color: "var(--text-secondary)", display: "block", marginBottom: "4px" }}>
                    Tax Amount
                  </label>
                  <input
                    type="number"
                    step="0.01"
                    className="input"
                    value={editForm.tax_amount}
                    onChange={(e) => setEditForm({ ...editForm, tax_amount: e.target.value })}
                    style={{ width: "100%", fontFamily: "var(--font-mono)" }}
                  />
                </div>

                {/* Total Amount */}
                <div style={{ gridColumn: "span 2" }}>
                  <label style={{ fontSize: "12px", fontWeight: "700", color: "var(--color-primary)", display: "block", marginBottom: "4px" }}>
                    Total Invoice Amount *
                  </label>
                  <input
                    type="number"
                    step="0.01"
                    className="input"
                    value={editForm.total_amount}
                    onChange={(e) => setEditForm({ ...editForm, total_amount: e.target.value })}
                    style={{ width: "100%", fontWeight: "800", fontSize: "15px", fontFamily: "var(--font-mono)" }}
                  />
                </div>

                {/* PO Number */}
                <div>
                  <label style={{ fontSize: "12px", fontWeight: "600", color: "var(--text-secondary)", display: "block", marginBottom: "4px" }}>
                    PO Reference
                  </label>
                  <input
                    type="text"
                    className="input"
                    value={editForm.po_number}
                    onChange={(e) => setEditForm({ ...editForm, po_number: e.target.value })}
                    style={{ width: "100%" }}
                  />
                </div>

                {/* Payment Terms */}
                <div>
                  <label style={{ fontSize: "12px", fontWeight: "600", color: "var(--text-secondary)", display: "block", marginBottom: "4px" }}>
                    Payment Terms
                  </label>
                  <input
                    type="text"
                    className="input"
                    value={editForm.payment_terms}
                    onChange={(e) => setEditForm({ ...editForm, payment_terms: e.target.value })}
                    style={{ width: "100%" }}
                  />
                </div>
              </div>
            </div>

            {/* Right Col: Original OCI Snapshot & Audit */}
            <div className="card" style={{ padding: "20px", display: "flex", flexDirection: "column", gap: "14px" }}>
              <div className="card-header">
                <h3 className="card-title" style={{ fontSize: "14.5px", fontWeight: "700" }}>
                  <ShieldCheck size={16} style={{ color: "var(--color-success)" }} />
                  Original OCI Snapshot
                </h3>
              </div>

              <div style={{ fontSize: "12px", color: "var(--text-secondary)", lineHeight: "1.5" }}>
                The original values extracted by OCI Document Understanding are preserved below for compliance and audit.
              </div>

              {reviewData.original_snapshot?.invoice ? (
                <div style={{ display: "flex", flexDirection: "column", gap: "10px", fontSize: "12.5px" }}>
                  <div style={{ padding: "8px 10px", backgroundColor: "var(--bg-surface-subtle)", borderRadius: "var(--radius-sm)" }}>
                    <span style={{ color: "var(--text-secondary)", fontSize: "11px", display: "block" }}>Original Vendor</span>
                    <strong style={{ color: "var(--text-primary)" }}>{reviewData.original_snapshot.invoice.vendor_name || "—"}</strong>
                  </div>
                  <div style={{ padding: "8px 10px", backgroundColor: "var(--bg-surface-subtle)", borderRadius: "var(--radius-sm)" }}>
                    <span style={{ color: "var(--text-secondary)", fontSize: "11px", display: "block" }}>Original Invoice #</span>
                    <strong style={{ fontFamily: "var(--font-mono)", color: "var(--color-primary)" }}>
                      {reviewData.original_snapshot.invoice.invoice_number || "—"}
                    </strong>
                  </div>
                  <div style={{ padding: "8px 10px", backgroundColor: "var(--bg-surface-subtle)", borderRadius: "var(--radius-sm)" }}>
                    <span style={{ color: "var(--text-secondary)", fontSize: "11px", display: "block" }}>Original Total</span>
                    <strong style={{ fontFamily: "var(--font-mono)" }}>
                      {formatAmount(reviewData.original_snapshot.invoice.total_amount)}
                    </strong>
                  </div>
                  <div style={{ padding: "8px 10px", backgroundColor: "var(--bg-surface-subtle)", borderRadius: "var(--radius-sm)" }}>
                    <span style={{ color: "var(--text-secondary)", fontSize: "11px", display: "block" }}>Original Date</span>
                    <strong>{reviewData.original_snapshot.invoice.invoice_date || "—"}</strong>
                  </div>
                </div>
              ) : (
                <div style={{ color: "var(--text-muted)", fontSize: "12px" }}>No snapshot recorded.</div>
              )}

              {/* Review Audit History */}
              <div style={{ marginTop: "auto", paddingTop: "12px", borderTop: "1px solid var(--border-subtle)" }}>
                <span style={{ fontSize: "11.5px", fontWeight: "700", color: "var(--text-secondary)", textTransform: "uppercase", display: "block", marginBottom: "6px" }}>
                  Review History
                </span>
                <div style={{ fontSize: "12px", color: "var(--text-secondary)" }}>
                  <div><strong>Reviewer:</strong> {reviewData.reviewed_by || "Not reviewed yet"}</div>
                  <div><strong>Time:</strong> {reviewData.reviewed_at || "—"}</div>
                  {reviewData.review_comments && (
                    <div style={{ marginTop: "4px", fontStyle: "italic", color: "var(--text-primary)" }}>
                      "{reviewData.review_comments}"
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>

          {/* Line Items Table */}
          <div className="card" style={{ padding: "20px" }}>
            <div className="card-header" style={{ marginBottom: "14px" }}>
              <h3 className="card-title" style={{ fontSize: "15px", fontWeight: "700" }}>
                <FileSpreadsheet size={15} style={{ color: "var(--color-primary)" }} />
                Line Items Breakdown ({editLines.length})
              </h3>
            </div>

            <div className="table-container">
              <table className="enterprise-table">
                <thead>
                  <tr>
                    <th style={{ width: "45px" }}>#</th>
                    <th>Description</th>
                    <th>Product / Item Code</th>
                    <th style={{ width: "90px", textAlign: "right" }}>Qty</th>
                    <th style={{ width: "120px", textAlign: "right" }}>Unit Price</th>
                    <th style={{ width: "110px", textAlign: "right" }}>Tax</th>
                    <th style={{ width: "130px", textAlign: "right" }}>Line Amount</th>
                  </tr>
                </thead>
                <tbody>
                  {editLines.map((line, idx) => (
                    <tr key={idx}>
                      <td style={{ fontFamily: "var(--font-mono)", fontWeight: "600", color: "var(--text-muted)" }}>
                        {line.line_number || idx + 1}
                      </td>
                      <td>
                        <input
                          type="text"
                          className="input"
                          value={line.description || ""}
                          onChange={(e) => {
                            const newLines = [...editLines];
                            newLines[idx].description = e.target.value;
                            setEditLines(newLines);
                          }}
                          style={{ width: "100%", fontSize: "12px" }}
                        />
                      </td>
                      <td>
                        <input
                          type="text"
                          className="input"
                          value={line.item_number || ""}
                          onChange={(e) => {
                            const newLines = [...editLines];
                            newLines[idx].item_number = e.target.value;
                            setEditLines(newLines);
                          }}
                          style={{ width: "100%", fontSize: "12px", fontFamily: "var(--font-mono)" }}
                        />
                      </td>
                      <td>
                        <input
                          type="number"
                          className="input"
                          value={line.quantity !== null && line.quantity !== undefined ? line.quantity : ""}
                          onChange={(e) => {
                            const newLines = [...editLines];
                            newLines[idx].quantity = e.target.value ? parseFloat(e.target.value) : null;
                            setEditLines(newLines);
                          }}
                          style={{ width: "100%", textAlign: "right", fontSize: "12px", fontFamily: "var(--font-mono)" }}
                        />
                      </td>
                      <td>
                        <input
                          type="number"
                          step="0.01"
                          className="input"
                          value={line.unit_price !== null && line.unit_price !== undefined ? line.unit_price : ""}
                          onChange={(e) => {
                            const newLines = [...editLines];
                            newLines[idx].unit_price = e.target.value ? parseFloat(e.target.value) : null;
                            setEditLines(newLines);
                          }}
                          style={{ width: "100%", textAlign: "right", fontSize: "12px", fontFamily: "var(--font-mono)" }}
                        />
                      </td>
                      <td>
                        <input
                          type="number"
                          step="0.01"
                          className="input"
                          value={line.tax_amount !== null && line.tax_amount !== undefined ? line.tax_amount : ""}
                          onChange={(e) => {
                            const newLines = [...editLines];
                            newLines[idx].tax_amount = e.target.value ? parseFloat(e.target.value) : null;
                            setEditLines(newLines);
                          }}
                          style={{ width: "100%", textAlign: "right", fontSize: "12px", fontFamily: "var(--font-mono)" }}
                        />
                      </td>
                      <td>
                        <input
                          type="number"
                          step="0.01"
                          className="input"
                          value={line.line_amount !== null && line.line_amount !== undefined ? line.line_amount : ""}
                          onChange={(e) => {
                            const newLines = [...editLines];
                            newLines[idx].line_amount = e.target.value ? parseFloat(e.target.value) : null;
                            setEditLines(newLines);
                          }}
                          style={{ width: "100%", textAlign: "right", fontWeight: "700", fontSize: "12.5px", fontFamily: "var(--font-mono)" }}
                        />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* ============================================================= */}
      {/* VIEW 4: ORACLE FUSION INTEGRATION WORKBENCH                   */}
      {/* ============================================================= */}
      {activeView === "fusion" && (
        <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
          {/* Fusion Connection & Destination Selector Banner */}
          <div className="card" style={{ padding: "20px", borderLeft: "4px solid var(--color-primary)" }}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: "16px" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                <Database size={26} style={{ color: "var(--color-primary)" }} />
                <div>
                  <h3 style={{ fontSize: "16px", fontWeight: "700", margin: 0 }}>
                    Oracle Cloud ERP (Fusion Payables) Integration
                  </h3>
                  <p style={{ fontSize: "12px", color: "var(--text-secondary)", margin: "2px 0 0 0" }}>
                    Select an Administrator-configured Oracle Fusion destination environment to map and submit approved invoices.
                  </p>
                </div>
              </div>

              {/* Destination Connection Selector */}
              <div style={{ display: "flex", alignItems: "center", gap: "10px", flexWrap: "wrap" }}>
                <div style={{ display: "flex", flexDirection: "column", gap: "2px" }}>
                  <label style={{ fontSize: "11px", fontWeight: "700", color: "var(--text-secondary)", textTransform: "uppercase" }}>
                    Fusion Destination
                  </label>
                  <select
                    className="input"
                    value={selectedConnectionId || ""}
                    onChange={(e) => {
                      const cid = Number(e.target.value);
                      setSelectedConnectionId(cid);
                      if (currentInvoiceId) {
                        loadFusionMappingForInvoice(currentInvoiceId, cid);
                      }
                    }}
                    style={{ minWidth: "260px", fontWeight: "600", fontSize: "12.5px" }}
                  >
                    {availableConnections.length === 0 ? (
                      <option value="">No Connections Configured</option>
                    ) : (
                      availableConnections.map((conn) => (
                        <option
                          key={conn.connection_id}
                          value={conn.connection_id}
                          disabled={!conn.is_active || conn.status !== "CONNECTED"}
                        >
                          #{conn.connection_id} {conn.connection_name} ({conn.environment}) — [{conn.status}]
                        </option>
                      ))
                    )}
                  </select>
                </div>

                <div style={{ display: "flex", gap: "8px", marginTop: "14px" }}>
                  <button className="btn btn-secondary" onClick={handleOpenFusionPreview} disabled={!selectedConnectionId || !currentInvoiceId} style={{ fontSize: "12.5px" }}>
                    <Eye size={14} />
                    Preview Payload
                  </button>

                  <button
                    className="btn btn-primary"
                    onClick={() => setIsConfirmSubmitModalOpen(true)}
                    disabled={!selectedConnectionId || !currentInvoiceId || reviewData?.status !== "APPROVED" || fusionMappingData?.validation?.is_valid === false}
                    style={{ fontSize: "12.5px" }}
                    title={reviewData?.status !== "APPROVED" ? "Invoice must be APPROVED before submission" : ""}
                  >
                    <Send size={14} />
                    Submit to Fusion
                  </button>
                </div>
              </div>
            </div>

            {/* If no connections exist or none connected */}
            {availableConnections.filter((c) => c.status === "CONNECTED").length === 0 && (
              <div style={{ marginTop: "14px", padding: "10px 14px", borderRadius: "var(--radius-sm)", backgroundColor: "rgba(245, 158, 11, 0.1)", border: "1px solid rgba(245, 158, 11, 0.3)", color: "#d97706", fontSize: "12px", display: "flex", alignItems: "center", gap: "8px" }}>
                <AlertCircle size={15} />
                <span>
                  No active & connected Oracle Fusion endpoints available. Please navigate to <strong>Settings ➔ Oracle Fusion Connections</strong> to configure and test an environment.
                </span>
              </div>
            )}
          </div>

          {/* Sub-view switcher: Mapping Workbench vs Submission History */}
          <div style={{ display: "flex", gap: "8px", borderBottom: "1px solid var(--border-subtle)", paddingBottom: "10px" }}>
            <button
              className={`btn ${fusionSubView === "mapping" ? "btn-primary" : "btn-secondary"}`}
              onClick={() => setFusionSubView("mapping")}
              style={{ fontSize: "12px", padding: "5px 14px" }}
            >
              <Layers size={13} />
              Visual Field Mapping ({currentInvoiceId ? `#${currentInvoiceId}` : "Select Invoice"})
            </button>
            <button
              className={`btn ${fusionSubView === "history" ? "btn-primary" : "btn-secondary"}`}
              onClick={() => {
                setFusionSubView("history");
                loadFusionSubmissionsList();
              }}
              style={{ fontSize: "12px", padding: "5px 14px" }}
            >
              <Clock size={13} />
              Submission History
              {fusionSubmissionsList.length > 0 && (
                <span style={{ marginLeft: "6px", padding: "1px 6px", borderRadius: "10px", backgroundColor: "rgba(255,255,255,0.25)", fontSize: "11px", fontWeight: "700" }}>
                  {fusionSubmissionsList.length}
                </span>
              )}
            </button>
          </div>

          {/* SUB-VIEW 1: MAPPING WORKBENCH */}
          {fusionSubView === "mapping" && (
            <>
              {/* Submission Receipt if available */}
              {reviewData?.fusion_invoice_id && (
                <div className="card" style={{ padding: "18px 22px", backgroundColor: "rgba(16, 185, 129, 0.05)", border: "1px solid rgba(16, 185, 129, 0.3)" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "10px", color: "var(--color-success)", fontWeight: "700", fontSize: "14.5px" }}>
                    <CheckCircle2 size={20} />
                    Oracle Fusion Invoice Created Successfully
                  </div>
                  <div style={{ fontSize: "12.5px", color: "var(--text-secondary)", marginTop: "6px" }}>
                    Fusion Invoice ID: <code style={{ fontFamily: "var(--font-mono)", fontWeight: "700", color: "var(--text-primary)" }}>{reviewData.fusion_invoice_id}</code> • Submitted: {reviewData.fusion_submitted_at || "Just now"}
                  </div>
                </div>
              )}

              {/* Visual Field Mapping Workbench: HEADER and LINES */}
              {fusionMappingData ? (
                <div className="card" style={{ padding: "20px" }}>
                  <div className="card-header" style={{ marginBottom: "16px" }}>
                    <div>
                      <h3 className="card-title" style={{ fontSize: "15px", fontWeight: "700" }}>
                        <Layers size={16} style={{ color: "var(--color-primary)" }} />
                        Visual Field Mapping (GSVAI ➔ Oracle Fusion REST API)
                      </h3>
                      <p className="card-subtitle" style={{ fontSize: "12px" }}>
                        Schema validation for Connection #{selectedConnectionId}: {fusionMappingData.connection_name || "Active Connection"}
                      </p>
                    </div>
                    {fusionMappingData.validation?.is_valid ? (
                      <span className="badge badge-live">Schema Validated</span>
                    ) : (
                      <span className="badge" style={{ backgroundColor: "rgba(239, 68, 68, 0.1)", color: "#b91c1c" }}>
                        Missing Required Fields
                      </span>
                    )}
                  </div>

                  {/* HEADER SECTION MAPPING */}
                  <div style={{ marginBottom: "24px" }}>
                    <h4 style={{ fontSize: "13px", fontWeight: "700", color: "var(--color-primary)", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "10px" }}>
                      Invoice Header Fields
                    </h4>
                    <div className="table-container">
                      <table className="enterprise-table">
                        <thead>
                          <tr>
                            <th>GSVAI Extracted Field</th>
                            <th>OCI Field</th>
                            <th>Extracted / Verified Value</th>
                            <th style={{ width: "110px", textAlign: "center" }}>Confidence</th>
                            <th>Oracle Fusion Field</th>
                            <th style={{ width: "90px" }}>Req</th>
                            <th style={{ width: "90px", textAlign: "center" }}>Status</th>
                          </tr>
                        </thead>
                        <tbody>
                          {fusionMappingData.header_mappings?.map((m, idx) => (
                            <tr key={idx}>
                              <td style={{ fontWeight: "600", color: "var(--text-primary)" }}>
                                {m.source_label}
                                <span style={{ display: "block", fontSize: "10.5px", fontFamily: "var(--font-mono)", color: "var(--text-muted)" }}>{m.source_field}</span>
                              </td>
                              <td>
                                <code style={{ fontSize: "11.5px", padding: "2px 6px", backgroundColor: "var(--bg-surface-subtle)", borderRadius: "4px" }}>
                                  {m.source_field.replace(/_/g, "")}
                                </code>
                              </td>
                              <td style={{ fontWeight: "600", maxWidth: "220px", overflow: "hidden", textOverflow: "ellipsis" }}>
                                {m.extracted_value !== null ? String(m.extracted_value) : "—"}
                              </td>
                              <td style={{ textAlign: "center" }}>
                                {renderConfidenceBadge(m.confidence)}
                              </td>
                              <td>
                                <code style={{ fontSize: "12px", fontWeight: "700", color: "var(--color-primary)", backgroundColor: "var(--color-primary-light)", padding: "2px 6px", borderRadius: "4px" }}>
                                  {m.target_field}
                                </code>
                              </td>
                              <td>
                                {m.required ? (
                                  <span style={{ fontSize: "11px", color: "#b91c1c", fontWeight: "700" }}>Required *</span>
                                ) : (
                                  <span style={{ fontSize: "11px", color: "var(--text-muted)" }}>Optional</span>
                                )}
                              </td>
                              <td style={{ textAlign: "center" }}>
                                <span style={{ fontSize: "11px", padding: "2px 8px", borderRadius: "10px", backgroundColor: "rgba(16, 185, 129, 0.1)", color: "var(--color-success)", fontWeight: "600" }}>
                                  ✓ Valid
                                </span>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>

                  {/* LINES SECTION MAPPING */}
                  <div>
                    <h4 style={{ fontSize: "13px", fontWeight: "700", color: "var(--color-primary)", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "10px" }}>
                      Invoice Line Items
                    </h4>
                    <div className="table-container">
                      <table className="enterprise-table">
                        <thead>
                          <tr>
                            <th>GSVAI Line Field</th>
                            <th>Sample Line Value</th>
                            <th>Oracle Fusion Field</th>
                            <th style={{ width: "90px" }}>Req</th>
                            <th style={{ width: "90px", textAlign: "center" }}>Status</th>
                          </tr>
                        </thead>
                        <tbody>
                          {fusionMappingData.line_mappings?.map((m, idx) => (
                            <tr key={idx}>
                              <td style={{ fontWeight: "600", color: "var(--text-primary)" }}>
                                {m.source_label}
                                <span style={{ display: "block", fontSize: "10.5px", fontFamily: "var(--font-mono)", color: "var(--text-muted)" }}>{m.source_field}</span>
                              </td>
                              <td style={{ fontWeight: "500", maxWidth: "260px", overflow: "hidden", textOverflow: "ellipsis" }}>
                                {m.extracted_value !== null ? String(m.extracted_value) : "—"}
                              </td>
                              <td>
                                <code style={{ fontSize: "12px", fontWeight: "700", color: "var(--color-primary)", backgroundColor: "var(--color-primary-light)", padding: "2px 6px", borderRadius: "4px" }}>
                                  {m.target_field}
                                </code>
                              </td>
                              <td>
                                {m.required ? (
                                  <span style={{ fontSize: "11px", color: "#b91c1c", fontWeight: "700" }}>Required *</span>
                                ) : (
                                  <span style={{ fontSize: "11px", color: "var(--text-muted)" }}>Optional</span>
                                )}
                              </td>
                              <td style={{ textAlign: "center" }}>
                                <span style={{ fontSize: "11px", padding: "2px 8px", borderRadius: "10px", backgroundColor: "rgba(16, 185, 129, 0.1)", color: "var(--color-success)", fontWeight: "600" }}>
                                  ✓ Valid
                                </span>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="card" style={{ padding: "30px", textAlign: "center", color: "var(--text-secondary)" }}>
                  <AlertCircle size={24} style={{ color: "var(--text-muted)", margin: "0 auto 10px" }} />
                  Please select an invoice from the <strong>Review Queue</strong> to inspect field mappings.
                </div>
              )}
            </>
          )}

          {/* SUB-VIEW 2: SUBMISSION HISTORY */}
          {fusionSubView === "history" && (
            <div className="card" style={{ padding: "20px" }}>
              <div className="card-header" style={{ marginBottom: "16px" }}>
                <div>
                  <h3 className="card-title" style={{ fontSize: "15px", fontWeight: "700" }}>
                    <History size={16} style={{ color: "var(--color-primary)" }} />
                    Oracle Fusion Submission History
                  </h3>
                  <p className="card-subtitle" style={{ fontSize: "12px" }}>
                    Audit record of all invoices submitted to Oracle Fusion ERP (GSVAI_FUSION_SUBMISSIONS)
                  </p>
                </div>
                <button className="btn btn-secondary" onClick={loadFusionSubmissionsList} style={{ fontSize: "12px" }}>
                  <RefreshCw size={13} /> Refresh
                </button>
              </div>

              <div className="table-container">
                <table className="enterprise-table">
                  <thead>
                    <tr>
                      <th>Submission ID</th>
                      <th>Invoice ID</th>
                      <th>Target Connection</th>
                      <th>Environment</th>
                      <th>Fusion Invoice ID</th>
                      <th>Supplier / Inv #</th>
                      <th>Amount</th>
                      <th>Submitted At</th>
                      <th>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {fusionSubmissionsList.length === 0 ? (
                      <tr><td colSpan={9} style={{ textAlign: "center", padding: "24px" }}>No submissions recorded yet.</td></tr>
                    ) : (
                      fusionSubmissionsList.map((sub) => (
                        <tr key={sub.submission_id}>
                          <td style={{ fontFamily: "var(--font-mono)", fontWeight: "700", color: "var(--color-primary)" }}>
                            #{sub.submission_id}
                          </td>
                          <td style={{ fontFamily: "var(--font-mono)" }}>#{sub.invoice_id}</td>
                          <td style={{ fontWeight: "600" }}>{sub.connection_name || `Connection #${sub.connection_id}`}</td>
                          <td>
                            <span style={{ padding: "2px 6px", borderRadius: "8px", backgroundColor: "var(--bg-surface-subtle)", fontSize: "11px", fontWeight: "700" }}>
                              {sub.environment}
                            </span>
                          </td>
                          <td style={{ fontFamily: "var(--font-mono)", fontWeight: "700", color: "var(--color-success)" }}>
                            {sub.fusion_invoice_id || "—"}
                          </td>
                          <td style={{ fontSize: "12px" }}>{sub.vendor_name || sub.invoice_number || "—"}</td>
                          <td style={{ fontFamily: "var(--font-mono)", fontWeight: "600" }}>
                            {formatAmount(sub.total_amount, sub.currency)}
                          </td>
                          <td style={{ fontSize: "11.5px", color: "var(--text-secondary)" }}>{sub.submitted_at ? sub.submitted_at.slice(0, 19) : "—"}</td>
                          <td>
                            <span style={{ fontSize: "11px", padding: "2px 8px", borderRadius: "10px", backgroundColor: "rgba(16, 185, 129, 0.1)", color: "#047857", fontWeight: "700" }}>
                              {sub.status || "FUSION_CREATED"}
                            </span>
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}

      {/* ============================================================= */}
      {/* MODAL 1: REJECTION REASON MODAL                               */}
      {/* ============================================================= */}
      {isRejectModalOpen && (
        <div
          style={{
            position: "fixed",
            top: 0,
            left: 0,
            width: "100vw",
            height: "100vh",
            backgroundColor: "rgba(0, 0, 0, 0.5)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 1000,
          }}
        >
          <div className="card animate-scale-up" style={{ width: "460px", padding: "24px" }}>
            <h3 style={{ fontSize: "16px", fontWeight: "700", color: "#b91c1c", marginBottom: "8px", display: "flex", alignItems: "center", gap: "8px" }}>
              <XCircle size={18} />
              Reject Invoice #{currentInvoiceId}
            </h3>
            <p style={{ fontSize: "12.5px", color: "var(--text-secondary)", marginBottom: "14px" }}>
              Please provide a mandatory reason for rejecting this invoice. The invoice will be marked as REJECTED and prevented from ERP submission.
            </p>

            <textarea
              rows={4}
              className="input"
              placeholder="e.g. Incorrect tax calculation / Vendor tax ID mismatch..."
              value={rejectReason}
              onChange={(e) => setRejectReason(e.target.value)}
              style={{ width: "100%", marginBottom: "18px" }}
            />

            <div style={{ display: "flex", justifyContent: "flex-end", gap: "10px" }}>
              <button className="btn btn-secondary" onClick={() => setIsRejectModalOpen(false)}>
                Cancel
              </button>
              <button
                className="btn btn-primary"
                onClick={handleRejectInvoice}
                disabled={!rejectReason.trim()}
                style={{ backgroundColor: "#b91c1c" }}
              >
                Reject Invoice
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ============================================================= */}
      {/* MODAL 2: ORACLE FUSION PAYLOAD PREVIEW MODAL                  */}
      {/* ============================================================= */}
      {isPreviewModalOpen && fusionPreviewPayload && (
        <div
          style={{
            position: "fixed",
            top: 0,
            left: 0,
            width: "100vw",
            height: "100vh",
            backgroundColor: "rgba(0, 0, 0, 0.5)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 1000,
          }}
        >
          <div className="card animate-scale-up" style={{ width: "620px", maxHeight: "80vh", display: "flex", flexDirection: "column", padding: "24px" }}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "14px" }}>
              <h3 style={{ fontSize: "16px", fontWeight: "700", margin: 0, display: "flex", alignItems: "center", gap: "8px" }}>
                <Eye size={18} style={{ color: "var(--color-primary)" }} />
                Oracle Fusion REST API Payload Preview
              </h3>
              <button onClick={() => setIsPreviewModalOpen(false)} style={{ background: "none", border: "none", cursor: "pointer", fontSize: "16px" }}>✕</button>
            </div>

            <p style={{ fontSize: "12px", color: "var(--text-secondary)", marginBottom: "12px" }}>
              Target Environment: <strong>{availableConnections.find((c) => c.connection_id === selectedConnectionId)?.connection_name || "Oracle Fusion"}</strong>
            </p>

            <pre
              style={{
                backgroundColor: "var(--bg-surface-subtle)",
                padding: "14px",
                borderRadius: "var(--radius-md)",
                border: "1px solid var(--border-subtle)",
                overflowY: "auto",
                flex: 1,
                fontSize: "12px",
                fontFamily: "var(--font-mono)",
                color: "var(--text-primary)",
              }}
            >
              {JSON.stringify(fusionPreviewPayload, null, 2)}
            </pre>

            <div style={{ display: "flex", justifyContent: "flex-end", gap: "10px", marginTop: "16px" }}>
              <button
                className="btn btn-secondary"
                onClick={() => handleCopyText(JSON.stringify(fusionPreviewPayload, null, 2), "payload")}
              >
                {copiedField === "payload" ? <Check size={14} /> : <Copy size={14} />}
                Copy JSON
              </button>
              <button className="btn btn-primary" onClick={() => setIsPreviewModalOpen(false)}>
                Close Preview
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ============================================================= */}
      {/* MODAL 3: CONFIRM FUSION SUBMISSION MODAL                      */}
      {/* ============================================================= */}
      {isConfirmSubmitModalOpen && (
        <div
          style={{
            position: "fixed",
            top: 0,
            left: 0,
            width: "100vw",
            height: "100vh",
            backgroundColor: "rgba(0, 0, 0, 0.5)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 1000,
          }}
        >
          <div className="card animate-scale-up" style={{ width: "480px", padding: "24px" }}>
            <h3 style={{ fontSize: "16px", fontWeight: "700", color: "var(--color-primary)", marginBottom: "8px", display: "flex", alignItems: "center", gap: "8px" }}>
              <Send size={18} />
              Confirm Oracle Fusion ERP Submission
            </h3>
            <p style={{ fontSize: "13px", color: "var(--text-secondary)", marginBottom: "16px", lineHeight: "1.5" }}>
              You are submitting Invoice <strong>#{reviewData?.invoice_number || currentInvoiceId}</strong> (Amount: <strong>{formatAmount(reviewData?.total_amount, reviewData?.currency)}</strong>) to Oracle Fusion Cloud ERP Payables.
            </p>

            <div
              style={{
                backgroundColor: "var(--bg-surface-subtle)",
                padding: "12px 14px",
                borderRadius: "var(--radius-md)",
                border: "1px solid var(--border-subtle)",
                fontSize: "12px",
                marginBottom: "20px",
              }}
            >
              <div><strong>Supplier:</strong> {reviewData?.vendor_name}</div>
              <div><strong>Target Connection:</strong> {availableConnections.find((c) => c.connection_id === selectedConnectionId)?.connection_name} (ID: {selectedConnectionId})</div>
              <div><strong>Environment:</strong> {availableConnections.find((c) => c.connection_id === selectedConnectionId)?.environment}</div>
              <div><strong>Business Unit:</strong> {availableConnections.find((c) => c.connection_id === selectedConnectionId)?.business_unit}</div>
            </div>

            <div style={{ display: "flex", justifyContent: "flex-end", gap: "10px" }}>
              <button className="btn btn-secondary" onClick={() => setIsConfirmSubmitModalOpen(false)}>
                Cancel
              </button>
              <button
                className="btn btn-primary"
                onClick={handleConfirmFusionSubmit}
                disabled={fusionSubmitting}
              >
                {fusionSubmitting ? <><Loader2 size={14} className="spin" /> Submitting...</> : "Confirm & Submit"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
