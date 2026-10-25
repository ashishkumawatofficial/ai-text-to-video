"""Interactive Autonomous Director Engine.

Plans multi-beat visual storyboards, synthesizes 9:16 keyframe previews,
executes conversational delta modifications, and gates master video compilation.
"""

from __future__ import annotations
import os
import re
from typing import Optional, Dict, Any, List, Callable, Tuple
from core.models import (
    DirectorMasterPlan,
    SceneBeatPlan,
    ConditioningMode,
    ApprovalStatus,
    StoryboardSession,
    ReferenceAsset,
    Genre,
    AudioCue,
    VideoProject,
    StoryboardBeat,
    IngestionMode,
    VisualStrategyRoute,
    ImageAsset,
    ImageRole,
    ContinuityLink,
    SubtitleTrack,
    SubtitleWordToken,
    RenderOutput
)
from core.session_manager import StoryboardSessionManager
from core.conditioning_engine import ConditioningEngine
from core.local_visual_mock import generate_local_keyframe
from core.story_writer import StoryWriterGateway
from core.models import VideoAspectRatio, NarrativeInputMode, NarrativeBrief


class InteractiveDirector:
    """Orchestrates interactive storyboard planning, conversational revisions, and approval gates."""

    def __init__(
        self,
        session_manager: Optional[StoryboardSessionManager] = None,
        story_writer: Optional[StoryWriterGateway] = None,
        comfy_client: Optional[Any] = None,
    ):
        self.session_manager = session_manager or StoryboardSessionManager()
        if story_writer is not None:
            self.story_writer = story_writer
        elif os.environ.get("TEST_MODE") == "1":
            from core.models import ModelCascadeConfig, ModelProvider
            self.story_writer = StoryWriterGateway(ModelCascadeConfig(provider=ModelProvider.OFFLINE))
        else:
            self.story_writer = StoryWriterGateway()
        if comfy_client is not None:
            self.comfy_client = comfy_client
        else:
            try:
                from core.runpod_client import ComfyUIClient
                self.comfy_client = ComfyUIClient()
            except Exception:
                self.comfy_client = None
        self.current_session: Optional[StoryboardSession] = None


    def create_storyboard(
        self,
        prompt: str,
        references: Optional[Dict[str, ReferenceAsset]] = None,
        genre_override: Optional[Genre] = None,
        session_id: Optional[str] = None,
        voice_override: Optional[str] = None,
        aspect_ratio: VideoAspectRatio | str = VideoAspectRatio.VERTICAL_9_16,
        input_mode: NarrativeInputMode | str = NarrativeInputMode.CONCEPT_EXPANSION,
    ) -> StoryboardSession:
        """Synthesizes a complete storyboard with keyframe artwork and halts at pending approval."""
        ratio_enum = VideoAspectRatio(aspect_ratio) if isinstance(aspect_ratio, str) else aspect_ratio
        mode_enum = NarrativeInputMode(input_mode) if isinstance(input_mode, str) else input_mode

        brief = NarrativeBrief(
            prompt_or_text=prompt,
            input_mode=mode_enum,
            aspect_ratio=ratio_enum,
            genre_hint=genre_override,
            voice_persona=voice_override or "en-US-ChristopherNeural",
            reference_assets=references or {},
        )

        writer_result = self.story_writer.synthesize_story(brief)
        plan = writer_result.plan

        # Classify conditioning modes and synthesize keyframe artwork
        prev_beat = None
        for beat in plan.scenes:
            beat.conditioning_mode = ConditioningEngine.classify_beat_conditioning(beat, previous_beat=prev_beat)
            keyframe_file = generate_local_keyframe(
                prompt=getattr(beat, "image_prompt", None) or beat.visual_prompt,
                scene_id=f"scene_{beat.beat_index}",
                width=plan.width,
                height=plan.height,
            )
            beat.keyframe_image_path = keyframe_file
            prev_beat = beat

        # Bind references if provided
        if references:
            plan = ConditioningEngine.bind_references_to_plan(plan, references)

        # Persist session
        session = self.session_manager.create_session(
            initial_prompt=prompt,
            plan=plan,
            reference_assets=references,
            session_id=session_id
        )
        self.current_session = session
        return session

    def apply_modification(self, session_id: str, instruction: str) -> Optional[StoryboardSession]:
        """Parses a natural language instruction and applies surgical delta edits to the session."""
        session = self.session_manager.load_session(session_id)
        if not session:
            return None
        self.current_session = session

        inst_lower = instruction.lower().strip()
        plan = session.plan

        # Detect targeted beat index (e.g., "scene 2", "beat 1", "2")
        target_beat = None
        match_beat = re.search(r"\b(?:scene|beat)\s*(\d+)\b", inst_lower)
        if match_beat:
            target_beat = int(match_beat.group(1))
        elif inst_lower.startswith("modify ") and inst_lower.split()[1].isdigit():
            target_beat = int(inst_lower.split()[1])

        modified_beats = []
        changes = []

        # 1. Global Voiceover / Music / Subtitles tweaks
        vo_match = re.search(r"\b(?:remove|mute|no)\s+(?:the\s+)?(?:voiceover|voice|narration)\b", inst_lower)
        if vo_match:
            if target_beat:
                for s in plan.scenes:
                    if s.beat_index == target_beat:
                        s.dialogue_text = None
                        if target_beat not in modified_beats:
                            modified_beats.append(target_beat)
                        changes.append(f"Muted voiceover for Scene {target_beat}")
            else:
                plan.voiceover_enabled = False
                for s in plan.scenes:
                    s.dialogue_text = None
                changes.append("Disabled global voiceover")

        if "female voice" in inst_lower or "jenny" in inst_lower:
            plan.voice_persona = "en-US-JennyNeural"
            changes.append("Changed narrator persona to en-US-JennyNeural (female)")

        if re.search(r"\b(?:remove|hide|no)\s+(?:the\s+)?subtitles?\b", inst_lower):
            plan.subtitles_enabled = False
            changes.append("Disabled on-screen subtitles")

        if "fast" in inst_lower and "music" in inst_lower:
            plan.music_genre_and_mood = "fast_paced_action_pulse"
            changes.append("Changed background music to fast-paced action pulse")

        # 2. Targeted Scene Edits (Visual, Duration, Camera)
        target_scenes = [s for s in plan.scenes if s.beat_index == target_beat] if target_beat else plan.scenes

        for scene in target_scenes:
            # Duration adjustment
            dur_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:seconds?|s\b)", inst_lower)
            if dur_match and ("longer" in inst_lower or "shorter" in inst_lower or "duration" in inst_lower or target_beat):
                new_dur = float(dur_match.group(1))
                if 0.5 <= new_dur <= 30.0:
                    scene.duration_sec = new_dur
                    if scene.beat_index not in modified_beats:
                        modified_beats.append(scene.beat_index)
                    changes.append(f"Adjusted Scene {scene.beat_index} duration to {new_dur}s")

            # Visual modification
            visual_triggers = ["make", "change", "color", "crystal", "glowing", "night", "dark", "rain", "cyber", "red", "purple", "blue", "add", "style"]
            if any(vt in inst_lower for vt in visual_triggers):
                # Clean up instruction to build new descriptive prompt element (stripping beat numbers and audio commands)
                clean_clause = re.sub(r"\b(?:modify|scene|beat|\d+)\b", "", instruction, flags=re.IGNORECASE)
                clean_clause = re.sub(r"\b(?:and\s+)?(?:remove|mute|no)\s+(?:the\s+)?(?:voiceover|voice|narration|subtitles?)\b", "", clean_clause, flags=re.IGNORECASE).strip()
                if clean_clause:
                    is_stylized = any(s in clean_clause.lower() or s in scene.visual_prompt.lower() for s in ["cartoon", "anime", "animated", "animation", "illustration", "pixar", "disney", "comic", "drawing", "3d render"])
                    style_suffix = "cinematic animated quality" if is_stylized else "8k photorealistic"
                    scene.visual_prompt = f"{scene.visual_prompt}, modified with {clean_clause}, {style_suffix}"
                    
                    # Regenerate keyframe plate
                    new_keyframe = generate_local_keyframe(
                        prompt=scene.visual_prompt,
                        scene_id=f"scene_{scene.beat_index}",
                        width=plan.width,
                        height=plan.height,
                    )
                    scene.keyframe_image_path = new_keyframe
                    if scene.beat_index not in modified_beats:
                        modified_beats.append(scene.beat_index)
                    changes.append(f"Updated Scene {scene.beat_index} visual keyframe ({clean_clause})")

        # Recalculate total duration
        plan.total_duration_sec = sum(s.duration_sec for s in plan.scenes)

        # Record turn & save
        summary = "; ".join(changes) if changes else f"Applied instructions: {instruction}"
        return self.session_manager.record_turn(
            session_id=session_id,
            user_message=instruction,
            modified_beats=modified_beats,
            summary_of_changes=summary,
            updated_plan=plan
        )

    def approve_session(self, session_id: str) -> Optional[StoryboardSession]:
        """Approves the storyboard session, unlocking final video production."""
        session = self.session_manager.set_approval_status(session_id, ApprovalStatus.APPROVED)
        self.current_session = session
        return session

    def convert_plan_to_video_project(self, plan: DirectorMasterPlan) -> VideoProject:
        """Converts an approved DirectorMasterPlan into a VideoProject domain object."""
        scenes: List[StoryboardBeat] = []

        for b in plan.scenes:
            # Map image assets
            image_assets: List[ImageAsset] = []
            if b.keyframe_image_path and os.path.exists(b.keyframe_image_path):
                image_assets.append(ImageAsset(
                    file_path=b.keyframe_image_path,
                    role=ImageRole.SCENE_IMAGE
                ))
            if b.start_frame_path and os.path.exists(b.start_frame_path):
                image_assets.append(ImageAsset(
                    file_path=b.start_frame_path,
                    role=ImageRole.START_FRAME
                ))

            # Strategy mapping
            if plan.genre == Genre.RIDDLE:
                route = VisualStrategyRoute.PROGRAMMATIC_HYBRID
            elif b.conditioning_mode == ConditioningMode.START_AND_END_FRAME:
                route = VisualStrategyRoute.START_END_INTERPOLATION
            else:
                route = VisualStrategyRoute.FLAT_RATE_DIFFUSION

            continuity = ContinuityLink(
                chain_from_previous=(
                    b.conditioning_mode == ConditioningMode.CHAIN_FROM_PREVIOUS
                    or getattr(b, "is_chained", False)
                ),
                cut_type="cut"
            )

            scenes.append(StoryboardBeat(
                beat_index=b.beat_index,
                name=b.name,
                duration_sec=b.duration_sec,
                visual_strategy=route,
                visual_prompt=b.visual_prompt,
                dialogue_text=b.dialogue_text,
                sound_effects=b.sound_effects,
                image_assets=image_assets,
                continuity=continuity,
                output_video_path=getattr(b, "output_video_path", None)
            ))

        return VideoProject(
            title=plan.title,
            genre=plan.genre,
            aspect_ratio=plan.aspect_ratio,
            width=plan.width,
            height=plan.height,
            ingestion_mode=IngestionMode.AUTONOMOUS_DIRECTOR,
            scenes=scenes
        )

    async def render_approved_session(
        self,
        session: StoryboardSession,
        output_path: str = "outputs/final_video.mp4",
        whisper_model: str = "tiny",
        backend: str = "auto",
        progress_cb: Optional[Callable[[int, str, str], None]] = None,
    ) -> RenderOutput:
        """Renders an approved StoryboardSession into a master MP4 video."""
        import time
        import subprocess
        import shutil
        from core.audio_engine import generate_narration_with_subtitles
        from core.sfx_mixer import build_audio_asset
        from core.chain_manager import chain_shots
        from core.visual_router import route_and_execute_beat
        from core.remotion_bridge import render_project_to_video
        from core.runpod_serverless import RunPodServerlessClient

        start_time = time.time()
        self.current_session = session
        plan = session.plan
        project = self.convert_plan_to_video_project(plan)

        temp_dir = os.path.abspath(os.path.join("outputs", "temp"))
        os.makedirs(temp_dir, exist_ok=True)

        # 1. Multi-Character Scene-by-Scene Dialogue Synthesis & Subtitle Sequencing
        from core.audio_engine import synthesize_scene_dialogue, stitch_beat_audio_tracks

        beat_audio_tracks: List[Tuple[str, float]] = []  # (audio_path, start_offset_sec)
        all_subtitle_words: List[SubtitleWordToken] = []
        cumulative_time = 0.0

        for idx, beat in enumerate(project.scenes):
            dialogue = (beat.dialogue_text or "").strip()
            # Plan scene mapping
            plan_scene = plan.scenes[idx] if idx < len(plan.scenes) else None
            speaker = getattr(plan_scene, "speaker", None) or getattr(beat, "speaker", "Narrator") or "Narrator"
            voice_persona = (
                getattr(plan_scene, "voice_persona", None)
                or getattr(beat, "voice_persona", None)
                or plan.voice_persona
            )

            if plan.voiceover_enabled and dialogue:
                safe_spk = re.sub(r'[^a-zA-Z0-9_]', '', speaker.replace(' ', '_')).lower() or 'narrator'
                beat_vo_path = os.path.join(temp_dir, f"vo_{project.id[:8]}_beat_{idx}_{safe_spk}.mp3")
                print(f"🎙️ Synthesizing Dialogue for Beat {idx} [{speaker}] using voice persona '{voice_persona}'...")
                
                audio_file, audio_dur, sub_track = await synthesize_scene_dialogue(
                    text=dialogue,
                    output_audio_path=beat_vo_path,
                    speaker=speaker,
                    voice_persona=voice_persona,
                    whisper_model_size=whisper_model,
                    prompt_context=getattr(session, "initial_prompt", "") or dialogue,
                )
                beat_audio_tracks.append((audio_file, cumulative_time))

                # Shift subtitle tokens to global video timeline
                shift_ms = int(round(cumulative_time * 1000))
                for word in sub_track.words:
                    all_subtitle_words.append(
                        SubtitleWordToken(
                            word=word.word,
                            start_ms=word.start_ms + shift_ms,
                            end_ms=word.end_ms + shift_ms,
                            confidence=word.confidence
                        )
                    )

            cumulative_time += beat.duration_sec

        # Composite individual character audio tracks into a master voiceover track
        vo_path = None
        if beat_audio_tracks:
            temp_master_vo = os.path.join(temp_dir, f"master_vo_{project.id[:8]}.mp3")
            vo_path = stitch_beat_audio_tracks(
                beat_tracks=beat_audio_tracks,
                total_duration_sec=cumulative_time,
                output_master_audio_path=temp_master_vo
            )

        if plan.subtitles_enabled and all_subtitle_words:
            project.subtitles = SubtitleTrack(
                style_preset=plan.subtitle_preset,
                words=all_subtitle_words
            )
        else:
            project.subtitles = SubtitleTrack(style_preset="none", words=[])

        # 2. SFX Assembly
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

        # 3. Visual Routing & Scene Preparation
        serverless_client = RunPodServerlessClient()
        use_serverless = (backend == "serverless") or (backend == "auto" and serverless_client.is_available())
        serverless_succeeded = False

        if use_serverless and serverless_client.is_available():
            print("⚡ [Serverless Dispatch] Rendering all visual beats concurrently...")
            try:
                def _combined_progress(idx: int, name: str, status: str):
                    print(f"   [Beat {idx+1}] '{name}' ➔ {status}")
                    if progress_cb:
                        try:
                            progress_cb(idx, name, status)
                        except Exception:
                            pass

                cost_report = await serverless_client.dispatch_parallel_beats(
                    beats=project.scenes,
                    output_dir=temp_dir,
                    aspect_ratio=project.aspect_ratio.value if hasattr(project.aspect_ratio, "value") else str(project.aspect_ratio),
                    progress_cb=_combined_progress
                )
                from core.runpod_serverless import format_cost_banner, ensure_video_duration_coverage
                print(format_cost_banner(cost_report))
                serverless_succeeded = True
                for s_idx, b in enumerate(project.scenes):
                    if b.output_video_path and os.path.exists(b.output_video_path):
                        b.output_video_path = ensure_video_duration_coverage(b.output_video_path, b.duration_sec)
                    if s_idx < len(plan.scenes):
                        plan.scenes[s_idx].output_video_path = b.output_video_path
                self.session_manager.save_session(session)
            except Exception as e:
                print(f"   ⚠️ Serverless batch execution failed ({e}). Falling back to dedicated pod/local cascade.")

        if not serverless_succeeded:
            print("🎨 Routing Visual Scenes via Tri-Strategy Engine...")
            prev_clip_path = None
            for idx, beat in enumerate(project.scenes):
                if progress_cb:
                    try:
                        progress_cb(idx, beat.name, "RENDERING")
                    except Exception:
                        pass

                if beat.output_video_path and os.path.exists(beat.output_video_path):
                    prev_clip_path = beat.output_video_path
                    continue

                if beat.continuity.chain_from_previous and prev_clip_path and os.path.exists(prev_clip_path):
                    print(f"   🔗 Chaining Frame -1 of previous clip into Frame 0 for Beat {beat.beat_index}")
                    chain_shots(prev_clip_path, beat, temp_dir=temp_dir)

                clip_dest = os.path.join(temp_dir, f"beat_{beat.beat_index}.mp4")
                route_and_execute_beat(beat, output_video_path=clip_dest, comfy_client=self.comfy_client, backend=backend)
                if beat.output_video_path and os.path.exists(beat.output_video_path):
                    beat.output_video_path = ensure_video_duration_coverage(beat.output_video_path, beat.duration_sec)
                    prev_clip_path = beat.output_video_path
                    if idx < len(plan.scenes):
                        plan.scenes[idx].output_video_path = beat.output_video_path

                if progress_cb:
                    try:
                        progress_cb(idx, beat.name, "COMPLETED")
                    except Exception:
                        pass

                print(f"   [Beat {beat.beat_index}] '{beat.name}' ➔ Route: {beat.visual_strategy.value}")

            self.session_manager.save_session(session)

        # 4. Master Compilation
        abs_output = os.path.abspath(output_path)
        os.makedirs(os.path.dirname(abs_output), exist_ok=True)
        print(f"🚀 Compiling Master Video ➔ {abs_output}")
        try:
            render_project_to_video(project, abs_output)
        except Exception as e:
            print(f"⚠️ Remotion render encountered an issue ({e}). Checking for valid clip fallback...")
            valid_clips = [b.output_video_path for b in project.scenes if b.output_video_path and os.path.exists(b.output_video_path)]
            if valid_clips:
                print(f"   🎬 Falling back to direct concatenation of {len(valid_clips)} scene clips...")
                try:
                    concat_list_file = os.path.join(temp_dir, f"concat_{project.id[:8]}.txt")
                    with open(concat_list_file, "w") as cf:
                        for cpath in valid_clips:
                            cf.write(f"file '{cpath}'\n")
                    cmd = ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_list_file, "-c", "copy", abs_output]
                    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
                except Exception as ce:
                    print(f"   ⚠️ Direct concat failed ({ce}). Copying first available clip.")
                    shutil.copy2(valid_clips[0], abs_output)
            else:
                raise

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
