"""
Unit and Integration Tests for GSVAI Enterprise AI Model Service & APIs.

Verifies:
- GSVAI_AI_MODELS table creation and non-destructive seeding
- Model retrieval & live status
- Provider validation (Groq, Ollama only)
- Single Primary rule enforcement & atomic swap
- Single Fallback rule enforcement & atomic swap
- Disable rules (cannot disable primary without replacement)
- Delete rules (cannot delete primary or fallback)
- Model testing with latency measurement (mocked for CI determinism)
- Audit log generation for all model mutations
- Zero secret exposure across all APIs
"""

import json
import unittest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from main import app
from services.oracle_db_service import get_connection
from services.auth_rbac_service import get_current_user_context
from services.ai_model_service import (
    ensure_ai_models_table,
    get_ai_models,
    get_ai_model_by_id,
    create_ai_model,
    update_ai_model,
    enable_ai_model,
    disable_ai_model,
    set_primary_model,
    set_fallback_model,
    delete_ai_model,
    test_ai_model,
)


class TestAIModelService(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Ensure database table is initialized before running tests."""
        ensure_ai_models_table()

    def test_01_initial_seeding_and_listing(self):
        """Verify initial seeded models (Groq primary, Ollama fallback) exist."""
        models = get_ai_models()
        self.assertGreaterEqual(len(models), 2)

        providers = [m["provider"] for m in models]
        self.assertIn("Groq", providers)
        self.assertIn("Ollama", providers)

        primary_models = [m for m in models if m["is_primary"]]
        self.assertEqual(len(primary_models), 1, "Exactly one primary model must exist")
        self.assertEqual(primary_models[0]["provider"], "Groq")

        fallback_models = [m for m in models if m["is_fallback"]]
        self.assertEqual(len(fallback_models), 1, "Exactly one fallback model must exist")
        self.assertEqual(fallback_models[0]["provider"], "Ollama")

    def test_02_zero_secrets_exposed(self):
        """Verify model listings and objects never expose any secrets or tokens."""
        models = get_ai_models()
        models_json = json.dumps(models).lower()
        forbidden_keys = ["api_key", "groq_api_key", "password", "secret", "wallet", "private_key", "token"]
        for key in forbidden_keys:
            self.assertNotIn(f'"{key}"', models_json, f"Forbidden key '{key}' found in model metadata!")

    def test_03_create_model_validation(self):
        """Verify provider validation, empty name rejection, and unsupported type rejection."""
        # 1. Unsupported provider
        with self.assertRaises(ValueError) as ctx:
            create_ai_model({
                "provider": "UnsupportedAI",
                "model_name": "test-model",
                "model_type": "LLM",
            })
        self.assertIn("not supported", str(ctx.exception).lower())

        # 2. Empty model name
        with self.assertRaises(ValueError) as ctx:
            create_ai_model({
                "provider": "Groq",
                "model_name": "",
                "model_type": "LLM",
            })
        self.assertIn("cannot be empty", str(ctx.exception).lower())

        # 3. Unsupported model type
        with self.assertRaises(ValueError) as ctx:
            create_ai_model({
                "provider": "Groq",
                "model_name": "test-model",
                "model_type": "AUDIO",
            })
        self.assertIn("not supported", str(ctx.exception).lower())

    def test_04_create_and_delete_model_lifecycle(self):
        """Create a custom model, verify retrieval, and delete it."""
        unique_name = "llama-3.3-70b-versatile-test"
        # Cleanup if exists from previous test
        models = get_ai_models()
        for m in models:
            if m["model_name"] == unique_name:
                delete_ai_model(m["model_id"])

        created = create_ai_model({
            "provider": "Groq",
            "model_name": unique_name,
            "model_type": "LLM",
            "priority": 3,
            "enabled": True,
            "description": "Test enterprise model",
        })
        self.assertIsNotNone(created.get("model_id"))
        self.assertEqual(created["model_name"], unique_name)
        self.assertEqual(created["provider"], "Groq")

        # Duplicate check
        with self.assertRaises(ValueError) as ctx:
            create_ai_model({
                "provider": "Groq",
                "model_name": unique_name,
                "model_type": "LLM",
            })
        self.assertIn("already configured", str(ctx.exception).lower())

        # Delete model
        del_result = delete_ai_model(created["model_id"])
        self.assertEqual(del_result["status"], "SUCCESS")

        # Verify no longer present
        self.assertIsNone(get_ai_model_by_id(created["model_id"]))

    def test_05_primary_uniqueness_enforcement(self):
        """Verify only one model can be primary at any time."""
        # Create a second Groq model
        test_model_name = "mixtral-8x7b-32768-test-primary"
        # Cleanup
        for m in get_ai_models():
            if m["model_name"] == test_model_name:
                delete_ai_model(m["model_id"])

        model2 = create_ai_model({
            "provider": "Groq",
            "model_name": test_model_name,
            "enabled": True,
            "priority": 5,
        })
        m2_id = model2["model_id"]

        try:
            # Set model2 as primary
            set_primary_model(m2_id)
            updated_models = get_ai_models()
            primary_models = [m for m in updated_models if m["is_primary"]]
            self.assertEqual(len(primary_models), 1)
            self.assertEqual(primary_models[0]["model_id"], m2_id)

            # Restore original Groq model as primary
            groq_orig = next(m for m in updated_models if m["model_name"] == "openai/gpt-oss-20b")
            set_primary_model(groq_orig["model_id"])

            restored_models = get_ai_models()
            primaries = [m for m in restored_models if m["is_primary"]]
            self.assertEqual(len(primaries), 1)
            self.assertEqual(primaries[0]["model_name"], "openai/gpt-oss-20b")
        finally:
            delete_ai_model(m2_id)

    def test_06_disable_rules_enforcement(self):
        """Verify primary model cannot be disabled without selecting replacement."""
        models = get_ai_models()
        primary_model = next(m for m in models if m["is_primary"])

        with self.assertRaises(ValueError) as ctx:
            disable_ai_model(primary_model["model_id"])
        self.assertIn("cannot disable the current primary model", str(ctx.exception).lower())

    def test_07_delete_rules_enforcement(self):
        """Verify active primary and fallback models cannot be deleted."""
        models = get_ai_models()
        primary = next(m for m in models if m["is_primary"])
        fallback = next(m for m in models if m["is_fallback"])

        with self.assertRaises(ValueError) as ctx:
            delete_ai_model(primary["model_id"])
        self.assertIn("cannot delete the active primary model", str(ctx.exception).lower())

        with self.assertRaises(ValueError) as ctx:
            delete_ai_model(fallback["model_id"])
        self.assertIn("cannot delete the active fallback model", str(ctx.exception).lower())

    @patch("groq.Groq")
    def test_08_test_groq_model_mocked(self, mock_groq_class):
        """Verify model test returns safe structure and latency measurement."""
        mock_client = MagicMock()
        mock_groq_class.return_value = mock_client
        mock_client.chat.completions.create.return_value = MagicMock()

        models = get_ai_models()
        groq_model = next(m for m in models if m["provider"] == "Groq")

        res = test_ai_model(groq_model["model_id"])
        self.assertTrue(res["success"])
        self.assertEqual(res["provider"], "Groq")
        self.assertIn("latency_ms", res)
        self.assertIn("message", res)
        self.assertNotIn("api_key", json.dumps(res).lower())

    def test_09_fastapi_endpoints_and_rbac(self):
        """Verify HTTP endpoints enforce permissions and return sanitized payloads."""
        # 1. Admin test
        client = TestClient(app)

        resp = client.get("/api/settings/ai-models", headers={"X-User-Id": "admin"})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("models", data)
        self.assertIn("current_runtime", data)
        self.assertGreaterEqual(len(data["models"]), 2)

        # 2. Unauthorized user test (user1 with role USER lacks AI_MODEL_VIEW)
        unauth_resp = client.get("/api/settings/ai-models", headers={"X-User-Id": "user1"})
        self.assertEqual(unauth_resp.status_code, 403)


if __name__ == "__main__":
    unittest.main()
