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

print("=" * 60)
print("GSVAI - OCI GENERATIVE AI TEST")
print("=" * 60)
# ---------------------------------------------------------
# 1. Load OCI configuration
# ---------------------------------------------------------

print("\nLoading OCI configuration...")

config = oci.config.from_file()

print("OCI configuration loaded successfully.")
print(f"Region: {config['region']}")


# ---------------------------------------------------------
# 2. OCI Compartment
# ---------------------------------------------------------

COMPARTMENT_ID = config["tenancy"]


# ---------------------------------------------------------
# 3. Create OCI Generative AI client
# ---------------------------------------------------------

print("\nCreating OCI Generative AI client...")

client = GenerativeAiInferenceClient(
    config=config
)

print("Generative AI client created successfully.")


# ---------------------------------------------------------
# 4. Select model
# ---------------------------------------------------------

MODEL_ID = "cohere.command-a-03-2025"

print(f"\nModel: {MODEL_ID}")


# ---------------------------------------------------------
# 5. Question
# ---------------------------------------------------------

question = "Explain what Retrieval-Augmented Generation (RAG) is in simple terms."

print("\nQuestion:")
print(question)


# ---------------------------------------------------------
# 6. Create chat request
# ---------------------------------------------------------

chat_request = CohereChatRequest(
    message=question,
    max_tokens=300,
    temperature=0.2,
)


# ---------------------------------------------------------
# 7. Create chat details
# ---------------------------------------------------------

chat_details = ChatDetails(
    compartment_id=COMPARTMENT_ID,
    serving_mode=OnDemandServingMode(
        model_id=MODEL_ID
    ),
    chat_request=chat_request,
)


# ---------------------------------------------------------
# 8. Call OCI Generative AI
# ---------------------------------------------------------

print("\nCalling OCI Generative AI...")

response = client.chat(
    chat_details=chat_details
)


# ---------------------------------------------------------
# 9. Display response
# ---------------------------------------------------------

answer = response.data.chat_response.text

print("\n" + "=" * 60)
print("OCI GENERATIVE AI RESPONSE")
print("=" * 60)

print(answer)

print("=" * 60)