import os
import array
import time

import oracledb
from dotenv import load_dotenv

from services.oci_embedding_service import model


# ---------------------------------------------------------
# Environment Configuration
# ---------------------------------------------------------

load_dotenv()

DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_WALLET_PASSWORD = os.getenv("DB_WALLET_PASSWORD")
DB_WALLET_DIR = os.getenv("DB_WALLET_DIR")
DB_DSN = os.getenv("DB_DSN")

EXPECTED_DIMENSIONS = 1024

# Number of chunks processed by BGE at once.
# 32 is a safe starting point for most laptops.
BATCH_SIZE = 32

# Commit after this many chunks.
COMMIT_BATCH_SIZE = 128


# ---------------------------------------------------------
# Validate Configuration
# ---------------------------------------------------------

required_config = {
    "DB_USER": DB_USER,
    "DB_PASSWORD": DB_PASSWORD,
    "DB_WALLET_PASSWORD": DB_WALLET_PASSWORD,
    "DB_WALLET_DIR": DB_WALLET_DIR,
    "DB_DSN": DB_DSN,
}

missing = [
    key
    for key, value in required_config.items()
    if not value
]

if missing:
    raise RuntimeError(
        f"Missing database configuration: {', '.join(missing)}"
    )


# ---------------------------------------------------------
# Convert Oracle LOB to Python String
# ---------------------------------------------------------

def lob_to_text(value):

    if value is None:
        raise ValueError("CHUNK_TEXT is NULL")

    if hasattr(value, "read"):
        value = value.read()

    return str(value)


# ---------------------------------------------------------
# Re-index Existing Embeddings
# ---------------------------------------------------------

def reindex_embeddings():

    print()
    print("=" * 75)
    print("GSVAI FAST EMBEDDING MIGRATION")
    print("=" * 75)
    print("Old embedding provider : OCI Cohere Embed v4")
    print("New embedding provider : BAAI/bge-large-en-v1.5")
    print(f"Vector dimensions      : {EXPECTED_DIMENSIONS}")
    print(f"BGE batch size         : {BATCH_SIZE}")
    print(f"Commit batch size      : {COMMIT_BATCH_SIZE}")
    print("=" * 75)
    print()

    # -----------------------------------------------------
    # Connect Oracle
    # -----------------------------------------------------

    print("Connecting to Oracle...")

    connection = oracledb.connect(
        user=DB_USER,
        password=DB_PASSWORD,
        dsn=DB_DSN,
        config_dir=DB_WALLET_DIR,
        wallet_location=DB_WALLET_DIR,
        wallet_password=DB_WALLET_PASSWORD,
    )

    print("Oracle database connection successful.")
    print()

    cursor = connection.cursor()

    try:

        # -------------------------------------------------
        # Count Chunks
        # -------------------------------------------------

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM GSVAI_DOCUMENT_CHUNKS
            """
        )

        total_chunks = cursor.fetchone()[0]

        print(f"Total chunks to migrate: {total_chunks}")
        print()

        if total_chunks == 0:
            print("No chunks found.")
            return

        # -------------------------------------------------
        # Fetch Existing Chunks
        # -------------------------------------------------

        print("Loading chunks from Oracle...")

        cursor.execute(
            """
            SELECT
                CHUNK_ID,
                DOCUMENT_ID,
                CHUNK_NUMBER,
                CHUNK_TEXT
            FROM GSVAI_DOCUMENT_CHUNKS
            ORDER BY CHUNK_ID
            """
        )

        rows = cursor.fetchall()

        print(f"Loaded {len(rows)} chunks.")
        print()

        # -------------------------------------------------
        # Migration Counters
        # -------------------------------------------------

        migrated = 0
        start_time = time.time()

        # -------------------------------------------------
        # Process Batches
        # -------------------------------------------------

        for batch_start in range(
            0,
            len(rows),
            BATCH_SIZE
        ):

            batch = rows[
                batch_start:
                batch_start + BATCH_SIZE
            ]

            batch_number = (
                batch_start // BATCH_SIZE
            ) + 1

            total_batches = (
                (len(rows) + BATCH_SIZE - 1)
                // BATCH_SIZE
            )

            print(
                f"Batch {batch_number}/{total_batches} "
                f"| chunks "
                f"{batch_start + 1}-"
                f"{min(batch_start + BATCH_SIZE, len(rows))}"
            )

            # -------------------------------------------------
            # Prepare Text
            # -------------------------------------------------

            texts = []

            for (
                chunk_id,
                document_id,
                chunk_number,
                chunk_text
            ) in batch:

                text = lob_to_text(chunk_text)

                if not text.strip():
                    raise ValueError(
                        f"Empty CHUNK_TEXT for "
                        f"CHUNK_ID {chunk_id}"
                    )

                texts.append(text)

            # -------------------------------------------------
            # Generate BGE Embeddings in Batch
            # -------------------------------------------------

            embedding_start = time.time()

            embeddings = model.encode(
                texts,
                batch_size=BATCH_SIZE,
                normalize_embeddings=True,
                show_progress_bar=False,
            )

            embedding_time = (
                time.time() - embedding_start
            )

            # -------------------------------------------------
            # Validate Embeddings
            # -------------------------------------------------

            if len(embeddings) != len(batch):
                raise ValueError(
                    "Number of embeddings does not "
                    "match number of chunks."
                )

            update_rows = []

            for row, embedding in zip(
                batch,
                embeddings
            ):

                chunk_id = row[0]

                if len(embedding) != EXPECTED_DIMENSIONS:
                    raise ValueError(
                        f"Embedding dimension mismatch "
                        f"for CHUNK_ID {chunk_id}. "
                        f"Expected {EXPECTED_DIMENSIONS}, "
                        f"received {len(embedding)}."
                    )

                vector = array.array(
                    "f",
                    embedding.tolist()
                )

                update_rows.append(
                    {
                        "embedding": vector,
                        "chunk_id": chunk_id,
                    }
                )

            # -------------------------------------------------
            # Batch Update Oracle
            # -------------------------------------------------

            update_start = time.time()

            cursor.executemany(
                """
                UPDATE GSVAI_DOCUMENT_CHUNKS
                SET EMBEDDING = :embedding
                WHERE CHUNK_ID = :chunk_id
                """,
                update_rows,
            )

            update_time = (
                time.time() - update_start
            )

            migrated += len(batch)

            # -------------------------------------------------
            # Commit Periodically
            # -------------------------------------------------

            if (
                migrated % COMMIT_BATCH_SIZE == 0
                or migrated == total_chunks
            ):

                connection.commit()

                elapsed = (
                    time.time() - start_time
                )

                rate = (
                    migrated / elapsed
                    if elapsed > 0
                    else 0
                )

                remaining = (
                    total_chunks - migrated
                )

                eta = (
                    remaining / rate
                    if rate > 0
                    else 0
                )

                print(
                    f"  ✓ Committed "
                    f"{migrated}/{total_chunks} "
                    f"| BGE: {embedding_time:.2f}s "
                    f"| Oracle: {update_time:.2f}s "
                    f"| Rate: {rate:.2f} chunks/s "
                    f"| ETA: {eta:.1f}s"
                )

            else:

                print(
                    f"  ✓ Processed "
                    f"{migrated}/{total_chunks} "
                    f"| BGE: {embedding_time:.2f}s "
                    f"| Oracle: {update_time:.2f}s"
                )

        # -----------------------------------------------------
        # Final Verification
        # -----------------------------------------------------

        print()
        print("Running migration verification...")

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM GSVAI_DOCUMENT_CHUNKS
            WHERE EMBEDDING IS NOT NULL
            """
        )

        embedded_count = cursor.fetchone()[0]

        # -----------------------------------------------------
        # Final Summary
        # -----------------------------------------------------

        elapsed = time.time() - start_time

        print()
        print("=" * 75)
        print("EMBEDDING MIGRATION COMPLETED")
        print("=" * 75)
        print(f"Total chunks       : {total_chunks}")
        print(f"Migrated           : {migrated}")
        print(f"Embeddings present : {embedded_count}")
        print(f"Time               : {elapsed:.1f} seconds")

        if elapsed > 0:
            print(
                f"Average speed      : "
                f"{migrated / elapsed:.2f} chunks/sec"
            )

        print("=" * 75)

    except Exception as error:

        print()
        print("=" * 75)
        print("ERROR DURING EMBEDDING MIGRATION")
        print("=" * 75)
        print(f"Error: {error}")
        print()
        print(
            "Rolling back the current uncommitted batch..."
        )
        print("=" * 75)

        connection.rollback()

        raise

    finally:

        cursor.close()
        connection.close()

        print()
        print("Oracle database connection closed.")


# ---------------------------------------------------------
# Main
# ---------------------------------------------------------

if __name__ == "__main__":
    reindex_embeddings()