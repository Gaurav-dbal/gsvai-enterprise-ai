# pyrefly: ignore [missing-import]

import random
import time

import oci

# pyrefly: ignore [missing-import]
from oci.generative_ai_inference import GenerativeAiInferenceClient

# pyrefly: ignore [missing-import]
from oci.generative_ai_inference.models import (
    ChatDetails,
    OnDemandServingMode,
    GenericChatRequest,
    SystemMessage,
    UserMessage,
    TextContent,
)


# =========================================================
# OCI Configuration
# =========================================================

config = oci.config.from_file()

# Current GSVAI configuration uses the tenancy as the
# Generative AI compartment.
COMPARTMENT_ID = config["tenancy"]

# Gemini 2.5 Flash
MODEL_ID = "google.gemini-2.5-flash"

# OCI region from ~/.oci/config
REGION = config.get("region", "unknown")


# =========================================================
# Configuration Logging
# =========================================================

print("=" * 60)
print("GSVAI OCI GENERATIVE AI CONFIGURATION")
print("=" * 60)
print(f"OCI Region      : {REGION}")
print(f"OCI Model       : {MODEL_ID}")
print(f"OCI Compartment : {COMPARTMENT_ID}")
print("=" * 60)


# =========================================================
# OCI Generative AI Client
# =========================================================

# Disable OCI SDK internal retry strategy.
#
# We handle HTTP 429 ourselves using:
#
#   Exponential Backoff
#   +
#   Randomized Jitter
#
client = GenerativeAiInferenceClient(
    config=config,
    retry_strategy=oci.retry.NoneRetryStrategy(),
)


# =========================================================
# OCI Chat With Exponential Backoff + Randomized Jitter
# =========================================================

def _chat_with_retry(
    chat_details: ChatDetails,
    max_retries: int = 3,
    initial_delay: float = 10.0,
    max_delay: float = 60.0,
    jitter_ratio: float = 0.5,
):
    """
    Call OCI Generative AI with exponential backoff
    and randomized jitter for HTTP 429 throttling.

    Retry sequence:

        Attempt 1
            |
            | 429
            v
        Base delay = 10 sec
        Random jitter = 0-50%
            |
            v
        Retry

        Attempt 2
            |
            | 429
            v
        Base delay = 20 sec
        Random jitter = 0-50%
            |
            v
        Retry

        Attempt 3
            |
            | 429
            v
        Stop

    Example:

        Attempt 1 -> 429
        wait approximately 10-15 sec

        Attempt 2 -> 429
        wait approximately 20-30 sec

        Attempt 3 -> 429
        stop

    Only HTTP 429 errors are retried.

    Other OCI errors are raised immediately.
    """

    for attempt in range(1, max_retries + 1):

        request_start = time.time()

        print()
        print("-" * 60)
        print("OCI GENERATIVE AI REQUEST")
        print("-" * 60)
        print(f"Region  : {REGION}")
        print(f"Model   : {MODEL_ID}")
        print(
            f"Attempt : {attempt}/{max_retries}"
        )

        try:

            response = client.chat(
                chat_details=chat_details
            )

            elapsed = time.time() - request_start

            print(
                f"OCI Generative AI request successful "
                f"in {elapsed:.2f} seconds."
            )

            return response

        except oci.exceptions.ServiceError as e:

            elapsed = time.time() - request_start

            print(
                f"OCI request failed after "
                f"{elapsed:.2f} seconds."
            )

            print(
                f"HTTP Status: {e.status}"
            )

            # =================================================
            # HTTP 429 - Throttling
            # =================================================

            if e.status == 429:

                print(
                    "OCI Generative AI returned HTTP 429."
                )

                print(
                    "OCI tenancy/model is currently "
                    "being throttled."
                )

                # -------------------------------------------------
                # Maximum attempts reached
                # -------------------------------------------------

                if attempt == max_retries:

                    print(
                        "Maximum retry attempts reached."
                    )

                    print(
                        "Stopping OCI request retries."
                    )

                    raise RuntimeError(
                        "OCI Generative AI is currently "
                        "throttling requests (HTTP 429). "
                        "The request was stopped after "
                        "maximum retry attempts."
                    ) from e

                # -------------------------------------------------
                # Exponential Backoff
                # -------------------------------------------------

                exponential_delay = (
                    initial_delay
                    * (2 ** (attempt - 1))
                )

                # -------------------------------------------------
                # Apply maximum delay
                # -------------------------------------------------

                exponential_delay = min(
                    exponential_delay,
                    max_delay,
                )

                # -------------------------------------------------
                # Randomized Jitter
                # -------------------------------------------------
                #
                # Example with jitter_ratio = 0.5:
                #
                # 10 sec base -> 10-15 sec
                # 20 sec base -> 20-30 sec
                # 40 sec base -> 40-60 sec
                #
                jitter = random.uniform(
                    0,
                    exponential_delay * jitter_ratio,
                )

                retry_delay = min(
                    exponential_delay + jitter,
                    max_delay,
                )

                print(
                    f"Base backoff : "
                    f"{exponential_delay:.2f} sec"
                )

                print(
                    f"Random jitter: "
                    f"{jitter:.2f} sec"
                )

                print(
                    f"Total delay  : "
                    f"{retry_delay:.2f} sec"
                )

                print(
                    "Waiting before next OCI request..."
                )

                time.sleep(retry_delay)

                continue

            # =================================================
            # Other OCI Errors
            # =================================================

            print(
                "OCI Generative AI request failed "
                f"with HTTP {e.status}."
            )

            print(
                "This error is not retryable."
            )

            raise

    raise RuntimeError(
        "OCI Generative AI request failed "
        "after retries."
    )


# =========================================================
# Extract Generic Chat Response
# =========================================================

def _extract_response_text(response) -> str:
    """
    Extract text from OCI GenericChatResponse.

    Expected structure:

        response
            -> data
                -> chat_response
                    -> choices
                        -> message
                            -> content
                                -> text
    """

    choices = response.data.chat_response.choices

    if not choices:

        raise RuntimeError(
            "OCI Generative AI returned "
            "an empty response."
        )

    message = choices[0].message

    if not message.content:

        raise RuntimeError(
            "OCI Generative AI returned "
            "an empty message."
        )

    text_parts = []

    for content in message.content:

        if hasattr(content, "text") and content.text:

            text_parts.append(
                content.text
            )

    if not text_parts:

        raise RuntimeError(
            "OCI Generative AI response "
            "contained no text."
        )

    return "".join(text_parts)


# =========================================================
# Generate RAG Answer
# =========================================================

def generate_answer(
    question: str,
    context: str,
) -> str:
    """
    Generate an answer using retrieved enterprise
    knowledge-base context.

    The LLM is instructed to remain grounded in
    the retrieved context and avoid hallucination.
    """

    system_prompt = """
You are GSVAI, an enterprise AI assistant.

Your task is to answer the user's question using the
knowledge context retrieved from the enterprise knowledge base.

IMPORTANT GROUNDING RULES:

1. Use the provided knowledge context as the primary
   and authoritative source.

2. Do NOT invent, assume, guess, or infer information
   that is not supported by the provided context.

3. If the context does not contain enough information
   to answer the question, respond exactly with:

   "I could not find this information in the knowledge base."

4. Do not use your general world knowledge to fill gaps
   in the enterprise knowledge base.

5. Give a clear and concise answer.

6. If the question cannot be answered from the supplied
   context, do not attempt to provide an alternative
   unsupported answer.

7. Do not mention internal implementation details such as
   embeddings, vector distances, or RAG unless the user asks.

8. When the context contains the answer, answer using
   only the information supported by that context.
"""

    # =====================================================
    # User Prompt
    # =====================================================

    user_prompt = f"""
Knowledge Context
-----------------
{context}

User Question
-------------
{question}

Answer
------
"""

    # =====================================================
    # Messages
    # =====================================================

    messages = [
        SystemMessage(
            content=[
                TextContent(
                    text=system_prompt
                )
            ]
        ),
        UserMessage(
            content=[
                TextContent(
                    text=user_prompt
                )
            ]
        ),
    ]

    # =====================================================
    # Gemini Generic Chat Request
    # =====================================================

    chat_request = GenericChatRequest(
        api_format="GENERIC",
        messages=messages,
        max_tokens=400,
        temperature=0.2,
        reasoning_effort="LOW",
    )

    # =====================================================
    # Chat Details
    # =====================================================

    chat_details = ChatDetails(
        compartment_id=COMPARTMENT_ID,
        serving_mode=OnDemandServingMode(
            model_id=MODEL_ID
        ),
        chat_request=chat_request,
    )

    # =====================================================
    # OCI Request
    # =====================================================

    response = _chat_with_retry(
        chat_details=chat_details
    )

    # =====================================================
    # Extract Answer
    # =====================================================

    return _extract_response_text(
        response
    )


# =========================================================
# Generate General AI Answer
# No RAG / General Query
# =========================================================

def generate_general_answer(
    question: str,
) -> str:
    """
    Generate a general AI answer without RAG context.
    """

    system_prompt = """
You are GSVAI, a premier enterprise AI assistant
powered by OCI Generative AI.

Your task is to answer the user's question accurately,
concisely, and professionally.

Rules:

1. Provide a direct, helpful, and well-structured answer.

2. If explaining technical concepts, architecture,
   or business processes, use clear points.

3. Maintain a professional enterprise tone.

4. Do not mention that you searched a knowledge base
   or that information was missing unless relevant.

5. Do not invent specific enterprise information
   that has not been provided.
"""

    # =====================================================
    # User Prompt
    # =====================================================

    user_prompt = f"""
User Question
-------------
{question}

Answer
------
"""

    # =====================================================
    # Messages
    # =====================================================

    messages = [
        SystemMessage(
            content=[
                TextContent(
                    text=system_prompt
                )
            ]
        ),
        UserMessage(
            content=[
                TextContent(
                    text=user_prompt
                )
            ]
        ),
    ]

    # =====================================================
    # Gemini Generic Chat Request
    # =====================================================

    chat_request = GenericChatRequest(
        api_format="GENERIC",
        messages=messages,
        max_tokens=450,
        temperature=0.3,
        reasoning_effort="LOW",
    )

    # =====================================================
    # Chat Details
    # =====================================================

    chat_details = ChatDetails(
        compartment_id=COMPARTMENT_ID,
        serving_mode=OnDemandServingMode(
            model_id=MODEL_ID
        ),
        chat_request=chat_request,
    )

    # =====================================================
    # OCI Request
    # =====================================================

    response = _chat_with_retry(
        chat_details=chat_details
    )

    # =====================================================
    # Extract Answer
    # =====================================================

    return _extract_response_text(
        response
    )