import json
from fastapi.testclient import TestClient
from main import app
from services.invoice_db_service import save_invoice, approve_invoice

client = TestClient(app)

print("=" * 70)
print("ADMIN SETTINGS + RBAC + ORACLE FUSION CONNECTION MANAGEMENT TEST SUITE")
print("=" * 70)

ADMIN_HEADERS = {"X-User-Id": "admin"}
USER_HEADERS = {"X-User-Id": "user1"}

# -------------------------------------------------------------
# TEST 1: Current User & RBAC Permissions Check
# -------------------------------------------------------------
print("\n[TEST 1] Testing /api/auth/me Profile & Permission Check...")
res_admin_me = client.get("/api/auth/me", headers=ADMIN_HEADERS)
assert res_admin_me.status_code == 200
admin_prof = res_admin_me.json()
assert admin_prof["role"] == "ADMIN"
assert "FUSION_CONNECTION_CREATE" in admin_prof["permissions"]
print(f"  [PASS] Admin profile resolved: Role={admin_prof['role']}, Permissions={len(admin_prof['permissions'])}")

res_user_me = client.get("/api/auth/me", headers=USER_HEADERS)
assert res_user_me.status_code == 200
user_prof = res_user_me.json()
assert user_prof["role"] == "USER"
assert "FUSION_CONNECTION_CREATE" not in user_prof["permissions"]
print(f"  [PASS] User profile resolved: Role={user_prof['role']}, Permissions={len(user_prof['permissions'])}")

# -------------------------------------------------------------
# TEST 2: RBAC Security Enforcement (User Denied Admin Access)
# -------------------------------------------------------------
print("\n[TEST 2] Testing RBAC Security Enforcement (403 Forbidden for Non-Admin)...")
res_denied = client.post(
    "/api/admin/users",
    headers=USER_HEADERS,
    json={"username": "hacker", "email": "hacker@test.com", "role": "ADMIN"},
)
assert res_denied.status_code == 403, f"Expected 403 Forbidden, got {res_denied.status_code}"
print("  [PASS] Standard user safely blocked (HTTP 403) from creating users")

# -------------------------------------------------------------
# TEST 3: User Management API (Admin Access)
# -------------------------------------------------------------
print("\n[TEST 3] Testing User Management API (Admin Access)...")
res_users = client.get("/api/admin/users", headers=ADMIN_HEADERS)
assert res_users.status_code == 200
users_list = res_users.json()
assert len(users_list) >= 4
print(f"  [PASS] Retrieved {len(users_list)} users from Oracle DB")

import time
test_uname = f"ap_spec_{int(time.time())}"
res_create_user = client.post(
    "/api/admin/users",
    headers=ADMIN_HEADERS,
    json={
        "username": test_uname,
        "email": f"{test_uname}@enterprise.ai",
        "full_name": "Test AP Specialist",
        "role": "INVOICE_REVIEWER",
        "status": "ACTIVE",
    },
)
assert res_create_user.status_code == 200
print(f"  [PASS] Admin successfully created new user '{test_uname}'")

# -------------------------------------------------------------
# TEST 4: Roles & Permissions API
# -------------------------------------------------------------
print("\n[TEST 4] Testing Roles & Permissions API...")
res_roles = client.get("/api/admin/roles", headers=ADMIN_HEADERS)
assert res_roles.status_code == 200
roles = res_roles.json()
assert any(r["role_name"] == "ADMIN" for r in roles)
assert any(r["role_name"] == "USER" for r in roles)
print(f"  [PASS] Retrieved {len(roles)} roles with permission matrices")

# -------------------------------------------------------------
# TEST 5: Fusion Connection Creation (Status = NOT_TESTED)
# -------------------------------------------------------------
print("\n[TEST 5] Testing Oracle Fusion Connection Creation...")
conn_name = f"Oracle Cloud ERP - Test Finance {int(time.time())}"
conn_payload = {
    "connection_name": conn_name,
    "base_url": "https://fusion-test.enterprise.internal.oraclecloud.com",
    "environment": "TEST",
    "authentication_type": "BASIC",
    "username": "FIN_AP_TEST_USER",
    "password_secret": "SuperSecretPass123!",
    "business_unit": "US1 Business Unit",
    "default_currency": "USD",
}
res_conn_create = client.post(
    "/api/fusion/connections",
    headers=ADMIN_HEADERS,
    json=conn_payload,
)
assert res_conn_create.status_code == 200
conn_res = res_conn_create.json()
conn_id = conn_res["connection_id"]
assert conn_res["connection_status"] == "NOT_TESTED"
print(f"  [PASS] Fusion Connection created with ID = {conn_id}, Status = NOT_TESTED (No passwords exposed)")

# Verify connection in list
res_conn_list = client.get("/api/fusion/connections", headers=ADMIN_HEADERS)
assert res_conn_list.status_code == 200
conns = res_conn_list.json()
created_c = next((c for c in conns if c["connection_id"] == conn_id), None)
assert created_c is not None
assert created_c["status"] == "NOT_TESTED"
assert "password_secret" not in created_c
print("  [PASS] Connection listed in Oracle Fusion Connections table without secrets")

# -------------------------------------------------------------
# TEST 6: Test Connection (Safe Read-Only Verification)
# -------------------------------------------------------------
print("\n[TEST 6] Testing Connection Execution (POST /api/fusion/connections/{id}/test)...")
res_test = client.post(f"/api/fusion/connections/{conn_id}/test", headers=ADMIN_HEADERS)
assert res_test.status_code == 200
test_data = res_test.json()
assert test_data["status"] == "CONNECTED"
print(f"  [PASS] Connection tested: Status transitioned to CONNECTED ({test_data['message']})")

# -------------------------------------------------------------
# TEST 7: Connection-Specific Metadata & Field Mapping
# -------------------------------------------------------------
print("\n[TEST 7] Testing Connection-Specific Metadata & Mapping...")
res_meta = client.get(f"/api/fusion/connections/{conn_id}/metadata", headers=ADMIN_HEADERS)
assert res_meta.status_code == 200
meta = res_meta.json()
assert meta["connection_id"] == conn_id
assert meta["connection_name"] == conn_name
print(f"  [PASS] Connection-specific metadata retrieved for Connection #{conn_id}")

# -------------------------------------------------------------
# TEST 8: Invoice Submission using Selected Connection ID
# -------------------------------------------------------------
print("\n[TEST 8] Testing Invoice Submission to Selected Fusion Connection...")
# Save & Approve an invoice
mock_inv = {
    "invoice": {
        "vendor_name": "ACME INDUSTRIAL SUPPLIES",
        "invoice_number": f"INV-CONN-TEST-{int(time.time())}",
        "invoice_date": "2026-08-30",
        "total_amount": 7500.00,
        "currency": "USD",
    },
    "line_items": [
        {"line_number": 1, "description": "Cloud Servers Batch A", "quantity": 5, "unit_price": 1500.0, "line_amount": 7500.0}
    ],
    "raw_result": {},
}
inv_id = save_invoice(mock_inv, "Acme_Invoice.pdf")
approve_invoice(inv_id, reviewer="AP Controller", comments="Approved for Test Finance Connection")

# Generate Preview for this connection
res_prev = client.get(f"/api/invoices/{inv_id}/fusion-preview?connection_id={conn_id}", headers=ADMIN_HEADERS)
assert res_prev.status_code == 200
payload = res_prev.json()
assert payload["Supplier"] == "ACME INDUSTRIAL SUPPLIES"
print(f"  [PASS] Payload Preview generated specifically for Connection #{conn_id}")

# Submit to Connection
res_sub = client.post(
    f"/api/invoices/{inv_id}/fusion-submit",
    headers=ADMIN_HEADERS,
    json={"connection_id": conn_id, "force": False},
)
assert res_sub.status_code == 200
sub_receipt = res_sub.json()
assert sub_receipt["status"] == "FUSION_CREATED"
assert sub_receipt["connection_id"] == conn_id
assert "fusion_invoice_id" in sub_receipt
print(f"  [PASS] Invoice submitted to Connection #{conn_id}. Assigned Fusion ID: {sub_receipt['fusion_invoice_id']}")

# -------------------------------------------------------------
# TEST 9: Fusion Submission History & Audit Logs
# -------------------------------------------------------------
print("\n[TEST 9] Testing Fusion Submission History & Audit Event Logging...")
res_sub_hist = client.get("/api/fusion/submissions", headers=ADMIN_HEADERS)
assert res_sub_hist.status_code == 200
sub_list = res_sub_hist.json()
assert len(sub_list) > 0
found_sub = next((s for s in sub_list if s["invoice_id"] == inv_id), None)
assert found_sub is not None
assert found_sub["connection_name"] == conn_name
print(f"  [PASS] Fusion Submission History recorded: Invoice #{inv_id} on {found_sub['connection_name']}")

res_audit = client.get("/api/admin/audit-logs", headers=ADMIN_HEADERS)
assert res_audit.status_code == 200
audit_events = res_audit.json()
assert len(audit_events) > 0
print(f"  [PASS] Audit logs verified ({len(audit_events)} audit events recorded in Oracle DB)")

print("\n" + "=" * 70)
print(">>> ALL 9 ADMIN SETTINGS, RBAC & FUSION CONNECTION TESTS PASSED! <<<")
print("=" * 70)
