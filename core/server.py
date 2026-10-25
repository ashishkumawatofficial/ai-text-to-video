"""FastAPI backend server for the AI Video Web Studio."""

from __future__ import annotations

import os
import asyncio
import uuid
import time
import subprocess
import shutil
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from pathlib import Path

from fastapi import FastAPI, HTTPException, BackgroundTasks, Request, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from core.models import (
    StudioSession,
    StoryboardCard,
    ChatMessage,
    TelemetryState,
    TelemetryWorkerTile,
    DirectingMode,
    BackendExecutionStrategy,
    VideoAspectRatio,
    StoryboardSession,
    StoryboardBeat,
    ConditioningMode,
)
from core.config import get_gemini_api_keys, get_gemini_api_key, get_runpod_serverless_endpoint_id
from core.interactive_director import InteractiveDirector
from core.runpod_serverless import RunPodServerlessClient
from core.runpod_client import check_endpoint_health
from core.chain_manager import extract_terminal_frame


app = FastAPI(
    title="AI Video Web Studio API",
    description="Backend API powering the interactive AI Video Production Studio",
    version="1.0.0",
)

# Enable CORS for local development (Vite runs on 5173 or 3000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure local asset directories exist and mount as static routes
_WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
_OUTPUTS_DIR = _WORKSPACE_ROOT / "outputs"
_CACHE_DIR = _WORKSPACE_ROOT / "cache"
_OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
_CACHE_DIR.mkdir(parents=True, exist_ok=True)

app.mount("/outputs", StaticFiles(directory=str(_OUTPUTS_DIR)), name="outputs")
app.mount("/cache", StaticFiles(directory=str(_CACHE_DIR)), name="cache")

# In-memory storage for active studio sessions
_ACTIVE_SESSIONS: Dict[str, StudioSession] = {}
_ACTIVE_TELEMETRY: Dict[str, TelemetryState] = {}
_ACTIVE_DIRECTORS: Dict[str, InteractiveDirector] = {}


# --- Request/Response DTOs ---

class GenerateStoryboardRequest(BaseModel):
    prompt: str
    aspect_ratio: str = "16:9"
    genre: str = "cinematic"
    directing_mode: str = "pro"
    backend: str = "serverless"
    voice_persona: Optional[str] = "auto"


class RerollBeatRequest(BaseModel):
    session_id: str
    beat_index: int
    prompt_override: Optional[str] = None


class DirectorChatRequest(BaseModel):
    session_id: str
    message: str


class StoryboardCardUpdateRequest(BaseModel):
    session_id: str
    beat_index: int
    speaker: Optional[str] = None
    voice_persona: Optional[str] = None
    dialogue_text: Optional[str] = None
    visual_prompt: Optional[str] = None
    camera_motion: Optional[str] = None


class RenderStartRequest(BaseModel):
    session_id: str
    backend: str = "serverless"


class RenderBeatRequest(BaseModel):
    session_id: str
    beat_index: int
    backend: Optional[str] = "serverless"


class ChainFrameRequest(BaseModel):
    session_id: str
    source_beat_index: int


class UnlinkChainRequest(BaseModel):
    session_id: str
    beat_index: int


class CompileMasterRequest(BaseModel):
    session_id: str
    allow_partial: bool = False


# --- API Routes ---

@app.get("/api/health")
async def health_check() -> Dict[str, Any]:
    """Probes backend connectivity, Gemini API status, and RunPod Serverless availability."""
    gemini_keys = get_gemini_api_keys()
    endpoint_id = get_runpod_serverless_endpoint_id()
    
    serverless_healthy = False
    workers_idle = 0
    workers_running = 0
    if endpoint_id:
        try:
            client = RunPodServerlessClient()
            health_data = client.check_health()
            if health_data.get("status") == "HEALTHY":
                serverless_healthy = True
                workers_idle = health_data.get("workers_idle", 0)
                workers_running = health_data.get("workers_running", 0)
        except Exception:
            pass

    return {
        "status": "HEALTHY",
        "gemini_active": bool(gemini_keys),
        "gemini_keys_count": len(gemini_keys),
        "serverless_endpoint_id": endpoint_id or "not_configured",
        "serverless_healthy": serverless_healthy,
        "workers_idle": workers_idle,
        "workers_running": workers_running,
    }


@app.get("/api/session/{session_id}")
async def get_session(session_id: str) -> StudioSession:
    """Retrieve full active state of a studio session."""
    director = _ACTIVE_DIRECTORS.get(session_id) or InteractiveDirector()
    _ACTIVE_DIRECTORS[session_id] = director
    sb_session = getattr(director, "session_manager", None) and director.session_manager.load_session(session_id)

    if session_id in _ACTIVE_SESSIONS:
        sess = _ACTIVE_SESSIONS[session_id]
        if sb_session and sb_session.plan:
            for card in sess.beats:
                scene = next((s for s in sb_session.plan.scenes if s.beat_index == card.beat_index + 1), None)
                if scene and scene.output_video_path and os.path.exists(scene.output_video_path):
                    rel_vid = os.path.relpath(scene.output_video_path, str(_WORKSPACE_ROOT))
                    card.output_video_path = f"/{rel_vid}"
                    card.render_status = "completed"
        return sess

    if not sb_session or not sb_session.plan:
        raise HTTPException(status_code=404, detail="Studio session not found")

    cards: List[StoryboardCard] = []
    for scene in sb_session.plan.scenes:
        idx = scene.beat_index - 1
        keyframe_url = None
        if scene.keyframe_image_path and os.path.exists(scene.keyframe_image_path):
            rel_path = os.path.relpath(scene.keyframe_image_path, str(_WORKSPACE_ROOT))
            keyframe_url = f"/{rel_path}"

        out_video_url = None
        if scene.output_video_path and os.path.exists(scene.output_video_path):
            rel_vid = os.path.relpath(scene.output_video_path, str(_WORKSPACE_ROOT))
            out_video_url = f"/{rel_vid}"

        cards.append(
            StoryboardCard(
                beat_id=f"beat_{idx}",
                beat_index=idx,
                visual_prompt=scene.visual_prompt,
                keyframe_path=keyframe_url,
                speaker=getattr(scene, "speaker", "Narrator") or "Narrator",
                dialogue_text=scene.dialogue_text or "",
                voice_actor=scene.voice_persona or sb_session.plan.voice_persona or "auto",
                camera_motion=scene.camera_movement or "push_in",
                duration_seconds=scene.duration_sec,
                duration_frames=int(scene.duration_sec * 16),
                render_status="completed" if out_video_url else "pending",
                output_video_path=out_video_url,
                is_chained=getattr(scene, "is_chained", False),
                chained_from_beat=getattr(scene, "chained_from_beat", None),
            )
        )

    out_file = _OUTPUTS_DIR / f"{session_id}_master.mp4"
    master_path = f"/outputs/{session_id}_master.mp4" if out_file.exists() else None

    # Check for default final_video.mp4 if session master file doesn't exist yet
    if not master_path and (_OUTPUTS_DIR / "final_video.mp4").exists():
        master_path = "/outputs/final_video.mp4"

    plan_ar = getattr(sb_session.plan, "aspect_ratio", "9:16")
    is_widescreen = (plan_ar == VideoAspectRatio.WIDESCREEN_16_9 or plan_ar == "16:9")

    restored = StudioSession(
        session_id=session_id,
        concept_prompt=sb_session.initial_prompt,
        aspect_ratio="16:9" if is_widescreen else "9:16",
        directing_mode=DirectingMode.AUTO,
        backend_strategy=BackendExecutionStrategy.SERVERLESS,
        beats=cards,
        status="completed" if master_path else "storyboard_ready",
        master_video_path=master_path,
    )
    _ACTIVE_SESSIONS[session_id] = restored
    return restored


@app.post("/api/storyboard/generate")
async def generate_storyboard(req: GenerateStoryboardRequest) -> StudioSession:
    """Plans narrative beats and generates keyframe image previews."""
    session_id = str(uuid.uuid4())
    director = InteractiveDirector()
    _ACTIVE_DIRECTORS[session_id] = director

    aspect_enum = VideoAspectRatio.WIDESCREEN_16_9 if req.aspect_ratio == "16:9" else VideoAspectRatio.VERTICAL_9_16
    mode_enum = DirectingMode.AUTO if req.directing_mode == "auto" else DirectingMode.PRO

    # Run story director planning
    session_plan = director.create_storyboard(
        prompt=req.prompt,
        aspect_ratio=aspect_enum,
        session_id=session_id,
        voice_override=req.voice_persona or "auto"
    )

    # Convert StoryboardSession beats into visual StoryboardCards
    cards: List[StoryboardCard] = []
    for scene in session_plan.plan.scenes:
        idx = scene.beat_index - 1
        keyframe_url = None
        if scene.keyframe_image_path and os.path.exists(scene.keyframe_image_path):
            rel_path = os.path.relpath(scene.keyframe_image_path, str(_WORKSPACE_ROOT))
            keyframe_url = f"/{rel_path}"

        cards.append(
            StoryboardCard(
                beat_id=f"beat_{idx}",
                beat_index=idx,
                visual_prompt=scene.visual_prompt,
                keyframe_path=keyframe_url,
                dialogue_text=scene.dialogue_text or "",
                speaker=getattr(scene, "speaker", "Narrator") or "Narrator",
                voice_actor=scene.voice_persona or session_plan.plan.voice_persona or req.voice_persona or "auto",
                camera_motion=scene.camera_movement or "push_in",
                duration_seconds=scene.duration_sec,
                duration_frames=int(scene.duration_sec * 16),
                render_status="pending",
                output_video_path=scene.output_video_path,
            )
        )

    studio_session = StudioSession(
        session_id=session_id,
        concept_prompt=req.prompt,
        aspect_ratio=req.aspect_ratio,
        directing_mode=mode_enum,
        backend_strategy=BackendExecutionStrategy(req.backend) if req.backend in [b.value for b in BackendExecutionStrategy] else BackendExecutionStrategy.SERVERLESS,
        beats=cards,
        status="storyboard_ready",
    )

    _ACTIVE_SESSIONS[session_id] = studio_session
    return studio_session


@app.post("/api/storyboard/reroll")
async def reroll_beat(req: RerollBeatRequest) -> StoryboardCard:
    """Surgically regenerates a single beat card's keyframe without modifying other scenes."""
    if req.session_id not in _ACTIVE_SESSIONS:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = _ACTIVE_SESSIONS[req.session_id]
    director = _ACTIVE_DIRECTORS.get(req.session_id)
    if not director:
        director = InteractiveDirector()
        _ACTIVE_DIRECTORS[req.session_id] = director

    target_card = next((c for c in session.beats if c.beat_index == req.beat_index), None)
    if not target_card:
        raise HTTPException(status_code=404, detail=f"Beat {req.beat_index} not found")

    # If prompt override provided, update card prompt
    if req.prompt_override:
        target_card.visual_prompt = req.prompt_override

    # Directly trigger fresh keyframe synthesis with force_refresh=True
    beat_num = req.beat_index + 1
    from core.local_visual_mock import generate_local_keyframe
    dim = (832, 480) if session.aspect_ratio == "16:9" else (480, 832) if session.aspect_ratio == "9:16" else (640, 640)
    new_keyframe = generate_local_keyframe(
        prompt=target_card.visual_prompt,
        scene_id=f"scene_{beat_num}",
        width=dim[0],
        height=dim[1],
        force_refresh=True
    )
    rel_path = os.path.relpath(new_keyframe, str(_WORKSPACE_ROOT))
    target_card.keyframe_path = f"/{rel_path}"
    target_card.edited_by_ai = True
    target_card.is_custom_image = False

    # Also sync directly into director session plan if present
    try:
        sb_session = getattr(director, "session_manager", None) and director.session_manager.load_session(req.session_id)
        if sb_session and sb_session.plan:
            scene = next((s for s in sb_session.plan.scenes if s.beat_index == beat_num), None)
            if scene:
                scene.keyframe_image_path = new_keyframe
                scene.visual_prompt = target_card.visual_prompt
                scene.start_frame_path = new_keyframe
                director.session_manager.save_session(sb_session)
    except Exception:
        pass
    
    session.updated_at = datetime.now(timezone.utc)
    return target_card


@app.post("/api/storyboard/upload-image")
async def upload_beat_image(
    session_id: str = Form(...),
    beat_index: int = Form(...),
    file: UploadFile = File(...)
) -> StoryboardCard:
    """Allows creators to upload their own custom keyframe/artwork for a specific scene beat."""
    if session_id not in _ACTIVE_SESSIONS:
        raise HTTPException(status_code=404, detail="Session not found")

    session = _ACTIVE_SESSIONS[session_id]
    target_card = next((c for c in session.beats if c.beat_index == beat_index), None)
    if not target_card:
        raise HTTPException(status_code=404, detail=f"Beat {beat_index} not found")

    # Save uploaded file into temporary uploads directory
    uploads_dir = _WORKSPACE_ROOT / "outputs" / "temp" / "uploads"
    uploads_dir.mkdir(parents=True, exist_ok=True)

    ext = os.path.splitext(file.filename or "")[1] or ".jpg"
    filename = f"user_keyframe_beat_{beat_index + 1}_{uuid.uuid4().hex[:8]}{ext}"
    saved_path = uploads_dir / filename

    content = await file.read()
    with open(saved_path, "wb") as f:
        f.write(content)

    rel_path = os.path.relpath(saved_path, str(_WORKSPACE_ROOT))
    target_card.keyframe_path = f"/{rel_path}"
    target_card.is_custom_image = True
    target_card.edited_by_ai = False

    # Also link directly into active director session so Wan (I2V) anchors on this user image
    director = _ACTIVE_DIRECTORS.get(session_id)
    if director and director.current_session and director.current_session.plan:
        beat_num = beat_index + 1
        scene = next((s for s in director.current_session.plan.scenes if s.beat_index == beat_num), None)
        if scene:
            scene.keyframe_image_path = str(saved_path)
            scene.start_frame_path = str(saved_path)
            scene.conditioning_mode = ConditioningMode.START_FRAME_ONLY

    session.updated_at = datetime.now(timezone.utc)
    return target_card


@app.patch("/api/storyboard/beat")
async def update_storyboard_beat(req: StoryboardCardUpdateRequest) -> Dict[str, Any]:
    """Updates an individual storyboard card's speaker, dialogue, voice actor, prompt, or camera motion."""
    if req.session_id not in _ACTIVE_SESSIONS:
        raise HTTPException(status_code=404, detail="Session not found")

    session = _ACTIVE_SESSIONS[req.session_id]
    card = next((c for c in session.beats if c.beat_index == req.beat_index), None)
    if not card:
        raise HTTPException(status_code=404, detail=f"Beat index {req.beat_index} not found in session")

    if req.speaker is not None:
        card.speaker = req.speaker
    if req.voice_persona is not None:
        card.voice_actor = req.voice_persona
    if req.dialogue_text is not None:
        card.dialogue_text = req.dialogue_text
    if req.visual_prompt is not None:
        card.visual_prompt = req.visual_prompt
    if req.camera_motion is not None:
        card.camera_motion = req.camera_motion

    card.edited_by_ai = False  # Direct creator edit
    session.updated_at = datetime.now(timezone.utc)

    # Sync back to StoryboardSession on disk if available
    director = _ACTIVE_DIRECTORS.get(req.session_id)
    if director and getattr(director, "current_session", None):
        sb_session = director.current_session
        beat_num = req.beat_index + 1
        scene = next((s for s in sb_session.plan.scenes if s.beat_index == beat_num), None)
        if scene:
            if req.speaker is not None:
                scene.speaker = req.speaker
            if req.voice_persona is not None:
                scene.voice_persona = req.voice_persona
            if req.dialogue_text is not None:
                scene.dialogue_text = req.dialogue_text
            if req.visual_prompt is not None:
                scene.visual_prompt = req.visual_prompt
            if req.camera_motion is not None:
                scene.camera_movement = req.camera_motion
        director.session_manager.save_session(sb_session)

    return {
        "status": "updated",
        "session_id": req.session_id,
        "beat": card.model_dump(),
    }


@app.post("/api/director/chat")
async def director_chat(req: DirectorChatRequest) -> Dict[str, Any]:
    """Conversational Gemini Co-Director that applies natural language delta changes to storyboard cards."""
    if req.session_id not in _ACTIVE_SESSIONS:
        director = _ACTIVE_DIRECTORS.get(req.session_id) or InteractiveDirector()
        _ACTIVE_DIRECTORS[req.session_id] = director
        sb_session = getattr(director, "session_manager", None) and director.session_manager.load_session(req.session_id)
        if sb_session and sb_session.plan:
            await get_session(req.session_id)
        else:
            raise HTTPException(status_code=404, detail="Session not found")

    session = _ACTIVE_SESSIONS[req.session_id]

    # Record user message in thread
    user_msg = ChatMessage(
        sender="user",
        text=req.message,
    )
    session.chat_history.append(user_msg)

    # Use director chat engine to parse natural language intent
    from core.director_chat import process_co_director_message
    reply_text, delta = await process_co_director_message(
        user_message=req.message,
        session=session
    )

    # Apply delta if present (handle both single delta dict and list of deltas)
    deltas = delta if isinstance(delta, list) else [delta] if isinstance(delta, dict) else []

    for d in deltas:
        if not isinstance(d, dict):
            continue
        action = d.get("action")
        target_beat = d.get("target_beat")
        field = d.get("field")
        new_val = d.get("new_value")

        # Safe target card matching (supports both 0-indexed and 1-indexed beat references)
        target_card = next((c for c in session.beats if c.beat_index == target_beat), None)
        if not target_card and isinstance(target_beat, int) and 1 <= target_beat <= len(session.beats):
            target_card = next((c for c in session.beats if c.beat_index == target_beat - 1), None)

        if action == "UPDATE_BEAT" and target_card is not None:
            card = target_card
            if field == "visual_prompt":
                card.visual_prompt = new_val
                card.edited_by_ai = True
                # Auto-regenerate keyframe plate so creator sees the visual update immediately
                from core.local_visual_mock import generate_local_keyframe
                dim = (832, 480) if session.aspect_ratio == "16:9" else (480, 832) if session.aspect_ratio == "9:16" else (640, 640)
                new_keyframe = generate_local_keyframe(
                    prompt=card.visual_prompt,
                    scene_id=f"scene_{card.beat_index + 1}",
                    width=dim[0],
                    height=dim[1],
                    force_refresh=True,
                )
                rel = os.path.relpath(new_keyframe, str(_WORKSPACE_ROOT))
                card.keyframe_path = f"/{rel}"
                card.is_custom_image = False
            elif field in ["dialogue", "dialogue_text"]:
                card.dialogue_text = new_val
                card.edited_by_ai = True
            elif field == "camera_motion":
                card.camera_motion = new_val
            elif field in ["speaker", "character"]:
                card.speaker = new_val
                card.edited_by_ai = True
            elif field in ["voice_actor", "voice_persona"]:
                card.voice_actor = new_val
                card.edited_by_ai = True
        elif action == "REROLL_KEYFRAME" and target_card is not None:
            card = target_card
            from core.local_visual_mock import generate_local_keyframe
            dim = (832, 480) if session.aspect_ratio == "16:9" else (480, 832) if session.aspect_ratio == "9:16" else (640, 640)
            new_keyframe = generate_local_keyframe(
                prompt=card.visual_prompt,
                scene_id=f"scene_{card.beat_index + 1}",
                width=dim[0],
                height=dim[1],
                force_refresh=True,
            )
            rel = os.path.relpath(new_keyframe, str(_WORKSPACE_ROOT))
            card.keyframe_path = f"/{rel}"
            card.edited_by_ai = True
            card.is_custom_image = False
        elif action == "CHANGE_ASPECT_RATIO" and new_val in ["16:9", "9:16", "1:1"]:
            session.aspect_ratio = new_val
        elif action == "CHANGE_VOICE_PERSONA":
            new_persona = new_val or "auto"
            for card in session.beats:
                card.voice_actor = new_persona
                card.edited_by_ai = True
            director = _ACTIVE_DIRECTORS.get(req.session_id)
            if director and getattr(director, "current_session", None) and director.current_session.plan:
                director.current_session.plan.voice_persona = new_persona
        elif action == "CHANGE_MUSIC":
            director = _ACTIVE_DIRECTORS.get(req.session_id)
            if director and getattr(director, "current_session", None) and director.current_session.plan:
                director.current_session.plan.music_genre_and_mood = new_val

    # Persist updates to disk session
    director = _ACTIVE_DIRECTORS.get(req.session_id) or InteractiveDirector()
    _ACTIVE_DIRECTORS[req.session_id] = director
    sb_session = getattr(director, "session_manager", None) and director.session_manager.load_session(req.session_id)
    if sb_session and sb_session.plan:
        for card in session.beats:
            target_scene = next((s for s in sb_session.plan.scenes if s.beat_index == card.beat_index + 1), None)
            if target_scene:
                target_scene.visual_prompt = card.visual_prompt
                target_scene.dialogue_text = card.dialogue_text
                target_scene.camera_movement = card.camera_motion
                if card.keyframe_path and not card.keyframe_path.startswith("http"):
                    target_scene.keyframe_image_path = os.path.join(str(_WORKSPACE_ROOT), card.keyframe_path.lstrip("/"))
        director.session_manager.save_session(sb_session)

    # Record AI message in thread
    ai_msg = ChatMessage(
        sender="director_ai",
        text=reply_text,
        applied_delta=delta,
    )
    session.chat_history.append(ai_msg)
    session.updated_at = datetime.now(timezone.utc)

    return {
        "reply": reply_text,
        "applied_delta": delta,
        "updated_beats": session.beats,
        "session": session,
    }


async def _render_single_beat_core(
    session: StudioSession,
    card: StoryboardCard,
    backend: str = "serverless",
    director: Optional[InteractiveDirector] = None,
) -> str:
    """Executes video generation for a single storyboard card and returns absolute output video path."""
    temp_dir = os.path.join(str(_WORKSPACE_ROOT), "outputs", "temp")
    os.makedirs(temp_dir, exist_ok=True)
    out_video_path = os.path.join(temp_dir, f"scene_{card.beat_index + 1}_{session.session_id[:8]}.mp4")

    # Sync card keyframe path if present
    img_disk_path = None
    if card.keyframe_path and not card.keyframe_path.startswith("http"):
        p = os.path.join(str(_WORKSPACE_ROOT), card.keyframe_path.lstrip("/"))
        if os.path.exists(p):
            img_disk_path = p

    # 1. If backend is serverless and available
    serverless_client = RunPodServerlessClient()
    use_serverless = (backend == "serverless" or backend == "auto") and serverless_client.is_available()

    if use_serverless:
        from core.runpod_client import build_wan3_workflow_payload
        from core.models import Wan3WorkflowConfig, VideoAspectRatio, ASPECT_RATIO_RESOLUTIONS
        from core.runpod_serverless import RunPodServerlessError, calculate_safe_video_frames, ensure_video_duration_coverage

        dim = ASPECT_RATIO_RESOLUTIONS.get(VideoAspectRatio(session.aspect_ratio), (1920, 1080))
        if dim[0] > dim[1]:
            render_w, render_h = 832, 480
        elif dim[0] < dim[1]:
            render_w, render_h = 480, 832
        else:
            render_w, render_h = 640, 640

        safe_frames = calculate_safe_video_frames(card.duration_seconds, fps=16.0)
        init_image = img_disk_path if (card.is_chained or card.is_custom_image) else None

        wan_cfg = Wan3WorkflowConfig(
            prompt=card.visual_prompt,
            negative_prompt="blurry, low quality, distorted anatomy, jitter, artifacts, realistic photography, inconsistent clothing, style drift",
            width=render_w,
            height=render_h,
            duration_frames=safe_frames,
            steps=12,
            reference_images=[init_image] if init_image else [],
        )
        workflow = build_wan3_workflow_payload(wan_cfg)

        try:
            dest_video = os.path.join(temp_dir, f"serverless_beat_{card.beat_index}_{session.session_id[:8]}.mp4")
            job_id = await asyncio.to_thread(serverless_client.run_job, workflow)
            poll_res = await asyncio.to_thread(serverless_client.poll_job, job_id)
            output_payload = poll_res.get("output")
            if not output_payload:
                raise RunPodServerlessError(f"Serverless job {job_id} returned empty output")
            rendered = serverless_client.parse_and_download_output(output_payload, dest_video)
            rendered = ensure_video_duration_coverage(rendered, card.duration_seconds)
            return rendered
        except Exception as e:
            print(f"⚠️ Serverless single-beat execution failed ({e}). Cascading to next tier.")

    # 2. Dedicated ComfyUI Pod execution
    if backend == "pod" and director and getattr(director, "comfy_client", None):
        try:
            from core.visual_router import route_and_execute_beat
            from core.models import SceneBeat
            temp_beat = SceneBeat(
                beat_index=card.beat_index + 1,
                visual_prompt=card.visual_prompt,
                duration_sec=card.duration_seconds,
                camera_movement=card.camera_motion,
                conditioning_mode="start_frame_only" if (card.is_chained or card.is_custom_image) else "pure_t2v",
                start_frame_path=img_disk_path if (card.is_chained or card.is_custom_image) else None,
            )
            route_and_execute_beat(temp_beat, output_video_path=out_video_path, comfy_client=director.comfy_client, backend="pod")
            if temp_beat.output_video_path and os.path.exists(temp_beat.output_video_path):
                return temp_beat.output_video_path
        except Exception as e:
            print(f"⚠️ Pod single-beat execution failed ({e}). Cascading to local plate.")

    # 3. Local / Mock video plate generation
    if not img_disk_path or not os.path.exists(img_disk_path):
        from core.local_visual_mock import generate_local_keyframe, get_cached_keyframe_path
        dim = (1280, 720) if session.aspect_ratio == "16:9" else (720, 1280)
        img_disk_path = get_cached_keyframe_path(card.visual_prompt)
        generate_local_keyframe(
            prompt=card.visual_prompt,
            scene_id=f"scene_{card.beat_index + 1}",
            width=dim[0],
            height=dim[1],
            output_path=img_disk_path,
        )
        rel = os.path.relpath(img_disk_path, str(_WORKSPACE_ROOT))
        card.keyframe_path = f"/{rel}"

    # Generate MP4 using OpenCV from keyframe image
    import cv2
    import numpy as np
    import subprocess

    img = cv2.imread(img_disk_path)
    if img is None:
        dim = (1280, 720) if session.aspect_ratio == "16:9" else (720, 1280)
        img = np.zeros((dim[1], dim[0], 3), dtype=np.uint8)

    h, w = img.shape[:2]
    w = w - (w % 2)
    h = h - (h % 2)
    img = cv2.resize(img, (w, h))

    fps = 16.0
    total_frames = max(16, int(round(card.duration_seconds * fps)))
    raw_video_path = os.path.join(temp_dir, f"raw_scene_{card.beat_index + 1}_{session.session_id[:8]}.mp4")
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    writer = cv2.VideoWriter(raw_video_path, fourcc, fps, (w, h))

    motion = (card.camera_motion or "push_in").lower()
    for frame_idx in range(total_frames):
        t = frame_idx / max(1, total_frames - 1)
        if "zoom" in motion or "push" in motion:
            scale = 1.0 + 0.08 * t
            nh, nw = int(h * scale), int(w * scale)
            zoomed = cv2.resize(img, (nw, nh), interpolation=cv2.INTER_LINEAR)
            dy = (nh - h) // 2
            dx = (nw - w) // 2
            frame = zoomed[dy:dy + h, dx:dx + w]
        elif "pan" in motion:
            dx = int(0.05 * w * t)
            frame = np.roll(img, dx, axis=1)
        else:
            frame = img.copy()
        writer.write(frame)
    writer.release()

    # Transcode OpenCV mp4v to web-compatible H.264 (avc1) via ffmpeg
    cmd = [
        "ffmpeg", "-y", "-i", raw_video_path,
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        out_video_path
    ]
    res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if res.returncode == 0 and os.path.exists(out_video_path):
        if os.path.exists(raw_video_path):
            try:
                os.remove(raw_video_path)
            except OSError:
                pass
    elif os.path.exists(raw_video_path):
        os.replace(raw_video_path, out_video_path)

    return out_video_path


@app.post("/api/render/beat")
async def render_single_beat(req: RenderBeatRequest) -> Dict[str, Any]:
    """Renders a single narrative beat card in isolation."""
    if req.session_id not in _ACTIVE_SESSIONS:
        director = _ACTIVE_DIRECTORS.get(req.session_id) or InteractiveDirector()
        _ACTIVE_DIRECTORS[req.session_id] = director
        sb_session = getattr(director, "session_manager", None) and director.session_manager.load_session(req.session_id)
        if sb_session and sb_session.plan:
            await get_session(req.session_id)
        else:
            raise HTTPException(status_code=404, detail="Session not found")

    session = _ACTIVE_SESSIONS[req.session_id]
    card = next((c for c in session.beats if c.beat_index == req.beat_index), None)
    if not card:
        raise HTTPException(status_code=404, detail=f"Beat index {req.beat_index} not found in session")

    director = _ACTIVE_DIRECTORS.get(req.session_id) or InteractiveDirector()
    _ACTIVE_DIRECTORS[req.session_id] = director

    card.render_status = "rendering"
    card.error_message = None

    try:
        backend_choice = req.backend or session.backend_strategy.value
        output_abs = await _render_single_beat_core(
            session=session,
            card=card,
            backend=backend_choice,
            director=director,
        )

        rel = os.path.relpath(output_abs, str(_WORKSPACE_ROOT))
        card.output_video_path = f"/{rel}"
        card.render_status = "completed"

        # Check if downstream beat was chained from this beat: flag out of sync
        for other_card in session.beats:
            if other_card.is_chained and other_card.chained_from_beat == req.beat_index:
                other_card.chain_out_of_sync = True

        # Sync back to StoryboardSession on disk
        sb_session = getattr(director, "current_session", None) or (
            getattr(director, "session_manager", None) and director.session_manager.load_session(req.session_id)
        )
        if sb_session and sb_session.plan:
            beat_num = card.beat_index + 1
            scene = next((s for s in sb_session.plan.scenes if s.beat_index == beat_num), None)
            if scene:
                scene.output_video_path = output_abs
            director.session_manager.save_session(sb_session)

        session.updated_at = datetime.now(timezone.utc)

        return {
            "status": "completed",
            "session_id": req.session_id,
            "beat_index": req.beat_index,
            "output_video_path": card.output_video_path,
            "beat": card.model_dump(),
        }
    except Exception as e:
        card.render_status = "failed"
        card.error_message = str(e)
        session.updated_at = datetime.now(timezone.utc)
        raise HTTPException(status_code=500, detail=f"Single beat render failed: {e}")


@app.post("/api/storyboard/chain-frame")
async def chain_frame_to_next_beat(req: ChainFrameRequest) -> Dict[str, Any]:
    """Extracts Frame -1 from source beat video and binds it as START_FRAME to the next beat."""
    if req.session_id not in _ACTIVE_SESSIONS:
        director = _ACTIVE_DIRECTORS.get(req.session_id) or InteractiveDirector()
        _ACTIVE_DIRECTORS[req.session_id] = director
        sb_session = getattr(director, "session_manager", None) and director.session_manager.load_session(req.session_id)
        if sb_session and sb_session.plan:
            await get_session(req.session_id)
        else:
            raise HTTPException(status_code=404, detail="Session not found")

    session = _ACTIVE_SESSIONS[req.session_id]
    source_card = next((c for c in session.beats if c.beat_index == req.source_beat_index), None)
    if not source_card:
        raise HTTPException(status_code=404, detail=f"Source beat index {req.source_beat_index} not found")

    target_beat_index = req.source_beat_index + 1
    target_card = next((c for c in session.beats if c.beat_index == target_beat_index), None)
    if not target_card:
        raise HTTPException(status_code=400, detail=f"Source beat {req.source_beat_index + 1} is the terminal shot in the storyboard")

    if not source_card.output_video_path:
        raise HTTPException(status_code=400, detail=f"Source beat {req.source_beat_index + 1} must be rendered before chaining its final frame")

    source_video_disk = os.path.join(str(_WORKSPACE_ROOT), source_card.output_video_path.lstrip("/"))
    if not os.path.exists(source_video_disk):
        raise HTTPException(status_code=404, detail=f"Rendered video clip not found on disk at {source_video_disk}")

    # Extract terminal frame
    temp_dir = os.path.join(str(_WORKSPACE_ROOT), "outputs", "temp")
    os.makedirs(temp_dir, exist_ok=True)
    chain_filename = f"chain_{session.session_id[:8]}_shot_{req.source_beat_index}_to_{target_beat_index}.png"
    chain_dest_path = os.path.join(temp_dir, chain_filename)

    try:
        extract_terminal_frame(source_video_disk, chain_dest_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OpenCV terminal frame extraction failed: {e}")

    rel_chain = os.path.relpath(chain_dest_path, str(_WORKSPACE_ROOT))
    target_card.keyframe_path = f"/{rel_chain}"
    target_card.is_chained = True
    target_card.chained_from_beat = req.source_beat_index
    target_card.chain_out_of_sync = False

    # Sync into StoryboardSession on disk
    director = _ACTIVE_DIRECTORS.get(req.session_id) or InteractiveDirector()
    _ACTIVE_DIRECTORS[req.session_id] = director
    sb_session = getattr(director, "current_session", None) or (
        getattr(director, "session_manager", None) and director.session_manager.load_session(req.session_id)
    )
    if sb_session and sb_session.plan:
        target_scene = next((s for s in sb_session.plan.scenes if s.beat_index == target_beat_index + 1), None)
        if target_scene:
            target_scene.keyframe_image_path = chain_dest_path
            target_scene.start_frame_path = chain_dest_path
            target_scene.conditioning_mode = ConditioningMode.START_FRAME_ONLY
            target_scene.is_chained = True
            target_scene.chained_from_beat = req.source_beat_index
        director.session_manager.save_session(sb_session)

    session.updated_at = datetime.now(timezone.utc)

    return {
        "status": "chained",
        "session_id": req.session_id,
        "source_beat_index": req.source_beat_index,
        "target_beat_index": target_beat_index,
        "chained_frame_path": target_card.keyframe_path,
        "target_card": target_card.model_dump(),
    }


@app.post("/api/storyboard/unlink-chain")
async def unlink_chained_beat(req: UnlinkChainRequest) -> Dict[str, Any]:
    """Unlinks a chained beat, clearing START_FRAME conditioning and reverting to independent keyframe."""
    if req.session_id not in _ACTIVE_SESSIONS:
        director = _ACTIVE_DIRECTORS.get(req.session_id) or InteractiveDirector()
        _ACTIVE_DIRECTORS[req.session_id] = director
        sb_session = getattr(director, "session_manager", None) and director.session_manager.load_session(req.session_id)
        if sb_session and sb_session.plan:
            await get_session(req.session_id)
        else:
            raise HTTPException(status_code=404, detail="Session not found")

    session = _ACTIVE_SESSIONS[req.session_id]
    target_card = next((c for c in session.beats if c.beat_index == req.beat_index), None)
    if not target_card:
        raise HTTPException(status_code=404, detail=f"Beat index {req.beat_index} not found")

    target_card.is_chained = False
    target_card.chained_from_beat = None
    target_card.chain_out_of_sync = False

    # Revert to prompt-generated keyframe
    from core.local_visual_mock import generate_local_keyframe, get_cached_keyframe_path
    dim = (1280, 720) if session.aspect_ratio == "16:9" else (720, 1280)
    img_disk_path = get_cached_keyframe_path(target_card.visual_prompt)
    if not os.path.exists(img_disk_path):
        generate_local_keyframe(
            prompt=target_card.visual_prompt,
            scene_id=f"scene_{target_card.beat_index + 1}",
            width=dim[0],
            height=dim[1],
            output_path=img_disk_path,
        )
    rel = os.path.relpath(img_disk_path, str(_WORKSPACE_ROOT))
    target_card.keyframe_path = f"/{rel}"

    # Sync back to StoryboardSession on disk
    director = _ACTIVE_DIRECTORS.get(req.session_id) or InteractiveDirector()
    _ACTIVE_DIRECTORS[req.session_id] = director
    sb_session = getattr(director, "current_session", None) or (
        getattr(director, "session_manager", None) and director.session_manager.load_session(req.session_id)
    )
    if sb_session and sb_session.plan:
        target_scene = next((s for s in sb_session.plan.scenes if s.beat_index == req.beat_index + 1), None)
        if target_scene:
            target_scene.keyframe_image_path = img_disk_path
            target_scene.start_frame_path = None
            target_scene.conditioning_mode = ConditioningMode.PURE_T2V
            target_scene.is_chained = False
            target_scene.chained_from_beat = None
        director.session_manager.save_session(sb_session)

    session.updated_at = datetime.now(timezone.utc)

    return {
        "status": "unlinked",
        "beat_index": req.beat_index,
        "target_card": target_card.model_dump(),
    }


@app.post("/api/render/compile")
async def compile_master_video(req: CompileMasterRequest) -> Dict[str, Any]:
    """Compiles individually rendered scene clips into a final master video in seconds."""
    if req.session_id not in _ACTIVE_SESSIONS:
        director = _ACTIVE_DIRECTORS.get(req.session_id) or InteractiveDirector()
        _ACTIVE_DIRECTORS[req.session_id] = director
        sb_session = getattr(director, "session_manager", None) and director.session_manager.load_session(req.session_id)
        if sb_session and sb_session.plan:
            await get_session(req.session_id)
        else:
            raise HTTPException(status_code=404, detail="Session not found")

    session = _ACTIVE_SESSIONS[req.session_id]
    completed_cards = [
        c for c in session.beats
        if c.output_video_path and os.path.exists(os.path.join(str(_WORKSPACE_ROOT), c.output_video_path.lstrip("/")))
    ]

    if not req.allow_partial and len(completed_cards) < len(session.beats):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot compile master video: {len(session.beats) - len(completed_cards)} beats are not yet rendered. Set allow_partial=True to compile available clips."
        )

    if not completed_cards:
        raise HTTPException(status_code=400, detail="Cannot compile master video: No rendered clips exist.")

    # Destination master MP4
    temp_dir = os.path.join(str(_WORKSPACE_ROOT), "outputs", "temp")
    os.makedirs(temp_dir, exist_ok=True)
    master_video_abs = os.path.join(str(_OUTPUTS_DIR), f"{session.session_id}_master.mp4")

    # Fast Concat Assembly
    valid_clips = [
        os.path.abspath(os.path.join(str(_WORKSPACE_ROOT), c.output_video_path.lstrip("/")))
        for c in completed_cards
    ]

    concat_list_file = os.path.join(temp_dir, f"concat_{session.session_id[:8]}.txt")
    with open(concat_list_file, "w") as cf:
        for cpath in valid_clips:
            cf.write(f"file '{cpath}'\n")

    assembled = False
    try:
        cmd = ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_list_file, "-c", "copy", master_video_abs]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        assembled = True
    except Exception:
        try:
            cmd = ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_list_file, "-c:v", "libx264", "-pix_fmt", "yuv420p", master_video_abs]
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            assembled = True
        except Exception:
            pass

    if not assembled or not os.path.exists(master_video_abs):
        import cv2
        fps = 16.0
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        writer = None
        for cpath in valid_clips:
            cap = cv2.VideoCapture(cpath)
            while cap.isOpened():
                ret, frame = cap.read()
                if not ret or frame is None:
                    break
                if writer is None:
                    h, w = frame.shape[:2]
                    writer = cv2.VideoWriter(master_video_abs, fourcc, fps, (w, h))
                writer.write(frame)
            cap.release()
        if writer:
            writer.release()

    if not os.path.exists(master_video_abs):
        shutil.copy2(valid_clips[0], master_video_abs)

    rel_master = os.path.relpath(master_video_abs, str(_WORKSPACE_ROOT))
    session.master_video_path = f"/{rel_master}"
    session.status = "completed"
    session.updated_at = datetime.now(timezone.utc)

    # Persist session to disk
    director = _ACTIVE_DIRECTORS.get(req.session_id) or InteractiveDirector()
    _ACTIVE_DIRECTORS[req.session_id] = director
    sb_session = getattr(director, "current_session", None) or (
        getattr(director, "session_manager", None) and director.session_manager.load_session(req.session_id)
    )
    if sb_session:
        director.session_manager.save_session(sb_session)

    total_duration = sum(c.duration_seconds for c in completed_cards)

    return {
        "status": "completed",
        "session_id": req.session_id,
        "master_video_path": session.master_video_path,
        "duration_seconds": round(total_duration, 2),
    }


@app.post("/api/render/start")
async def start_render(req: RenderStartRequest, bg: BackgroundTasks) -> Dict[str, Any]:
    """Initiates multi-beat video synthesis across parallel backend workers."""
    if req.session_id not in _ACTIVE_SESSIONS:
        director = _ACTIVE_DIRECTORS.get(req.session_id) or InteractiveDirector()
        _ACTIVE_DIRECTORS[req.session_id] = director
        sb_session = getattr(director, "session_manager", None) and director.session_manager.load_session(req.session_id)
        if sb_session and sb_session.plan:
            await get_session(req.session_id)
        else:
            raise HTTPException(status_code=404, detail="Session not found")

    session = _ACTIVE_SESSIONS[req.session_id]
    session.status = "rendering"
    session.backend_strategy = BackendExecutionStrategy(req.backend) if req.backend in [b.value for b in BackendExecutionStrategy] else BackendExecutionStrategy.SERVERLESS

    # Initialize telemetry
    telemetry = TelemetryState(
        total_workers=len(session.beats),
        active_workers=len(session.beats),
        elapsed_seconds=0.0,
        estimated_cost_usd=0.0,
        worker_tiles=[
            TelemetryWorkerTile(
                worker_id=f"worker-{c.beat_index + 1}",
                beat_index=c.beat_index,
                status="in_queue",
                elapsed_seconds=0.0,
                progress_percent=0
            )
            for c in session.beats
        ]
    )
    _ACTIVE_TELEMETRY[req.session_id] = telemetry
    session.telemetry = telemetry

    # Run synthesis in background task
    async def _render_job():
        start_time = time.time()
        try:
            director = _ACTIVE_DIRECTORS.get(req.session_id)
            if not director:
                director = InteractiveDirector()
                _ACTIVE_DIRECTORS[req.session_id] = director

            # Load persistent session if not set in memory
            sb_session = getattr(director, "current_session", None)
            if not sb_session or not sb_session.plan:
                sb_session = getattr(director, "session_manager", None) and director.session_manager.load_session(req.session_id)
                if sb_session:
                    director.current_session = sb_session

            if not sb_session or not sb_session.plan:
                raise ValueError(f"Storyboard session '{req.session_id}' could not be loaded from memory or disk.")

            # Sync cards back to session plan
            if session.beats and session.beats[0].voice_actor:
                sb_session.plan.voice_persona = session.beats[0].voice_actor
            for card in session.beats:
                beat_num = card.beat_index + 1
                scene = next((s for s in sb_session.plan.scenes if s.beat_index == beat_num), None)
                if scene:
                    scene.visual_prompt = card.visual_prompt
                    scene.speaker = getattr(card, "speaker", "Narrator") or "Narrator"
                    scene.dialogue_text = card.dialogue_text
                    scene.voice_persona = card.voice_actor
                    if card.keyframe_path:
                        clean_rel = card.keyframe_path.lstrip("/")
                        disk_path = str(_WORKSPACE_ROOT / clean_rel)
                        if os.path.exists(disk_path):
                            scene.keyframe_image_path = disk_path
                            if card.is_custom_image:
                                scene.start_frame_path = disk_path
                                scene.conditioning_mode = ConditioningMode.START_FRAME_ONLY

            # Save synced plan
            director.session_manager.save_session(sb_session)

            # Telemetry progress callback
            def _progress_cb(idx: int, name: str, status: str):
                if req.session_id in _ACTIVE_TELEMETRY:
                    t = _ACTIVE_TELEMETRY[req.session_id]
                    if idx < len(t.worker_tiles):
                        tile = t.worker_tiles[idx]
                        tile.status = status.lower()
                        s_lower = status.lower()
                        if "in_queue" in s_lower:
                            tile.progress_percent = 20
                        elif "submitting" in s_lower:
                            tile.progress_percent = 10
                        elif "downloading" in s_lower or "in_progress" in s_lower:
                            tile.progress_percent = 70
                        elif "completed" in s_lower:
                            tile.progress_percent = 100

            out_file = _OUTPUTS_DIR / f"{session.session_id}_master.mp4"

            # Execute rendering asynchronously
            render_output = await director.render_approved_session(
                session=sb_session,
                output_path=str(out_file),
                backend=session.backend_strategy.value,
                progress_cb=_progress_cb,
            )
            
            # Update cards with rendered outputs from sb_session.plan.scenes
            for card in session.beats:
                beat_num = card.beat_index + 1
                scene = next((s for s in sb_session.plan.scenes if s.beat_index == beat_num), None)
                if scene and scene.output_video_path and os.path.exists(scene.output_video_path):
                    rel = os.path.relpath(scene.output_video_path, str(_WORKSPACE_ROOT))
                    card.output_video_path = f"/{rel}"
                    card.render_status = "completed"

            # Set master composition output path
            if out_file.exists():
                session.master_video_path = f"/outputs/{session.session_id}_master.mp4"
            elif session.beats and session.beats[0].output_video_path:
                session.master_video_path = session.beats[0].output_video_path

            session.status = "completed"
            session.updated_at = datetime.now(timezone.utc)
        except Exception as e:
            session.status = "failed"
            print(f"Error rendering session {session.session_id}: {e}")
            import traceback
            traceback.print_exc()
        finally:
            elapsed = time.time() - start_time
            if req.session_id in _ACTIVE_TELEMETRY:
                t = _ACTIVE_TELEMETRY[req.session_id]
                t.elapsed_seconds = elapsed
                t.active_workers = 0
                t.estimated_cost_usd = round(elapsed * 0.00021 * len(session.beats), 4)

    bg.add_task(_render_job)

    return {
        "status": "DISPATCHED",
        "session_id": req.session_id,
        "worker_count": len(session.beats),
    }


@app.post("/api/render/cancel")
async def cancel_render(req: Dict[str, str]) -> Dict[str, Any]:
    """Immediately terminates all in-flight cloud serverless rendering jobs."""
    session_id = req.get("session_id")
    if not session_id or session_id not in _ACTIVE_SESSIONS:
        raise HTTPException(status_code=404, detail="Session not found")

    session = _ACTIVE_SESSIONS[session_id]
    session.status = "cancelled"

    # Terminate active cloud jobs
    try:
        client = RunPodServerlessClient()
        cancelled_count = client.cancel_batch()
    except Exception:
        cancelled_count = 0

    if session_id in _ACTIVE_TELEMETRY:
        _ACTIVE_TELEMETRY[session_id].active_workers = 0

    return {
        "cancelled": True,
        "jobs_terminated": cancelled_count,
    }


@app.get("/api/events")
async def events_stream(request: Request):
    """Server-Sent Events (SSE) streaming live telemetry and worker status updates."""
    async def event_generator():
        while True:
            if await request.is_disconnected():
                break

            # Broadcast latest telemetry from any active session
            latest_telemetry = None
            for s_id, t in _ACTIVE_TELEMETRY.items():
                latest_telemetry = t.model_dump()
                break

            if latest_telemetry:
                yield {
                    "event": "telemetry",
                    "data": latest_telemetry
                }

            await asyncio.sleep(1.5)

    return EventSourceResponse(event_generator())


@app.get("/api/export/{session_id}")
async def export_video(session_id: str):
    """Downloads the rendered master MP4 file."""
    if session_id not in _ACTIVE_SESSIONS:
        raise HTTPException(status_code=404, detail="Session not found")

    session = _ACTIVE_SESSIONS[session_id]
    if not session.master_video_path:
        raise HTTPException(status_code=400, detail="Video is not rendered yet")

    full_path = _WORKSPACE_ROOT / session.master_video_path.lstrip("/")
    if not full_path.exists():
        raise HTTPException(status_code=404, detail="Master video file not found")

    return FileResponse(
        path=str(full_path),
        filename=f"studio_{session_id[:8]}.mp4",
        media_type="video/mp4"
    )


# Mount built React Studio SPA at root if present
_STUDIO_DIST = _WORKSPACE_ROOT / "studio" / "dist"
if _STUDIO_DIST.exists():
    app.mount("/", StaticFiles(directory=str(_STUDIO_DIST), html=True), name="studio_ui")

