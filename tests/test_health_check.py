"""Tests for RunPod & ComfyUI Endpoint Health Diagnostics."""

import pytest
from unittest.mock import patch, MagicMock
from core.runpod_client import check_endpoint_health
from core.models import RunPodHealthReport


def test_health_check_offline_endpoint():
    # An unreachable URL should return healthy=False with a clean error report
    report = check_endpoint_health("http://127.0.0.1:9999")
    assert isinstance(report, RunPodHealthReport)
    assert not report.is_reachable
    assert "Unreachable" in report.status_summary or "Offline" in report.status_summary


def test_health_check_online_endpoint_mocked():
    mock_stats_resp = MagicMock()
    mock_stats_resp.status_code = 200
    mock_stats_resp.json.return_value = {
        "system": {
            "os": "linux",
            "python_version": "3.10.12",
            "comfyui_version": "0.3.10"
        },
        "devices": [
            {
                "name": "NVIDIA GeForce RTX 4090",
                "type": "cuda",
                "vram_total": 25757220864,
                "vram_free": 21474836480
            }
        ]
    }

    mock_objects_resp = MagicMock()
    mock_objects_resp.status_code = 200
    mock_objects_resp.json.return_value = {
        "CheckpointLoaderSimple": {
            "input": {
                "required": {
                    "ckpt_name": [
                        ["wan3.0_i2v_14b_fp8.safetensors", "flux1-schnell.safetensors"],
                        {}
                    ]
                }
            }
        }
    }

    def mock_get(url, *args, **kwargs):
        if "system_stats" in url:
            return mock_stats_resp
        if "object_info" in url:
            return mock_objects_resp
        return MagicMock(status_code=404)

    with patch("requests.get", side_effect=mock_get):
        report = check_endpoint_health("http://mock-runpod-comfy:8188")
        assert report.is_reachable
        assert report.gpu_name == "NVIDIA GeForce RTX 4090"
        assert report.vram_total_gb == pytest.approx(24.0, rel=0.1)
        assert report.has_wan3
        assert "Healthy" in report.status_summary
