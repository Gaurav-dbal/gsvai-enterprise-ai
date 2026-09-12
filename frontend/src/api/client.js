// API Client for GSVAI Backend

const DEFAULT_API_URL = "http://127.0.0.1:8000";

export const getApiBaseUrl = () => {
  return localStorage.getItem("gsvai_api_url") || DEFAULT_API_URL;
};

export const setApiBaseUrl = (url) => {
  if (!url) {
    localStorage.removeItem("gsvai_api_url");
  } else {
    localStorage.setItem("gsvai_api_url", url.trim().replace(/\/+$/, ""));
  }
};

/**
 * Check backend health status
 * GET /health
 */
export async function checkBackendHealth() {
  const baseUrl = getApiBaseUrl();
  const startTime = performance.now();
  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 5000);

    const response = await fetch(`${baseUrl}/health`, {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
      },
      signal: controller.signal,
    });

    clearTimeout(timeoutId);
    const latency = Math.round(performance.now() - startTime);

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const data = await response.json();
    return {
      status: "connected",
      data,
      latency,
    };
  } catch (error) {
    return {
      status: "disconnected",
      error: error.message || "Failed to connect to backend",
      latency: null,
    };
  }
}

/**
 * Send chat question to real backend endpoint
 * POST /chat
 * Body: { "question": string }
 * Response: { "answer": string }
 */
export async function sendChatMessage(question) {
  const baseUrl = getApiBaseUrl();
  
  const response = await fetch(`${baseUrl}/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ question }),
  });

  if (!response.ok) {
    const errorText = await response.text().catch(() => "Unknown error");
    throw new Error(`Chat API error (${response.status}): ${errorText}`);
  }

  const data = await response.json();
  return data;
}

/**
 * Upload PDF document for extraction, chunking, embedding, and Oracle Vector storage
 * POST /documents/upload
 * Form field: file
 */
export async function uploadDocument(file) {
  const baseUrl = getApiBaseUrl();
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${baseUrl}/documents/upload`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ detail: "Upload failed" }));
    throw new Error(errorData.detail || `Upload failed with status ${response.status}`);
  }

  const data = await response.json();
  return data;
}

/**
 * Analyze document with Document Intelligence
 * POST /document-intelligence/analyze
 * Form field: file
 */
export async function analyzeDocument(file) {
  const baseUrl = getApiBaseUrl();
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${baseUrl}/document-intelligence/analyze`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ detail: "Document analysis failed" }));
    throw new Error(errorData.detail || `Analysis failed with status ${response.status}`);
  }

  const data = await response.json();
  return data;
}

/**
 * Fetch persisted Document Intelligence records
 * GET /document-intelligence
 */
export async function fetchDocumentIntelligenceRecords() {
  const baseUrl = getApiBaseUrl();

  const response = await fetch(`${baseUrl}/document-intelligence`, {
    method: "GET",
    headers: {
      "Content-Type": "application/json",
    },
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ detail: "Failed to fetch document intelligence records" }));
    throw new Error(errorData.detail || `Request failed with status ${response.status}`);
  }

  const data = await response.json();
  return data;
}

/**
 * Fetch a single persisted Document Intelligence analysis result by ID
 * GET /document-intelligence/{analysisId}
 */
export async function fetchDocumentIntelligenceAnalysis(analysisId) {
  const baseUrl = getApiBaseUrl();

  const response = await fetch(`${baseUrl}/document-intelligence/${analysisId}`, {
    method: "GET",
    headers: {
      "Content-Type": "application/json",
    },
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ detail: `Failed to fetch analysis ${analysisId}` }));
    throw new Error(errorData.detail || `Request failed with status ${response.status}`);
  }

  const data = await response.json();
  return data;
}

/**
 * Fetch all workspace indexed documents from backend
 * GET /ai-workspace/documents
 */
export async function fetchAIWorkspaceDocuments() {
  const baseUrl = getApiBaseUrl();
  let response;

  try {
    response = await fetch(`${baseUrl}/ai-workspace/documents`, {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
      },
    });

    if (response.status === 404) {
      // Fallback to /documents if /ai-workspace/documents is not found
      response = await fetch(`${baseUrl}/documents`, {
        method: "GET",
        headers: {
          "Content-Type": "application/json",
        },
      });
    }
  } catch (netErr) {
    throw new Error(`Connection error: Could not reach backend at ${baseUrl}. ${netErr.message}`);
  }

  if (!response.ok) {
    const errorText = await response.text().catch(() => "Unknown error");
    throw new Error(`Failed to fetch workspace documents (${response.status}): ${errorText}`);
  }

  const data = await response.json();
  return data.documents || (Array.isArray(data) ? data : []);
}

/**
 * Send unified message to AI Workspace (General AI, Enterprise RAG, or Document Context)
 * Primary: POST /ai-workspace/chat (with fallback to POST /chat)
 */
export async function sendAIWorkspaceChat(question, documentId = null, scope = "all", queryMode = null) {
  const baseUrl = getApiBaseUrl();

  const payload = {
    question,
    document_id: documentId,
    scope: scope || "all",
    query_mode: queryMode || null,
  };

  let response;
  try {
    response = await fetch(`${baseUrl}/ai-workspace/chat`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    });

    if (response.status === 404) {
      // Fallback to /chat if /ai-workspace/chat is not found
      response = await fetch(`${baseUrl}/chat`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      });
    }
  } catch (netErr) {
    throw new Error(`Connection error: Could not reach backend at ${baseUrl}. ${netErr.message}`);
  }

  if (!response.ok) {
    const errorText = await response.text().catch(() => "Unknown error");
    throw new Error(`AI Workspace Chat error (${response.status}): ${errorText}`);
  }

  const data = await response.json();
  return data;
}

/**
 * Upload and process document in AI Workspace
 * (OCI Document Understanding OCR -> Oracle Persistence -> Knowledge Vector Indexing)
 * Primary: POST /ai-workspace/upload (with fallback to POST /document-intelligence/analyze)
 */
export async function uploadWorkspaceDocument(file) {
  const baseUrl = getApiBaseUrl();
  const formData = new FormData();
  formData.append("file", file);

  let response;
  try {
    response = await fetch(`${baseUrl}/ai-workspace/upload`, {
      method: "POST",
      body: formData,
    });

    if (response.status === 404) {
      // Fallback to /document-intelligence/analyze if /ai-workspace/upload is not found
      response = await fetch(`${baseUrl}/document-intelligence/analyze`, {
        method: "POST",
        body: formData,
      });
    }
  } catch (netErr) {
    throw new Error(`Connection error: Could not upload to backend at ${baseUrl}. ${netErr.message}`);
  }

  if (!response.ok) {
    let errorDetail = `Upload failed with status ${response.status}`;
    try {
      const errJson = await response.json();
      if (errJson && errJson.detail) {
        errorDetail = typeof errJson.detail === "string" ? errJson.detail : JSON.stringify(errJson.detail);
      }
    } catch {
      const errText = await response.text().catch(() => "");
      if (errText) errorDetail = errText;
    }
    throw new Error(`Document upload error (${response.status}): ${errorDetail}`);
  }

  const data = await response.json();
  return data;
}

/**
 * Upload an invoice PDF to initiate asynchronous OCI Document Understanding processing
 * POST /api/invoices/upload
 * Form field: file
 */
export async function uploadInvoicePdf(file) {
  const baseUrl = getApiBaseUrl();
  const formData = new FormData();
  formData.append("file", file);

  let response;
  try {
    response = await fetch(`${baseUrl}/api/invoices/upload`, {
      method: "POST",
      body: formData,
    });
  } catch (netErr) {
    throw new Error(`Connection error: Could not reach backend at ${baseUrl}. ${netErr.message}`);
  }

  if (!response.ok) {
    let errorDetail = `Upload failed with status ${response.status}`;
    try {
      const errJson = await response.json();
      if (errJson && errJson.detail) {
        errorDetail = typeof errJson.detail === "string" ? errJson.detail : JSON.stringify(errJson.detail);
      }
    } catch {
      const errText = await response.text().catch(() => "");
      if (errText) errorDetail = errText;
    }
    throw new Error(errorDetail);
  }

  return await response.json();
}

/**
 * Get real-time status and progress for an invoice processing task
 * GET /api/invoices/{processing_id}/status
 */
export async function getInvoiceProcessingStatus(processingId) {
  const baseUrl = getApiBaseUrl();
  let response;
  try {
    response = await fetch(`${baseUrl}/api/invoices/${processingId}/status`, {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
      },
    });
  } catch (netErr) {
    throw new Error(`Connection error: Could not check status at ${baseUrl}. ${netErr.message}`);
  }

  if (!response.ok) {
    let errorDetail = `Failed to get status (${response.status})`;
    try {
      const errJson = await response.json();
      if (errJson && errJson.detail) {
        errorDetail = typeof errJson.detail === "string" ? errJson.detail : JSON.stringify(errJson.detail);
      }
    } catch {
      // ignore
    }
    throw new Error(errorDetail);
  }

  return await response.json();
}

/**
 * Get normalized invoice result once processing is completed
 * GET /api/invoices/{processing_id}/result
 */
export async function getInvoiceProcessingResult(processingId) {
  const baseUrl = getApiBaseUrl();
  let response;
  try {
    response = await fetch(`${baseUrl}/api/invoices/${processingId}/result`, {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
      },
    });
  } catch (netErr) {
    throw new Error(`Connection error: Could not fetch result at ${baseUrl}. ${netErr.message}`);
  }

  if (!response.ok) {
    let errorDetail = `Failed to get result (${response.status})`;
    try {
      const errJson = await response.json();
      if (errJson && errJson.detail) {
        errorDetail = typeof errJson.detail === "string" ? errJson.detail : JSON.stringify(errJson.detail);
      }
    } catch {
      // ignore
    }
    throw new Error(errorDetail);
  }

  return await response.json();
}

/**
 * Get Invoice Review Queue (optionally filtered by status)
 * GET /api/invoices/review-queue
 */
export async function getReviewQueue(status = null) {
  const baseUrl = getApiBaseUrl();
  const url = status
    ? `${baseUrl}/api/invoices/review-queue?status=${encodeURIComponent(status)}`
    : `${baseUrl}/api/invoices/review-queue`;

  const response = await fetch(url, {
    method: "GET",
    headers: { "Content-Type": "application/json" },
  });

  if (!response.ok) {
    const errText = await response.text().catch(() => "");
    throw new Error(`Failed to fetch review queue (${response.status}): ${errText}`);
  }

  return await response.json();
}

/**
 * Get detailed invoice data for human review
 * GET /api/invoices/{invoice_id}/review
 */
export async function getInvoiceForReview(invoiceId) {
  const baseUrl = getApiBaseUrl();
  const response = await fetch(`${baseUrl}/api/invoices/${invoiceId}/review`, {
    method: "GET",
    headers: { "Content-Type": "application/json" },
  });

  if (!response.ok) {
    const errText = await response.text().catch(() => "");
    throw new Error(`Failed to load invoice #${invoiceId} (${response.status}): ${errText}`);
  }

  return await response.json();
}

/**
 * Save human corrections to invoice header and lines
 * PUT /api/invoices/{invoice_id}/review
 */
export async function updateInvoiceReview(invoiceId, payload) {
  const baseUrl = getApiBaseUrl();
  const response = await fetch(`${baseUrl}/api/invoices/${invoiceId}/review`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    let errorMsg = `Failed to save corrections (${response.status})`;
    try {
      const errJson = await response.json();
      if (errJson && errJson.detail) errorMsg = errJson.detail;
    } catch {
      // ignore
    }
    throw new Error(errorMsg);
  }

  return await response.json();
}

/**
 * Approve an invoice for Oracle Fusion submission
 * POST /api/invoices/{invoice_id}/approve
 */
export async function approveInvoice(invoiceId, payload = { reviewer: "Human Reviewer", comments: "Approved" }) {
  const baseUrl = getApiBaseUrl();
  const response = await fetch(`${baseUrl}/api/invoices/${invoiceId}/approve`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    let errorMsg = `Approval failed (${response.status})`;
    try {
      const errJson = await response.json();
      if (errJson && errJson.detail) errorMsg = errJson.detail;
    } catch {
      // ignore
    }
    throw new Error(errorMsg);
  }

  return await response.json();
}

/**
 * Reject an invoice with required comments
 * POST /api/invoices/{invoice_id}/reject
 */
export async function rejectInvoice(invoiceId, payload) {
  const baseUrl = getApiBaseUrl();
  const response = await fetch(`${baseUrl}/api/invoices/${invoiceId}/reject`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    let errorMsg = `Rejection failed (${response.status})`;
    try {
      const errJson = await response.json();
      if (errJson && errJson.detail) errorMsg = errJson.detail;
    } catch {
      // ignore
    }
    throw new Error(errorMsg);
  }

  return await response.json();
}

/**
 * Get current user profile and permissions
 * GET /api/auth/me
 */
export async function getCurrentUser() {
  const baseUrl = getApiBaseUrl();
  const response = await fetch(`${baseUrl}/api/auth/me`, {
    method: "GET",
    headers: { "Content-Type": "application/json" },
  });
  if (!response.ok) throw new Error(`Failed to load user profile (${response.status})`);
  return await response.json();
}

/**
 * Admin: Get all users
 * GET /api/admin/users
 */
export async function getAdminUsers() {
  const baseUrl = getApiBaseUrl();
  const response = await fetch(`${baseUrl}/api/admin/users`, {
    method: "GET",
    headers: { "Content-Type": "application/json" },
  });
  if (!response.ok) throw new Error(`Failed to load users (${response.status})`);
  return await response.json();
}

/**
 * Admin: Create user
 * POST /api/admin/users
 */
export async function createAdminUser(userData) {
  const baseUrl = getApiBaseUrl();
  const response = await fetch(`${baseUrl}/api/admin/users`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(userData),
  });
  if (!response.ok) {
    let msg = `Failed to create user (${response.status})`;
    try {
      const err = await response.json();
      if (err.detail) msg = err.detail;
    } catch {}
    throw new Error(msg);
  }
  return await response.json();
}

/**
 * Admin: Update user
 * PUT /api/admin/users/{user_id}
 */
export async function updateAdminUser(userId, updates) {
  const baseUrl = getApiBaseUrl();
  const response = await fetch(`${baseUrl}/api/admin/users/${userId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(updates),
  });
  if (!response.ok) {
    let msg = `Failed to update user (${response.status})`;
    try {
      const err = await response.json();
      if (err.detail) msg = err.detail;
    } catch {}
    throw new Error(msg);
  }
  return await response.json();
}

/**
 * Admin: Get roles & permissions
 * GET /api/admin/roles
 */
export async function getAdminRoles() {
  const baseUrl = getApiBaseUrl();
  const response = await fetch(`${baseUrl}/api/admin/roles`, {
    method: "GET",
    headers: { "Content-Type": "application/json" },
  });
  if (!response.ok) throw new Error(`Failed to load roles (${response.status})`);
  return await response.json();
}

/**
 * Admin: Update role permissions
 * PUT /api/admin/roles/{role_name}
 */
export async function updateAdminRolePermissions(roleName, permissions) {
  const baseUrl = getApiBaseUrl();
  const response = await fetch(`${baseUrl}/api/admin/roles/${roleName}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ permissions }),
  });
  if (!response.ok) throw new Error(`Failed to update permissions (${response.status})`);
  return await response.json();
}

/**
 * Admin: Get audit event logs
 * GET /api/admin/audit-logs
 */
export async function getAdminAuditLogs(limit = 100) {
  const baseUrl = getApiBaseUrl();
  const response = await fetch(`${baseUrl}/api/admin/audit-logs?limit=${limit}`, {
    method: "GET",
    headers: { "Content-Type": "application/json" },
  });
  if (!response.ok) throw new Error(`Failed to load audit logs (${response.status})`);
  return await response.json();
}

/**
 * Get Oracle Fusion connections list
 * GET /api/fusion/connections
 */
export async function getFusionConnections(activeOnly = false) {
  const baseUrl = getApiBaseUrl();
  const response = await fetch(`${baseUrl}/api/fusion/connections?active_only=${activeOnly}`, {
    method: "GET",
    headers: { "Content-Type": "application/json" },
  });
  if (!response.ok) throw new Error(`Failed to fetch Fusion connections (${response.status})`);
  return await response.json();
}

/**
 * Admin: Create new Oracle Fusion connection
 * POST /api/fusion/connections
 */
export async function createFusionConnection(connData) {
  const baseUrl = getApiBaseUrl();
  const response = await fetch(`${baseUrl}/api/fusion/connections`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(connData),
  });
  if (!response.ok) {
    let msg = `Failed to create connection (${response.status})`;
    try {
      const err = await response.json();
      if (err.detail) msg = err.detail;
    } catch {}
    throw new Error(msg);
  }
  return await response.json();
}

/**
 * Admin: Update Oracle Fusion connection
 * PUT /api/fusion/connections/{connection_id}
 */
export async function updateFusionConnection(connectionId, updates) {
  const baseUrl = getApiBaseUrl();
  const response = await fetch(`${baseUrl}/api/fusion/connections/${connectionId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(updates),
  });
  if (!response.ok) {
    let msg = `Failed to update connection (${response.status})`;
    try {
      const err = await response.json();
      if (err.detail) msg = err.detail;
    } catch {}
    throw new Error(msg);
  }
  return await response.json();
}

/**
 * Test Oracle Fusion connection (safe read-only)
 * POST /api/fusion/connections/{connection_id}/test
 */
export async function testFusionConnection(connectionId) {
  const baseUrl = getApiBaseUrl();
  const response = await fetch(`${baseUrl}/api/fusion/connections/${connectionId}/test`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
  });
  if (!response.ok) {
    let msg = `Test failed (${response.status})`;
    try {
      const err = await response.json();
      if (err.detail) msg = err.detail;
    } catch {}
    throw new Error(msg);
  }
  return await response.json();
}

/**
 * Admin: Toggle enable/disable Oracle Fusion connection
 * POST /api/fusion/connections/{connection_id}/disable
 */
export async function disableFusionConnection(connectionId) {
  const baseUrl = getApiBaseUrl();
  const response = await fetch(`${baseUrl}/api/fusion/connections/${connectionId}/disable`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
  });
  if (!response.ok) throw new Error(`Failed to toggle connection state (${response.status})`);
  return await response.json();
}

/**
 * Get schema metadata for a specific Oracle Fusion connection
 * GET /api/fusion/connections/{connection_id}/metadata
 */
export async function getFusionConnectionMetadata(connectionId) {
  const baseUrl = getApiBaseUrl();
  const url = connectionId
    ? `${baseUrl}/api/fusion/connections/${connectionId}/metadata`
    : `${baseUrl}/api/fusion/metadata`;
  const response = await fetch(url, {
    method: "GET",
    headers: { "Content-Type": "application/json" },
  });
  if (!response.ok) throw new Error(`Failed to load Fusion metadata (${response.status})`);
  return await response.json();
}

/**
 * Get Oracle Fusion submission history
 * GET /api/fusion/submissions
 */
export async function getFusionSubmissionHistory(invoiceId = null) {
  const baseUrl = getApiBaseUrl();
  const url = invoiceId
    ? `${baseUrl}/api/fusion/submissions?invoice_id=${invoiceId}`
    : `${baseUrl}/api/fusion/submissions`;
  const response = await fetch(url, {
    method: "GET",
    headers: { "Content-Type": "application/json" },
  });
  if (!response.ok) throw new Error(`Failed to load submission history (${response.status})`);
  return await response.json();
}

/**
 * Get visual field mapping between GSVAI fields and Fusion API fields for an invoice on a connection
 * GET /api/invoices/{invoice_id}/fusion-mapping
 */
export async function getInvoiceFusionMapping(invoiceId, connectionId = null) {
  const baseUrl = getApiBaseUrl();
  const url = connectionId
    ? `${baseUrl}/api/invoices/${invoiceId}/fusion-mapping?connection_id=${connectionId}`
    : `${baseUrl}/api/invoices/${invoiceId}/fusion-mapping`;
  const response = await fetch(url, {
    method: "GET",
    headers: { "Content-Type": "application/json" },
  });

  if (!response.ok) {
    let errorMsg = `Failed to load field mappings (${response.status})`;
    try {
      const errJson = await response.json();
      if (errJson && errJson.detail) errorMsg = errJson.detail;
    } catch {}
    throw new Error(errorMsg);
  }

  return await response.json();
}

/**
 * Save custom field mappings for an invoice on a connection
 * PUT /api/invoices/{invoice_id}/fusion-mapping
 */
export async function saveInvoiceFusionMapping(invoiceId, mappings, connectionId = null) {
  const baseUrl = getApiBaseUrl();
  const response = await fetch(`${baseUrl}/api/invoices/${invoiceId}/fusion-mapping`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ mappings, connection_id: connectionId }),
  });

  if (!response.ok) {
    let errorMsg = `Failed to save field mapping (${response.status})`;
    try {
      const errJson = await response.json();
      if (errJson && errJson.detail) errorMsg = errJson.detail;
    } catch {}
    throw new Error(errorMsg);
  }

  return await response.json();
}

/**
 * Generate preview of Oracle Fusion JSON payload for a connection
 * GET /api/invoices/{invoice_id}/fusion-preview
 */
export async function getFusionPayloadPreview(invoiceId, connectionId = null) {
  const baseUrl = getApiBaseUrl();
  const url = connectionId
    ? `${baseUrl}/api/invoices/${invoiceId}/fusion-preview?connection_id=${connectionId}`
    : `${baseUrl}/api/invoices/${invoiceId}/fusion-preview`;
  const response = await fetch(url, {
    method: "GET",
    headers: { "Content-Type": "application/json" },
  });

  if (!response.ok) {
    let errorMsg = `Failed to preview payload (${response.status})`;
    try {
      const errJson = await response.json();
      if (errJson && errJson.detail) errorMsg = errJson.detail;
    } catch {}
    throw new Error(errorMsg);
  }

  return await response.json();
}

/**
 * Submit an approved invoice to the selected Oracle Fusion connection
 * POST /api/invoices/{invoice_id}/fusion-submit
 */
export async function submitInvoiceToFusion(invoiceId, connectionId, force = false) {
  const baseUrl = getApiBaseUrl();
  const response = await fetch(`${baseUrl}/api/invoices/${invoiceId}/fusion-submit`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ connection_id: connectionId, force }),
  });

  if (!response.ok) {
    let errorMsg = `Fusion submission failed (${response.status})`;
    try {
      const errJson = await response.json();
      if (errJson && errJson.detail) errorMsg = errJson.detail;
    } catch {}
    throw new Error(errorMsg);
  }

  return await response.json();
}

/**
 * Fetch available database sources for Data Assistant
 * GET /api/data-assistant/sources
 */
export async function fetchDataAssistantSources() {
  const baseUrl = getApiBaseUrl();
  const response = await fetch(`${baseUrl}/api/data-assistant/sources`, {
    method: "GET",
    headers: { "Content-Type": "application/json" },
  });

  if (!response.ok) {
    let errorMsg = `Failed to fetch data sources (${response.status})`;
    try {
      const errJson = await response.json();
      if (errJson && errJson.detail) errorMsg = errJson.detail;
    } catch {}
    throw new Error(errorMsg);
  }

  return await response.json();
}

/**
 * Fetch discovered database schema metadata and dynamic prompt suggestions
 * GET /api/data-assistant/schema
 */
export async function fetchDataAssistantSchema(connectionId = null) {
  const baseUrl = getApiBaseUrl();
  const url = connectionId
    ? `${baseUrl}/api/data-assistant/schema?connection_id=${connectionId}`
    : `${baseUrl}/api/data-assistant/schema`;

  const response = await fetch(url, {
    method: "GET",
    headers: { "Content-Type": "application/json" },
  });

  if (!response.ok) {
    let errorMsg = `Failed to fetch schema (${response.status})`;
    try {
      const errJson = await response.json();
      if (errJson && errJson.detail) errorMsg = errJson.detail;
    } catch {}
    throw new Error(errorMsg);
  }

  return await response.json();
}

/**
 * Execute natural language text-to-SQL query against real database
 * POST /api/data-assistant/query
 */
export async function executeDataAssistantQuery({ question, connection_id = null, max_rows = 100 }) {
  const baseUrl = getApiBaseUrl();
  const response = await fetch(`${baseUrl}/api/data-assistant/query`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-User-Id": localStorage.getItem("gsvai_user_id") || "user_admin",
      "X-User-Role": localStorage.getItem("gsvai_user_role") || "ADMIN",
    },
    body: JSON.stringify({ question, connection_id, max_rows }),
  });

  if (!response.ok) {
    let errorMsg = `Data Assistant query failed (${response.status})`;
    try {
      const errJson = await response.json();
      if (errJson && errJson.detail) errorMsg = errJson.detail;
    } catch {}
    throw new Error(errorMsg);
  }

  return await response.json();
}

/**
 * Fetch all configured database connections for Settings
 * GET /api/database/connections
 */
export async function fetchDatabaseConnections(activeOnly = false) {
  const baseUrl = getApiBaseUrl();
  const response = await fetch(`${baseUrl}/api/database/connections?active_only=${activeOnly}`, {
    method: "GET",
    headers: { "Content-Type": "application/json" },
  });

  if (!response.ok) {
    let errorMsg = `Failed to fetch database connections (${response.status})`;
    try {
      const errJson = await response.json();
      if (errJson && errJson.detail) errorMsg = errJson.detail;
    } catch {}
    throw new Error(errorMsg);
  }

  return await response.json();
}

/**
 * Test connectivity for an Oracle Database connection
 * POST /api/database/connections/{connection_id}/test
 */
export async function testDatabaseConnection(connectionId) {
  const baseUrl = getApiBaseUrl();
  const response = await fetch(`${baseUrl}/api/database/connections/${connectionId}/test`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
  });

  if (!response.ok) {
    let errorMsg = `Connection test failed (${response.status})`;
    try {
      const errJson = await response.json();
      if (errJson && errJson.detail) errorMsg = errJson.detail;
    } catch {}
    throw new Error(errorMsg);
  }

  return await response.json();
}

/**
 * Fetch live aggregated platform dashboard statistics from Oracle DB
 * GET /api/dashboard/stats
 */
export async function fetchDashboardStats(period = "today") {
  const baseUrl = getApiBaseUrl();
  const response = await fetch(`${baseUrl}/api/dashboard/stats?period=${encodeURIComponent(period)}`, {
    method: "GET",
    headers: { "Content-Type": "application/json" },
  });

  if (!response.ok) {
    let errorMsg = `Failed to fetch dashboard stats (${response.status})`;
    try {
      const errJson = await response.json();
      if (errJson && errJson.detail) errorMsg = errJson.detail;
    } catch {}
    throw new Error(errorMsg);
  }

  return await response.json();
}

/**
 * Fetch real aggregate invoice and document counters from Oracle DB
 * GET /api/invoices/stats
 */
export async function fetchInvoiceStats() {
  const baseUrl = getApiBaseUrl();
  const response = await fetch(`${baseUrl}/api/invoices/stats`, {
    method: "GET",
    headers: { "Content-Type": "application/json" },
  });

  if (!response.ok) {
    let errorMsg = `Failed to fetch invoice stats (${response.status})`;
    try {
      const errJson = await response.json();
      if (errJson && errJson.detail) errorMsg = errJson.detail;
    } catch {}
    throw new Error(errorMsg);
  }

  return await response.json();
}

/**
 * Fetch comprehensive end-to-end AI/ML/OCR processing trace for an invoice
 * GET /api/invoices/{invoice_id}/trace
 */
export async function fetchInvoiceAITrace(invoiceId) {
  const baseUrl = getApiBaseUrl();
  const response = await fetch(`${baseUrl}/api/invoices/${invoiceId}/trace`, {
    method: "GET",
    headers: { "Content-Type": "application/json" },
  });

  if (!response.ok) {
    let errorMsg = `Failed to fetch invoice AI trace (${response.status})`;
    try {
      const errJson = await response.json();
      if (errJson && errJson.detail) errorMsg = errJson.detail;
    } catch {}
    throw new Error(errorMsg);
  }

  return await response.json();
}

// =========================================================
// Email Automation & AI Triage APIs
// =========================================================

/**
 * Fetch live connectivity status for Email Automation
 * GET /api/email-automation/status
 */
export async function fetchEmailAutomationStatus() {
  const baseUrl = getApiBaseUrl();
  const response = await fetch(`${baseUrl}/api/email-automation/status`, {
    method: "GET",
    headers: { "Content-Type": "application/json" },
  });

  if (!response.ok) {
    let errorMsg = `Failed to fetch email status (${response.status})`;
    try {
      const errJson = await response.json();
      if (errJson?.detail) errorMsg = errJson.detail;
    } catch {}
    throw new Error(errorMsg);
  }

  return await response.json();
}

/**
 * Fetch verified AI model and vector DB configurations
 * GET /api/email-automation/models-config
 */
export async function fetchEmailModelsConfig() {
  const baseUrl = getApiBaseUrl();
  const response = await fetch(`${baseUrl}/api/email-automation/models-config`, {
    method: "GET",
    headers: { "Content-Type": "application/json" },
  });

  if (!response.ok) {
    let errorMsg = `Failed to fetch models config (${response.status})`;
    try {
      const errJson = await response.json();
      if (errJson?.detail) errorMsg = errJson.detail;
    } catch {}
    throw new Error(errorMsg);
  }

  return await response.json();
}

/**
 * Fetch live email inbox from Oracle DB
 * GET /api/email-automation/inbox
 */
export async function fetchEmailInbox(limit = 100) {
  const baseUrl = getApiBaseUrl();
  const response = await fetch(`${baseUrl}/api/email-automation/inbox?limit=${limit}`, {
    method: "GET",
    headers: { "Content-Type": "application/json" },
  });

  if (!response.ok) {
    let errorMsg = `Failed to fetch email inbox (${response.status})`;
    try {
      const errJson = await response.json();
      if (errJson?.detail) errorMsg = errJson.detail;
    } catch {}
    throw new Error(errorMsg);
  }

  return await response.json();
}

/**
 * Sync latest emails from Microsoft Graph into Oracle DB
 * POST /api/email-automation/sync
 */
export async function syncEmailInbox(top = 20) {
  const baseUrl = getApiBaseUrl();
  const response = await fetch(`${baseUrl}/api/email-automation/sync?top=${top}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
  });

  if (!response.ok) {
    let errorMsg = `Failed to sync inbox (${response.status})`;
    try {
      const errJson = await response.json();
      if (errJson?.detail) errorMsg = errJson.detail;
    } catch {}
    throw new Error(errorMsg);
  }

  return await response.json();
}

/**
 * Process unread emails through AI pipeline (Stops at Human Approval)
 * POST /api/email-automation/process
 */
export async function processNewEmails() {
  const baseUrl = getApiBaseUrl();
  const response = await fetch(`${baseUrl}/api/email-automation/process`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
  });

  if (!response.ok) {
    let errorMsg = `Failed to process emails (${response.status})`;
    try {
      const errJson = await response.json();
      if (errJson?.detail) errorMsg = errJson.detail;
    } catch {}
    throw new Error(errorMsg);
  }

  return await response.json();
}

/**
 * Fetch full email record, analysis, RAG sources, draft and 15-stage trace
 * GET /api/email-automation/{email_id}/details
 */
export async function fetchEmailDetails(emailId) {
  const baseUrl = getApiBaseUrl();
  const response = await fetch(`${baseUrl}/api/email-automation/${encodeURIComponent(emailId)}/details`, {
    method: "GET",
    headers: { "Content-Type": "application/json" },
  });

  if (!response.ok) {
    let errorMsg = `Failed to fetch email details (${response.status})`;
    try {
      const errJson = await response.json();
      if (errJson?.detail) errorMsg = errJson.detail;
    } catch {}
    throw new Error(errorMsg);
  }

  return await response.json();
}

/**
 * Retry processing for a throttled email
 * POST /api/email-automation/{email_id}/retry
 */
export async function retryEmailProcessing(emailId) {
  const baseUrl = getApiBaseUrl();
  const response = await fetch(`${baseUrl}/api/email-automation/${encodeURIComponent(emailId)}/retry`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
  });

  if (!response.ok) {
    let errorMsg = `Failed to retry email processing (${response.status})`;
    try {
      const errJson = await response.json();
      if (errJson?.detail) errorMsg = errJson.detail;
    } catch {}
    throw new Error(errorMsg);
  }

  return await response.json();
}

/**
 * Reprocess AI analysis and routing for an email
 * POST /api/email-automation/{email_id}/reprocess
 */
export async function reprocessEmail(emailId) {
  const baseUrl = getApiBaseUrl();
  const response = await fetch(`${baseUrl}/api/email-automation/${encodeURIComponent(emailId)}/reprocess`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
  });

  if (!response.ok) {
    let errorMsg = `Failed to reprocess email (${response.status})`;
    try {
      const errJson = await response.json();
      if (errJson?.detail) errorMsg = errJson.detail;
    } catch {}
    throw new Error(errorMsg);
  }

  return await response.json();
}

/**
 * Human Approval: Dispatch reply via Microsoft Graph
 * POST /api/email-automation/{email_id}/approve-reply
 */
export async function approveAndSendEmailReply(emailId, replyText) {
  const baseUrl = getApiBaseUrl();
  const response = await fetch(`${baseUrl}/api/email-automation/${encodeURIComponent(emailId)}/approve-reply`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ reply_text: replyText }),
  });

  if (!response.ok) {
    let errorMsg = `Failed to approve and send reply (${response.status})`;
    try {
      const errJson = await response.json();
      if (errJson?.detail) errorMsg = errJson.detail;
    } catch {}
    throw new Error(errorMsg);
  }

  return await response.json();
}

/**
 * Reject or route email to human review
 * POST /api/email-automation/{email_id}/reject
 */
export async function rejectEmail(emailId, reason = "Sent to manual review") {
  const baseUrl = getApiBaseUrl();
  const response = await fetch(`${baseUrl}/api/email-automation/${encodeURIComponent(emailId)}/reject`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ reason }),
  });

  if (!response.ok) {
    let errorMsg = `Failed to route email (${response.status})`;
    try {
      const errJson = await response.json();
      if (errJson?.detail) errorMsg = errJson.detail;
    } catch {}
    throw new Error(errorMsg);
  }

  return await response.json();
}

/**
 * Admin: Get live AI runtime configuration metadata
 * GET /api/settings/ai-runtime
 */
export async function getAIRuntimeConfig() {
  const baseUrl = getApiBaseUrl();
  const response = await fetch(`${baseUrl}/api/settings/ai-runtime`, {
    method: "GET",
    headers: { "Content-Type": "application/json" },
  });
  if (!response.ok) {
    let msg = `Failed to load AI runtime configuration (${response.status})`;
    try {
      const err = await response.json();
      if (err.detail) msg = err.detail;
    } catch {}
    throw new Error(msg);
  }
  return await response.json();
}

/**
 * Admin: Get all configured AI models and current active runtime
 * GET /api/settings/ai-models
 */
export async function getAIModels() {
  const baseUrl = getApiBaseUrl();
  const response = await fetch(`${baseUrl}/api/settings/ai-models`, {
    method: "GET",
    headers: { "Content-Type": "application/json" },
  });
  if (!response.ok) {
    let msg = `Failed to load AI models (${response.status})`;
    try {
      const err = await response.json();
      if (err.detail) msg = err.detail;
    } catch {}
    throw new Error(msg);
  }
  return await response.json();
}

/**
 * Admin: Create a new AI model in persistent registry
 * POST /api/settings/ai-models
 */
export async function createAIModel(modelData) {
  const baseUrl = getApiBaseUrl();
  const response = await fetch(`${baseUrl}/api/settings/ai-models`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(modelData),
  });
  if (!response.ok) {
    let msg = `Failed to create AI model (${response.status})`;
    try {
      const err = await response.json();
      if (err.detail) msg = err.detail;
    } catch {}
    throw new Error(msg);
  }
  return await response.json();
}

/**
 * Admin: Update an existing AI model
 * PUT /api/settings/ai-models/{model_id}
 */
export async function updateAIModel(modelId, updates) {
  const baseUrl = getApiBaseUrl();
  const response = await fetch(`${baseUrl}/api/settings/ai-models/${modelId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(updates),
  });
  if (!response.ok) {
    let msg = `Failed to update AI model (${response.status})`;
    try {
      const err = await response.json();
      if (err.detail) msg = err.detail;
    } catch {}
    throw new Error(msg);
  }
  return await response.json();
}

/**
 * Admin: Delete an existing AI model
 * DELETE /api/settings/ai-models/{model_id}
 */
export async function deleteAIModel(modelId) {
  const baseUrl = getApiBaseUrl();
  const response = await fetch(`${baseUrl}/api/settings/ai-models/${modelId}`, {
    method: "DELETE",
    headers: { "Content-Type": "application/json" },
  });
  if (!response.ok) {
    let msg = `Failed to delete AI model (${response.status})`;
    try {
      const err = await response.json();
      if (err.detail) msg = err.detail;
    } catch {}
    throw new Error(msg);
  }
  return await response.json();
}

/**
 * Admin: Enable an AI model
 * POST /api/settings/ai-models/{model_id}/enable
 */
export async function enableAIModel(modelId) {
  const baseUrl = getApiBaseUrl();
  const response = await fetch(`${baseUrl}/api/settings/ai-models/${modelId}/enable`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
  });
  if (!response.ok) {
    let msg = `Failed to enable AI model (${response.status})`;
    try {
      const err = await response.json();
      if (err.detail) msg = err.detail;
    } catch {}
    throw new Error(msg);
  }
  return await response.json();
}

/**
 * Admin: Disable an AI model
 * POST /api/settings/ai-models/{model_id}/disable
 */
export async function disableAIModel(modelId) {
  const baseUrl = getApiBaseUrl();
  const response = await fetch(`${baseUrl}/api/settings/ai-models/${modelId}/disable`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
  });
  if (!response.ok) {
    let msg = `Failed to disable AI model (${response.status})`;
    try {
      const err = await response.json();
      if (err.detail) msg = err.detail;
    } catch {}
    throw new Error(msg);
  }
  return await response.json();
}

/**
 * Admin: Set model as Primary LLM
 * POST /api/settings/ai-models/{model_id}/set-primary
 */
export async function setPrimaryAIModel(modelId) {
  const baseUrl = getApiBaseUrl();
  const response = await fetch(`${baseUrl}/api/settings/ai-models/${modelId}/set-primary`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
  });
  if (!response.ok) {
    let msg = `Failed to set primary model (${response.status})`;
    try {
      const err = await response.json();
      if (err.detail) msg = err.detail;
    } catch {}
    throw new Error(msg);
  }
  return await response.json();
}

/**
 * Admin: Set model as Fallback LLM
 * POST /api/settings/ai-models/{model_id}/set-fallback
 */
export async function setFallbackAIModel(modelId) {
  const baseUrl = getApiBaseUrl();
  const response = await fetch(`${baseUrl}/api/settings/ai-models/${modelId}/set-fallback`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
  });
  if (!response.ok) {
    let msg = `Failed to set fallback model (${response.status})`;
    try {
      const err = await response.json();
      if (err.detail) msg = err.detail;
    } catch {}
    throw new Error(msg);
  }
  return await response.json();
}

/**
 * Admin: Test model connectivity and latency
 * POST /api/settings/ai-models/{model_id}/test
 */
export async function testAIModel(modelId) {
  const baseUrl = getApiBaseUrl();
  const response = await fetch(`${baseUrl}/api/settings/ai-models/${modelId}/test`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
  });
  if (!response.ok) {
    let msg = `Failed to test AI model (${response.status})`;
    try {
      const err = await response.json();
      if (err.detail) msg = err.detail;
    } catch {}
    throw new Error(msg);
  }
  return await response.json();
}

// ============================================================
// Phase 3: RAG & Knowledge Base
// ============================================================

export async function getRagKnowledgeStats() {
  const baseUrl = getApiBaseUrl();
  const response = await fetch(`${baseUrl}/api/settings/rag-knowledge/stats`, {
    method: "GET",
    headers: { "Content-Type": "application/json" },
  });
  if (!response.ok) throw new Error(`Failed to load RAG stats (${response.status})`);
  return await response.json();
}

export async function getRagKnowledgeHealth() {
  const baseUrl = getApiBaseUrl();
  const response = await fetch(`${baseUrl}/api/settings/rag-knowledge/health`, {
    method: "GET",
    headers: { "Content-Type": "application/json" },
  });
  if (!response.ok) throw new Error(`Failed to check RAG health (${response.status})`);
  return await response.json();
}

export async function getRagKnowledgeDocuments() {
  const baseUrl = getApiBaseUrl();
  const response = await fetch(`${baseUrl}/api/settings/rag-knowledge/documents`, {
    method: "GET",
    headers: { "Content-Type": "application/json" },
  });
  if (!response.ok) throw new Error(`Failed to load knowledge documents (${response.status})`);
  return await response.json();
}

export async function testRagRetrieval(queryOrObj, topK = 5) {
  const baseUrl = getApiBaseUrl();
  let payload = {};
  if (typeof queryOrObj === "object" && queryOrObj !== null) {
    payload = {
      query: queryOrObj.query || "",
      top_k: queryOrObj.top_k || topK,
    };
  } else {
    payload = {
      query: queryOrObj,
      top_k: topK,
    };
  }
  const response = await fetch(`${baseUrl}/api/settings/rag-knowledge/retrieval-test`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    let msg = `Retrieval test failed (${response.status})`;
    try {
      const err = await response.json();
      if (err.detail) msg = err.detail;
    } catch {}
    throw new Error(msg);
  }
  return await response.json();
}

export async function reprocessKnowledgeDocument(documentId) {
  const baseUrl = getApiBaseUrl();
  const response = await fetch(`${baseUrl}/api/settings/rag-knowledge/documents/${documentId}/reprocess`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
  });
  if (!response.ok) {
    let msg = `Reprocess failed (${response.status})`;
    try {
      const err = await response.json();
      if (err.detail) msg = err.detail;
    } catch {}
    throw new Error(msg);
  }
  return await response.json();
}

export async function deleteKnowledgeDocument(documentId) {
  const baseUrl = getApiBaseUrl();
  const response = await fetch(`${baseUrl}/api/settings/rag-knowledge/documents/${documentId}`, {
    method: "DELETE",
    headers: { "Content-Type": "application/json" },
  });
  if (!response.ok) {
    let msg = `Delete failed (${response.status})`;
    try {
      const err = await response.json();
      if (err.detail) msg = err.detail;
    } catch {}
    throw new Error(msg);
  }
  return await response.json();
}

// ============================================================
// Phase 4: AI Observability & Telemetry
// ============================================================

export async function getAIObservabilitySummary() {
  const baseUrl = getApiBaseUrl();
  const response = await fetch(`${baseUrl}/api/settings/ai-observability/summary`, {
    method: "GET",
    headers: { "Content-Type": "application/json" },
  });
  if (!response.ok) throw new Error(`Failed to load observability summary (${response.status})`);
  return await response.json();
}

export async function getAIObservabilityRequests(limit = 50, provider = null, status = null) {
  const baseUrl = getApiBaseUrl();
  const params = new URLSearchParams({ limit });
  if (provider && provider !== "ALL") params.append("provider", provider);
  if (status && status !== "ALL") params.append("status_filter", status);

  const response = await fetch(`${baseUrl}/api/settings/ai-observability/requests?${params.toString()}`, {
    method: "GET",
    headers: { "Content-Type": "application/json" },
  });
  if (!response.ok) throw new Error(`Failed to load requests (${response.status})`);
  return await response.json();
}

export async function getAIObservabilityProviders() {
  const baseUrl = getApiBaseUrl();
  const response = await fetch(`${baseUrl}/api/settings/ai-observability/providers`, {
    method: "GET",
    headers: { "Content-Type": "application/json" },
  });
  if (!response.ok) throw new Error(`Failed to load provider metrics (${response.status})`);
  return await response.json();
}

export async function getAIObservabilityTrace(requestId) {
  const baseUrl = getApiBaseUrl();
  const response = await fetch(`${baseUrl}/api/settings/ai-observability/traces/${requestId}`, {
    method: "GET",
    headers: { "Content-Type": "application/json" },
  });
  if (!response.ok) throw new Error(`Failed to load trace (${response.status})`);
  return await response.json();
}

// ============================================================
// Phase 5: AI Security & Guardrails
// ============================================================

export async function getAISecurityOverview() {
  const baseUrl = getApiBaseUrl();
  const response = await fetch(`${baseUrl}/api/settings/ai-security`, {
    method: "GET",
    headers: { "Content-Type": "application/json" },
  });
  if (!response.ok) throw new Error(`Failed to load security overview (${response.status})`);
  return await response.json();
}

export async function getAISecurityEvents(limit = 50) {
  const baseUrl = getApiBaseUrl();
  const response = await fetch(`${baseUrl}/api/settings/ai-security/events?limit=${limit}`, {
    method: "GET",
    headers: { "Content-Type": "application/json" },
  });
  if (!response.ok) throw new Error(`Failed to load security events (${response.status})`);
  return await response.json();
}

export async function testAISecurity(controlOrObj, payload) {
  const baseUrl = getApiBaseUrl();
  let body = {};
  if (typeof controlOrObj === "object" && controlOrObj !== null) {
    body = {
      control: controlOrObj.control || "prompt_injection",
      payload: controlOrObj.payload || controlOrObj.input_text || "",
      input_text: controlOrObj.input_text || controlOrObj.payload || "",
    };
  } else {
    body = {
      control: controlOrObj || "prompt_injection",
      payload: payload || "",
      input_text: payload || "",
    };
  }
  const response = await fetch(`${baseUrl}/api/settings/ai-security/test`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    let msg = `Security test failed (${response.status})`;
    try {
      const err = await response.json();
      if (err.detail) msg = err.detail;
    } catch {}
    throw new Error(msg);
  }
  return await response.json();
}

// ============================================================
// Phase 6: AI Agents Control Center
// ============================================================

export async function getAIAgents() {
  const baseUrl = getApiBaseUrl();
  const response = await fetch(`${baseUrl}/api/settings/ai-agents`, {
    method: "GET",
    headers: { "Content-Type": "application/json" },
  });
  if (!response.ok) throw new Error(`Failed to load AI agents (${response.status})`);
  return await response.json();
}

export async function getAIAgentsHistory(limit = 50) {
  const baseUrl = getApiBaseUrl();
  const response = await fetch(`${baseUrl}/api/settings/ai-agents/history?limit=${limit}`, {
    method: "GET",
    headers: { "Content-Type": "application/json" },
  });
  if (!response.ok) throw new Error(`Failed to load agent history (${response.status})`);
  return await response.json();
}

export async function getAIAgentDetail(agentId) {
  const baseUrl = getApiBaseUrl();
  const response = await fetch(`${baseUrl}/api/settings/ai-agents/${agentId}`, {
    method: "GET",
    headers: { "Content-Type": "application/json" },
  });
  if (!response.ok) throw new Error(`Failed to load agent detail (${response.status})`);
  return await response.json();
}

export async function testAIAgent(agentId, testPayload = null) {
  const baseUrl = getApiBaseUrl();
  let pld = null;
  if (typeof testPayload === "object" && testPayload !== null) {
    pld = testPayload.query || testPayload.test_payload || JSON.stringify(testPayload);
  } else {
    pld = testPayload;
  }
  const response = await fetch(`${baseUrl}/api/settings/ai-agents/${agentId}/test`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ test_payload: pld }),
  });
  if (!response.ok) {
    let msg = `Agent diagnostic test failed (${response.status})`;
    try {
      const err = await response.json();
      if (err.detail) msg = err.detail;
    } catch {}
    throw new Error(msg);
  }
  return await response.json();
}
