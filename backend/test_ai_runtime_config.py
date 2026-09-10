import os
import unittest
from unittest.mock import patch

from services.ai_runtime_config import (
    get_llm_config,
    get_embedding_config,
    get_vector_db_config,
    get_ai_runtime_config,
    format_rate_limit_error,
    get_llm_runtime_health,
)


class TestAIRuntimeConfig(unittest.TestCase):

    def test_groq_llm_configuration(self):
        with patch.dict(
            os.environ,
            {
                "GROQ_API_KEY": "ci-test-key",
                "GROQ_MODEL": "openai/gpt-oss-20b",
                "GROQ_REGION": "Groq Cloud",
            },
            clear=False,
        ):
            config = get_llm_config()

        self.assertEqual(config["provider"], "Groq")
        self.assertEqual(config["model"], "openai/gpt-oss-20b")
        self.assertEqual(
            config["endpoint"],
            "https://api.groq.com/openai/v1",
        )
        self.assertTrue(config["is_configured"])
        self.assertEqual(config["region"], "Groq Cloud")

    def test_embedding_configuration(self):
        with patch.dict(
            os.environ,
            {"EMBEDDING_MODEL": "BAAI/bge-large-en-v1.5"},
            clear=False,
        ):
            config = get_embedding_config()

        self.assertEqual(
            config["provider"],
            "Local Sentence Transformers",
        )
        self.assertEqual(
            config["service"],
            "Sentence Transformers Local Embedding Engine",
        )
        self.assertEqual(
            config["model"],
            "BAAI/bge-large-en-v1.5",
        )
        self.assertEqual(config["dimension"], 1024)
        self.assertEqual(config["dimensions"], 1024)
        self.assertEqual(config["metric"], "COSINE")

    def test_vector_database_configuration(self):
        config = get_vector_db_config()

        self.assertEqual(
            config["provider"],
            "Oracle AI Vector Search",
        )
        self.assertEqual(
            config["database_name"],
            "Oracle Autonomous Database",
        )
        self.assertEqual(
            config["table"],
            "GSVAI_DOCUMENT_CHUNKS",
        )
        self.assertEqual(config["dimension"], 1024)
        self.assertEqual(config["dimensions"], 1024)
        self.assertEqual(config["metric"], "COSINE")

    def test_combined_runtime_configuration(self):
        with patch.dict(
            os.environ,
            {
                "GROQ_API_KEY": "ci-test-key",
                "GROQ_MODEL": "openai/gpt-oss-20b",
                "EMBEDDING_MODEL": "BAAI/bge-large-en-v1.5",
                "OCI_REGION": "ap-hyderabad-1",
            },
            clear=False,
        ):
            config = get_ai_runtime_config()

        self.assertEqual(config["llm"]["provider"], "Groq")
        self.assertEqual(
            config["llm"]["model"],
            "openai/gpt-oss-20b",
        )

        self.assertEqual(
            config["embedding"]["provider"],
            "Local Sentence Transformers",
        )
        self.assertEqual(config["embedding"]["dimensions"], 1024)

        self.assertEqual(
            config["vector_database"]["provider"],
            "Oracle AI Vector Search",
        )
        self.assertEqual(
            config["vector_database"]["dimensions"],
            1024,
        )
        self.assertEqual(
            config["vector_database"]["metric"],
            "COSINE",
        )

        self.assertEqual(
            config["oci_region"],
            "ap-hyderabad-1",
        )

    def test_rate_limit_error_uses_active_provider(self):
        with patch.dict(
            os.environ,
            {
                "GROQ_API_KEY": "ci-test-key",
                "GROQ_MODEL": "openai/gpt-oss-20b",
            },
            clear=False,
        ):
            message = format_rate_limit_error()

        self.assertEqual(
            message,
            "Groq request rate limited (HTTP 429).",
        )

    def test_rate_limit_error_includes_model(self):
        message = format_rate_limit_error(
            provider="Groq",
            model="openai/gpt-oss-20b",
        )

        self.assertEqual(
            message,
            "Groq (openai/gpt-oss-20b) request rate limited (HTTP 429).",
        )

    def test_llm_runtime_health_when_configured(self):
        with patch.dict(
            os.environ,
            {
                "GROQ_API_KEY": "ci-test-key",
                "GROQ_MODEL": "openai/gpt-oss-20b",
            },
            clear=False,
        ):
            health = get_llm_runtime_health()

        self.assertEqual(health["provider"], "Groq")
        self.assertEqual(
            health["model"],
            "openai/gpt-oss-20b",
        )
        self.assertEqual(health["status"], "operational")
        self.assertEqual(health["label"], "Connected")


if __name__ == "__main__":
    unittest.main(verbosity=2)
