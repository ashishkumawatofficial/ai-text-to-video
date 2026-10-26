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


def test_dual_prompt_separation_and_reroll(client):
    """Verifies image_prompt and motion_prompt are decoupled, editable, and rerollable independently."""
    payload = {
        "prompt": "A lone astronaut walking in a neon cyberpunk wasteland",
        "aspect_ratio": "16:9",
        "genre": "cinematic",
        "directing_mode": "pro",
        "backend": "local"
    }

    resp = client.post("/api/storyboard/generate", json=payload)
    assert resp.status_code == 200
    session_data = resp.json()
    beats = session_data["beats"]
    assert len(beats) > 0
    first_beat = beats[0]
    assert "image_prompt" in first_beat and first_beat["image_prompt"] is not None
    assert "motion_prompt" in first_beat and first_beat["motion_prompt"] is not None

    session_id = session_data["session_id"]

    # 1. Update both prompts explicitly via patch
    patch_resp = client.patch("/api/storyboard/beat", json={
        "session_id": session_id,
        "beat_index": 0,
        "image_prompt": "Ultra-detailed static wide shot of a lone astronaut in glowing armor",
        "motion_prompt": "Slow camera push-in, neon particles floating through the wind",
        "speaker": None,
        "dialogue_text": ""
    })
    assert patch_resp.status_code == 200
    updated_beat = patch_resp.json()["beat"]
    assert updated_beat["image_prompt"] == "Ultra-detailed static wide shot of a lone astronaut in glowing armor"
    assert updated_beat["motion_prompt"] == "Slow camera push-in, neon particles floating through the wind"
    assert updated_beat["speaker"] is None
    assert updated_beat["dialogue_text"] == ""

    # 2. Reroll specifically with target_prompt_type="image"
    reroll_resp = client.post("/api/storyboard/reroll", json={
        "session_id": session_id,
        "beat_index": 0,
        "prompt_override": "Tweak: Golden hour lighting on astronaut helmet",
        "target_prompt_type": "image"
    })
    assert reroll_resp.status_code == 200
    rerolled_beat = reroll_resp.json()
    assert rerolled_beat["image_prompt"] == "Tweak: Golden hour lighting on astronaut helmet"
    # motion_prompt remains intact!
    assert rerolled_beat["motion_prompt"] == "Slow camera push-in, neon particles floating through the wind"


def test_replan_storyboard_preserves_session(client):
    """Verifies that re-planning an active storyboard with session_id preserves identity and updates beats."""
    # 1. Initial storyboard generation
    resp = client.post("/api/storyboard/generate", json={
        "prompt": "A brave deep-sea diver discovering an underwater bioluminescent cave",
        "aspect_ratio": "16:9",
        "genre": "cinematic",
        "directing_mode": "pro",
        "backend": "local"
    })
    assert resp.status_code == 200
    initial_session = resp.json()
    orig_session_id = initial_session["session_id"]
    assert initial_session["concept_prompt"] == "A brave deep-sea diver discovering an underwater bioluminescent cave"
    assert len(initial_session["beats"]) > 0

    # 2. Re-plan storyboard with updated script and existing session_id
    replan_resp = client.post("/api/storyboard/generate", json={
        "session_id": orig_session_id,
        "prompt": "A brave deep-sea diver encounters a giant crystalline leviathan glowing in turquoise light",
        "aspect_ratio": "16:9",
        "genre": "cinematic",
        "directing_mode": "pro",
        "backend": "local"
    })
    assert replan_resp.status_code == 200
    replanned_session = replan_resp.json()

    # Session ID must be strictly preserved
    assert replanned_session["session_id"] == orig_session_id
    # Concept prompt is updated
    assert replanned_session["concept_prompt"] == "A brave deep-sea diver encounters a giant crystalline leviathan glowing in turquoise light"
    assert len(replanned_session["beats"]) > 0
    # Chat history records the replan note
    assert len(replanned_session["chat_history"]) >= 1
    assert any("re-planned" in msg["text"].lower() for msg in replanned_session["chat_history"])


def test_render_single_beat_modality_variable_scope(client):
    """Verifies that POST /api/render/beat executes cleanly without VideoGenerationModality scope error."""
    # 1. Create a session with a beat card
    session_id = "test-session-render-scope"
    test_session = StudioSession(
        session_id=session_id,
        concept_prompt="A futuristic hovercar speeding through neon rain",
        aspect_ratio="16:9",
        backend_strategy="local",
        beats=[
            StoryboardCard(
                beat_id="beat_0",
                beat_index=0,
                visual_prompt="Hovercar gliding across wet asphalt under holographic billboards",
                motion_prompt="Camera follows closely behind hovercar as thrusters flare with blue flame",
                image_prompt="Cinematic wide shot of sleek aerodynamic hovercar parked on neon street",
                duration_seconds=3.0,
                render_status="pending",
                model_id="kling-v1.5",
            )
        ]
    )
    _ACTIVE_SESSIONS[session_id] = test_session

    # 2. Invoke single beat render
    resp = client.post("/api/render/beat", json={
        "session_id": session_id,
        "beat_index": 0,
        "backend": "local"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "video_path" in data or "status" in data




