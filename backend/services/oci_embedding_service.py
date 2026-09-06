from sentence_transformers import SentenceTransformer


MODEL_ID = "BAAI/bge-large-en-v1.5"


# ---------------------------------------------------------
# Local Embedding Model
# ---------------------------------------------------------

model = SentenceTransformer(MODEL_ID)


# ---------------------------------------------------------
# Generate Embedding
# ---------------------------------------------------------

def generate_embedding(text: str):
    """
    Generate a 1024-dimensional embedding locally.

    This replaces OCI Cohere Embed v4.0 while keeping
    compatibility with the existing Oracle Vector Search
    configuration.
    """

    embedding = model.encode(
        text,
        normalize_embeddings=True
    )

    return embedding.tolist()