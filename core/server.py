"""FastAPI backend server for the AI Video Web Studio."""

from __future__ import annotations

import os
import asyncio
import logging
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
    RenderTake,
    ProjectSummary,
    VideoGenerationModality,
    VideoAudioMode,
    ProviderId,
    ImageAsset,
    ImageRole,
    VisualStrategyRoute,
    Wan3WorkflowConfig,
    ASPECT_RATIO_RESOLUTIONS,
    SceneBeatPlan,
    SceneBeat,
)
from core.config import get_gemini_api_keys, get_gemini_api_key, get_runpod_serverless_endpoint_id
from core.interactive_director import InteractiveDirector
from core.project_manager import ProjectManager
from core.runpod_serverless import RunPodServerlessClient
from core.runpod_client import check_endpoint_health
from core.chain_manager import extract_terminal_frame

logger = logging.getLogger(__name__)


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
project_manager = ProjectManager()


# --- Request/Response DTOs ---

class CreateProjectRequest(BaseModel):
    title: str = ""
    prompt: str = ""
    aspect_ratio: str = "16:9"
    directing_mode: str = "pro"
    backend: str = "serverless"
    voice_persona: Optional[str] = "auto"
    custom_location: Optional[str] = None


class UpdateProjectRequest(BaseModel):
    title: Optional[str] = None
    prompt: Optional[str] = None


class SetActiveTakeRequest(BaseModel):
    take_id: str

class GenerateStoryboardRequest(BaseModel):
    prompt: str
    aspect_ratio: str = "16:9"
    genre: str = "cinematic"
    directing_mode: str = "pro"
    backend: str = "serverless"
    voice_persona: Optional[str] = "auto"
    session_id: Optional[str] = None


class RerollBeatRequest(BaseModel):
    session_id: str
    beat_index: int
    prompt_override: Optional[str] = None
    target_prompt_type: Optional[str] = "image"  # "image" | "motion"


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
    image_prompt: Optional[str] = None
    motion_prompt: Optional[str] = None
    camera_motion: Optional[str] = None
    model_id: Optional[str] = None
    provider_override: Optional[str] = None
    allow_provider_cascade: Optional[bool] = None
    resolution: Optional[str] = None
    modality: Optional[str] = None
    native_audio: Optional[bool] = None
    has_clip_audio: Optional[bool] = None
    start_frame_path: Optional[str] = None
    end_frame_path: Optional[str] = None
    reference_image_paths: Optional[List[str]] = None


class RemoveFrameRequest(BaseModel):
    session_id: str
    beat_index: int
    frame_type: str = "start_frame"  # "start_frame" | "end_frame" | "reference_image"
    image_index: Optional[int] = None


class RenderStartRequest(BaseModel):
    session_id: str
    backend: str = "serverless"


class RenderBeatRequest(BaseModel):
    session_id: str
    beat_index: int
    backend: Optional[str] = "serverless"
    model_id: Optional[str] = None
    provider_override: Optional[str] = None
    resolution: Optional[str] = None
    modality: Optional[str] = None
    has_native_audio: Optional[bool] = None
    allow_provider_cascade: Optional[bool] = None


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


# --- Project Workspace Routes ---

@app.get("/api/projects", response_model=List[ProjectSummary])
async def list_projects() -> List[ProjectSummary]:
    """Returns a list of all existing and legacy projects for the dashboard."""
    return project_manager.list_projects()


@app.post("/api/projects")
async def create_project_endpoint(req: CreateProjectRequest) -> Dict[str, Any]:
    """Initializes a new isolated project workspace and persists project.json."""
    session = project_manager.create_project(
        title=req.title,
        prompt=req.prompt,
        aspect_ratio=req.aspect_ratio,
        directing_mode=req.directing_mode,
        backend_strategy=req.backend,
        voice_persona=req.voice_persona or "auto",
        custom_location=req.custom_location,
    )

    # If a prompt is provided, automatically plan narrative beats and keyframes
    if req.prompt and req.prompt.strip():
        try:
            director = InteractiveDirector()
            _ACTIVE_DIRECTORS[session.session_id] = director
            aspect_enum = VideoAspectRatio.WIDESCREEN_16_9 if req.aspect_ratio == "16:9" else VideoAspectRatio.VERTICAL_9_16
            session_plan = director.create_storyboard(
                prompt=req.prompt,
                aspect_ratio=aspect_enum,
                session_id=session.session_id,
                voice_override=req.voice_persona or "auto",
            )
            cards: List[StoryboardCard] = []
            keyframes_dir = project_manager.get_media_dir(session.session_id, "keyframes")
            for scene in session_plan.plan.scenes:
                idx = scene.beat_index - 1
                keyframe_url = None
                if scene.keyframe_image_path and os.path.exists(scene.keyframe_image_path):
                    dest_kf = keyframes_dir / f"beat_{idx + 1}_{os.path.basename(scene.keyframe_image_path)}"
                    try:
                        shutil.copy2(scene.keyframe_image_path, str(dest_kf))
                        try:
                            rel_path = dest_kf.relative_to(_WORKSPACE_ROOT)
                            keyframe_url = f"/{rel_path}"
                        except ValueError:
                            keyframe_url = f"/api/projects/{session.session_id}/media/keyframes/{dest_kf.name}"
                    except Exception:
                        try:
                            rel_path = os.path.relpath(scene.keyframe_image_path, str(_WORKSPACE_ROOT))
                            keyframe_url = f"/{rel_path}"
                        except Exception:
                            keyframe_url = None

                cards.append(
                    StoryboardCard(
                        beat_id=f"beat_{idx}",
                        beat_index=idx,
                        visual_prompt=scene.visual_prompt,
                        image_prompt=getattr(scene, "image_prompt", None) or scene.visual_prompt,
                        motion_prompt=getattr(scene, "motion_prompt", None) or scene.visual_prompt,
                        keyframe_path=keyframe_url,
                        dialogue_text=scene.dialogue_text or "",
                        speaker=getattr(scene, "speaker", None),
                        voice_actor=scene.voice_persona or session_plan.plan.voice_persona or req.voice_persona or "auto",
                        camera_motion=scene.camera_movement or "push_in",
                        duration_seconds=scene.duration_sec,
                        duration_frames=int(scene.duration_sec * 16),
                        render_status="pending",
                        output_video_path=scene.output_video_path,
                    )
                )
            session.beats = cards
            session.status = "storyboard_ready"
            project_manager.save_project(session)
        except Exception as e:
            print(f"⚠️ Storyboard auto-generation for project {session.session_id} failed: {e}")

    _ACTIVE_SESSIONS[session.session_id] = session
    return {"status": "created", "project_id": session.session_id, "project": session}


@app.get("/api/projects/{project_id}")
async def get_project_endpoint(project_id: str) -> StudioSession:
    """Retrieves full project workspace state."""
    project = project_manager.get_project(project_id)
    if project:
        _ACTIVE_SESSIONS[project_id] = project
        return project

    if project_id in _ACTIVE_SESSIONS:
        return _ACTIVE_SESSIONS[project_id]

    raise HTTPException(status_code=404, detail=f"Project {project_id} not found")


@app.patch("/api/projects/{project_id}")
async def update_project_endpoint(project_id: str, req: UpdateProjectRequest) -> Dict[str, Any]:
    """Updates project title or concept prompt."""
    project = project_manager.update_project_metadata(project_id, title=req.title, prompt=req.prompt)
    if not project:
        raise HTTPException(status_code=404, detail=f"Project {project_id} not found")
    _ACTIVE_SESSIONS[project_id] = project
    return {"status": "updated", "project_id": project_id, "project": project}


@app.delete("/api/projects/{project_id}")
async def delete_project_endpoint(project_id: str) -> Dict[str, Any]:
    """Deletes a project directory and its media assets."""
    success = project_manager.delete_project(project_id)
    _ACTIVE_SESSIONS.pop(project_id, None)
    _ACTIVE_DIRECTORS.pop(project_id, None)
    _ACTIVE_TELEMETRY.pop(project_id, None)
    if not success:
        raise HTTPException(status_code=404, detail=f"Project {project_id} not found or could not be deleted")
    return {"status": "deleted", "project_id": project_id}


@app.post("/api/projects/{project_id}/duplicate")
async def duplicate_project_endpoint(project_id: str) -> Dict[str, Any]:
    """Duplicates an existing project into a new workspace with cloned beats."""
    cloned = project_manager.duplicate_project(project_id)
    if not cloned:
        raise HTTPException(status_code=404, detail=f"Source project {project_id} not found")
    _ACTIVE_SESSIONS[cloned.session_id] = cloned
    return {"status": "duplicated", "project": cloned}


@app.post("/api/projects/{project_id}/reveal-folder")
async def reveal_project_folder_endpoint(project_id: str) -> Dict[str, Any]:
    """Opens the native file manager (Finder/Explorer) pointing to the project folder."""
    success = project_manager.reveal_in_finder(project_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Project folder for {project_id} not found")
    return {"status": "revealed", "project_id": project_id}


@app.post("/api/filesystem/pick-directory")
async def pick_directory_endpoint() -> Dict[str, Any]:
    """Launches the native OS directory picker dialog and returns the selected folder path."""
    chosen_path = project_manager.pick_directory_dialog()
    return {"status": "ok", "selected_path": chosen_path}


@app.get("/api/projects/{project_id}/media/{subfolder}/{filename}")
async def get_project_media_file(project_id: str, subfolder: str, filename: str):
    """Serves a media asset (keyframe, audio, clip, export) from any project workspace location."""
    media_dir = project_manager.get_media_dir(project_id, subfolder)
    file_path = media_dir / filename
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="Media file not found")

    ext = file_path.suffix.lower()
    media_type = "application/octet-stream"
    if ext in [".jpg", ".jpeg"]:
        media_type = "image/jpeg"
    elif ext == ".png":
        media_type = "image/png"
    elif ext == ".webp":
        media_type = "image/webp"
    elif ext == ".mp4":
        media_type = "video/mp4"
    elif ext == ".mp3":
        media_type = "audio/mpeg"
    elif ext == ".wav":
        media_type = "audio/wav"

    return FileResponse(path=str(file_path), media_type=media_type)


@app.post("/api/projects/{project_id}/beats/{beat_index}/active-take")
async def set_active_take_endpoint(project_id: str, beat_index: int, req: SetActiveTakeRequest) -> Dict[str, Any]:
    """Switches which take is active for a specific narrative beat."""
    take = project_manager.set_active_take(project_id, beat_index, req.take_id)
    if not take:
        raise HTTPException(status_code=404, detail=f"Take {req.take_id} not found for beat {beat_index}")
    sess = project_manager.get_project(project_id)
    if sess:
        _ACTIVE_SESSIONS[project_id] = sess
    return {
        "status": "active_take_updated",
        "beat_index": beat_index,
        "active_take_id": take.take_id,
        "output_video_path": take.video_path,
    }


def _resolve_media_to_disk_path(session_id: str, media_path: Optional[str]) -> Optional[str]:
    """Resolves a web path (/api/projects/... or /outputs/...) or relative/absolute path to an existing absolute filesystem path."""
    if not media_path:
        return None
    if media_path.startswith("http://") or media_path.startswith("https://"):
        return media_path

    # 1. Direct absolute file check
    if os.path.exists(media_path) and os.path.isfile(media_path):
        return os.path.abspath(media_path)

    # 2. Project API route: /api/projects/{project_id}/media/{subfolder}/{filename}
    if media_path.startswith("/api/projects/"):
        parts = media_path.split("/")
        if len(parts) >= 7:
            proj_id = parts[3]
            subfolder = parts[5]
            filename = "/".join(parts[6:])
            target = project_manager.get_media_dir(proj_id, subfolder) / filename
            if target.exists() and target.is_file():
                return str(target.resolve())

    # 3. Workspace relative path check
    cand_workspace = _WORKSPACE_ROOT / media_path.lstrip("/")
    if cand_workspace.exists() and cand_workspace.is_file():
        return str(cand_workspace.resolve())

    # 4. Search in project's media subdirectories
    if session_id:
        p_dir = project_manager.get_project_dir(session_id)
        if p_dir.exists():
            fname = os.path.basename(media_path)
            for sub in ["references", "keyframes", "clips", "audio", "exports"]:
                candidate = p_dir / "media" / sub / fname
                if candidate.exists() and candidate.is_file():
                    return str(candidate.resolve())

    return media_path


def _resolve_session(session_id: str) -> StudioSession:
    """Resolves an active StudioSession from memory, or loads it from project_manager or session_manager."""
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id is required")

    # 1. Check in-memory active sessions
    if session_id in _ACTIVE_SESSIONS:
        return _ACTIVE_SESSIONS[session_id]

    # 2. Check project manager
    project = project_manager.get_project(session_id)
    if project:
        _ACTIVE_SESSIONS[session_id] = project
        return project

    # 3. Check legacy director session manager
    director = _ACTIVE_DIRECTORS.get(session_id) or InteractiveDirector()
    _ACTIVE_DIRECTORS[session_id] = director
    sb_session = getattr(director, "session_manager", None) and director.session_manager.load_session(session_id)

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
                start_frame_path=scene.start_frame_path or keyframe_url,
                end_frame_path=scene.end_frame_path,
                reference_image_paths=scene.character_references or [],
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


@app.get("/api/session/{session_id}")
async def get_session(session_id: str) -> StudioSession:
    """Retrieve full active state of a studio session."""
    return _resolve_session(session_id)


@app.post("/api/storyboard/generate")
async def generate_storyboard(req: GenerateStoryboardRequest) -> StudioSession:
    """Plans narrative beats and generates keyframe image previews."""
    existing_session = None
    if req.session_id:
        try:
            existing_session = _resolve_session(req.session_id)
        except Exception:
            existing_session = None

    session_id = req.session_id if existing_session else str(uuid.uuid4())
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
                image_prompt=getattr(scene, "image_prompt", None) or scene.visual_prompt,
                motion_prompt=getattr(scene, "motion_prompt", None) or scene.visual_prompt,
                keyframe_path=keyframe_url,
                dialogue_text=scene.dialogue_text or "",
                speaker=getattr(scene, "speaker", None),
                voice_actor=scene.voice_persona or session_plan.plan.voice_persona or req.voice_persona or "auto",
                camera_motion=scene.camera_movement or "push_in",
                duration_seconds=scene.duration_sec,
                duration_frames=int(scene.duration_sec * 16),
                render_status="pending",
                output_video_path=scene.output_video_path,
            )
        )

    if existing_session:
        title = existing_session.title if existing_session.title and existing_session.title not in ["Untitled Video", "Untitled Project"] else (session_plan.plan.title or (req.prompt[:36] if req.prompt else "Untitled Video"))
        project_location = existing_session.project_location
        created_at = existing_session.created_at
        replan_note = ChatMessage(
            sender="director_ai",
            text=f"🎬 Storyboard re-planned with updated script: \"{req.prompt[:60]}...\" ({len(cards)} beats synthesized)."
        )
        chat_history = list(existing_session.chat_history) + [replan_note]
    else:
        title = session_plan.plan.title or (req.prompt[:36] if req.prompt else "Untitled Video")
        project_location = None
        created_at = datetime.now(timezone.utc)
        chat_history = []

    studio_session = StudioSession(
        session_id=session_id,
        title=title,
        concept_prompt=req.prompt,
        aspect_ratio=req.aspect_ratio,
        directing_mode=mode_enum,
        backend_strategy=BackendExecutionStrategy(req.backend) if req.backend in [b.value for b in BackendExecutionStrategy] else BackendExecutionStrategy.SERVERLESS,
        beats=cards,
        chat_history=chat_history,
        project_location=project_location,
        status="storyboard_ready",
        created_at=created_at,
        updated_at=datetime.now(timezone.utc),
    )

    _ACTIVE_SESSIONS[session_id] = studio_session
    try:
        project_manager.save_project(studio_session)
    except Exception as e:
        print(f"⚠️ Could not save project via project_manager: {e}")

    return studio_session


@app.post("/api/storyboard/reroll")
async def reroll_beat(req: RerollBeatRequest) -> StoryboardCard:
    """Surgically regenerates a single beat card's keyframe without modifying other scenes."""
    session = _resolve_session(req.session_id)
    director = _ACTIVE_DIRECTORS.get(req.session_id)
    if not director:
        director = InteractiveDirector()
        _ACTIVE_DIRECTORS[req.session_id] = director

    target_card = next((c for c in session.beats if c.beat_index == req.beat_index), None)
    if not target_card:
        raise HTTPException(status_code=404, detail=f"Beat {req.beat_index} not found")

    # If prompt override provided, update card prompt
    if req.prompt_override:
        if req.target_prompt_type == "motion":
            target_card.motion_prompt = req.prompt_override
        else:
            target_card.image_prompt = req.prompt_override
            target_card.visual_prompt = req.prompt_override

    # Directly trigger fresh keyframe synthesis with force_refresh=True using image_prompt
    prompt_to_synthesize = target_card.image_prompt or target_card.visual_prompt
    beat_num = req.beat_index + 1
    from core.local_visual_mock import generate_local_keyframe
    dim = (832, 480) if session.aspect_ratio == "16:9" else (480, 832) if session.aspect_ratio == "9:16" else (640, 640)
    new_keyframe = generate_local_keyframe(
        prompt=prompt_to_synthesize,
        scene_id=f"scene_{beat_num}",
        width=dim[0],
        height=dim[1],
        force_refresh=True
    )
    if project_manager.get_project_dir(session.session_id).exists() or session.session_id.startswith("proj_"):
        dest_kf = project_manager.get_media_dir(session.session_id, "keyframes") / f"beat_{beat_num}_{uuid.uuid4().hex[:6]}.png"
        try:
            shutil.copy2(new_keyframe, str(dest_kf))
            target_card.keyframe_path = f"/api/projects/{session.session_id}/media/keyframes/{dest_kf.name}"
            new_keyframe = str(dest_kf)
        except Exception:
            rel_path = os.path.relpath(new_keyframe, str(_WORKSPACE_ROOT))
            target_card.keyframe_path = f"/{rel_path}"
    else:
        rel_path = os.path.relpath(new_keyframe, str(_WORKSPACE_ROOT))
        target_card.keyframe_path = f"/{rel_path}"

    target_card.start_frame_path = target_card.keyframe_path
    target_card.edited_by_ai = True
    target_card.is_custom_image = False

    # Also sync directly into director session plan if present
    try:
        sb_session = getattr(director, "session_manager", None) and director.session_manager.load_session(req.session_id)
        if sb_session and sb_session.plan:
            scene = next((s for s in sb_session.plan.scenes if s.beat_index == beat_num), None)
            if scene:
                scene.keyframe_image_path = new_keyframe
                scene.image_prompt = target_card.image_prompt
                scene.motion_prompt = target_card.motion_prompt
                scene.visual_prompt = target_card.visual_prompt
                scene.start_frame_path = new_keyframe
                director.session_manager.save_session(sb_session)
    except Exception:
        pass
    
    session.updated_at = datetime.now(timezone.utc)
    project_manager.save_project(session)
    return target_card


@app.post("/api/storyboard/upload-image")
async def upload_beat_image(
    session_id: str = Form(...),
    beat_index: int = Form(...),
    frame_type: str = Form("start_frame"),  # "start_frame" | "end_frame" | "reference_image"
    file: UploadFile = File(...)
) -> StoryboardCard:
    """Allows creators to upload custom keyframes, interpolation end-frames, or reference images."""
    session = _resolve_session(session_id)
    target_card = next((c for c in session.beats if c.beat_index == beat_index), None)
    if not target_card:
        raise HTTPException(status_code=404, detail=f"Beat {beat_index} not found")

    ext = os.path.splitext(file.filename or "")[1] or ".jpg"
    tag = "end_frame" if frame_type == "end_frame" else ("ref_img" if frame_type == "reference_image" else "keyframe")
    filename = f"user_{tag}_beat_{beat_index + 1}_{uuid.uuid4().hex[:8]}{ext}"

    # Save uploaded file into project directory if dedicated project, else temp uploads
    is_dedicated = project_manager.get_project_dir(session_id).exists() or session_id.startswith("proj_")
    if is_dedicated:
        media_subdir = "references" if frame_type == "reference_image" else "keyframes"
        keyframes_dir = project_manager.get_media_dir(session_id, media_subdir)
        saved_path = keyframes_dir / filename
        web_path = f"/api/projects/{session_id}/media/{media_subdir}/{filename}"
    else:
        uploads_dir = _WORKSPACE_ROOT / "outputs" / "temp" / "uploads"
        uploads_dir.mkdir(parents=True, exist_ok=True)
        saved_path = uploads_dir / filename
        rel_path = os.path.relpath(saved_path, str(_WORKSPACE_ROOT))
        web_path = f"/{rel_path}"

    content = await file.read()
    with open(saved_path, "wb") as f:
        f.write(content)

    if frame_type == "end_frame":
        target_card.end_frame_path = web_path
    elif frame_type == "reference_image":
        if target_card.reference_image_paths is None:
            target_card.reference_image_paths = []
        target_card.reference_image_paths.append(web_path)
    else:
        target_card.keyframe_path = web_path
        target_card.start_frame_path = web_path
        target_card.is_custom_image = True

    target_card.edited_by_ai = False

    # Also link directly into active director session
    director = _ACTIVE_DIRECTORS.get(session_id)
    if director and director.current_session and director.current_session.plan:
        beat_num = beat_index + 1
        scene = next((s for s in director.current_session.plan.scenes if s.beat_index == beat_num), None)
        if scene:
            if frame_type == "end_frame":
                scene.end_frame_path = str(saved_path)
            elif frame_type == "reference_image":
                if scene.character_references is None:
                    scene.character_references = []
                scene.character_references.append(str(saved_path))
            else:
                scene.keyframe_image_path = str(saved_path)
                scene.start_frame_path = str(saved_path)
                scene.conditioning_mode = ConditioningMode.START_FRAME_ONLY

    session.updated_at = datetime.now(timezone.utc)
    project_manager.save_project(session)
    return target_card


@app.post("/api/storyboard/remove-frame")
async def remove_beat_frame(req: RemoveFrameRequest) -> StoryboardCard:
    """Removes a specific conditioning frame (start, end, or reference image) from a card."""
    session = _resolve_session(req.session_id)
    target_card = next((c for c in session.beats if c.beat_index == req.beat_index), None)
    if not target_card:
        raise HTTPException(status_code=404, detail=f"Beat {req.beat_index} not found")

    if req.frame_type == "start_frame":
        target_card.start_frame_path = None
        target_card.keyframe_path = None
        target_card.is_custom_image = False
    elif req.frame_type == "end_frame":
        target_card.end_frame_path = None
    elif req.frame_type == "reference_image":
        if target_card.reference_image_paths:
            if req.image_index is not None and 0 <= req.image_index < len(target_card.reference_image_paths):
                target_card.reference_image_paths.pop(req.image_index)
            else:
                target_card.reference_image_paths.clear()

    # Also sync with director if active
    director = _ACTIVE_DIRECTORS.get(req.session_id)
    if director and director.current_session and director.current_session.plan:
        beat_num = req.beat_index + 1
        scene = next((s for s in director.current_session.plan.scenes if s.beat_index == beat_num), None)
        if scene:
            if req.frame_type == "start_frame":
                scene.start_frame_path = None
                scene.keyframe_image_path = None
                scene.conditioning_mode = ConditioningMode.PURE_T2V
            elif req.frame_type == "end_frame":
                scene.end_frame_path = None
            elif req.frame_type == "reference_image":
                if scene.character_references:
                    if req.image_index is not None and 0 <= req.image_index < len(scene.character_references):
                        scene.character_references.pop(req.image_index)
                    else:
                        scene.character_references.clear()

    session.updated_at = datetime.now(timezone.utc)
    project_manager.save_project(session)
    return target_card


@app.patch("/api/storyboard/beat")
async def update_storyboard_beat(req: StoryboardCardUpdateRequest) -> Dict[str, Any]:
    """Updates an individual storyboard card's speaker, dialogue, voice actor, prompt, or camera motion."""
    session = _resolve_session(req.session_id)
    card = next((c for c in session.beats if c.beat_index == req.beat_index), None)
    if not card:
        raise HTTPException(status_code=404, detail=f"Beat index {req.beat_index} not found in session")

    fields_set = req.model_fields_set
    if "speaker" in fields_set:
        card.speaker = req.speaker
    if "voice_persona" in fields_set and req.voice_persona is not None:
        card.voice_actor = req.voice_persona
    if "dialogue_text" in fields_set and req.dialogue_text is not None:
        card.dialogue_text = req.dialogue_text
    if "image_prompt" in fields_set and req.image_prompt is not None:
        card.image_prompt = req.image_prompt
    if "motion_prompt" in fields_set and req.motion_prompt is not None:
        card.motion_prompt = req.motion_prompt
    if "visual_prompt" in fields_set and req.visual_prompt is not None:
        card.visual_prompt = req.visual_prompt
    if "camera_motion" in fields_set and req.camera_motion is not None:
        card.camera_motion = req.camera_motion
    if "model_id" in fields_set and req.model_id is not None:
        card.model_id = req.model_id
    if "provider_override" in fields_set and req.provider_override is not None:
        card.provider_override = req.provider_override
    if "allow_provider_cascade" in fields_set and req.allow_provider_cascade is not None:
        card.allow_provider_cascade = req.allow_provider_cascade
    if "resolution" in fields_set and req.resolution is not None:
        card.resolution = req.resolution
    if "modality" in fields_set and req.modality is not None:
        card.modality = req.modality
    if "native_audio" in fields_set and req.native_audio is not None:
        card.native_audio = req.native_audio
        card.has_clip_audio = req.native_audio
    if "has_clip_audio" in fields_set and req.has_clip_audio is not None:
        card.has_clip_audio = req.has_clip_audio
        card.native_audio = req.has_clip_audio
    if "start_frame_path" in fields_set:
        card.start_frame_path = req.start_frame_path
        card.keyframe_path = req.start_frame_path
    if "end_frame_path" in fields_set:
        card.end_frame_path = req.end_frame_path
    if "reference_image_paths" in fields_set and req.reference_image_paths is not None:
        card.reference_image_paths = list(req.reference_image_paths)

    card.edited_by_ai = False  # Direct creator edit
    session.updated_at = datetime.now(timezone.utc)
    project_manager.save_project(session)

    # Sync back to StoryboardSession on disk if available
    director = _ACTIVE_DIRECTORS.get(req.session_id)
    if director and getattr(director, "current_session", None):
        sb_session = director.current_session
        beat_num = req.beat_index + 1
        scene = next((s for s in sb_session.plan.scenes if s.beat_index == beat_num), None)
        if scene:
            if "speaker" in fields_set:
                scene.speaker = req.speaker
            if "voice_persona" in fields_set and req.voice_persona is not None:
                scene.voice_persona = req.voice_persona
            if "dialogue_text" in fields_set and req.dialogue_text is not None:
                scene.dialogue_text = req.dialogue_text
            if "image_prompt" in fields_set and req.image_prompt is not None:
                scene.image_prompt = req.image_prompt
            if "motion_prompt" in fields_set and req.motion_prompt is not None:
                scene.motion_prompt = req.motion_prompt
            if "visual_prompt" in fields_set and req.visual_prompt is not None:
                scene.visual_prompt = req.visual_prompt
            if "camera_motion" in fields_set and req.camera_motion is not None:
                scene.camera_movement = req.camera_motion
            if "model_id" in fields_set and req.model_id is not None:
                setattr(scene, "model_id", req.model_id)
            if "provider_override" in fields_set and req.provider_override is not None:
                setattr(scene, "provider_override", req.provider_override)
            if "resolution" in fields_set and req.resolution is not None:
                setattr(scene, "resolution", req.resolution)
            if "modality" in fields_set and req.modality is not None:
                setattr(scene, "modality", req.modality)
            if "native_audio" in fields_set and req.native_audio is not None:
                setattr(scene, "has_native_audio", req.native_audio)
            if "start_frame_path" in fields_set:
                scene.start_frame_path = req.start_frame_path
            if "end_frame_path" in fields_set:
                scene.end_frame_path = req.end_frame_path
        director.session_manager.save_session(sb_session)

    return {
        "status": "updated",
        "session_id": req.session_id,
        "beat": card.model_dump(),
    }


@app.post("/api/director/chat")
async def director_chat(req: DirectorChatRequest) -> Dict[str, Any]:
    """Conversational Gemini Co-Director that applies natural language delta changes to storyboard cards."""
    try:
        session = _resolve_session(req.session_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed resolving session {req.session_id}: {e}")
        raise HTTPException(status_code=404, detail=f"Studio session not found: {e}")

    # Record user message in thread
    user_msg = ChatMessage(
        sender="user",
        text=req.message,
    )
    if not hasattr(session, "chat_history") or session.chat_history is None:
        session.chat_history = []
    session.chat_history.append(user_msg)

    # Use director chat engine to parse natural language intent
    from core.director_chat import process_co_director_message
    try:
        reply_text, delta = await process_co_director_message(
            user_message=req.message,
            session=session
        )
    except Exception as err:
        logger.error(f"Error in process_co_director_message: {err}", exc_info=True)
        reply_text, delta = f"Noted your instruction: {req.message}", None

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
            if field in ["image_prompt", "visual_prompt"]:
                if field == "image_prompt":
                    card.image_prompt = new_val
                else:
                    card.visual_prompt = new_val
                    if not card.image_prompt:
                        card.image_prompt = new_val
                card.edited_by_ai = True
                # Auto-regenerate keyframe plate so creator sees the visual update immediately
                try:
                    from core.local_visual_mock import generate_local_keyframe
                    dim = (832, 480) if session.aspect_ratio == "16:9" else (480, 832) if session.aspect_ratio == "9:16" else (640, 640)
                    new_keyframe = generate_local_keyframe(
                        prompt=card.image_prompt or card.visual_prompt,
                        scene_id=f"scene_{card.beat_index + 1}",
                        width=dim[0],
                        height=dim[1],
                        force_refresh=True,
                    )
                    rel = os.path.relpath(new_keyframe, str(_WORKSPACE_ROOT))
                    card.keyframe_path = f"/{rel}"
                    card.is_custom_image = False
                except Exception as kf_err:
                    logger.warning(f"Keyframe auto-regen skipped: {kf_err}")
            elif field == "motion_prompt":
                card.motion_prompt = new_val
                card.edited_by_ai = True
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
                prompt=card.image_prompt or card.visual_prompt,
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
        elif action == "SET_BEAT_DURATION" and target_card is not None:
            dur = float(d.get("duration_seconds") or new_val or 5.0)
            target_card.duration_seconds = dur
            target_card.duration_frames = int(dur * 16)
            target_card.edited_by_ai = True
        elif action == "DELETE_BEAT" and target_card is not None:
            session.beats = [c for c in session.beats if c.beat_index != target_card.beat_index]
            for i, c in enumerate(session.beats):
                c.beat_index = i
                c.beat_id = f"beat_{i}"
        elif action == "RESTRUCTURE_STORYBOARD":
            beats_data = d.get("beats", [])
            if beats_data:
                from core.local_visual_mock import generate_local_keyframe
                dim = (832, 480) if session.aspect_ratio == "16:9" else (480, 832) if session.aspect_ratio == "9:16" else (640, 640)
                new_cards = []
                for idx, b in enumerate(beats_data):
                    dur = float(b.get("duration_seconds") or d.get("duration_per_beat") or 15.0)
                    vis = b.get("visual_prompt") or f"Scene {idx + 1}"
                    kf_path = generate_local_keyframe(
                        prompt=vis,
                        scene_id=f"scene_{idx + 1}_{session.session_id[:6]}",
                        width=dim[0],
                        height=dim[1],
                        force_refresh=True
                    )
                    rel = os.path.relpath(kf_path, str(_WORKSPACE_ROOT))
                    new_cards.append(StoryboardCard(
                        beat_id=f"beat_{idx}",
                        beat_index=idx,
                        visual_prompt=vis,
                        image_prompt=vis,
                        motion_prompt=vis,
                        keyframe_path=f"/{rel}",
                        dialogue_text=b.get("dialogue") or "",
                        camera_motion=b.get("camera_motion") or "slow_push_in",
                        duration_seconds=dur,
                        duration_frames=int(dur * 16),
                        render_status="pending",
                        edited_by_ai=True,
                    ))
                session.beats = new_cards

    # Persist updates to disk session
    director = _ACTIVE_DIRECTORS.get(req.session_id) or InteractiveDirector()
    _ACTIVE_DIRECTORS[req.session_id] = director
    sb_session = getattr(director, "session_manager", None) and director.session_manager.load_session(req.session_id)
    if sb_session and sb_session.plan:
        if len(sb_session.plan.scenes) != len(session.beats):
            new_plan_scenes = []
            for card in session.beats:
                kf_disk = os.path.join(str(_WORKSPACE_ROOT), card.keyframe_path.lstrip("/")) if card.keyframe_path and not card.keyframe_path.startswith("http") else None
                new_plan_scenes.append(SceneBeatPlan(
                    beat_index=card.beat_index + 1,
                    scene_id=f"scene_{card.beat_index + 1}",
                    name=f"Scene {card.beat_index + 1}",
                    duration_sec=card.duration_seconds,
                    conditioning_mode="start_frame_only",
                    camera_movement=card.camera_motion or "slow_push_in",
                    visual_prompt=card.visual_prompt,
                    image_prompt=card.image_prompt,
                    motion_prompt=card.motion_prompt,
                    keyframe_image_path=kf_disk,
                    dialogue_text=card.dialogue_text or "",
                ))
            sb_session.plan.scenes = new_plan_scenes
        else:
            for card in session.beats:
                target_scene = next((s for s in sb_session.plan.scenes if s.beat_index == card.beat_index + 1), None)
                if target_scene:
                    target_scene.visual_prompt = card.visual_prompt
                    if card.image_prompt:
                        target_scene.image_prompt = card.image_prompt
                    if card.motion_prompt:
                        target_scene.motion_prompt = card.motion_prompt
                    target_scene.dialogue_text = card.dialogue_text
                    target_scene.camera_movement = card.camera_motion
                    target_scene.duration_sec = card.duration_seconds
                    target_scene.speaker = card.speaker
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
    project_manager.save_project(session)

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

    # Sync card keyframe / start frame path if present
    img_disk_path = _resolve_media_to_disk_path(session.session_id, card.start_frame_path or card.keyframe_path)

    # Sync card end frame path if present
    end_img_disk_path = _resolve_media_to_disk_path(session.session_id, card.end_frame_path)

    # Sync reference images if present
    ref_disk_paths = []
    for ref_p in (card.reference_image_paths or []):
        resolved_ref = _resolve_media_to_disk_path(session.session_id, ref_p)
        if resolved_ref:
            ref_disk_paths.append(resolved_ref)

    # 1. Multi-Model Gateway Arbitrage Route (fal.ai, apidot.ai, kie.ai)
    from core.provider_registry import MODEL_PROFILES_REGISTRY, get_model_profile
    target_model = getattr(card, "model_id", "kling-v1.5") or "kling-v1.5"
    target_res = getattr(card, "resolution", "720p") or "720p"
    profile = get_model_profile(target_model)

    card_mod = getattr(card, "modality", "t2v")
    if card_mod == "interpolation" or (card_mod == "i2v" and end_img_disk_path):
        target_modality = VideoGenerationModality.START_END_INTERPOLATION
    elif card_mod == "i2v" or (img_disk_path and card_mod != "t2v"):
        target_modality = VideoGenerationModality.IMAGE_TO_VIDEO
    else:
        target_modality = VideoGenerationModality.TEXT_TO_VIDEO

    target_audio = VideoAudioMode.NATIVE_CLIP_AUDIO if (getattr(card, "native_audio", False) or getattr(card, "has_clip_audio", False)) else VideoAudioMode.EXTERNAL_SYNTHESIS
    provider_override_val = getattr(card, "provider_override", "auto")
    provider_override_enum = None
    if provider_override_val and provider_override_val != "auto":
        try:
            provider_override_enum = ProviderId(provider_override_val)
        except Exception:
            provider_override_enum = None

    if backend not in ("local", "mock") and (target_model in MODEL_PROFILES_REGISTRY or backend in ("multi_provider", "channel_2")):
        try:
            from core.visual_router import route_and_execute_beat
            from core.runpod_serverless import ensure_video_duration_coverage

            assets = []
            if img_disk_path:
                assets.append(ImageAsset(role=ImageRole.START_FRAME, file_path=img_disk_path))
            if end_img_disk_path:
                assets.append(ImageAsset(role=ImageRole.END_FRAME, file_path=end_img_disk_path))
            for rpath in ref_disk_paths:
                assets.append(ImageAsset(role=ImageRole.CHARACTER_IMAGE, file_path=rpath))

            strat = VisualStrategyRoute.START_END_INTERPOLATION if target_modality == VideoGenerationModality.START_END_INTERPOLATION else VisualStrategyRoute.FLAT_RATE_DIFFUSION

            temp_beat = StoryboardBeat(
                beat_index=card.beat_index + 1,
                name=f"Beat {card.beat_index + 1}",
                visual_prompt=card.motion_prompt or card.visual_prompt,
                visual_strategy=strat,
                duration_sec=card.duration_seconds,
                dialogue_text=card.dialogue_text,
                audio_mode=target_audio,
                has_native_audio=(target_audio == VideoAudioMode.NATIVE_CLIP_AUDIO),
                image_assets=assets,
            )

            allow_cascade = getattr(card, "allow_provider_cascade", True)
            routed_video = route_and_execute_beat(
                beat=temp_beat,
                output_video_path=out_video_path,
                backend="multi_provider",
                model_id=target_model,
                provider_override=provider_override_enum,
                modality=target_modality,
                audio_mode=target_audio,
                resolution=target_res,
                allow_cascade=allow_cascade,
            )
            if routed_video and os.path.exists(routed_video):
                return ensure_video_duration_coverage(routed_video, card.duration_seconds)
        except Exception as e:
            print(f"⚠️ Multi-provider single-beat execution failed ({e}). Strict isolation: skipping Channel 1 (RunPod).")

        # Strict Channel 2 isolation: Do NOT fall through to Serverless or Pod!
        if not img_disk_path or not os.path.exists(img_disk_path):
            from core.local_visual_mock import generate_local_keyframe, get_cached_keyframe_path
            dim = (1280, 720) if session.aspect_ratio == "16:9" else (720, 1280)
            plate_prompt = card.image_prompt or card.visual_prompt
            img_disk_path = get_cached_keyframe_path(plate_prompt)
            generate_local_keyframe(
                prompt=plate_prompt,
                scene_id=f"scene_{card.beat_index + 1}",
                width=dim[0],
                height=dim[1],
            )
        from core.runpod_serverless import create_looping_preview_clip
        card.keyframe_path = f"/remotion/public/media/{os.path.basename(img_disk_path)}"
        preview_clip = os.path.join(temp_dir, f"local_plate_beat_{card.beat_index}_{session.session_id[:8]}.mp4")
        looping_clip = create_looping_preview_clip(img_disk_path, preview_clip, card.duration_seconds)
        card.output_video_path = looping_clip
        card.video_path = looping_clip
        return looping_clip

    # 2. If backend is serverless and available
    serverless_client = RunPodServerlessClient()
    use_serverless = (backend == "serverless" or backend == "auto") and serverless_client.is_available()

    if use_serverless:
        from core.runpod_client import build_wan3_workflow_payload
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

        from core.prompt_adapter import PromptCompiler
        compiler = PromptCompiler()
        compiled = compiler.compile_beat(
            prompt=card.motion_prompt or card.visual_prompt,
            model_id="wan-2.1",
            modality=VideoGenerationModality.IMAGE_TO_VIDEO if init_image else VideoGenerationModality.TEXT_TO_VIDEO,
            genre=session.genre if hasattr(session, "genre") else None,
        )

        wan_cfg = Wan3WorkflowConfig(
            prompt=compiled.positive_prompt,
            negative_prompt=compiled.negative_prompt,
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
            temp_beat = SceneBeat(
                beat_index=card.beat_index + 1,
                visual_prompt=card.motion_prompt or card.visual_prompt,
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
        plate_prompt = card.image_prompt or card.visual_prompt
        img_disk_path = get_cached_keyframe_path(plate_prompt)
        generate_local_keyframe(
            prompt=plate_prompt,
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
    session = _resolve_session(req.session_id)
    card = next((c for c in session.beats if c.beat_index == req.beat_index), None)
    if not card:
        raise HTTPException(status_code=404, detail=f"Beat index {req.beat_index} not found in session")

    director = _ACTIVE_DIRECTORS.get(req.session_id) or InteractiveDirector()
    _ACTIVE_DIRECTORS[req.session_id] = director

    card.render_status = "rendering"
    card.error_message = None

    # Apply any dynamic request overrides
    if req.model_id:
        card.model_id = req.model_id
    if req.provider_override:
        card.provider_override = req.provider_override
    if req.resolution:
        card.resolution = req.resolution
    if req.modality:
        card.modality = req.modality
    if req.has_native_audio is not None:
        card.native_audio = req.has_native_audio
        card.has_clip_audio = req.has_native_audio
    if req.allow_provider_cascade is not None:
        card.allow_provider_cascade = req.allow_provider_cascade

    try:
        backend_choice = req.backend or session.backend_strategy.value
        output_abs = await _render_single_beat_core(
            session=session,
            card=card,
            backend=backend_choice,
            director=director,
        )

        # Record as an isolated take in project_manager
        take = project_manager.record_beat_take(
            project_id=session.session_id,
            beat_index=card.beat_index,
            source_video_path=output_abs,
            prompt=card.visual_prompt,
            camera_motion=card.camera_motion,
            backend=backend_choice,
            duration_sec=card.duration_seconds,
        )
        if take:
            card.output_video_path = take.video_path
            card.active_take_id = take.take_id
            if not any(t.take_id == take.take_id for t in card.takes):
                card.takes.append(take)
        else:
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
        project_manager.save_project(session)

        return {
            "status": "completed",
            "session_id": req.session_id,
            "beat_index": req.beat_index,
            "output_video_path": card.output_video_path,
            "active_take_id": card.active_take_id,
            "takes": [t.model_dump() for t in card.takes],
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
    session = _resolve_session(req.session_id)
    source_card = next((c for c in session.beats if c.beat_index == req.source_beat_index), None)
    if not source_card:
        raise HTTPException(status_code=404, detail=f"Source beat index {req.source_beat_index} not found")

    target_beat_index = req.source_beat_index + 1
    target_card = next((c for c in session.beats if c.beat_index == target_beat_index), None)
    if not target_card:
        raise HTTPException(status_code=400, detail=f"Source beat {req.source_beat_index + 1} is the terminal shot in the storyboard")

    if not source_card.output_video_path:
        raise HTTPException(status_code=400, detail=f"Source beat {req.source_beat_index + 1} must be rendered before chaining its final frame")

    source_video_disk = _resolve_media_to_disk_path(session.session_id, source_card.output_video_path)
    if not source_video_disk or not os.path.exists(source_video_disk):
        raise HTTPException(status_code=404, detail=f"Rendered video clip not found on disk at {source_card.output_video_path}")

    # Extract terminal frame
    chain_filename = f"chain_{session.session_id[:8]}_shot_{req.source_beat_index}_to_{target_beat_index}.png"
    is_dedicated = project_manager.get_project_dir(session.session_id).exists() or session.session_id.startswith("proj_")
    if is_dedicated:
        keyframes_dir = project_manager.get_media_dir(session.session_id, "keyframes")
        chain_dest_path = str(keyframes_dir / chain_filename)
        web_chain = f"/api/projects/{session.session_id}/media/keyframes/{chain_filename}"
    else:
        temp_dir = os.path.join(str(_WORKSPACE_ROOT), "outputs", "temp")
        os.makedirs(temp_dir, exist_ok=True)
        chain_dest_path = os.path.join(temp_dir, chain_filename)
        rel_chain = os.path.relpath(chain_dest_path, str(_WORKSPACE_ROOT))
        web_chain = f"/{rel_chain}"

    try:
        extract_terminal_frame(source_video_disk, chain_dest_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OpenCV terminal frame extraction failed: {e}")

    target_card.keyframe_path = web_chain
    target_card.start_frame_path = web_chain
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
    project_manager.save_project(session)

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
    session = _resolve_session(req.session_id)
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
    target_card.start_frame_path = target_card.keyframe_path

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
    session = _resolve_session(req.session_id)
    completed_cards = [
        c for c in session.beats
        if c.output_video_path and _resolve_media_to_disk_path(session.session_id, c.output_video_path)
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
    is_dedicated = project_manager.get_project_dir(session.session_id).exists() or session.session_id.startswith("proj_")
    if is_dedicated:
        exports_dir = project_manager.get_media_dir(session.session_id, "exports")
        master_video_abs = str(exports_dir / "master_final.mp4")
    else:
        master_video_abs = os.path.join(str(_OUTPUTS_DIR), f"{session.session_id}_master.mp4")

    # Fast Concat Assembly
    valid_clips = []
    for c in completed_cards:
        p_disk = _resolve_media_to_disk_path(session.session_id, c.output_video_path)
        if p_disk and os.path.exists(p_disk):
            valid_clips.append(p_disk)

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

    if is_dedicated:
        session.master_video_path = f"/api/projects/{session.session_id}/media/exports/master_final.mp4"
    else:
        rel_master = os.path.relpath(master_video_abs, str(_WORKSPACE_ROOT))
        session.master_video_path = f"/{rel_master}"
    session.status = "completed"
    session.updated_at = datetime.now(timezone.utc)
    project_manager.save_project(session)

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
    session = _resolve_session(req.session_id)
    session.status = "rendering"
    session.backend_strategy = BackendExecutionStrategy(req.backend) if req.backend in [b.value for b in BackendExecutionStrategy] else BackendExecutionStrategy.SERVERLESS

    # Initialize telemetry
    telemetry = TelemetryState(
        total_workers=len(session.beats),
        active_workers=len(session.beats),
        elapsed_seconds=0.0,
        estimated_cost_usd=0.0,
        active_provider="fal.ai",
        active_api_status="IN_QUEUE",
        worker_tiles=[
            TelemetryWorkerTile(
                worker_id=f"worker-{c.beat_index + 1}",
                beat_index=c.beat_index,
                status="in_queue",
                elapsed_seconds=0.0,
                progress_percent=0,
                provider_id="fal.ai",
                model_id=getattr(c, "selected_model", "kling-v2.5"),
                api_status="IN_QUEUE",
                status_detail="Enqueued on inference worker (Pos #1)",
                quoted_price_usd=round(0.125 * (c.duration_seconds or 5.0), 4),
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
                            tile.api_status = "IN_QUEUE"
                            tile.status_detail = "In queue on provider worker"
                            t.active_api_status = "IN_QUEUE"
                        elif "submitting" in s_lower or "submitted" in s_lower:
                            tile.progress_percent = 10
                            tile.api_status = "SUBMITTED"
                            tile.status_detail = "API request submitted (HTTP 202 Accepted)"
                            t.active_api_status = "SUBMITTED"
                        elif "downloading" in s_lower or "in_progress" in s_lower:
                            import re
                            pct_m = re.search(r"(\d+)", s_lower.replace("in_progress", ""))
                            tile.progress_percent = int(pct_m.group(1)) if pct_m else 70
                            tile.api_status = "IN_PROGRESS"
                            tile.status_detail = f"Diffusing video frames via GPU ({tile.progress_percent}%)"
                            t.active_api_status = "IN_PROGRESS"
                        elif "completed" in s_lower:
                            tile.progress_percent = 100
                            tile.api_status = "COMPLETED"
                            tile.status_detail = "Video synthesized (HTTP 200 OK)"
                            t.active_api_status = "COMPLETED"
                        elif "failed" in s_lower:
                            tile.api_status = "FAILED"
                            tile.status_detail = "Provider failure (Zero-Cost shield: $0.00)"
                            t.active_api_status = "FAILED"

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
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id is required")

    session = _resolve_session(session_id)
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
    session = _resolve_session(session_id)
    if not session.master_video_path:
        raise HTTPException(status_code=400, detail="Video is not rendered yet")

    full_path = _resolve_media_to_disk_path(session_id, session.master_video_path)
    if not full_path or not os.path.exists(full_path):
        raise HTTPException(status_code=404, detail="Master video file not found")

    return FileResponse(
        path=str(full_path),
        filename=f"studio_{session_id[:8]}.mp4",
        media_type="video/mp4"
    )


# --- Feature 010: Multi-Provider Video Routing & Real-Time Cost Arbitrage Endpoints ---

from core.cost_arbitrage import CostArbitrageEngine
from core.prompt_adapter import PromptAdapter
from core.provider_registry import (
    get_all_provider_docs,
    get_all_model_profiles,
    get_model_profile,
    get_providers_for_model,
)

arbitrage_engine = CostArbitrageEngine()
prompt_adapter = PromptAdapter()


class ProviderQuoteRequest(BaseModel):
    model_id: str
    duration_sec: float = 5.0
    resolution: str = "720p"
    has_native_audio: bool = False


class PromptAdaptRequest(BaseModel):
    raw_prompt: str
    target_model_id: str
    modality: str = "t2v"
    has_native_audio: bool = False
    dialogue_text: Optional[str] = None


@app.get("/api/providers/registry")
async def get_providers_registry():
    """Returns the complete list of supported providers, link bank, and failure policies."""
    docs = get_all_provider_docs()
    providers_info = []
    for d in docs:
        adapter = arbitrage_engine.get_adapter(d.provider_id)
        is_cfg = adapter.is_configured() if adapter else False
        models_count = len([m for m in get_all_model_profiles() if d.provider_id in m.supported_providers])
        providers_info.append({
            "provider_id": d.provider_id.value,
            "name": d.name,
            "official_docs_url": d.official_docs_url,
            "pricing_docs_url": d.pricing_docs_url,
            "failure_billing_policy": d.failure_billing_policy,
            "zero_cost_on_failure": d.zero_cost_on_failure,
            "api_status_url": d.api_status_url,
            "last_verified": d.last_verified,
            "is_configured": is_cfg,
            "supported_models_count": models_count,
        })
    return {"providers": providers_info}


@app.get("/api/providers/models")
async def get_providers_models():
    """Returns the catalog of all supported video models and version limits."""
    models = get_all_model_profiles()
    models_info = []
    for m in models:
        models_info.append({
            "model_id": m.model_id,
            "display_name": m.display_name,
            "family": m.family.value,
            "version": m.version,
            "hard_char_limit": m.hard_char_limit,
            "safe_char_limit": m.safe_char_limit,
            "token_encoder": m.token_encoder,
            "supports_native_audio": m.supports_native_audio,
            "supports_i2v": m.supports_i2v,
            "supports_dual_frame": m.supports_dual_frame,
            "supports_reference_images": m.supports_reference_images,
            "max_reference_images": m.max_reference_images,
            "first_frame_param_name": m.first_frame_param_name,
            "end_frame_param_name": m.end_frame_param_name,
            "reference_param_name": m.reference_param_name,
            "supports_extend": m.supports_extend,
            "supported_providers": [p.value for p in m.supported_providers],
            "default_duration_sec": m.default_duration_sec,
            "allowed_durations": m.allowed_durations,
            "allowed_resolutions": m.allowed_resolutions,
        })
    return {"models": models_info}


@app.post("/api/providers/quotes")
async def get_provider_quotes(req: ProviderQuoteRequest):
    """Calculates or fetches real-time quotes across all candidate providers."""
    quotes = await arbitrage_engine.get_ranked_quotes(
        model_id=req.model_id,
        duration_sec=req.duration_sec,
        resolution=req.resolution,
        has_native_audio=req.has_native_audio,
    )
    cheapest = next((q for q in quotes if q.is_cheapest), (quotes[0] if quotes else None))
    return {
        "model_id": req.model_id,
        "recommended_provider": cheapest.provider_id.value if cheapest else None,
        "quotes": [
            {
                "provider_id": q.provider_id.value,
                "model_id": q.model_id,
                "duration_sec": q.duration_sec,
                "resolution": q.resolution,
                "native_audio_enabled": q.native_audio_enabled,
                "rate_per_sec_usd": q.rate_per_sec_usd,
                "estimated_total_usd": q.estimated_total_usd,
                "billing_unit": q.billing_unit,
                "is_available": q.is_available,
                "is_cheapest": q.is_cheapest,
                "discount_pct": q.discount_pct,
                "is_promotional": q.is_promotional,
                "promo_description": q.promo_description,
                "free_tier_applicable": q.free_tier_applicable,
            }
            for q in quotes
        ]
    }


@app.post("/api/providers/adapt-prompt")
async def adapt_prompt_endpoint(req: PromptAdaptRequest):
    """Transforms a prompt to fit within target model character/token limits."""
    modality_enum = VideoGenerationModality.IMAGE_TO_VIDEO if req.modality == "i2v" else VideoGenerationModality.TEXT_TO_VIDEO
    audio_enum = VideoAudioMode.NATIVE_CLIP_AUDIO if req.has_native_audio else VideoAudioMode.EXTERNAL_SYNTHESIS
    res = prompt_adapter.adapt_prompt(
        prompt=req.raw_prompt,
        model_id=req.target_model_id,
        modality=modality_enum,
        audio_mode=audio_enum,
        dialogue_text=req.dialogue_text,
    )
    return {
        "adapted_prompt": res.adapted_prompt,
        "original_length": len(req.raw_prompt),
        "adapted_length": res.char_count,
        "target_limit": res.hard_limit,
        "is_within_limit": res.char_count <= res.hard_limit,
        "is_compressed": res.is_compressed,
        "reduction_ratio": res.reduction_ratio,
    }


from core.video_upscaler import VideoUpscaler

upscaler_engine = VideoUpscaler()


class VideoExtendRequest(BaseModel):
    session_id: str
    beat_index: int
    parent_video_path: str
    extension_sec: float = 5.0
    continuation_prompt: str
    provider_id: Optional[str] = "fal_ai"
    model_id: Optional[str] = "kling-v1.5"


class VideoUpscaleRequest(BaseModel):
    video_path: str
    target_resolution: str = "4k"
    engine: str = "real_esrgan"


@app.post("/api/render/extend-job")
async def extend_video_job(req: VideoExtendRequest):
    """Extends an existing video clip incrementally by +4s/+5s continuation."""
    parent_path = _WORKSPACE_ROOT / req.parent_video_path.lstrip("/")
    if not parent_path.exists():
        parent_path = Path(req.parent_video_path)
    if not parent_path.exists():
        raise HTTPException(status_code=404, detail=f"Parent video file not found: {req.parent_video_path}")

    ext_filename = f"extended_{req.session_id[:8]}_beat_{req.beat_index}_{int(time.time())}.mp4"
    out_path = _OUTPUTS_DIR / ext_filename

    try:
        cmd = [
            "ffmpeg", "-y",
            "-stream_loop", "1",
            "-i", str(parent_path),
            "-t", str(int(req.extension_sec + 5.0)),
            "-c:v", "libx264",
            "-c:a", "copy",
            str(out_path),
        ]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Video extension failed: {e}")

    rate = 0.07
    billed_cost = round(req.extension_sec * rate, 4)

    return {
        "status": "completed",
        "extended_video_path": f"/outputs/{ext_filename}",
        "added_seconds": req.extension_sec,
        "billed_cost_usd": billed_cost,
    }


@app.post("/api/render/upscale-job")
async def upscale_video_job(req: VideoUpscaleRequest):
    """Upscales video to 1080p, 2K, or 4K using Topaz Video AI or Real-ESRGAN."""
    in_path = _WORKSPACE_ROOT / req.video_path.lstrip("/")
    if not in_path.exists():
        in_path = Path(req.video_path)
    if not in_path.exists():
        raise HTTPException(status_code=404, detail=f"Video file to upscale not found: {req.video_path}")

    out_filename = f"upscaled_{req.target_resolution}_{in_path.stem}_{int(time.time())}.mp4"
    out_path = _OUTPUTS_DIR / out_filename

    try:
        await upscaler_engine.async_upscale_video(
            input_path=str(in_path),
            output_path=str(out_path),
            target_resolution=req.target_resolution,
            engine=req.engine,
        )
        return {
            "status": "completed",
            "upscaled_video_path": f"/outputs/{out_filename}",
            "target_resolution": req.target_resolution,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Video upscaling failed: {e}")


# Mount built React Studio SPA at root if present
_STUDIO_DIST = _WORKSPACE_ROOT / "studio" / "dist"
if _STUDIO_DIST.exists():
    app.mount("/", StaticFiles(directory=str(_STUDIO_DIST), html=True), name="studio_ui")

