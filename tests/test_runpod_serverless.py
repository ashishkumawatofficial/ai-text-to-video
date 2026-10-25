"""Unit tests for RunPod Serverless client, payload parsing, and concurrency."""

import os
import json
import base64
import pytest
from unittest.mock import patch, MagicMock

from core.runpod_serverless import (
    RunPodServerlessClient,
    RunPodServerlessError,
)
from core.models import ServerlessJobStatus


def test_serverless_client_initialization():
    client = RunPodServerlessClient(endpoint_id="v2-test123", api_key="rpa_testkey")
    assert client.is_available() is True
    assert client.endpoint_url == "https://api.runpod.ai/v2/v2-test123"
    assert client.headers["Authorization"] == "Bearer rpa_testkey"


@patch("requests.post")
def test_run_job_submission(mock_post):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"id": "job_abc123", "status": "IN_QUEUE"}
    mock_post.return_value = mock_resp

    client = RunPodServerlessClient(endpoint_id="v2-test123", api_key="rpa_testkey")
    job_id = client.run_job(workflow={"1": {"class_type": "KSampler"}})

    assert job_id == "job_abc123"
    assert "job_abc123" in client._active_jobs
    mock_post.assert_called_once()


@patch("requests.get")
def test_poll_job_completion(mock_get):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "id": "job_abc123",
        "status": "COMPLETED",
        "executionTime": 45200,
        "output": {"videos": [{"url": "https://example.com/video.mp4"}]}
    }
    mock_get.return_value = mock_resp

    client = RunPodServerlessClient(endpoint_id="v2-test123", api_key="rpa_testkey")
    client._active_jobs.append("job_abc123")
    
    result = client.poll_job("job_abc123", timeout_sec=5, poll_interval=0.01)
    assert result["status"] == "COMPLETED"
    assert result["executionTime"] == 45200
    assert "job_abc123" not in client._active_jobs


@patch("requests.get")
def test_poll_job_failure_raises_error(mock_get):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "id": "job_fail",
        "status": "FAILED",
        "error": "CUDA out of memory in KSampler"
    }
    mock_get.return_value = mock_resp

    client = RunPodServerlessClient(endpoint_id="v2-test123", api_key="rpa_testkey")
    with pytest.raises(RunPodServerlessError) as exc_info:
        client.poll_job("job_fail", timeout_sec=5, poll_interval=0.01)

    assert "CUDA out of memory" in str(exc_info.value)


def test_payload_parser_base64_data_uri(tmp_path):
    client = RunPodServerlessClient(endpoint_id="v2-test123", api_key="rpa_testkey")
    fake_video = b"\x00\x00\x00\x1cftypisom\x00\x00\x02\x00"
    b64_str = f"data:video/mp4;base64,{base64.b64encode(fake_video).decode('utf-8')}"
    dest = str(tmp_path / "output.mp4")

    out_file = client.parse_and_download_output(b64_str, dest)
    assert os.path.exists(out_file)
    with open(out_file, "rb") as f:
        assert f.read() == fake_video


@patch("requests.get")
def test_payload_parser_url_stream(mock_get, tmp_path):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    fake_video = b"\x00\x00\x00\x1cftypisom\x00\x00\x02\x00"
    mock_resp.iter_content.return_value = [fake_video]
    mock_get.return_value = mock_resp

    client = RunPodServerlessClient(endpoint_id="v2-test123", api_key="rpa_testkey")
    dest = str(tmp_path / "streamed.mp4")

    payload = {"videos": [{"url": "https://runpod-storage.s3.amazonaws.com/wan2_video.mp4"}]}
    out_file = client.parse_and_download_output(payload, dest)

    assert os.path.exists(out_file)
    with open(out_file, "rb") as f:
        assert f.read() == fake_video


@patch("requests.post")
def test_cancel_job(mock_post):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_post.return_value = mock_resp

    client = RunPodServerlessClient(endpoint_id="v2-test123", api_key="rpa_testkey")
    client._active_jobs.append("job_cancel_me")

    success = client.cancel_job("job_cancel_me")
    assert success is True
    assert "job_cancel_me" not in client._active_jobs


@patch("requests.post")
def test_cancel_batch(mock_post):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_post.return_value = mock_resp

    client = RunPodServerlessClient(endpoint_id="v2-test123", api_key="rpa_testkey")
    client._active_jobs.extend(["job_1", "job_2", "job_3"])

    cancelled = client.cancel_batch()
    assert cancelled == ["job_1", "job_2", "job_3"]
    assert len(client._active_jobs) == 0
    assert mock_post.call_count == 3


def test_generate_cost_report():
    from core.models import ServerlessJob
    from core.runpod_serverless import format_multi_worker_status, format_cost_banner

    client = RunPodServerlessClient(endpoint_id="v2-test123", api_key="rpa_testkey")
    jobs = [
        ServerlessJob(job_id="j1", beat_index=0, beat_name="Intro", status=ServerlessJobStatus.COMPLETED, execution_time_ms=75000),
        ServerlessJob(job_id="j2", beat_index=1, beat_name="Build-up", status=ServerlessJobStatus.COMPLETED, execution_time_ms=80000),
        ServerlessJob(job_id="j3", beat_index=2, beat_name="Climax", status=ServerlessJobStatus.COMPLETED, execution_time_ms=70000),
        ServerlessJob(job_id="j4", beat_index=3, beat_name="Ending", status=ServerlessJobStatus.COMPLETED, execution_time_ms=75000),
    ]

    report = client.generate_cost_report(jobs, wall_clock_sec=85.0)

    assert report.total_beats == 4
    assert report.successful_beats == 4
    assert report.wall_clock_duration_sec == 85.0
    assert report.cumulative_gpu_seconds == 300.0  # (75000 + 80000 + 70000 + 75000) / 1000
    # 300s * $0.00021/s = $0.0630
    assert report.estimated_cost_usd == 0.063
    assert report.effective_concurrency == pytest.approx(3.53, rel=0.01)

    # Test status table format
    status_table = format_multi_worker_status(jobs)
    assert "#1" in status_table
    assert "Intro" in status_table
    assert "COMPLETED" in status_table

    # Test cost banner format
    banner = format_cost_banner(report)
    assert "RUNPOD SERVERLESS COMPUTE & COST SUMMARY" in banner
    assert "$0.0630 USD" in banner

