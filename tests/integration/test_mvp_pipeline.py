"""Integration test for MVP end-to-end video pipeline."""

import pytest
import os
from core.pipeline import run_pipeline
from core.models import Genre


@pytest.mark.asyncio
async def test_end_to_end_mvp_pipeline(tmp_path):
    output_mp4 = str(tmp_path / "test_mvp_output.mp4")
    sample_prompt = "A clever detective solves the mystery of the missing key."

    render_output = await run_pipeline(
        prompt=sample_prompt,
        genre_override=Genre.CINEMATIC_STORY,
        output_path=output_mp4,
        whisper_model="tiny",
        backend="local"
    )

    assert os.path.exists(render_output.file_path)
    assert os.path.getsize(render_output.file_path) > 10000  # Substantial video file
    assert render_output.resolution == "1080x1920"
    assert render_output.fps == 30
    assert render_output.duration_sec > 0
