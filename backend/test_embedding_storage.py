from services.oci_embedding_service import generate_embedding
from services.oracle_db_service import get_connection
import array


print("=" * 60)
print("GSVAI - EMBEDDING + ORACLE VECTOR TEST")
print("=" * 60)


# ---------------------------------------------------------
# Test text
# ---------------------------------------------------------

text = (
    "Oracle Fusion Payables allows organizations "
    "to create and manage supplier invoices."
)

print("\nText:")
print(text)


# ---------------------------------------------------------
# Generate embedding
# ---------------------------------------------------------

print("\nGenerating OCI embedding...")

embedding = generate_embedding(text)

print("Embedding generated successfully.")
print("Vector dimensions:", len(embedding))


# ---------------------------------------------------------
# Connect to Oracle
# ---------------------------------------------------------

print("\nConnecting to Oracle Database...")

connection = get_connection()

print("Oracle Database connection successful.")


# ---------------------------------------------------------
# Insert embedding
# ---------------------------------------------------------

cursor = connection.cursor()


document_id = 4
chunk_number = 3


print("\nStoring vector in Oracle...")

# Convert OCI embedding list to FLOAT32 vector
embedding_vector = array.array("f", embedding)
cursor.execute(
    """
    UPDATE GSVAI_DOCUMENT_CHUNKS
       SET EMBEDDING = :embedding
     WHERE DOCUMENT_ID = :document_id
       AND CHUNK_NUMBER = :chunk_number
    """,
    embedding=embedding_vector,
    document_id=document_id,
    chunk_number=chunk_number,
)

print("Rows updated:", cursor.rowcount)

connection.commit()


print("Vector stored successfully.")


# ---------------------------------------------------------
# Verify
# ---------------------------------------------------------

cursor.execute(
    """
    SELECT
        CHUNK_ID,
        CHUNK_NUMBER,
        VECTOR_DIMENSION_COUNT(EMBEDDING)
    FROM GSVAI_DOCUMENT_CHUNKS
    WHERE DOCUMENT_ID = :document_id
      AND CHUNK_NUMBER = :chunk_number
    """,
    document_id=document_id,
    chunk_number=chunk_number,
)


result = cursor.fetchone()


print("\nVerification")
print("-" * 40)
print("Chunk ID          :", result[0])
print("Chunk Number      :", result[1])
print("Vector Dimensions :", result[2])


cursor.close()
connection.close()


print("\n" + "=" * 60)
print("EMBEDDING STORED SUCCESSFULLY")
print("=" * 60)