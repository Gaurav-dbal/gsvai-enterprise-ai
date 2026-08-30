import React, { useState, useEffect } from "react";
import {
  Server,
  Cpu,
  RefreshCw,
  CheckCircle,
  XCircle,
  Save,
  Layers,
  Users,
  Shield,
  Database,
  Sliders,
  History,
  Plus,
  Edit,
  Trash2,
  Lock,
  ExternalLink,
  ShieldCheck,
  AlertCircle,
  Check,
  Power,
  ChevronRight,
  Eye,
  UserCheck,
} from "lucide-react";
import { SectionHeader } from "../../common/SectionHeader";
import { StatusBadge } from "../../common/Badge";
import {
  getApiBaseUrl,
  setApiBaseUrl,
  checkBackendHealth,
  getCurrentUser,
  getAdminUsers,
  createAdminUser,
  updateAdminUser,
  getAdminRoles,
  updateAdminRolePermissions,
  getAdminAuditLogs,
  getFusionConnections,
  createFusionConnection,
  updateFusionConnection,
  testFusionConnection,
  disableFusionConnection,
} from "../../../api/client";

export function SettingsView({ onHealthCheckUpdate, onNavigate }) {
  // Navigation sub-tab: 'general' | 'users' | 'roles' | 'fusion' | 'integrations' | 'audit'
  const [activeTab, setActiveTab] = useState("general");

  // --- Current User / Auth State ---
  const [currentUser, setCurrentUser] = useState(null);

  // --- General Tab State ---
  const [apiUrl, setApiUrl] = useState(getApiBaseUrl());
  const [isTestingBackend, setIsTestingBackend] = useState(false);
  const [backendTestResult, setBackendTestResult] = useState(null);
  const [backendSavedSuccess, setBackendSavedSuccess] = useState(false);

  // --- Users Tab State ---
  const [usersList, setUsersList] = useState([]);
  const [usersLoading, setUsersLoading] = useState(false);
  const [isAddUserModalOpen, setIsAddUserModalOpen] = useState(false);
  const [isEditUserModalOpen, setIsEditUserModalOpen] = useState(false);
  const [selectedUserForEdit, setSelectedUserForEdit] = useState(null);
  const [userFormData, setUserFormData] = useState({
    username: "",
    email: "",
    full_name: "",
    role: "USER",
    status: "ACTIVE",
  });

  // --- Roles Tab State ---
  const [rolesList, setRolesList] = useState([]);
  const [rolesLoading, setRolesLoading] = useState(false);
  const [selectedRole, setSelectedRole] = useState(null);
  const [rolePermissionsDraft, setRolePermissionsDraft] = useState([]);
  const [roleSaveSuccess, setRoleSaveSuccess] = useState(false);

  // --- Fusion Connections State ---
  const [fusionConnections, setFusionConnections] = useState([]);
  const [fusionConnsLoading, setFusionConnsLoading] = useState(false);
  const [isAddConnModalOpen, setIsAddConnModalOpen] = useState(false);
  const [isEditConnModalOpen, setIsEditConnModalOpen] = useState(false);
  const [selectedConnForEdit, setSelectedConnForEdit] = useState(null);
  const [testingConnId, setTestingConnId] = useState(null);
  const [connTestResults, setConnTestResults] = useState({});
  const [connFormData, setConnFormData] = useState({
    connection_name: "",
    base_url: "",
    environment: "TEST",
    authentication_type: "BASIC",
    username: "",
    password_secret: "",
    business_unit: "US1 Business Unit",
    default_currency: "USD",
  });

  // --- Audit Logs State ---
  const [auditLogs, setAuditLogs] = useState([]);
  const [auditLoading, setAuditLoading] = useState(false);

  // Global message / error
  const [notification, setNotification] = useState(null);

  useEffect(() => {
    loadCurrentUser();
  }, []);

  useEffect(() => {
    if (activeTab === "users") loadUsers();
    if (activeTab === "roles") loadRoles();
    if (activeTab === "fusion") loadFusionConnections();
    if (activeTab === "audit") loadAuditLogs();
  }, [activeTab]);

  const loadCurrentUser = async () => {
    try {
      const u = await getCurrentUser();
      setCurrentUser(u);
    } catch (err) {
      console.warn("Could not fetch user profile:", err);
    }
  };

  const showNotification = (msg, type = "success") => {
    setNotification({ msg, type });
    setTimeout(() => setNotification(null), 4000);
  };

  // --- General Handlers ---
  const handleSaveApiUrl = () => {
    setApiBaseUrl(apiUrl);
    setBackendSavedSuccess(true);
    setTimeout(() => setBackendSavedSuccess(false), 2500);
    handleTestBackendConnection();
  };

  const handleTestBackendConnection = async () => {
    setIsTestingBackend(true);
    setBackendTestResult(null);
    const res = await checkBackendHealth();
    setBackendTestResult(res);
    setIsTestingBackend(false);
    if (onHealthCheckUpdate) onHealthCheckUpdate();
  };

  // --- Users Handlers ---
  const loadUsers = async () => {
    setUsersLoading(true);
    try {
      const data = await getAdminUsers();
      setUsersList(data || []);
    } catch (err) {
      showNotification(err.message, "error");
    } finally {
      setUsersLoading(false);
    }
  };

  const handleCreateUser = async (e) => {
    e.preventDefault();
    try {
      await createAdminUser(userFormData);
      setIsAddUserModalOpen(false);
      setUserFormData({ username: "", email: "", full_name: "", role: "USER", status: "ACTIVE" });
      showNotification(`User ${userFormData.username} created successfully.`);
      loadUsers();
    } catch (err) {
      showNotification(err.message, "error");
    }
  };

  const handleUpdateUser = async (e) => {
    e.preventDefault();
    if (!selectedUserForEdit) return;
    try {
      await updateAdminUser(selectedUserForEdit.user_id, {
        email: userFormData.email,
        full_name: userFormData.full_name,
        role: userFormData.role,
        status: userFormData.status,
      });
      setIsEditUserModalOpen(false);
      setSelectedUserForEdit(null);
      showNotification("User updated successfully.");
      loadUsers();
    } catch (err) {
      showNotification(err.message, "error");
    }
  };

  const handleToggleUserStatus = async (user) => {
    const newStatus = user.status === "ACTIVE" ? "DISABLED" : "ACTIVE";
    try {
      await updateAdminUser(user.user_id, { status: newStatus });
      showNotification(`User ${user.username} set to ${newStatus}.`);
      loadUsers();
    } catch (err) {
      showNotification(err.message, "error");
    }
  };

  // --- Roles Handlers ---
  const loadRoles = async () => {
    setRolesLoading(true);
    try {
      const data = await getAdminRoles();
      setRolesList(data || []);
      if (data && data.length > 0) {
        setSelectedRole(data[0]);
        setRolePermissionsDraft(data[0].permissions || []);
      }
    } catch (err) {
      showNotification(err.message, "error");
    } finally {
      setRolesLoading(false);
    }
  };

  const handleSelectRole = (role) => {
    setSelectedRole(role);
    setRolePermissionsDraft(role.permissions || []);
    setRoleSaveSuccess(false);
  };

  const handleTogglePermission = (permKey) => {
    if (rolePermissionsDraft.includes(permKey)) {
      setRolePermissionsDraft(rolePermissionsDraft.filter((p) => p !== permKey));
    } else {
      setRolePermissionsDraft([...rolePermissionsDraft, permKey]);
    }
  };

  const handleSaveRolePermissions = async () => {
    if (!selectedRole) return;
    try {
      await updateAdminRolePermissions(selectedRole.role_name, rolePermissionsDraft);
      setRoleSaveSuccess(true);
      setTimeout(() => setRoleSaveSuccess(false), 3000);
      showNotification(`Permissions saved for role ${selectedRole.role_name}`);
      loadRoles();
    } catch (err) {
      showNotification(err.message, "error");
    }
  };

  // --- Fusion Connections Handlers ---
  const loadFusionConnections = async () => {
    setFusionConnsLoading(true);
    try {
      const data = await getFusionConnections();
      setFusionConnections(data || []);
    } catch (err) {
      showNotification(err.message, "error");
    } finally {
      setFusionConnsLoading(false);
    }
  };

  const handleCreateConnection = async (e) => {
    e.preventDefault();
    try {
      await createFusionConnection(connFormData);
      setIsAddConnModalOpen(false);
      setConnFormData({
        connection_name: "",
        base_url: "",
        environment: "TEST",
        authentication_type: "BASIC",
        username: "",
        password_secret: "",
        business_unit: "US1 Business Unit",
        default_currency: "USD",
      });
      showNotification("Fusion connection created with status NOT_TESTED. Please test connectivity.");
      loadFusionConnections();
    } catch (err) {
      showNotification(err.message, "error");
    }
  };

  const handleUpdateConnection = async (e) => {
    e.preventDefault();
    if (!selectedConnForEdit) return;
    try {
      await updateFusionConnection(selectedConnForEdit.connection_id, connFormData);
      setIsEditConnModalOpen(false);
      setSelectedConnForEdit(null);
      showNotification("Connection updated.");
      loadFusionConnections();
    } catch (err) {
      showNotification(err.message, "error");
    }
  };

  const handleTestConnection = async (connId) => {
    setTestingConnId(connId);
    try {
      const res = await testFusionConnection(connId);
      setConnTestResults((prev) => ({ ...prev, [connId]: res }));
      showNotification(
        `Connection #${connId} (${res.connection_name}) tested: ${res.status} — ${res.message}`,
        res.is_connected ? "success" : "error"
      );
      loadFusionConnections();
    } catch (err) {
      showNotification(`Test failed: ${err.message}`, "error");
    } finally {
      setTestingConnId(null);
    }
  };

  const handleToggleConnectionActive = async (connId) => {
    try {
      await disableFusionConnection(connId);
      showNotification(`Connection #${connId} state toggled.`);
      loadFusionConnections();
    } catch (err) {
      showNotification(err.message, "error");
    }
  };

  // --- Audit Logs Handlers ---
  const loadAuditLogs = async () => {
    setAuditLoading(true);
    try {
      const data = await getAdminAuditLogs(100);
      setAuditLogs(data || []);
    } catch (err) {
      showNotification(err.message, "error");
    } finally {
      setAuditLoading(false);
    }
  };

  const PERMISSION_GROUPS = [
    {
      group: "User & Role Administration",
      permissions: [
        { key: "USER_VIEW", label: "View Users" },
        { key: "USER_MANAGE", label: "Manage Users (Create/Edit/Disable)" },
        { key: "ROLE_VIEW", label: "View Roles" },
        { key: "ROLE_MANAGE", label: "Manage Roles & Permissions" },
      ],
    },
    {
      group: "Oracle Fusion Connections",
      permissions: [
        { key: "FUSION_CONNECTION_VIEW", label: "View Fusion Connections" },
        { key: "FUSION_CONNECTION_CREATE", label: "Create Fusion Connection" },
        { key: "FUSION_CONNECTION_EDIT", label: "Edit Fusion Connection" },
        { key: "FUSION_CONNECTION_TEST", label: "Test Connection Connectivity" },
        { key: "FUSION_CONNECTION_DISABLE", label: "Enable/Disable Connection" },
      ],
    },
    {
      group: "Invoice Lifecycle & Workflow",
      permissions: [
        { key: "INVOICE_VIEW", label: "View Invoices & Queue" },
        { key: "INVOICE_UPLOAD", label: "Upload Invoice PDFs" },
        { key: "INVOICE_REVIEW", label: "Access Review Workspace" },
        { key: "INVOICE_EDIT", label: "Save Field Corrections" },
        { key: "INVOICE_APPROVE", label: "Approve Invoices" },
        { key: "INVOICE_REJECT", label: "Reject Invoices" },
      ],
    },
    {
      group: "ERP Mapping & Submission",
      permissions: [
        { key: "FUSION_MAPPING_VIEW", label: "View Field Mapping & Preview" },
        { key: "FUSION_MAPPING_EDIT", label: "Save Custom Field Mapping" },
        { key: "FUSION_SUBMIT", label: "Submit to Oracle Fusion ERP" },
        { key: "AUDIT_VIEW", label: "View System & Security Audit Logs" },
      ],
    },
  ];

  return (
    <div className="animate-fade-in" style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
      {/* Module Title Header */}
      <SectionHeader
        title="Administration & Platform Control Center"
        description="Manage system infrastructure, user accounts, role-based access control (RBAC), and Oracle Cloud ERP Fusion connection environments."
        isLive={currentUser?.role === "ADMIN"}
        badgeText={currentUser?.role === "ADMIN" ? "ADMINISTRATOR" : "STANDARD USER"}
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
            className={`btn ${activeTab === "general" ? "btn-primary" : "btn-secondary"}`}
            onClick={() => setActiveTab("general")}
            style={{ fontSize: "12.5px", padding: "6px 14px" }}
          >
            <Server size={14} />
            General & API
          </button>

          <button
            className={`btn ${activeTab === "users" ? "btn-primary" : "btn-secondary"}`}
            onClick={() => setActiveTab("users")}
            style={{ fontSize: "12.5px", padding: "6px 14px" }}
          >
            <Users size={14} />
            Users
          </button>

          <button
            className={`btn ${activeTab === "roles" ? "btn-primary" : "btn-secondary"}`}
            onClick={() => setActiveTab("roles")}
            style={{ fontSize: "12.5px", padding: "6px 14px" }}
          >
            <Shield size={14} />
            Roles & Permissions
          </button>

          <button
            className={`btn ${activeTab === "fusion" ? "btn-primary" : "btn-secondary"}`}
            onClick={() => setActiveTab("fusion")}
            style={{ fontSize: "12.5px", padding: "6px 14px" }}
          >
            <Database size={14} />
            Oracle Fusion Connections
            {fusionConnections.length > 0 && (
              <span
                style={{
                  marginLeft: "6px",
                  padding: "1px 6px",
                  borderRadius: "10px",
                  backgroundColor: activeTab === "fusion" ? "rgba(255,255,255,0.25)" : "var(--bg-surface-subtle)",
                  fontSize: "11px",
                  fontWeight: "700",
                }}
              >
                {fusionConnections.length}
              </span>
            )}
          </button>

          <button
            className={`btn ${activeTab === "integrations" ? "btn-primary" : "btn-secondary"}`}
            onClick={() => setActiveTab("integrations")}
            style={{ fontSize: "12.5px", padding: "6px 14px" }}
          >
            <Sliders size={14} />
            Integration Settings
          </button>

          <button
            className={`btn ${activeTab === "audit" ? "btn-primary" : "btn-secondary"}`}
            onClick={() => setActiveTab("audit")}
            style={{ fontSize: "12.5px", padding: "6px 14px" }}
          >
            <History size={14} />
            Audit & Security Logs
          </button>
        </div>

        {/* Current User Badge */}
        {currentUser && (
          <div style={{ display: "flex", alignItems: "center", gap: "8px", fontSize: "12px" }}>
            <span style={{ color: "var(--text-secondary)" }}>Active Identity:</span>
            <span style={{ fontWeight: "700", color: "var(--color-primary)" }}>{currentUser.username}</span>
            <span style={{ padding: "2px 8px", borderRadius: "10px", backgroundColor: "var(--color-primary-light)", color: "var(--color-primary)", fontWeight: "600", fontSize: "11px" }}>
              {currentUser.role}
            </span>
          </div>
        )}
      </div>

      {/* Global Notifications */}
      {notification && (
        <div
          style={{
            padding: "12px 18px",
            borderRadius: "var(--radius-md)",
            backgroundColor: notification.type === "error" ? "rgba(239, 68, 68, 0.08)" : "rgba(16, 185, 129, 0.08)",
            border: `1px solid ${notification.type === "error" ? "rgba(239, 68, 68, 0.3)" : "rgba(16, 185, 129, 0.3)"}`,
            color: notification.type === "error" ? "#b91c1c" : "#047857",
            fontSize: "13px",
            fontWeight: "600",
            display: "flex",
            alignItems: "center",
            gap: "10px",
          }}
        >
          {notification.type === "error" ? <AlertCircle size={16} /> : <CheckCircle size={16} />}
          <span>{notification.msg}</span>
        </div>
      )}

      {/* ============================================================= */}
      {/* TAB 1: GENERAL & BACKEND CONFIGURATION                        */}
      {/* ============================================================= */}
      {activeTab === "general" && (
        <div className="grid-2">
          {/* Backend API Configuration */}
          <div className="card" style={{ display: "flex", flexDirection: "column", gap: "14px", padding: "24px" }}>
            <div className="card-header">
              <h3 className="card-title" style={{ fontSize: "15px", fontWeight: "700" }}>
                <Server size={16} style={{ color: "var(--color-primary)" }} />
                FastAPI Backend Connection
              </h3>
              <span className="badge badge-live">Configurable</span>
            </div>

            <div>
              <label style={{ fontSize: "12.5px", color: "var(--text-secondary)", fontWeight: "500", display: "block", marginBottom: "4px" }}>
                Backend Base URL
              </label>
              <div style={{ display: "flex", gap: "8px" }}>
                <input
                  type="text"
                  className="input"
                  style={{ flex: 1 }}
                  value={apiUrl}
                  onChange={(e) => setApiUrl(e.target.value)}
                  placeholder="http://127.0.0.1:8000"
                />
                <button className="btn btn-primary" onClick={handleSaveApiUrl}>
                  <Save size={14} /> Save
                </button>
              </div>
              {backendSavedSuccess && (
                <span style={{ fontSize: "12px", color: "#059669", display: "block", marginTop: "4px", fontWeight: "600" }}>
                  ✓ API Base URL updated successfully.
                </span>
              )}
            </div>

            {/* Health Verification */}
            <div style={{ paddingTop: "12px", borderTop: "1px solid var(--border-subtle)" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span style={{ fontSize: "12.5px", color: "var(--text-secondary)" }}>
                  Health Check Endpoint (`GET /health`)
                </span>
                <button className="btn btn-secondary" onClick={handleTestBackendConnection} disabled={isTestingBackend} style={{ fontSize: "12px" }}>
                  <RefreshCw size={13} className={isTestingBackend ? "spin" : ""} />
                  Test Health
                </button>
              </div>

              {backendTestResult && (
                <div
                  style={{
                    marginTop: "12px",
                    padding: "10px 14px",
                    borderRadius: "var(--radius-md)",
                    backgroundColor: backendTestResult.status === "connected" ? "rgba(16, 185, 129, 0.08)" : "rgba(239, 68, 68, 0.08)",
                    border: `1px solid ${backendTestResult.status === "connected" ? "rgba(16, 185, 129, 0.3)" : "rgba(239, 68, 68, 0.3)"}`,
                    fontSize: "12.5px",
                  }}
                >
                  {backendTestResult.status === "connected" ? (
                    <div style={{ display: "flex", alignItems: "center", gap: "8px", color: "#047857", fontWeight: "600" }}>
                      <CheckCircle size={15} />
                      Connected to {backendTestResult.data?.service} (v{backendTestResult.data?.version}) • Latency: {backendTestResult.latency}ms
                    </div>
                  ) : (
                    <div style={{ display: "flex", alignItems: "center", gap: "8px", color: "#b91c1c", fontWeight: "600" }}>
                      <XCircle size={15} />
                      Connection Failed: {backendTestResult.error}
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>

          {/* System Infrastructure Details */}
          <div className="card" style={{ padding: "24px", display: "flex", flexDirection: "column", gap: "14px" }}>
            <div className="card-header">
              <h3 className="card-title" style={{ fontSize: "15px", fontWeight: "700" }}>
                <Cpu size={16} style={{ color: "var(--color-primary)" }} />
                Platform Infrastructure
              </h3>
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: "10px", fontSize: "12.5px" }}>
              <div style={{ padding: "8px 12px", backgroundColor: "var(--bg-surface-subtle)", borderRadius: "var(--radius-sm)", display: "flex", justifyContent: "space-between" }}>
                <span style={{ color: "var(--text-secondary)" }}>Oracle Database:</span>
                <strong>Autonomous Vector Database 23ai</strong>
              </div>
              <div style={{ padding: "8px 12px", backgroundColor: "var(--bg-surface-subtle)", borderRadius: "var(--radius-sm)", display: "flex", justifyContent: "space-between" }}>
                <span style={{ color: "var(--text-secondary)" }}>OCI GenAI Region:</span>
                <strong>ap-hyderabad-1</strong>
              </div>
              <div style={{ padding: "8px 12px", backgroundColor: "var(--bg-surface-subtle)", borderRadius: "var(--radius-sm)", display: "flex", justifyContent: "space-between" }}>
                <span style={{ color: "var(--text-secondary)" }}>OCI Document Understanding:</span>
                <strong>Active (INVOICE Processor)</strong>
              </div>
              <div style={{ padding: "8px 12px", backgroundColor: "var(--bg-surface-subtle)", borderRadius: "var(--radius-sm)", display: "flex", justifyContent: "space-between" }}>
                <span style={{ color: "var(--text-secondary)" }}>Role-Based Access Control:</span>
                <strong>Enforced via Backend Authorization</strong>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ============================================================= */}
      {/* TAB 2: USER MANAGEMENT                                        */}
      {/* ============================================================= */}
      {activeTab === "users" && (
        <div className="card" style={{ padding: "20px" }}>
          <div className="card-header" style={{ marginBottom: "16px" }}>
            <div>
              <h3 className="card-title" style={{ fontSize: "16px", fontWeight: "700" }}>User Accounts & Identities</h3>
              <p className="card-subtitle" style={{ fontSize: "12.5px" }}>Manage platform users, assigned roles, and operational status</p>
            </div>
            <button className="btn btn-primary" onClick={() => setIsAddUserModalOpen(true)} style={{ fontSize: "12.5px" }}>
              <Plus size={14} /> Add User
            </button>
          </div>

          <div className="table-container">
            <table className="enterprise-table">
              <thead>
                <tr>
                  <th>Username</th>
                  <th>Full Name</th>
                  <th>Email</th>
                  <th>Assigned Role</th>
                  <th>Status</th>
                  <th style={{ width: "140px", textAlign: "center" }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {usersLoading ? (
                  <tr><td colSpan={6} style={{ textAlign: "center", padding: "24px" }}>Loading user directory...</td></tr>
                ) : usersList.length === 0 ? (
                  <tr><td colSpan={6} style={{ textAlign: "center", padding: "24px" }}>No users registered.</td></tr>
                ) : (
                  usersList.map((u) => (
                    <tr key={u.user_id}>
                      <td style={{ fontWeight: "700", color: "var(--color-primary)", fontFamily: "var(--font-mono)" }}>
                        {u.username}
                      </td>
                      <td style={{ fontWeight: "600", color: "var(--text-primary)" }}>{u.full_name || "—"}</td>
                      <td style={{ color: "var(--text-secondary)", fontSize: "12px" }}>{u.email}</td>
                      <td>
                        <span style={{ padding: "2px 8px", borderRadius: "10px", backgroundColor: "var(--color-primary-light)", color: "var(--color-primary)", fontWeight: "700", fontSize: "11px" }}>
                          {u.role}
                        </span>
                      </td>
                      <td><StatusBadge status={u.status} /></td>
                      <td style={{ textAlign: "center" }}>
                        <div style={{ display: "flex", justifyContent: "center", gap: "6px" }}>
                          <button
                            className="btn btn-secondary"
                            style={{ padding: "3px 8px", fontSize: "11px" }}
                            onClick={() => {
                              setSelectedUserForEdit(u);
                              setUserFormData({
                                username: u.username,
                                email: u.email,
                                full_name: u.full_name || "",
                                role: u.role,
                                status: u.status,
                              });
                              setIsEditUserModalOpen(true);
                            }}
                          >
                            <Edit size={12} /> Edit
                          </button>
                          <button
                            className="btn btn-secondary"
                            style={{ padding: "3px 8px", fontSize: "11px", color: u.status === "ACTIVE" ? "#b91c1c" : "#047857" }}
                            onClick={() => handleToggleUserStatus(u)}
                          >
                            <Power size={12} /> {u.status === "ACTIVE" ? "Disable" : "Enable"}
                          </button>
                        </div>
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
      {/* TAB 3: ROLES & PERMISSIONS MATRIX                             */}
      {/* ============================================================= */}
      {activeTab === "roles" && (
        <div className="grid-3" style={{ gap: "20px" }}>
          {/* Left Column: Role Selector */}
          <div className="card" style={{ padding: "18px" }}>
            <div className="card-header" style={{ marginBottom: "14px" }}>
              <h3 className="card-title" style={{ fontSize: "15px", fontWeight: "700" }}>System Roles</h3>
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
              {rolesList.map((r) => {
                const isSelected = selectedRole?.role_name === r.role_name;
                return (
                  <div
                    key={r.role_name}
                    onClick={() => handleSelectRole(r)}
                    style={{
                      padding: "12px 14px",
                      borderRadius: "var(--radius-md)",
                      border: `1px solid ${isSelected ? "var(--color-primary)" : "var(--border-subtle)"}`,
                      backgroundColor: isSelected ? "var(--color-primary-light)" : "var(--bg-surface-subtle)",
                      cursor: "pointer",
                    }}
                  >
                    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                      <strong style={{ fontSize: "13px", color: isSelected ? "var(--color-primary)" : "var(--text-primary)" }}>
                        {r.role_name}
                      </strong>
                      <span style={{ fontSize: "11px", color: "var(--text-muted)" }}>
                        {r.permissions.length} perms
                      </span>
                    </div>
                    <div style={{ fontSize: "11.5px", color: "var(--text-secondary)", marginTop: "4px", lineHeight: "1.4" }}>
                      {r.description}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Right 2 Columns: Permissions Matrix for Selected Role */}
          {selectedRole && (
            <div className="card" style={{ gridColumn: "span 2", padding: "20px" }}>
              <div className="card-header" style={{ marginBottom: "16px" }}>
                <div>
                  <h3 className="card-title" style={{ fontSize: "15px", fontWeight: "700" }}>
                    Permissions for {selectedRole.role_name}
                  </h3>
                  <p className="card-subtitle" style={{ fontSize: "12px" }}>
                    Granular backend authorization permissions assigned to this role
                  </p>
                </div>
                <button className="btn btn-primary" onClick={handleSaveRolePermissions} style={{ fontSize: "12.5px" }}>
                  <Save size={14} /> Save Permissions
                </button>
              </div>

              {roleSaveSuccess && (
                <div style={{ padding: "8px 12px", backgroundColor: "rgba(16, 185, 129, 0.1)", color: "#047857", borderRadius: "var(--radius-sm)", fontSize: "12px", fontWeight: "600", marginBottom: "14px" }}>
                  ✓ Permissions updated successfully for {selectedRole.role_name}.
                </div>
              )}

              <div style={{ display: "flex", flexDirection: "column", gap: "18px" }}>
                {PERMISSION_GROUPS.map((grp) => (
                  <div key={grp.group} style={{ backgroundColor: "var(--bg-surface-subtle)", padding: "14px", borderRadius: "var(--radius-md)" }}>
                    <h4 style={{ fontSize: "12px", fontWeight: "700", color: "var(--color-primary)", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "10px" }}>
                      {grp.group}
                    </h4>
                    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px" }}>
                      {grp.permissions.map((p) => {
                        const isChecked = rolePermissionsDraft.includes(p.key);
                        return (
                          <label
                            key={p.key}
                            style={{
                              display: "flex",
                              alignItems: "center",
                              gap: "8px",
                              fontSize: "12.5px",
                              cursor: "pointer",
                              color: isChecked ? "var(--text-primary)" : "var(--text-secondary)",
                              fontWeight: isChecked ? "600" : "400",
                            }}
                          >
                            <input
                              type="checkbox"
                              checked={isChecked}
                              onChange={() => handleTogglePermission(p.key)}
                              style={{ width: "15px", height: "15px", cursor: "pointer" }}
                            />
                            <span>{p.label}</span>
                          </label>
                        );
                      })}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* ============================================================= */}
      {/* TAB 4: ORACLE FUSION CONNECTIONS MANAGEMENT                   */}
      {/* ============================================================= */}
      {activeTab === "fusion" && (
        <div className="card" style={{ padding: "20px" }}>
          <div className="card-header" style={{ marginBottom: "16px", flexWrap: "wrap", gap: "12px" }}>
            <div>
              <h3 className="card-title" style={{ fontSize: "16px", fontWeight: "700" }}>Oracle Fusion Connections</h3>
              <p className="card-subtitle" style={{ fontSize: "12.5px" }}>
                Administrator-configured Oracle Cloud ERP Payables environments. Zero default URLs. Must be tested before use.
              </p>
            </div>
            <button className="btn btn-primary" onClick={() => setIsAddConnModalOpen(true)} style={{ fontSize: "12.5px" }}>
              <Plus size={14} /> Add Fusion Connection
            </button>
          </div>

          <div className="table-container">
            <table className="enterprise-table">
              <thead>
                <tr>
                  <th style={{ width: "50px" }}>ID</th>
                  <th>Connection Name</th>
                  <th>Environment</th>
                  <th>Base URL</th>
                  <th>Business Unit</th>
                  <th>Status</th>
                  <th>Last Tested</th>
                  <th style={{ width: "200px", textAlign: "center" }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {fusionConnsLoading ? (
                  <tr><td colSpan={8} style={{ textAlign: "center", padding: "24px" }}>Loading connections...</td></tr>
                ) : fusionConnections.length === 0 ? (
                  <tr>
                    <td colSpan={8} style={{ textAlign: "center", padding: "30px", color: "var(--text-secondary)" }}>
                      <AlertCircle size={20} style={{ color: "var(--text-muted)", margin: "0 auto 8px" }} />
                      No Oracle Fusion connections configured. Click <strong>Add Fusion Connection</strong> to register an environment.
                    </td>
                  </tr>
                ) : (
                  fusionConnections.map((c) => {
                    const isTestingThis = testingConnId === c.connection_id;
                    return (
                      <tr key={c.connection_id}>
                        <td style={{ fontFamily: "var(--font-mono)", fontWeight: "700", color: "var(--color-primary)" }}>
                          #{c.connection_id}
                        </td>
                        <td style={{ fontWeight: "700", color: "var(--text-primary)" }}>{c.connection_name}</td>
                        <td>
                          <span style={{ padding: "2px 8px", borderRadius: "10px", backgroundColor: "var(--bg-surface-subtle)", border: "1px solid var(--border-subtle)", fontWeight: "700", fontSize: "11px" }}>
                            {c.environment}
                          </span>
                        </td>
                        <td style={{ fontFamily: "var(--font-mono)", fontSize: "11.5px", maxWidth: "220px", overflow: "hidden", textOverflow: "ellipsis" }}>
                          {c.base_url}
                        </td>
                        <td style={{ fontSize: "12px", color: "var(--text-secondary)" }}>{c.business_unit || "—"}</td>
                        <td>
                          {c.status === "CONNECTED" ? (
                            <span style={{ fontSize: "11px", padding: "3px 8px", borderRadius: "12px", backgroundColor: "rgba(16, 185, 129, 0.1)", color: "#047857", fontWeight: "700", display: "inline-flex", alignItems: "center", gap: "4px" }}>
                              <CheckCircle size={12} /> Connected
                            </span>
                          ) : c.status === "FAILED" ? (
                            <span style={{ fontSize: "11px", padding: "3px 8px", borderRadius: "12px", backgroundColor: "rgba(239, 68, 68, 0.1)", color: "#b91c1c", fontWeight: "700", display: "inline-flex", alignItems: "center", gap: "4px" }}>
                              <XCircle size={12} /> Failed
                            </span>
                          ) : c.status === "DISABLED" ? (
                            <span style={{ fontSize: "11px", padding: "3px 8px", borderRadius: "12px", backgroundColor: "var(--bg-surface-subtle)", color: "var(--text-muted)", fontWeight: "600" }}>
                              Disabled
                            </span>
                          ) : (
                            <span style={{ fontSize: "11px", padding: "3px 8px", borderRadius: "12px", backgroundColor: "rgba(245, 158, 11, 0.1)", color: "#d97706", fontWeight: "700" }}>
                              Not Tested
                            </span>
                          )}
                        </td>
                        <td style={{ fontSize: "11.5px", color: "var(--text-secondary)" }}>
                          {c.last_tested_at ? c.last_tested_at.slice(0, 10) : "Never"}
                        </td>
                        <td style={{ textAlign: "center" }}>
                          <div style={{ display: "flex", justifyContent: "center", gap: "6px" }}>
                            <button
                              className="btn btn-secondary"
                              style={{ padding: "3px 8px", fontSize: "11px" }}
                              onClick={() => handleTestConnection(c.connection_id)}
                              disabled={isTestingThis}
                              title="Perform safe read-only connectivity test"
                            >
                              <RefreshCw size={12} className={isTestingThis ? "spin" : ""} />
                              {isTestingThis ? "Testing..." : "Test"}
                            </button>
                            <button
                              className="btn btn-secondary"
                              style={{ padding: "3px 8px", fontSize: "11px" }}
                              onClick={() => {
                                setSelectedConnForEdit(c);
                                setConnFormData({
                                  connection_name: c.connection_name,
                                  base_url: c.base_url,
                                  environment: c.environment,
                                  authentication_type: c.authentication_type || "BASIC",
                                  username: c.username || "",
                                  password_secret: "",
                                  business_unit: c.business_unit || "US1 Business Unit",
                                  default_currency: c.default_currency || "USD",
                                });
                                setIsEditConnModalOpen(true);
                              }}
                            >
                              <Edit size={12} /> Edit
                            </button>
                            <button
                              className="btn btn-secondary"
                              style={{ padding: "3px 8px", fontSize: "11px", color: c.is_active ? "#b91c1c" : "#047857" }}
                              onClick={() => handleToggleConnectionActive(c.connection_id)}
                            >
                              <Power size={12} /> {c.is_active ? "Disable" : "Enable"}
                            </button>
                          </div>
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* ============================================================= */}
      {/* TAB 5: INTEGRATION SETTINGS                                   */}
      {/* ============================================================= */}
      {activeTab === "integrations" && (
        <div className="card" style={{ padding: "24px" }}>
          <div className="card-header" style={{ marginBottom: "18px" }}>
            <h3 className="card-title" style={{ fontSize: "16px", fontWeight: "700" }}>Global Integration Parameters</h3>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px" }}>
            <div>
              <label style={{ fontSize: "12px", fontWeight: "600", color: "var(--text-secondary)", display: "block", marginBottom: "4px" }}>
                Default Base Currency
              </label>
              <input type="text" className="input" defaultValue="USD" style={{ width: "100%" }} />
            </div>
            <div>
              <label style={{ fontSize: "12px", fontWeight: "600", color: "var(--text-secondary)", display: "block", marginBottom: "4px" }}>
                Default Payment Terms
              </label>
              <input type="text" className="input" defaultValue="Net 30" style={{ width: "100%" }} />
            </div>
            <div>
              <label style={{ fontSize: "12px", fontWeight: "600", color: "var(--text-secondary)", display: "block", marginBottom: "4px" }}>
                REST Connection Timeout (Seconds)
              </label>
              <input type="number" className="input" defaultValue="30" style={{ width: "100%" }} />
            </div>
            <div>
              <label style={{ fontSize: "12px", fontWeight: "600", color: "var(--text-secondary)", display: "block", marginBottom: "4px" }}>
                Automatic Retry Limit on Failed Submissions
              </label>
              <input type="number" className="input" defaultValue="3" style={{ width: "100%" }} />
            </div>
          </div>
        </div>
      )}

      {/* ============================================================= */}
      {/* TAB 6: AUDIT LOGS                                             */}
      {/* ============================================================= */}
      {activeTab === "audit" && (
        <div className="card" style={{ padding: "20px" }}>
          <div className="card-header" style={{ marginBottom: "16px" }}>
            <div>
              <h3 className="card-title" style={{ fontSize: "16px", fontWeight: "700" }}>Platform & Security Audit Trail</h3>
              <p className="card-subtitle" style={{ fontSize: "12.5px" }}>Live audit log records from Oracle Database (GSVAI_AUDIT_LOGS)</p>
            </div>
            <button className="btn btn-secondary" onClick={loadAuditLogs} style={{ fontSize: "12px" }}>
              <RefreshCw size={13} className={auditLoading ? "spin" : ""} /> Refresh
            </button>
          </div>

          <div className="table-container">
            <table className="enterprise-table">
              <thead>
                <tr>
                  <th style={{ width: "60px" }}>Log ID</th>
                  <th>Timestamp</th>
                  <th>Actor / User</th>
                  <th>Action</th>
                  <th>Resource</th>
                  <th>Resource ID</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {auditLoading ? (
                  <tr><td colSpan={7} style={{ textAlign: "center", padding: "24px" }}>Loading audit stream...</td></tr>
                ) : auditLogs.length === 0 ? (
                  <tr><td colSpan={7} style={{ textAlign: "center", padding: "24px" }}>No audit events logged yet.</td></tr>
                ) : (
                  auditLogs.map((log) => (
                    <tr key={log.log_id}>
                      <td style={{ fontFamily: "var(--font-mono)", fontWeight: "600", color: "var(--color-primary)" }}>
                        #{log.log_id}
                      </td>
                      <td style={{ fontSize: "11.5px", color: "var(--text-secondary)" }}>{log.created_at || "—"}</td>
                      <td style={{ fontWeight: "700", color: "var(--text-primary)" }}>{log.user_id}</td>
                      <td>
                        <span style={{ fontSize: "11px", fontWeight: "700", padding: "2px 6px", borderRadius: "4px", backgroundColor: "var(--bg-surface-subtle)" }}>
                          {log.action}
                        </span>
                      </td>
                      <td style={{ fontSize: "12px", color: "var(--text-secondary)" }}>{log.resource_type}</td>
                      <td style={{ fontFamily: "var(--font-mono)", fontSize: "11.5px" }}>{log.resource_id || "—"}</td>
                      <td>
                        <span style={{ fontSize: "11px", padding: "2px 6px", borderRadius: "8px", backgroundColor: log.status === "SUCCESS" || log.status === "CONNECTED" ? "rgba(16, 185, 129, 0.1)" : "rgba(239, 68, 68, 0.1)", color: log.status === "SUCCESS" || log.status === "CONNECTED" ? "#047857" : "#b91c1c", fontWeight: "600" }}>
                          {log.status || "SUCCESS"}
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

      {/* ============================================================= */}
      {/* MODAL: ADD USER                                               */}
      {/* ============================================================= */}
      {isAddUserModalOpen && (
        <div style={{ position: "fixed", top: 0, left: 0, width: "100vw", height: "100vh", backgroundColor: "rgba(0,0,0,0.5)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000 }}>
          <div className="card animate-scale-up" style={{ width: "480px", padding: "24px" }}>
            <h3 style={{ fontSize: "16px", fontWeight: "700", marginBottom: "16px", display: "flex", alignItems: "center", gap: "8px" }}>
              <Users size={18} style={{ color: "var(--color-primary)" }} /> Add User Account
            </h3>
            <form onSubmit={handleCreateUser} style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
              <div>
                <label style={{ fontSize: "12px", fontWeight: "600", display: "block", marginBottom: "4px" }}>Username *</label>
                <input
                  type="text"
                  required
                  className="input"
                  value={userFormData.username}
                  onChange={(e) => setUserFormData({ ...userFormData, username: e.target.value })}
                  style={{ width: "100%" }}
                  placeholder="e.g. john_doe"
                />
              </div>
              <div>
                <label style={{ fontSize: "12px", fontWeight: "600", display: "block", marginBottom: "4px" }}>Email *</label>
                <input
                  type="email"
                  required
                  className="input"
                  value={userFormData.email}
                  onChange={(e) => setUserFormData({ ...userFormData, email: e.target.value })}
                  style={{ width: "100%" }}
                  placeholder="john@enterprise.ai"
                />
              </div>
              <div>
                <label style={{ fontSize: "12px", fontWeight: "600", display: "block", marginBottom: "4px" }}>Full Name</label>
                <input
                  type="text"
                  className="input"
                  value={userFormData.full_name}
                  onChange={(e) => setUserFormData({ ...userFormData, full_name: e.target.value })}
                  style={{ width: "100%" }}
                  placeholder="John Doe"
                />
              </div>
              <div>
                <label style={{ fontSize: "12px", fontWeight: "600", display: "block", marginBottom: "4px" }}>Role *</label>
                <select
                  className="input"
                  value={userFormData.role}
                  onChange={(e) => setUserFormData({ ...userFormData, role: e.target.value })}
                  style={{ width: "100%" }}
                >
                  <option value="ADMIN">ADMIN (Full Access)</option>
                  <option value="USER">USER (AI Workspace & Viewer)</option>
                  <option value="INVOICE_REVIEWER">INVOICE_REVIEWER (Review & Correct)</option>
                  <option value="INVOICE_APPROVER">INVOICE_APPROVER (Approve & ERP Submit)</option>
                </select>
              </div>
              <div style={{ display: "flex", justifyContent: "flex-end", gap: "10px", marginTop: "12px" }}>
                <button type="button" className="btn btn-secondary" onClick={() => setIsAddUserModalOpen(false)}>Cancel</button>
                <button type="submit" className="btn btn-primary">Create User</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ============================================================= */}
      {/* MODAL: EDIT USER                                              */}
      {/* ============================================================= */}
      {isEditUserModalOpen && (
        <div style={{ position: "fixed", top: 0, left: 0, width: "100vw", height: "100vh", backgroundColor: "rgba(0,0,0,0.5)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000 }}>
          <div className="card animate-scale-up" style={{ width: "480px", padding: "24px" }}>
            <h3 style={{ fontSize: "16px", fontWeight: "700", marginBottom: "16px" }}>Edit User: {userFormData.username}</h3>
            <form onSubmit={handleUpdateUser} style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
              <div>
                <label style={{ fontSize: "12px", fontWeight: "600", display: "block", marginBottom: "4px" }}>Email</label>
                <input
                  type="email"
                  className="input"
                  value={userFormData.email}
                  onChange={(e) => setUserFormData({ ...userFormData, email: e.target.value })}
                  style={{ width: "100%" }}
                />
              </div>
              <div>
                <label style={{ fontSize: "12px", fontWeight: "600", display: "block", marginBottom: "4px" }}>Full Name</label>
                <input
                  type="text"
                  className="input"
                  value={userFormData.full_name}
                  onChange={(e) => setUserFormData({ ...userFormData, full_name: e.target.value })}
                  style={{ width: "100%" }}
                />
              </div>
              <div>
                <label style={{ fontSize: "12px", fontWeight: "600", display: "block", marginBottom: "4px" }}>Role</label>
                <select
                  className="input"
                  value={userFormData.role}
                  onChange={(e) => setUserFormData({ ...userFormData, role: e.target.value })}
                  style={{ width: "100%" }}
                >
                  <option value="ADMIN">ADMIN</option>
                  <option value="USER">USER</option>
                  <option value="INVOICE_REVIEWER">INVOICE_REVIEWER</option>
                  <option value="INVOICE_APPROVER">INVOICE_APPROVER</option>
                </select>
              </div>
              <div>
                <label style={{ fontSize: "12px", fontWeight: "600", display: "block", marginBottom: "4px" }}>Status</label>
                <select
                  className="input"
                  value={userFormData.status}
                  onChange={(e) => setUserFormData({ ...userFormData, status: e.target.value })}
                  style={{ width: "100%" }}
                >
                  <option value="ACTIVE">ACTIVE</option>
                  <option value="DISABLED">DISABLED</option>
                </select>
              </div>
              <div style={{ display: "flex", justifyContent: "flex-end", gap: "10px", marginTop: "12px" }}>
                <button type="button" className="btn btn-secondary" onClick={() => setIsEditUserModalOpen(false)}>Cancel</button>
                <button type="submit" className="btn btn-primary">Save Changes</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ============================================================= */}
      {/* MODAL: ADD FUSION CONNECTION                                 */}
      {/* ============================================================= */}
      {isAddConnModalOpen && (
        <div style={{ position: "fixed", top: 0, left: 0, width: "100vw", height: "100vh", backgroundColor: "rgba(0,0,0,0.5)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000 }}>
          <div className="card animate-scale-up" style={{ width: "540px", padding: "24px" }}>
            <h3 style={{ fontSize: "16px", fontWeight: "700", marginBottom: "8px", display: "flex", alignItems: "center", gap: "8px" }}>
              <Database size={18} style={{ color: "var(--color-primary)" }} /> Add Oracle Fusion Connection
            </h3>
            <p style={{ fontSize: "12px", color: "var(--text-secondary)", marginBottom: "16px" }}>
              Explicitly configure an Oracle Fusion Payables ERP endpoint. The connection will be created in NOT_TESTED status.
            </p>
            <form onSubmit={handleCreateConnection} style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
              <div>
                <label style={{ fontSize: "12px", fontWeight: "600", display: "block", marginBottom: "4px" }}>Connection Name *</label>
                <input
                  type="text"
                  required
                  className="input"
                  value={connFormData.connection_name}
                  onChange={(e) => setConnFormData({ ...connFormData, connection_name: e.target.value })}
                  style={{ width: "100%" }}
                  placeholder="e.g. Oracle Fusion Payables (TEST)"
                />
              </div>
              <div>
                <label style={{ fontSize: "12px", fontWeight: "600", display: "block", marginBottom: "4px" }}>Fusion Base URL *</label>
                <input
                  type="url"
                  required
                  className="input"
                  value={connFormData.base_url}
                  onChange={(e) => setConnFormData({ ...connFormData, base_url: e.target.value })}
                  style={{ width: "100%", fontFamily: "var(--font-mono)" }}
                  placeholder="https://fa-your-instance.oraclecloud.com"
                />
              </div>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px" }}>
                <div>
                  <label style={{ fontSize: "12px", fontWeight: "600", display: "block", marginBottom: "4px" }}>Environment *</label>
                  <select
                    className="input"
                    value={connFormData.environment}
                    onChange={(e) => setConnFormData({ ...connFormData, environment: e.target.value })}
                    style={{ width: "100%" }}
                  >
                    <option value="TEST">TEST</option>
                    <option value="UAT">UAT</option>
                    <option value="DEV">DEV</option>
                    <option value="PROD">PROD</option>
                  </select>
                </div>
                <div>
                  <label style={{ fontSize: "12px", fontWeight: "600", display: "block", marginBottom: "4px" }}>Authentication Type</label>
                  <select
                    className="input"
                    value={connFormData.authentication_type}
                    onChange={(e) => setConnFormData({ ...connFormData, authentication_type: e.target.value })}
                    style={{ width: "100%" }}
                  >
                    <option value="BASIC">Basic Auth</option>
                    <option value="OAUTH2">OAuth 2.0</option>
                    <option value="BEARER_TOKEN">Bearer Token</option>
                  </select>
                </div>
              </div>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px" }}>
                <div>
                  <label style={{ fontSize: "12px", fontWeight: "600", display: "block", marginBottom: "4px" }}>Username</label>
                  <input
                    type="text"
                    className="input"
                    value={connFormData.username}
                    onChange={(e) => setConnFormData({ ...connFormData, username: e.target.value })}
                    style={{ width: "100%" }}
                    placeholder="FIN_AP_USER"
                  />
                </div>
                <div>
                  <label style={{ fontSize: "12px", fontWeight: "600", display: "block", marginBottom: "4px" }}>Password / Secret</label>
                  <input
                    type="password"
                    className="input"
                    value={connFormData.password_secret}
                    onChange={(e) => setConnFormData({ ...connFormData, password_secret: e.target.value })}
                    style={{ width: "100%" }}
                    placeholder="••••••••••••"
                  />
                </div>
              </div>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px" }}>
                <div>
                  <label style={{ fontSize: "12px", fontWeight: "600", display: "block", marginBottom: "4px" }}>Business Unit</label>
                  <input
                    type="text"
                    className="input"
                    value={connFormData.business_unit}
                    onChange={(e) => setConnFormData({ ...connFormData, business_unit: e.target.value })}
                    style={{ width: "100%" }}
                    placeholder="US1 Business Unit"
                  />
                </div>
                <div>
                  <label style={{ fontSize: "12px", fontWeight: "600", display: "block", marginBottom: "4px" }}>Default Currency</label>
                  <input
                    type="text"
                    className="input"
                    value={connFormData.default_currency}
                    onChange={(e) => setConnFormData({ ...connFormData, default_currency: e.target.value })}
                    style={{ width: "100%" }}
                    placeholder="USD"
                  />
                </div>
              </div>
              <div style={{ display: "flex", justifyContent: "flex-end", gap: "10px", marginTop: "14px" }}>
                <button type="button" className="btn btn-secondary" onClick={() => setIsAddConnModalOpen(false)}>Cancel</button>
                <button type="submit" className="btn btn-primary">Save Connection</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ============================================================= */}
      {/* MODAL: EDIT FUSION CONNECTION                                */}
      {/* ============================================================= */}
      {isEditConnModalOpen && (
        <div style={{ position: "fixed", top: 0, left: 0, width: "100vw", height: "100vh", backgroundColor: "rgba(0,0,0,0.5)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000 }}>
          <div className="card animate-scale-up" style={{ width: "540px", padding: "24px" }}>
            <h3 style={{ fontSize: "16px", fontWeight: "700", marginBottom: "8px" }}>Edit Connection: {connFormData.connection_name}</h3>
            <p style={{ fontSize: "12px", color: "var(--text-secondary)", marginBottom: "16px" }}>
              Updating URL or credentials will reset the status to NOT_TESTED until verified.
            </p>
            <form onSubmit={handleUpdateConnection} style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
              <div>
                <label style={{ fontSize: "12px", fontWeight: "600", display: "block", marginBottom: "4px" }}>Connection Name</label>
                <input
                  type="text"
                  required
                  className="input"
                  value={connFormData.connection_name}
                  onChange={(e) => setConnFormData({ ...connFormData, connection_name: e.target.value })}
                  style={{ width: "100%" }}
                />
              </div>
              <div>
                <label style={{ fontSize: "12px", fontWeight: "600", display: "block", marginBottom: "4px" }}>Fusion Base URL</label>
                <input
                  type="url"
                  required
                  className="input"
                  value={connFormData.base_url}
                  onChange={(e) => setConnFormData({ ...connFormData, base_url: e.target.value })}
                  style={{ width: "100%", fontFamily: "var(--font-mono)" }}
                />
              </div>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px" }}>
                <div>
                  <label style={{ fontSize: "12px", fontWeight: "600", display: "block", marginBottom: "4px" }}>Environment</label>
                  <select
                    className="input"
                    value={connFormData.environment}
                    onChange={(e) => setConnFormData({ ...connFormData, environment: e.target.value })}
                    style={{ width: "100%" }}
                  >
                    <option value="TEST">TEST</option>
                    <option value="UAT">UAT</option>
                    <option value="DEV">DEV</option>
                    <option value="PROD">PROD</option>
                  </select>
                </div>
                <div>
                  <label style={{ fontSize: "12px", fontWeight: "600", display: "block", marginBottom: "4px" }}>Business Unit</label>
                  <input
                    type="text"
                    className="input"
                    value={connFormData.business_unit}
                    onChange={(e) => setConnFormData({ ...connFormData, business_unit: e.target.value })}
                    style={{ width: "100%" }}
                  />
                </div>
              </div>
              <div>
                <label style={{ fontSize: "12px", fontWeight: "600", display: "block", marginBottom: "4px" }}>New Password / Secret (Leave blank to keep current)</label>
                <input
                  type="password"
                  className="input"
                  value={connFormData.password_secret}
                  onChange={(e) => setConnFormData({ ...connFormData, password_secret: e.target.value })}
                  style={{ width: "100%" }}
                  placeholder="••••••••••••"
                />
              </div>
              <div style={{ display: "flex", justifyContent: "flex-end", gap: "10px", marginTop: "14px" }}>
                <button type="button" className="btn btn-secondary" onClick={() => setIsEditConnModalOpen(false)}>Cancel</button>
                <button type="submit" className="btn btn-primary">Save Changes</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
