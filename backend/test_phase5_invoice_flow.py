import json
from fastapi.testclient import TestClient
from main import app
from services.invoice_db_service import (
    save_invoice,
    get_review_queue,
    get_invoice_for_review,
    update_invoice_review,
    approve_invoice,
    reject_invoice,
)
from services.oracle_fusion_service import (
    get_fusion_connections,
    get_fusion_invoice_metadata,
    get_invoice_field_mapping,
    generate_fusion_payload,
    submit_invoice_to_fusion,
)

client = TestClient(app)

print("=" * 70)
print("PHASE 5: ORACLE DB + HUMAN REVIEW + APPROVAL + FUSION TEST SUITE")
print("=" * 70)

# Mock OCI normalized invoice output
mock_oci_output = {
    "status": "success",
    "document_name": "Test_Invoice_Phase5.pdf",
    "processor_type": "INVOICE",
    "job_id": "ocid1.aidocumentprocessorjob.oc1.ap-hyderabad-1.testjob12345",
    "invoice": {
        "vendor_name": "AADIFIDELIS SOLUTIONS PRIVATE LIMITED",
        "invoice_number": "1025/BL/DL/0889",
        "invoice_date": "2025-11-13",
        "due_date": "2025-11-13",
        "po_number": None,
        "currency": "USD",
        "subtotal": 37908720.0,
        "tax_amount": 1271307.1,
        "total_amount": 1500142.0,
        "payment_terms": "Net 30",
    },
    "field_mapping": [
        {
            "application_field": "vendor_name",
            "display_name": "Vendor Name",
            "oci_field": "VendorName",
            "value": "AADIFIDELIS SOLUTIONS PRIVATE LIMITED",
            "confidence": 0.9935568,
        },
        {
            "application_field": "invoice_number",
            "display_name": "Invoice Number",
            "oci_field": "InvoiceId",
            "value": "1025/BL/DL/0889",
            "confidence": 0.82151884,
        },
        {
            "application_field": "total_amount",
            "display_name": "Total Amount",
            "oci_field": "InvoiceTotal",
            "value": 1500142.0,
            "confidence": 0.889,
        },
    ],
    "line_items": [
        {
            "line_number": 1,
            "description": "Referral : Payouts for Business Loan the Month of Oct, 2025",
            "item_number": "997159",
            "quantity": 1,
            "unit_price": 1271307.14,
            "tax_amount": 228834.86,
            "line_amount": 1500142.0,
        }
    ],
    "raw_result": {"pages": []},
}

# -------------------------------------------------------------
# TEST 1: Oracle DB Persistence
# -------------------------------------------------------------
print("\n[TEST 1] Testing Oracle DB Persistence (save_invoice)...")
invoice_id = save_invoice(mock_oci_output, "Test_Invoice_Phase5.pdf")
assert invoice_id is not None and invoice_id > 0, "Failed to save invoice to Oracle DB"
print(f"  [PASS] Invoice saved to Oracle DB with INVOICE_ID = {invoice_id}")

# -------------------------------------------------------------
# TEST 2: Review Queue API
# -------------------------------------------------------------
print("\n[TEST 2] Testing Review Queue API (GET /api/invoices/review-queue)...")
res = client.get("/api/invoices/review-queue")
assert res.status_code == 200
queue = res.json()
assert len(queue) > 0, "Review queue should not be empty"
found = next((inv for inv in queue if inv["invoice_id"] == invoice_id), None)
assert found is not None, f"Invoice #{invoice_id} not found in review queue"
assert found["status"] == "REVIEW_REQUIRED", f"Expected REVIEW_REQUIRED, got {found['status']}"
print(f"  [PASS] Invoice #{invoice_id} retrieved from Review Queue (Status: {found['status']}, Vendor: {found['vendor_name']})")

# -------------------------------------------------------------
# TEST 3: Invoice Detailed Review & Original Snapshot
# -------------------------------------------------------------
print("\n[TEST 3] Testing Invoice Review Workspace API (GET /api/invoices/{id}/review)...")
res = client.get(f"/api/invoices/{invoice_id}/review")
assert res.status_code == 200
review_data = res.json()
assert review_data["invoice_id"] == invoice_id
assert review_data["vendor_name"] == "AADIFIDELIS SOLUTIONS PRIVATE LIMITED"
assert len(review_data["line_items"]) == 1
assert "original_snapshot" in review_data
assert review_data["original_snapshot"]["invoice"]["invoice_number"] == "1025/BL/DL/0889"
print(f"  [PASS] Full review payload retrieved (Original OCI Snapshot preserved with {len(review_data['line_items'])} line items)")

# -------------------------------------------------------------
# TEST 4: Human Corrections (Edit & Save)
# -------------------------------------------------------------
print("\n[TEST 4] Testing Human Corrections (PUT /api/invoices/{id}/review)...")
corrections_payload = {
    "header_fields": {
        "vendor_name": "AADIFIDELIS SOLUTIONS PVT LTD (VERIFIED)",
        "invoice_number": "1025/BL/DL/0890-CORRECTED",
        "invoice_date": "2025-11-13",
        "due_date": "2025-12-13",
        "po_number": "PO-2026-9901",
        "currency": "USD",
        "subtotal": 37908720.0,
        "tax_amount": 1271307.1,
        "total_amount": 1500142.0,
        "payment_terms": "Net 30",
    },
    "line_items": [
        {
            "line_number": 1,
            "description": "Referral : Business Loan Payouts Oct 2025 (Corrected)",
            "item_number": "997159",
            "quantity": 1,
            "unit_price": 1271307.14,
            "tax_amount": 228834.86,
            "line_amount": 1500142.0,
        }
    ],
    "reviewer": "Senior AP Reviewer",
    "comments": "Corrected vendor suffix and invoice number typo.",
}
res = client.put(f"/api/invoices/{invoice_id}/review", json=corrections_payload)
assert res.status_code == 200

# Verify corrections were applied while original OCI snapshot remains untouched
res_updated = client.get(f"/api/invoices/{invoice_id}/review")
updated_data = res_updated.json()
assert updated_data["vendor_name"] == "AADIFIDELIS SOLUTIONS PVT LTD (VERIFIED)"
assert updated_data["invoice_number"] == "1025/BL/DL/0890-CORRECTED"
assert updated_data["reviewed_by"] == "Senior AP Reviewer"
assert updated_data["original_snapshot"]["invoice"]["invoice_number"] == "1025/BL/DL/0889"
print("  [PASS] Human corrections saved; Original OCI extracted value permanently preserved for audit")

# -------------------------------------------------------------
# TEST 5: Human Approval
# -------------------------------------------------------------
print("\n[TEST 5] Testing Human Approval (POST /api/invoices/{id}/approve)...")
res = client.post(
    f"/api/invoices/{invoice_id}/approve",
    json={"reviewer": "AP Manager", "comments": "Approved for Oracle Fusion ERP processing."},
)
assert res.status_code == 200
assert res.json()["status"] == "APPROVED"

res_after_appr = client.get(f"/api/invoices/{invoice_id}/review")
assert res_after_appr.json()["status"] == "APPROVED"
print(f"  [PASS] Invoice #{invoice_id} successfully transitioned to APPROVED status")

# -------------------------------------------------------------
# TEST 6: Oracle Fusion Connections & Metadata Discovery
# -------------------------------------------------------------
print("\n[TEST 6] Testing Oracle Fusion Connections & Metadata APIs...")
res_conns = client.get("/api/fusion/connections", headers={"X-User-Id": "admin"})
assert res_conns.status_code == 200
conns = res_conns.json()
assert len(conns) > 0
active_conn = conns[0]
conn_id = active_conn["connection_id"]
print(f"  [PASS] Fusion Connections: Found {len(conns)} connections. Active Connection ID = {conn_id}")

res_meta = client.get(f"/api/fusion/connections/{conn_id}/metadata", headers={"X-User-Id": "admin"})
assert res_meta.status_code == 200
meta = res_meta.json()
assert len(meta["sections"]) == 2  # HEADER and LINES
header_sec = next(s for s in meta["sections"] if s["name"] == "HEADER")
lines_sec = next(s for s in meta["sections"] if s["name"] == "LINES")
assert any(f["name"] == "Supplier" and f["required"] for f in header_sec["fields"])
assert any(f["name"] == "InvoiceNumber" and f["required"] for f in header_sec["fields"])
print(f"  [PASS] Fusion Metadata Discovered: {len(header_sec['fields'])} Header Fields, {len(lines_sec['fields'])} Line Fields")

# -------------------------------------------------------------
# TEST 7: Oracle Fusion Field Mapping & Validation
# -------------------------------------------------------------
print("\n[TEST 7] Testing Fusion Field Mapping (GET /api/invoices/{id}/fusion-mapping)...")
res_map = client.get(f"/api/invoices/{invoice_id}/fusion-mapping?connection_id={conn_id}", headers={"X-User-Id": "admin"})
assert res_map.status_code == 200
map_data = res_map.json()
assert len(map_data["header_mappings"]) > 0
assert len(map_data["line_mappings"]) > 0
assert map_data["validation"]["is_valid"] is True
print(f"  [PASS] Visual Field Mapping: {len(map_data['header_mappings'])} Header mappings, {len(map_data['line_mappings'])} Line mappings (Validation: VALID)")

# -------------------------------------------------------------
# TEST 8: Oracle Fusion Payload Preview
# -------------------------------------------------------------
print("\n[TEST 8] Testing Fusion Payload Preview (GET /api/invoices/{id}/fusion-preview)...")
res_prev = client.get(f"/api/invoices/{invoice_id}/fusion-preview?connection_id={conn_id}", headers={"X-User-Id": "admin"})
assert res_prev.status_code == 200
payload = res_prev.json()
assert payload["Supplier"] == "AADIFIDELIS SOLUTIONS PVT LTD (VERIFIED)"
assert payload["InvoiceNumber"] == "1025/BL/DL/0890-CORRECTED"
assert payload["InvoiceAmount"] == 1500142.0
assert len(payload["invoiceLines"]) == 1
assert payload["invoiceLines"][0]["LineNumber"] == 1
print(f"  [PASS] Generated Oracle Fusion REST Payload (Supplier='{payload['Supplier']}', Lines={len(payload['invoiceLines'])})")

# -------------------------------------------------------------
# TEST 9: Oracle Fusion Submission & Idempotency
# -------------------------------------------------------------
print("\n[TEST 9] Testing Fusion Submission & Idempotency (POST /api/invoices/{id}/fusion-submit)...")
res_sub = client.post(
    f"/api/invoices/{invoice_id}/fusion-submit",
    headers={"X-User-Id": "admin"},
    json={"connection_id": conn_id, "force": False},
)
assert res_sub.status_code == 200
sub_result = res_sub.json()
assert sub_result["status"] == "FUSION_CREATED"
assert "fusion_invoice_id" in sub_result
fusion_inv_id = sub_result["fusion_invoice_id"]
print(f"  [PASS] Successfully submitted to Oracle Fusion. Assigned Fusion Invoice ID: {fusion_inv_id}")

# Test idempotency (duplicate submission prevention)
res_sub_dup = client.post(
    f"/api/invoices/{invoice_id}/fusion-submit",
    headers={"X-User-Id": "admin"},
    json={"connection_id": conn_id, "force": False},
)
assert res_sub_dup.status_code == 200
assert res_sub_dup.json().get("already_submitted") is True
print(f"  [PASS] Idempotency check verified: Prevented duplicate submission for Invoice #{invoice_id}")

# -------------------------------------------------------------
# TEST 10: Rejection Flow
# -------------------------------------------------------------
print("\n[TEST 10] Testing Rejection Flow on another invoice...")
import time
mock_oci_output_2 = dict(mock_oci_output)
mock_oci_output_2["invoice"] = dict(mock_oci_output["invoice"])
mock_oci_output_2["invoice"]["invoice_number"] = f"INV-TO-REJECT-{int(time.time())}"
inv_2_id = save_invoice(mock_oci_output_2, "Invoice_To_Reject.pdf")

res_rej = client.post(
    f"/api/invoices/{inv_2_id}/reject",
    headers={"X-User-Id": "admin"},
    json={"reviewer": "AP Specialist", "comments": "Vendor VAT number does not match tax filing."},
)
assert res_rej.status_code == 200
assert res_rej.json()["status"] == "REJECTED"

# Verify rejected invoice CANNOT be submitted to Fusion
res_rej_fusion = client.post(
    f"/api/invoices/{inv_2_id}/fusion-submit",
    headers={"X-User-Id": "admin"},
    json={"connection_id": conn_id, "force": False},
)
assert res_rej_fusion.status_code == 400
print(f"  [PASS] Rejection flow verified and rejected invoice safely blocked from Fusion submission")

print("\n" + "=" * 70)
print(">>> ALL 10 PHASE 5 TESTS COMPLETED WITH 100% SUCCESS! <<<")
print("=" * 70)
