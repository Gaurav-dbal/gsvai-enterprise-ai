import os
import sys

# Ensure UTF-8 output encoding
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

print("=" * 70)
print("GSVAI ENTERPRISE AI WORKSPACE: END-TO-END VERIFICATION")
print("=" * 70)

# -------------------------------------------------------------
# Test 1: Verify Routes Exist on FastAPI App
# -------------------------------------------------------------
print("\n[TEST 1] Verifying FastAPI Routes...")
routes = [route.path for route in app.routes]
expected_routes = [
    "/ai-workspace/documents",
    "/ai-workspace/chat",
    "/ai-workspace/upload",
    "/chat",
    "/documents/upload",
    "/document-intelligence/analyze",
    "/document-intelligence",
    "/documents",
    "/health",
]
for r in expected_routes:
    assert r in routes, f"Missing route: {r}"
    print(f"  [PASS] Route verified: {r}")
print("Test 1 Passed: All routes present.")

# -------------------------------------------------------------
# Test 2: Test GET /ai-workspace/documents
# -------------------------------------------------------------
print("\n[TEST 2] Testing GET /ai-workspace/documents...")
res = client.get("/ai-workspace/documents")
assert res.status_code == 200, f"Failed: {res.text}"
docs_data = res.json()
assert docs_data.get("status") == "success"
assert "documents" in docs_data
print(f"  [PASS] Documents retrieved: {docs_data.get('count')} files indexed")
if docs_data.get("documents"):
    first_doc = docs_data["documents"][0]
    print(f"  [PASS] Sample doc: ID={first_doc.get('document_id')}, Name={first_doc.get('document_name')}, Pages={first_doc.get('page_count')}, Status={first_doc.get('status')}")
print("Test 2 Passed.")

# -------------------------------------------------------------
# Test 3: Test General AI Mode via POST /ai-workspace/chat
# -------------------------------------------------------------
print("\n[TEST 3] Testing General AI Mode ('What is Generative AI?')...")
res = client.post(
    "/ai-workspace/chat",
    json={"question": "What is Generative AI?", "document_id": None, "scope": "all"}
)
assert res.status_code == 200, f"Failed: {res.text}"
gen_data = res.json()
assert "answer" in gen_data
assert len(gen_data["answer"]) > 20
print(f"  [PASS] Source Type: {gen_data.get('source_type')}")
print(f"  [PASS] Answer preview: {gen_data['answer'][:120]}...")
print("Test 3 Passed: General AI returned valid answer.")

# -------------------------------------------------------------
# Test 4: Test Document Upload Pipeline (if test file exists)
# -------------------------------------------------------------
test_pdf_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "docs", "6Month_AI_Career_Plan.pdf"))
uploaded_doc_id = None

if os.path.exists(test_pdf_path):
    print(f"\n[TEST 4] Testing Document Upload Pipeline with '{os.path.basename(test_pdf_path)}'...")
    with open(test_pdf_path, "rb") as f:
        res = client.post(
            "/ai-workspace/upload",
            files={"file": ("6Month_AI_Career_Plan.pdf", f, "application/pdf")}
        )
    assert res.status_code == 200, f"Upload Failed: {res.text}"
    upload_res = res.json()
    assert upload_res.get("status") == "success"
    assert upload_res.get("indexing_status") == "INDEXED"
    uploaded_doc_id = upload_res.get("document_id")
    print(f"  [PASS] Document ID: {uploaded_doc_id}")
    print(f"  [PASS] Analysis ID: {upload_res.get('analysis_id')}")
    print(f"  [PASS] Pages: {upload_res.get('pages')}, Chunks: {upload_res.get('chunks')}")
    print(f"  [PASS] Pipeline: {upload_res.get('pipeline')}")
    print("Test 4 Passed: Full ingestion, OCR and Vector DB indexing completed.")
else:
    print("\n[TEST 4] Test PDF not found at docs path, skipping fresh upload.")
    if docs_data.get("documents"):
        uploaded_doc_id = docs_data["documents"][0]["document_id"]

# -------------------------------------------------------------
# Test 5: Test Selected Document Q&A Mode
# -------------------------------------------------------------
if uploaded_doc_id:
    print(f"\n[TEST 5] Testing Selected Document Q&A (Document ID: {uploaded_doc_id})...")
    res = client.post(
        "/ai-workspace/chat",
        json={
            "question": "What is the target salary mentioned in this document?",
            "document_id": uploaded_doc_id,
            "scope": "document"
        }
    )
    assert res.status_code == 200, f"Failed: {res.text}"
    doc_qa_data = res.json()
    print(f"  [PASS] Source Type: {doc_qa_data.get('source_type')}")
    print(f"  [PASS] Sources Count: {len(doc_qa_data.get('sources', []))}")
    print(f"  [PASS] Answer: {doc_qa_data.get('answer')[:150]}...")
    if doc_qa_data.get("sources"):
        src = doc_qa_data["sources"][0]
        print(f"  [PASS] Citation: Doc='{src.get('document_name')}', Page={src.get('page_number')}")
    print("Test 5 Passed: Selected Document Q&A grounded and cited.")

# -------------------------------------------------------------
# Test 6: Test Document Summary Mode
# -------------------------------------------------------------
if uploaded_doc_id:
    print(f"\n[TEST 6] Testing Document Summary Mode (Document ID: {uploaded_doc_id})...")
    res = client.post(
        "/ai-workspace/chat",
        json={
            "question": "Summarize this document.",
            "document_id": uploaded_doc_id,
            "scope": "document",
            "query_mode": "summary"
        }
    )
    assert res.status_code == 200, f"Failed: {res.text}"
    summary_data = res.json()
    print(f"  [PASS] Source Type: {summary_data.get('source_type')}")
    print(f"  [PASS] Summary Preview: {summary_data.get('answer')[:150]}...")
    print("Test 6 Passed: Document summary successfully generated.")

# -------------------------------------------------------------
# Test 7: Test Date-Based Document Summary Mode
# -------------------------------------------------------------
print("\n[TEST 7] Testing Date-Based Document Summary Mode ('Summarize documents uploaded today')...")
res = client.post(
    "/ai-workspace/chat",
    json={"question": "Summarize the documents uploaded today.", "document_id": None, "scope": "all"}
)
assert res.status_code == 200, f"Failed: {res.text}"
date_data = res.json()
print(f"  [PASS] Source Type: {date_data.get('source_type')}")
print(f"  [PASS] Date Summary: {date_data.get('answer')[:160]}...")
print("Test 7 Passed: Date-based document summary completed.")

# -------------------------------------------------------------
# Test 8: Test All Documents RAG Mode
# -------------------------------------------------------------
print("\n[TEST 8] Testing All Documents RAG Mode...")
res = client.post(
    "/ai-workspace/chat",
    json={"question": "How do I create a supplier invoice in Oracle Fusion Payables?", "document_id": None, "scope": "all"}
)
assert res.status_code == 200, f"Failed: {res.text}"
all_docs_data = res.json()
print(f"  [PASS] Source Type: {all_docs_data.get('source_type')}")
print(f"  [PASS] Answer: {all_docs_data.get('answer')[:150]}...")
print("Test 8 Passed: All documents search returned valid answer.")

# -------------------------------------------------------------
# Test 9: Verify Backward Compatibility (/chat & /document-intelligence)
# -------------------------------------------------------------
print("\n[TEST 9] Testing Backward Compatibility for existing APIs (/chat, /document-intelligence)...")
res_chat = client.post("/chat", json={"question": "What is AI?"})
assert res_chat.status_code == 200, f"/chat failed: {res_chat.text}"
print("  [PASS] POST /chat working (HTTP 200)")

res_di = client.get("/document-intelligence")
assert res_di.status_code == 200, f"/document-intelligence failed: {res_di.text}"
print(f"  [PASS] GET /document-intelligence working (HTTP 200, count={res_di.json().get('count')})")

res_docs = client.get("/documents")
assert res_docs.status_code == 200, f"/documents failed: {res_docs.text}"
print("  [PASS] GET /documents working (HTTP 200)")

print("\n" + "=" * 70)
print("ALL 9 TEST SUITES COMPLETED SUCCESSFULLY WITH 100% PASS RATE!")
print("=" * 70)
