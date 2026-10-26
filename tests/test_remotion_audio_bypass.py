"""Unit tests for Remotion audio props generation, native clip audio detection, and voiceover bypass."""

import pytest
from core.models import (
    VideoProject,
    StoryboardBeat,
    Genre,
    VideoAudioMode,
)
from core.remotion_bridge import build_remotion_props
from core.prompt_adapter import PromptAdapter


def test_build_remotion_props_native_clip_audio_detection():
    beat_with_audio = StoryboardBeat(
        beat_index=0,
        name="Scene With Native Audio",
        duration_sec=4.0,
        visual_prompt="A hero shouts a warning in the storm",
        dialogue_text="Look out, the dam is breaking!",
        output_video_path="/tmp/fake_native_audio.mp4",
    )
    # Set native audio mode
    setattr(beat_with_audio, "audio_mode", VideoAudioMode.NATIVE_CLIP_AUDIO)
    setattr(beat_with_audio, "has_native_audio", True)

    beat_without_audio = StoryboardBeat(
        beat_index=1,
        name="Scene Without Audio",
        duration_sec=3.0,
        visual_prompt="Camera pans across flooding river",
        output_video_path="/tmp/fake_silent.mp4",
    )

    proj = VideoProject(
        title="Test Project Audio",
        genre=Genre.CINEMATIC_STORY,
        scenes=[beat_with_audio, beat_without_audio],
    )

    props = build_remotion_props(proj)

    scenes = props["scenes"]
    assert len(scenes) == 2

    # First scene must have native audio active
    assert scenes[0]["hasClipAudio"] is True
    assert scenes[0]["audioVolume"] == 1.0

    # Second scene must have native audio inactive
    assert scenes[1]["hasClipAudio"] is False
    assert scenes[1]["audioVolume"] == 0.0


def test_prompt_adapter_injects_model_specific_audio_tags():
    adapter = PromptAdapter()

    # MiniMax audio tag test: should wrap dialogue in <d>...</d>
    res_minimax = adapter.adapt_prompt(
        prompt="A space captain issues a final order from the bridge.",
        model_id="minimax-h3",
        audio_mode=VideoAudioMode.NATIVE_CLIP_AUDIO,
        dialogue_text="Engage warp drive immediately.",
    )
    assert "<d>Engage warp drive immediately.</d>" in res_minimax.adapted_prompt

    # Kling spoken line cue test
    res_kling = adapter.adapt_prompt(
        prompt="A medieval knight speaks to his army.",
        model_id="kling-v1.5",
        audio_mode=VideoAudioMode.NATIVE_CLIP_AUDIO,
        dialogue_text="Hold the line until dawn!",
    )
    assert "Spoken line:" in res_kling.adapted_prompt
    assert "Hold the line until dawn!" in res_kling.adapted_prompt
