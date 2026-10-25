import pytest
from core.models import NarrativeBrief, VideoAspectRatio, NarrativeInputMode
from core.story_writer import StoryWriter

def test_kinetic_prompt_contains_motion_layers():
    # Test formula: Subject Action + Interaction + Micro-environmental Physics + Camera Kinetics
    sample_prompt = (
        "16:9 widescreen, a brown bull in a business suit trips over a wooden tea stool while dropping papers, "
        "the roadside cows burst into laughter and point, "
        "hot chai splashes into the air with billowing steam in the morning sunlight, "
        "cinematic slow push in, smooth eye-level tracking"
    )
    
    # Verify presence of action, interaction, physics, camera
    assert any(w in sample_prompt.lower() for w in ["trips", "dropping", "drinks", "running", "chews", "walks"])
    assert any(w in sample_prompt.lower() for w in ["laughter", "gasp", "cheer", "react", "point", "glance"])
    assert any(w in sample_prompt.lower() for w in ["steam", "dust", "splashes", "lighting", "sparks", "sunlight"])
    assert any(w in sample_prompt.lower() for w in ["push in", "pan", "tracking", "zoom", "tilt"])

def test_system_prompt_mandates_four_part_kinetic_prompt():
    writer = StoryWriter()
    brief = NarrativeBrief(
        prompt_or_text="Action scene with moving cars",
        aspect_ratio=VideoAspectRatio.WIDESCREEN_16_9
    )
    sys_prompt = writer._build_system_prompt(brief)
    assert "4-PART KINETIC MOTION PROMPTING" in sys_prompt
    assert "Primary Subject Action" in sys_prompt
    assert "Secondary Interaction" in sys_prompt
    assert "Micro-environmental Physics" in sys_prompt
    assert "Camera Movement" in sys_prompt
