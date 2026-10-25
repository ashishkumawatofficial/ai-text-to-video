"""Integration test for User Story 2: Deterministic Riddle Pipeline."""

import pytest
import os
from core.pipeline import run_pipeline


@pytest.mark.asyncio
async def test_deterministic_riddle_generation(tmp_path):
    output_mp4 = str(tmp_path / "test_riddle_output.mp4")
    manifest = "specs/001-universal-video-pipeline/examples/riddle_manifest.json"

    render_output = await run_pipeline(
        manifest_path=manifest,
        output_path=output_mp4,
        whisper_model="tiny",
        backend="local"
    )

    assert os.path.exists(render_output.file_path)
    assert os.path.getsize(render_output.file_path) > 100000
    assert render_output.resolution == "1080x1920"
    assert render_output.duration_sec == 16.0
