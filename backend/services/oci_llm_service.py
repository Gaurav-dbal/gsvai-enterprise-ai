# pyrefly: ignore [missing-import]

import os
import time

from dotenv import load_dotenv
from groq import Groq, APIError, RateLimitError

load_dotenv()

MODEL_ID = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY must be configured in the environment.")

client = Groq(api_key=GROQ_API_KEY)

print("=" * 60)
print("GSVAI GROQ GENERATIVE AI CONFIGURATION")
print("=" * 60)
print(f"Groq Model      : {MODEL_ID}")
print("Groq Endpoint   : https://api.groq.com/openai/v1")
print("=" * 60)


def _chat_with_retry(
    messages: list[dict],
    max_completion_tokens: int,
    temperature: float,
    reasoning_effort: str = "low",
    max_retries: int = 3,
):
    """Call Groq with conservative 429 retry handling."""

    retry_delays = [2, 5]

    for attempt in range(1, max_retries + 1):
        try:
            print(f"Groq request (attempt {attempt}/{max_retries})")

            response = client.chat.completions.create(
                model=MODEL_ID,
                messages=messages,
                max_completion_tokens=max_completion_tokens,
                temperature=temperature,
                reasoning_effort=reasoning_effort,
                include_reasoning=False,
                stream=False,
            )

            print("Groq request successful.")
            return response

        except RateLimitError as e:
            print("Groq returned HTTP 429 rate limit.")

            if attempt == max_retries:
                raise RuntimeError(
                    "Groq is currently rate limiting requests (HTTP 429). "
                    "The request was stopped after conservative retries."
                ) from e

            retry_after = None
            try:
                response = getattr(e, "response", None)
                headers = getattr(response, "headers", {}) or {}
                retry_after = headers.get("retry-after")
            except Exception:
                pass

            if retry_after:
                try:
                    delay = max(float(retry_after), 1.0)
                except (TypeError, ValueError):
                    delay = retry_delays[attempt - 1]
            else:
                delay = retry_delays[attempt - 1]

            print(f"Waiting {delay:g} seconds before retry...")
            time.sleep(delay)

        except APIError as e:
            print(f"Groq API request failed: {e}")
            raise

    raise RuntimeError("Groq request failed after retries.")


def _extract_response_text(response) -> str:
    """Extract text from a Groq Chat Completion response."""

    if not response.choices:
        raise RuntimeError("Groq returned an empty response.")

    message = response.choices[0].message

    if not message:
        raise RuntimeError("Groq returned an empty message.")

    text = message.content

    if not text:
        raise RuntimeError("Groq response contained no text.")

    return text


def generate_answer(question: str, context: str) -> str:
    """Generate a grounded answer using retrieved enterprise context."""

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

    response = _chat_with_retry(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        max_completion_tokens=400,
        temperature=0.2,
        reasoning_effort="low",
    )

    return _extract_response_text(response)


def generate_general_answer(question: str) -> str:
    """Generate a general AI answer without RAG context."""

    system_prompt = """
You are GSVAI, a premier enterprise AI assistant powered by Groq.

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

    user_prompt = f"""
User Question
-------------
{question}

Answer
------
"""

    response = _chat_with_retry(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        max_completion_tokens=450,
        temperature=0.3,
        reasoning_effort="low",
    )

    return _extract_response_text(response)
