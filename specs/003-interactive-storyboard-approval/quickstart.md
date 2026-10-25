# Quickstart & Validation Guide: Interactive Storyboard & Multi-Modal Director Engine

**Feature**: `003-interactive-storyboard-approval`  
**Date**: 2026-10-23  
**Status**: Ready

This guide outlines runnable scenarios to validate interactive storyboard framing, conversational modification, and multi-modal asset conditioning.

---

## Prerequisites

1. Ensure the Python virtual environment is active:
   ```bash
   source .venv/bin/activate
   ```
2. Ensure Remotion dependencies are installed:
   ```bash
   npm --prefix remotion install
   ```

---

## Scenario 1: Initial Prompt to Storyboard Plan & Approval Gate

**Objective**: Verify that submitting a prompt generates a full storyboard without automatically rendering video, pausing at the approval checkpoint.

```bash
python -m core.cli direct --prompt "A brave astronaut discovering an ancient crystal on Mars"
```

### Expected Output:
- Terminal prints formatted `🎬 Interactive Storyboard Preview`.
- Table displays Beat 1 (*"The Call"* / 3.5s) and Beat 2 (*"The Discovery"* / 4.0s).
- Visual keyframe files exist in `outputs/temp/`.
- Audio strategy indicates voiceover, music mood, and subtitle styling.
- Terminal pauses at interactive prompt:
  ```text
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  [A]pprove & Render Video | [M]odify Beat | [Q]uit > 
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ```
- **Zero MP4 files are rendered** until approved.

---

## Scenario 2: Conversational Delta Modification via REPL

**Objective**: Verify that natural language feedback updates only the targeted scene without discarding other beats.

1. In the interactive prompt from Scenario 1, enter:
   ```text
   modify 2 make the crystal glowing purple and remove the voiceover
   ```
2. Expected Behavior:
   - System confirms delta modification targeting Beat 2.
   - Beat 2's visual prompt updates with `"purple crystal"` and regenerates its keyframe image in `<3s`.
   - Beat 2's `dialogue_text` is set to null.
   - Beat 1's keyframe path and dialogue remain completely unchanged.
   - Refreshed storyboard table is displayed.

---

## Scenario 3: Approval and Master Video Synthesis

**Objective**: Verify that selecting `Approve` locks the plan and dispatches to the master video pipeline.

1. In the interactive prompt, enter:
   ```text
   approve
   ```
2. Expected Behavior:
   - Status changes to `APPROVED`.
   - Pipeline synthesizes audio and stages assets into `remotion/public/media/`.
   - Remotion renders master video into `outputs/final_video.mp4`.
   - Output video features the approved beats and camera motion.

---

## Scenario 4: Multi-Modal Ingestion & Autonomous Frame Conditioning

**Objective**: Verify that attaching character art binds character identity and assigns correct conditioning modes.

```bash
python -m core.cli direct \
  --prompt "Detective Ren corners an android in the rain. Action strike then arrest." \
  --character "detective_ren:assets/detective_scene1.jpg" \
  --auto-approve \
  --output outputs/detective_action.mp4
```

### Expected Behavior:
- Scene 1 is assigned `START_FRAME_ONLY` with `detective_scene1.jpg` bound.
- Scene 2 (whip pan cut) is autonomously classified as `HARD_CUT`.
- Scene 3 (continuous arrest) is autonomously classified as `CHAIN_FROM_PREVIOUS`.
- Master video compiles successfully.
