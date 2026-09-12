import sys
import os

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from services.oracle_db_service import get_connection


def ensure_observability_table():
    """
    Idempotently creates the GSVAI_AI_OBSERVABILITY table and its indexes
    in the active Oracle Autonomous Database.
    """
    conn = get_connection()
    cursor = conn.cursor()
    try:
        # Check if table already exists
        cursor.execute(
            """
            SELECT COUNT(*) FROM USER_TABLES WHERE TABLE_NAME = 'GSVAI_AI_OBSERVABILITY'
            """
        )
        exists = cursor.fetchone()[0] > 0

        if not exists:
            print("Creating GSVAI_AI_OBSERVABILITY table...")
            cursor.execute(
                """
                CREATE TABLE GSVAI_AI_OBSERVABILITY (
                    ID NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                    REQUEST_ID VARCHAR2(64) UNIQUE,
                    CREATED_AT TIMESTAMP DEFAULT SYSTIMESTAMP,
                    PROVIDER VARCHAR2(64),
                    MODEL VARCHAR2(128),
                    SERVING_MODE VARCHAR2(32),
                    INPUT_TOKENS NUMBER DEFAULT 0,
                    OUTPUT_TOKENS NUMBER DEFAULT 0,
                    TOTAL_TOKENS NUMBER DEFAULT 0,
                    LATENCY_MS NUMBER(10,2),
                    STATUS VARCHAR2(32),
                    FALLBACK NUMBER(1) DEFAULT 0,
                    FALLBACK_REASON VARCHAR2(256),
                    RAG_USED NUMBER(1) DEFAULT 0,
                    RETRIEVAL_LATENCY_MS NUMBER(10,2),
                    RETRIEVAL_COUNT NUMBER DEFAULT 0,
                    CITATION_COUNT NUMBER DEFAULT 0,
                    ROUTE VARCHAR2(64),
                    ERROR_MESSAGE VARCHAR2(512),
                    TRACE_JSON CLOB
                )
                """
            )
            print("GSVAI_AI_OBSERVABILITY table created.")

            # Create performance indexes
            try:
                cursor.execute(
                    "CREATE INDEX IDX_OBS_CREATED_AT ON GSVAI_AI_OBSERVABILITY(CREATED_AT DESC)"
                )
                cursor.execute(
                    "CREATE INDEX IDX_OBS_PROVIDER ON GSVAI_AI_OBSERVABILITY(PROVIDER)"
                )
                cursor.execute(
                    "CREATE INDEX IDX_OBS_STATUS ON GSVAI_AI_OBSERVABILITY(STATUS)"
                )
                cursor.execute(
                    "CREATE INDEX IDX_OBS_ROUTE ON GSVAI_AI_OBSERVABILITY(ROUTE)"
                )
                print("Observability indexes created.")
            except Exception as ie:
                print(f"Index creation note: {ie}")

            conn.commit()
        else:
            print("GSVAI_AI_OBSERVABILITY table already exists.")

    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    ensure_observability_table()
