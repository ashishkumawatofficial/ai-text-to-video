"""Global pytest configuration and zero-waste test isolation.

Ensures that automated test suites:
1. Set TEST_MODE=1 so that pipelines and engines automatically use local/free tiers
   (e.g., Edge-TTS, procedural PIL keyframes, local video compositor).
2. Never burn paid cloud credits (Cloudflare neurons, Puter AI tokens, RunPod GPU seconds)
   during automated regression testing.
3. Completely isolate projects and storyboard sessions into pytest's temporary directories
   so tests never pollute the real user workspace or dashboard.
"""

import os
import shutil
from pathlib import Path
import pytest

# Ensure TEST_MODE is active across the entire test session
os.environ["TEST_MODE"] = "1"

_WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
_INITIAL_SESSION_FILES = set()
_INITIAL_PROJECT_DIRS = set()


def pytest_sessionstart(session):
    """Snapshot existing user session files and project directories so test artifacts can be purged."""
    global _INITIAL_SESSION_FILES, _INITIAL_PROJECT_DIRS
    sessions_dir = _WORKSPACE_ROOT / "outputs" / "temp" / "sessions"
    projects_dir = _WORKSPACE_ROOT / "outputs" / "projects"

    if sessions_dir.exists():
        _INITIAL_SESSION_FILES = set(sessions_dir.glob("*.json"))
    if projects_dir.exists():
        _INITIAL_PROJECT_DIRS = set(p for p in projects_dir.iterdir() if p.is_dir())


@pytest.fixture(autouse=True)
def enforce_zero_waste_test_environment(tmp_path, monkeypatch):
    """Enforce zero-waste execution and complete filesystem isolation across all pytest runs."""
    monkeypatch.setenv("TEST_MODE", "1")

    test_projects_dir = tmp_path / "test_projects"
    test_sessions_dir = tmp_path / "test_sessions"
    test_projects_dir.mkdir(parents=True, exist_ok=True)
    test_sessions_dir.mkdir(parents=True, exist_ok=True)

    from core import project_manager as pm_module
    from core import session_manager as sm_module
    from core import server as srv_module

    # Monkeypatch module-level directory constants
    monkeypatch.setattr(pm_module, "_PROJECTS_DIR", test_projects_dir)
    monkeypatch.setattr(pm_module, "_LEGACY_SESSIONS_DIR", test_sessions_dir)
    monkeypatch.setattr(sm_module, "DEFAULT_SESSIONS_DIR", str(test_sessions_dir))

    # Re-route active project_manager in FastAPI server to the test directories
    test_pm = pm_module.ProjectManager(projects_dir=test_projects_dir, legacy_sessions_dir=test_sessions_dir)
    monkeypatch.setattr(srv_module, "project_manager", test_pm)

    # Clear active server in-memory states between tests
    srv_module._ACTIVE_SESSIONS.clear()
    srv_module._ACTIVE_DIRECTORS.clear()

    yield

    # Clean up test directories immediately after each test finishes
    if test_projects_dir.exists():
        shutil.rmtree(test_projects_dir, ignore_errors=True)
    if test_sessions_dir.exists():
        shutil.rmtree(test_sessions_dir, ignore_errors=True)

    outputs_test_sessions = _WORKSPACE_ROOT / "outputs" / "temp" / "test_sessions"
    if outputs_test_sessions.exists():
        shutil.rmtree(outputs_test_sessions, ignore_errors=True)
    outputs_test_projects = _WORKSPACE_ROOT / "outputs" / "temp" / "test_projects"
    if outputs_test_projects.exists():
        shutil.rmtree(outputs_test_projects, ignore_errors=True)


def pytest_sessionfinish(session, exitstatus):
    """Hook invoked when the full test session finishes.
    Guarantees that all test session files, test directories, and temporary
    test artifacts are cleanly wiped from disk after tests complete.
    """
    temp_dir = _WORKSPACE_ROOT / "outputs" / "temp"
    sessions_dir = temp_dir / "sessions"
    projects_dir = _WORKSPACE_ROOT / "outputs" / "projects"

    # 1. Clean up dedicated test directories
    test_dirs = [
        temp_dir / "test_sessions",
        temp_dir / "test_projects",
        temp_dir / "test_run",
    ]
    for d in test_dirs:
        if d.exists():
            shutil.rmtree(d, ignore_errors=True)

    # 2. Delete any new session files created in outputs/temp/sessions/ during tests
    if sessions_dir.exists():
        current_session_files = set(sessions_dir.glob("*.json"))
        new_session_files = current_session_files - _INITIAL_SESSION_FILES
        for f in new_session_files:
            try:
                f.unlink()
            except OSError:
                pass

        # Also purge any files matching test patterns even if they were present
        for f in sessions_dir.glob("*.json"):
            if f.name.startswith("test") or "test-ses" in f.name:
                try:
                    f.unlink()
                except OSError:
                    pass

    # 3. Delete any new project dirs created in outputs/projects/ during tests
    if projects_dir.exists():
        current_project_dirs = set(p for p in projects_dir.iterdir() if p.is_dir())
        new_project_dirs = current_project_dirs - _INITIAL_PROJECT_DIRS
        for p in new_project_dirs:
            if "test" in p.name.lower() or p.name.startswith("sess_"):
                shutil.rmtree(p, ignore_errors=True)

    # 4. Clean up any leftover temporary files in outputs/temp/ created during tests
    if temp_dir.exists():
        for f in temp_dir.glob("*test*"):
            if f.is_file():
                try:
                    f.unlink()
                except OSError:
                    pass
        for f in temp_dir.glob("concat_*.txt"):
            try:
                f.unlink()
            except OSError:
                pass

