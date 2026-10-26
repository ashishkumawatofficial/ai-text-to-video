"""Unified Command Line Interface for Universal Video Studio."""

from __future__ import annotations
import sys
import asyncio
import argparse
import core.config  # Auto-loads .env
from core.models import Genre
from core.pipeline import run_pipeline
from core.cache import cleanup_temporary_artifacts


BANNER = r"""
  _    _       _                                _   _ _     _            
 | |  | |     (_)                              | | | (_)   | |           
 | |  | |_ __  _ _   _____ _ __ ___  __ _  ___ | | | |_  __| | ___  ___  
 | |  | | '_ \| \ \ / / _ \ '__/ __|/ _` |/ _ \| | | | |/ _` |/ _ \/ _ \ 
 | |__| | | | | |\ V /  __/ |  \__ \ (_| | (_) \ \_/ / | (_| |  __/ (_) |
  \____/|_| |_|_| \_/ \___|_|  |___/\__,_|\___/ \___/|_|\__,_|\___|\___/ 
                     Universal AI Video Generation Studio
"""


def main():
    print(BANNER)
    parser = argparse.ArgumentParser(
        prog="universal-video",
        description="Universal Multi-Genre AI Video Production Studio (Riddles, Stories, Action)"
    )

    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # Render command
    render_parser = subparsers.add_parser("render", help="Render a video from prompt or manifest")
    render_parser.add_argument("--prompt", "-p", type=str, help="Natural language prompt / concept")
    render_parser.add_argument("--manifest", "-m", type=str, help="Path to JSON storyboard manifest")
    render_parser.add_argument("--genre", "-g", choices=["riddle", "cinematic_story", "action"], help="Genre override")
    render_parser.add_argument("--aspect-ratio", "-ar", choices=["9:16", "16:9", "1:1", "4:5"], default="9:16", help="Aspect ratio (default 9:16)")
    render_parser.add_argument("--output", "-o", default="outputs/final_video.mp4", help="Output MP4 path")
    render_parser.add_argument("--voice", default="en-US-ChristopherNeural", help="Neural TTS voice name")
    render_parser.add_argument("--backend", "-b", choices=["auto", "serverless", "pod", "local"], default="auto", help="Visual diffusion rendering backend (default: auto)")

    # Clean command
    clean_parser = subparsers.add_parser("clean", help="Clean temporary render caches and artifacts")
    clean_parser.add_argument("--hours", type=float, default=24.0, help="Max age in hours (default 24)")

    # Health command
    health_parser = subparsers.add_parser("health", help="Check RunPod ComfyUI remote inference connectivity and specs")
    health_parser.add_argument("--url", "-u", type=str, default=None, help="ComfyUI endpoint URL override")

    # Direct command (Feature 003 & 004: Dynamic AI Storyboard & Multi-Aspect Ratio Framing)
    direct_parser = subparsers.add_parser("direct", help="Interactive Director: create, review, and modify storyboard before rendering")
    direct_parser.add_argument("--prompt", "-p", type=str, required=True, help="Natural language concept, long script text, or file path")
    direct_parser.add_argument("--aspect-ratio", "-ar", choices=["9:16", "16:9", "1:1", "4:5"], default="9:16", help="Canvas aspect ratio (default: 9:16 vertical)")
    direct_parser.add_argument("--input-mode", "-im", choices=["concept_expansion", "script_adaptation"], default="concept_expansion", help="Input mode: concept_expansion (default) or script_adaptation")
    direct_parser.add_argument("--model", type=str, default=None, help="Model override (e.g. gemini-3.8-flash, gpt-4o, offline)")
    direct_parser.add_argument("--character", "-c", action="append", default=[], help="Character reference (format: 'name:path/to/img.jpg')")
    direct_parser.add_argument("--environment", "-e", type=str, default=None, help="Environment reference image path")
    direct_parser.add_argument("--start-frame", "-s", type=str, default=None, help="Explicit start frame path")
    direct_parser.add_argument("--genre", "-g", choices=["riddle", "cinematic_story", "action"], help="Genre override")

    # Studio command (Feature 006: Web Studio Interface & AI Director Copilot)
    studio_parser = subparsers.add_parser("studio", help="Launch the local Web Studio Interface (FastAPI + React Vite)")
    studio_parser.add_argument("--host", default="127.0.0.1", help="Backend host (default: 127.0.0.1)")
    studio_parser.add_argument("--port", type=int, default=8000, help="Backend port (default: 8000)")
    studio_parser.add_argument("--no-frontend", action="store_true", help="Launch backend server only without spawning Vite")
    direct_parser.add_argument("--output", "-o", default="outputs/final_video.mp4", help="Output MP4 path")
    direct_parser.add_argument("--voice", default=None, help="Neural TTS voice name override")
    direct_parser.add_argument("--backend", "-b", choices=["auto", "serverless", "pod", "local"], default="auto", help="Visual diffusion rendering backend (default: auto)")
    direct_parser.add_argument("--auto-approve", action="store_true", help="Automatically approve storyboard and render video without interactive prompt")


    # Verify APIs command (Zero-waste health check of all configured providers)
    subparsers.add_parser("verify-apis", help="Run lightweight zero-waste live probe across all configured AI providers")

    args = parser.parse_args()

    if args.command == "health":
        from core.runpod_client import check_endpoint_health
        report = check_endpoint_health(args.url)
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print(f"📡 RunPod ComfyUI Endpoint: {report.url}")
        print(f"📊 Status: {report.status_summary} (Latency: {report.latency_ms}ms)")
        if report.is_reachable:
            print(f"🎮 GPU Device: {report.gpu_name or 'N/A'}")
            print(f"💾 VRAM: {report.vram_free_gb} GB free / {report.vram_total_gb} GB total")
            print(f"⚡ ComfyUI Version: {report.comfyui_version}")
            print(f"🧠 Wan 3.0 Model: {'✅ Detected' if report.has_wan3 else '❌ Not Found'}")
            print(f"🧠 Wan 2.1 Model: {'✅ Detected' if report.has_wan2 else '❌ Not Found'}")
            print(f"🎭 IP-Adapter: {'✅ Detected' if report.has_ipadapter else '❌ Not Found'}")
            if report.available_checkpoints:
                print(f"📦 Checkpoints ({len(report.available_checkpoints)}): {', '.join(report.available_checkpoints[:5])}")
        from core.runpod_serverless import check_serverless_health
        sl_health = check_serverless_health()
        print(f"⚡ RunPod Serverless Endpoint: {sl_health.endpoint_id}")
        print(f"📊 Serverless Status: {sl_health.status}")
        if sl_health.status == "HEALTHY":
            print(f"   • Workers Idle: {sl_health.workers_idle} | Workers Running: {sl_health.workers_running}")
            print(f"   • Jobs In Queue: {sl_health.jobs_in_queue} | In Progress: {sl_health.jobs_in_progress}")
        elif sl_health.error:
            print(f"   ⚠️ {sl_health.error}")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        return

    if args.command == "verify-apis":
        from core.api_verifier import run_api_verification
        run_api_verification()
        return

    if args.command == "clean":
        count = cleanup_temporary_artifacts(max_age_hours=args.hours)
        print(f"🧹 Cleaned {count} temporary artifact files.")
        return

    if args.command == "direct":
        from core.interactive_director import InteractiveDirector
        from core.models import ReferenceAsset

        # 1. Parse reference assets
        references = {}
        for char_arg in getattr(args, "character", []):
            if ":" in char_arg:
                cname, cpath = char_arg.split(":", 1)
            else:
                cname = os.path.splitext(os.path.basename(char_arg))[0]
                cpath = char_arg
            references[cname] = ReferenceAsset(
                tag=cname,
                role="character",
                file_path=cpath
            )

        if getattr(args, "environment", None):
            references["environment"] = ReferenceAsset(
                tag="environment",
                role="environment",
                file_path=args.environment
            )

        if getattr(args, "start_frame", None):
            references["start_frame"] = ReferenceAsset(
                tag="start_frame",
                role="start_frame",
                file_path=args.start_frame
            )

        genre = Genre(args.genre) if getattr(args, "genre", None) else None

        # Check if prompt points to a readable script file
        prompt_text = args.prompt
        input_mode = args.input_mode
        import os
        if os.path.exists(prompt_text) and os.path.isfile(prompt_text):
            try:
                with open(prompt_text, "r", encoding="utf-8") as f:
                    prompt_text = f.read().strip()
                input_mode = "script_adaptation"
                print(f"📖 Loaded long-form script from {args.prompt} ({len(prompt_text)} chars)")
            except Exception as e:
                print(f"⚠️ Could not read script file {args.prompt}: {e}. Treating as text prompt.")

        # Custom story writer / model configuration if requested
        story_writer = None
        if getattr(args, "model", None):
            from core.models import ModelCascadeConfig, ModelProvider
            from core.story_writer import StoryWriterGateway
            model_val = args.model.lower()
            if model_val == "offline":
                cfg = ModelCascadeConfig(provider=ModelProvider.OFFLINE)
            elif "gemini" in model_val:
                cfg = ModelCascadeConfig(provider=ModelProvider.GEMINI, gemini_models=[args.model])
            elif "gpt" in model_val:
                cfg = ModelCascadeConfig(provider=ModelProvider.OPENAI, openai_models=[args.model])
            else:
                cfg = ModelCascadeConfig(gemini_models=[args.model])
            story_writer = StoryWriterGateway(cfg)

        director = InteractiveDirector(story_writer=story_writer)

        session = director.create_storyboard(
            prompt=prompt_text,
            references=references if references else None,
            genre_override=genre,
            voice_override=getattr(args, "voice", None),
            aspect_ratio=args.aspect_ratio,
            input_mode=input_mode,
        )

        def print_storyboard(curr_session):
            plan = curr_session.plan
            print("\n🎬 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            print(f"✨ Interactive Storyboard Preview: '{plan.title}'")
            print(f"📁 Session ID: {curr_session.session_id} | Status: {curr_session.approval_status.value.upper()}")
            print(f"🎭 Genre: {plan.genre.value} | Total Duration: {plan.total_duration_sec}s | Canvas: {plan.aspect_ratio} ({plan.width}x{plan.height})")
            vo_status = plan.voice_persona if plan.voiceover_enabled else "MUTED"

            sub_status = plan.subtitle_preset if plan.subtitles_enabled else "DISABLED"
            print(f"🎙️ Voiceover: {vo_status} | 🎵 Music: {plan.music_genre_and_mood} | 📝 Subtitles: {sub_status}")
            print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")

            for beat in plan.scenes:
                cond_str = beat.conditioning_mode.value.upper() if beat.conditioning_mode else "PURE_T2V"
                print(f"┌── [Beat {beat.beat_index}] '{beat.name}' ({beat.duration_sec}s) ─── Route: {cond_str}")
                print(f"│ 🎥 Camera: {beat.camera_movement}")
                print(f"│ 🎨 Visual Prompt: {beat.visual_prompt}")
                print(f"│ 🖼️ Keyframe: {beat.keyframe_image_path or 'Pending'}")
                if beat.start_frame_path:
                    print(f"│ 🔗 Start Frame Anchor: {beat.start_frame_path}")
                if beat.dialogue_text:
                    print(f"│ 💬 Dialogue: \"{beat.dialogue_text}\"")
                if beat.sound_effects:
                    sfx_names = ", ".join(f"{s.sfx_name} (+{s.offset_sec}s)" for s in beat.sound_effects)
                    print(f"│ 🔊 SFX: {sfx_names}")
                print(f"└───\n")

        print_storyboard(session)

        if getattr(args, "auto_approve", False):
            print("🚀 Auto-Approve enabled. Proceeding directly to master video synthesis...")
            approved_session = director.approve_session(session.session_id)
            asyncio.run(director.render_approved_session(
                approved_session,
                output_path=args.output,
                backend=getattr(args, "backend", "auto")
            ))
            return

        while True:
            try:
                print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
                choice = input("[A]pprove & Render Video | [M]odify Beat | [Q]uit > ").strip()
                print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            except (EOFError, KeyboardInterrupt):
                print("\nExiting without rendering.")
                break

            choice_lower = choice.lower()
            if choice_lower in ["a", "approve"]:
                print("🎉 Storyboard Approved! Beginning video synthesis...")
                approved_session = director.approve_session(session.session_id)
                asyncio.run(director.render_approved_session(
                    approved_session,
                    output_path=args.output,
                    backend=getattr(args, "backend", "auto")
                ))
                break
            elif choice_lower in ["q", "quit", "exit"]:
                print(f"Exiting without rendering. Session state saved: outputs/temp/sessions/{session.session_id}.json")
                break
            elif choice_lower.startswith("m") or choice_lower.startswith("modify"):
                instruction = choice
                if choice_lower in ["m", "modify"]:
                    try:
                        instruction = input("Enter modification instruction (e.g. 'modify 2 make the crystal purple and remove voiceover') > ").strip()
                    except (EOFError, KeyboardInterrupt):
                        print("\nCancelled modification.")
                        continue

                print(f"🔄 Applying delta modification: '{instruction}'...")
                updated_session = director.apply_modification(session.session_id, instruction)
                if updated_session:
                    session = updated_session
                    print_storyboard(session)
                else:
                    print("⚠️ Failed to apply modification.")
            else:
                print(f"Unknown action: '{choice}'. Enter 'a' to approve, 'm' to modify, or 'q' to quit.")
        return

    if args.command == "studio":
        import subprocess
        import uvicorn
        from pathlib import Path

        workspace_root = Path(__file__).resolve().parent.parent
        studio_dir = workspace_root / "studio"

        print("🎬 Launching AI Video Web Studio...")
        print(f"📡 Backend API starting at http://{args.host}:{args.port}")

        frontend_process = None
        if not args.no_frontend and studio_dir.exists():
            print("🚀 Starting Vite React Frontend at http://localhost:5173 ...")
            try:
                frontend_process = subprocess.Popen(
                    ["npm", "run", "dev"],
                    cwd=str(studio_dir),
                )
            except Exception as e:
                print(f"⚠️ Could not automatically start Vite dev server: {e}")

        try:
            uvicorn.run("core.server:app", host=args.host, port=args.port, reload=True)
        finally:
            if frontend_process:
                print("\n🛑 Stopping Vite dev server...")
                frontend_process.terminate()
        return

    if args.command == "render" or (args.command is None and (getattr(args, "prompt", None) or getattr(args, "manifest", None))):
        prompt = getattr(args, "prompt", None)
        manifest = getattr(args, "manifest", None)
        genre = Genre(args.genre) if getattr(args, "genre", None) else None
        output = getattr(args, "output", "outputs/final_video.mp4")
        voice = getattr(args, "voice", "en-US-ChristopherNeural")

        if not prompt and not manifest:
            render_parser.print_help()
            sys.exit(1)

        asyncio.run(
            run_pipeline(
                prompt=prompt,
                manifest_path=manifest,
                genre_override=genre,
                aspect_ratio=getattr(args, "aspect_ratio", "9:16"),
                output_path=output,
                voice=voice,
                backend=getattr(args, "backend", "auto"),
            )
        )

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
