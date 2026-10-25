"""Project Workspace Manager for isolated project storage, legacy session discovery, and multi-take history."""

from __future__ import annotations

import os
import json
import shutil
import uuid
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from core.models import (
    StudioSession,
    StoryboardCard,
    RenderTake,
    ProjectSummary,
    DirectingMode,
    BackendExecutionStrategy,
    StoryboardSession,
)


_WORKSPACE_ROOT = Path(__file__).resolve().parent.parent


def get_default_projects_dir() -> Path:
    if os.environ.get("TEST_MODE") == "1":
        return _WORKSPACE_ROOT / "outputs" / "temp" / "test_projects"
    return _WORKSPACE_ROOT / "outputs" / "projects"


def get_default_legacy_sessions_dir() -> Path:
    if os.environ.get("TEST_MODE") == "1":
        return _WORKSPACE_ROOT / "outputs" / "temp" / "test_sessions"
    return _WORKSPACE_ROOT / "outputs" / "temp" / "sessions"


_PROJECTS_DIR = get_default_projects_dir()
_LEGACY_SESSIONS_DIR = get_default_legacy_sessions_dir()
_OUTPUTS_DIR = _WORKSPACE_ROOT / "outputs"


class ProjectManager:
    """Manages dedicated project workspaces, asset encapsulation, and multi-take history."""

    def __init__(
        self,
        projects_dir: Optional[Path] = None,
        legacy_sessions_dir: Optional[Path] = None,
    ):
        self.projects_dir = projects_dir or get_default_projects_dir()
        self.legacy_sessions_dir = legacy_sessions_dir or get_default_legacy_sessions_dir()
        self.projects_dir.mkdir(parents=True, exist_ok=True)
        self.legacy_sessions_dir.mkdir(parents=True, exist_ok=True)
        self.registry_file = self.projects_dir / "registry.json"

    def _load_registry(self) -> Dict[str, str]:
        if self.registry_file.exists():
            try:
                with open(self.registry_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def _save_registry(self, registry: Dict[str, str]):
        try:
            with open(self.registry_file, "w", encoding="utf-8") as f:
                json.dump(registry, f, indent=2)
        except Exception:
            pass

    def _register_custom_location(self, project_id: str, location_path: str):
        registry = self._load_registry()
        registry[project_id] = location_path
        self._save_registry(registry)

    def _unregister_custom_location(self, project_id: str):
        registry = self._load_registry()
        if project_id in registry:
            del registry[project_id]
            self._save_registry(registry)

    def get_project_dir(self, project_id: str) -> Path:
        """Returns the isolated workspace directory for a project (custom or default)."""
        registry = self._load_registry()
        if project_id in registry:
            return Path(registry[project_id])
        return self.projects_dir / project_id

    def get_media_dir(self, project_id: str, subfolder: str) -> Path:
        """Returns and provisions a specific media subfolder (keyframes, audio, clips, exports)."""
        media_path = self.get_project_dir(project_id) / "media" / subfolder
        media_path.mkdir(parents=True, exist_ok=True)
        return media_path

    def provision_project_workspace(self, project_id: str) -> Dict[str, Path]:
        """Provisions the full isolated directory structure for a project."""
        proj_dir = self.get_project_dir(project_id)
        proj_dir.mkdir(parents=True, exist_ok=True)
        
        dirs = {
            "root": proj_dir,
            "keyframes": self.get_media_dir(project_id, "keyframes"),
            "audio": self.get_media_dir(project_id, "audio"),
            "clips": self.get_media_dir(project_id, "clips"),
            "exports": self.get_media_dir(project_id, "exports"),
        }
        return dirs

    def create_project(
        self,
        title: str,
        prompt: str,
        aspect_ratio: str = "16:9",
        directing_mode: str = "pro",
        backend_strategy: str = "serverless",
        voice_persona: str = "auto",
        project_id: Optional[str] = None,
        custom_location: Optional[str] = None,
    ) -> StudioSession:
        """Initializes a new isolated project workspace and persists project.json."""
        pid = project_id or f"proj_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"

        if custom_location and custom_location.strip():
            raw_path = custom_location.strip()
            p = Path(raw_path).expanduser()
            if not p.is_absolute():
                p = (_WORKSPACE_ROOT / p).resolve()
            target_dir = p
            if (target_dir / "project.json").exists():
                try:
                    with open(target_dir / "project.json", "r", encoding="utf-8") as f:
                        existing_data = json.load(f)
                    if existing_data.get("session_id") != pid:
                        target_dir = target_dir / pid
                except Exception:
                    target_dir = target_dir / pid
            self._register_custom_location(pid, str(target_dir))

        self.provision_project_workspace(pid)
        resolved_proj_dir = self.get_project_dir(pid)

        clean_mode = DirectingMode.PRO if directing_mode == "pro" else DirectingMode.AUTO
        clean_backend = BackendExecutionStrategy.SERVERLESS
        if backend_strategy == "pod":
            clean_backend = BackendExecutionStrategy.POD
        elif backend_strategy == "local":
            clean_backend = BackendExecutionStrategy.LOCAL

        try:
            rel = resolved_proj_dir.relative_to(_WORKSPACE_ROOT)
            display_loc = str(rel)
        except Exception:
            display_loc = str(resolved_proj_dir)

        session = StudioSession(
            session_id=pid,
            title=title or (prompt[:40] if prompt else "Untitled Project"),
            concept_prompt=prompt,
            aspect_ratio=aspect_ratio,
            directing_mode=clean_mode,
            backend_strategy=clean_backend,
            beats=[],
            chat_history=[],
            project_location=display_loc,
            status="draft",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        self.save_project(session)
        return session

    def get_project(self, project_id: str) -> Optional[StudioSession]:
        """Loads a project state from outputs/projects/ or seamlessly from legacy sessions."""
        # 1. Check dedicated projects folder
        proj_file = self.get_project_dir(project_id) / "project.json"
        if proj_file.exists():
            try:
                with open(proj_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                return StudioSession.model_validate(data)
            except Exception:
                pass

        # 2. Check legacy session files
        legacy_file = self.legacy_sessions_dir / f"{project_id}.json"
        if legacy_file.exists():
            try:
                with open(legacy_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                # Check if it's already a StudioSession format
                if "beats" in data:
                    sess = StudioSession.model_validate(data)
                    return sess
                
                # Otherwise, adapt from StoryboardSession model
                sb_session = StoryboardSession.model_validate(data)
                return self._adapt_legacy_session(sb_session)
            except Exception:
                pass

        return None

    def save_project(self, session: StudioSession) -> Path:
        """Serializes and saves the project state to disk."""
        session.updated_at = datetime.now(timezone.utc)
        
        # Check if project has a dedicated directory or is legacy
        proj_dir = self.get_project_dir(session.session_id)
        if proj_dir.exists() or not (self.legacy_sessions_dir / f"{session.session_id}.json").exists():
            self.provision_project_workspace(session.session_id)
            target_path = proj_dir / "project.json"
        else:
            target_path = self.legacy_sessions_dir / f"{session.session_id}.json"

        with open(target_path, "w", encoding="utf-8") as f:
            f.write(session.model_dump_json(indent=2))
        return target_path

    def list_projects(self) -> List[ProjectSummary]:
        """Scans and returns all project summaries from both dedicated projects and legacy sessions."""
        summaries: Dict[str, ProjectSummary] = {}

        # 1. Scan dedicated project workspaces (outputs/projects/*)
        if self.projects_dir.exists():
            for p_dir in self.projects_dir.iterdir():
                if p_dir.is_dir():
                    p_file = p_dir / "project.json"
                    if p_file.exists():
                        try:
                            with open(p_file, "r", encoding="utf-8") as f:
                                data = json.load(f)
                            sess = StudioSession.model_validate(data)
                            summary = self._create_summary_from_studio_session(sess, is_legacy=False)
                            summaries[sess.session_id] = summary
                        except Exception:
                            continue

        # 1b. Scan registered custom workspaces
        registry = self._load_registry()
        for pid, custom_path_str in registry.items():
            if pid in summaries:
                continue
            custom_dir = Path(custom_path_str)
            p_file = custom_dir / "project.json"
            if p_file.exists():
                try:
                    with open(p_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    sess = StudioSession.model_validate(data)
                    summary = self._create_summary_from_studio_session(sess, is_legacy=False)
                    summaries[sess.session_id] = summary
                except Exception:
                    continue

        # 2. Scan legacy sessions (outputs/temp/sessions/*.json)
        if self.legacy_sessions_dir.exists():
            for s_file in self.legacy_sessions_dir.glob("*.json"):
                sess_id = s_file.stem
                if sess_id in summaries:
                    continue  # Dedicated project takes precedence

                try:
                    with open(s_file, "r", encoding="utf-8") as f:
                        data = json.load(f)

                    if "beats" in data:
                        sess = StudioSession.model_validate(data)
                        summary = self._create_summary_from_studio_session(sess, is_legacy=True)
                    else:
                        sb = StoryboardSession.model_validate(data)
                        summary = self._create_summary_from_legacy_sb(sb)

                    summaries[sess_id] = summary
                except Exception:
                    continue

        # Sort projects by updated_at descending
        sorted_list = sorted(
            summaries.values(),
            key=lambda x: x.updated_at or x.created_at or "",
            reverse=True,
        )
        return sorted_list

    def update_project_metadata(
        self,
        project_id: str,
        title: Optional[str] = None,
        prompt: Optional[str] = None,
    ) -> Optional[StudioSession]:
        """Updates project title or concept prompt."""
        session = self.get_project(project_id)
        if not session:
            return None

        if title is not None:
            session.title = title.strip()
        if prompt is not None:
            session.concept_prompt = prompt.strip()

        self.save_project(session)
        return session

    def delete_project(self, project_id: str) -> bool:
        """Permanently deletes a project workspace or legacy session file."""
        deleted = False

        # 1. Delete dedicated project folder if present
        proj_dir = self.get_project_dir(project_id)
        if proj_dir.exists():
            try:
                shutil.rmtree(proj_dir)
                deleted = True
            except OSError:
                pass

        # 1b. Unregister custom location if tracked in registry
        self._unregister_custom_location(project_id)

        # 2. Delete legacy session file if present
        legacy_file = self.legacy_sessions_dir / f"{project_id}.json"
        if legacy_file.exists():
            try:
                legacy_file.unlink()
                deleted = True
            except OSError:
                pass

        # 3. Clean up root master video if present
        master_file = _OUTPUTS_DIR / f"{project_id}_master.mp4"
        if master_file.exists():
            try:
                master_file.unlink()
            except OSError:
                pass

        return deleted

    def reveal_in_finder(self, project_id: str) -> bool:
        """Opens the project folder in the native file manager (macOS Finder, Windows Explorer, Linux xdg-open)."""
        import platform
        import subprocess

        proj_dir = self.get_project_dir(project_id)
        target_path: Path = proj_dir
        if not target_path.exists():
            legacy_file = self.legacy_sessions_dir / f"{project_id}.json"
            if legacy_file.exists():
                target_path = legacy_file.parent
            else:
                return False

        try:
            system = platform.system()
            if system == "Darwin":
                if target_path.is_file():
                    subprocess.run(["open", "-R", str(target_path)], check=True)
                else:
                    subprocess.run(["open", str(target_path)], check=True)
                return True
            elif system == "Windows":
                if target_path.is_file():
                    subprocess.run(["explorer", f"/select,{str(target_path)}"])
                else:
                    os.startfile(str(target_path))
                return True
            else:
                folder = target_path if target_path.is_dir() else target_path.parent
                subprocess.run(["xdg-open", str(folder)], check=True)
                return True
        except Exception as e:
            print(f"Error revealing project folder in file manager: {e}")
            return False

    def pick_directory_dialog(self) -> Optional[str]:
        """Opens a native OS folder picker dialog and returns the chosen absolute path."""
        import platform
        import subprocess

        system = platform.system()
        try:
            if system == "Darwin":
                cmd = [
                    "osascript",
                    "-e", 'try',
                    "-e", 'POSIX path of (choose folder with prompt "Select Project Storage Location")',
                    "-e", 'on error',
                    "-e", 'return ""',
                    "-e", 'end try',
                ]
                res = subprocess.run(cmd, capture_output=True, text=True)
                path = res.stdout.strip().rstrip("/")
                return path if path else None
            elif system == "Windows":
                ps_cmd = (
                    "[System.Reflection.Assembly]::LoadWithPartialName('System.windows.forms') | Out-Null; "
                    "$f = New-Object System.Windows.Forms.FolderBrowserDialog; "
                    "if ($f.ShowDialog() -eq 'OK') { $f.SelectedPath }"
                )
                res = subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], capture_output=True, text=True)
                path = res.stdout.strip()
                return path if path else None
            else:
                for tool in ["zenity --file-selection --directory", "kdialog --getexistingdirectory"]:
                    try:
                        parts = tool.split()
                        res = subprocess.run(parts, capture_output=True, text=True)
                        path = res.stdout.strip()
                        if path:
                            return path
                    except Exception:
                        pass
                return None
        except Exception as e:
            print(f"Error opening directory picker dialog: {e}")
            return None

    def duplicate_project(self, project_id: str) -> Optional[StudioSession]:
        """Clones an existing project with cloned beats and ' (Copy)' title."""
        source = self.get_project(project_id)
        if not source:
            return None

        new_pid = f"proj_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
        new_title = f"{source.title or source.concept_prompt[:30]} (Copy)"

        # Deep clone session state
        cloned_data = source.model_dump()
        cloned_data["session_id"] = new_pid
        cloned_data["title"] = new_title
        cloned_data["created_at"] = datetime.now(timezone.utc)
        cloned_data["updated_at"] = datetime.now(timezone.utc)

        new_session = StudioSession.model_validate(cloned_data)
        self.provision_project_workspace(new_pid)
        self.save_project(new_session)
        return new_session

    def record_beat_take(
        self,
        project_id: str,
        beat_index: int,
        source_video_path: str,
        prompt: str = "",
        camera_motion: str = "push_in",
        backend: str = "serverless",
        duration_sec: float = 3.0,
    ) -> Optional[RenderTake]:
        """Records a new render take for a beat, saving it to project clips and updating active take."""
        session = self.get_project(project_id)
        if not session:
            return None

        # Find matching beat card
        target_card: Optional[StoryboardCard] = None
        for card in session.beats:
            if card.beat_index == beat_index:
                target_card = card
                break

        if not target_card:
            return None

        take_index = len(target_card.takes) + 1
        short_id = uuid.uuid4().hex[:6]
        
        # Provision isolated clips directory
        clips_dir = self.get_media_dir(project_id, "clips")
        dest_filename = f"beat_{beat_index}_take_{take_index}_{short_id}.mp4"
        dest_path = clips_dir / dest_filename

        # Copy or move clip
        if os.path.exists(source_video_path):
            try:
                shutil.copy2(source_video_path, str(dest_path))
            except Exception:
                dest_path = Path(source_video_path)

        try:
            rel = dest_path.relative_to(_WORKSPACE_ROOT)
            relative_url = f"/{rel}"
        except Exception:
            relative_url = str(dest_path)
        if not dest_path.exists():
            # Fallback relative URL
            try:
                rel = os.path.relpath(str(source_video_path), str(_WORKSPACE_ROOT))
                relative_url = f"/{rel}"
            except Exception:
                relative_url = str(source_video_path)

        take = RenderTake(
            take_id=f"take_{take_index}_{short_id}",
            beat_index=beat_index,
            take_index=take_index,
            video_path=relative_url,
            prompt=prompt or target_card.visual_prompt,
            camera_motion=camera_motion or target_card.camera_motion,
            backend=backend,
            duration_sec=duration_sec or target_card.duration_seconds,
            created_at=datetime.now(timezone.utc).isoformat(),
        )

        target_card.takes.append(take)
        target_card.active_take_id = take.take_id
        target_card.output_video_path = take.video_path
        target_card.render_status = "completed"

        self.save_project(session)
        return take

    def set_active_take(
        self,
        project_id: str,
        beat_index: int,
        take_id: str,
    ) -> Optional[RenderTake]:
        """Switches which take is active for a scene beat."""
        session = self.get_project(project_id)
        if not session:
            return None

        target_card: Optional[StoryboardCard] = None
        for card in session.beats:
            if card.beat_index == beat_index:
                target_card = card
                break

        if not target_card:
            return None

        selected_take: Optional[RenderTake] = None
        for take in target_card.takes:
            if take.take_id == take_id:
                selected_take = take
                break

        if not selected_take:
            return None

        target_card.active_take_id = take_id
        target_card.output_video_path = selected_take.video_path
        self.save_project(session)
        return selected_take

    def _create_summary_from_studio_session(
        self,
        session: StudioSession,
        is_legacy: bool = False,
    ) -> ProjectSummary:
        """Constructs a ProjectSummary from an existing StudioSession."""
        total_sec = sum(b.duration_seconds for b in session.beats)
        completed = sum(1 for b in session.beats if b.render_status == "completed" or b.output_video_path)
        total_takes = sum(len(b.takes) for b in session.beats)

        # Thumbnail from beat 0
        thumb = None
        if session.beats and session.beats[0].keyframe_path:
            kf_path = session.beats[0].keyframe_path
            if kf_path.startswith("/api/projects/"):
                thumb = kf_path
            else:
                candidate = os.path.join(str(_WORKSPACE_ROOT), kf_path.lstrip("/"))
                if os.path.exists(candidate):
                    thumb = kf_path

        # Master video check
        master_vid = session.master_video_path
        if not master_vid:
            legacy_master = _OUTPUTS_DIR / f"{session.session_id}_master.mp4"
            if legacy_master.exists():
                master_vid = f"/outputs/{session.session_id}_master.mp4"

        # Determine title
        title = session.title or (session.concept_prompt[:40] if session.concept_prompt else "Untitled Video")

        loc = session.project_location
        if not loc:
            p_dir = self.get_project_dir(session.session_id)
            try:
                loc = str(p_dir.relative_to(_WORKSPACE_ROOT))
            except Exception:
                loc = str(p_dir)

        return ProjectSummary(
            project_id=session.session_id,
            title=title,
            concept_prompt=session.concept_prompt,
            aspect_ratio=session.aspect_ratio if session.aspect_ratio in ["16:9", "9:16", "1:1"] else "16:9",
            directing_mode=session.directing_mode.value if hasattr(session.directing_mode, "value") else str(session.directing_mode),
            status=session.status,
            total_duration_sec=round(total_sec, 1),
            beat_count=len(session.beats),
            completed_beats_count=completed,
            total_takes_count=total_takes,
            thumbnail_url=thumb,
            master_video_path=master_vid,
            project_location=loc,
            created_at=session.created_at.isoformat() if hasattr(session.created_at, "isoformat") else str(session.created_at),
            updated_at=session.updated_at.isoformat() if hasattr(session.updated_at, "isoformat") else str(session.updated_at),
            is_legacy=is_legacy,
        )

    def _create_summary_from_legacy_sb(self, sb: StoryboardSession) -> ProjectSummary:
        """Constructs a ProjectSummary from a legacy StoryboardSession."""
        scenes = sb.plan.scenes if sb.plan and sb.plan.scenes else []
        total_sec = sb.plan.total_duration_sec if sb.plan else sum(s.duration_sec for s in scenes)
        completed = sum(1 for s in scenes if s.output_video_path and os.path.exists(s.output_video_path))

        thumb = None
        if scenes and scenes[0].keyframe_image_path and os.path.exists(scenes[0].keyframe_image_path):
            rel = os.path.relpath(scenes[0].keyframe_image_path, str(_WORKSPACE_ROOT))
            thumb = f"/{rel}"

        legacy_master = _OUTPUTS_DIR / f"{sb.session_id}_master.mp4"
        master_vid = f"/outputs/{sb.session_id}_master.mp4" if legacy_master.exists() else None

        title = sb.plan.title if (sb.plan and sb.plan.title) else (sb.initial_prompt[:40] if sb.initial_prompt else "Legacy Storyboard")

        return ProjectSummary(
            project_id=sb.session_id,
            title=title,
            concept_prompt=sb.initial_prompt,
            aspect_ratio=sb.plan.aspect_ratio if (sb.plan and sb.plan.aspect_ratio in ["16:9", "9:16", "1:1"]) else "16:9",
            directing_mode="pro",
            status="completed" if completed == len(scenes) and len(scenes) > 0 else "draft",
            total_duration_sec=round(total_sec, 1),
            beat_count=len(scenes),
            completed_beats_count=completed,
            total_takes_count=completed,
            thumbnail_url=thumb,
            master_video_path=master_vid,
            project_location=f"outputs/temp/sessions/{sb.session_id}.json",
            created_at=sb.created_at,
            updated_at=sb.updated_at,
            is_legacy=True,
        )

    def _adapt_legacy_session(self, sb: StoryboardSession) -> StudioSession:
        """Converts a StoryboardSession into a full StudioSession."""
        beats: List[StoryboardCard] = []
        scenes = sb.plan.scenes if sb.plan and sb.plan.scenes else []
        for idx, scene in enumerate(scenes):
            keyframe_url = None
            if scene.keyframe_image_path and os.path.exists(scene.keyframe_image_path):
                rel = os.path.relpath(scene.keyframe_image_path, str(_WORKSPACE_ROOT))
                keyframe_url = f"/{rel}"

            video_url = None
            takes: List[RenderTake] = []
            if scene.output_video_path and os.path.exists(scene.output_video_path):
                rel = os.path.relpath(scene.output_video_path, str(_WORKSPACE_ROOT))
                video_url = f"/{rel}"
                takes.append(
                    RenderTake(
                        take_id=f"take_1_{scene.beat_index}",
                        beat_index=scene.beat_index,
                        take_index=1,
                        video_path=video_url,
                        prompt=scene.visual_prompt,
                        camera_motion=scene.camera_movement,
                        duration_sec=scene.duration_sec,
                    )
                )

            card = StoryboardCard(
                beat_index=scene.beat_index,
                image_prompt=getattr(scene, "image_prompt", None) or scene.visual_prompt,
                motion_prompt=getattr(scene, "motion_prompt", None) or scene.visual_prompt,
                visual_prompt=scene.visual_prompt,
                keyframe_path=keyframe_url,
                speaker=scene.speaker,
                dialogue_text=scene.dialogue_text or "",
                voice_actor=scene.voice_persona or "en-US-ChristopherNeural",
                camera_motion=scene.camera_movement or "push_in",
                duration_seconds=scene.duration_sec,
                duration_frames=int(scene.duration_sec * 16),
                render_status="completed" if video_url else "pending",
                output_video_path=video_url,
                active_take_id=takes[0].take_id if takes else None,
                takes=takes,
                is_chained=getattr(scene, "is_chained", False),
                chained_from_beat=getattr(scene, "chained_from_beat", None),
            )
            beats.append(card)

        legacy_master = _OUTPUTS_DIR / f"{sb.session_id}_master.mp4"
        master_path = f"/outputs/{sb.session_id}_master.mp4" if legacy_master.exists() else None

        title = sb.plan.title if (sb.plan and sb.plan.title) else (sb.initial_prompt[:40] if sb.initial_prompt else "Legacy Storyboard")

        return StudioSession(
            session_id=sb.session_id,
            title=title,
            concept_prompt=sb.initial_prompt,
            aspect_ratio=sb.plan.aspect_ratio if (sb.plan and sb.plan.aspect_ratio in ["16:9", "9:16", "1:1"]) else "16:9",
            directing_mode=DirectingMode.PRO,
            backend_strategy=BackendExecutionStrategy.SERVERLESS,
            beats=beats,
            chat_history=[],
            master_video_path=master_path,
            project_location=f"outputs/temp/sessions/{sb.session_id}.json",
            status="completed" if master_path else "draft",
        )
