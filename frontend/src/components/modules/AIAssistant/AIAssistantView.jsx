import React, { useState, useRef, useEffect } from "react";
import {
  Bot,
  Send,
  User,
  Sparkles,
  Copy,
  Check,
  RefreshCw,
  Trash2,
} from "lucide-react";
import { SectionHeader } from "../../common/SectionHeader";
import { sendChatMessage } from "../../../api/client";

const SUGGESTIONS = [
  "What is Generative AI and how does it transform enterprise workflows?",
  "Explain how OCI Generative AI with Cohere Command A processes enterprise queries.",
  "What are the best practices for automated invoice 3-way matching in ERP systems?",
  "Summarize the key architectural benefits of RAG in enterprise document intelligence.",
];

export function AIAssistantView({ backendStatus, backendLatency }) {
  const [messages, setMessages] = useState([
    {
      id: "welcome-1",
      sender: "assistant",
      text: "Hello! I am your **GSVAI Enterprise Intelligence Assistant**, connected directly to **OCI Generative AI (Cohere Command A)**.\n\nAsk me anything about enterprise workflows, business intelligence, document extraction, or technical architecture.",
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    },
  ]);
  const [inputQuery, setInputQuery] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [copiedId, setCopiedId] = useState(null);
  const [errorMessage, setErrorMessage] = useState(null);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  const handleSendMessage = async (textToSend) => {
    const query = (textToSend || inputQuery).trim();
    if (!query || isLoading) return;

    setErrorMessage(null);
    const userMsgId = `user-${Date.now()}`;
    const userMsg = {
      id: userMsgId,
      sender: "user",
      text: query,
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    };

    setMessages((prev) => [...prev, userMsg]);
    setInputQuery("");
    setIsLoading(true);

    try {
      // Real API call to FastAPI backend POST /chat -> OCI Generative AI Cohere Command A
      const response = await sendChatMessage(query);
      
      const assistantMsg = {
        id: `assistant-${Date.now()}`,
        sender: "assistant",
        text: response.answer || "No response received from backend.",
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      };

      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err) {
      console.error("AI Assistant Chat Error:", err);
      const errMsg = err.message || "Failed to communicate with FastAPI backend.";
      setErrorMessage(errMsg);

      const errorBotMsg = {
        id: `error-${Date.now()}`,
        sender: "assistant",
        isError: true,
        text: `⚠️ **Connection Error**: Could not reach backend.\n\n*Details*: \`${errMsg}\`\n\nPlease ensure the FastAPI server is running on \`http://127.0.0.1:8000\`.`,
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      };
      setMessages((prev) => [...prev, errorBotMsg]);
    } finally {
      setIsLoading(false);
      setTimeout(() => inputRef.current?.focus(), 100);
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
    setMessages([
      {
        id: `welcome-${Date.now()}`,
        sender: "assistant",
        text: "Conversation reset. How can I assist you with enterprise intelligence today?",
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      },
    ]);
    setErrorMessage(null);
  };

  return (
    <div className="animate-fade-in" style={{ display: "flex", flexDirection: "column", height: "100%", gap: "16px" }}>
      {/* Header */}
      <SectionHeader
        title="Live AI Intelligence Assistant"
        description="Direct conversational interface powered by OCI Generative AI (Cohere Command A) on-demand in ap-hyderabad-1."
        isLive={true}
        badgeText="LIVE OCI COHERE COMMAND A"
        actions={
          <button className="btn btn-secondary" onClick={handleClearHistory} title="Clear conversation history">
            <Trash2 size={14} />
            Clear
          </button>
        }
      />

      {/* Main Chat Interface */}
      <div className="chat-container">
        {/* Messages Scroll Area */}
        <div className="chat-messages">
          {messages.map((msg) => {
            const isUser = msg.sender === "user";
            const isCopied = copiedId === msg.id;

            return (
              <div key={msg.id} className={`chat-bubble-row ${isUser ? "user" : "assistant"}`}>
                <div className={`chat-avatar ${isUser ? "user" : "assistant"}`}>
                  {isUser ? <User size={16} /> : <Bot size={16} />}
                </div>

                <div style={{ display: "flex", flexDirection: "column", gap: "4px", maxWidth: "100%" }}>
                  <div className={`chat-bubble ${isUser ? "user" : "assistant"}`}>
                    <div style={{ whiteSpace: "pre-wrap", wordBreak: "break-word" }}>
                      {msg.text}
                    </div>
                  </div>

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
                        {isCopied ? <Check size={11} style={{ color: "var(--color-success-text)" }} /> : <Copy size={11} />}
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
                <Bot size={16} />
              </div>
              <div className="chat-bubble assistant" style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <RefreshCw size={14} className="animate-spin" style={{ color: "var(--color-primary)" }} />
                <span style={{ fontSize: "13px", color: "var(--text-secondary)" }}>
                  OCI Cohere Command A is generating response...
                </span>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Input & Suggestions Footer */}
        <div className="chat-footer">
          {/* Quick suggestions chips */}
          <div className="prompt-chips">
            <span style={{ fontSize: "11.5px", color: "var(--text-secondary)", display: "flex", alignItems: "center", gap: "4px" }}>
              <Sparkles size={12} style={{ color: "var(--color-primary)" }} /> Prompts:
            </span>
            {SUGGESTIONS.map((sug, idx) => (
              <button
                key={idx}
                className="prompt-chip"
                onClick={() => handleSendMessage(sug)}
                disabled={isLoading}
              >
                {sug}
              </button>
            ))}
          </div>

          {/* Chat Input Field */}
          <div className="chat-input-row">
            <input
              ref={inputRef}
              type="text"
              className="chat-input"
              placeholder={isLoading ? "Generating response..." : "Ask GSVAI Assistant anything..."}
              value={inputQuery}
              onChange={(e) => setInputQuery(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={isLoading}
            />

            <button
              className="btn btn-primary"
              style={{ height: "42px", padding: "0 18px" }}
              onClick={() => handleSendMessage()}
              disabled={!inputQuery.trim() || isLoading}
            >
              {isLoading ? <RefreshCw size={16} className="animate-spin" /> : <Send size={16} />}
              <span>Send</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
