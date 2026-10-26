"""Unit tests for FastAPI provider registry, models, quotes, and prompt adaptation endpoints."""

import pytest
from fastapi.testclient import TestClient
from core.server import app

client = TestClient(app)


def test_get_providers_registry():
    response = client.get("/api/providers/registry")
    assert response.status_code == 200
    data = response.json()
    assert "providers" in data
    assert len(data["providers"]) >= 3
    # Check that fal.ai, apidot, kie are present with documentation links
    provider_ids = [p["provider_id"] for p in data["providers"]]
    assert "fal_ai" in provider_ids
    assert "apidot_ai" in provider_ids
    assert "kie_ai" in provider_ids

    fal = next(p for p in data["providers"] if p["provider_id"] == "fal_ai")
    assert fal["official_docs_url"] == "https://fal.ai/docs"
    assert fal["zero_cost_on_failure"] is True


def test_get_providers_models():
    response = client.get("/api/providers/models")
    assert response.status_code == 200
    data = response.json()
    assert "models" in data
    models = data["models"]
    model_ids = [m["model_id"] for m in models]

    assert "kling-v1.5" in model_ids
    assert "seedance-2.5" in model_ids
    assert "runway-gen3-alpha" in model_ids
    assert "wan-2.1" in model_ids

    kling = next(m for m in models if m["model_id"] == "kling-v1.5")
    assert kling["hard_char_limit"] == 3072
    assert kling["supports_native_audio"] is True


def test_post_provider_quotes():
    payload = {
        "model_id": "kling-v1.5",
        "duration_sec": 5.0,
        "resolution": "720p",
        "has_native_audio": False
    }
    response = client.post("/api/providers/quotes", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["model_id"] == "kling-v1.5"
    assert "quotes" in data
    assert len(data["quotes"]) > 0
    assert any(q["is_cheapest"] for q in data["quotes"])


def test_post_provider_quotes_scaled_by_resolution():
    res_480p = client.post("/api/providers/quotes", json={"model_id": "kling-v1.5", "duration_sec": 5.0, "resolution": "480p"}).json()
    res_720p = client.post("/api/providers/quotes", json={"model_id": "kling-v1.5", "duration_sec": 5.0, "resolution": "720p"}).json()
    res_1080p = client.post("/api/providers/quotes", json={"model_id": "kling-v1.5", "duration_sec": 5.0, "resolution": "1080p"}).json()
    res_4k = client.post("/api/providers/quotes", json={"model_id": "kling-v1.5", "duration_sec": 5.0, "resolution": "4k"}).json()

    cheapest_480p = next(q for q in res_480p["quotes"] if q["is_cheapest"])
    cheapest_720p = next(q for q in res_720p["quotes"] if q["is_cheapest"])
    cheapest_1080p = next(q for q in res_1080p["quotes"] if q["is_cheapest"])
    cheapest_4k = next(q for q in res_4k["quotes"] if q["is_cheapest"])

    assert cheapest_480p["rate_per_sec_usd"] < cheapest_720p["rate_per_sec_usd"]
    assert cheapest_720p["rate_per_sec_usd"] < cheapest_1080p["rate_per_sec_usd"]
    assert cheapest_1080p["rate_per_sec_usd"] < cheapest_4k["rate_per_sec_usd"]



def test_post_adapt_prompt():
    payload = {
        "raw_prompt": "A solitary cyberpunk detective in a trenchcoat walks cautiously through a neon-lit rain-slicked alleyway while gazing at hologram billboards.",
        "target_model_id": "runway-gen3-alpha",
        "modality": "i2v",
        "has_native_audio": True,
        "dialogue_text": "The signal was coming from here."
    }
    response = client.post("/api/providers/adapt-prompt", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["is_within_limit"] is True
    assert "adapted_prompt" in data
    assert "The signal was coming from here." in data["adapted_prompt"]
