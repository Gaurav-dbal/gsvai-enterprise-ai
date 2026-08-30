import io
from fastapi.testclient import TestClient
from main import app
from services.invoice_state_service import invoice_state_manager

client = TestClient(app)

print("=" * 60)
print("TESTING INVOICE AUTOMATION API ENDPOINTS")
print("=" * 60)

# 1. Health check
res = client.get("/health")
assert res.status_code == 200, f"Health check failed: {res.status_code}"
print("[PASS] GET /health (HTTP 200)")

# 2. Reject non-PDF
dummy_txt = io.BytesIO(b"Hello world")
res = client.post("/api/invoices/upload", files={"file": ("invoice.txt", dummy_txt, "text/plain")})
assert res.status_code == 400, f"Expected 400 for non-PDF, got {res.status_code}"
print("[PASS] POST /api/invoices/upload rejects non-PDF (HTTP 400)")

# 3. Reject missing file
res = client.post("/api/invoices/upload")
assert res.status_code == 422, f"Expected 422 for missing file, got {res.status_code}"
print("[PASS] POST /api/invoices/upload rejects missing file (HTTP 422)")

# 4. Status 404 for unknown processing ID
res = client.get("/api/invoices/invalid-uuid-12345/status")
assert res.status_code == 404, f"Expected 404 for unknown ID, got {res.status_code}"
print("[PASS] GET /api/invoices/{id}/status returns 404 for unknown ID")

# 5. Test State Manager Lifecycle
task_id = "test-task-123"
invoice_state_manager.create_task(task_id, "invoice_test.pdf", 102400)
status_res = client.get(f"/api/invoices/{task_id}/status")
assert status_res.status_code == 200
status_json = status_res.json()
assert status_json["status"] == "UPLOADED"
assert status_json["stage"] == "UPLOADING"
assert status_json["progress"] == 10
print("[PASS] GET /api/invoices/{id}/status returns active state (UPLOADED, 10%)")

# 6. Update to PROCESSING stage
invoice_state_manager.update_task(
    task_id,
    stage="OCI_DOCUMENT_UNDERSTANDING",
    status="PROCESSING",
    progress=55,
    message="OCI is analyzing your invoice...",
)
status_res = client.get(f"/api/invoices/{task_id}/status")
assert status_res.status_code == 200
status_json = status_res.json()
assert status_json["status"] == "PROCESSING"
assert status_json["progress"] == 55
assert status_json["stage"] == "OCI_DOCUMENT_UNDERSTANDING"
print("[PASS] Real-time status update verified (PROCESSING, 55%, stage=OCI_DOCUMENT_UNDERSTANDING)")

# 7. Complete task and test result endpoint
mock_result = {
    "processing_id": task_id,
    "status": "COMPLETED",
    "document_name": "invoice_test.pdf",
    "processor_type": "INVOICE",
    "invoice": {
        "vendor_name": "AADIFIDELIS SOLUTIONS PRIVATE LIMITED",
        "invoice_number": "1025/BL/DL/0889",
        "invoice_date": "2025-11-13",
        "due_date": "2025-11-13",
        "po_number": None,
        "currency": None,
        "subtotal": 37908720,
        "tax_amount": 1271307.1,
        "total_amount": 1500142,
        "payment_terms": None,
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
    ],
    "line_items": [
        {
            "line_number": 1,
            "description": "Referral : Payouts for Business Loan the Month of Oct, 2025",
            "item_number": "997159",
            "quantity": 0,
            "unit_price": 1271307.14,
            "tax_amount": None,
            "line_amount": 1500142,
        }
    ],
}
invoice_state_manager.update_task(task_id, result=mock_result)

res_result = client.get(f"/api/invoices/{task_id}/result")
assert res_result.status_code == 200
result_json = res_result.json()
assert result_json["status"] == "COMPLETED"
assert result_json["invoice"]["vendor_name"] == "AADIFIDELIS SOLUTIONS PRIVATE LIMITED"
assert result_json["invoice"]["invoice_number"] == "1025/BL/DL/0889"
assert len(result_json["line_items"]) == 1
assert result_json["line_items"][0]["line_amount"] == 1500142
print("[PASS] GET /api/invoices/{id}/result returns normalized invoice and line items (HTTP 200)")

print("\n" + "=" * 60)
print("ALL INVOICE API TESTS PASSED SUCCESSFULLY!")
print("=" * 60)
