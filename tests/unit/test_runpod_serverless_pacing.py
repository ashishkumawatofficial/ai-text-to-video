import os
import pytest
from core.runpod_serverless import calculate_safe_video_frames, ensure_video_duration_coverage

def test_calculate_safe_video_frames():
    # 4k + 1 rule: 17, 33, 49, 65, 81 frames at 16 fps
    # 1.0s -> ~16 frames -> returns 17
    assert calculate_safe_video_frames(1.0) == 17
    # 2.0s -> ~32 frames -> returns 33
    assert calculate_safe_video_frames(2.0) == 33
    # 3.0s -> ~48 frames -> returns 49
    assert calculate_safe_video_frames(3.0) == 49
    # 4.0s -> ~64 frames -> returns 65
    assert calculate_safe_video_frames(4.0) == 65
    # 5.0s -> ~80 frames -> returns 81
    assert calculate_safe_video_frames(5.0) == 81
    # 6.0s -> >80 frames -> returns 81
    assert calculate_safe_video_frames(6.0) == 81

def test_ensure_video_duration_coverage_nonexistent():
    # Gracefully returns path if file does not exist
    res = ensure_video_duration_coverage("nonexistent.mp4", 5.0)
    assert res == "nonexistent.mp4"
