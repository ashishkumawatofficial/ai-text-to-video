"""Global pytest configuration and zero-waste test isolation.

Ensures that automated test suites:
1. Set TEST_MODE=1 so that pipelines and engines automatically use local/free tiers
   (e.g., Edge-TTS, procedural PIL keyframes, local video compositor).
2. Never burn paid cloud credits (Cloudflare neurons, Puter AI tokens, RunPod GPU seconds)
   during automated regression testing.
"""

import os
import pytest


@pytest.fixture(autouse=True)
def enforce_zero_waste_test_environment(monkeypatch):
    """Enforce zero-waste execution across all pytest runs."""
    monkeypatch.setenv("TEST_MODE", "1")
