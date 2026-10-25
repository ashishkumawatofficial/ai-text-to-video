"""Tests for Gemini multi-key chaining, failover rotation, and resilience."""

from unittest.mock import MagicMock
import pytest

from core.config import get_gemini_api_keys, get_gemini_api_key
from core.story_writer import StoryWriterGateway
from core.models import NarrativeBrief, VideoAspectRatio, ModelCascadeConfig, ModelProvider


def test_get_gemini_api_keys_chains_multiple_keys(monkeypatch):
    """Verifies get_gemini_api_keys extracts GEMINI_API_KEY and GEMINI_API_KEY_2 in order."""
    monkeypatch.setenv("GEMINI_API_KEY", "key_alpha")
    monkeypatch.setenv("GEMINI_API_KEY_2", "key_beta")
    monkeypatch.setenv("GOOGLE_API_KEY", "key_gamma")

    keys = get_gemini_api_keys()
    assert keys == ["key_alpha", "key_beta", "key_gamma"]
    assert get_gemini_api_key() == "key_alpha"


def test_gemini_query_chains_to_second_key_on_failure(monkeypatch):
    """Verifies that if key 1 throws 429 Resource Exhausted, _query_gemini seamlessly retries with key 2."""
    gateway = StoryWriterGateway()
    keys_attempted = []

    class MockClient:
        def __init__(self, api_key):
            self.api_key = api_key
            self.models = MagicMock()
            self.models.generate_content.side_effect = self._generate

        def _generate(self, model, contents, config):
            keys_attempted.append(self.api_key)
            if self.api_key == "primary_quota_exceeded":
                raise RuntimeError("429 RESOURCE_EXHAUSTED: quota exceeded for current key")
            mock_resp = MagicMock()
            mock_resp.text = '{"title": "Chained Success", "genre": "action", "aspect_ratio": "16:9", "total_duration_sec": 10.0, "scenes": []}'
            return mock_resp

    # Monkeypatch genai.Client
    import google.genai
    monkeypatch.setattr(google.genai, "Client", MockClient)

    res = gateway._query_gemini(
        model_name="gemini-flash-latest",
        api_key=["primary_quota_exceeded", "backup_key_succeeds"],
        system_prompt="system",
        user_prompt="user",
    )

    assert "Chained Success" in res
    assert keys_attempted == ["primary_quota_exceeded", "backup_key_succeeds"]
