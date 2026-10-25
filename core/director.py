"""Autonomous Director Engine: deconstructs raw concepts/prompts into storyboard beats."""

from __future__ import annotations
import re
from typing import Optional, List
from core.models import (
    VideoProject,
    Genre,
    IngestionMode,
    StoryboardBeat,
    VisualStrategyRoute,
    AudioCue
)


def classify_genre_from_prompt(prompt: str) -> Genre:
    """Classifies the genre from semantic signals in the prompt text."""
    lower = prompt.lower()
    # Riddle keywords
    if any(k in lower for k in ["riddle", "puzzle", "can you solve", "guess", "which one", "how many", "glasses", "doors"]):
        return Genre.RIDDLE

    # Action keywords
    if any(k in lower for k in ["fight", "battle", "combat", "chase", "sword", "ninja", "explosion", "strike", "samurai", "cyberpunk"]):
        return Genre.ACTION

    # Default to cinematic story
    return Genre.CINEMATIC_STORY


def deconstruct_prompt_to_storyboard(
    prompt: str,
    target_genre: Optional[Genre] = None,
    fps: int = 30
) -> VideoProject:
    """Deconstructs a concept prompt into structured storyboard beats and dialogue."""
    genre = target_genre or classify_genre_from_prompt(prompt)

    if genre == Genre.RIDDLE:
        title = "Brain Teaser Challenge"
        scenes = [
            StoryboardBeat(
                beat_index=1,
                name="Riddle Hook",
                duration_sec=4.0,
                visual_strategy=VisualStrategyRoute.PROGRAMMATIC_HYBRID,
                visual_prompt="Close up of puzzle setup with clean lighting on tabletop",
                dialogue_text=prompt if "?" in prompt else f"{prompt}. Can you solve this puzzle?",
                sound_effects=[AudioCue(sfx_name="whoosh", offset_sec=0.1)]
            ),
            StoryboardBeat(
                beat_index=2,
                name="Thinking Pause",
                duration_sec=7.0,
                visual_strategy=VisualStrategyRoute.PROGRAMMATIC_HYBRID,
                visual_prompt="Static focus with animated countdown timer clock",
                dialogue_text="Pause the video and think. Comment your answer below!",
                sound_effects=[
                    AudioCue(sfx_name="clock_tick", offset_sec=1.0),
                    AudioCue(sfx_name="clock_tick", offset_sec=2.0),
                    AudioCue(sfx_name="clock_tick", offset_sec=3.0),
                    AudioCue(sfx_name="clock_tick", offset_sec=4.0),
                    AudioCue(sfx_name="clock_tick", offset_sec=5.0),
                    AudioCue(sfx_name="clock_tick", offset_sec=6.0)
                ]
            ),
            StoryboardBeat(
                beat_index=3,
                name="Solution Reveal",
                duration_sec=4.5,
                visual_strategy=VisualStrategyRoute.PROGRAMMATIC_HYBRID,
                visual_prompt="Clear demonstration of the correct move with highlight badges",
                dialogue_text="Here is the solution! Did you get it right?",
                sound_effects=[AudioCue(sfx_name="solved_chime", offset_sec=0.2)]
            )
        ]

    elif genre == Genre.ACTION:
        title = "Kinetic Action Sequence"
        scenes = [
            StoryboardBeat(
                beat_index=1,
                name="The Confrontation",
                duration_sec=3.0,
                visual_strategy=VisualStrategyRoute.FLAT_RATE_DIFFUSION,
                visual_prompt="Low angle cinematic camera tracking hero stepping into neon shadows",
                dialogue_text="When shadows gather, only the decisive survive.",
                sound_effects=[AudioCue(sfx_name="whoosh", offset_sec=0.2)]
            ),
            StoryboardBeat(
                beat_index=2,
                name="The Strike",
                duration_sec=3.5,
                visual_strategy=VisualStrategyRoute.FLAT_RATE_DIFFUSION,
                visual_prompt="High kinetic whip pan as warrior lunges with energy sparks and camera shake",
                dialogue_text="One motion. Zero hesitation.",
                sound_effects=[AudioCue(sfx_name="whoosh", offset_sec=0.5)]
            )
        ]

    else:
        # Cinematic Story
        title = "Cinematic Tale"
        clean_concept = prompt.rstrip(".!?")
        scenes = [
            StoryboardBeat(
                beat_index=1,
                name="The Call",
                duration_sec=3.5,
                visual_strategy=VisualStrategyRoute.FLAT_RATE_DIFFUSION,
                visual_prompt=f"Atmospheric cinematic wide shot of {clean_concept}, establishing scene, 8k photorealistic vertical 9:16",
                dialogue_text=f"{clean_concept}. Every journey begins with a single curious glance.",
                sound_effects=[AudioCue(sfx_name="whoosh", offset_sec=0.1)]
            ),
            StoryboardBeat(
                beat_index=2,
                name="The Discovery",
                duration_sec=4.0,
                visual_strategy=VisualStrategyRoute.FLAT_RATE_DIFFUSION,
                visual_prompt=f"Dramatic cinematic close-up revealing discovery and climax of {clean_concept}, glowing detail, 8k vertical 9:16",
                dialogue_text="And what was found changed everything.",
                sound_effects=[AudioCue(sfx_name="solved_chime", offset_sec=0.5)]
            )
        ]

    return VideoProject(
        title=title,
        genre=genre,
        ingestion_mode=IngestionMode.AUTONOMOUS_DIRECTOR,
        fps=fps,
        scenes=scenes
    )
