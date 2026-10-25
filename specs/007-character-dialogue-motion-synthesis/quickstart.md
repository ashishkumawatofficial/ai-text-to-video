# Quickstart Validation Guide: Multi-Character Dialogue & Video Motion Synthesis

**Feature**: `007-character-dialogue-motion-synthesis`  
**Date**: 2026-10-25  

This guide provides runnable scenarios to validate multi-character dialogue attribution, per-scene vocal synthesis, and smooth temporal video motion without shutter/strobe artifacts.

---

## 1. Prerequisites

1. Active Python virtual environment (`.venv/bin/activate`).
2. Valid API keys configured in `.env`:
   - `GEMINI_API_KEY` (for story planning & character identification)
   - `RUNPOD_API_KEY` & `RUNPOD_SERVERLESS_ENDPOINT_ID` (for Wan 2.1 GPU workers)
3. Local Web Studio servers running:
   - Backend: `python -m core.cli studio` (Port 8000)
   - Frontend: `npm run dev` in `studio/` (Port 5173)

---

## 2. Validation Scenarios

### Scenario A: Multi-Character Dialogue Attribution & Pacing Verification

**Goal**: Verify that the story writer identifies distinct character speakers, assigns personality vocal personas, and authors 4-part motion prompts.

```bash
# Execute CLI story generation with multi-character brief
.venv/bin/python -c "
from core.models import NarrativeBrief, VideoAspectRatio, NarrativeInputMode
from core.story_writer import StoryWriter

writer = StoryWriter()
brief = NarrativeBrief(
    prompt_or_text='4 cows sitting at a roadside tea stall laughing at a suit-wearing corporate cow walking past',
    aspect_ratio=VideoAspectRatio.WIDESCREEN_16_9,
    input_mode=NarrativeInputMode.PROMPT_EXPANSION
)
result = writer.generate_plan(brief)

print('=== Plan Title:', result.plan.title)
for scene in result.plan.scenes:
    print(f'Beat {scene.beat_index}:')
    print(f'  Speaker: {getattr(scene, \"speaker\", None)}')
    print(f'  Voice Persona: {scene.voice_persona}')
    print(f'  Dialogue: \"{scene.dialogue_text}\"')
    print(f'  Visual Prompt (Kinetics): {scene.visual_prompt[:90]}...')
"
```

**Expected Outcome**:
- Each scene beat has a non-null `speaker` (e.g. `"Tea Stall Cow #1"`, `"Suit Cow"`).
- Scene beats have distinct `voice_persona` assignments (e.g. `cartoon_animal`, `en-US-GuyNeural`, `en-US-DavisNeural`).
- `visual_prompt` describes subject action, interaction, and camera movement rather than static image aesthetics.

---

### Scenario B: Multi-Speaker Audio Synthesis & Subtitle Alignment

**Goal**: Verify that each scene's dialogue is synthesized with its assigned character voice and that word-level subtitle tokens are extracted without merging all dialogue into a monotone track.

```bash
# Run unit test for multi-speaker speech synthesis
.venv/bin/python -m pytest tests/unit/test_audio_engine.py -k "test_resolve_voice_persona or test_synthesize_speech"
```

**Expected Outcome**:
- Speech synthesis routes character personas to their distinct neural voices.
- Subtitle tracks contain accurate word-level milliseconds aligned with dialogue pacing.

---

### Scenario C: Video Diffusion Temporal Coherence (Zero Strobe / Shuttering)

**Goal**: Verify that the ComfyUI workflow uses temporal video latents (`EmptyHunyuanLatentVideo` / `WanImageToVideo`) and generates smooth optical flow across frames.

```bash
# Validate workflow structure and latent node schema
.venv/bin/python -c "
from core.runpod_client import build_wan3_workflow_payload
from core.models import Wan3WorkflowConfig

cfg = Wan3WorkflowConfig(
    prompt='The cow on the left sips tea calmly as steam rises. Camera pans right.',
    width=832,
    height=480,
    duration_frames=33,
    steps=12,
    reference_images=['outputs/temp/keyframe_de29c3dec08a.jpg']
)
payload = build_wan3_workflow_payload(cfg)

# Verify 3D video latent node is used instead of 2D EmptyLatentImage
latent_node = payload.get('6', {})
print('Latent Node Class:', latent_node.get('class_type'))
assert latent_node.get('class_type') != 'EmptyLatentImage', 'FAIL: EmptyLatentImage causes strobe flickering!'
print('SUCCESS: Temporal video latent node configured properly.')
"
```

**Expected Outcome**:
- `latent_node.class_type` is `EmptyHunyuanLatentVideo` or `WanImageToVideo`.
- `EmptyLatentImage` is not present in the temporal video generation chain.

---

### Scenario D: Web Studio End-to-End Visual Verification

**Goal**: Verify that Web Studio cards display the character speaker badge, allow changing character voice personas, and render the final video without terminal frame freeze.

1. Open `http://localhost:5173`.
2. Inspect any beat card: verify the **Speaker Name** badge (e.g. `[Cow 1]`) and **Voice Persona** dropdown are present.
3. Change a card's voice persona (e.g. from `Male Narrator` to `Cartoon Animal`).
4. Click **Approve & Synthesize Video**.
5. Observe telemetry tiles progress in real-time (`SUBMITTING` ➔ `IN_QUEUE` ➔ `DOWNLOADING` ➔ `COMPLETED`).
6. Play the completed video in the master preview:
   - Verify that characters speak with different voices.
   - Verify that video motion is smooth, fluid, and continuous without 16 fps image shuttering.
   - Verify that visual motion continues for the full duration of the spoken dialogue.
