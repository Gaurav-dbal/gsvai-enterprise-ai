import React, { useState } from "react";
import {
  Database,
  Play,
  Code2,
  Table,
  BarChart3,
  Copy,
  Check,
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

const SCHEMAS = [
  { id: "erp_fin", name: "ERP_Financials_PROD (Oracle Fusion)" },
  { id: "procurement", name: "Procurement_DataWarehouse" },
  { id: "hr_analytics", name: "HR_Workforce_Analytics" },
];

const PRESETS = [
  "What is the total quarterly spend by supplier category for Q2 2026?",
  "List top 5 vendors with highest invoice variance rate in the last 6 months.",
  "Show average PO approval cycle time grouped by department.",
];

const MOCK_QUERY_RESULT = {
  sql: `SELECT 
    v.category_name,
    COUNT(i.invoice_id) AS total_invoices,
    SUM(i.invoice_amount) AS total_spend_usd,
    ROUND(AVG(i.processing_days), 1) AS avg_cycle_days
FROM fusion_ap_invoices i
JOIN fusion_vendors v ON i.vendor_id = v.vendor_id
WHERE i.invoice_date >= '2026-04-01' AND i.invoice_date <= '2026-06-30'
GROUP BY v.category_name
ORDER BY total_spend_usd DESC;`,
  explanation:
    "This query joins the Oracle Fusion AP invoices table with vendor classification dimension, filtering for Q2 2026 transactions, aggregating total gross spend, invoice count, and average turnaround cycle.",
  data: [
    { category: "Cloud & Infrastructure", spend: 485000, invoices: 42, avgDays: 1.8 },
    { category: "Hardware & Telecom", spend: 320000, invoices: 28, avgDays: 2.4 },
    { category: "Professional Services", spend: 215000, invoices: 19, avgDays: 3.1 },
    { category: "Facilities & Logistics", spend: 142000, invoices: 64, avgDays: 1.2 },
    { category: "Software & SaaS", spend: 98000, invoices: 35, avgDays: 1.0 },
  ],
};

export function DataAssistantView() {
  const [selectedSchema, setSelectedSchema] = useState(SCHEMAS[0].id);
  const [question, setQuestion] = useState(PRESETS[0]);
  const [isCopied, setIsCopied] = useState(false);
  const [activeTab, setActiveTab] = useState("table");

  const handleCopySql = () => {
    navigator.clipboard.writeText(MOCK_QUERY_RESULT.sql);
    setIsCopied(true);
    setTimeout(() => setIsCopied(false), 2000);
  };

  return (
    <div className="animate-fade-in" style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
      <SectionHeader
        title="Data Assistant (Text-to-SQL & Enterprise Analytics)"
        description="Natural language data querying against enterprise relational schemas with automated SQL generation and visual analytics."
        isLive={false}
        badgeText="DEMO / TEXT-TO-SQL"
      />

      {/* Query Formulation Card */}
      <div className="card" style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: "10px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <Database size={16} style={{ color: "var(--color-primary)" }} />
            <span style={{ fontSize: "12.5px", fontWeight: "600", color: "var(--text-secondary)" }}>Target Database Schema:</span>
            <select
              value={selectedSchema}
              onChange={(e) => setSelectedSchema(e.target.value)}
              style={{ fontSize: "13px", padding: "5px 10px" }}
            >
              {SCHEMAS.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name}
                </option>
              ))}
            </select>
          </div>

          <div style={{ display: "flex", gap: "6px" }}>
            {PRESETS.map((p, idx) => (
              <button
                key={idx}
                className="prompt-chip"
                onClick={() => setQuestion(p)}
                style={{ fontSize: "11px" }}
              >
                Preset {idx + 1}
              </button>
            ))}
          </div>
        </div>

        {/* Input */}
        <div style={{ display: "flex", gap: "10px" }}>
          <input
            type="text"
            style={{ flex: 1, height: "42px" }}
            placeholder="Ask a question about your enterprise data..."
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
          />
          <button className="btn btn-primary" style={{ padding: "0 20px" }}>
            <Play size={15} />
            Generate & Execute SQL
          </button>
        </div>
      </div>

      {/* Generated SQL & Explanation */}
      <div className="card">
        <div className="card-header">
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <Code2 size={16} style={{ color: "var(--color-purple-text)" }} />
            <h3 className="card-title">Generated SQL Query (ANSI / Oracle SQL)</h3>
          </div>

          <button className="btn btn-secondary" style={{ padding: "4px 10px", fontSize: "12px" }} onClick={handleCopySql}>
            {isCopied ? <Check size={13} style={{ color: "var(--color-success-text)" }} /> : <Copy size={13} />}
            <span>{isCopied ? "Copied" : "Copy SQL"}</span>
          </button>
        </div>

        {/* SQL Code Box */}
        <pre
          style={{
            backgroundColor: "var(--bg-surface-subtle)",
            border: "1px solid var(--border-subtle)",
            borderRadius: "var(--radius-md)",
            padding: "12px 16px",
            color: "var(--color-primary)",
            fontSize: "12.5px",
            lineHeight: "1.5",
            overflowX: "auto",
          }}
        >
          {MOCK_QUERY_RESULT.sql}
        </pre>

        <p style={{ fontSize: "12.5px", color: "var(--text-secondary)", marginTop: "10px" }}>
          <strong style={{ color: "var(--text-primary)" }}>Query Explanation:</strong> {MOCK_QUERY_RESULT.explanation}
        </p>
      </div>

      {/* Query Result (Table & Chart Views) */}
      <div className="card">
        <div className="card-header">
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <Table size={16} style={{ color: "var(--color-success)" }} />
            <h3 className="card-title">Query Results (5 Rows returned in 34ms)</h3>
          </div>

          <div style={{ display: "flex", gap: "6px" }}>
            <button
              className={`btn ${activeTab === "table" ? "btn-primary" : "btn-secondary"}`}
              style={{ padding: "4px 10px", fontSize: "12px" }}
              onClick={() => setActiveTab("table")}
            >
              <Table size={13} /> Table
            </button>
            <button
              className={`btn ${activeTab === "chart" ? "btn-primary" : "btn-secondary"}`}
              style={{ padding: "4px 10px", fontSize: "12px" }}
              onClick={() => setActiveTab("chart")}
            >
              <BarChart3 size={13} /> Chart
            </button>
          </div>
        </div>

        {activeTab === "table" ? (
          <div className="table-container">
            <table className="enterprise-table">
              <thead>
                <tr>
                  <th>Category Name</th>
                  <th>Total Spend (USD)</th>
                  <th>Total Invoices</th>
                  <th>Avg Cycle (Days)</th>
                </tr>
              </thead>
              <tbody>
                {MOCK_QUERY_RESULT.data.map((row, idx) => (
                  <tr key={idx}>
                    <td style={{ fontWeight: "600", color: "var(--text-primary)" }}>{row.category}</td>
                    <td style={{ fontWeight: "700", color: "var(--color-success-text)", fontFamily: "var(--font-mono)" }}>
                      ${row.spend.toLocaleString()}
                    </td>
                    <td>{row.invoices}</td>
                    <td style={{ color: "var(--text-secondary)" }}>{row.avgDays} days</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div style={{ height: "240px", width: "100%", paddingTop: "10px" }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={MOCK_QUERY_RESULT.data} margin={{ top: 10, right: 20, left: 20, bottom: 20 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#F2F4F7" />
                <XAxis dataKey="category" stroke="#98A2B3" fontSize={11} tickLine={false} />
                <YAxis stroke="#98A2B3" fontSize={11} tickLine={false} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "#FFFFFF",
                    borderColor: "#E4E7EC",
                    borderRadius: "6px",
                    boxShadow: "0 4px 6px -2px rgba(16, 24, 40, 0.08)",
                    color: "#172033",
                  }}
                  formatter={(val) => `$${val.toLocaleString()}`}
                />
                <Bar dataKey="spend" fill="#2563EB" radius={[3, 3, 0, 0]} name="Spend (USD)" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>
    </div>
  );
}
