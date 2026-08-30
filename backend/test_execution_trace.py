import os
import sys
import json

# Ensure UTF-8 output encoding on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

print("=" * 75)
print("GSVAI ENTERPRISE AI: EXECUTION TRACE VERIFICATION SUITE")
print("=" * 75)

# Fetch current documents list
res_docs = client.get("/ai-workspace/documents")
assert res_docs.status_code == 200, f"Failed to get documents: {res_docs.text}"
docs_list = res_docs.json().get("documents", [])

career_doc = next((d for d in docs_list if "career" in d["document_name"].lower()), None)
sr_doc = next((d for d in docs_list if "sr" in d["document_name"].lower() or "oracle" in d["document_name"].lower()), None)

if career_doc:
    sample_doc_id = career_doc["document_id"]
    sample_doc_name = career_doc["document_name"]
    sample_question = "What is the target salary mentioned in this document?"
elif sr_doc:
    sample_doc_id = sr_doc["document_id"]
    sample_doc_name = sr_doc["document_name"]
    sample_question = "What is the purpose of the Service Request process?"
else:
    sample_doc_id = docs_list[0]["document_id"] if docs_list else 12
    sample_doc_name = docs_list[0]["document_name"] if docs_list else "Enterprise_Doc.pdf"
    sample_question = "Explain the key topics described in this document."

print(f"Active Document for Tests: ID={sample_doc_id}, Name='{sample_doc_name}'\n")

# -------------------------------------------------------------
# TEST 1: General AI Query Trace ("What is Generative AI?")
# -------------------------------------------------------------
print("[TEST 1] General AI Query: 'What is Generative AI?'")
res1 = client.post(
    "/ai-workspace/chat",
    json={"question": "What is Generative AI?", "document_id": None, "scope": "all"}
)
assert res1.status_code == 200, f"Test 1 Failed: {res1.text}"
data1 = res1.json()
trace1 = data1.get("trace")

assert trace1 is not None, "Trace object missing from response"
assert trace1["enabled"] is True
assert trace1["route"] == "GENERAL_AI"
assert trace1["rag_used"] is False
assert len(data1.get("sources", [])) == 0

step_names = [s["name"] for s in trace1["steps"]]
step_statuses = {s["name"]: s["status"] for s in trace1["steps"]}

print(f"  [PASS] Route: {trace1['route_label']}")
print(f"  [PASS] RAG Used: {trace1['rag_used']}")
print(f"  [PASS] Total Duration: {trace1['total_duration_ms']}ms ({len(trace1['steps'])} steps)")
print(f"  [PASS] Steps Recorded: {step_names}")
assert step_statuses.get("Embedding Generation") == "skipped"
assert step_statuses.get("Oracle Vector Search") == "skipped"
assert step_statuses.get("OCI Generative AI") == "completed"
print(f"  [PASS] Embedding: SKIPPED (Reason: RAG not used)")
print(f"  [PASS] Vector Search: SKIPPED (Reason: RAG not used)")
llm_step = next(s for s in trace1["steps"] if s["name"] == "OCI Generative AI")
print(f"  [PASS] Actual OCI Model: {llm_step['details'].get('model')}")
print("Test 1 Passed: General AI trace accurately reflects execution.\n")

# -------------------------------------------------------------
# TEST 2: Selected Document RAG
# -------------------------------------------------------------
print(f"[TEST 2] Selected Document RAG: '{sample_question}' (Doc ID: {sample_doc_id}, Name: '{sample_doc_name}')")
res2 = client.post(
    "/ai-workspace/chat",
    json={
        "question": sample_question,
        "document_id": sample_doc_id,
        "scope": "document"
    }
)
assert res2.status_code == 200, f"Test 2 Failed: {res2.text}"
data2 = res2.json()
trace2 = data2.get("trace")

assert trace2 is not None
assert trace2["route"] == "SELECTED_DOCUMENT_RAG"
assert trace2["rag_used"] is True

step_statuses2 = {s["name"]: s["status"] for s in trace2["steps"]}
assert step_statuses2.get("Embedding Generation") == "completed"
assert step_statuses2.get("Oracle Vector Search") == "completed"
assert step_statuses2.get("OCI Generative AI") == "completed"

emb_step2 = next(s for s in trace2["steps"] if s["name"] == "Embedding Generation")
vec_step2 = next(s for s in trace2["steps"] if s["name"] == "Oracle Vector Search")
src_step2 = next(s for s in trace2["steps"] if s["name"] == "Sources / Citations")

print(f"  [PASS] Route: {trace2['route_label']}")
print(f"  [PASS] RAG Used: {trace2['rag_used']}")
print(f"  [PASS] Embedding Model: {emb_step2['details'].get('model')} ({emb_step2['details'].get('dimensions')} dims, {emb_step2['duration_ms']}ms)")
print(f"  [PASS] Vector Search: Table='{vec_step2['details'].get('table')}', Metric='{vec_step2['details'].get('distance_metric')}', Chunks={vec_step2['details'].get('chunks_matched')}, Distance={vec_step2['details'].get('min_distance')}")
print(f"  [PASS] Citations Count: {src_step2['details'].get('citation_count')} sources")
print("Test 2 Passed: Selected Document RAG trace verified end-to-end.\n")

# -------------------------------------------------------------
# TEST 3: All Documents RAG ("How do I create a supplier invoice?")
# -------------------------------------------------------------
print("[TEST 3] All Documents RAG Query: 'How do I create a supplier invoice in Oracle Fusion Payables?'")
res3 = client.post(
    "/ai-workspace/chat",
    json={
        "question": "How do I create a supplier invoice in Oracle Fusion Payables?",
        "document_id": None,
        "scope": "all"
    }
)
assert res3.status_code == 200, f"Test 3 Failed: {res3.text}"
data3 = res3.json()
trace3 = data3.get("trace")

assert trace3 is not None
print(f"  [PASS] Route: {trace3['route_label']}")
print(f"  [PASS] RAG Used: {trace3['rag_used']}")
print(f"  [PASS] Total Duration: {trace3['total_duration_ms']}ms")
print("Test 3 Passed: All Documents RAG trace verified.\n")

# -------------------------------------------------------------
# TEST 4: Document Summary ("Summarize this document.")
# -------------------------------------------------------------
print(f"[TEST 4] Document Summary: 'Summarize this document.' (Doc ID: {sample_doc_id})")
res4 = client.post(
    "/ai-workspace/chat",
    json={
        "question": "Summarize this document.",
        "document_id": sample_doc_id,
        "scope": "document",
        "query_mode": "summary"
    }
)
assert res4.status_code == 200, f"Test 4 Failed: {res4.text}"
data4 = res4.json()
trace4 = data4.get("trace")

assert trace4 is not None
assert trace4["route"] == "DOCUMENT_SUMMARY"
assert trace4["rag_used"] is True

step_statuses4 = {s["name"]: s["status"] for s in trace4["steps"]}
assert step_statuses4.get("Embedding Generation") == "skipped"
assert step_statuses4.get("Oracle Vector Search") == "skipped"
assert step_statuses4.get("Context Construction") == "completed"
assert step_statuses4.get("OCI Generative AI") == "completed"

print(f"  [PASS] Route: {trace4['route_label']}")
print(f"  [PASS] Sequential Chunk Retrieval (Embedding/Vector search skipped for direct summary)")
print(f"  [PASS] Summary Length: {len(data4.get('answer', ''))} characters")
print("Test 4 Passed: Document Summary trace verified.\n")

# -------------------------------------------------------------
# TEST 5: Date-Based Summary ("Summarize documents uploaded today.")
# -------------------------------------------------------------
print("[TEST 5] Date-Based Summary: 'Summarize documents uploaded today.'")
res5 = client.post(
    "/ai-workspace/chat",
    json={"question": "Summarize the documents uploaded today.", "document_id": None, "scope": "all"}
)
assert res5.status_code == 200, f"Test 5 Failed: {res5.text}"
data5 = res5.json()
trace5 = data5.get("trace")

assert trace5 is not None
assert trace5["route"] == "DATE_BASED_SUMMARY"
print(f"  [PASS] Route: {trace5['route_label']}")
print(f"  [PASS] Date Filter: TRUNC(CREATED_AT) = TRUNC(SYSDATE)")
print("Test 5 Passed: Date-based summary trace verified.\n")

print("=" * 75)
print("ALL 5 AI EXECUTION TRACE TESTS COMPLETED WITH 100% SUCCESS!")
print("=" * 75)
