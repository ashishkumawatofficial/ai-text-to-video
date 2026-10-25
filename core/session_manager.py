"""Storyboard Session Manager for conversational review and delta invalidation."""

from __future__ import annotations
import os
import json
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from core.models import (
    StoryboardSession,
    DirectorMasterPlan,
    ApprovalStatus,
    SessionTurn,
    ReferenceAsset
)


def get_default_sessions_dir() -> str:
    if os.environ.get("TEST_MODE") == "1":
        path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "outputs", "temp", "test_sessions"))
    else:
        path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "outputs", "temp", "sessions"))
    os.makedirs(path, exist_ok=True)
    return path


DEFAULT_SESSIONS_DIR = get_default_sessions_dir()


class StoryboardSessionManager:
    """Manages file-persisted storyboard review sessions and delta modifications."""

    def __init__(self, sessions_dir: Optional[str] = None):
        self.sessions_dir = sessions_dir or get_default_sessions_dir()
        os.makedirs(self.sessions_dir, exist_ok=True)

    def _get_session_path(self, session_id: str) -> str:
        return os.path.join(self.sessions_dir, f"{session_id}.json")

    def create_session(
        self,
        initial_prompt: str,
        plan: DirectorMasterPlan,
        reference_assets: Optional[Dict[str, ReferenceAsset]] = None,
        session_id: Optional[str] = None
    ) -> StoryboardSession:
        """Initializes and persists a new storyboard review session."""
        session = StoryboardSession(
            session_id=session_id or f"sess_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{os.urandom(3).hex()}",
            initial_prompt=initial_prompt,
            plan=plan,
            reference_assets=reference_assets or {},
            approval_status=ApprovalStatus.PENDING_REVIEW
        )
        self.save_session(session)
        return session

    def load_session(self, session_id: str) -> Optional[StoryboardSession]:
        """Loads and parses an existing storyboard review session from disk."""
        path = self._get_session_path(session_id)
        if not os.path.exists(path):
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return StoryboardSession.model_validate(data)
        except Exception:
            return None

    def save_session(self, session: StoryboardSession) -> str:
        """Serializes and saves the active session state."""
        session.updated_at = datetime.now(timezone.utc).isoformat()
        path = self._get_session_path(session.session_id)
        with open(path, "w", encoding="utf-8") as f:
            f.write(session.model_dump_json(indent=2))
        return path

    def record_turn(
        self,
        session_id: str,
        user_message: str,
        modified_beats: List[int],
        summary_of_changes: str,
        updated_plan: Optional[DirectorMasterPlan] = None
    ) -> Optional[StoryboardSession]:
        """Appends a user interaction turn to the session history."""
        session = self.load_session(session_id)
        if not session:
            return None

        if updated_plan is not None:
            session.plan = updated_plan

        turn = SessionTurn(
            turn_index=len(session.history) + 1,
            user_message=user_message,
            modified_beats=modified_beats,
            summary_of_changes=summary_of_changes
        )
        session.history.append(turn)
        session.approval_status = ApprovalStatus.MODIFICATIONS_REQUESTED
        self.save_session(session)
        return session

    def set_approval_status(self, session_id: str, status: ApprovalStatus) -> Optional[StoryboardSession]:
        """Updates the approval status of a session."""
        session = self.load_session(session_id)
        if not session:
            return None
        session.approval_status = status
        self.save_session(session)
        return session

    def invalidate_beat_keyframe(self, session_id: str, beat_index: int) -> bool:
        """Surgically invalidates the cached keyframe image for a specific beat."""
        session = self.load_session(session_id)
        if not session:
            return False

        found = False
        for scene in session.plan.scenes:
            if scene.beat_index == beat_index:
                if scene.keyframe_image_path and os.path.exists(scene.keyframe_image_path):
                    try:
                        os.remove(scene.keyframe_image_path)
                    except OSError:
                        pass
                scene.keyframe_image_path = None
                found = True
                break

        if found:
            self.save_session(session)
        return found
