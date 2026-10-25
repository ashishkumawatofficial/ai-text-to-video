# Quickstart & Validation Guide: Iterative Shot Chaining & Single-Beat Rendering

**Feature**: `008-iterative-shot-chaining`  
**Date**: 2026-10-25  
**Spec**: [specs/008-iterative-shot-chaining/spec.md](file:///Users/ashishkumavat/Projects/ai-text-to-video/specs/008-iterative-shot-chaining/spec.md)  
**Contracts**: [specs/008-iterative-shot-chaining/contracts/chaining_api.json](file:///Users/ashishkumavat/Projects/ai-text-to-video/specs/008-iterative-shot-chaining/contracts/chaining_api.json)  
**Data Model**: [specs/008-iterative-shot-chaining/data-model.md](file:///Users/ashishkumavat/Projects/ai-text-to-video/specs/008-iterative-shot-chaining/data-model.md)

---

## 1. Prerequisites & Setup

Ensure the Python virtual environment is activated and dependencies (FastAPI, OpenCV, PyTest) are available:

```bash
# Verify environment and dependencies
./.venv/bin/python -c "import cv2, fastapi, pydantic; print('All core dependencies present')"
```

Ensure the backend server is running (or test harness is used):
```bash
# Start backend server
./.venv/bin/python -m uvicorn core.server:app --port 8000 --reload
```

---

## 2. Validation Scenarios

### Scenario 1: Single-Beat Video Generation in Isolation (FR-001, FR-002, SC-001)

**Goal**: Render Beat 0 without triggering any other scene beats.

1. **Create a Test Storyboard Session**:
   ```bash
   curl -s -X POST http://localhost:8000/api/storyboard/generate \
     -H "Content-Type: application/json" \
     -d '{"prompt": "A courageous detective walks down a neon-lit rain alley", "aspect_ratio": "16:9", "directing_mode": "pro"}' \
     | jq '{session_id: .session_id, beats_count: (.beats | length)}'
   ```
   *Capture the returned `session_id`.*

2. **Render Only Beat 0**:
   ```bash
   curl -s -X POST http://localhost:8000/api/render/beat \
     -H "Content-Type: application/json" \
     -d '{"session_id": "<SESSION_ID>", "beat_index": 0, "backend": "local"}' \
     | jq '{status: .status, output_video: .output_video_path, beat_0_status: .beat.render_status}'
   ```

3. **Verify Isolated State**:
   ```bash
   curl -s http://localhost:8000/api/session/<SESSION_ID> \
     | jq '.beats[] | {beat_index: .beat_index, render_status: .render_status, output_video_path: .output_video_path}'
   ```
   **Expected Outcome**:
   - `beat_index: 0` has `render_status: "completed"` and a valid `output_video_path`.
   - `beat_index: 1`, `beat_index: 2` remain `render_status: "pending"` with `output_video_path: null`.

---

### Scenario 2: Terminal Frame Extraction & Consecutive Shot Chaining (FR-004, FR-005, FR-006, SC-002)

**Goal**: Extract Frame -1 from Shot 0 and bind it as Shot 1's starting visual anchor.

1. **Trigger Frame Chaining**:
   ```bash
   curl -s -X POST http://localhost:8000/api/storyboard/chain-frame \
     -H "Content-Type: application/json" \
     -d '{"session_id": "<SESSION_ID>", "source_beat_index": 0}' \
     | jq '{status: .status, source: .source_beat_index, target: .target_beat_index, chained_frame: .chained_frame_path, target_is_chained: .target_card.is_chained}'
   ```

2. **Verify Target Card & File Integrity**:
   - Verify extracted frame file exists on disk:
     ```bash
     ls -lh outputs/temp/chain_*
     ```
   - Verify `target_card.is_chained == true` and `target_card.chained_from_beat == 0`.
   - Verify `target_card.keyframe_path` matches the extracted frame path.

3. **Render Shot 1 with Chained Conditioning**:
   ```bash
   curl -s -X POST http://localhost:8000/api/render/beat \
     -H "Content-Type: application/json" \
     -d '{"session_id": "<SESSION_ID>", "beat_index": 1, "backend": "local"}' \
     | jq '{status: .status, beat_index: .beat_index, video: .output_video_path}'
   ```
   **Expected Outcome**:
   - Shot 1 successfully renders using Shot 0's terminal frame as its visual anchor.
   - Optical continuity between Shot 0 and Shot 1 is 100% consistent with zero visual jump cuts.

---

### Scenario 3: Selective Unlinking & Continuity Overrides (FR-007)

**Goal**: Creator unlinks Shot 1 to revert to a standalone shot with independent artwork.

1. **Trigger Unlink**:
   ```bash
   curl -s -X POST http://localhost:8000/api/storyboard/unlink-chain \
     -H "Content-Type: application/json" \
     -d '{"session_id": "<SESSION_ID>", "beat_index": 1}' \
     | jq '{status: .status, beat_index: .beat_index, is_chained: .target_card.is_chained, keyframe: .target_card.keyframe_path}'
   ```
   **Expected Outcome**:
   - `target_card.is_chained == false`.
   - `target_card.chained_from_beat == null`.
   - `keyframe_path` reverts to the independent generated keyframe plate.

---

### Scenario 4: Fast Master Video Timeline Compilation (FR-008, SC-004)

**Goal**: Stitch all individually approved clips into a master 1080p video with dialogue, SFX, and kinetic subtitles in < 15 seconds.

1. **Render Remaining Beats**:
   Ensure all beats have `render_status: "completed"`.
2. **Trigger Master Compilation**:
   ```bash
   time curl -s -X POST http://localhost:8000/api/render/compile \
     -H "Content-Type: application/json" \
     -d '{"session_id": "<SESSION_ID>"}' \
     | jq '{status: .status, master_video_path: .master_video_path, duration: .duration_seconds}'
   ```
   **Expected Outcome**:
   - HTTP 200 with `master_video_path` pointing to the assembled MP4.
   - Compilation completes in < 15 seconds because video diffusion steps are skipped.
   - Output video contains aligned character audio and kinetic subtitle overlays.

---

## 3. Automated Regression Tests

Run the dedicated test suite validating single-beat dispatch, OpenCV terminal frame seeking, and master compilation:

```bash
./.venv/bin/pytest tests/test_studio_backend.py -v -k "chain or beat"
```
