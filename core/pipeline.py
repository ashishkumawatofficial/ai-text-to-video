"""Main Pipeline Orchestrator for the Universal Video Pipeline."""

from __future__ import annotations
import os
import sys
import time
import asyncio
import argparse
from typing import Optional

from core.models import (
    VideoProject,
    Genre,
    IngestionMode,
    RenderOutput
)
from core.director import deconstruct_prompt_to_storyboard
from core.manifest_parser import load_manifest_from_file
from core.audio_engine import generate_narration_with_subtitles
from core.sfx_mixer import build_audio_asset
from core.chain_manager import chain_shots
from core.visual_router import route_and_execute_beat
from core.remotion_bridge import render_project_to_video


async def run_pipeline(
    prompt: Optional[str] = None,
    manifest_path: Optional[str] = None,
    genre_override: Optional[Genre] = None,
    aspect_ratio: str = "9:16",
    output_path: str = "outputs/final_video.mp4",
    voice: str = "en-US-ChristopherNeural",
    whisper_model: str = "tiny",
    backend: str = "auto",
) -> RenderOutput:
    """Executes the universal video pipeline end-to-end."""
    start_time = time.time()
    print("🎬 Starting Universal Video Generation Pipeline...")

    # 1. Project Ingestion
    if manifest_path:
        print(f"📄 Loading Directed Studio Manifest: {manifest_path}")
        project = load_manifest_from_file(manifest_path)
    elif prompt:
        print(f"🧠 Deconstructing Concept Prompt: '{prompt}'")
        project = deconstruct_prompt_to_storyboard(prompt, target_genre=genre_override)
    else:
        raise ValueError("Must provide either a prompt or a manifest_path")

    if genre_override:
        project.genre = genre_override

    if aspect_ratio:
        from core.models import ASPECT_RATIO_RESOLUTIONS
        project.aspect_ratio = aspect_ratio
        if aspect_ratio in ASPECT_RATIO_RESOLUTIONS:
            project.width, project.height = ASPECT_RATIO_RESOLUTIONS[aspect_ratio]


    print(f"✨ Project: '{project.title}' | Genre: {project.genre.value} | Scenes: {len(project.scenes)}")

    # 2. Audio & Narration Synthesis
    combined_dialogue = " ".join([b.dialogue_text for b in project.scenes if b.dialogue_text]).strip()
    if not combined_dialogue:
        combined_dialogue = f"Welcome to this {project.genre.value} experience."

    temp_audio_dir = os.path.abspath(os.path.join("outputs", "temp"))
    os.makedirs(temp_audio_dir, exist_ok=True)
    temp_vo_path = os.path.join(temp_audio_dir, f"vo_{project.id[:8]}.mp3")

    print("🎙️ Synthesizing Voiceover & Extracting Subtitle Timestamps...")
    vo_path, subtitles = await generate_narration_with_subtitles(
        text=combined_dialogue,
        output_audio_path=temp_vo_path,
        voice=voice,
        prompt_context=project.title,
        whisper_model_size=whisper_model
    )
    project.subtitles = subtitles
    print(f"📝 Subtitle Tokens Extracted: {len(subtitles.words)} words aligned")

    # 3. Audio & SFX Assembly
    all_sfx_requests = []
    current_time_offset = 0.0
    for beat in project.scenes:
        for cue in beat.sound_effects:
            all_sfx_requests.append({
                "sfx_name": cue.sfx_name,
                "offset_sec": current_time_offset + cue.offset_sec,
                "volume": cue.volume
            })
        current_time_offset += beat.duration_sec

    project.audio = build_audio_asset(
        voiceover_path=vo_path,
        music_name="bgm_ambient.wav",
        sfx_requests=all_sfx_requests,
        fps=project.fps
    )

    # 4. Visual Routing & Scene Preparation
    from core.runpod_serverless import RunPodServerlessClient
    serverless_client = RunPodServerlessClient()
    is_test_mode = os.environ.get("TEST_MODE") == "1"
    use_serverless = (backend == "serverless") or (backend == "auto" and serverless_client.is_available() and not is_test_mode)
    serverless_succeeded = False

    if use_serverless and serverless_client.is_available():
        print("⚡ [Serverless Dispatch] Rendering all visual beats concurrently...")
        try:
            def _progress_cb(idx: int, name: str, status: str):
                print(f"   [Beat {idx+1}] '{name}' ➔ {status}")

            cost_report = await serverless_client.dispatch_parallel_beats(
                beats=project.scenes,
                output_dir=temp_audio_dir,
                aspect_ratio=project.aspect_ratio.value if hasattr(project.aspect_ratio, "value") else str(project.aspect_ratio),
                progress_cb=_progress_cb
            )
            from core.runpod_serverless import format_cost_banner
            print(format_cost_banner(cost_report))
            serverless_succeeded = True
        except Exception as e:
            print(f"   ⚠️ Serverless batch execution failed ({e}). Falling back to dedicated pod/local cascade.")

    if not serverless_succeeded:
        print("🎨 Routing Visual Scenes via Tri-Strategy Engine...")
        prev_clip_path = None
        for beat in project.scenes:
            if beat.output_video_path and os.path.exists(beat.output_video_path):
                prev_clip_path = beat.output_video_path
                continue

            if beat.continuity.chain_from_previous and prev_clip_path and os.path.exists(prev_clip_path):
                print(f"   🔗 Chaining Frame -1 of previous clip into Frame 0 for Beat {beat.beat_index}")
                chain_shots(prev_clip_path, beat, temp_dir=temp_audio_dir)

            clip_dest = os.path.join(temp_audio_dir, f"beat_{beat.beat_index}.mp4")
            route_and_execute_beat(beat, output_video_path=clip_dest, backend=backend)
            if beat.output_video_path and os.path.exists(beat.output_video_path):
                prev_clip_path = beat.output_video_path

            print(f"   [Beat {beat.beat_index}] '{beat.name}' ➔ Route: {beat.visual_strategy.value}")

    # 5. Remotion Master Compilation
    abs_output = os.path.abspath(output_path)
    print(f"🚀 Compiling Master Video in Remotion ➔ {abs_output}")
    render_project_to_video(project, abs_output)

    total_time = round(time.time() - start_time, 2)
    file_size = os.path.getsize(abs_output) if os.path.exists(abs_output) else 0

    print(f"✅ Video Production Complete! File: {abs_output} ({round(file_size / (1024*1024), 2)} MB in {total_time}s)")

    return RenderOutput(
        file_path=abs_output,
        resolution=f"{project.width}x{project.height}",
        fps=project.fps,
        duration_sec=current_time_offset,
        file_size_bytes=file_size,
        render_duration_sec=total_time
    )


def main():
    parser = argparse.ArgumentParser(description="Universal Multi-Genre Video Generation Pipeline")
    parser.add_argument("--prompt", type=str, help="Natural language concept or story prompt")
    parser.add_argument("--manifest", type=str, help="Path to JSON storyboard manifest")
    parser.add_argument("--genre", type=str, choices=["riddle", "cinematic_story", "action"], help="Genre override")
    parser.add_argument("--output", type=str, default="outputs/final_video.mp4", help="Output MP4 filepath")
    parser.add_argument("--voice", type=str, default="en-US-ChristopherNeural", help="Edge-TTS voice")
    parser.add_argument("--whisper-model", type=str, default="tiny", help="Faster-Whisper model size")
    parser.add_argument("--backend", "-b", choices=["auto", "serverless", "pod", "local"], default="auto", help="Visual backend")

    args = parser.parse_args()

    genre_enum = Genre(args.genre) if args.genre else None

    asyncio.run(
        run_pipeline(
            prompt=args.prompt,
            manifest_path=args.manifest,
            genre_override=genre_enum,
            output_path=args.output,
            voice=args.voice,
            whisper_model=args.whisper_model,
            backend=args.backend,
        )
    )


if __name__ == "__main__":
    main()
