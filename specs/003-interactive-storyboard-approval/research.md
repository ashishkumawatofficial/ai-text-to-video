# Research & Architectural Decisions: Interactive Storyboard & Multi-Modal Director Engine

**Feature**: `003-interactive-storyboard-approval`  
**Date**: 2026-10-23  
**Status**: Completed

---

## 1. Conversational Storyboard Session & Delta Editing Architecture

### Context
When a user requests modifications (e.g., *"Make Scene 2 crystal glow red and remove the voiceover"*), the system must not discard the entire project or regenerate unaffected scenes. Unaffected visual keyframes, audio assets, and parameters must be preserved while applying targeted delta mutations.

### Decision
Implement `StoryboardSessionManager` with an in-memory & file-persisted JSON state store (`outputs/temp/sessions/<session_id>.json`).
- Each session contains:
  - `session_id`: Unique identifier (UUID).
  - `plan`: Current `DirectorMasterPlan` object.
  - `history`: List of conversational user turns and applied system deltas.
  - `asset_catalog`: Registry of uploaded reference images and generated keyframe paths.
  - `approval_status`: `PENDING_REVIEW` | `MODIFICATIONS_REQUESTED` | `APPROVED` | `REJECTED`.
- **Delta Invalidation Strategy**: When an instruction targets Beat $K$:
  - Only Beat $K$'s visual prompt and cached keyframe path are invalidated.
  - Neighboring beats $1 \dots K-1$ and $K+1 \dots N$ remain untouched in memory and on disk.
  - Re-generation latency for a single beat modification drops to `<2.5s`.

### Alternatives Considered
- *Full regeneration on every message*: Rejected because regenerating 3–4 scenes every time the user fixes a typo or asks for one color change wastes 10–20 seconds and introduces unwanted visual drift in unchanged scenes.
- *In-memory only session*: Rejected because CLI users need to be able to exit, resume, or branch alternative versions across multiple command-line invocations.

---

## 2. LLM Director Reasoning & Offline Fallback Strategy

### Context
The director must formulate sophisticated narrative arcs, camera angles, voiceover dialogue, audio mood, and SFX cue timing from natural language. However, the system must maintain 100% reliability offline without failing when API keys are absent or network is disconnected.

### Decision
Implement a **Dual-Mode Autonomous Director Engine**:
1. **Mode A (Reasoning Director via LLM)**:
   - When `GEMINI_API_KEY` or `OPENAI_API_KEY` is present, prompt the LLM using Pydantic structured output (`DirectorMasterPlan.model_validate_json()`).
   - The LLM reasons over genre, narrative pacing, number of scenes (2–6), voice persona, audio ducking, and contextual sound design.
2. **Mode B (Rule-Based Semantic Heuristics Fallback)**:
   - When offline or no API key is configured, execute deterministic semantic extraction that parses character nouns, action verbs, and tone signals to generate a structured `DirectorMasterPlan`.
   - Never crashes, requires $0.00 compute tokens, and finishes in `<50ms`.

### Alternatives Considered
- *LLM-only (Hard dependency)*: Rejected because unit tests, CI/CD pipelines, and local development environments without paid API keys would immediately fail.
- *Rule-based only*: Rejected because regex heuristics cannot adapt to nuanced creative requests or complex multi-turn modifications.

---

## 3. Autonomous Frame Conditioning & Continuity Decision Engine

### Context
In video diffusion, feeding the wrong conditioning mode creates severe artifacts:
- Chaining the previous frame across an editorial cut causes nightmarish morphing (e.g. an astronaut's face morphing into a wide shot of a planet).
- Generating pure T2V when character continuity is needed causes the actor's face and clothes to randomly change between cuts.

### Decision
Implement an autonomous conditioning classifier in `core/conditioning_engine.py`:
- **`START_FRAME_ONLY`**:
  - Assigned when: A beat introduces or focuses on a specific character or environment reference, and motion initiates from that anchor.
- **`CHAIN_FROM_PREVIOUS`**:
  - Assigned when: Consecutive beats share the same character, the same camera angle, and the scene description denotes continuous action (e.g. *"continues lifting the artifact"* or *"keeps running"*).
  - The pipeline automatically extracts the terminal frame of Beat $N-1$ (`outputs/temp/last_frame_beat_{N-1}.jpg`) and injects it as Frame 0 of Beat $N$.
- **`START_AND_END_FRAME`**:
  - Assigned when: A beat describes a clear state transformation or targeted camera movement between two fixed anchors (e.g. *"sheathes sword"*, *"arrives at gate"*).
- **`HARD_CUT_NEW_KEYFRAME`**:
  - Assigned when: The camera angle changes (e.g. Wide ➔ Macro Close-up), the setting changes, or time jumps. Explicitly severs frame chaining to guarantee clean cinematic cuts.
- **`PURE_T2V`**:
  - Assigned when: Background atmosphere, fluid elements (water, smoke, fire), or abstract drone landscape sweeps with no strict subject continuity.

### Alternatives Considered
- *Always chain previous frame*: Rejected because camera angle switches look like broken AI warp distortions.
- *Never chain frames (Always independent keyframes)*: Rejected because continuous 1-shot action flows become disjointed.

---

## 4. Multi-Modal Asset Ingestion Protocol

### Context
Users should be able to provide character headshots (`--image character.jpg`), wardrobe concepts, environment reference art, or explicit start/end frames without needing to edit raw JSON manifests.

### Decision
Support flexible multi-modal asset flags in CLI & API:
- `--character "name:path/to/img.jpg"`: Registers character identity plate and assigns `@character_name` tag.
- `--environment "path/to/env.jpg"`: Locks background plate conditioning for the scene location.
- `--start-frame "path/to/frame.jpg"`: Overrides Beat 1 Frame 0 conditioning.
- The director binds these assets into the ComfyUI / Wan 3.0 multi-reference slots (`image_1` through `image_10`) automatically.

---

## 5. Interactive Review & Approval Gate Protocol

### Context
How does the system pause and wait for user approval across CLI and Agent modes?

### Decision
- **CLI Workflow**:
  - `python -m core.cli direct --prompt "..."`: Generates storyboard and enters an interactive terminal REPL loop.
  - Displays formatted table of scenes, keyframe locations, and audio decisions.
  - Prompts: `[A]pprove & Render, [M]odify Beat, [V]iew Thumbnails, [Q]uit > `.
  - `--approve` / `--auto-approve`: Non-interactive flag for CI/CD and automated pipelines.
- **Python / Agent API Workflow**:
  - `director.create_storyboard(prompt, references) -> StoryboardSession`
  - `director.apply_modification(session_id, instruction) -> StoryboardSession`
  - `director.approve_and_render(session_id) -> RenderOutput`
