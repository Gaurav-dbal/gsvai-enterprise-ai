import React, { useState, useEffect, useCallback } from "react";
import { Sidebar, NAV_ITEMS } from "./components/layout/Sidebar";
import { Header } from "./components/layout/Header";
import { OverviewView } from "./components/modules/Overview/OverviewView";
import { AIWorkspaceView } from "./components/modules/AIWorkspace/AIWorkspaceView";
import { AIAssistantView } from "./components/modules/AIAssistant/AIAssistantView";
import { KnowledgeAssistantView } from "./components/modules/KnowledgeAssistant/KnowledgeAssistantView";
import { DocumentIntelligenceView } from "./components/modules/DocumentIntelligence/DocumentIntelligenceView";
import { InvoiceAutomationView } from "./components/modules/InvoiceAutomation/InvoiceAutomationView";
import { DataAssistantView } from "./components/modules/DataAssistant/DataAssistantView";
import { EmailAutomationView } from "./components/modules/EmailAutomation/EmailAutomationView";
import { SettingsView } from "./components/modules/Settings/SettingsView";
import { checkBackendHealth } from "./api/client";
import "./App.css";

function App() {
  const [activeTab, setActiveTab] = useState("overview");
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
  const [backendStatus, setBackendStatus] = useState("checking");
  const [backendData, setBackendData] = useState(null);
  const [backendLatency, setBackendLatency] = useState(null);
  const [isRefreshingHealth, setIsRefreshingHealth] = useState(false);

  // Health check function
  const refreshHealth = useCallback(async () => {
    setIsRefreshingHealth(true);
    const result = await checkBackendHealth();
    if (result.status === "connected") {
      setBackendStatus("connected");
      setBackendData(result.data);
      setBackendLatency(result.latency);
    } else {
      setBackendStatus("disconnected");
      setBackendData(null);
      setBackendLatency(null);
    }
    setIsRefreshingHealth(false);
  }, []);

  // Poll backend health on initial load and periodically
  useEffect(() => {
    refreshHealth();
    const interval = setInterval(refreshHealth, 30000);
    return () => clearInterval(interval);
  }, [refreshHealth]);

  // Find active nav item details
  const activeNavItem = NAV_ITEMS.find((item) => item.id === activeTab) || NAV_ITEMS[0];

  // Render view based on activeTab
  const renderView = () => {
    switch (activeTab) {
      case "overview":
        return (
          <OverviewView
            onNavigate={setActiveTab}
            backendStatus={backendStatus}
            latency={backendLatency}
          />
        );
      case "ai-workspace":
        return (
          <AIWorkspaceView
            backendStatus={backendStatus}
            backendLatency={backendLatency}
          />
        );
      case "ai-assistant":
      case "knowledge-assistant":
      case "document-intelligence":
        return (
          <AIWorkspaceView
            backendStatus={backendStatus}
            backendLatency={backendLatency}
          />
        );
      case "invoice-automation":
      case "invoice-review":
      case "invoice-approval":
        return <InvoiceAutomationView />;
      case "data-assistant":
        return <DataAssistantView />;
      case "email-automation":
        return <EmailAutomationView />;
      case "settings":
        return <SettingsView onHealthCheckUpdate={refreshHealth} onNavigate={setActiveTab} />;
      default:
        return (
          <OverviewView
            onNavigate={setActiveTab}
            backendStatus={backendStatus}
            latency={backendLatency}
          />
        );
    }
  };

  return (
    <div className="app-container">
      {/* Left Sidebar */}
      <Sidebar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        isCollapsed={isSidebarCollapsed}
        setIsCollapsed={setIsSidebarCollapsed}
        backendStatus={backendStatus}
      />

      {/* Main Content Area */}
      <div className="main-wrapper">
        {/* Global Top Header */}
        <Header
          activeTitle={activeNavItem.label}
          backendStatus={backendStatus}
          backendData={backendData}
          latency={backendLatency}
          onRefreshHealth={refreshHealth}
          isRefreshing={isRefreshingHealth}
        />

        {/* Dynamic View Content */}
        <main className="content-area">
          {renderView()}
        </main>
      </div>
    </div>
  );
}

export default App;