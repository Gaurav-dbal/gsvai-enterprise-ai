from services.semantic_search_service import search_similar_chunks


print("=" * 60)
print("GSVAI - SEMANTIC SEARCH TEST")
print("=" * 60)


# --------------------------------------------------
# 1. User question
# --------------------------------------------------

query = "How do I create a supplier invoice?"

print()
print("User Question:")
print(query)
print()


# --------------------------------------------------
# 2. Perform semantic search
# --------------------------------------------------

print("Searching Oracle Vector Database...")
print()

results = search_similar_chunks(query, top_k=5)


# --------------------------------------------------
# 3. Display search results
# --------------------------------------------------

print()
print("=" * 60)
print("SEARCH RESULTS")
print("=" * 60)


if not results:

    print("No matching chunks found.")

else:

    for index, row in enumerate(results, start=1):

        document_id = row["document_id"]
        chunk_number = row["chunk_number"]
        chunk_text = row["chunk_text"]
        distance = row["distance"]

        print()
        print(f"Result #{index}")
        print("-" * 40)

        print(f"Document ID  : {document_id}")
        print(f"Chunk Number : {chunk_number}")
        print(f"Distance     : {distance}")
        print(f"Text         : {chunk_text}")


# --------------------------------------------------
# 4. Test completed
# --------------------------------------------------

print()
print("=" * 60)
print("SEMANTIC SEARCH TEST COMPLETE")
print("=" * 60)