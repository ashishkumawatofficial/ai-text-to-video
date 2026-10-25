"""Integration test for User Story 4: High-Octane Action & Chaining."""

import pytest
import os
from core.pipeline import run_pipeline


@pytest.mark.asyncio
async def test_action_pipeline_with_chaining(tmp_path):
    output_mp4 = str(tmp_path / "test_action_output.mp4")
    manifest = "specs/001-universal-video-pipeline/examples/action_manifest.json"

    render_output = await run_pipeline(
        manifest_path=manifest,
        output_path=output_mp4,
        whisper_model="tiny",
        backend="local"
    )

    assert os.path.exists(render_output.file_path)
    assert os.path.getsize(render_output.file_path) > 50000
    assert render_output.resolution == "1080x1920"
    assert render_output.duration_sec == 6.5
