"""Unit tests for VideoUpscaler 4K super-resolution workflow."""

import os
import subprocess
import pytest
from core.video_upscaler import VideoUpscaler


@pytest.fixture
def test_clip(tmp_path):
    input_file = str(tmp_path / "test_input_720p.mp4")
    # Generate 1-second 720p test video
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi",
        "-i", "testsrc=duration=1:size=1280x720:rate=30",
        "-c:v", "libx264",
        input_file
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return input_file


def test_upscale_to_4k(test_clip, tmp_path):
    upscaler = VideoUpscaler()
    output_4k = str(tmp_path / "upscaled_4k.mp4")

    res = upscaler.upscale_video(
        input_path=test_clip,
        output_path=output_4k,
        target_resolution="4k",
        engine="real_esrgan",
    )

    assert os.path.exists(res)
    assert os.path.getsize(res) > 0

    # Probe resolution with ffprobe
    cmd = [
        "ffprobe", "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=width,height",
        "-of", "csv=s=x:p=0",
        res
    ]
    probe_res = subprocess.check_output(cmd).decode().strip()
    assert probe_res == "3840x2160"
