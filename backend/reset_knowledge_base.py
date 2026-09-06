import os

import oracledb
from dotenv import load_dotenv


# ---------------------------------------------------------
# Environment Configuration
# ---------------------------------------------------------

load_dotenv()

DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_WALLET_PASSWORD = os.getenv("DB_WALLET_PASSWORD")
DB_WALLET_DIR = os.getenv("DB_WALLET_DIR")
DB_DSN = os.getenv("DB_DSN")


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
# Reset Knowledge Base
# ---------------------------------------------------------

def reset_knowledge_base():

    print()
    print("=" * 70)
    print("GSVAI KNOWLEDGE BASE RESET")
    print("=" * 70)
    print()
    print("WARNING:")
    print("This will DELETE all existing GSVAI documents")
    print("and all associated document chunks/vectors.")
    print()
    print("The database will be rebuilt using BGE embeddings.")
    print("=" * 70)
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
        # Show Current Counts
        # -------------------------------------------------

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM GSVAI_DOCUMENTS
            """
        )

        document_count = cursor.fetchone()[0]

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM GSVAI_DOCUMENT_CHUNKS
            """
        )

        chunk_count = cursor.fetchone()[0]

        print("Current knowledge base:")
        print(f"  Documents : {document_count}")
        print(f"  Chunks    : {chunk_count}")
        print()

        # -------------------------------------------------
        # Delete Child Records First
        # -------------------------------------------------

        print("Deleting document chunks...")

        cursor.execute(
            """
            DELETE FROM GSVAI_DOCUMENT_CHUNKS
            """
        )

        deleted_chunks = cursor.rowcount

        print(
            f"Deleted chunks: {deleted_chunks}"
        )

        # -------------------------------------------------
        # Delete Parent Records
        # -------------------------------------------------

        print("Deleting document records...")

        cursor.execute(
            """
            DELETE FROM GSVAI_DOCUMENTS
            """
        )

        deleted_documents = cursor.rowcount

        print(
            f"Deleted documents: {deleted_documents}"
        )

        # -------------------------------------------------
        # Commit
        # -------------------------------------------------

        print()
        print("Committing database reset...")

        connection.commit()

        print("Commit successful.")
        print()

        # -------------------------------------------------
        # Verify
        # -------------------------------------------------

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM GSVAI_DOCUMENTS
            """
        )

        remaining_documents = cursor.fetchone()[0]

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM GSVAI_DOCUMENT_CHUNKS
            """
        )

        remaining_chunks = cursor.fetchone()[0]

        print("=" * 70)
        print("RESET VERIFICATION")
        print("=" * 70)
        print(
            f"Remaining documents : {remaining_documents}"
        )
        print(
            f"Remaining chunks    : {remaining_chunks}"
        )
        print("=" * 70)

        if (
            remaining_documents == 0
            and remaining_chunks == 0
        ):

            print()
            print("✓ KNOWLEDGE BASE RESET SUCCESSFUL")
            print()
            print(
                "Database is ready for fresh BGE ingestion."
            )

        else:

            raise RuntimeError(
                "Reset verification failed. "
                "Records still exist."
            )

    except Exception as error:

        print()
        print("=" * 70)
        print("ERROR DURING KNOWLEDGE BASE RESET")
        print("=" * 70)
        print(f"Error: {error}")
        print()
        print("Rolling back...")
        print("=" * 70)

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

    reset_knowledge_base()