import React, { useState, useEffect, useRef } from "react";
import {
  UploadCloud,
  FileText,
  CheckCircle2,
  Clock,
  Layers,
  Sparkles,
  RefreshCw,
  Shield,
  AlertCircle,
} from "lucide-react";
import { SectionHeader } from "../../common/SectionHeader";
import { StatusBadge } from "../../common/Badge";
import {
  analyzeDocument,
  fetchDocumentIntelligenceRecords,
  fetchDocumentIntelligenceAnalysis,
} from "../../../api/client";

const DOC_TYPES = [
  { id: "contract", label: "Master Services Agreement / Contract" },
  { id: "invoice", label: "Commercial Invoice" },
  { id: "po", label: "Purchase Order" },
  { id: "id_doc", label: "Identity & Compliance Document" },
];

export function DocumentIntelligenceView() {
  const [selectedType, setSelectedType] = useState("contract");
  const [isProcessing, setIsProcessing] = useState(false);
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);
  const [isLoadingDetail, setIsLoadingDetail] = useState(false);
  const [selectedFile, setSelectedFile] = useState(null);
  const [uploadedFileName, setUploadedFileName] = useState("No document selected");
  const [analysisResult, setAnalysisResult] = useState(null);
  const [selectedAnalysisId, setSelectedAnalysisId] = useState(null);
  const [errorMessage, setErrorMessage] = useState(null);
  const [isDragging, setIsDragging] = useState(false);
  const [history, setHistory] = useState([]);

  const fileInputRef = useRef(null);

  // Load persisted history records on component mount
  useEffect(() => {
    loadPersistedRecords();
  }, []);

  const loadPersistedRecords = async () => {
    try {
      setIsLoadingHistory(true);
      const data = await fetchDocumentIntelligenceRecords();
      if (data && data.documents && data.documents.length > 0) {
        setHistory(data.documents);
        // Automatically load the latest document analysis if none is currently selected
        const latestId = data.documents[0].analysis_id;
        handleSelectRecord(latestId);
      } else {
        setHistory([]);
      }
    } catch (err) {
      console.error("Failed to load document intelligence records:", err);
    } finally {
      setIsLoadingHistory(false);
    }
  };

  const handleSelectRecord = async (analysisId) => {
    if (!analysisId) return;
    setSelectedAnalysisId(analysisId);
    setIsLoadingDetail(true);
    setErrorMessage(null);

    try {
      const data = await fetchDocumentIntelligenceAnalysis(analysisId);
      if (data && data.analysis) {
        setAnalysisResult(data.analysis);
        setUploadedFileName(data.analysis.document_name || "Document");
      }
    } catch (err) {
      console.error(`Failed to load analysis #${analysisId}:`, err);
      setErrorMessage(err.message || `Failed to load document analysis #${analysisId}`);
    } finally {
      setIsLoadingDetail(false);
    }
  };

  const handleFileProcess = async (file) => {
    if (!file) return;

    if (!file.name.toLowerCase().endsWith(".pdf")) {
      setErrorMessage("Only PDF files are currently supported for Document Intelligence.");
      return;
    }

    setErrorMessage(null);
    setIsProcessing(true);
    setSelectedFile(file);
    setUploadedFileName(file.name);

    try {
      const result = await analyzeDocument(file);
      setAnalysisResult(result);
      if (result.analysis_id) {
        setSelectedAnalysisId(result.analysis_id);
      }

      // Refresh persisted history list from Oracle database
      const recordsData = await fetchDocumentIntelligenceRecords();
      if (recordsData && recordsData.documents) {
        setHistory(recordsData.documents);
      }
    } catch (err) {
      console.error("Document Intelligence OCI error:", err);
      setErrorMessage(err.message || "Failed to analyze document with OCI Document Understanding.");
    } finally {
      setIsProcessing(false);
    }
  };

  const handleDropzoneClick = () => {
    if (fileInputRef.current && !isProcessing) {
      fileInputRef.current.click();
    }
  };

  const handleRunOcrClick = (e) => {
    e.stopPropagation();
    if (isProcessing) return;

    if (selectedFile) {
      handleFileProcess(selectedFile);
    } else if (fileInputRef.current) {
      fileInputRef.current.click();
    }
  };

  const handleFileInputChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      handleFileProcess(e.target.files[0]);
    }
    e.target.value = "";
  };

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
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileProcess(e.dataTransfer.files[0]);
    }
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return "Just now";
    try {
      const d = new Date(dateStr);
      return d.toLocaleString(undefined, {
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      });
    } catch {
      return dateStr;
    }
  };

  const getPageCount = () => {
    if (!analysisResult) return 0;
    return analysisResult.page_count ?? analysisResult.pages ?? 0;
  };

  const getTextPageCount = () => {
    if (!analysisResult) return 0;
    return analysisResult.text_page_count ?? analysisResult.text_pages ?? 0;
  };

  const getOcrRequiredPages = () => {
    if (!analysisResult) return 0;
    return analysisResult.ocr_required_pages ?? 0;
  };

  const getPipelineSteps = () => {
    if (isProcessing) {
      return [
        {
          step: 1,
          label: "Document Ingestion & Parsing",
          status: "active",
          desc: "Uploading to OCI Object Storage...",
        },
        {
          step: 2,
          label: "OCR & Text Layer Reconstruction",
          status: "active",
          desc: "OCI Document Understanding processor job running...",
        },
        {
          step: 3,
          label: "Key-Value & Table Extraction",
          status: "pending",
          desc: "Waiting for OCR completion...",
        },
        {
          step: 4,
          label: "Entity Normalization & Validation",
          status: "pending",
          desc: "Waiting for OCR completion...",
        },
      ];
    }

    if (!analysisResult) {
      return [
        {
          step: 1,
          label: "Document Ingestion & Parsing",
          status: "pending",
          desc: "Upload document to initiate OCI Object Storage ingestion",
        },
        {
          step: 2,
          label: "OCR & Text Layer Reconstruction",
          status: "pending",
          desc: "OCI AI Document Text Extraction & OCR",
        },
        {
          step: 3,
          label: "Key-Value & Table Extraction",
          status: "pending",
          desc: "Extracts key-value entities & tabular structures",
        },
        {
          step: 4,
          label: "Entity Normalization & Validation",
          status: "pending",
          desc: "Normalizes data types & verifies format compliance",
        },
      ];
    }

    const p = analysisResult.pipeline || {};
    const pageCount = getPageCount();
    const textPageCount = getTextPageCount();

    return [
      {
        step: 1,
        label: "Document Ingestion & Parsing",
        status: p.document_ingestion === "completed" ? "completed" : "pending",
        desc: p.document_ingestion === "completed"
          ? `PDF ingested & uploaded to OCI Object Storage (${pageCount} page${pageCount === 1 ? "" : "s"})`
          : "Ingestion pending",
      },
      {
        step: 2,
        label: "OCR & Text Layer Reconstruction",
        status: p.ocr === "completed" || p.text_extraction === "completed" ? "completed" : p.ocr === "ocr_required" ? "warning" : "pending",
        desc: p.ocr === "completed" || p.text_extraction === "completed"
          ? `OCI Document Understanding OCR completed (${textPageCount || pageCount} text page(s) extracted)`
          : "OCR processing pending",
      },
      {
        step: 3,
        label: "Key-Value & Table Extraction",
        status: p.key_value_extraction === "completed" || p.table_extraction === "completed" ? "completed" : "pending",
        desc: (analysisResult.entities?.length || 0) > 0 || (analysisResult.tables?.length || 0) > 0
          ? `${analysisResult.entities?.length || 0} entities, ${analysisResult.tables?.length || 0} tables extracted`
          : "0 key-value entities, 0 tables detected in document",
      },
      {
        step: 4,
        label: "Entity Normalization & Validation",
        status: p.validation === "completed" || p.entity_normalization === "completed" ? "completed" : p.validation === "completed_with_errors" ? "warning" : "pending",
        desc: p.validation === "completed" || p.entity_normalization === "completed"
          ? "Entity formats & constraints validated"
          : p.validation === "completed_with_errors"
          ? "Validation completed with errors/warnings"
          : "No entities to normalize & validate",
      },
    ];
  };

  const entitiesList = analysisResult?.entities || [];
  const pageCount = getPageCount();
  const textPageCount = getTextPageCount();
  const ocrReqCount = getOcrRequiredPages();
  const fullTextStr = analysisResult?.full_text || "";

  return (
    <div className="animate-fade-in" style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
      <SectionHeader
        title="Document Intelligence (OCI Document Understanding)"
        description="Automated optical character recognition (OCR), key-value entity extraction, and structural document parsing."
        isLive={true}
        badgeText="LIVE / OCI DOCUMENT UNDERSTANDING"
      />

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
        </div>
      )}

      {/* Hidden File Input */}
      <input
        type="file"
        ref={fileInputRef}
        accept=".pdf"
        onChange={handleFileInputChange}
        style={{ display: "none" }}
      />

      {/* Upload Zone & Document Classification */}
      <div className="grid-2">
        {/* Upload Dropzone */}
        <div className="card" style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
          <div className="card-header">
            <h3 className="card-title">
              <UploadCloud size={16} style={{ color: "var(--color-primary)" }} />
              Upload Enterprise Document
            </h3>
            <span style={{ fontSize: "11.5px", color: "var(--text-secondary)" }}>PDF Supported</span>
          </div>

          <div
            onClick={handleDropzoneClick}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            style={{
              border: isDragging ? "1.5px dashed var(--color-primary)" : "1.5px dashed var(--border-subtle)",
              borderRadius: "var(--radius-lg)",
              padding: "30px 20px",
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              justifyContent: "center",
              gap: "10px",
              cursor: isProcessing ? "wait" : "pointer",
              backgroundColor: isDragging ? "var(--color-primary-light)" : "var(--bg-surface-subtle)",
              transition: "all 0.15s ease",
            }}
          >
            <div
              style={{
                width: "42px",
                height: "42px",
                borderRadius: "var(--radius-md)",
                backgroundColor: "var(--color-primary-light)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                color: "var(--color-primary)",
              }}
            >
              {isProcessing || isLoadingDetail ? (
                <RefreshCw size={22} className="animate-spin" />
              ) : (
                <UploadCloud size={22} />
              )}
            </div>

            <div style={{ textAlign: "center" }}>
              <div style={{ fontSize: "13.5px", fontWeight: "600", color: "var(--text-primary)" }}>
                {isProcessing
                  ? "Processing OCI OCR Job..."
                  : isLoadingDetail
                  ? "Loading Analysis Result..."
                  : "Click to browse or drop PDF here"}
              </div>
              <div style={{ fontSize: "12px", color: "var(--text-secondary)", marginTop: "2px" }}>
                Active Document: <strong style={{ color: "var(--color-primary)" }}>{uploadedFileName}</strong>
                {analysisResult?.analysis_id ? ` (#${analysisResult.analysis_id})` : ""}
              </div>
            </div>

            <button
              className="btn btn-secondary"
              style={{ marginTop: "4px", fontSize: "12px" }}
              disabled={isProcessing || isLoadingDetail}
              onClick={handleRunOcrClick}
            >
              {isProcessing ? <RefreshCw size={13} className="animate-spin" /> : <Sparkles size={13} />}
              {isProcessing ? "Running OCI Document Understanding..." : "Run AI OCR Extraction"}
            </button>
          </div>

          {/* Doc Type Selector */}
          <div>
            <label style={{ fontSize: "12px", color: "var(--text-secondary)", fontWeight: "500", display: "block", marginBottom: "4px" }}>
              Document Classifier Template
            </label>
            <select
              style={{ width: "100%" }}
              value={selectedType}
              onChange={(e) => setSelectedType(e.target.value)}
            >
              {DOC_TYPES.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.label}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Pipeline Stepper Visualizer */}
        <div className="card" style={{ display: "flex", flexDirection: "column", justifyContent: "space-between" }}>
          <div className="card-header">
            <h3 className="card-title">
              <Layers size={16} style={{ color: "var(--color-success)" }} />
              Extraction Pipeline Progression
            </h3>
            <span className="badge badge-live">
              {analysisResult ? "OCI Live" : "Automated"}
            </span>
          </div>

          <div style={{ padding: "6px 0" }}>
            <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
              {getPipelineSteps().map((st) => (
                <div key={st.step} style={{ display: "flex", alignItems: "flex-start", gap: "10px" }}>
                  <div
                    style={{
                      width: "24px",
                      height: "24px",
                      borderRadius: "var(--radius-sm)",
                      backgroundColor:
                        st.status === "completed"
                          ? "var(--color-success)"
                          : st.status === "warning"
                          ? "var(--color-warning)"
                          : st.status === "active"
                          ? "var(--color-primary)"
                          : "var(--border-subtle)",
                      color: st.status === "pending" ? "var(--text-muted)" : "white",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      fontWeight: "700",
                      fontSize: "11px",
                      flexShrink: 0,
                    }}
                  >
                    {st.status === "completed" ? (
                      <CheckCircle2 size={14} />
                    ) : st.status === "active" ? (
                      <RefreshCw size={12} className="animate-spin" />
                    ) : (
                      st.step
                    )}
                  </div>
                  <div>
                    <div style={{ fontSize: "13px", fontWeight: "600", color: "var(--text-primary)" }}>
                      {st.label}
                    </div>
                    <div style={{ fontSize: "11.5px", color: "var(--text-secondary)" }}>
                      {st.desc}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div
            style={{
              backgroundColor: "var(--bg-surface-subtle)",
              border: "1px solid var(--border-subtle)",
              padding: "10px 12px",
              borderRadius: "var(--radius-md)",
              fontSize: "12px",
              color: "var(--text-secondary)",
              display: "flex",
              alignItems: "center",
              gap: "6px",
            }}
          >
            <Shield
              size={15}
              style={{
                color: analysisResult ? "var(--color-success)" : "var(--text-muted)",
              }}
            />
            {analysisResult ? (
              <span>
                OCI Document Understanding OCR: <strong style={{ color: "var(--color-success-text)" }}>{analysisResult.ocr_status === "completed" ? "Completed" : analysisResult.ocr_status || "Completed"}</strong>
                {" — "}
                <span><strong>{pageCount}</strong> page(s) detected, <strong>{textPageCount}</strong> with text</span>
                {ocrReqCount > 0 && <span> (<strong>{ocrReqCount}</strong> required OCR)</span>}
                {fullTextStr ? <span> | <strong>{fullTextStr.length.toLocaleString()}</strong> characters</span> : ""}
              </span>
            ) : (
              <span>OCI Document Understanding OCR: Ready. Select a PDF or choose a persisted record below.</span>
            )}
          </div>
        </div>
      </div>

      {/* Extracted Text Preview Area */}
      {analysisResult && (
        <div className="card">
          <div className="card-header">
            <div>
              <h3 className="card-title">
                <FileText size={16} style={{ color: "var(--color-primary)" }} />
                Extracted Text Preview
              </h3>
              <p className="card-subtitle">
                Actual OCR text extracted by OCI Document Understanding ({textPageCount} of {pageCount} pages with text)
                {fullTextStr ? ` — ${fullTextStr.length.toLocaleString()} total characters` : ""}
              </p>
            </div>
            <span className="badge badge-live">
              OCI OCR {analysisResult.ocr_status === "completed" ? "Completed" : analysisResult.ocr_status || "Completed"}
            </span>
          </div>

          <div
            style={{
              backgroundColor: "var(--bg-surface-subtle)",
              border: "1px solid var(--border-subtle)",
              borderRadius: "var(--radius-md)",
              padding: "14px 16px",
              maxHeight: "220px",
              overflowY: "auto",
              fontFamily: "var(--font-mono, monospace)",
              fontSize: "12px",
              lineHeight: "1.6",
              color: "var(--text-primary)",
              whiteSpace: "pre-wrap",
              wordBreak: "break-word",
            }}
          >
            {analysisResult.extracted_text_preview || analysisResult.full_text || "No text returned."}
          </div>
        </div>
      )}

      {/* Extracted Fields Table */}
      <div className="card">
        <div className="card-header">
          <div>
            <h3 className="card-title">
              <FileText size={16} style={{ color: "var(--color-info-text)" }} />
              Extracted Key-Value Entities
            </h3>
            <p className="card-subtitle">Values parsed and normalized by AI document extractor</p>
          </div>
          <span style={{ fontSize: "11.5px", color: "var(--text-secondary)" }}>
            {entitiesList.length} Fields Extracted
          </span>
        </div>

        <div className="table-container">
          <table className="enterprise-table">
            <thead>
              <tr>
                <th>Entity / Field Name</th>
                <th>Extracted Value</th>
                <th>Confidence Score</th>
                <th>Validation Status</th>
              </tr>
            </thead>
            <tbody>
              {entitiesList.length > 0 ? (
                entitiesList.map((item, idx) => {
                  const fieldLabel = item.field_name || item.field || item.normalized_field_name || "Unknown Field";
                  const confVal = typeof item.confidence === "number"
                    ? (item.confidence <= 1 ? Math.round(item.confidence * 100) : Math.round(item.confidence))
                    : null;

                  return (
                    <tr key={idx}>
                      <td style={{ fontWeight: "600", color: "var(--text-secondary)" }}>{fieldLabel}</td>
                      <td style={{ color: "var(--text-primary)", fontWeight: "500" }}>{item.value}</td>
                      <td>
                        {confVal !== null ? (
                          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                            <div style={{ width: "50px", height: "5px", backgroundColor: "#E4E7EC", borderRadius: "3px", overflow: "hidden" }}>
                              <div
                                style={{
                                  width: `${confVal}%`,
                                  height: "100%",
                                  backgroundColor: confVal > 90 ? "var(--color-success)" : confVal > 70 ? "var(--color-warning)" : "var(--color-danger)",
                                }}
                              />
                            </div>
                            <span style={{ fontSize: "11.5px", fontWeight: "600", color: confVal > 90 ? "var(--color-success-text)" : "var(--color-warning-text)" }}>
                              {confVal}%
                            </span>
                          </div>
                        ) : (
                          <span style={{ fontSize: "11.5px", color: "var(--text-muted)" }}>—</span>
                        )}
                      </td>
                      <td>
                        <StatusBadge status={item.validation_status || "Valid"} />
                      </td>
                    </tr>
                  );
                })
              ) : (
                <tr>
                  <td colSpan={4} style={{ textAlign: "center", padding: "28px 16px", color: "var(--text-secondary)" }}>
                    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "6px" }}>
                      <span style={{ fontWeight: "600", color: "var(--text-primary)", fontSize: "13px" }}>
                        No Structured Key-Value Entities Detected
                      </span>
                      <span style={{ fontSize: "12px", maxWidth: "520px", lineHeight: "1.5" }}>
                        {analysisResult
                          ? "OCI Document Understanding did not detect predefined key-value pairs in this document."
                          : "Upload a document or select an existing record to view structured key-value entities."}
                      </span>
                    </div>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Extracted Tables (if any) */}
      {analysisResult && analysisResult.tables && analysisResult.tables.length > 0 && (
        <div className="card">
          <div className="card-header">
            <div>
              <h3 className="card-title">
                <Layers size={16} style={{ color: "var(--color-primary)" }} />
                Extracted Tables
              </h3>
              <p className="card-subtitle">
                Tabular structures parsed by OCI Document Understanding
              </p>
            </div>
            <span style={{ fontSize: "11.5px", color: "var(--text-secondary)" }}>
              {analysisResult.tables.length} Table{analysisResult.tables.length === 1 ? "" : "s"} Extracted
            </span>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
            {analysisResult.tables.map((tbl, tIdx) => (
              <div key={tIdx} className="table-container" style={{ border: "1px solid var(--border-subtle)", borderRadius: "var(--radius-md)" }}>
                <div style={{ padding: "8px 12px", backgroundColor: "var(--bg-surface-subtle)", borderBottom: "1px solid var(--border-subtle)", fontSize: "12px", fontWeight: "600", color: "var(--text-primary)" }}>
                  Table {tbl.table_number || tIdx + 1} {tbl.page_number ? `(Page ${tbl.page_number})` : ""} — {tbl.row_count || tbl.rows.length} rows, {tbl.column_count || (tbl.rows[0]?.length || 0)} cols
                </div>
                <table className="enterprise-table">
                  <tbody>
                    {tbl.rows.map((row, rIdx) => (
                      <tr key={rIdx}>
                        {row.map((cell, cIdx) => (
                          <td key={cIdx} style={{ fontSize: "12px", color: "var(--text-primary)" }}>
                            {cell}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Processing History */}
      <div className="card">
        <div className="card-header">
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <h3 className="card-title" style={{ margin: 0 }}>
              <Clock size={16} style={{ color: "var(--text-secondary)" }} />
              Recent Document Processing History
            </h3>
            {isLoadingHistory && <RefreshCw size={12} className="animate-spin" style={{ color: "var(--color-primary)" }} />}
          </div>
          <button
            className="btn btn-secondary"
            style={{ fontSize: "11.5px", padding: "4px 8px" }}
            onClick={loadPersistedRecords}
            disabled={isLoadingHistory}
          >
            <RefreshCw size={11} className={isLoadingHistory ? "animate-spin" : ""} />
            Refresh
          </button>
        </div>

        <div className="table-container">
          <table className="enterprise-table">
            <thead>
              <tr>
                <th>Doc ID</th>
                <th>File Name</th>
                <th>Type</th>
                <th>Pages</th>
                <th>Date & Time</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {history.length > 0 ? (
                history.map((h) => {
                  const isSelected = selectedAnalysisId === h.analysis_id || analysisResult?.analysis_id === h.analysis_id;
                  const docIdLabel = h.analysis_id ? `DOC-${h.analysis_id}` : h.id;
                  const statusLabel = h.job_status === "SUCCEEDED" || h.ocr_status === "completed" ? "Completed" : h.job_status || h.status || "Completed";

                  return (
                    <tr
                      key={h.analysis_id || h.id}
                      onClick={() => h.analysis_id && handleSelectRecord(h.analysis_id)}
                      style={{
                        cursor: h.analysis_id ? "pointer" : "default",
                        backgroundColor: isSelected ? "var(--color-primary-light, rgba(235, 94, 40, 0.08))" : "transparent",
                        transition: "background-color 0.15s ease",
                      }}
                      title={h.analysis_id ? `Click to view analysis for ${h.document_name || h.name}` : ""}
                    >
                      <td style={{ fontFamily: "var(--font-mono)", color: "var(--color-primary)", fontWeight: "600" }}>
                        {docIdLabel}
                      </td>
                      <td style={{ fontWeight: isSelected ? "700" : "500", color: "var(--text-primary)" }}>
                        {h.document_name || h.name}
                      </td>
                      <td>{h.document_type || h.type || "PDF"}</td>
                      <td>{h.page_count ?? h.pages ?? 1}</td>
                      <td style={{ color: "var(--text-secondary)" }}>{formatDate(h.created_at || h.date)}</td>
                      <td><StatusBadge status={statusLabel} /></td>
                    </tr>
                  );
                })
              ) : (
                <tr>
                  <td colSpan={6} style={{ textAlign: "center", padding: "24px 16px", color: "var(--text-secondary)" }}>
                    {isLoadingHistory ? "Loading persisted records from Oracle Database..." : "No document intelligence records found."}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
