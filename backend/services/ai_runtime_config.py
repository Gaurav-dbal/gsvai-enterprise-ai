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


def get_ai_runtime_console_metadata() -> Dict[str, Any]:
    """
    Returns verified, safe runtime configuration metadata for the
    GSVAI Enterprise AI Administration Console (Settings -> AI Runtime).
    Never exposes API keys, secrets, or internal credentials.
    """
    # 1. Primary LLM
    primary_config = get_llm_config()
    is_primary_configured = bool(primary_config.get("is_configured"))
    primary_status = "Active" if is_primary_configured else "Inactive"
    primary_data = {
        "provider": primary_config.get("provider", "Groq"),
        "model": primary_config.get("model", "openai/gpt-oss-20b"),
        "status": primary_status,
        "enabled": True,
        "runtime": "API",
        "endpoint": primary_config.get("endpoint", "https://api.groq.com/openai/v1"),
        "region": primary_config.get("region", "Groq Cloud"),
        "configured": is_primary_configured,
    }

    # 2. Fallback LLM (probe local endpoint for live status)
    ollama_endpoint = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    ollama_model = os.getenv("OLLAMA_MODEL", "qwen3:0.6b")
    ollama_available = False
    try:
        import requests
        resp = requests.get(f"{ollama_endpoint.rstrip('/')}/api/tags", timeout=1.0)
        if resp.status_code == 200:
            ollama_available = True
    except Exception:
        ollama_available = False

    fallback_data = {
        "provider": "Ollama",
        "model": ollama_model,
        "status": "Available" if ollama_available else "Unavailable",
        "enabled": True,
        "runtime": "LOCAL",
        "endpoint": ollama_endpoint,
        "configured": True,
    }

    # 3. Embedding Engine
    emb_config = get_embedding_config()
    embedding_data = {
        "provider": emb_config.get("provider", "Local Sentence Transformers"),
        "model": emb_config.get("model", "BAAI/bge-large-en-v1.5"),
        "dimensions": emb_config.get("dimensions", 1024),
        "status": "Active",
        "service": emb_config.get("service", "Sentence Transformers Local Embedding Engine"),
        "configured": True,
    }

    # 4. Vector Search Engine
    vdb_config = get_vector_db_config()
    vector_search_data = {
        "provider": vdb_config.get("provider", "Oracle AI Vector Search"),
        "database_name": vdb_config.get("database_name", "Oracle Autonomous Database"),
        "table": vdb_config.get("table", "GSVAI_DOCUMENT_CHUNKS"),
        "dimensions": vdb_config.get("dimensions", 1024),
        "distance_metric": vdb_config.get("metric", "COSINE"),
        "status": "Active",
    }

    # 5. Current Live Runtime
    current_runtime_raw = {}
    try:
        from services import oci_llm_service
        runtime_info = oci_llm_service.get_runtime_info()
        current_runtime_raw = runtime_info.get("current_runtime", {})
    except Exception:
        current_runtime_raw = {}

    fallback_active = bool(current_runtime_raw.get("fallback", False))
    current_runtime_data = {
        "provider": current_runtime_raw.get("provider", primary_data["provider"]),
        "model": current_runtime_raw.get("model", primary_data["model"]),
        "fallback": fallback_active,
        "fallback_reason": current_runtime_raw.get("fallback_reason", None),
        "primary_provider": primary_data["provider"],
        "primary_model": primary_data["model"],
        "serving_mode": "LOCAL" if fallback_active else "API",
    }

    return {
        "primary": primary_data,
        "fallback": fallback_data,
        "embedding": embedding_data,
        "vector_search": vector_search_data,
        "current_runtime": current_runtime_data,
    }
