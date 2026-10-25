"""Unit tests for Puter AI integration."""

import os
from unittest.mock import patch, MagicMock
from core.config import get_puter_api_key
from core.local_visual_mock import generate_local_keyframe
from core.story_writer import StoryWriterGateway
from core.models import NarrativeBrief, VideoAspectRatio


def test_get_puter_api_key_loaded():
    """Verify get_puter_api_key extracts PUTER_API_KEY from environment."""
    key = get_puter_api_key()
    assert key is not None
    assert len(key) > 20
    assert not key.startswith("your_")


def test_story_writer_has_puter_candidate():
    """Verify StoryWriterGateway includes Puter as a cascade candidate when key is present."""
    writer = StoryWriterGateway()
    brief = NarrativeBrief(
        prompt_or_text="A story about cows celebrating a birthday",
        aspect_ratio=VideoAspectRatio.WIDESCREEN_16_9,
    )
    # Mocking _query_puter to return a valid dummy DirectorMasterPlan json
    dummy_json = '''{
        "title": "Cow Party",
        "genre": "cinematic_story",
        "aspect_ratio": "16:9",
        "total_duration_sec": 10.0,
        "scenes": [
            {
                "beat_index": 0,
                "name": "Celebration",
                "duration_sec": 5.0,
                "camera_movement": "zoom_in",
                "visual_prompt": "16:9 widescreen, cows dancing with hats",
                "dialogue_text": "Moo!"
            }
        ]
    }'''
    with patch.object(writer, "_query_gemini", side_effect=Exception("Gemini quota 429")):
        with patch.object(writer, "_query_puter", return_value=dummy_json) as mock_puter:
            result = writer.synthesize_story(brief)
            assert result.model_used == "gpt-4o"
            assert result.plan.title == "Cow Party"
            assert mock_puter.called


async def test_director_chat_puter_fallback(monkeypatch):
    """Verify process_co_director_message falls back to Puter AI (gpt-4o / claude-sonnet) when Gemini fails."""
    monkeypatch.setenv("TEST_MODE", "0")
    from core.director_chat import process_co_director_message
    from core.models import StudioSession

    session = StudioSession(
        session_id="test_session",
        concept_prompt="Cow adventure",
        aspect_ratio="16:9",
        beats=[],
        chat_history=[],
    )

    dummy_puter_resp = MagicMock()
    dummy_puter_resp.status_code = 200
    dummy_puter_resp.json.return_value = {
        "result": {
            "message": {
                "content": '{"reply": "Puter Director updated Shot 1 to high drama.", "delta": {"action": "UPDATE_VISUAL_PROMPT", "target_beat": 0, "new_value": "Dramatic close up of cow in rain"}}'
            }
        }
    }

    # Simulate Gemini failing with 429
    with patch("google.genai.Client", side_effect=Exception("ResourceExhausted: 429")):
        with patch("requests.post", return_value=dummy_puter_resp) as mock_post:
            reply, delta = await process_co_director_message("Make shot 1 more dramatic", session)
            assert "Puter Director" in reply
            assert delta is not None
            assert delta["action"] == "UPDATE_VISUAL_PROMPT"
            assert mock_post.called
