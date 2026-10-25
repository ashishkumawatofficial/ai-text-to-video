# Quickstart Validation Guide: Universal Multi-Genre Video Pipeline

**Feature Branch**: `001-universal-video-pipeline`  
**Date**: 2026-10-23  
**Status**: Ready  

---

## 1. Prerequisites & Environment Setup

### 1.1 Core Requirements
- **Python**: 3.11+ installed with virtual environment active.
- **Node.js**: v18+ or v20+ with `npm` installed.
- **FFmpeg**: 6.0+ installed and on system `PATH`.
- **RunPod Instance (Optional for local testing / Required for GPU diffusion)**:
  - NVIDIA GPU with 24GB+ VRAM (RTX 4090 or A100) running ComfyUI.
  - Environment variable: `RUNPOD_API_KEY` and `RUNPOD_COMFY_URL` (e.g. `http://xyz-8188.proxy.runpod.net`).

### 1.2 Installation Commands
```bash
# 1. Activate Python virtual environment and install core packages
source .venv/bin/activate
pip install -r requirements.txt  # pydantic edge-tts faster-whisper requests websockets pillow opencv-python

# 2. Install Remotion master compositor dependencies
cd remotion
npm install
cd ..
```

---

## 2. Validation Scenario 1: The Deterministic Riddle (Strategy 1 - $0.00 Cost)

Tests the zero-hallucination programmatic pipeline (6-glasses riddle with countdown timer and transparent arm reveal).

### Run Command:
```bash
python -m core.pipeline \
  --mode directed_studio \
  --manifest specs/001-universal-video-pipeline/examples/riddle_manifest.json \
  --output outputs/val_01_riddle.mp4
```

### Expected Outcomes:
- **Duration**: ~30 seconds (1080x1920, 30fps).
- **Scene 1 (0s–14s)**: Static 4K tabletop plate with 6 glasses; voiceover audio playing.
- **Scene 2 (14s–21s)**: 7-second SVG radial countdown timer overlay with tick sound effects.
- **Scene 3 (21s–30s)**: Transparent hand sprite lifts Glass 2, pours crystal-clear water into Glass 5, and returns. Zero wood grain shifting, 0% black fill.
- **Subtitles**: Kinetic yellow-glow words highlighted in real time matching voiceover syllables.

---

## 3. Validation Scenario 2: Directed Studio Story with Reference Images (Strategy 3)

Tests image-to-video motion generation with user-provided reference images for character and style locking.

### Run Command:
```bash
python -m core.pipeline \
  --mode directed_studio \
  --manifest specs/001-universal-video-pipeline/examples/story_studio_manifest.json \
  --output outputs/val_02_story.mp4
```

### Expected Outcomes:
- **Consistency**: The character's face, hair, and clothing in Scene 1 and Scene 2 match the provided `character_reference.png`.
- **Motion**: Fluid cinematic camera push-in and character emotional reaction rendered via RunPod ComfyUI I2V.
- **Compositing**: Automatic music ducking when character narrates; subtitles smoothly animated.

---

## 4. Validation Scenario 3: Tail-to-Head Frame Chaining (Clip Continuity)

Tests automated extraction of Frame -1 from Clip 1 and injection as Frame 0 into Clip 2.

### Run Command:
```bash
python -m core.pipeline \
  --mode test_chaining \
  --clip1-prompt "samurai unsheathing glowing sword" \
  --clip2-prompt "samurai lunging forward into camera strike" \
  --output outputs/val_03_chained_action.mp4
```

### Expected Outcomes:
- **Extraction**: `outputs/temp/clip_01_tail.png` is generated at the completion of Clip 1.
- **Injection**: Clip 2 begins with `clip_01_tail.png` as its initial latent frame.
- **Visual Result**: Transition between Clip 1 and Clip 2 exhibits zero jump cut; sword angle and character stance align seamlessly.

---

## 5. Quick Remotion Studio Preview (Live Interactive Editor)

To inspect the master composition, kinetic subtitle layout, or countdown dial in the browser:

```bash
cd remotion
npm run start
```
*Opens `http://localhost:3000` with live scrubbing, layer controls, and real-time audio playback.*
