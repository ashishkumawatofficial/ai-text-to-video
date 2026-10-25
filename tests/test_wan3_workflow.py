"""Tests for Wan 3.0 Omni-Reference ComfyUI Workflow Recipe."""

import os
import json
import pytest
from core.models import Wan3WorkflowConfig
from core.runpod_client import build_wan3_workflow_payload


def test_wan3_workflow_json_exists():
    workflow_path = os.path.join(
        os.path.dirname(__file__), "..", "core", "workflows", "wan3_omni_reference.json"
    )
    assert os.path.exists(workflow_path)
    with open(workflow_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert isinstance(data, dict)
    assert len(data) > 0


def test_wan3_workflow_payload_binding():
    config = Wan3WorkflowConfig(
        prompt="A cyber detective steps through neon fog",
        negative_prompt="blurry, distorted",
        duration_frames=180,
        reference_images=["ref1.png", "ref2.png", "ref3.png"]
    )

    payload = build_wan3_workflow_payload(config)
    assert isinstance(payload, dict)

    # Check prompt injected into CLIPTextEncode node
    clip_nodes = [node for node in payload.values() if node.get("class_type") == "CLIPTextEncode"]
    assert any("cyber detective" in str(node.get("inputs", {}).get("text", "")) for node in clip_nodes)

    # Check latent video duration
    latent_nodes = [node for node in payload.values() if "Latent" in node.get("class_type", "")]
    assert any(node.get("inputs", {}).get("length") == 180 or node.get("inputs", {}).get("duration_frames") == 180 for node in latent_nodes)
