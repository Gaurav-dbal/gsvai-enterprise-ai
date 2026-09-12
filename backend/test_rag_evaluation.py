"""
GSVAI Enterprise AI
RAG Quality Evaluation Suite

Purpose:
    Evaluate live RAG quality against a golden evaluation dataset.

This is a LIVE integration evaluation.

It verifies:
    1. API response
    2. Trace availability
    3. Correct routing
    4. RAG usage
    5. Embedding generation
    6. 1024-dimensional embeddings
    7. Oracle Vector Search
    8. Retrieved chunks
    9. Retrieval distance
    10. LLM execution
    11. Groq provider
    12. Citations / sources
    13. Required concept coverage
    14. Reference-answer coverage

This test does NOT modify enterprise data.
"""

import json
import sys
from pathlib import Path

from fastapi.testclient import TestClient


# ============================================================
# PROJECT PATH
# ============================================================

# Allows this file to be executed from:
#
#   Project root:
#       python .\backend\test_rag_evaluation.py
#
#   backend directory:
#       python .\test_rag_evaluation.py

PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# ============================================================
# APPLICATION
# ============================================================

from backend.main import app


client = TestClient(app)


# ============================================================
# GSVAI RAG QUALITY EVALUATION DATASET
# ============================================================

DATASET_PATH = Path(__file__).with_name("rag_evaluation_dataset.json")


def load_evaluation_cases():
    """
    Load golden RAG evaluation cases from JSON.
    """

    if not DATASET_PATH.exists():
        raise FileNotFoundError(
            f"Golden RAG evaluation dataset not found: {DATASET_PATH}"
        )

    with DATASET_PATH.open("r", encoding="utf-8") as f:
        dataset = json.load(f)

    cases = dataset.get("evaluation_cases", [])

    if not cases:
        raise ValueError(
            "Golden RAG evaluation dataset contains no evaluation cases."
        )

    return cases


EVALUATION_CASES = load_evaluation_cases()


# ============================================================
# EVALUATION HELPERS
# ============================================================

def get_case_name(case):
    """
    Support both:
        case["name"]
    and:
        case["id"]
    """

    return case.get(
        "name",
        case.get(
            "id",
            "Unknown Case"
        )
    )


def get_step(trace, step_name):
    """
    Find a trace step by name.
    """

    steps = trace.get("steps", [])

    for step in steps:
        if (
            step.get("name") == step_name
            or step.get("step") == step_name
        ):
            return step

    return None


def get_llm_step(trace):
    """
    Find the LLM generation step.
    """

    possible_names = [
        "Groq LLM",
        "Ollama LLM",
        "LLM Generation",
        "Generate Answer",
        "LLM",
    ]

    for name in possible_names:
        step = get_step(trace, name)

        if step:
            return step

    return None


def get_sources(response):
    """
    Extract sources from the API response.
    """

    sources = response.get("sources")

    if sources is None:
        sources = []

    return sources


# ============================================================
# SINGLE CASE EVALUATION
# ============================================================

def evaluate_case(case):
    """
    Execute and evaluate one RAG question.
    """

    case_name = get_case_name(case)

    question = case.get("question", "")

    expected_route = case.get(
        "expected_route",
        "ENTERPRISE_KNOWLEDGE_RAG"
    )

    expected_source_keywords = case.get(
        "expected_source_keywords",
        []
    )

    required_concepts = case.get(
        "required_concepts",
        []
    )

    reference_answer = case.get(
        "reference_answer",
        ""
    )

    min_citations = case.get(
        "min_citations",
        1
    )

    max_distance = case.get(
        "max_distance",
        0.58
    )

    print()
    print("-" * 75)
    print(f"EVALUATION: {case_name}")
    print("-" * 75)

    print(f"Question: {question}")

    # ========================================================
    # API REQUEST
    # ========================================================

    payload = {
        "question": question,
        "document_id": None,
        "scope": "all",
    }

    response = client.post(
        "/ai-workspace/chat",
        json=payload,
    )

    # --------------------------------------------------------
    # Check 1: HTTP response
    # --------------------------------------------------------

    assert response.status_code == 200, (
        f"Expected HTTP 200, got {response.status_code}: "
        f"{response.text[:500]}"
    )

    print("[PASS] HTTP 200")

    data = response.json()

    # ========================================================
    # RESPONSE
    # ========================================================

    answer = data.get("answer", "")

    trace = data.get("trace")

    sources = get_sources(data)

    # --------------------------------------------------------
    # Check 2: Trace exists
    # --------------------------------------------------------

    assert trace is not None, (
        "RAG response does not contain trace."
    )

    print("[PASS] Execution trace available")

    # --------------------------------------------------------
    # Check 3: Route
    # --------------------------------------------------------

    route = (
        trace.get("route")
        or trace.get("routing")
        or trace.get("source_type")
        or data.get("source_type")
    )

    assert route == expected_route, (
        f"Expected route '{expected_route}', "
        f"got '{route}'"
    )

    print(f"[PASS] Route: {route}")

    # --------------------------------------------------------
    # Check 4: RAG used
    # --------------------------------------------------------

    rag_used = trace.get("rag_used")

    if rag_used is None:
        rag_used = data.get("rag_used")

    assert rag_used is True, (
        f"Expected RAG to be used, got {rag_used}"
    )

    print("[PASS] RAG used")

    # ========================================================
    # EMBEDDING
    # ========================================================

    embedding_step = get_step(
        trace,
        "Embedding Generation"
    )

    if embedding_step is None:
        embedding_step = get_step(
            trace,
            "Query Embedding"
        )

    assert embedding_step is not None, (
        "Embedding generation trace step not found."
    )

    embedding_status = embedding_step.get(
        "status",
        ""
    ).lower()

    assert embedding_status == "completed", (
        f"Embedding step status is '{embedding_status}'"
    )

    print("[PASS] Embedding generation completed")

    # --------------------------------------------------------
    # Check 6: Embedding dimensions
    # --------------------------------------------------------

    embedding_details = (
        embedding_step.get("details")
        or {}
    )

    dimensions = (
        embedding_details.get("dimensions")
        or embedding_details.get("dimension")
    )

    if dimensions is None:
        dimensions = trace.get("embedding_dimensions")

    assert dimensions == 1024, (
        f"Expected 1024-dimensional embeddings, "
        f"got {dimensions}"
    )

    print(
        f"[PASS] Embedding dimensions: {dimensions}"
    )

    # ========================================================
    # VECTOR SEARCH
    # ========================================================

    vector_step = get_step(
        trace,
        "Oracle Vector Search"
    )

    if vector_step is None:
        vector_step = get_step(
            trace,
            "Vector Search"
        )

    assert vector_step is not None, (
        "Oracle Vector Search trace step not found."
    )

    vector_status = vector_step.get(
        "status",
        ""
    ).lower()

    assert vector_status == "completed", (
        f"Vector search status is '{vector_status}'"
    )

    print(
        "[PASS] Oracle Vector Search completed"
    )

    # --------------------------------------------------------
    # Check 8: Retrieved chunks
    # --------------------------------------------------------

    vector_details = (
        vector_step.get("details")
        or {}
    )

    chunks_matched = (
        vector_details.get("chunks_matched")
        or vector_details.get("results_count")
        or vector_details.get("result_count")
        or 0
    )

    assert int(chunks_matched) > 0, (
        "Oracle Vector Search returned zero chunks."
    )

    print(
        f"[PASS] Chunks retrieved: {chunks_matched}"
    )

    # --------------------------------------------------------
    # Check 9: Retrieval distance
    # --------------------------------------------------------

    min_distance = (
        vector_details.get("min_distance")
    )

    if min_distance is None:
        min_distance = vector_details.get(
            "best_distance"
        )

    if min_distance is None:
        min_distance = vector_details.get(
            "distance"
        )

    assert min_distance is not None, (
        "Minimum retrieval distance not found."
    )

    min_distance = float(min_distance)

    assert min_distance <= max_distance, (
        f"Retrieval distance {min_distance:.4f} "
        f"exceeds maximum allowed {max_distance:.4f}"
    )

    print(
        f"[PASS] Retrieval distance: "
        f"{min_distance:.4f} "
        f"(threshold {max_distance:.4f})"
    )

    # ========================================================
    # LLM
    # ========================================================

    llm_step = get_llm_step(trace)

    assert llm_step is not None, (
        "LLM generation trace step not found."
    )

    llm_status = llm_step.get(
        "status",
        ""
    ).lower()

    assert llm_status == "completed", (
        f"LLM step status is '{llm_status}'"
    )

    print("[PASS] LLM generation completed")

    # --------------------------------------------------------
    # Check 11: Groq provider
    # --------------------------------------------------------

    llm_details = (
        llm_step.get("details")
        or {}
    )

    provider = (
        llm_details.get("provider")
        or trace.get("llm_provider")
        or ""
    )

    assert "groq" in str(provider).lower(), (
        f"Expected Groq provider, got '{provider}'"
    )

    print(
        f"[PASS] LLM provider: {provider}"
    )

    # --------------------------------------------------------
    # Check 12: Model exists
    # --------------------------------------------------------

    model = (
        llm_details.get("model")
        or trace.get("llm_model")
    )

    assert model, (
        "LLM model information missing."
    )

    print(
        f"[PASS] LLM model: {model}"
    )

    # ========================================================
    # SOURCES / CITATIONS
    # ========================================================

    citation_step = get_step(
        trace,
        "Sources / Citations"
    )

    if citation_step is None:
        citation_step = get_step(
            trace,
            "Sources/Citations"
        )

    if citation_step is None:
        citation_step = get_step(
            trace,
            "Citations"
        )

    assert citation_step is not None, (
        "Sources/Citations trace step not found."
    )

    citation_details = (
        citation_step.get("details")
        or {}
    )

    citation_count = (
        citation_details.get("citation_count")
        or len(sources)
    )

    # --------------------------------------------------------
    # Check 13: Citation count
    # --------------------------------------------------------

    assert int(citation_count) >= min_citations, (
        f"Expected at least {min_citations} citations, "
        f"got {citation_count}"
    )

    print(
        f"[PASS] Citation count: {citation_count}"
    )

    # ========================================================
    # SOURCE VALIDATION
    # ========================================================

    source_text = ""

    for source in sources:

        if not isinstance(source, dict):
            continue

        document_name = str(
            source.get("document_name", "")
        )

        page_number = str(
            source.get("page_number", "")
        )

        chunk_number = str(
            source.get("chunk_number", "")
        )

        text = str(
            source.get("text", "")
        )

        source_text += (
            f" {document_name}"
            f" {page_number}"
            f" {chunk_number}"
            f" {text}"
        )

    source_text_lower = source_text.lower()

    # --------------------------------------------------------
    # Check 14: Expected source keywords
    # --------------------------------------------------------

    matched_source_keywords = []

    for keyword in expected_source_keywords:

        if keyword.lower() in source_text_lower:

            matched_source_keywords.append(
                keyword
            )

    if expected_source_keywords:

        source_keyword_coverage = (
            len(matched_source_keywords)
            / len(expected_source_keywords)
        )

        assert source_keyword_coverage >= 0.50, (
            "Expected source keyword coverage "
            f"{source_keyword_coverage:.1%} "
            f"is below 50%. "
            f"Matched: {matched_source_keywords}; "
            f"Expected: {expected_source_keywords}"
        )

        print(
            "[PASS] Expected source keywords: "
            f"{source_keyword_coverage:.1%} "
            f"({len(matched_source_keywords)}/"
            f"{len(expected_source_keywords)})"
        )

    else:

        source_keyword_coverage = 1.0

        print(
            "[PASS] No source keyword requirement"
        )

    # ========================================================
    # ANSWER VALIDATION
    # ========================================================

    answer = str(answer)

    answer_lower = answer.lower()

    # --------------------------------------------------------
    # Required concept coverage
    # --------------------------------------------------------

    matched_required_concepts = []

    for concept in required_concepts:

        if concept.lower() in answer_lower:

            matched_required_concepts.append(
                concept
            )

    if required_concepts:

        concept_coverage = (
            len(matched_required_concepts)
            / len(required_concepts)
        )

    else:

        concept_coverage = 1.0

    # --------------------------------------------------------
    # Check 15: Required concept coverage
    # --------------------------------------------------------

    assert concept_coverage >= 0.60, (
        "Ground-truth concept coverage "
        f"{concept_coverage:.1%} is below 60%. "
        f"Matched: {matched_required_concepts}; "
        f"Required: {required_concepts}"
    )

    print(
        "[PASS] Ground-truth concept coverage: "
        f"{concept_coverage:.1%} "
        f"({len(matched_required_concepts)}/"
        f"{len(required_concepts)})"
    )

    # ========================================================
    # REFERENCE ANSWER COVERAGE
    # ========================================================

    reference_lower = reference_answer.lower()

    reference_concepts = []

    for concept in required_concepts:

        if concept.lower() in reference_lower:

            reference_concepts.append(
                concept
            )

    matched_reference_concepts = []

    for concept in reference_concepts:

        if concept.lower() in answer_lower:

            matched_reference_concepts.append(
                concept
            )

    if reference_concepts:

        reference_coverage = (
            len(matched_reference_concepts)
            / len(reference_concepts)
        )

    else:

        reference_coverage = 1.0

    # --------------------------------------------------------
    # Check 16: Reference answer coverage
    # --------------------------------------------------------

    assert reference_coverage >= 0.60, (
        "Reference-answer coverage "
        f"{reference_coverage:.1%} is below 60%. "
        f"Matched: {matched_reference_concepts}; "
        f"Reference concepts: {reference_concepts}"
    )

    print(
        "[PASS] Reference-answer coverage: "
        f"{reference_coverage:.1%} "
        f"({len(matched_reference_concepts)}/"
        f"{len(reference_concepts)})"
    )

    # ========================================================
    # ADDITIONAL ANSWER QUALITY CHECKS
    # ========================================================

    # These are included in the final score to preserve the
    # original evaluator's answer-quality checks.

    answer_keyword_matches = []

    for concept in required_concepts:

        if concept.lower() in answer_lower:

            answer_keyword_matches.append(
                concept
            )

    # --------------------------------------------------------
    # Check 17: Answer has meaningful content
    #
    # This is informational rather than a separate weighted
    # check because concept coverage already evaluates content.
    # --------------------------------------------------------

    assert len(answer.strip()) >= 50, (
        f"Answer is too short: "
        f"{len(answer.strip())} characters"
    )

    print(
        f"[PASS] Answer length: "
        f"{len(answer.strip())} characters"
    )

    # ========================================================
    # FINAL SCORE
    # ========================================================

    checks = [
        True,                              # HTTP 200
        trace is not None,                # Trace
        route == expected_route,          # Route
        rag_used is True,                 # RAG
        embedding_status == "completed",  # Embedding
        dimensions == 1024,               # Dimensions
        vector_status == "completed",     # Vector
        int(chunks_matched) > 0,          # Chunks
        min_distance <= max_distance,     # Distance
        llm_status == "completed",        # LLM
        "groq" in str(provider).lower(),  # Provider
        bool(model),                       # Model
        int(citation_count) >= min_citations,
        source_keyword_coverage >= 0.50,
        concept_coverage >= 0.60,
        reference_coverage >= 0.60,
        len(answer.strip()) >= 50,
    ]

    passed_checks = sum(
        1 for check in checks
        if check
    )

    total_checks = len(checks)

    score = (
        passed_checks / total_checks
    ) * 100

    # ========================================================
    # RESULT
    # ========================================================

    print()
    print(
        f"CASE SCORE: "
        f"{score:.1f}% "
        f"({passed_checks}/{total_checks})"
    )

    print(
        f"Concept Coverage: "
        f"{concept_coverage:.1%}"
    )

    print(
        f"Reference Coverage: "
        f"{reference_coverage:.1%}"
    )

    print(
        f"Retrieval Distance: "
        f"{min_distance:.4f}"
    )

    print(
        f"Citations: "
        f"{citation_count}"
    )

    print(
        f"Answer Length: "
        f"{len(answer.strip())}"
    )

    return {
        "id": case.get("id"),
        "name": case_name,
        "question": question,
        "score": score,
        "passed_checks": passed_checks,
        "total_checks": total_checks,
        "concept_coverage": round(
            concept_coverage * 100,
            1
        ),
        "reference_coverage": round(
            reference_coverage * 100,
            1
        ),
        "retrieval_distance": round(
            min_distance,
            4
        ),
        "citation_count": int(
            citation_count
        ),
        "answer_length": len(
            answer.strip()
        ),
        "matched_concepts":
            matched_required_concepts,
    }


# ============================================================
# MAIN EVALUATION RUNNER
# ============================================================

if __name__ == "__main__":

    print("=" * 75)
    print(
        "GSVAI ENTERPRISE AI - "
        "RAG QUALITY EVALUATION"
    )
    print("=" * 75)

    print()
    print(
        "Evaluation type: "
        "LIVE RAG integration / "
        "golden dataset quality checks"
    )

    print(
        "Evaluation does NOT modify enterprise data."
    )

    print()

    print(
        f"Golden dataset: "
        f"{DATASET_PATH}"
    )

    print(
        f"Evaluation cases loaded: "
        f"{len(EVALUATION_CASES)}"
    )

    print()

    results = []

    failed_cases = []

    # ========================================================
    # RUN ALL CASES
    # ========================================================

    for case in EVALUATION_CASES:

        try:

            result = evaluate_case(case)

            results.append(result)

        except AssertionError as exc:

            case_name = get_case_name(case)

            print()
            print(
                f"[FAIL] {case_name}"
            )

            print(
                f"Reason: {exc}"
            )

            failed_cases.append(
                {
                    "id": case.get("id"),
                    "name": case_name,
                    "error": str(exc),
                }
            )

            results.append(
                {
                    "id": case.get("id"),
                    "name": case_name,
                    "score": 0.0,
                    "passed_checks": 0,
                    "total_checks": 17,
                    "concept_coverage": 0.0,
                    "reference_coverage": 0.0,
                    "retrieval_distance": None,
                    "citation_count": 0,
                    "answer_length": 0,
                    "matched_concepts": [],
                }
            )

        except Exception as exc:

            case_name = get_case_name(case)

            print()
            print(
                f"[ERROR] {case_name}"
            )

            print(
                f"Unexpected error: "
                f"{type(exc).__name__}: {exc}"
            )

            failed_cases.append(
                {
                    "id": case.get("id"),
                    "name": case_name,
                    "error": (
                        f"{type(exc).__name__}: "
                        f"{exc}"
                    ),
                }
            )

            results.append(
                {
                    "id": case.get("id"),
                    "name": case_name,
                    "score": 0.0,
                    "passed_checks": 0,
                    "total_checks": 17,
                    "concept_coverage": 0.0,
                    "reference_coverage": 0.0,
                    "retrieval_distance": None,
                    "citation_count": 0,
                    "answer_length": 0,
                    "matched_concepts": [],
                }
            )

    # ========================================================
    # OVERALL SUMMARY
    # ========================================================

    print()
    print()
    print("=" * 75)
    print(
        "GSVAI RAG QUALITY EVALUATION SUMMARY"
    )
    print("=" * 75)

    if results:

        overall_score = sum(
            result["score"]
            for result in results
        ) / len(results)

    else:

        overall_score = 0.0

    total_passed = sum(
        result["passed_checks"]
        for result in results
    )

    total_checks = sum(
        result["total_checks"]
        for result in results
    )

    print()
    print(
        f"Cases Evaluated : "
        f"{len(results)}"
    )

    print(
        f"Cases Failed    : "
        f"{len(failed_cases)}"
    )

    print(
        f"Checks Passed   : "
        f"{total_passed}/{total_checks}"
    )

    print(
        f"Overall Score   : "
        f"{overall_score:.1f}%"
    )

    print()
    print(
        "-" * 75
    )

    # ========================================================
    # CASE RESULTS
    # ========================================================

    for result in results:

        print(
            f"{result['name']}: "
            f"{result['score']:.1f}% "
            f"({result['passed_checks']}/"
            f"{result['total_checks']})"
        )

        print(
            f"    Concept Coverage : "
            f"{result['concept_coverage']:.1f}%"
        )

        print(
            f"    Reference Coverage: "
            f"{result['reference_coverage']:.1f}%"
        )

        if result["retrieval_distance"] is not None:

            print(
                f"    Retrieval Distance: "
                f"{result['retrieval_distance']:.4f}"
            )

        print(
            f"    Citations         : "
            f"{result['citation_count']}"
        )

        print(
            f"    Answer Length     : "
            f"{result['answer_length']}"
        )

        print()

    # ========================================================
    # FAILED CASES
    # ========================================================

    if failed_cases:

        print(
            "-" * 75
        )

        print(
            "FAILED CASES"
        )

        print(
            "-" * 75
        )

        for failure in failed_cases:

            print(
                f"{failure['name']}: "
                f"{failure['error']}"
            )

        print()

    # ========================================================
    # FINAL DECISION
    # ========================================================

    print("=" * 75)

    if overall_score >= 80.0 and not failed_cases:

        print(
            "RAG EVALUATION PASSED"
        )

        print(
            f"Overall quality score: "
            f"{overall_score:.1f}%"
        )

    else:

        print(
            "RAG EVALUATION REQUIRES REVIEW"
        )

        print(
            f"Overall quality score: "
            f"{overall_score:.1f}%"
        )

    print("=" * 75)