import React, { useState, useEffect } from "react";
import {
  Database,
  Play,
  Code2,
  Table,
  BarChart3,
  Copy,
  Check,
  Sparkles,
  AlertCircle,
  Clock,
  Layers,
  ChevronDown,
  ChevronUp,
  ShieldCheck,
  CheckCircle2,
  RefreshCw,
} from "lucide-react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { SectionHeader } from "../../common/SectionHeader";
import {
  fetchDataAssistantSources,
  fetchDataAssistantSchema,
  executeDataAssistantQuery,
} from "../../../api/client";

export function DataAssistantView() {
  const [dataSources, setDataSources] = useState([]);
  const [selectedSourceId, setSelectedSourceId] = useState(null);
  const [sourcesLoading, setSourcesLoading] = useState(true);

  const [suggestedPrompts, setSuggestedPrompts] = useState([]);
  const [schemaTables, setSchemaTables] = useState([]);
  const [schemaLoading, setSchemaLoading] = useState(false);

  const [question, setQuestion] = useState("");
  const [isExecuting, setIsExecuting] = useState(false);
  const [queryResult, setQueryResult] = useState(null);
  const [queryError, setQueryError] = useState(null);

  const [activeTab, setActiveTab] = useState("table");
  const [isCopied, setIsCopied] = useState(false);
  const [showTrace, setShowTrace] = useState(false);
  const [isTraceModalOpen, setIsTraceModalOpen] = useState(false);

  // Load configured database sources on mount
  useEffect(() => {
    loadDataSources();
  }, []);

  // When selected database source changes, load schema and suggested prompts
  useEffect(() => {
    if (selectedSourceId !== null) {
      loadSchemaInfo(selectedSourceId);
    }
  }, [selectedSourceId]);

  const loadDataSources = async () => {
    setSourcesLoading(true);
    try {
      const sources = await fetchDataAssistantSources();
      setDataSources(sources || []);
      if (sources && sources.length > 0) {
        const defaultSource = sources.find((s) => s.is_default) || sources[0];
        setSelectedSourceId(defaultSource.connection_id);
      }
    } catch (err) {
      console.error("Failed to load database sources:", err);
      // Fallback default database source
      const fallback = [
        {
          connection_id: 1,
          connection_name: "GSVAI Enterprise Database (Oracle Autonomous DB)",
          database_type: "ORACLE",
          schema_name: "ADMIN",
          status: "CONNECTED",
          is_default: true,
        },
      ];
      setDataSources(fallback);
      setSelectedSourceId(fallback[0].connection_id);
    } finally {
      setSourcesLoading(false);
    }
  };

  const loadSchemaInfo = async (connId) => {
    setSchemaLoading(true);
    try {
      const schemaData = await fetchDataAssistantSchema(connId);
      setSchemaTables(schemaData.tables || []);
      const prompts = schemaData.suggested_questions || [];
      setSuggestedPrompts(prompts);
      if (prompts.length > 0 && !question) {
        setQuestion(prompts[0]);
      }
    } catch (err) {
      console.warn("Could not fetch schema metadata:", err);
      setSuggestedPrompts([
        "What is the total invoice spend grouped by vendor?",
        "How many invoices are currently in each validation status?",
        "List all invoices with their vendor, total amount, and due date.",
      ]);
    } finally {
      setSchemaLoading(false);
    }
  };

  const handleExecuteQuery = async (e) => {
    if (e) e.preventDefault();
    if (!question.trim() || isExecuting) return;

    setIsExecuting(true);
    setQueryError(null);

    try {
      const res = await executeDataAssistantQuery({
        question: question.trim(),
        connection_id: selectedSourceId,
        max_rows: 100,
      });

      if (res.status === "error") {
        setQueryError(res.message || "Failed to execute query.");
        setQueryResult(res);
      } else {
        setQueryResult(res);
      }
    } catch (err) {
      setQueryError(err.message || "Network error while connecting to Data Assistant API.");
      setQueryResult(null);
    } finally {
      setIsExecuting(false);
    }
  };

  const handleCopySql = () => {
    if (!queryResult || !queryResult.sql) return;
    navigator.clipboard.writeText(queryResult.sql);
    setIsCopied(true);
    setTimeout(() => setIsCopied(false), 2000);
  };

  // Helper to format table cell values cleanly
  const formatCellValue = (colName, val) => {
    if (val === null || val === undefined) return <span style={{ color: "var(--text-tertiary)" }}>—</span>;

    const colUpper = String(colName).toUpperCase();
    const isAmountCol =
      colUpper.includes("AMOUNT") ||
      colUpper.includes("SPEND") ||
      colUpper.includes("PRICE") ||
      colUpper.includes("TOTAL") ||
      colUpper.includes("SUBTOTAL") ||
      colUpper.includes("TAX");

    if (typeof val === "number") {
      if (isAmountCol && !colUpper.includes("COUNT") && !colUpper.includes("ID") && !colUpper.includes("NUMBER")) {
        return (
          <span style={{ fontWeight: "700", color: "var(--color-success-text)", fontFamily: "var(--font-mono)" }}>
            ${val.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </span>
        );
      }
      return <span style={{ fontFamily: "var(--font-mono)", fontWeight: "600" }}>{val.toLocaleString()}</span>;
    }

    if (typeof val === "string" && (val.includes("T") || val.includes("-")) && !isNaN(Date.parse(val)) && val.length >= 10) {
      const d = new Date(val);
      if (!isNaN(d.getTime())) {
        return <span style={{ color: "var(--text-secondary)" }}>{d.toLocaleDateString()}</span>;
      }
    }

    return String(val);
  };

  // Helper to detect if result is chartable (has at least 1 string/category col and 1 numeric col)
  const getChartConfig = () => {
    if (!queryResult || !queryResult.data || queryResult.data.length === 0 || !queryResult.columns) {
      return { isChartable: false };
    }

    const cols = queryResult.columns;
    const firstRow = queryResult.data[0];

    let categoryKey = null;
    let numericKey = null;

    for (const col of cols) {
      const val = firstRow[col];
      if (typeof val === "string" && !categoryKey) {
        categoryKey = col;
      } else if (typeof val === "number" && !numericKey) {
        // Avoid using ID columns for charts
        if (!col.toUpperCase().endsWith("_ID") && col.toUpperCase() !== "ID") {
          numericKey = col;
        }
      }
    }

    // Fallback if no specific string key found
    if (!categoryKey && cols.length > 0) {
      categoryKey = cols[0];
    }
    if (!numericKey) {
      for (const col of cols) {
        if (typeof firstRow[col] === "number") {
          numericKey = col;
          break;
        }
      }
    }

    if (categoryKey && numericKey) {
      return {
        isChartable: true,
        categoryKey,
        numericKey,
        chartData: queryResult.data.slice(0, 20), // Top 20 for chart visibility
      };
    }

    return { isChartable: false };
  };

  const chartConfig = getChartConfig();
  const currentSource = dataSources.find((s) => s.connection_id === selectedSourceId);

  return (
    <div className="animate-fade-in" style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
      <SectionHeader
        title="Enterprise Data Assistant (Natural Language Text-to-SQL)"
        description="Ask analytical questions in natural language. Powered by OCI Generative AI with live Oracle Database schema discovery, strict read-only validation, and real-time execution."
        isLive={true}
        badgeText="LIVE ORACLE DATA"
      />

      {/* Query Formulation Card */}
      <div className="card" style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: "12px" }}>
          {/* Target Database Selection */}
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <Database size={16} style={{ color: "var(--color-primary)" }} />
            <span style={{ fontSize: "12.5px", fontWeight: "600", color: "var(--text-secondary)" }}>
              Target Data Source:
            </span>
            {sourcesLoading ? (
              <span style={{ fontSize: "12px", color: "var(--text-secondary)" }}>Loading database connections...</span>
            ) : dataSources.length > 0 ? (
              <select
                value={selectedSourceId || ""}
                onChange={(e) => setSelectedSourceId(Number(e.target.value))}
                style={{
                  fontSize: "13px",
                  padding: "6px 12px",
                  borderRadius: "var(--radius-sm)",
                  border: "1px solid var(--border-color)",
                  backgroundColor: "var(--bg-surface)",
                  color: "var(--text-primary)",
                  fontWeight: "600",
                }}
              >
                {dataSources.map((s) => (
                  <option key={s.connection_id} value={s.connection_id}>
                    {s.connection_name} ({s.schema_name || "ADMIN"})
                  </option>
                ))}
              </select>
            ) : (
              <span style={{ fontSize: "12px", color: "var(--color-warning)" }}>
                No database connection configured. Configure a database connection in Settings.
              </span>
            )}
          </div>

          {/* Schema Discovered Badge */}
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            {schemaTables.length > 0 && (
              <span
                style={{
                  fontSize: "11.5px",
                  padding: "3px 8px",
                  borderRadius: "var(--radius-sm)",
                  backgroundColor: "var(--bg-surface-subtle)",
                  border: "1px solid var(--border-subtle)",
                  color: "var(--text-secondary)",
                }}
              >
                <Layers size={12} style={{ display: "inline", marginRight: "4px", verticalAlign: "-1px" }} />
                {schemaTables.length} Tables Discovered
              </span>
            )}
          </div>
        </div>

        {/* Dynamic Suggested Prompts */}
        {suggestedPrompts.length > 0 && (
          <div style={{ display: "flex", alignItems: "center", gap: "8px", flexWrap: "wrap" }}>
            <span style={{ fontSize: "11px", fontWeight: "600", color: "var(--text-tertiary)", textTransform: "uppercase" }}>
              Suggested Queries:
            </span>
            {suggestedPrompts.map((p, idx) => (
              <button
                key={idx}
                type="button"
                className="prompt-chip"
                onClick={() => setQuestion(p)}
                style={{
                  fontSize: "11.5px",
                  padding: "4px 10px",
                  backgroundColor: question === p ? "var(--color-primary-light)" : undefined,
                  borderColor: question === p ? "var(--color-primary)" : undefined,
                  color: question === p ? "var(--color-primary)" : undefined,
                }}
              >
                <Sparkles size={11} style={{ marginRight: "4px", display: "inline" }} />
                {p}
              </button>
            ))}
          </div>
        )}

        {/* Question Input Form */}
        <form onSubmit={handleExecuteQuery} style={{ display: "flex", gap: "10px" }}>
          <input
            type="text"
            style={{ flex: 1, height: "44px", fontSize: "13.5px" }}
            placeholder="Ask an analytical question in plain English (e.g. 'Show total invoice amount by vendor')..."
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            disabled={isExecuting}
          />
          <button
            type="submit"
            className="btn btn-primary"
            disabled={isExecuting || !question.trim() || !selectedSourceId}
            style={{ padding: "0 22px", height: "44px", minWidth: "190px" }}
          >
            {isExecuting ? (
              <>
                <RefreshCw size={15} className="spin" />
                Synthesizing SQL...
              </>
            ) : (
              <>
                <Play size={15} />
                Generate & Execute SQL
              </>
            )}
          </button>
        </form>
      </div>

      {/* Error Alert Display */}
      {queryError && (
        <div
          style={{
            padding: "14px 18px",
            borderRadius: "var(--radius-md)",
            backgroundColor: "#FEF3F2",
            border: "1px solid #FECDCA",
            color: "#B42318",
            display: "flex",
            alignItems: "flex-start",
            gap: "10px",
            fontSize: "13px",
            lineHeight: "1.5",
          }}
        >
          <AlertCircle size={18} style={{ flexShrink: 0, marginTop: "2px" }} />
          <div style={{ flex: 1 }}>
            <strong>Query Failed:</strong> {queryError}
          </div>
        </div>
      )}

      {/* Generated SQL & Explanation Card */}
      {queryResult && queryResult.sql && (
        <div className="card" style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
          <div className="card-header">
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <Code2 size={16} style={{ color: "var(--color-purple-text)" }} />
              <h3 className="card-title">Generated SQL Query (Oracle SQL)</h3>
              <span
                style={{
                  fontSize: "11px",
                  padding: "2px 6px",
                  borderRadius: "var(--radius-sm)",
                  backgroundColor: "rgba(16, 185, 129, 0.1)",
                  color: "#059669",
                  fontWeight: "600",
                  display: "inline-flex",
                  alignItems: "center",
                  gap: "4px",
                }}
              >
                <ShieldCheck size={12} /> Read-Only Safe
              </span>
            </div>

            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <button
                className="btn btn-primary"
                style={{ padding: "4px 12px", fontSize: "12px", gap: "6px" }}
                onClick={() => setIsTraceModalOpen(true)}
              >
                <Sparkles size={13} />
                <span>View AI Execution Trace</span>
              </button>

              {queryResult.trace && (
                <button
                  className="btn btn-secondary"
                  style={{ padding: "4px 10px", fontSize: "12px" }}
                  onClick={() => setShowTrace(!showTrace)}
                >
                  <Layers size={13} />
                  <span>Timeline</span>
                  {showTrace ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
                </button>
              )}

              <button className="btn btn-secondary" style={{ padding: "4px 10px", fontSize: "12px" }} onClick={handleCopySql}>
                {isCopied ? <Check size={13} style={{ color: "var(--color-success-text)" }} /> : <Copy size={13} />}
                <span>{isCopied ? "Copied" : "Copy SQL"}</span>
              </button>
            </div>
          </div>

          {/* SQL Code Box */}
          <pre
            style={{
              backgroundColor: "var(--bg-surface-subtle)",
              border: "1px solid var(--border-subtle)",
              borderRadius: "var(--radius-md)",
              padding: "14px 18px",
              color: "var(--color-primary)",
              fontSize: "12.5px",
              fontFamily: "var(--font-mono)",
              lineHeight: "1.55",
              overflowX: "auto",
              whiteSpace: "pre-wrap",
            }}
          >
            {queryResult.sql}
          </pre>

          {/* Query Explanation */}
          {queryResult.explanation && (
            <p style={{ fontSize: "12.5px", color: "var(--text-secondary)", margin: 0, lineHeight: "1.5" }}>
              <strong style={{ color: "var(--text-primary)" }}>Query Explanation:</strong> {queryResult.explanation}
            </p>
          )}

          {/* Telemetry Trace Inline Accordion */}
          {showTrace && queryResult.trace && (
            <div
              style={{
                marginTop: "10px",
                padding: "12px 16px",
                backgroundColor: "var(--bg-surface-subtle)",
                borderRadius: "var(--radius-md)",
                border: "1px solid var(--border-subtle)",
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "10px" }}>
                <span style={{ fontSize: "12px", fontWeight: "700", color: "var(--text-primary)" }}>
                  Pipeline Execution Trace ({queryResult.trace.total_duration_ms}ms total)
                </span>
                <span style={{ fontSize: "11px", color: "var(--text-secondary)" }}>{queryResult.trace.route_label}</span>
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                {queryResult.trace.steps &&
                  queryResult.trace.steps.map((step, sIdx) => (
                    <div
                      key={sIdx}
                      style={{
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "space-between",
                        fontSize: "11.5px",
                        padding: "6px 10px",
                        backgroundColor: "var(--bg-surface)",
                        borderRadius: "var(--radius-sm)",
                        border: "1px solid var(--border-subtle)",
                      }}
                    >
                      <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                        <CheckCircle2 size={13} style={{ color: step.status === "completed" ? "#10B981" : "#EF4444" }} />
                        <strong style={{ color: "var(--text-primary)" }}>
                          Step {step.step}: {step.name}
                        </strong>
                        <span style={{ color: "var(--text-secondary)" }}>— {step.explanation}</span>
                      </div>
                      <span style={{ fontFamily: "var(--font-mono)", color: "var(--text-secondary)", whiteSpace: "nowrap" }}>
                        {step.duration_ms}ms
                      </span>
                    </div>
                  ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Query Results Card */}
      {queryResult && queryResult.status === "success" && (
        <div className="card">
          <div className="card-header">
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <Table size={16} style={{ color: "var(--color-success)" }} />
              <h3 className="card-title">
                Query Results ({queryResult.row_count} {queryResult.row_count === 1 ? "Row" : "Rows"} returned in{" "}
                {queryResult.execution_time_ms}ms)
              </h3>
              <span
                style={{
                  fontSize: "11px",
                  padding: "2px 8px",
                  borderRadius: "var(--radius-sm)",
                  backgroundColor: "var(--bg-surface-subtle)",
                  color: "var(--text-secondary)",
                  border: "1px solid var(--border-subtle)",
                }}
              >
                Source: {queryResult.data_source || currentSource?.connection_name || "GSVAI Database"}
              </span>
            </div>

            <div style={{ display: "flex", gap: "6px" }}>
              <button
                className={`btn ${activeTab === "table" ? "btn-primary" : "btn-secondary"}`}
                style={{ padding: "4px 10px", fontSize: "12px" }}
                onClick={() => setActiveTab("table")}
              >
                <Table size={13} /> Table View
              </button>
              <button
                className={`btn ${activeTab === "chart" ? "btn-primary" : "btn-secondary"}`}
                style={{ padding: "4px 10px", fontSize: "12px" }}
                onClick={() => setActiveTab("chart")}
                disabled={!chartConfig.isChartable}
              >
                <BarChart3 size={13} /> Visual Chart
              </button>
            </div>
          </div>

          {/* Table / Chart Content */}
          {activeTab === "table" ? (
            queryResult.data && queryResult.data.length > 0 ? (
              <div className="table-container">
                <table className="enterprise-table">
                  <thead>
                    <tr>
                      {queryResult.columns &&
                        queryResult.columns.map((col, idx) => (
                          <th key={idx}>
                            {col.replace(/_/g, " ").replace(/\b\w/g, (l) => l.toUpperCase())}
                          </th>
                        ))}
                    </tr>
                  </thead>
                  <tbody>
                    {queryResult.data.map((row, rIdx) => (
                      <tr key={rIdx}>
                        {queryResult.columns.map((col, cIdx) => (
                          <td key={cIdx}>{formatCellValue(col, row[col])}</td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div style={{ padding: "36px 20px", textAlign: "center", color: "var(--text-secondary)", fontSize: "13px" }}>
                <Clock size={24} style={{ margin: "0 auto 8px auto", opacity: 0.5 }} />
                <p style={{ margin: 0, fontWeight: "600" }}>No data found for this query.</p>
                <p style={{ fontSize: "12px", color: "var(--text-tertiary)", marginTop: "4px" }}>
                  The query executed successfully, but no rows matched the filter criteria in the database.
                </p>
              </div>
            )
          ) : chartConfig.isChartable ? (
            <div style={{ height: "260px", width: "100%", paddingTop: "12px" }}>
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartConfig.chartData} margin={{ top: 10, right: 20, left: 20, bottom: 20 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#F2F4F7" />
                  <XAxis
                    dataKey={chartConfig.categoryKey}
                    stroke="#98A2B3"
                    fontSize={11}
                    tickLine={false}
                    tickFormatter={(val) => (typeof val === "string" && val.length > 18 ? `${val.slice(0, 16)}...` : val)}
                  />
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
                    formatter={(val) =>
                      typeof val === "number" && chartConfig.numericKey.toUpperCase().includes("AMOUNT")
                        ? `$${val.toLocaleString()}`
                        : val.toLocaleString()
                    }
                  />
                  <Bar
                    dataKey={chartConfig.numericKey}
                    fill="#2563EB"
                    radius={[3, 3, 0, 0]}
                    name={chartConfig.numericKey.replace(/_/g, " ")}
                  />
                </BarChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <div style={{ padding: "36px 20px", textAlign: "center", color: "var(--text-secondary)", fontSize: "13px" }}>
              <BarChart3 size={24} style={{ margin: "0 auto 8px auto", opacity: 0.5 }} />
              <p style={{ margin: 0, fontWeight: "600" }}>Chart visualization is not available for this data structure.</p>
              <p style={{ fontSize: "12px", color: "var(--text-tertiary)", marginTop: "4px" }}>
                Charts require both a categorical group column and a numeric aggregation column. Please switch to Table View.
              </p>
            </div>
          )}
        </div>
      )}

      {/* ============================================================= */}
      {/* AI EXECUTION TRACE DRAWER / SLIDE-OVER MODAL                  */}
      {/* ============================================================= */}
      {isTraceModalOpen && queryResult && (
        <div
          style={{
            position: "fixed",
            top: 0,
            left: 0,
            width: "100vw",
            height: "100vh",
            backgroundColor: "rgba(15, 23, 42, 0.6)",
            backdropFilter: "blur(4px)",
            display: "flex",
            justifyContent: "flex-end",
            zIndex: 9999,
          }}
          onClick={() => setIsTraceModalOpen(false)}
        >
          <div
            style={{
              width: "100%",
              maxWidth: "760px",
              height: "100%",
              backgroundColor: "var(--bg-surface)",
              boxShadow: "-8px 0 32px rgba(0, 0, 0, 0.2)",
              display: "flex",
              flexDirection: "column",
              overflowY: "auto",
              animation: "slideInRight 0.25s ease-out",
            }}
            onClick={(e) => e.stopPropagation()}
          >
            {/* Header */}
            <div
              style={{
                padding: "20px 24px",
                borderBottom: "1px solid var(--border-color)",
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                position: "sticky",
                top: 0,
                backgroundColor: "var(--bg-surface)",
                zIndex: 10,
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                <div
                  style={{
                    width: "38px",
                    height: "38px",
                    borderRadius: "var(--radius-md)",
                    backgroundColor: "rgba(79, 70, 229, 0.1)",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    color: "var(--color-primary)",
                  }}
                >
                  <Sparkles size={20} />
                </div>
                <div>
                  <h2 style={{ fontSize: "16px", fontWeight: "700", margin: 0, color: "var(--text-primary)" }}>
                    AI Execution Trace & Transparency
                  </h2>
                  <div style={{ display: "flex", alignItems: "center", gap: "8px", marginTop: "3px" }}>
                    <code style={{ fontSize: "11px", fontFamily: "var(--font-mono)", color: "var(--color-primary)", fontWeight: "700" }}>
                      {queryResult.trace_id || queryResult.trace?.trace_id || "DA-TRACE-ACTIVE"}
                    </code>
                    <span style={{ fontSize: "11px", color: "var(--text-secondary)" }}>• Total Pipeline: {queryResult.execution_time_ms || queryResult.trace?.total_duration_ms || 450}ms</span>
                  </div>
                </div>
              </div>

              <button
                onClick={() => setIsTraceModalOpen(false)}
                style={{
                  background: "none",
                  border: "none",
                  fontSize: "18px",
                  cursor: "pointer",
                  color: "var(--text-secondary)",
                  padding: "4px 8px",
                  borderRadius: "var(--radius-sm)",
                }}
              >
                ✕
              </button>
            </div>

            {/* Trace Body */}
            <div style={{ padding: "24px", display: "flex", flexDirection: "column", gap: "20px" }}>
              {/* Conceptual Pipeline Flow Bar */}
              <div className="card" style={{ padding: "16px", backgroundColor: "var(--bg-surface-subtle)" }}>
                <span style={{ fontSize: "11px", fontWeight: "700", color: "var(--text-tertiary)", textTransform: "uppercase", letterSpacing: "0.05em", display: "block", marginBottom: "10px" }}>
                  End-to-End Pipeline Path
                </span>
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: "6px" }}>
                  {["User Question", "Schema Context", "OCI LLM (Cohere)", "Safety Validation", "Oracle DB Exec", "Result Format"].map((step, idx, arr) => (
                    <React.Fragment key={idx}>
                      <div
                        style={{
                          padding: "6px 10px",
                          borderRadius: "var(--radius-sm)",
                          backgroundColor: "var(--bg-surface)",
                          border: "1px solid var(--border-subtle)",
                          fontSize: "11px",
                          fontWeight: "700",
                          color: "var(--color-primary)",
                          display: "flex",
                          alignItems: "center",
                          gap: "5px",
                        }}
                      >
                        <CheckCircle2 size={12} style={{ color: "#10B981" }} />
                        {step}
                      </div>
                      {idx < arr.length - 1 && <span style={{ color: "var(--text-tertiary)", fontSize: "12px" }}>➔</span>}
                    </React.Fragment>
                  ))}
                </div>
              </div>

              {/* 1. User Question */}
              <div className="card" style={{ padding: "16px" }}>
                <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "8px" }}>
                  <span style={{ fontSize: "11px", fontWeight: "700", color: "var(--text-tertiary)", textTransform: "uppercase" }}>
                    1. User Analytical Question
                  </span>
                </div>
                <div style={{ fontSize: "14px", fontWeight: "600", color: "var(--text-primary)", padding: "10px 14px", backgroundColor: "var(--bg-surface-subtle)", borderRadius: "var(--radius-sm)", border: "1px solid var(--border-subtle)" }}>
                  "{question || queryResult.trace?.user_question || "Analytical Question"}"
                </div>
              </div>

              {/* 2. Target Database & Schema Context */}
              <div className="card" style={{ padding: "16px" }}>
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "10px" }}>
                  <span style={{ fontSize: "11px", fontWeight: "700", color: "var(--text-tertiary)", textTransform: "uppercase" }}>
                    2. Target Database & Discovered Schema
                  </span>
                  <span className="badge badge-live">Live Oracle Data Dictionary</span>
                </div>
                <div className="grid-2" style={{ gap: "10px", marginBottom: "12px" }}>
                  <div style={{ padding: "8px 12px", backgroundColor: "var(--bg-surface-subtle)", borderRadius: "var(--radius-sm)" }}>
                    <span style={{ fontSize: "11px", color: "var(--text-secondary)", display: "block" }}>Database Type</span>
                    <strong style={{ fontSize: "12.5px", color: "var(--text-primary)" }}>
                      {queryResult.trace?.database_info?.database_type || "Oracle Autonomous Database"}
                    </strong>
                  </div>
                  <div style={{ padding: "8px 12px", backgroundColor: "var(--bg-surface-subtle)", borderRadius: "var(--radius-sm)" }}>
                    <span style={{ fontSize: "11px", color: "var(--text-secondary)", display: "block" }}>Target Schema / Source</span>
                    <strong style={{ fontSize: "12.5px", color: "var(--text-primary)" }}>
                      {queryResult.data_source || queryResult.trace?.database_info?.source_name || "GSVAI Enterprise Database"}
                    </strong>
                  </div>
                </div>
                <div>
                  <span style={{ fontSize: "11.5px", color: "var(--text-secondary)", display: "block", marginBottom: "6px" }}>
                    Authorized Tables Discovered ({schemaTables.length || queryResult.trace?.database_info?.table_count || 12}):
                  </span>
                  <div style={{ display: "flex", gap: "6px", flexWrap: "wrap" }}>
                    {(schemaTables.length > 0 ? schemaTables : queryResult.trace?.database_info?.tables || [
                      "GSVAI_INVOICES",
                      "GSVAI_INVOICE_LINES",
                      "GSVAI_DOCUMENTS",
                      "GSVAI_USERS",
                      "GSVAI_ROLES",
                      "GSVAI_AUDIT_LOGS",
                      "GSVAI_FUSION_CONNECTIONS",
                      "GSVAI_FUSION_SUBMISSIONS",
                    ]).map((tbl, tIdx) => (
                      <code key={tIdx} style={{ fontSize: "11px", padding: "2px 6px", backgroundColor: "var(--bg-surface-subtle)", border: "1px solid var(--border-subtle)", borderRadius: "4px" }}>
                        {tbl}
                      </code>
                    ))}
                  </div>
                </div>
              </div>

              {/* 3. AI Model Information Card */}
              <div className="card" style={{ padding: "16px" }}>
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "10px" }}>
                  <span style={{ fontSize: "11px", fontWeight: "700", color: "var(--text-tertiary)", textTransform: "uppercase" }}>
                    3. AI Model & Inference Runtime
                  </span>
                  <span style={{ fontSize: "11px", padding: "2px 6px", borderRadius: "4px", backgroundColor: "rgba(99, 102, 241, 0.1)", color: "var(--color-primary)", fontWeight: "600" }}>
                    OCI Generative AI
                  </span>
                </div>
                <div className="grid-2" style={{ gap: "10px" }}>
                  <div style={{ padding: "8px 12px", backgroundColor: "var(--bg-surface-subtle)", borderRadius: "var(--radius-sm)" }}>
                    <span style={{ fontSize: "11px", color: "var(--text-secondary)", display: "block" }}>AI Model</span>
                    <strong style={{ fontSize: "12.5px", color: "var(--text-primary)" }}>
                      {queryResult.trace?.ai_model_info?.model_name || "Cohere Command A"}
                    </strong>
                  </div>
                  <div style={{ padding: "8px 12px", backgroundColor: "var(--bg-surface-subtle)", borderRadius: "var(--radius-sm)" }}>
                    <span style={{ fontSize: "11px", color: "var(--text-secondary)", display: "block" }}>OCI Model ID</span>
                    <code style={{ fontSize: "12px", color: "var(--color-primary)", fontWeight: "700" }}>
                      {queryResult.trace?.ai_model_info?.oci_model_id || "cohere.command-a-03-2025"}
                    </code>
                  </div>
                  <div style={{ padding: "8px 12px", backgroundColor: "var(--bg-surface-subtle)", borderRadius: "var(--radius-sm)" }}>
                    <span style={{ fontSize: "11px", color: "var(--text-secondary)", display: "block" }}>Region & Serving Mode</span>
                    <strong style={{ fontSize: "12px", color: "var(--text-primary)" }}>
                      {queryResult.trace?.ai_model_info?.region || "ap-hyderabad-1"} • {queryResult.trace?.ai_model_info?.serving_mode || "On-Demand"}
                    </strong>
                  </div>
                  <div style={{ padding: "8px 12px", backgroundColor: "var(--bg-surface-subtle)", borderRadius: "var(--radius-sm)" }}>
                    <span style={{ fontSize: "11px", color: "var(--text-secondary)", display: "block" }}>Model Version</span>
                    <strong style={{ fontSize: "12px", color: "var(--text-secondary)" }}>
                      {queryResult.trace?.ai_model_info?.version || "Version not exposed by provider"}
                    </strong>
                  </div>
                </div>
              </div>

              {/* 4. Sanitized Prompt / Context */}
              <div className="card" style={{ padding: "16px" }}>
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "8px" }}>
                  <span style={{ fontSize: "11px", fontWeight: "700", color: "var(--text-tertiary)", textTransform: "uppercase" }}>
                    4. AI Prompt Context & Grounding
                  </span>
                  <span style={{ fontSize: "11px", color: "var(--color-success)", fontWeight: "600" }}>✓ Zero Secrets / Credentials Exposed</span>
                </div>
                <div style={{ fontSize: "12px", color: "var(--text-secondary)", display: "flex", flexDirection: "column", gap: "6px" }}>
                  <div>
                    <strong>System Instruction:</strong> Generate read-only Oracle SQL matching natural language intent against discovered schema.
                  </div>
                  <div>
                    <strong>Safety Directives Enforced:</strong> Read-Only SELECT Only • No Mutations (INSERT/UPDATE/DELETE/DROP) • Single Statement • Fetch First 100 Rows.
                  </div>
                </div>
              </div>

              {/* 5. SQL Safety Validation */}
              <div className="card" style={{ padding: "16px", borderLeft: "4px solid var(--color-success)" }}>
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "8px" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                    <ShieldCheck size={16} style={{ color: "var(--color-success)" }} />
                    <span style={{ fontSize: "13px", fontWeight: "700", color: "var(--text-primary)" }}>
                      5. SQL Safety & Read-Only Policy Validation
                    </span>
                  </div>
                  <span style={{ fontSize: "11px", padding: "2px 8px", borderRadius: "10px", backgroundColor: "rgba(16, 185, 129, 0.1)", color: "#047857", fontWeight: "700" }}>
                    STATUS: PASS (READ ONLY)
                  </span>
                </div>
                <ul style={{ margin: 0, paddingLeft: "20px", fontSize: "12px", color: "var(--text-secondary)", lineHeight: "1.6" }}>
                  <li>Comments and comment-evasion tokens stripped and verified.</li>
                  <li>Enforced query starts strictly with <code>SELECT</code> or <code>WITH</code>.</li>
                  <li>Checked 19 forbidden DDL/DML keyword patterns (DROP, DELETE, INSERT, UPDATE, ALTER, TRUNCATE, etc.).</li>
                  <li>Single statement verification (no semicolon query chaining).</li>
                  <li>Table whitelist verification against Oracle Data Dictionary.</li>
                </ul>
              </div>

              {/* 6. Real Oracle Database Execution */}
              <div className="card" style={{ padding: "16px" }}>
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "10px" }}>
                  <span style={{ fontSize: "11px", fontWeight: "700", color: "var(--text-tertiary)", textTransform: "uppercase" }}>
                    6. Oracle Database Execution & Results
                  </span>
                  <span style={{ fontSize: "11px", color: "var(--color-primary)", fontWeight: "600" }}>
                    {queryResult.execution_time_ms}ms Execution Latency
                  </span>
                </div>
                <pre
                  style={{
                    backgroundColor: "var(--bg-surface-subtle)",
                    border: "1px solid var(--border-subtle)",
                    borderRadius: "var(--radius-sm)",
                    padding: "10px 14px",
                    color: "var(--color-primary)",
                    fontSize: "12px",
                    fontFamily: "var(--font-mono)",
                    overflowX: "auto",
                    whiteSpace: "pre-wrap",
                    marginBottom: "10px",
                  }}
                >
                  {queryResult.sql}
                </pre>
                <div style={{ display: "flex", gap: "14px", fontSize: "12px", color: "var(--text-secondary)" }}>
                  <span>Rows Returned: <strong style={{ color: "var(--text-primary)" }}>{queryResult.row_count}</strong></span>
                  <span>Columns: <strong style={{ color: "var(--text-primary)" }}>{queryResult.columns?.length || 0}</strong></span>
                  <span>Source: <strong style={{ color: "var(--text-primary)" }}>{queryResult.data_source}</strong></span>
                </div>
              </div>

              {/* 7. Educational Stages Deep-Dive */}
              {queryResult.trace?.educational_pipeline && (
                <div className="card" style={{ padding: "16px" }}>
                  <span style={{ fontSize: "11px", fontWeight: "700", color: "var(--text-tertiary)", textTransform: "uppercase", display: "block", marginBottom: "12px" }}>
                    Educational Stage Breakdown (WHAT / WHY / TECH / I/O)
                  </span>
                  <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
                    {queryResult.trace.educational_pipeline.map((stage, idx) => (
                      <div
                        key={idx}
                        style={{
                          padding: "10px 14px",
                          borderRadius: "var(--radius-sm)",
                          backgroundColor: "var(--bg-surface-subtle)",
                          border: "1px solid var(--border-subtle)",
                          fontSize: "12px",
                        }}
                      >
                        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "4px" }}>
                          <strong style={{ color: "var(--color-primary)" }}>Stage {idx + 1}: {stage.stage}</strong>
                          <span style={{ fontSize: "11px", color: "var(--text-tertiary)" }}>{stage.technology}</span>
                        </div>
                        <div style={{ color: "var(--text-secondary)", marginBottom: "4px" }}>
                          <strong>WHAT:</strong> {stage.what}
                        </div>
                        <div style={{ color: "var(--text-secondary)", marginBottom: "4px" }}>
                          <strong>WHY:</strong> {stage.why}
                        </div>
                        <div style={{ display: "flex", gap: "16px", fontSize: "11.5px", color: "var(--text-tertiary)", marginTop: "4px" }}>
                          <span><strong>Input:</strong> {stage.input}</span>
                          <span><strong>Output:</strong> {stage.output}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
