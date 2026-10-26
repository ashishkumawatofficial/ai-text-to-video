"""Unit and contract tests for StoryWriterGateway, ModelCascade, and aspect-ratio styling."""

import json
import pytest
from core.models import (
    NarrativeBrief,
    NarrativeInputMode,
    VideoAspectRatio,
    ASPECT_RATIO_RESOLUTIONS,
    DirectorMasterPlan,
    SceneBeat,
    Genre,
    CameraMotion,
    StoryWriterResult,
    ModelCascadeConfig,
    ModelProvider
)


@pytest.fixture
def sample_gemini_json_response():
    """Mock structured JSON response adhering to DirectorMasterPlan schema."""
    return json.dumps({
        "story_title": "The Time Barista's Napoleon Brew",
        "genre": "cinematic_story",
        "aspect_ratio": "9:16",
        "width": 1080,
        "height": 1920,
        "target_audience": "comedy_history_fans",
        "background_music": {
            "mood": "quirky_orchestral",
            "tempo_bpm": 110,
            "genre": "classical_comedy"
        },
        "scenes": [
            {
                "scene_id": "scene_1",
                "beat_title": "Espresso Machine Chrono-Glitch",
                "duration_sec": 4.5,
                "visual_prompt": "vertical 9:16 portrait focus, a frantic barista in a copper apron pulling an espresso lever that erupts in swirling electric-blue chrono-sparks inside a vintage cafe",
                "camera_movement": "zoom_in",
                "dialogue_text": "One double-shot espresso for table... wait, what century is this?!",
                "voice_persona": "en-US-ChristopherNeural",
                "sound_effects": [
                    {"sfx_name": "steam_hiss", "start_offset_sec": 0.5, "duration_sec": 1.5, "volume": 0.8}
                ]
            },
            {
                "scene_id": "scene_2",
                "beat_title": "Imperial Audience",
                "duration_sec": 5.0,
                "visual_prompt": "vertical 9:16 portrait framing, Napoleon Bonaparte standing in front of a battlefield tent, looking utterly bewildered as a steaming paper cup appears in his hand",
                "camera_movement": "pan_left",
                "dialogue_text": "Is this British sorcery? It smells... divine.",
                "voice_persona": "en-US-GuyNeural",
                "sound_effects": [
                    {"sfx_name": "military_drum", "start_offset_sec": 0.2, "duration_sec": 2.0, "volume": 0.7}
                ]
            }
        ]
    })


def test_sample_response_validates_against_models(sample_gemini_json_response):
    """Test that mock LLM JSON strictly validates into DirectorMasterPlan."""
    plan = DirectorMasterPlan.model_validate_json(sample_gemini_json_response)
    assert plan.story_title == "The Time Barista's Napoleon Brew"
    assert len(plan.scenes) == 2
    assert plan.aspect_ratio == "9:16"
    assert plan.width == 1080
    assert plan.height == 1920
    assert plan.scenes[0].duration_sec == 4.5
    assert "British sorcery" in plan.scenes[1].dialogue_text
    assert "Napoleon" in plan.scenes[1].visual_prompt


def test_story_writer_result_contract_validation(sample_gemini_json_response):
    """Test that StoryWriterResult serializes according to the JSON schema contract."""
    plan = DirectorMasterPlan.model_validate_json(sample_gemini_json_response)
    result = StoryWriterResult(
        plan=plan,
        model_used="gemini-2.5-flash",
        tier_level=1,
        latency_ms=1850.5,
        fallback_occurred=False,
        error_trace=[]
    )
    data = result.model_dump()
    assert data["model_used"] == "gemini-2.5-flash"
    assert data["tier_level"] == 1
    assert data["latency_ms"] == 1850.5
    assert data["fallback_occurred"] is False
    assert "plan" in data
    assert data["plan"]["aspect_ratio"] == "9:16"
    assert data["plan"]["width"] == 1080
    assert data["plan"]["height"] == 1920


def test_narrative_brief_aspect_ratio_resolution_mapping():
    """Test that NarrativeBrief dynamically initializes canvas resolution from aspect ratio."""
    brief_9_16 = NarrativeBrief(prompt_or_text="Short prompt", aspect_ratio=VideoAspectRatio.VERTICAL_9_16)
    assert brief_9_16.width == 1080
    assert brief_9_16.height == 1920

    brief_16_9 = NarrativeBrief(prompt_or_text="Short prompt", aspect_ratio=VideoAspectRatio.WIDESCREEN_16_9)
    assert brief_16_9.width == 1920
    assert brief_16_9.height == 1080

    brief_1_1 = NarrativeBrief(prompt_or_text="Short prompt", aspect_ratio=VideoAspectRatio.SQUARE_1_1)
    assert brief_1_1.width == 1080
    assert brief_1_1.height == 1080

    brief_4_5 = NarrativeBrief(prompt_or_text="Short prompt", aspect_ratio=VideoAspectRatio.PORTRAIT_4_5)
    assert brief_4_5.width == 1080
    assert brief_4_5.height == 1350


def test_story_writer_offline_fallback():
    """Test that StoryWriterGateway falls back to deterministic rule engine when no keys are configured."""
    from core.story_writer import StoryWriterGateway

    gateway = StoryWriterGateway(ModelCascadeConfig(provider=ModelProvider.OFFLINE))
    brief = NarrativeBrief(
        prompt_or_text="A legendary swordsman facing a dragon on a volcano peak",
        aspect_ratio=VideoAspectRatio.VERTICAL_9_16,
    )
    result = gateway.synthesize_story(brief)

    assert result.tier_level == 4
    assert result.model_used.startswith("offline_heuristic")
    assert result.plan.aspect_ratio == "9:16"
    assert result.plan.width == 1080
    assert result.plan.height == 1920
    assert len(result.plan.scenes) >= 2
    assert "vertical 9:16" in result.plan.scenes[0].visual_prompt.lower()
    assert result.latency_ms > 0.0


def test_story_writer_aspect_ratio_styling_widescreen_16_9():
    """Test that aspect ratio 16:9 sets canvas to 1920x1080 and adds widescreen framing to prompts."""
    from core.story_writer import StoryWriterGateway

    gateway = StoryWriterGateway(ModelCascadeConfig(provider=ModelProvider.OFFLINE))
    brief = NarrativeBrief(
        prompt_or_text="A space station orbiting Saturn's rings",
        aspect_ratio=VideoAspectRatio.WIDESCREEN_16_9,
    )
    result = gateway.synthesize_story(brief)

    assert result.plan.aspect_ratio == "16:9"
    assert result.plan.width == 1920
    assert result.plan.height == 1080
    for scene in result.plan.scenes:
        assert "16:9" in scene.visual_prompt.lower() or "widescreen" in scene.visual_prompt.lower()


def test_story_writer_script_adaptation_preserves_dialogue():
    """Test that script adaptation partitions text while preserving 100% of spoken words."""
    from core.story_writer import StoryWriterGateway

    gateway = StoryWriterGateway(ModelCascadeConfig(provider=ModelProvider.OFFLINE))
    script = (
        "Captain Vance stared into the pulsar storm. We only have one jump left. "
        "The hyperdrive sparked violently. Hold on to something! "
        "The ship broke through into a calm starlit nebula. We made it."
    )
    brief = NarrativeBrief(
        prompt_or_text=script,
        input_mode=NarrativeInputMode.SCRIPT_ADAPTATION,
        aspect_ratio=VideoAspectRatio.VERTICAL_9_16,
    )
    result = gateway.synthesize_story(brief)

    assert len(result.plan.scenes) >= 2
    # Verify dialogue is preserved across scenes
    all_dialogue = " ".join(scene.dialogue_text for scene in result.plan.scenes if scene.dialogue_text)
    assert "We only have one jump left" in all_dialogue
    assert "Hold on to something!" in all_dialogue
    assert "We made it" in all_dialogue


def test_story_writer_cascade_failover(monkeypatch, sample_gemini_json_response):
    """Test that when a primary model hits a rate limit (HTTP 429), the gateway cascades to the next tier."""
    from core.story_writer import StoryWriterGateway

    attempts = []

    def mock_query_gemini(self, model_name, api_key, system_prompt, user_prompt):
        attempts.append(model_name)
        if model_name == "gemini-3.8-flash":
            raise RuntimeError("HTTP 429: Resource has been exhausted (quota limit exceeded)")
        return sample_gemini_json_response

    monkeypatch.setattr(StoryWriterGateway, "_query_gemini", mock_query_gemini)
    monkeypatch.setenv("GEMINI_API_KEY", "mock_key_for_test")

    gateway = StoryWriterGateway(
        ModelCascadeConfig(
            provider=ModelProvider.GEMINI,
            gemini_models=["gemini-3.8-flash", "gemini-3.5-flash", "gemini-3.1-flash-lite"],
        )
    )
    brief = NarrativeBrief(
        prompt_or_text="A funny robot barista in Neo-Tokyo",
        aspect_ratio=VideoAspectRatio.VERTICAL_9_16,
    )
    result = gateway.synthesize_story(brief)

    assert result.fallback_occurred is True
    assert result.model_used == "gemini-3.5-flash"
    assert "gemini-3.8-flash" in attempts
    assert "gemini-3.5-flash" in attempts
    assert len(result.error_trace) == 1
    assert "429" in result.error_trace[0]


def test_gemini_model_aliasing_and_default_cascade():
    """Verify that deprecated 2.5/2.0 models forward-alias to 3.8 and default config places 3.8 at Tier 1."""
    from core.models import resolve_llm_model, ModelCascadeConfig

    cfg = ModelCascadeConfig()
    assert cfg.gemini_models[0] == "gemini-3.8-flash"
    assert cfg.gemini_models[1] == "gemini-3.5-flash"

    # Test deprecated model aliasing
    assert resolve_llm_model("gemini-2.5-flash") == "gemini-3.8-flash"
    assert resolve_llm_model("gemini-2.5-pro") == "gemini-3.8-flash"
    assert resolve_llm_model("gemini-2.0-flash") == "gemini-3.8-flash"
    assert resolve_llm_model("gemini-1.5-flash") == "gemini-3.1-flash-lite"
    assert resolve_llm_model("gemini-3.8-flash") == "gemini-3.8-flash"
    assert resolve_llm_model(None) == "gemini-3.8-flash"


