import pytest
from unittest.mock import patch, MagicMock
from core.models import NarrativeBrief, VideoAspectRatio, NarrativeInputMode, DirectorMasterPlan, SceneBeatPlan
from core.story_writer import StoryWriter

def test_system_prompt_includes_multi_character_rules():
    writer = StoryWriter()
    brief = NarrativeBrief(
        prompt_or_text="Two friendly cows chatting over a fence",
        aspect_ratio=VideoAspectRatio.WIDESCREEN_16_9,
        input_mode=NarrativeInputMode.CONCEPT_EXPANSION
    )
    system_prompt = writer._build_system_prompt(brief)
    
    # Assert multi-character instructions are present
    assert "MULTI-CHARACTER DIALOGUE ATTRIBUTION" in system_prompt
    assert "speaker" in system_prompt
    assert "voice_persona" in system_prompt
    assert "4-PART KINETIC MOTION PROMPTING" in system_prompt

def test_generate_plan_parses_character_speakers_and_personas():
    writer = StoryWriter()
    mock_json = """
    {
      "title": "Pasture Gossip",
      "genre": "cinematic_story",
      "aspect_ratio": "16:9",
      "total_duration_sec": 9.0,
      "scenes": [
        {
          "beat_index": 1,
          "name": "The Greeting",
          "duration_sec": 4.5,
          "camera_movement": "slow_push_in",
          "visual_prompt": "16:9 widescreen, a spotted cow chews grass and winks, background cows glance over, morning mist floats over the pasture, cinematic slow push in",
          "speaker": "Daisy the Cow",
          "voice_persona": "female_warm",
          "dialogue_text": "Good morning Barnaby! Did you see that suit-wearing bull?"
        },
        {
          "beat_index": 2,
          "name": "The Reply",
          "duration_sec": 4.5,
          "camera_movement": "pan_right",
          "visual_prompt": "16:9 widescreen, Barnaby the brown bull chuckles and sips warm tea, wooden stall shakes slightly, steam rises from teapot, smooth eye-level tracking pan",
          "speaker": "Barnaby the Bull",
          "voice_persona": "male_casual",
          "dialogue_text": "Ha! He thinks briefcase equals grass!"
        }
      ]
    }
    """
    
    with patch.object(writer, "_query_gemini", return_value=mock_json):
        brief = NarrativeBrief(
            prompt_or_text="Two cows discussing corporate fashion",
            aspect_ratio=VideoAspectRatio.WIDESCREEN_16_9
        )
        with patch("core.story_writer.get_gemini_api_keys", return_value=["dummy_key"]):
            result = writer.generate_plan(brief)
            
            assert len(result.plan.scenes) == 2
            beat1 = result.plan.scenes[0]
            beat2 = result.plan.scenes[1]
            
            assert beat1.speaker == "Daisy the Cow"
            assert beat1.voice_persona == "female_warm"
            assert beat1.dialogue_text.startswith("Good morning")
            
            assert beat2.speaker == "Barnaby the Bull"
            assert beat2.voice_persona == "male_casual"
            assert beat2.dialogue_text.startswith("Ha!")
