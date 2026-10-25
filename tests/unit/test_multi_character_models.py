import pytest
from core.models import SceneBeatPlan, StoryboardCard, CharacterProfile

def test_scene_beat_plan_speaker_field():
    # Backward compatibility: speaker defaults to "Narrator" if omitted
    beat = SceneBeatPlan(
        beat_index=0,
        visual_prompt="Subject drinks tea at stall"
    )
    assert getattr(beat, "speaker", "Narrator") == "Narrator"
    assert beat.voice_persona is None

    # Custom speaker & voice persona assignment
    beat_with_speaker = SceneBeatPlan(
        beat_index=1,
        visual_prompt="Corporate cow looks annoyed",
        speaker="Mr. Suit Cow",
        voice_persona="male_casual",
        dialogue_text="I don't have time for this nonsense."
    )
    assert beat_with_speaker.speaker == "Mr. Suit Cow"
    assert beat_with_speaker.voice_persona == "male_casual"
    assert beat_with_speaker.dialogue_text == "I don't have time for this nonsense."

def test_storyboard_card_speaker_field():
    card = StoryboardCard(
        beat_id="beat-1",
        beat_index=0,
        visual_prompt="Two cows giggling"
    )
    assert getattr(card, "speaker", "Narrator") == "Narrator"
    assert card.voice_actor in ["en-US-ChristopherNeural", "auto"]

    card_custom = StoryboardCard(
        beat_id="beat-2",
        beat_index=1,
        visual_prompt="Cow laughing hysterically",
        speaker="Tea Stall Cow #2",
        voice_actor="cartoon_animal",
        dialogue_text="Look at his briefcase!"
    )
    assert card_custom.speaker == "Tea Stall Cow #2"
    assert card_custom.voice_actor == "cartoon_animal"

def test_character_profile_model():
    profile = CharacterProfile(
        name="Cow 1",
        archetype="cartoon_animal",
        gender="male",
        default_voice="en-US-GuyNeural",
        visual_summary="spotted cow in red scarf"
    )
    assert profile.name == "Cow 1"
    assert profile.default_voice == "en-US-GuyNeural"
