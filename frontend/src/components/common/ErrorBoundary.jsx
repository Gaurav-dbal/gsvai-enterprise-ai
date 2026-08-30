import React from "react";
import { AlertTriangle, RefreshCw } from "lucide-react";

export class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error("GSVAI Uncaught Runtime Exception:", error, errorInfo);
    this.setState({ errorInfo });
  }

  handleReload = () => {
    window.location.reload();
  };

  render() {
    if (this.state.hasError) {
      return (
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            minHeight: "100vh",
            backgroundColor: "#0B0F19",
            color: "#F3F4F6",
            padding: "24px",
            fontFamily: "Inter, system-ui, -apple-system, sans-serif",
          }}
        >
          <div
            style={{
              maxWidth: "600px",
              width: "100%",
              backgroundColor: "#111827",
              border: "1px solid #1F2937",
              borderRadius: "12px",
              padding: "32px",
              boxShadow: "0 20px 25px -5px rgba(0, 0, 0, 0.5)",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: "12px", marginBottom: "16px" }}>
              <div
                style={{
                  width: "42px",
                  height: "42px",
                  borderRadius: "8px",
                  backgroundColor: "rgba(239, 68, 68, 0.15)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  color: "#EF4444",
                }}
              >
                <AlertTriangle size={22} />
              </div>
              <div>
                <h2 style={{ fontSize: "18px", fontWeight: "700", margin: 0, color: "#F9FAFB" }}>
                  GSVAI APPLICATION ERROR
                </h2>
                <p style={{ fontSize: "12px", color: "#9CA3AF", margin: "2px 0 0 0" }}>
                  The application encountered an unexpected runtime error.
                </p>
              </div>
            </div>

            <p style={{ fontSize: "13px", color: "#D1D5DB", lineHeight: "1.6", marginBottom: "20px" }}>
              An unexpected error occurred while rendering the user interface. You can try refreshing the page or navigating back.
            </p>

            {/* Developer Details in Development */}
            {this.state.error && (
              <div style={{ marginBottom: "24px" }}>
                <span style={{ fontSize: "11px", fontWeight: "700", color: "#9CA3AF", textTransform: "uppercase" }}>
                  Developer Diagnostics:
                </span>
                <pre
                  style={{
                    marginTop: "6px",
                    padding: "12px",
                    borderRadius: "6px",
                    backgroundColor: "#030712",
                    border: "1px solid #374151",
                    color: "#F87171",
                    fontSize: "11.5px",
                    fontFamily: "monospace",
                    overflowX: "auto",
                    whiteSpace: "pre-wrap",
                  }}
                >
                  {this.state.error.toString()}
                  {this.state.errorInfo?.componentStack && (
                    <div style={{ marginTop: "8px", color: "#9CA3AF", fontSize: "10.5px" }}>
                      {this.state.errorInfo.componentStack}
                    </div>
                  )}
                </pre>
              </div>
            )}

            <div style={{ display: "flex", gap: "10px", justifyContent: "flex-end" }}>
              <button
                onClick={this.handleReload}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "6px",
                  padding: "8px 18px",
                  borderRadius: "6px",
                  backgroundColor: "#2563EB",
                  color: "#FFFFFF",
                  border: "none",
                  fontWeight: "600",
                  fontSize: "13px",
                  cursor: "pointer",
                }}
              >
                <RefreshCw size={14} />
                Refresh Application
              </button>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
