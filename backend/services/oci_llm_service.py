# pyrefly: ignore [missing-import]

# pyrefly: ignore [missing-import]
import oci

# pyrefly: ignore [missing-import]
from oci.generative_ai_inference import GenerativeAiInferenceClient

# pyrefly: ignore [missing-import]
from oci.generative_ai_inference.models import (
    ChatDetails,
    OnDemandServingMode,
    CohereChatRequest,
)


# ---------------------------------------------------------
# OCI Configuration
# ---------------------------------------------------------

config = oci.config.from_file()

COMPARTMENT_ID = config["tenancy"]

MODEL_ID = "cohere.command-a-03-2025"


# ---------------------------------------------------------
# OCI Generative AI Client
# ---------------------------------------------------------

client = GenerativeAiInferenceClient(
    config=config
)


# ---------------------------------------------------------
# Generate RAG Answer
# ---------------------------------------------------------

def generate_answer(question: str, context: str) -> str:

    prompt = f"""
You are GSVAI, an enterprise AI assistant.

Your task is to answer the user's question using the
knowledge context retrieved from the enterprise knowledge base.

Rules:

1. Use the provided knowledge context as the primary source.
2. Do not invent or assume information that is not present
   in the context.
3. If the context does not contain enough information to answer
   the question, say:
   "I could not find this information in the knowledge base."
4. Give a clear and concise answer.
5. Do not mention internal implementation details such as
   embeddings, vector distances, or RAG unless the user asks.

Knowledge Context
-----------------
{context}

User Question
-------------
{question}

Answer
------
"""

    chat_request = CohereChatRequest(
        message=prompt,
        max_tokens=400,
        temperature=0.2,
    )

    chat_details = ChatDetails(
        compartment_id=COMPARTMENT_ID,
        serving_mode=OnDemandServingMode(
            model_id=MODEL_ID
        ),
        chat_request=chat_request,
    )

    response = client.chat(
        chat_details=chat_details
    )

    return response.data.chat_response.text


# ---------------------------------------------------------
# Generate General AI Answer (No RAG / General Query)
# ---------------------------------------------------------

def generate_general_answer(question: str) -> str:
    """
    Generates a direct, professional enterprise AI answer for
    general knowledge, technology, or business questions.
    """
    prompt = f"""
You are GSVAI, a premier enterprise AI assistant powered by OCI Generative AI.

Your task is to answer the user's question accurately, concisely, and professionally.

Rules:
1. Provide a direct, helpful, and well-structured answer.
2. If explaining technical concepts, architecture, or business processes, use clear points.
3. Maintain a professional enterprise tone.
4. Do NOT mention that you searched a knowledge base or that information was missing unless relevant.

User Question
-------------
{question}

Answer
------
"""

    chat_request = CohereChatRequest(
        message=prompt,
        max_tokens=450,
        temperature=0.3,
    )

    chat_details = ChatDetails(
        compartment_id=COMPARTMENT_ID,
        serving_mode=OnDemandServingMode(
            model_id=MODEL_ID
        ),
        chat_request=chat_request,
    )

    response = client.chat(
        chat_details=chat_details
    )

    return response.data.chat_response.text