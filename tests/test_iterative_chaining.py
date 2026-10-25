"""Unit and Integration tests for Iterative Shot Chaining & Single-Beat Rendering."""

import os
import shutil
import tempfile
import numpy as np
import cv2
import pytest
from fastapi.testclient import TestClient

from core.server import app, _ACTIVE_SESSIONS, _ACTIVE_DIRECTORS
from core.models import (
    StudioSession,
    StoryboardCard,
    DirectingMode,
    BackendExecutionStrategy,
    StoryboardSession,
    DirectorMasterPlan,
    SceneBeatPlan,
)
from core.chain_manager import extract_terminal_frame
from core.interactive_director import InteractiveDirector


@pytest.fixture
def temp_workspace():
    test_dir = tempfile.mkdtemp(prefix="test_chaining_")
    yield test_dir
    shutil.rmtree(test_dir, ignore_errors=True)


def create_dummy_mp4(filepath: str, width: int = 320, height: int = 240, num_frames: int = 16) -> str:
    """Creates a small valid H.264 MP4 with distinct frame colors for testing."""
    os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(filepath, fourcc, 16.0, (width, height))
    for i in range(num_frames):
        # Frame 0 is black, last frame (num_frames-1) has a bright red square
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        if i == num_frames - 1:
            frame[:, :] = (0, 0, 255)  # Bright red BGR
        else:
            frame[:, :] = (i * 10, i * 10, i * 10)
        out.write(frame)
    out.release()
    return filepath


@pytest.fixture
def mock_session():
    session_id = "test-session-chaining-1234"
    cards = [
        StoryboardCard(
            beat_id="beat_0",
            beat_index=0,
            visual_prompt="Close up of a detective under neon rain",
            speaker="Detective",
            dialogue_text="It all started that night...",
            voice_actor="en-US-ChristopherNeural",
            camera_motion="push_in",
            duration_seconds=2.0,
            duration_frames=32,
            render_status="pending",
        ),
        StoryboardCard(
            beat_id="beat_1",
            beat_index=1,
            visual_prompt="Wide shot of the dimly lit alleyway",
            speaker="Narrator",
            dialogue_text="Shadows danced along the brick wall.",
            voice_actor="auto",
            camera_motion="pan_right",
            duration_seconds=2.0,
            duration_frames=32,
            render_status="pending",
        ),
        StoryboardCard(
            beat_id="beat_2",
            beat_index=2,
            visual_prompt="The detective picks up an old silver coin",
            speaker="Detective",
            dialogue_text="Clues don't lie.",
            voice_actor="en-US-ChristopherNeural",
            camera_motion="tilt_down",
            duration_seconds=2.0,
            duration_frames=32,
            render_status="pending",
        ),
    ]

    session = StudioSession(
        session_id=session_id,
        concept_prompt="Film noir mystery",
        aspect_ratio="16:9",
        directing_mode=DirectingMode.PRO,
        backend_strategy=BackendExecutionStrategy.SERVERLESS,
        beats=cards,
        status="storyboard_ready",
    )
    _ACTIVE_SESSIONS[session_id] = session

    # Also setup a mock InteractiveDirector session
    director = InteractiveDirector()
    scenes = [
        SceneBeatPlan(
            beat_index=1,
            visual_prompt=cards[0].visual_prompt,
            speaker=cards[0].speaker,
            dialogue_text=cards[0].dialogue_text,
            duration_sec=2.0,
            camera_movement=cards[0].camera_motion,
        ),
        SceneBeatPlan(
            beat_index=2,
            visual_prompt=cards[1].visual_prompt,
            speaker=cards[1].speaker,
            dialogue_text=cards[1].dialogue_text,
            duration_sec=2.0,
            camera_movement=cards[1].camera_motion,
        ),
        SceneBeatPlan(
            beat_index=3,
            visual_prompt=cards[2].visual_prompt,
            speaker=cards[2].speaker,
            dialogue_text=cards[2].dialogue_text,
            duration_sec=2.0,
            camera_movement=cards[2].camera_motion,
        ),
    ]
    sb_session = StoryboardSession(
        session_id=session_id,
        initial_prompt="Film noir",
        plan=DirectorMasterPlan(concept_prompt="Film noir", duration_total_sec=6.0, scenes=scenes),
    )
    director.current_session = sb_session
    _ACTIVE_DIRECTORS[session_id] = director

    return session


def test_opencv_terminal_frame_extraction(temp_workspace):
    """Verifies that extract_terminal_frame reads the exact final frame."""
    video_path = os.path.join(temp_workspace, "test_clip.mp4")
    create_dummy_mp4(video_path, num_frames=10)

    out_frame_path = os.path.join(temp_workspace, "tail_frame.png")
    extracted = extract_terminal_frame(video_path, out_frame_path)

    assert os.path.exists(extracted)
    img = cv2.imread(extracted)
    assert img is not None
    # Terminal frame should be bright red (BGR: 0, 0, 255)
    b, g, r = img[100, 100]
    assert r > 200 and b < 50 and g < 50


@pytest.mark.asyncio
async def test_render_single_beat_isolated(mock_session):
    """Verifies that POST /api/render/beat renders only the requested beat and leaves others pending."""
    client = TestClient(app)
    session_id = mock_session.session_id

    # Trigger single-beat render for beat 0 using local mock backend
    resp = client.post(
        "/api/render/beat",
        json={"session_id": session_id, "beat_index": 0, "backend": "local"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "completed"
    assert data["beat_index"] == 0
    assert data["output_video_path"] is not None

    # Verify session in memory
    session = _ACTIVE_SESSIONS[session_id]
    assert session.beats[0].render_status == "completed"
    assert session.beats[0].output_video_path == data["output_video_path"]

    # Verify other beats remain pending and untouched
    assert session.beats[1].render_status == "pending"
    assert session.beats[1].output_video_path is None
    assert session.beats[2].render_status == "pending"
    assert session.beats[2].output_video_path is None


@pytest.mark.asyncio
async def test_chain_frame_consecutive_shots(mock_session):
    """Verifies that POST /api/storyboard/chain-frame extracts Frame -1 and binds it as START_FRAME."""
    client = TestClient(app)
    session_id = mock_session.session_id

    # 1. Verify 400 when source beat is not yet rendered
    resp_fail = client.post(
        "/api/storyboard/chain-frame",
        json={"session_id": session_id, "source_beat_index": 0},
    )
    assert resp_fail.status_code == 400

    # 2. Render beat 0
    resp_render = client.post(
        "/api/render/beat",
        json={"session_id": session_id, "beat_index": 0, "backend": "local"},
    )
    assert resp_render.status_code == 200

    # 3. Chain beat 0 to beat 1
    resp_chain = client.post(
        "/api/storyboard/chain-frame",
        json={"session_id": session_id, "source_beat_index": 0},
    )
    assert resp_chain.status_code == 200
    chain_data = resp_chain.json()
    assert chain_data["status"] == "chained"
    assert chain_data["source_beat_index"] == 0
    assert chain_data["target_beat_index"] == 1
    assert os.path.exists(chain_data["chained_frame_path"].lstrip("/"))

    # 4. Verify target card state
    target_card = chain_data["target_card"]
    assert target_card["is_chained"] is True
    assert target_card["chained_from_beat"] == 0
    assert target_card["keyframe_path"] == chain_data["chained_frame_path"]


@pytest.mark.asyncio
async def test_unlink_chain_and_upstream_invalidation(mock_session):
    """Verifies unlinking reverts state, and re-rendering Shot 0 flags Shot 1 as out of sync."""
    client = TestClient(app)
    session_id = mock_session.session_id

    # 1. Render Beat 0 and Chain to Beat 1
    client.post("/api/render/beat", json={"session_id": session_id, "beat_index": 0, "backend": "local"})
    client.post("/api/storyboard/chain-frame", json={"session_id": session_id, "source_beat_index": 0})

    session = _ACTIVE_SESSIONS[session_id]
    assert session.beats[1].is_chained is True
    assert session.beats[1].chained_from_beat == 0

    # 2. Unlink Beat 1
    resp_unlink = client.post("/api/storyboard/unlink-chain", json={"session_id": session_id, "beat_index": 1})
    assert resp_unlink.status_code == 200
    unlink_data = resp_unlink.json()
    assert unlink_data["status"] == "unlinked"
    assert unlink_data["target_card"]["is_chained"] is False
    assert unlink_data["target_card"]["chained_from_beat"] is None
    assert session.beats[1].is_chained is False

    # 3. Chain Beat 0 to Beat 1 again
    client.post("/api/storyboard/chain-frame", json={"session_id": session_id, "source_beat_index": 0})
    assert session.beats[1].is_chained is True
    assert session.beats[1].chain_out_of_sync is False

    # 4. Re-render Beat 0: should flag downstream Beat 1 as chain_out_of_sync
    client.post("/api/render/beat", json={"session_id": session_id, "beat_index": 0, "backend": "local"})
    assert session.beats[1].chain_out_of_sync is True


@pytest.mark.asyncio
async def test_compile_master_from_prerendered_clips(mock_session):
    """Verifies that POST /api/render/compile assembles pre-rendered clips without re-running diffusion."""
    client = TestClient(app)
    session_id = mock_session.session_id

    # 1. Reject if no clips are rendered and allow_partial is false
    resp_empty = client.post("/api/render/compile", json={"session_id": session_id, "allow_partial": False})
    assert resp_empty.status_code == 400

    # 2. Render all 3 beats
    for idx in range(3):
        client.post("/api/render/beat", json={"session_id": session_id, "beat_index": idx, "backend": "local"})

    # 3. Trigger compilation
    resp_compile = client.post("/api/render/compile", json={"session_id": session_id, "allow_partial": False})
    assert resp_compile.status_code == 200
    comp_data = resp_compile.json()
    assert comp_data["status"] == "completed"
    assert comp_data["master_video_path"] is not None
    assert comp_data["duration_seconds"] > 0


@pytest.mark.asyncio
async def test_session_reload_persists_chaining_state(mock_session):
    """Verifies that reloading an evicted session from disk preserves chaining metadata."""
    client = TestClient(app)
    session_id = mock_session.session_id

    # 1. Render Beat 0 and Chain to Beat 1
    client.post("/api/render/beat", json={"session_id": session_id, "beat_index": 0, "backend": "local"})
    client.post("/api/storyboard/chain-frame", json={"session_id": session_id, "source_beat_index": 0})

    # 2. Evict in-memory session cache
    if session_id in _ACTIVE_SESSIONS:
        del _ACTIVE_SESSIONS[session_id]

    # 3. Fetch session to trigger disk restoration
    resp_get = client.get(f"/api/session/{session_id}")
    assert resp_get.status_code == 200
    restored = resp_get.json()

    # Beat 1 must still have is_chained == True and chained_from_beat == 0
    beat_1 = next(b for b in restored["beats"] if b["beat_index"] == 1)
    assert beat_1["is_chained"] is True
    assert beat_1["chained_from_beat"] == 0





