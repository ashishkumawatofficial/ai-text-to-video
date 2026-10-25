"""Tri-Strategy Anti-Reroll Visual Routing Engine with Multi-Tier Cloud & Local Cascading."""

from __future__ import annotations
import os
from typing import Optional
from core.models import (
    StoryboardBeat,
    VisualStrategyRoute,
    Genre,
    ImageRole,
    ImageAsset,
    BackendExecutionStrategy,
)
from core.runpod_client import ComfyUIClient


def select_beat_strategy(
    genre: Genre,
    beat_name: str,
    has_sprite_assets: bool = False,
    has_dual_anchor_frames: bool = False
) -> VisualStrategyRoute:
    """Classifies and assigns the anti-reroll visual strategy for a storyboard beat."""
    # Logic & Riddles
    if genre == Genre.RIDDLE:
        name_lower = beat_name.lower()
        if any(keyword in name_lower for keyword in ["hook", "question", "pause", "countdown", "think"]):
            return VisualStrategyRoute.PROGRAMMATIC_HYBRID
        
        if "reveal" in name_lower or "solution" in name_lower:
            if has_sprite_assets:
                return VisualStrategyRoute.PROGRAMMATIC_HYBRID
            if has_dual_anchor_frames:
                return VisualStrategyRoute.START_END_INTERPOLATION
            return VisualStrategyRoute.PROGRAMMATIC_HYBRID

    # Dual-Frame Interpolation for verified state transitions
    if has_dual_anchor_frames:
        return VisualStrategyRoute.START_END_INTERPOLATION

    # Default for narrative and action
    return VisualStrategyRoute.FLAT_RATE_DIFFUSION


def route_and_execute_beat(
    beat: StoryboardBeat,
    output_video_path: str,
    comfy_client: Optional[ComfyUIClient] = None,
    backend: str = "auto",
    serverless_client: Optional[Any] = None,
    force_serverless_error: bool = False,
) -> str:
    """Routes the beat based on its visual strategy across Serverless, Pod, and Local tiers."""
    os.makedirs(os.path.dirname(os.path.abspath(output_video_path)), exist_ok=True)

    if beat.visual_strategy == VisualStrategyRoute.PROGRAMMATIC_HYBRID:
        beat.output_video_path = output_video_path
        return output_video_path

    if beat.visual_strategy == VisualStrategyRoute.START_END_INTERPOLATION:
        start_frame = next((a.file_path for a in beat.image_assets if a.role == ImageRole.START_FRAME), None)
        end_frame = next((a.file_path for a in beat.image_assets if a.role == ImageRole.END_FRAME), None)
        if comfy_client and comfy_client.is_available() and start_frame and end_frame:
            workflow = {
                "start_image": start_frame,
                "end_image": end_frame,
                "duration_frames": int(beat.duration_sec * 30)
            }
            return comfy_client.execute_video_workflow(workflow, output_video_path)
        else:
            beat.output_video_path = output_video_path
            return output_video_path

    # Strategy: FLAT_RATE_DIFFUSION
    if backend != "local":
        # Tier 1: RunPod Serverless
        should_try_serverless = backend in ("auto", "serverless") and not force_serverless_error
        if should_try_serverless:
            try:
                from core.runpod_serverless import RunPodServerlessClient
                sl_client = serverless_client or RunPodServerlessClient()
                if sl_client.is_available():
                    init_image = next((a.file_path for a in beat.image_assets if a.role == ImageRole.START_FRAME), None)
                    from core.runpod_client import build_wan3_workflow_payload, Wan3WorkflowConfig
                    safe_frames = 17 if beat.duration_sec <= 4.0 else 33
                    wan_cfg = Wan3WorkflowConfig(
                        prompt=beat.visual_prompt,
                        width=832,
                        height=480,
                        duration_frames=safe_frames,
                        steps=12,
                        reference_images=[init_image] if init_image else [],
                    )
                    workflow = build_wan3_workflow_payload(wan_cfg)
                    res = sl_client.execute_video_job(workflow, output_video_path)
                    beat.output_video_path = res
                    return res
            except Exception as e:
                print(f"      ⚠️ Serverless execution unavailable ({e}). Cascading to Tier 2: Dedicated Pod.")

        # Tier 2: Dedicated RunPod ComfyUI Pod (port 8188)
        should_try_pod = backend in ("auto", "pod")
        if should_try_pod:
            client = comfy_client or ComfyUIClient()
            if client.is_available():
                init_image = next((a.file_path for a in beat.image_assets if a.role == ImageRole.START_FRAME), None)
                try:
                    from core.runpod_client import build_wan3_workflow_payload, Wan3WorkflowConfig
                    safe_frames = 17 if beat.duration_sec <= 4.0 else 33
                    wan_cfg = Wan3WorkflowConfig(
                        prompt=beat.visual_prompt,
                        width=832,
                        height=480,
                        duration_frames=safe_frames,
                        steps=12,
                        reference_images=[init_image] if init_image else [],
                    )
                    workflow = build_wan3_workflow_payload(wan_cfg)
                    from core.config import get_comfy_timeout_sec
                    res = client.execute_video_workflow(workflow, output_video_path, timeout_sec=get_comfy_timeout_sec())
                    beat.output_video_path = res
                    return res
                except Exception as e:
                    print(f"      ⚠️ ComfyUI remote execution failed ({type(e).__name__}: {e}). Engaging local fallback.")

    # Tier 3: Zero-GPU Local Keyframe Plate Engine
    from core.local_visual_mock import generate_local_keyframe, get_cached_keyframe_path
    has_existing_img = any(os.path.exists(a.file_path) for a in beat.image_assets)
    if not has_existing_img:
        prompt_text = beat.visual_prompt or beat.dialogue_text or beat.name
        keyframe_file = get_cached_keyframe_path(prompt_text)
        generate_local_keyframe(
            prompt=prompt_text,
            scene_id=f"scene_{beat.beat_index}",
            output_path=keyframe_file
        )
        beat.image_assets.append(
            ImageAsset(
                file_path=keyframe_file,
                role=ImageRole.START_FRAME,
                source="local_mock"
            )
        )
        print(f"      🎨 [Local Keyframe] Generated scene illustration: {os.path.basename(keyframe_file)}")

    beat.output_video_path = output_video_path
    return output_video_path
