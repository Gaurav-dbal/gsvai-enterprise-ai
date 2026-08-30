import os
import array

# pyrefly: ignore [missing-import]
import oracledb

from dotenv import load_dotenv
from services.oci_embedding_service import generate_embedding


# --------------------------------------------------
# Load environment variables
# --------------------------------------------------

load_dotenv()


# --------------------------------------------------
# Database configuration
# --------------------------------------------------

DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_WALLET_PASSWORD = os.getenv("DB_WALLET_PASSWORD")
DB_WALLET_DIR = os.getenv("DB_WALLET_DIR")
DB_DSN = os.getenv("DB_DSN")


# --------------------------------------------------
import time
from services.oci_embedding_service import MODEL_ID as EMBEDDING_MODEL_ID


# --------------------------------------------------
# Semantic Vector Search with Telemetry
# --------------------------------------------------

def search_similar_chunks_with_telemetry(
    query: str,
    top_k: int = 5,
    document_id: int = None,
):
    """
    Executes semantic vector search and measures exact embedding and database query duration
    for real backend execution tracing.
    """
    print(f"Generating embedding for query: {query}")

    # 1. Generate embedding
    t_emb_start = time.perf_counter()
    query_embedding = generate_embedding(query)
    embedding_duration_ms = (time.perf_counter() - t_emb_start) * 1000

    print(
        f"Query embedding generated: {len(query_embedding)} dimensions ({embedding_duration_ms:.1f}ms)"
    )

    query_vector = array.array("f", query_embedding)

    # 2. Connect to Oracle
    connection = oracledb.connect(
        user=DB_USER,
        password=DB_PASSWORD,
        dsn=DB_DSN,
        config_dir=DB_WALLET_DIR,
        wallet_location=DB_WALLET_DIR,
        wallet_password=DB_WALLET_PASSWORD,
    )

    t_db_start = time.perf_counter()
    cursor = connection.cursor()

    try:
        if document_id:
            sql = """
                SELECT
                    c.DOCUMENT_ID,
                    d.DOCUMENT_NAME,
                    c.CHUNK_NUMBER,
                    c.CHUNK_TEXT,
                    VECTOR_DISTANCE(
                        c.EMBEDDING,
                        :query_embedding,
                        COSINE
                    ) AS DISTANCE
                FROM GSVAI_DOCUMENT_CHUNKS c
                JOIN GSVAI_DOCUMENTS d
                    ON c.DOCUMENT_ID = d.DOCUMENT_ID
                WHERE c.EMBEDDING IS NOT NULL
                  AND c.DOCUMENT_ID = :document_id
                ORDER BY DISTANCE
                FETCH FIRST :top_k ROWS ONLY
            """

            cursor.execute(
                sql,
                query_embedding=query_vector,
                document_id=document_id,
                top_k=top_k,
            )
        else:
            sql = """
                SELECT
                    c.DOCUMENT_ID,
                    d.DOCUMENT_NAME,
                    c.CHUNK_NUMBER,
                    c.CHUNK_TEXT,
                    VECTOR_DISTANCE(
                        c.EMBEDDING,
                        :query_embedding,
                        COSINE
                    ) AS DISTANCE
                FROM GSVAI_DOCUMENT_CHUNKS c
                JOIN GSVAI_DOCUMENTS d
                    ON c.DOCUMENT_ID = d.DOCUMENT_ID
                WHERE c.EMBEDDING IS NOT NULL
                ORDER BY DISTANCE
                FETCH FIRST :top_k ROWS ONLY
            """

            cursor.execute(
                sql,
                query_embedding=query_vector,
                top_k=top_k,
            )

        rows = cursor.fetchall()
        search_duration_ms = (time.perf_counter() - t_db_start) * 1000

        results = []
        for row in rows:
            doc_id = row[0]
            doc_name = row[1]
            chunk_num = row[2]
            chunk_text = row[3]
            distance = row[4]

            if hasattr(chunk_text, "read"):
                chunk_text = chunk_text.read()

            results.append({
                "document_id": doc_id,
                "document_name": doc_name,
                "chunk_number": chunk_num,
                "chunk_text": chunk_text,
                "distance": distance,
            })

        min_distance = min([r["distance"] for r in results]) if results else 1.0

        telemetry = {
            "embedding_duration_ms": embedding_duration_ms,
            "search_duration_ms": search_duration_ms,
            "dimensions": len(query_embedding),
            "model_id": EMBEDDING_MODEL_ID,
            "top_k": top_k,
            "document_id": document_id,
            "chunks_found": len(results),
            "min_distance": min_distance,
        }

        print(f"Search returned {len(results)} result(s) ({search_duration_ms:.1f}ms).")
        return results, telemetry

    finally:
        cursor.close()
        connection.close()


def search_similar_chunks(
    query: str,
    top_k: int = 5,
    document_id: int = None,
):
    results, _ = search_similar_chunks_with_telemetry(
        query=query,
        top_k=top_k,
        document_id=document_id,
    )
    return results