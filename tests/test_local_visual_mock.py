"""Tests for Local Visual Mock Keyframe Engine (Zero-GPU Fallback)."""

import os
import pytest
from PIL import Image
from core.local_visual_mock import generate_local_keyframe, get_cached_keyframe_path


def test_generate_local_keyframe_creates_valid_image(tmp_path):
    output_img = str(tmp_path / "test_frame.jpg")
    result_path = generate_local_keyframe(
        prompt="A cyber detective in the neon rain looking at a data core",
        scene_id="scene_test_1",
        output_path=output_img,
        width=1080,
        height=1920
    )

    assert os.path.exists(result_path)
    assert os.path.getsize(result_path) > 1000

    # Verify dimensions
    with Image.open(result_path) as img:
        assert img.size == (1080, 1920)


def test_keyframe_caching(tmp_path):
    prompt = "A golden glowing chest opening in a mystical cave"
    cached = get_cached_keyframe_path(prompt, cache_dir=str(tmp_path))
    assert not os.path.exists(cached)

    first_run = generate_local_keyframe(prompt, "scene_1", cached)
    assert os.path.exists(first_run)

    # Second run should return cached immediately
    second_run = generate_local_keyframe(prompt, "scene_1", cached)
    assert second_run == first_run
