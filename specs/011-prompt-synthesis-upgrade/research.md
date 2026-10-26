# Phase 0 Research: Model-Aware Prompt Synthesis & Gemini Upgrade

**Branch**: `011-prompt-synthesis-upgrade` | **Date**: 2026-10-26

## Research Findings & Architectural Decisions

### 1. Gemini Model Upgrade & Deprecation Aliasing
- **Decision**: Update `ModelCascadeConfig` to establish `gemini-3.8-flash` as the Tier 1 flagship narrative generation model, backed by `gemini-3.5-flash`, `gemini-3.1-flash-lite`, and `gemini-flash-latest`. Establish an explicit dictionary alias layer `LLM_MODEL_ALIASES` in `core/models.py` mapping `gemini-2.5-flash`, `gemini-2.5-pro`, `gemini-2.0-flash`, and `gemini-1.5-flash` forward to `gemini-3.8-flash` and `gemini-3.1-flash-lite`.
- **Rationale**: Google has phased out the 2.5 and 2.0 experimental generations in 2026. The 3.8 series offers native multimodal reasoning, near-instant JSON serialization conforming to Pydantic schemas, and superior Hollywood cinematic beat decomposition. Aliasing ensures zero breaking changes for existing CLI invocations or persisted sessions.
- **Alternatives Considered**: 
  - *Hard failure on 2.5 inputs*: Rejected because it would abruptly break user scripts, CLI aliases, and existing session manifests without delivering user value.

### 2. Single-Source-of-Truth Model Capability Declarations
- **Decision**: Expand `VideoModelProfile` in `core/provider_registry.py` to become the comprehensive Single Source of Truth (SOT) for each model. Include `audio_syntax`, `negative_prompt_strategy`, `prompt_syntax_type`, `provider_endpoints`, and `provider_rates`.
- **Rationale**: Currently, registering a new model version (such as Kling 4.5, Wan 3.5, or Veo 4) requires modifying 5 separate files (`models.py`, `provider_registry.py`, `cost_arbitrage.py`, `fal_provider.py`, `apidot_provider.py`). By consolidating provider endpoints and rates into the model profile, adding a new model or version becomes a single declarative entry.
- **Alternatives Considered**: 
  - *External YAML/JSON files*: Evaluated, but maintaining strongly-typed Pydantic models in Python guarantees compile-time linting, IDE autocompletion, and zero JSON parse overhead on hot paths.

### 3. Render-Time Dynamic Prompt Compilation (Late-Stage Adaptation)
- **Decision**: Remove the premature `adapter.adapt_prompt(model_id="kling-v1.5")` call from `StoryWriterGateway` during storyboard creation. Keep storyboard `image_prompt` and `motion_prompt` pure and model-neutral. Introduce `PromptCompiler` executed inside `route_and_execute_beat` at the exact instant a clip is dispatched.
- **Rationale**: Storyboard generation and video rendering are decoupled in the Studio workflow. Users frequently tweak scripts, swap models (e.g. from Kling to Wan 2.1 to Hailuo), or change modalities (T2V vs I2V). Compiling at render time ensures the prompt matches the exact model profile, tokenizer budget, and audio markup without requiring an LLM re-run.
- **Alternatives Considered**:
  - *Adapting prompts on every UI model dropdown change*: Rejected because it mutates persistent storyboard records, causing destructive data loss of the director's original prose.

### 4. Pure-Motion Kinetic I2V Prompting & Prompt-Fighting Elimination
- **Decision**: In Image-to-Video mode conditioned on an approved keyframe (`START_FRAME`), `PromptCompiler` isolates kinetic motion vectors, subject dynamics, and camera movement while filtering out static appearance descriptions (e.g. clothing colors, stationary background decor). Refine regular expressions to preserve action-oriented prepositions (e.g. "strikes with", "holding", "interacts with").
- **Rationale**: Diffusion transformers conditioned on an input frame derive visual textures directly from image latents. Re-specifying clothing and face details in the text prompt induces "prompt fighting," which causes face distortion, sudden attire changes, and temporal jitter.
- **Alternatives Considered**:
  - *Empty text prompt with camera motion only*: Rejected because video models need explicit cues for complex subject actions (e.g. running, swinging sword, speaking).

### 5. Context-Aware Dynamic Negative Prompting
- **Decision**: Create a `NegativePromptCompiler` that dynamically constructs negative prompts from `(genre, visual_art_style, model_profile)`. Specifically:
  - *Cinematic Photorealism*: Negates 3D renders, CGI, plastic skin, jitter, morphing, and anatomical distortion, while strictly omitting anti-realism terms like `"realistic photography"`.
  - *3D Animation / Pixar Style*: Negates photorealism, live-action footage, film grain, and noise.
  - *Riddles / Motion Graphics*: Negates complex backgrounds, clutter, low contrast, and blur.
- **Rationale**: The previous hardcoded negative string penalized `"realistic photography"`, which actively degraded photorealistic cinematic generations.
- **Alternatives Considered**:
  - *Manual negative prompt input only*: Rejected because casual creators expect intelligent defaults that produce high-fidelity results without prompt engineering.

### 6. Multi-Reference Character Identity Binding
- **Decision**: Pass bound character reference assets (`ImageRole.CHARACTER_IMAGE`) into provider payloads for models that advertise `supports_reference_images=True`, capped at `max_reference_images`.
- **Rationale**: Frame -1 chaining only works for sequential continuity shots. For hard cuts, camera angle switches, and multi-scene narratives, reference image slots (available in Kling 2.0+, Wan 3.0, Veo 3) are the only mechanism to lock facial identity without fine-tuning LoRAs.
- **Alternatives Considered**:
  - *Re-using Frame -1 across hard cuts*: Rejected because injecting an old camera angle as the start frame prevents changing angles or cutting to a new perspective.
