# pyrefly: ignore [missing-import]

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


# ---------------------------------------------------------
# OCI Configuration
# ---------------------------------------------------------

config = oci.config.from_file()

COMPARTMENT_ID = config["tenancy"]

# Gemini 2.5 Flash
MODEL_ID = "google.gemini-2.5-flash"


# ---------------------------------------------------------
# OCI Generative AI Client
# ---------------------------------------------------------

# Disable the OCI SDK's internal retry strategy.
# Our application-level retry logic below handles HTTP 429.
client = GenerativeAiInferenceClient(
    config=config,
    retry_strategy=oci.retry.NoneRetryStrategy(),
)


# ---------------------------------------------------------
# OCI Chat with Retry / Exponential Backoff
# ---------------------------------------------------------

def _chat_with_retry(
    chat_details: ChatDetails,
    max_retries: int = 5,
    initial_delay: int = 2,
):
    """
    Calls OCI Generative AI with application-level retry
    handling for HTTP 429 throttling.

    Retry sequence:

        Attempt 1
        wait 2 sec
        Attempt 2
        wait 4 sec
        Attempt 3
        wait 8 sec
        Attempt 4
        wait 16 sec
        Attempt 5

    Only HTTP 429 errors are retried.
    Other OCI errors are raised immediately.
    """

    delay = initial_delay

    for attempt in range(1, max_retries + 1):

        try:

            print(
                f"OCI Generative AI request "
                f"(attempt {attempt}/{max_retries})"
            )

            response = client.chat(
                chat_details=chat_details
            )

            print(
                "OCI Generative AI request successful."
            )

            return response

        except oci.exceptions.ServiceError as e:

            if e.status == 429:

                if attempt == max_retries:

                    print(
                        "OCI Generative AI throttling persists "
                        "after maximum retries."
                    )

                    raise

                print(
                    f"OCI Generative AI returned HTTP 429 "
                    f"(throttled). Retrying in {delay} seconds..."
                )

                time.sleep(delay)

                delay *= 2

            else:

                print(
                    f"OCI Generative AI request failed "
                    f"with HTTP {e.status}."
                )

                raise

    raise RuntimeError(
        "OCI Generative AI request failed after retries."
    )


# ---------------------------------------------------------
# Extract Generic Chat Response
# ---------------------------------------------------------

def _extract_response_text(response) -> str:
    """
    Extracts text from OCI GenericChatResponse.

    Gemini uses the generic chat response structure:

        chat_response
            -> choices
                -> message
                    -> content
                        -> text
    """

    choices = response.data.chat_response.choices

    if not choices:
        raise RuntimeError(
            "OCI Generative AI returned an empty response."
        )

    message = choices[0].message

    if not message.content:
        raise RuntimeError(
            "OCI Generative AI returned an empty message."
        )

    text_parts = []

    for content in message.content:

        if hasattr(content, "text") and content.text:
            text_parts.append(content.text)

    if not text_parts:
        raise RuntimeError(
            "OCI Generative AI response contained no text."
        )

    return "".join(text_parts)


# ---------------------------------------------------------
# Generate RAG Answer
# ---------------------------------------------------------

def generate_answer(
    question: str,
    context: str
) -> str:

    system_prompt = """
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
"""

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

    chat_request = GenericChatRequest(
        api_format="GENERIC",
        messages=messages,
        max_tokens=400,
        temperature=0.2,
        reasoning_effort="LOW",
    )

    chat_details = ChatDetails(
        compartment_id=COMPARTMENT_ID,
        serving_mode=OnDemandServingMode(
            model_id=MODEL_ID
        ),
        chat_request=chat_request,
    )

    response = _chat_with_retry(
        chat_details=chat_details
    )

    return _extract_response_text(response)


# ---------------------------------------------------------
# Generate General AI Answer
# No RAG / General Query
# ---------------------------------------------------------

def generate_general_answer(
    question: str
) -> str:

    system_prompt = """
You are GSVAI, a premier enterprise AI assistant powered by
OCI Generative AI.

Your task is to answer the user's question accurately,
concisely, and professionally.

Rules:

1. Provide a direct, helpful, and well-structured answer.

2. If explaining technical concepts, architecture, or business
   processes, use clear points.

3. Maintain a professional enterprise tone.

4. Do NOT mention that you searched a knowledge base or that
   information was missing unless relevant.
"""

    user_prompt = f"""
User Question
-------------
{question}

Answer
------
"""

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

    chat_request = GenericChatRequest(
        api_format="GENERIC",
        messages=messages,
        max_tokens=450,
        temperature=0.3,
        reasoning_effort="LOW",
    )

    chat_details = ChatDetails(
        compartment_id=COMPARTMENT_ID,
        serving_mode=OnDemandServingMode(
            model_id=MODEL_ID
        ),
        chat_request=chat_request,
    )

    response = _chat_with_retry(
        chat_details=chat_details
    )

    return _extract_response_text(response)