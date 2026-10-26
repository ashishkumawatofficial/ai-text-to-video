"""Unit tests for director chat multi-beat updates, dialogue clearing, and fallback handling."""

import pytest
from core.models import StudioSession, StoryboardCard, DirectingMode, BackendExecutionStrategy
from core.director_chat import process_co_director_message


@pytest.fixture
def sample_session():
    return StudioSession(
        session_id="test_chat_session",
        title="Test Titan Story",
        concept_prompt="Stone man throws car",
        aspect_ratio="9:16",
        directing_mode=DirectingMode.PRO,
        backend_strategy=BackendExecutionStrategy.SERVERLESS,
        beats=[
            StoryboardCard(beat_index=0, visual_prompt="Hero stands", dialogue_text=""),
            StoryboardCard(beat_index=1, visual_prompt="Hero lifts car", dialogue_text="And the city became his playground."),
            StoryboardCard(beat_index=2, visual_prompt="Car flies through air", dialogue_text="Gravity is merely a suggestion to the earth-born."),
        ]
    )


@pytest.mark.asyncio
async def test_clear_dialogue_multiple_beats(sample_session, monkeypatch):
    # Test rule-based fallback without external LLM network calls
    monkeypatch.setenv("TEST_MODE", "1")

    reply, delta = await process_co_director_message("for beat 2 and 3 remove dialogue", sample_session)
    assert isinstance(delta, list)
    assert len(delta) == 2
    assert delta[0]["action"] == "UPDATE_BEAT"
    assert delta[0]["target_beat"] == 1
    assert delta[0]["field"] == "dialogue"
    assert delta[0]["new_value"] == ""

    assert delta[1]["action"] == "UPDATE_BEAT"
    assert delta[1]["target_beat"] == 2
    assert delta[1]["field"] == "dialogue"
    assert delta[1]["new_value"] == ""


@pytest.mark.asyncio
async def test_clear_dialogue_negative_phrasing(sample_session, monkeypatch):
    monkeypatch.setenv("TEST_MODE", "1")

    reply, delta = await process_co_director_message("i don't want that too, for scene 3 also don't want", sample_session)
    assert isinstance(delta, list)
    assert len(delta) >= 1
    # Check that it removed dialogue rather than triggering a reroll keyframe
    for d in delta:
        assert d["action"] == "UPDATE_BEAT"
        assert d["field"] == "dialogue"
        assert d["new_value"] == ""


@pytest.mark.asyncio
async def test_remove_narrator_all_clips(sample_session, monkeypatch):
    monkeypatch.setenv("TEST_MODE", "1")

    reply, delta = await process_co_director_message("i dont' want narrator in these clips", sample_session)
    assert isinstance(delta, list)
    assert len(delta) == 3
    for d in delta:
        assert d["action"] == "UPDATE_BEAT"
        assert d["field"] == "dialogue"
        assert d["new_value"] == ""


@pytest.mark.asyncio
async def test_restructure_storyboard_clips(sample_session, monkeypatch):
    monkeypatch.setenv("TEST_MODE", "1")

    reply, delta = await process_co_director_message("i think intead of 3 clips we can rewrite whole story in 2 clips of 15s per clip so total 30 seconds video", sample_session)
    assert isinstance(delta, dict)
    assert delta["action"] == "RESTRUCTURE_STORYBOARD"
    assert delta["num_beats"] == 2
    assert delta["duration_per_beat"] == 15.0
    assert len(delta["beats"]) == 2
    assert "Restructured your story into 2 extended scenes" in reply


@pytest.mark.asyncio
async def test_conversational_query_no_mutation(sample_session, monkeypatch):
    monkeypatch.setenv("TEST_MODE", "1")

    reply, delta = await process_co_director_message("what do you think about the pacing of this story?", sample_session)
    assert delta is None
    assert "I understand your vision" in reply


@pytest.mark.asyncio
async def test_puter_fallback_when_gemini_fails(sample_session, monkeypatch):
    """Verifies that Puter AI is invoked cleanly if Gemini keys are invalid."""
    monkeypatch.delenv("TEST_MODE", raising=False)
    monkeypatch.setenv("GEMINI_API_KEYS", "invalid_dummy_key")
    
    # Run chat message through fallback tier
    reply, delta = await process_co_director_message(
        "i think intead of 3 clips we can rewrite whole story in 2 clips of 15s per clip so total 30 seconds video",
        sample_session
    )
    assert isinstance(reply, str) and len(reply) > 10
    assert delta is not None
    assert delta.get("action") == "RESTRUCTURE_STORYBOARD"


@pytest.mark.asyncio
async def test_character_replacement_single_beat(sample_session, monkeypatch):
    """Verifies copilot replaces a character in a specific beat."""
    monkeypatch.delenv("TEST_MODE", raising=False)

    reply, delta = await process_co_director_message(
        "replace the stone man with a sleek futuristic android in scene 1",
        sample_session
    )
    assert isinstance(reply, str)
    assert isinstance(delta, dict)
    assert delta["action"] == "UPDATE_BEAT"
    assert delta["target_beat"] == 0
    assert "android" in delta["new_value"].lower()


