# Quickstart & Validation Guide: Wan 3.0, RunPod Diagnostics, and Local Visual Mock

**Feature**: `specs/002-wan3-runpod-preview`  
**Date**: 2026-10-23  
**Status**: Completed  

---

## Prerequisites

1. Activate your Python virtual environment:
   ```bash
   source .venv/bin/activate
   ```
2. Verify dependencies:
   ```bash
   pip list | grep -E "requests|pydantic|edge-tts"
   ```

---

## Validation Scenario 1: RunPod Health Diagnostic Check

Test connectivity to your local or remote RunPod ComfyUI instance:

```bash
# Default check (checks http://127.0.0.1:8188)
python -m core.cli health

# Or test remote RunPod proxy
RUNPOD_COMFY_URL="https://your-pod-8188.proxy.runpod.net" python -m core.cli health
```

**Expected Outcome**:
- If offline: Outputs a clean diagnostic report indicating unreachable status and troubleshooting advice (no crash or unhandled traceback).
- If online: Displays green health status, ping latency (e.g. `42ms`), GPU model (e.g. `NVIDIA RTX 4090`), VRAM free/total, and confirms whether Wan 3.0 or Wan 2.1 checkpoints are present.

---

## Validation Scenario 2: Local Visual Mock Storyboard Rendering (Zero GPU)

Render an illustrated narrative video directly on your Mac without an active GPU:

```bash
python -m core.cli render \
  --prompt "A clever cyber detective uncovers a secret data core in the rain" \
  --genre cinematic_story \
  --output outputs/my_story_illustrated.mp4
```

**Expected Outcome**:
1. Pipeline logs `🎨 Generating Local Visual Keyframe illustrations for scenes...`
2. Each scene displays an illustrated high-definition scene background (not a black box with text).
3. The camera exhibits smooth continuous 2.5D Ken Burns zoom and pan throughout each shot.
4. Total compilation finishes in under 30 seconds.

---

## Validation Scenario 3: Deterministic Riddle Visual Assets

Render the 6-glasses riddle with full visual puzzle assets:

```bash
python -m core.cli render \
  --manifest specs/001-universal-video-pipeline/examples/riddle_manifest.json \
  --output outputs/riddle_illustrated.mp4
```

**Expected Outcome**:
1. All 3 scenes display the crisp 6-glasses puzzle visual plate.
2. Scene 2 displays the ticking countdown dial.
3. Scene 3 highlights the solution move with clean graphics.

---

## Validation Scenario 4: Automated Test Suite

Run the full regression and unit test suite:

```bash
pytest tests/
```

**Expected Outcome**:
All tests pass cleanly.
