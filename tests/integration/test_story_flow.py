"""Integration test for User Story 3: Character Consistency & Story Flow."""

import pytest
import os
from core.pipeline import run_pipeline


@pytest.mark.asyncio
async def test_character_story_flow(tmp_path):
    output_mp4 = str(tmp_path / "test_story_output.mp4")
    manifest = "specs/001-universal-video-pipeline/examples/story_studio_manifest.json"

    render_output = await run_pipeline(
        manifest_path=manifest,
        output_path=output_mp4,
        whisper_model="tiny",
        backend="local"
    )

    assert os.path.exists(render_output.file_path)
    assert os.path.getsize(render_output.file_path) > 50000
    assert render_output.resolution == "1080x1920"
    assert render_output.duration_sec == 7.5
