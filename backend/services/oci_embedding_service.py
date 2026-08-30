# pyrefly: ignore [missing-import]
import oci


MODEL_ID = "cohere.embed-v4.0"


# ---------------------------------------------------------
# OCI Configuration
# ---------------------------------------------------------

config = oci.config.from_file()


# ---------------------------------------------------------
# OCI Generative AI Client
# ---------------------------------------------------------

client = oci.generative_ai_inference.GenerativeAiInferenceClient(
    config=config
)


# ---------------------------------------------------------
# Generate Embedding
# ---------------------------------------------------------

def generate_embedding(text: str):

    details = oci.generative_ai_inference.models.EmbedTextDetails(
        compartment_id=config["tenancy"],

        serving_mode=oci.generative_ai_inference.models.OnDemandServingMode(
            model_id=MODEL_ID
        ),

        inputs=[text],

        input_type="SEARCH_DOCUMENT",

        output_dimensions=1024
    )

    response = client.embed_text(
        embed_text_details=details
    )

    embedding = response.data.embeddings[0]

    return embedding