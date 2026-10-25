"""Unit tests for Sound Effects Mixer."""

import pytest
from core.sfx_mixer import resolve_sfx_file, resolve_music_file, build_audio_asset


def test_sfx_resolution():
    tick_path = resolve_sfx_file("tick")
    assert tick_path is not None
    assert tick_path.endswith("clock_tick.wav")

    whoosh_path = resolve_sfx_file("whoosh")
    assert whoosh_path is not None
    assert whoosh_path.endswith("whoosh.wav")


def test_music_resolution():
    music_path = resolve_music_file("bgm_ambient.wav")
    assert music_path is not None
    assert music_path.endswith("bgm_ambient.wav")


def test_build_audio_asset():
    asset = build_audio_asset(
        voiceover_path="/tmp/fake_vo.mp3",
        music_name="bgm_ambient.wav",
        sfx_requests=[
            {"sfx_name": "tick", "offset_sec": 1.5, "volume": 0.8}
        ],
        fps=30
    )

    assert asset.voiceover_path == "/tmp/fake_vo.mp3"
    assert asset.music_path is not None
    assert len(asset.sfx_cues) == 1
    assert asset.sfx_cues[0].start_frame == 45
    assert asset.sfx_cues[0].volume == 0.8
