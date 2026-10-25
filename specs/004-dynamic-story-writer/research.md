# Research & Technical Decisions: Dynamic AI Story Writer & Narrative Cascade

**Feature**: `specs/004-dynamic-story-writer`  
**Date**: 2026-10-23  
**Status**: Complete

---

## 1. LLM Client Gateway & Provider Abstraction

### Context
The story writing engine needs to support dynamic narrative creation using the latest AI models when API credentials are present, while remaining completely resilient and operational when offline.

### Decision
Implement a unified `StoryWriterGateway` in `core/story_writer.py` supporting:
1. **Google Gemini Client**: Using the modern `google-genai` SDK (`client = genai.Client()`).
2. **OpenAI Compatible Client**: Using `openai` SDK or direct HTTP client when `OPENAI_API_KEY` is configured.
3. **Deterministic Heuristic Engine**: Using our existing rule-based narrative synthesizer when no API keys are present or all network attempts fail.

### Rationale
- Decouples narrative generation from specific proprietary vendor lock-in.
- Supports pure zero-dependency local operation for developers without API keys.
- Ensures native JSON schema enforcement across providers.

### Alternatives Considered
- *LangChain / LlamaIndex*: Rejected to avoid bloated dependency overhead, slow startup latency, and unpredictable schema translation bugs.
- *OpenAI-only*: Rejected because Gemini provides 1M+ token context windows for long scripts and native Pydantic schema validation at high speed.

---

## 2. Multi-Tier Model Priority Cascade

### Context
Cloud LLMs encounter rate limits (`HTTP 429 Too Many Requests`), transient outages, account tier restrictions, and model deprecation. Relying on a single hardcoded model string causes production failures.

### Decision
Implement an ordered model cascade with programmatic auto-discovery:
1. **Tier 1 (Latest Frontier)**: Primary attempt with the newest available generation (`gemini-2.5-flash`, `gemini-2.5-pro`, or `gpt-4o`).
2. **Tier 2 (High-Throughput Stable)**: Rapid fallback (`gemini-1.5-flash`, `gemini-1.5-pro`, `gpt-4o-mini`) executed on any 429/404/503 exception in `<500ms`.
3. **Tier 3 (Lightweight Fallback)**: Budget tier (`gemini-1.5-flash-8b`, `gpt-3.5-turbo`).
4. **Tier 4 (Offline Rule Engine)**: Executed when no API keys are present, network is disconnected, or all cloud tiers fail.

### Rationale
- Guaranteed 100% pipeline uptime and 0% unhandled crashes.
- Automatic utilization of the newest models when account tiers permit.

---

## 3. Structured Output & Pydantic Schema Enforcement

### Context
Downstream video composition in Remotion requires strict scene beat definitions (`duration_sec`, `camera_movement`, `visual_prompt`, `dialogue_text`, `sound_effects`). Markdown parsing or unformatted text frequently introduces syntax errors.

### Decision
Use provider-native Structured JSON Output mode:
- For Gemini: `response_mime_type="application/json"` with `response_schema=DirectorMasterPlan`.
- For OpenAI: `response_format={"type": "json_object"}`.
- All outputs are immediately validated via `DirectorMasterPlan.model_validate_json()`. If validation fails, the cascade catches the error and queries the next tier.

### Rationale
- 100% elimination of markdown regex parsing errors.
- Type safety and schema synchronization across Python models and Remotion TypeScript contracts.

---

## 4. Script Segmentation & Dialogue Preservation

### Context
When users paste an existing multi-paragraph script or educational lesson (User Story 2), the engine must partition the text into vertical 9:16 beats without losing original dialogue lines.

### Decision
Provide system instructions that explicitly differentiate:
1. **Spoken Dialogue**: Exact preservation of the user's spoken text assigned to `dialogue_text` across sequential beats.
2. **Visual Staging**: Transforming prose and descriptive sentences into cinematic visual diffusion prompts tailored to the target aspect ratio with camera motion directions.
3. **Timing Constraints**: Allocating scene durations between 3.0s and 8.0s per beat (total video duration between 10s and 60s) to match standard short/medium video reading speeds.

---

## 5. Multi-Aspect Ratio Framing & Dynamic Canvas Adaptation

### Context
Video creators produce content across platforms with contrasting screen geometries:
- TikTok / Reels / Shorts: `9:16` vertical (`1080x1920`)
- YouTube / TV / Desktop: `16:9` widescreen (`1920x1080`)
- Instagram Feed: `1:1` square (`1080x1080`)
- Instagram Portrait: `4:5` vertical feed (`1080x1350`)
If a widescreen composition is rendered onto a 9:16 canvas, subjects are either cropped inappropriately or bordered with black pillarboxes.

### Decision
1. **Prompt Phrasing Adaptation**: Inject composition keywords into visual diffusion prompts based on the aspect ratio:
   - `9:16`: `"vertical 9:16 composition, mobile portrait framing, tall perspective, centered character blocking"`
   - `16:9`: `"cinematic widescreen 16:9 composition, panoramic landscape framing, anamorphic perspective, rule-of-thirds horizontal blocking"`
   - `1:1`: `"square 1:1 balanced composition, centered subject framing, symmetrical perspective"`
   - `4:5`: `"social portrait 4:5 composition, vertical feed framing"`
2. **Canvas Dimension Transmission**: Pass target `width` and `height` in `DirectorMasterPlan` and `VideoProject`. Remotion's `calculateMetadata` already dynamically adopts `props.width` and `props.height`, ensuring the rendered MP4 perfectly matches the canvas dimensions without pillarboxes or stretching.
3. **Diffusion Keyframe Resolution**: ComfyUI / visual generation stage receives the exact resolution `(width, height)` to synthesize keyframes natively at the selected aspect ratio.

### Rationale
- Delivers first-class multi-platform support with zero visual distortion.
- Preserves creative intent across widescreen filmic storytelling and mobile-first vertical reels.

