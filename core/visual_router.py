"""Tri-Strategy Anti-Reroll Visual Routing Engine with Multi-Tier Cloud & Local Cascading."""

from __future__ import annotations
import os
import asyncio
import concurrent.futures
from typing import Optional, Any, List
from core.models import (
    StoryboardBeat,
    VisualStrategyRoute,
    Genre,
    ImageRole,
    ImageAsset,
    BackendExecutionStrategy,
    ProviderId,
    VideoGenerationModality,
    VideoAudioMode,
    VideoGenerationRequest,
    RenderingJobTicket,
)
from core.runpod_client import ComfyUIClient
from core.cost_arbitrage import CostArbitrageEngine
from core.provider_registry import get_model_profile, get_providers_for_model, MODEL_PROFILES_REGISTRY


def _run_async(coro):
    """Executes an async coroutine synchronously and safely regardless of current event loop."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(asyncio.run, coro).result()
    else:
        return asyncio.run(coro)


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
    model_id: Optional[str] = None,
    provider_override: Optional[ProviderId] = None,
    arbitrage_engine: Optional[CostArbitrageEngine] = None,
    modality: Optional[VideoGenerationModality] = None,
    audio_mode: Optional[VideoAudioMode] = None,
    resolution: Optional[str] = "720p",
    allow_cascade: bool = True,
    progress_cb: Optional[Any] = None,
) -> str:
    """Routes the beat based on its visual strategy across Serverless, Pod, Multi-Provider, and Local tiers."""
    os.makedirs(os.path.dirname(os.path.abspath(output_video_path)), exist_ok=True)

    if beat.visual_strategy == VisualStrategyRoute.PROGRAMMATIC_HYBRID:
        beat.output_video_path = output_video_path
        return output_video_path

    start_frame = next((a.file_path for a in beat.image_assets if a.role == ImageRole.START_FRAME), None)
    end_frame = next((a.file_path for a in beat.image_assets if a.role == ImageRole.END_FRAME), None)
    ref_images = [a.file_path for a in beat.image_assets if a.role in (ImageRole.STYLE_REFERENCE, ImageRole.CHARACTER_IMAGE, ImageRole.SCENE_IMAGE, ImageRole.STORYBOARD_IMAGE)]

    if beat.visual_strategy == VisualStrategyRoute.START_END_INTERPOLATION:
        if backend in ("channel_2", "multi_provider") or (model_id and model_id in MODEL_PROFILES_REGISTRY):
            pass  # Fall through to Channel 2 multi-provider execution
        elif comfy_client and comfy_client.is_available() and start_frame and end_frame:
            workflow = {
                "start_image": start_frame,
                "end_image": end_frame,
                "duration_frames": int(beat.duration_sec * 30)
            }
            return comfy_client.execute_video_workflow(workflow, output_video_path)
        else:
            beat.output_video_path = output_video_path
            return output_video_path

    # Channel 2: Multi-Model Gateway Arbitrage (fal.ai, apidot.ai, kie.ai)
    if backend in ("channel_2", "multi_provider", "api") or (model_id and model_id in MODEL_PROFILES_REGISTRY):
        target_model_id = model_id or getattr(beat, "model_id", "kling-v1.5") or "kling-v1.5"
        profile = get_model_profile(target_model_id) or MODEL_PROFILES_REGISTRY.get("kling-v1.5")
        if profile:
            engine = arbitrage_engine or CostArbitrageEngine()
            
            # Determine generation modality
            if modality:
                target_modality = modality
            elif getattr(beat, "modality", None) == "t2v":
                target_modality = VideoGenerationModality.TEXT_TO_VIDEO
            elif getattr(beat, "modality", None) == "i2v":
                target_modality = VideoGenerationModality.IMAGE_TO_VIDEO
            elif getattr(beat, "modality", None) == "interpolation":
                target_modality = VideoGenerationModality.START_END_INTERPOLATION
            elif beat.visual_strategy == VisualStrategyRoute.START_END_INTERPOLATION and start_frame and end_frame:
                target_modality = VideoGenerationModality.START_END_INTERPOLATION
            elif start_frame:
                target_modality = VideoGenerationModality.IMAGE_TO_VIDEO
            else:
                target_modality = VideoGenerationModality.TEXT_TO_VIDEO

            # Determine audio mode
            target_audio = audio_mode or getattr(beat, 'audio_mode', VideoAudioMode.EXTERNAL_SYNTHESIS)
            target_res = resolution or getattr(beat, "resolution", "720p") or "720p"

            # Determine candidate providers pre-sorted by lowest cost satisfying all parameters
            try:
                ranked = _run_async(engine.get_ranked_quotes(
                    target_model_id,
                    duration_sec=beat.duration_sec,
                    resolution=target_res,
                    has_native_audio=(target_audio == VideoAudioMode.NATIVE_CLIP_AUDIO)
                ))
                available_ranked = [q.provider_id for q in ranked if q.is_available]
            except Exception as e:
                print(f"      ⚠️ Failed fetching live quotes for {target_model_id}: {e}")
                available_ranked = []

            if not available_ranked:
                available_ranked = get_providers_for_model(target_model_id)

            if provider_override and provider_override != ProviderId.AUTO:
                # If creator set a specific preferred provider, try it first
                fallback_ranked = [p for p in available_ranked if p != provider_override] if allow_cascade else []
                candidates = [provider_override] + fallback_ranked
            else:
                # Pure Cost Arbitrage: Attempt 1 is cheapest, Attempt 2 is next cheapest, etc.
                candidates = available_ranked if allow_cascade else available_ranked[:1]

            from core.prompt_adapter import PromptCompiler
            prompt_compiler = PromptCompiler()
            raw_prompt = getattr(beat, "motion_prompt", None) or beat.visual_prompt or beat.name
            compiled_prompt = prompt_compiler.compile_beat(
                prompt=raw_prompt,
                model_id=target_model_id,
                modality=target_modality,
                audio_mode=target_audio,
                dialogue_text=beat.dialogue_text,
                genre=getattr(beat, "genre", None),
                art_style=getattr(beat, "art_style", None),
            )

            # Pass start_frame if I2V or interpolation modality is active or supported
            effective_start_frame = start_frame if (target_modality in (VideoGenerationModality.IMAGE_TO_VIDEO, VideoGenerationModality.START_END_INTERPOLATION) or profile.supports_i2v) else None
            effective_end_frame = end_frame if (target_modality == VideoGenerationModality.START_END_INTERPOLATION or profile.supports_dual_frame) else None
            effective_ref_images = (
                ref_images[:profile.max_reference_images]
                if (profile.supports_reference_images and profile.max_reference_images > 0)
                else []
            )

            req = VideoGenerationRequest(
                project_id="proj_default",
                beat_index=beat.beat_index,
                model_profile=profile,
                prompt=compiled_prompt.positive_prompt,
                negative_prompt=compiled_prompt.negative_prompt,
                start_frame_path=effective_start_frame,
                end_frame_path=effective_end_frame,
                reference_image_paths=effective_ref_images,
                reference_assets=effective_ref_images,
                duration_sec=beat.duration_sec,
                aspect_ratio="16:9",
                resolution=target_res,
                audio_mode=target_audio,
                dialogue_text=beat.dialogue_text,
                selected_provider_id=provider_override,
                allow_provider_cascade=allow_cascade,
            )

            try:
                def _on_arbitrage_progress(info: Any):
                    if progress_cb:
                        try:
                            s = info.get("status", "IN_PROGRESS")
                            pct = info.get("progress_percent", 50)
                            progress_cb(beat.beat_index, beat.name, f"{s}_{pct}")
                        except Exception:
                            pass

                ticket = _run_async(engine.execute_with_cascade(
                    req,
                    candidates,
                    output_video_path,
                    progress_callback=_on_arbitrage_progress if progress_cb else None
                ))
                beat.output_video_path = ticket.output_video_path or output_video_path
                return beat.output_video_path
            except Exception as e:
                print(f"      ⚠️ Channel 2 multi-provider cascade failed ({e}). Strict isolation: skipping Channel 1 (RunPod).")
                # Strict Channel 2 isolation: never route to Channel 1 (RunPod / ComfyUI)
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
                beat.output_video_path = output_video_path
                return output_video_path

    # If backend is explicitly channel_2/multi_provider, do NOT fall through to RunPod
    if backend in ("channel_2", "multi_provider", "api"):
        beat.output_video_path = output_video_path
        return output_video_path
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
