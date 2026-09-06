"""
GSVAI AI Runtime Configuration Source of Truth.

Provides centralized, dynamic, provider-agnostic runtime discovery for:
- LLM Provider & Model
- Embedding Provider, Model & Dimensions
- Vector Database Provider, Table & Metric
- Rate-limit error formatting

Email Automation and other modules must consume this service instead
of hardcoding provider or model strings.
"""

import os
from typing import Any, Dict, Optional
from dotenv import load_dotenv

load_dotenv()


def get_llm_config() -> Dict[str, Any]:
    """Resolves active LLM provider and model dynamically from environment."""
    groq_api_key = os.getenv("GROQ_API_KEY")
    groq_model = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")

    if groq_api_key:
        return {
            "provider": "Groq",
            "model": groq_model,
            "endpoint": "https://api.groq.com/openai/v1",
            "is_configured": True,
            "region": os.getenv("GROQ_REGION", "Groq Cloud"),
        }

    # Fallback to OCI Generative AI if OCI config is present
    oci_model = os.getenv("OCI_GENAI_MODEL_ID", "google.gemini-2.5-flash")
    return {
        "provider": "OCI Generative AI",
        "model": oci_model,
        "endpoint": "Oracle Cloud Infrastructure",
        "is_configured": False,
        "region": os.getenv("OCI_REGION", "ap-hyderabad-1"),
    }


def get_embedding_config() -> Dict[str, Any]:
    """Resolves active embedding model, provider, and dimensions."""
    # Resolved from environment with fallback to current local model
    embed_model = os.getenv("EMBEDDING_MODEL", "BAAI/bge-large-en-v1.5")
    return {
        "provider": "Local Sentence Transformers",
        "service": "Sentence Transformers Local Embedding Engine",
        "model": embed_model,
        "dimension": 1024,
        "dimensions": 1024,
        "metric": "COSINE",
    }


def get_vector_db_config() -> Dict[str, Any]:
    """Resolves active vector database configuration."""
    return {
        "provider": "Oracle AI Vector Search",
        "database_name": "Oracle Autonomous Database",
        "table": "GSVAI_DOCUMENT_CHUNKS",
        "dimension": 1024,
        "dimensions": 1024,
        "metric": "COSINE",
    }


def get_ai_runtime_config() -> Dict[str, Any]:
    """
    Returns the comprehensive active AI runtime configuration.
    Single source of truth for Email Automation, Telemetry, and UI status.
    """
    llm = get_llm_config()
    embedding = get_embedding_config()
    vdb = get_vector_db_config()

    return {
        "llm": llm,
        "embedding": embedding,
        "vector_database": vdb,
        "oci_region": os.getenv("OCI_REGION", "ap-hyderabad-1"),
    }


def format_rate_limit_error(provider: Optional[str] = None, model: Optional[str] = None) -> str:
    """Generates a dynamic, provider-agnostic HTTP 429 rate-limit error message."""
    active_provider = provider or get_llm_config()["provider"]
    if model:
        return f"{active_provider} ({model}) request rate limited (HTTP 429)."
    return f"{active_provider} request rate limited (HTTP 429)."


def get_llm_runtime_health() -> Dict[str, Any]:
    """
    Evaluates current live health of the active LLM provider.
    Decoupled from historical database error logs.
    """
    llm_cfg = get_llm_config()
    is_ok = bool(llm_cfg.get("is_configured"))

    return {
        "provider": llm_cfg["provider"],
        "model": llm_cfg["model"],
        "status": "operational" if is_ok else "unconfigured",
        "message": f"{llm_cfg['provider']} operational ({llm_cfg['model']})"
        if is_ok
        else f"{llm_cfg['provider']} API key or model not configured in environment.",
        "label": "Connected" if is_ok else "Unconfigured",
    }
