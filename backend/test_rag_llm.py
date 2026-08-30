# pyrefly: ignore [missing-import]
from services.rag_service import answer_question


print("=" * 60)
print("GSVAI - COMPLETE RAG + LLM TEST")
print("=" * 60)


# --------------------------------------------------
# User Question
# --------------------------------------------------

question = "How do I create a supplier invoice?"

print()
print("USER QUESTION")
print("-" * 60)
print(question)


# --------------------------------------------------
# Run RAG Pipeline
# --------------------------------------------------

print()
print("Running RAG pipeline...")
print()

answer = answer_question(
    question,
    top_k=5
)


# --------------------------------------------------
# Final Answer
# --------------------------------------------------

print()
print("=" * 60)
print("FINAL RAG ANSWER")
print("=" * 60)

print()
print(answer)

print()
print("=" * 60)
print("GSVAI RAG TEST COMPLETE")
print("=" * 60)