import time
from typing import Any, Dict, List, Optional
import oracledb

from services.oracle_db_service import get_connection
from services.ai_runtime_config import get_embedding_config
from services.semantic_search_service import search_similar_chunks_with_telemetry
from services.oci_embedding_service import generate_embedding
from services.auth_rbac_service import log_audit_event


def get_rag_knowledge_stats() -> Dict[str, Any]:
    """
    Returns dynamically calculated statistics for enterprise RAG and Knowledge base.
    No hardcoded counts.
    """
    conn = get_connection()
    cursor = conn.cursor()
    try:
        # Document counts by status
        cursor.execute(
            """
            SELECT
                COUNT(*) AS total_docs,
                NVL(SUM(CASE WHEN STATUS = 'INDEXED' THEN 1 ELSE 0 END), 0) AS indexed_docs,
                NVL(SUM(CASE WHEN STATUS = 'PROCESSING' THEN 1 ELSE 0 END), 0) AS processing_docs,
                NVL(SUM(CASE WHEN STATUS = 'FAILED' THEN 1 ELSE 0 END), 0) AS failed_docs
            FROM GSVAI_DOCUMENTS
            """
        )
        row_docs = cursor.fetchone()
        total_docs = row_docs[0] or 0
        indexed_docs = row_docs[1] or 0
        processing_docs = row_docs[2] or 0
        failed_docs = row_docs[3] or 0

        # Chunk counts and embedded chunk counts
        cursor.execute(
            """
            SELECT
                COUNT(*) AS total_chunks,
                NVL(SUM(CASE WHEN EMBEDDING IS NOT NULL THEN 1 ELSE 0 END), 0) AS embedded_chunks
            FROM GSVAI_DOCUMENT_CHUNKS
            """
        )
        row_chunks = cursor.fetchone()
        total_chunks = row_chunks[0] or 0
        embedded_chunks = row_chunks[1] or 0

        emb_cfg = get_embedding_config()

        return {
            "documents_count": total_docs,
            "indexed_count": indexed_docs,
            "chunks_count": total_chunks,
            "dimensions": 1024,
            "distance_metric": "COSINE",
            "vector_table": "GSVAI_DOCUMENT_CHUNKS",
            "embedding_model": emb_cfg["model"],
            "documents": {
                "total": total_docs,
                "indexed": indexed_docs,
                "processing": processing_docs,
                "failed": failed_docs,
            },
            "chunks": {
                "total": total_chunks,
                "embedded": embedded_chunks,
                "pending_embedding": max(0, total_chunks - embedded_chunks),
            },
            "embedding": {
                "provider": emb_cfg["provider"],
                "model": emb_cfg["model"],
                "dimensions": emb_cfg["dimensions"],
                "status": "HEALTHY",
            },
            "vector_search": {
                "provider": "Oracle AI Vector Search",
                "table": "GSVAI_DOCUMENT_CHUNKS",
                "dimensions": 1024,
                "distance_metric": "COSINE",
                "status": "HEALTHY",
            },
            "retrieval": {
                "default_top_k": 5,
                "similarity_threshold": "Not explicitly configured",
                "ranking_mode": "COSINE Nearest Neighbors",
            },
        }
    finally:
        cursor.close()
        conn.close()


def get_rag_knowledge_health() -> Dict[str, Any]:
    """
    Evaluates health of the local embedding engine and Oracle Vector Search.
    Does NOT call the LLM.
    """
    status_components = {}
    overall_healthy = True

    # 1. Embedding Engine Check
    try:
        t_start = time.perf_counter()
        probe_embedding = generate_embedding("GSVAI knowledge health check probe")
        emb_latency_ms = round((time.perf_counter() - t_start) * 1000, 2)

        if len(probe_embedding) == 1024:
            status_components["embedding_engine"] = {
                "status": "HEALTHY",
                "model": "BAAI/bge-large-en-v1.5",
                "dimensions": len(probe_embedding),
                "latency_ms": emb_latency_ms,
            }
        else:
            overall_healthy = False
            status_components["embedding_engine"] = {
                "status": "DEGRADED",
                "error": f"Unexpected embedding dimensions: {len(probe_embedding)} (expected 1024)",
            }
    except Exception as e:
        overall_healthy = False
        status_components["embedding_engine"] = {
            "status": "UNAVAILABLE",
            "error": str(e),
        }

    # 2. Oracle Vector Search Check
    try:
        t_start = time.perf_counter()
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                SELECT COUNT(*) FROM GSVAI_DOCUMENT_CHUNKS WHERE ROWNUM <= 1
                """
            )
            cursor.fetchone()
            db_latency_ms = round((time.perf_counter() - t_start) * 1000, 2)
            status_components["vector_database"] = {
                "status": "HEALTHY",
                "provider": "Oracle Autonomous Database",
                "table": "GSVAI_DOCUMENT_CHUNKS",
                "latency_ms": db_latency_ms,
            }
        finally:
            cursor.close()
            conn.close()
    except Exception as e:
        overall_healthy = False
        status_components["vector_database"] = {
            "status": "UNAVAILABLE",
            "error": str(e),
        }

    return {
        "status": "HEALTHY" if overall_healthy else "DEGRADED",
        "dimension_match": overall_healthy,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "components": status_components,
    }


def get_rag_knowledge_documents() -> List[Dict[str, Any]]:
    """
    Returns the real inventory of documents persisted in the enterprise knowledge base.
    """
    conn = get_connection()
    cursor = conn.cursor()
    try:
        # Fetch documents along with chunk count and embedded chunk count
        cursor.execute(
            """
            SELECT
                d.DOCUMENT_ID,
                d.DOCUMENT_NAME,
                d.DOCUMENT_TYPE,
                d.STATUS,
                d.CREATED_AT,
                d.SOURCE,
                NVL(c.chunk_count, 0) AS chunks_count,
                NVL(c.embedded_count, 0) AS embedded_count,
                NVL(i.PAGE_COUNT, 0) AS page_count,
                NVL(i.OCR_STATUS, 'completed') AS ocr_status,
                i.ANALYSIS_ID
            FROM GSVAI_DOCUMENTS d
            LEFT JOIN (
                SELECT
                    DOCUMENT_ID,
                    COUNT(*) AS chunk_count,
                    SUM(CASE WHEN EMBEDDING IS NOT NULL THEN 1 ELSE 0 END) AS embedded_count
                FROM GSVAI_DOCUMENT_CHUNKS
                GROUP BY DOCUMENT_ID
            ) c ON d.DOCUMENT_ID = c.DOCUMENT_ID
            LEFT JOIN (
                SELECT
                    DOCUMENT_NAME,
                    PAGE_COUNT,
                    OCR_STATUS,
                    ANALYSIS_ID,
                    ROW_NUMBER() OVER (PARTITION BY DOCUMENT_NAME ORDER BY ANALYSIS_ID DESC) AS rn
                FROM GSVAI_DOCUMENT_INTELLIGENCE
            ) i ON d.DOCUMENT_NAME = i.DOCUMENT_NAME AND i.rn = 1
            ORDER BY d.DOCUMENT_ID DESC
            """
        )

        rows = cursor.fetchall()
        documents = []
        for r in rows:
            created_str = r[4].isoformat() + "Z" if hasattr(r[4], "isoformat") else str(r[4] or "")
            documents.append({
                "document_id": r[0],
                "document_name": r[1],
                "document_type": r[2] or "PDF",
                "status": r[3] or "UNKNOWN",
                "created_at": created_str,
                "source": r[5] or r[1],
                "chunks_count": int(r[6]),
                "embedded_count": int(r[7]),
                "embedding_status": "COMPLETED" if r[6] > 0 and r[6] == r[7] else ("PENDING" if r[6] > 0 else "NO_CHUNKS"),
                "page_count": int(r[8]) if r[8] else None,
                "ocr_status": r[9],
                "analysis_id": r[10],
            })
        return documents
    finally:
        cursor.close()
        conn.close()


def test_rag_retrieval(query: str, top_k: int = 5, user_id: str = "admin") -> Dict[str, Any]:
    """
    Executes a diagnostic semantic search against Oracle Vector Search.
    Does NOT invoke the LLM.
    """
    q_clean = query.strip()
    if not q_clean:
        raise ValueError("Diagnostic retrieval query cannot be empty.")

    t_start = time.perf_counter()
    chunks, telemetry = search_similar_chunks_with_telemetry(q_clean, top_k=top_k)
    elapsed_ms = round((time.perf_counter() - t_start) * 1000, 2)

    formatted_results = []
    for idx, chunk in enumerate(chunks, start=1):
        raw_text = chunk.get("text", "")
        # Safe preview up to 250 characters
        preview = raw_text[:250] + ("..." if len(raw_text) > 250 else "")
        distance = chunk.get("distance", 0.0)
        similarity = max(0.0, min(1.0, 1.0 - (distance or 0.0)))

        formatted_results.append({
            "rank": idx,
            "document_id": chunk.get("document_id"),
            "document_name": chunk.get("document_name"),
            "chunk_number": chunk.get("chunk_number"),
            "chunk_index": chunk.get("chunk_number"),
            "distance": round(distance, 4) if distance is not None else None,
            "similarity": round(similarity, 4),
            "score": round(similarity, 4),
            "preview_text": preview,
            "chunk_text": preview,
        })

    # Log audit event
    log_audit_event(
        action="KNOWLEDGE_RETRIEVAL_TESTED",
        resource_type="RAG_KNOWLEDGE",
        resource_id=str(top_k),
        user_id=user_id,
        details={
            "query_length": len(q_clean),
            "top_k": top_k,
            "results_count": len(formatted_results),
            "latency_ms": elapsed_ms,
        },
    )

    return {
        "query": q_clean,
        "embedding_dimensions": 1024,
        "retrieval_count": len(formatted_results),
        "latency_ms": elapsed_ms,
        "telemetry": {
            "search_latency_ms": telemetry.get("search_latency_ms"),
            "embedding_latency_ms": telemetry.get("embedding_latency_ms"),
            "dimensions": telemetry.get("dimensions", 1024),
            "model_id": telemetry.get("model_id"),
        },
        "results": formatted_results,
        "chunks": formatted_results,
    }


def reprocess_knowledge_document(document_id: int, user_id: str = "admin") -> Dict[str, Any]:
    """
    Safely re-embeds all existing chunks for a document using the active BGE model.
    """
    conn = get_connection()
    cursor = conn.cursor()
    try:
        # Verify document exists
        cursor.execute(
            """
            SELECT DOCUMENT_ID, DOCUMENT_NAME FROM GSVAI_DOCUMENTS WHERE DOCUMENT_ID = :doc_id
            """,
            doc_id=document_id
        )
        doc_row = cursor.fetchone()
        if not doc_row:
            raise ValueError(f"Document ID {document_id} not found.")

        doc_name = doc_row[1]

        # Fetch chunks
        cursor.execute(
            """
            SELECT CHUNK_ID, CHUNK_TEXT FROM GSVAI_DOCUMENT_CHUNKS WHERE DOCUMENT_ID = :doc_id ORDER BY CHUNK_NUMBER
            """,
            doc_id=document_id
        )
        chunks = cursor.fetchall()
        if not chunks:
            raise ValueError(f"No chunks found for Document ID {document_id}.")

        reprocessed_count = 0
        t_start = time.perf_counter()

        for chunk_id, chunk_raw in chunks:
            chunk_text = chunk_raw.read() if hasattr(chunk_raw, "read") else (chunk_raw or "")
            new_emb = generate_embedding(chunk_text)

            cursor.execute(
                """
                UPDATE GSVAI_DOCUMENT_CHUNKS
                SET EMBEDDING = :emb
                WHERE CHUNK_ID = :chunk_id
                """,
                emb=str(new_emb),
                chunk_id=chunk_id
            )
            reprocessed_count += 1

        cursor.execute(
            """
            UPDATE GSVAI_DOCUMENTS
            SET STATUS = 'INDEXED'
            WHERE DOCUMENT_ID = :doc_id
            """,
            doc_id=document_id
        )
        conn.commit()
        elapsed_ms = round((time.perf_counter() - t_start) * 1000, 2)

        log_audit_event(
            action="KNOWLEDGE_DOCUMENT_REPROCESSED",
            resource_type="RAG_KNOWLEDGE",
            resource_id=str(document_id),
            user_id=user_id,
            details={
                "document_name": doc_name,
                "chunks_reprocessed": reprocessed_count,
                "latency_ms": elapsed_ms,
            },
        )

        return {
            "status": "SUCCESS",
            "document_id": document_id,
            "document_name": doc_name,
            "chunks_reprocessed": reprocessed_count,
            "latency_ms": elapsed_ms,
            "message": f"Successfully reprocessed and re-embedded {reprocessed_count} chunks for '{doc_name}'.",
        }
    finally:
        cursor.close()
        conn.close()


def delete_knowledge_document(document_id: int, user_id: str = "admin") -> Dict[str, Any]:
    """
    Safely deletes a document and all associated chunks from the Oracle Vector DB.
    Guarantees no orphan chunks remain.
    """
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            SELECT DOCUMENT_NAME FROM GSVAI_DOCUMENTS WHERE DOCUMENT_ID = :doc_id
            """,
            doc_id=document_id
        )
        row = cursor.fetchone()
        if not row:
            raise ValueError(f"Document ID {document_id} not found.")

        doc_name = row[0]

        # 1. Delete chunks first
        cursor.execute(
            """
            DELETE FROM GSVAI_DOCUMENT_CHUNKS WHERE DOCUMENT_ID = :doc_id
            """,
            doc_id=document_id
        )
        deleted_chunks = cursor.rowcount

        # 2. Delete parent document record
        cursor.execute(
            """
            DELETE FROM GSVAI_DOCUMENTS WHERE DOCUMENT_ID = :doc_id
            """,
            doc_id=document_id
        )

        conn.commit()

        log_audit_event(
            action="KNOWLEDGE_DOCUMENT_DELETED",
            resource_type="RAG_KNOWLEDGE",
            resource_id=str(document_id),
            user_id=user_id,
            details={
                "document_name": doc_name,
                "deleted_chunks": deleted_chunks,
            },
        )

        return {
            "status": "SUCCESS",
            "document_id": document_id,
            "document_name": doc_name,
            "deleted_chunks": deleted_chunks,
            "message": f"Deleted document '{doc_name}' and removed {deleted_chunks} vector chunks.",
        }
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()
