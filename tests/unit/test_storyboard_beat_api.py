import pytest
from fastapi.testclient import TestClient
from core.server import app, _ACTIVE_SESSIONS
from core.models import StudioSession, StoryboardCard, DirectingMode, BackendExecutionStrategy

@pytest.fixture
def client():
    return TestClient(app)

def test_patch_storyboard_beat_updates_card(client):
    session_id = "test-session-patch"
    test_session = StudioSession(
        session_id=session_id,
        concept_prompt="Two cows drinking tea",
        aspect_ratio="16:9",
        directing_mode=DirectingMode.PRO,
        backend_strategy=BackendExecutionStrategy.SERVERLESS,
        beats=[
            StoryboardCard(
                beat_id="beat_0",
                beat_index=0,
                visual_prompt="Spotted cow drinks tea",
                speaker="Narrator",
                dialogue_text="Once upon a time in a pasture",
                voice_actor="en-US-ChristopherNeural",
                camera_motion="push_in"
            )
        ]
    )
    _ACTIVE_SESSIONS[session_id] = test_session

    # Execute PATCH to update speaker and voice persona
    payload = {
        "session_id": session_id,
        "beat_index": 0,
        "speaker": "Barnaby the Bull",
        "voice_persona": "cartoon_animal",
        "dialogue_text": "Hey Daisy! Nice tea!",
        "camera_motion": "pan_left"
    }
    response = client.patch("/api/storyboard/beat", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "updated"
    assert data["beat"]["speaker"] == "Barnaby the Bull"
    assert data["beat"]["voice_actor"] == "cartoon_animal"
    assert data["beat"]["dialogue_text"] == "Hey Daisy! Nice tea!"
    assert data["beat"]["camera_motion"] == "pan_left"

    # Verify session in memory was updated
    updated_card = _ACTIVE_SESSIONS[session_id].beats[0]
    assert updated_card.speaker == "Barnaby the Bull"
    assert updated_card.voice_actor == "cartoon_animal"
