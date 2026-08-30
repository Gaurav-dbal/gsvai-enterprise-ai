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

