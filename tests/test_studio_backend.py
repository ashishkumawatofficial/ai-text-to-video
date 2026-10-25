"""Unit and contract tests for the AI Video Web Studio FastAPI backend."""

import pytest
from fastapi.testclient import TestClient

from core.server import app, _ACTIVE_SESSIONS
from core.models import StudioSession, StoryboardCard


@pytest.fixture
def client():
    return TestClient(app)


def test_health_endpoint(client):
    """Verifies GET /api/health returns 200 with proper status structure."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "HEALTHY"
    assert "gemini_active" in data
    assert "serverless_healthy" in data


def test_generate_and_reroll_storyboard(client):
    """Verifies POST /api/storyboard/generate and POST /api/storyboard/reroll."""
    payload = {
        "prompt": "An astronaut discovering a glowing alien relic on Mars",
        "aspect_ratio": "16:9",
        "genre": "cinematic",
        "directing_mode": "pro",
        "backend": "local"
    }

    resp = client.post("/api/storyboard/generate", json=payload)
    assert resp.status_code == 200
    session_data = resp.json()

    assert "session_id" in session_data
    session_id = session_data["session_id"]
    assert len(session_data["beats"]) > 0
    assert session_data["aspect_ratio"] == "16:9"

    # Test single-beat re-roll
    reroll_payload = {
        "session_id": session_id,
        "beat_index": 0,
        "prompt_override": "Astronaut standing near a violet crystal pyramid"
    }
    reroll_resp = client.post("/api/storyboard/reroll", json=reroll_payload)
    assert reroll_resp.status_code == 200
    updated_card = reroll_resp.json()
    assert updated_card["beat_index"] == 0
    assert "violet crystal" in updated_card["visual_prompt"]
    assert updated_card["edited_by_ai"] is True


def test_director_chat_flow(client):
    """Verifies POST /api/director/chat applies conversational delta modifications."""
    # Create test session in active store
    test_session = StudioSession(
        session_id="test-session-chat",
        concept_prompt="Cyberpunk street racer in Neo Tokyo",
        aspect_ratio="16:9",
        beats=[
            StoryboardCard(
                beat_id="beat_0",
                beat_index=0,
                visual_prompt="Neon alleyway with glistening rain",
                dialogue_text="The city never sleeps.",
            ),
            StoryboardCard(
                beat_id="beat_1",
                beat_index=1,
                visual_prompt="High speed motorcycle race through tunnel",
                dialogue_text="Hold on tight.",
            )
        ]
    )
    _ACTIVE_SESSIONS["test-session-chat"] = test_session

    chat_payload = {
        "session_id": "test-session-chat",
        "message": "Make beat 2 darker with thunder and heavy lightning"
    }

    resp = client.post("/api/director/chat", json=chat_payload)
    assert resp.status_code == 200
    data = resp.json()
    assert "reply" in data
    assert len(data["updated_beats"]) == 2

    # Verify session chat history contains user and ai turns
    session = _ACTIVE_SESSIONS["test-session-chat"]
    assert len(session.chat_history) == 2
    assert session.chat_history[0].sender == "user"
    assert session.chat_history[1].sender == "director_ai"


def test_render_cancel_flow(client):
    """Verifies POST /api/render/cancel updates session state to cancelled."""
    test_session = StudioSession(
        session_id="test-session-cancel",
        concept_prompt="Deep ocean submarine exploring trenches",
        status="rendering"
    )
    _ACTIVE_SESSIONS["test-session-cancel"] = test_session

    cancel_resp = client.post("/api/render/cancel", json={"session_id": "test-session-cancel"})
    assert cancel_resp.status_code == 200
    assert cancel_resp.json()["cancelled"] is True
    assert _ACTIVE_SESSIONS["test-session-cancel"].status == "cancelled"


def test_upload_beat_image(client):
    """Verifies POST /api/storyboard/upload-image uploads and binds user image."""
    import io
    test_session = StudioSession(
        session_id="test-session-upload",
        concept_prompt="Ancient samurai temple duel",
        aspect_ratio="16:9",
        beats=[
            StoryboardCard(
                beat_id="beat_0",
                beat_index=0,
                visual_prompt="Samurai bowing in cherry blossom courtyard",
                dialogue_text="Honor above all.",
            )
        ]
    )
    _ACTIVE_SESSIONS["test-session-upload"] = test_session

    fake_image = io.BytesIO(b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00\xff\xdb")
    resp = client.post(
        "/api/storyboard/upload-image",
        data={"session_id": "test-session-upload", "beat_index": 0},
        files={"file": ("custom_samurai.jpg", fake_image, "image/jpeg")}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_custom_image"] is True
    assert "user_keyframe_beat_1" in data["keyframe_path"]
    assert _ACTIVE_SESSIONS["test-session-upload"].beats[0].is_custom_image is True


def test_voice_persona_in_studio_chat_and_generation(client):
    """Verifies voice_persona flows into storyboard generation and can be dynamically changed via chat."""
    payload = {
        "prompt": "A cute cartoon squirrel hiding an acorn from a friendly bird",
        "aspect_ratio": "16:9",
        "genre": "cinematic",
        "directing_mode": "pro",
        "backend": "local",
        "voice_persona": "cartoon_animal"
    }

    resp = client.post("/api/storyboard/generate", json=payload)
    assert resp.status_code == 200
    session_data = resp.json()
    assert len(session_data["beats"]) > 0
    assert session_data["beats"][0]["voice_actor"] == "cartoon_animal"

    # Now change voice via Director Copilot chat
    session_id = session_data["session_id"]
    chat_resp = client.post("/api/director/chat", json={
        "session_id": session_id,
        "message": "Switch narrator to a kid voice please"
    })
    assert chat_resp.status_code == 200
    chat_data = chat_resp.json()
    assert chat_data["applied_delta"]["action"] == "CHANGE_VOICE_PERSONA"
    assert chat_data["applied_delta"]["new_value"] == "kid"
    assert chat_data["updated_beats"][0]["voice_actor"] == "kid"

