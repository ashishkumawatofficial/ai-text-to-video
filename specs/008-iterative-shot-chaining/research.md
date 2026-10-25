# Phase 0 Research: Iterative Shot Chaining & Single-Beat Rendering in Pro Director

**Feature**: `008-iterative-shot-chaining`  
**Date**: 2026-10-25  
**Spec**: [specs/008-iterative-shot-chaining/spec.md](file:///Users/ashishkumavat/Projects/ai-text-to-video/specs/008-iterative-shot-chaining/spec.md)

---

## 1. Single-Beat Video Synthesis Architecture

### Context
In existing versions, clicking "Approve & Synthesize Video" triggers parallel dispatch across all storyboard beats simultaneously (`dispatch_parallel_beats` or full sequential loop). In Pro Director mode, creators need the ability to render a single beat (e.g., Shot 1), inspect it, and verify motion and character behavior before investing GPU compute into subsequent shots.

### Decision
Implement a dedicated asynchronous endpoint `POST /api/render/beat` in [`core/server.py`](file:///Users/ashishkumavat/Projects/ai-text-to-video/core/server.py):
* Accepts `{ session_id: str, beat_index: int, backend?: str }`.
* Loads the current `StoryboardSession` and target `SceneBeat`.
* Routes the single beat through the selected inference backend:
  * **Serverless**: Uses `RunPodServerlessClient.run_job()` and `poll_job()` to diffuse the single beat on an isolated cloud worker.
  * **Pod**: Uses existing `route_and_execute_beat()` targeting `RUNPOD_COMFY_URL`.
  * **Local Mock**: Generates a fast 2.5D Ken Burns plate video using `ensure_video_duration_coverage()` for instant zero-cost testing.
* Sets `card.render_status = "rendering"` in telemetry/state, then `"completed"` upon finish.
* Returns the updated `StoryboardCard` with `output_video_path` and `render_status: "completed"`.

### Rationale
* Isolates compute spend: a creator testing an ambiguous camera prompt pays for only 1 video clip (~$0.008 on RunPod) instead of all 4 clips (~$0.035).
* Preserves existing full-batch rendering for 1-Click Auto mode while empowering Pro Director creators with granular control.

### Alternatives Considered
* *Full project re-render with skipped indices*: Too heavyweight; requires constructing dummy multi-scene project payloads when only 1 clip is desired.
* *Client-side simulated video*: Defeats the purpose of verifying actual AI video diffusion motion.

---

## 2. Terminal Frame Extraction and Continuity Chaining

### Context
When Shot 1 renders to MP4, the final frame (Frame -1) represents the exact spatial and temporal state where Shot 1 concludes. To eliminate visual jump cuts, clothing resets, and face shifting in Shot 2, Shot 2 must use Shot 1's final frame as its `START_FRAME` visual anchor.

### Decision
Implement `POST /api/storyboard/chain-frame` in [`core/server.py`](file:///Users/ashishkumavat/Projects/ai-text-to-video/core/server.py):
* Accepts `{ session_id: str, source_beat_index: int }` (targeting `target_beat_index = source_beat_index + 1`).
* Uses [`extract_terminal_frame()`](file:///Users/ashishkumavat/Projects/ai-text-to-video/core/chain_manager.py#L10-L38) from `core/chain_manager.py` using OpenCV (`cv2.VideoCapture`) to extract Frame -1.
* Saves the extracted frame to `outputs/temp/chain_{session_id[:8]}_shot_{source}_to_{target}.png`.
* Updates the target beat in the session plan:
  * `target_scene.keyframe_image_path = extracted_path`
  * `target_scene.start_frame_path = extracted_path`
  * `target_scene.conditioning_mode = ConditioningMode.START_FRAME_ONLY` (or `CHAIN_FROM_PREVIOUS`)
* Updates the target card:
  * `target_card.keyframe_path = f"/{rel_path}"`
  * `target_card.is_chained = True`
  * `target_card.chained_from_beat = source_beat_index`
* Returns the updated `target_card` to the React canvas.

### Rationale
* OpenCV frame seeking (`total_frames - 1`) executes in < 80ms, delivering instant visual feedback on the canvas.
* Automatically updates the target card's keyframe preview in the studio UI, letting the creator visually confirm the exact handoff frame before clicking "Render Beat" on Shot 2.

### Alternatives Considered
* *FFmpeg CLI subprocess*: Slower startup time than native Python OpenCV bindings; OpenCV is already an existing production dependency in `.venv`.
* *Client-side HTML5 canvas capture*: Unreliable due to browser CORS/video decoding variations; server-side extraction guarantees bit-identical frames for the video diffusion model.

---

## 3. Fast Master Video Assembly from Pre-Rendered Clips

### Context
When all clips (or selected clips) are individually rendered, the creator needs to produce the final master video with character voices, background music, sound effects, and kinetic subtitles without re-rendering the video clips.

### Decision
Implement `POST /api/render/compile` in [`core/server.py`](file:///Users/ashishkumavat/Projects/ai-text-to-video/core/server.py):
* Inspects `session.beats` to verify which clips have valid `output_video_path`.
* Skips video diffusion completely for completed clips.
* Synthesizes audio tracks using [`synthesize_scene_dialogue`](file:///Users/ashishkumavat/Projects/ai-text-to-video/core/audio_engine.py#L320) and [`stitch_beat_audio_tracks`](file:///Users/ashishkumavat/Projects/ai-text-to-video/core/audio_engine.py#L355) if not already cached.
* Sequenced subtitle word tokens are mapped with global start/end timestamps.
* Calls [`render_project_to_video()`](file:///Users/ashishkumavat/Projects/ai-text-to-video/core/remotion_bridge.py) with the pre-diffused video paths, resulting in instant final Remotion composition in under 15 seconds.

### Rationale
* Separates video diffusion (slow, GPU-heavy) from audio/subtitle/remotion compositing (fast, CPU/Node-based).
* Compiles the master video in seconds because heavy video generation is already completed.

---

## 4. UI / UX State Synchronization in Studio Canvas

### Decision
* In [`studio/src/components/BeatCard.tsx`](file:///Users/ashishkumavat/Projects/ai-text-to-video/studio/src/components/BeatCard.tsx):
  * **Footer Action `▶ Render Beat`**: Available on every pending card in Pro Director mode. Triggers `POST /api/render/beat`.
  * **Footer Action `🔗 Chain to Shot K+1`**: Appears automatically once a card's clip status is `completed` (unless it is the final shot). Triggers `POST /api/storyboard/chain-frame`.
  * **Badge `🔗 Chained from Shot K`**: Displayed on the card header when `is_chained === true`.
  * **Inline Player**: Auto-plays the rendered clip in a loop when `output_video_path` exists.
* In [`studio/src/components/DirectorSidebar.tsx`](file:///Users/ashishkumavat/Projects/ai-text-to-video/studio/src/components/DirectorSidebar.tsx):
  * When in Pro Director mode, if any beats are rendered, provide a prominent `🎬 Compile Master Video` button alongside the existing full batch button.
