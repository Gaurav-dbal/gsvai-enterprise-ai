import os
import array
# pyrefly: ignore [missing-import]
import oracledb
# pyrefly: ignore [missing-import]
import pymupdf

from dotenv import load_dotenv

from services.oci_embedding_service import generate_embedding


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
# Extract PDF Text
# ---------------------------------------------------------

def extract_pdf_pages(file_path: str):

    print("Opening PDF...")

    document = pymupdf.open(file_path)

    pages = []

    try:

        for page_number, page in enumerate(
            document,
            start=1
        ):

            text = page.get_text("text").strip()

            if text:

                pages.append({
                    "page_number": page_number,
                    "text": text
                })

    finally:

        document.close()

    print(
        f"Extracted text from {len(pages)} page(s)."
    )

    return pages


# ---------------------------------------------------------
# Create Chunks
# ---------------------------------------------------------

def create_chunks(
    pages,
    words_per_chunk: int = 400,
    overlap_words: int = 50
):

    chunks = []

    chunk_number = 1

    for page in pages:

        page_number = page["page_number"]

        words = page["text"].split()

        start = 0

        while start < len(words):

            end = start + words_per_chunk

            chunk_words = words[start:end]

            if not chunk_words:
                break

            chunk_text = " ".join(chunk_words)

            # Keep page information inside the chunk
            chunk_text = (
                f"[Source Page: {page_number}]\n\n"
                f"{chunk_text}"
            )

            chunks.append({
                "chunk_number": chunk_number,
                "page_number": page_number,
                "text": chunk_text
            })

            chunk_number += 1

            start += (
                words_per_chunk - overlap_words
            )

    print(
        f"Created {len(chunks)} chunk(s)."
    )

    return chunks


# ---------------------------------------------------------
# Generate Document ID
# ---------------------------------------------------------

def get_next_document_id(cursor):

    cursor.execute(
        """
        SELECT NVL(MAX(DOCUMENT_ID), 0) + 1
        FROM GSVAI_DOCUMENTS
        """
    )

    return cursor.fetchone()[0]


# ---------------------------------------------------------
# Generate Chunk ID
# ---------------------------------------------------------

def get_next_chunk_id(cursor):

    cursor.execute(
        """
        SELECT NVL(MAX(CHUNK_ID), 0) + 1
        FROM GSVAI_DOCUMENT_CHUNKS
        """
    )

    return cursor.fetchone()[0]


# ---------------------------------------------------------
# Ingest PDF
# ---------------------------------------------------------

def ingest_pdf(file_path: str):

    filename = os.path.basename(file_path)

    print()
    print("=" * 60)
    print("GSVAI PDF INGESTION")
    print("=" * 60)

    print(
        f"File: {filename}"
    )

    # -----------------------------------------------------
    # 1. Extract PDF
    # -----------------------------------------------------

    pages = extract_pdf_pages(
        file_path
    )

    if not pages:

        raise ValueError(
            "No readable text found in the PDF."
        )

    # -----------------------------------------------------
    # 2. Create chunks
    # -----------------------------------------------------

    chunks = create_chunks(
        pages
    )

    if not chunks:

        raise ValueError(
            "No chunks could be created from the PDF."
        )

    # -----------------------------------------------------
    # 3. Connect Oracle
    # -----------------------------------------------------

    print(
        "Connecting to Oracle..."
    )

    connection = oracledb.connect(
        user=DB_USER,
        password=DB_PASSWORD,
        dsn=DB_DSN,
        config_dir=DB_WALLET_DIR,
        wallet_location=DB_WALLET_DIR,
        wallet_password=DB_WALLET_PASSWORD,
    )

    print(
        "Oracle database connection successful."
    )

    cursor = connection.cursor()

    try:

        # -------------------------------------------------
        # 4. Create Parent Document
        # -------------------------------------------------

        document_id = get_next_document_id(
            cursor
        )

        print(
            f"Creating document record. "
            f"DOCUMENT_ID = {document_id}"
        )

        cursor.execute(
            """
            INSERT INTO GSVAI_DOCUMENTS
            (
                DOCUMENT_ID,
                DOCUMENT_NAME,
                DOCUMENT_TYPE,
                SOURCE,
                CREATED_AT,
                STATUS
            )
            VALUES
            (
                :document_id,
                :document_name,
                :document_type,
                :source,
                SYSTIMESTAMP,
                :status
            )
            """,
            document_id=document_id,
            document_name=filename,
            document_type="PDF",
            source=filename,
            status="PROCESSING"
        )

        print(
            "Parent document created successfully."
        )

        # -------------------------------------------------
        # 5. Insert Chunks + Embeddings
        # -------------------------------------------------

        for index, chunk in enumerate(
            chunks,
            start=1
        ):

            chunk_number = chunk["chunk_number"]

            chunk_text = chunk["text"]

            print()
            print(
                f"Processing chunk "
                f"{index}/{len(chunks)}..."
            )

            # ---------------------------------------------
            # Generate OCI Embedding
            # ---------------------------------------------

            print(
                "Generating OCI embedding..."
            )

            embedding = generate_embedding(
                chunk_text
            )

            print(
                f"Embedding dimensions: "
                f"{len(embedding)}"
            )

            if len(embedding) != 1024:

                raise ValueError(
                    "Embedding dimension mismatch. "
                    f"Expected 1024, received "
                    f"{len(embedding)}."
                )

            vector = array.array(
                "f",
                embedding
            )

            # ---------------------------------------------
            # Generate Chunk ID
            # ---------------------------------------------

            chunk_id = get_next_chunk_id(
                cursor
            )

            # ---------------------------------------------
            # Insert Child Record
            # ---------------------------------------------

            cursor.execute(
                """
                INSERT INTO GSVAI_DOCUMENT_CHUNKS
                (
                    CHUNK_ID,
                    DOCUMENT_ID,
                    CHUNK_TEXT,
                    CHUNK_NUMBER,
                    CREATED_AT,
                    EMBEDDING
                )
                VALUES
                (
                    :chunk_id,
                    :document_id,
                    :chunk_text,
                    :chunk_number,
                    SYSTIMESTAMP,
                    :embedding
                )
                """,
                chunk_id=chunk_id,
                document_id=document_id,
                chunk_text=chunk_text,
                chunk_number=chunk_number,
                embedding=vector
            )

            print(
                f"Chunk {chunk_number} stored successfully."
            )

        # -------------------------------------------------
        # 6. Update Document Status
        # -------------------------------------------------

        cursor.execute(
            """
            UPDATE GSVAI_DOCUMENTS
            SET STATUS = 'INDEXED'
            WHERE DOCUMENT_ID = :document_id
            """,
            document_id=document_id
        )

        # -------------------------------------------------
        # 7. Commit Everything
        # -------------------------------------------------

        connection.commit()

        print()
        print("=" * 60)
        print("PDF INGESTION COMPLETED")
        print("=" * 60)

        print(
            f"Document ID : {document_id}"
        )

        print(
            f"Pages       : {len(pages)}"
        )

        print(
            f"Chunks      : {len(chunks)}"
        )

        print(
            "Status      : INDEXED"
        )

        print("=" * 60)

        return {
            "document_id": document_id,
            "filename": filename,
            "pages": len(pages),
            "chunks": len(chunks),
            "status": "INDEXED"
        }

    except Exception:

        print(
            "ERROR during ingestion."
        )

        print(
            "Rolling back transaction..."
        )

        connection.rollback()

        raise

    finally:

        cursor.close()

        connection.close()

        print(
            "Oracle database connection closed."
        )


# ---------------------------------------------------------
# Ingest Document from Extracted Pages (OCI OCR / Parsed)
# ---------------------------------------------------------

def ingest_document_pages(
    filename: str,
    pages: list,
    document_type: str = "PDF"
):
    """
    Ingests pre-extracted document pages (e.g. from OCI Document Understanding)
    into GSVAI_DOCUMENTS and GSVAI_DOCUMENT_CHUNKS with embeddings.
    """
    print()
    print("=" * 60)
    print("GSVAI KNOWLEDGE INGESTION (FROM EXTRACTED OCR PAGES)")
    print("=" * 60)
    print(f"File: {filename}, Pages: {len(pages)}")

    if not pages:
        raise ValueError("No pages provided for ingestion.")

    # 1. Create chunks
    chunks = create_chunks(pages)

    if not chunks:
        raise ValueError("No chunks could be created from document pages.")

    # 2. Connect Oracle
    connection = oracledb.connect(
        user=DB_USER,
        password=DB_PASSWORD,
        dsn=DB_DSN,
        config_dir=DB_WALLET_DIR,
        wallet_location=DB_WALLET_DIR,
        wallet_password=DB_WALLET_PASSWORD,
    )
    cursor = connection.cursor()

    try:
        # 3. Create Parent Document Record
        document_id = get_next_document_id(cursor)
        print(f"Creating document record in GSVAI_DOCUMENTS: DOCUMENT_ID = {document_id}")

        cursor.execute(
            """
            INSERT INTO GSVAI_DOCUMENTS
            (
                DOCUMENT_ID,
                DOCUMENT_NAME,
                DOCUMENT_TYPE,
                SOURCE,
                CREATED_AT,
                STATUS
            )
            VALUES
            (
                :document_id,
                :document_name,
                :document_type,
                :source,
                SYSTIMESTAMP,
                :status
            )
            """,
            document_id=document_id,
            document_name=filename,
            document_type=document_type,
            source=filename,
            status="PROCESSING"
        )

        # 4. Generate Embeddings and Insert Chunks
        for index, chunk in enumerate(chunks, start=1):
            chunk_number = chunk["chunk_number"]
            chunk_text = chunk["text"]
            embedding = generate_embedding(chunk_text)

            if len(embedding) != 1024:
                raise ValueError(
                    f"Embedding dimension mismatch. Expected 1024, received {len(embedding)}."
                )

            vector = array.array("f", embedding)
            chunk_id = get_next_chunk_id(cursor)

            cursor.execute(
                """
                INSERT INTO GSVAI_DOCUMENT_CHUNKS
                (
                    CHUNK_ID,
                    DOCUMENT_ID,
                    CHUNK_TEXT,
                    CHUNK_NUMBER,
                    CREATED_AT,
                    EMBEDDING
                )
                VALUES
                (
                    :chunk_id,
                    :document_id,
                    :chunk_text,
                    :chunk_number,
                    SYSTIMESTAMP,
                    :embedding
                )
                """,
                chunk_id=chunk_id,
                document_id=document_id,
                chunk_text=chunk_text,
                chunk_number=chunk_number,
                embedding=vector
            )

        # 5. Mark Document Status as INDEXED
        cursor.execute(
            """
            UPDATE GSVAI_DOCUMENTS
            SET STATUS = 'INDEXED'
            WHERE DOCUMENT_ID = :document_id
            """,
            document_id=document_id
        )

        connection.commit()

        print(f"Document ID {document_id} ({filename}) successfully indexed into Oracle Vector DB with {len(chunks)} chunks.")
        print("=" * 60)

        return {
            "document_id": document_id,
            "filename": filename,
            "pages": len(pages),
            "chunks": len(chunks),
            "status": "INDEXED"
        }

    except Exception:
        print("ERROR during knowledge ingestion. Rolling back...")
        connection.rollback()
        raise

    finally:
        cursor.close()
        connection.close()