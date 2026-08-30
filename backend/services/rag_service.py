from services.semantic_search_service import search_similar_chunks
from services.oci_llm_service import generate_answer


# --------------------------------------------------
# Extract Page Number
# --------------------------------------------------

def extract_page_number(text: str):

    if not text:
        return None

    marker = "[Source Page:"

    if marker not in text:
        return None

    try:
        start = text.index(marker) + len(marker)
        end = text.index("]", start)

        page_number = text[start:end].strip()

        return int(page_number)

    except (ValueError, IndexError):
        return None


# --------------------------------------------------
# --------------------------------------------------
# Build RAG Context from Retrieved Chunks
# --------------------------------------------------

def build_rag_context_from_results(results):
    """
    Assembles retrieved chunks into LLM prompt context and UI sources list.
    """
    if not results:
        return "", []

    context_parts = []
    sources = []

    for index, result in enumerate(results, start=1):
        document_id_val = result["document_id"]
        chunk_number = result["chunk_number"]
        chunk_text = result["chunk_text"]
        distance = result["distance"]

        # Extract page number from chunk
        page_number = extract_page_number(chunk_text)

        # Context for LLM
        source = f"""
[Source {index}]

Document ID: {document_id_val}

Page Number: {page_number}

Chunk Number: {chunk_number}

Distance: {distance}

{chunk_text}
""".strip()

        context_parts.append(source)

        # Source metadata for UI
        sources.append({
            "source_number": index,
            "document_id": document_id_val,
            "document_name": result["document_name"],
            "page_number": page_number,
            "chunk_number": chunk_number,
            "distance": distance,
            "text": chunk_text,
        })

    context = "\n\n".join(context_parts)
    print(f"RAG context created from {len(results)} chunk(s).")
    return context, sources


# --------------------------------------------------
# Build RAG Context
# --------------------------------------------------

def build_rag_context(
    query: str,
    top_k: int = 5,
    document_id: int = None,
):
    print("Building RAG context...")
    results = search_similar_chunks(
        query,
        top_k=top_k,
        document_id=document_id,
    )
    if not results:
        print("No relevant chunks found.")
        return "", []

    return build_rag_context_from_results(results)



# --------------------------------------------------
# Complete RAG Question
# --------------------------------------------------

def answer_question(
    question: str,
    top_k: int = 5,
    document_id: int = None,
):

    print()

    print("Starting RAG pipeline...")


    # --------------------------------------------------
    # Step 1: Retrieve context
    # --------------------------------------------------

    context, sources = build_rag_context(
        question,
        top_k=top_k,
        document_id=document_id,
    )


    if not context:

        return {

            "answer":
                "I could not find relevant information "
                "in the knowledge base.",

            "sources": []

        }


    # --------------------------------------------------
    # Step 2: Send context + question to LLM
    # --------------------------------------------------

    print(
        "Sending RAG context to OCI Cohere..."
    )


    answer = generate_answer(

        question=question,

        context=context

    )


    print(
        "RAG answer generated successfully."
    )


    # --------------------------------------------------
    # Step 3: Return answer + sources
    # --------------------------------------------------

    return {

        "answer": answer,

        "sources": sources

    }