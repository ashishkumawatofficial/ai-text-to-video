import os
import pytest
from unittest.mock import patch, AsyncMock
from core.audio_engine import (
    synthesize_scene_dialogue,
    stitch_beat_audio_tracks,
    resolve_voice_persona,
    DEFAULT_VOICE
)
from core.models import SubtitleTrack, SubtitleWordToken

@pytest.mark.asyncio
async def test_resolve_voice_persona_archetypes():
    cow_profile = resolve_voice_persona("cartoon_animal")
    assert cow_profile["edge_voice"] == "en-US-AnaNeural"
    assert cow_profile["edge_pitch"] == "+20Hz"

    villain_profile = resolve_voice_persona("deep_villain")
    assert villain_profile["edge_pitch"] == "-12Hz"

    kid_profile = resolve_voice_persona("kid")
    assert kid_profile["edge_pitch"] == "+12Hz"

@pytest.mark.asyncio
async def test_synthesize_scene_dialogue_mocked(tmp_path):
    output_mp3 = str(tmp_path / "test_beat_dialogue.mp3")
    
    # Mock synthesize_speech and get_audio_duration_seconds
    with patch("core.audio_engine.synthesize_speech", new_callable=AsyncMock) as mock_synth:
        mock_synth.return_value = output_mp3
        with patch("core.audio_engine.get_audio_duration_seconds", return_value=3.2):
            audio_path, duration, subtitles = await synthesize_scene_dialogue(
                text="Look at that fancy corporate bull!",
                output_audio_path=output_mp3,
                speaker="Cow 1",
                voice_persona="cartoon_animal"
            )
            
            assert audio_path == output_mp3
            assert duration == 3.2
            assert len(subtitles.words) > 0
            mock_synth.assert_called_once()
            call_kwargs = mock_synth.call_args[1]
            assert call_kwargs["voice"] == "cartoon_animal"
            assert "Character speaker: Cow 1" in call_kwargs["prompt_context"]

def test_stitch_beat_audio_tracks_duration(tmp_path):
    output_master = str(tmp_path / "master_vo.mp3")
    # Empty beat tracks should still create a silent track of requested duration
    result = stitch_beat_audio_tracks(
        beat_tracks=[],
        total_duration_sec=5.0,
        output_master_audio_path=output_master
    )
    assert os.path.exists(result)
    assert os.path.getsize(result) > 500
