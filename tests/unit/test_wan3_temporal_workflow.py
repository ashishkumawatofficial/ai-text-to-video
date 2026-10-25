import pytest
from core.models import Wan3WorkflowConfig
from core.runpod_client import build_wan3_workflow_payload

def test_wan3_workflow_uses_temporal_video_latents():
    cfg = Wan3WorkflowConfig(
        prompt="Cow sips tea calmly while steam rises. Cinematic tracking shot.",
        width=832,
        height=480,
        duration_frames=33,
        steps=12,
        reference_images=["outputs/temp/test_keyframe.jpg"]
    )
    payload = build_wan3_workflow_payload(cfg)
    
    # Node 6 MUST NOT be standard 2D EmptyLatentImage which causes strobe flickering
    latent_node = payload.get("6", {})
    assert latent_node.get("class_type") != "EmptyLatentImage", (
        "EmptyLatentImage causes strobe flickering by generating independent 2D frames!"
    )
    assert latent_node.get("class_type") == "EmptyHunyuanLatentVideo"
    assert latent_node.get("inputs", {}).get("length") == 33
    assert latent_node.get("inputs", {}).get("batch_size") == 1

def test_wan3_workflow_binds_keyframe_image():
    cfg = Wan3WorkflowConfig(
        prompt="Subject drinks tea at stall",
        width=832,
        height=480,
        duration_frames=65,
        steps=14,
        reference_images=["outputs/temp/approved_keyframe.png"]
    )
    payload = build_wan3_workflow_payload(cfg)
    
    # Verify that reference keyframe is passed and not ignored
    # Check if a LoadImage node exists or image input is bound
    image_nodes = [n for n in payload.values() if n.get("class_type") == "LoadImage"]
    assert len(image_nodes) > 0 or any("approved_keyframe.png" in str(v) for v in payload.values())
