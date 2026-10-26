# Feature Specification: Model-Aware Prompt Synthesis & Gemini Upgrade

**Feature Branch**: `011-prompt-synthesis-upgrade`

**Created**: 2026-10-26

**Status**: Draft

**Input**: User description: "specify changes required based on our study. also upgrade gemini model version to latest as 2.5 deprecated."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Latest Gemini Frontier Model Cascade for Story Synthesis (Priority: P1)

As a video creator initiating a new project from a concept prompt or script, I want narrative deconstruction to execute against the newest 2026 flagship model (`gemini-3.8-flash`) as the primary tier, so that scene breakdown, character attribution, and cinematography directives reflect state-of-the-art narrative intelligence without relying on deprecated model versions.

**Why this priority**: Fundamental entry point of the entire studio pipeline. Using deprecated 2.5 models risks API outages, deprecation rejections, and lower storyboarding quality.

**Independent Test**: Can be tested by invoking storyboard creation with valid credentials and verifying that `gemini-3.8-flash` successfully authors the complete `DirectorMasterPlan` in Tier 1.

**Acceptance Scenarios**:

1. **Given** a valid Gemini API key, **When** the creator submits a narrative concept or script, **Then** the synthesis engine calls `gemini-3.8-flash` as Tier 1, cascading to `gemini-3.5-flash`, `gemini-3.1-flash-lite`, and `gemini-flash-latest` before falling back to secondary providers.
2. **Given** a request specifying an explicit model override or legacy 2.5 model, **When** processed by the system, **Then** the system automatically routes to the modern equivalent (`gemini-3.8-flash`) with zero runtime errors.
3. **Given** all cloud APIs are offline or unconfigured, **When** the creator creates a storyboard, **Then** the system falls back to the deterministic offline heuristic engine without crashing.

---

### User Story 2 - Model-Specific Late-Stage Prompt Compilation at Render Time (Priority: P1)

As a creator rendering an individual beat or full timeline, I want the system to adapt and compile the visual prompt specifically for the selected target video model at render dispatch time, rather than baking a one-size-fits-all model format into the storyboard during initial story planning.

**Why this priority**: Eliminates prompt truncation, syntax incompatibility, and degraded video quality when switching between disparate video diffusion models (e.g. Wan 2.1, Kling, Google Veo, MiniMax Hailuo, Runway).

**Independent Test**: Can be tested by switching a beat card from one video model (e.g., Kling) to another (e.g., MiniMax or Wan 2.1) and verifying the dispatched prompt adheres strictly to the destination model's character limits, tokenizer constraints, and audio tag format without modifying the underlying canonical storyboard script.

**Acceptance Scenarios**:

1. **Given** a storyboard beat with dialogue, **When** dispatched to a model requiring inline dialogue tags (e.g., MiniMax H3), **Then** the prompt compiler formats spoken lines with `<d>dialogue</d>` tags.
2. **Given** a storyboard beat dispatched to a compact-budget model (e.g., Runway Gen-3 with 1,000 character limit), **When** the original motion prompt exceeds the limit, **Then** semantic compression retains high-priority kinetic vectors while fitting within the safe budget.
3. **Given** a storyboard beat dispatched to an open-weights DiT model (e.g., Wan 2.1), **When** compiling the prompt, **Then** the system outputs natural language subject-action-camera framing free of legacy quality buzzwords.

---

### User Story 3 - Pure-Motion Kinetic Prompting for Image-to-Video Continuity (Priority: P2)

As a creator generating video clips conditioned on an approved keyframe image (I2V), I want the video prompt to focus strictly on motion vectors, physical action, and camera movement while eliminating redundant descriptions of static wardrobe and environment, so that the video diffusion model does not suffer from prompt fighting against the input image.

**Why this priority**: Directly increases the First-Take Yield (FTY) of video generation from ~30% to >65% by preventing facial morphing, costume double-rendering, and motion freeze.

**Independent Test**: Can be tested by generating an I2V clip from an approved keyframe and inspecting the dispatched prompt to ensure static attire descriptions are suppressed while active kinetic verbs and object interactions are retained.

**Acceptance Scenarios**:

1. **Given** an approved keyframe image attached as `START_FRAME`, **When** the beat is rendered via I2V, **Then** the prompt adapter strips static visual appearance descriptions (e.g., clothing color, background architecture) and retains primary subject action, physical effects, and camera kinematics.
2. **Given** a prompt containing object interaction (e.g., "draws glowing sword from scabbard"), **When** the kinetic filter runs, **Then** the object interaction is preserved intact rather than greedily pruned by adjective/preposition filters.

---

### User Story 4 - Context-Aware Dynamic Negative Prompting (Priority: P2)

As a director producing videos across diverse genres (cinematic photorealism, 3D animation, anime, riddles), I want negative prompts to be dynamically synthesized based on the project genre and target model, so that live-action photorealistic renders are not degraded by contradictory anti-realism negative tags.

**Why this priority**: Hardcoded negative prompts currently include `"realistic photography"`, which harms live-action cinematic styles.

**Independent Test**: Can be tested by verifying that rendering a `cinematic_story` project does not include anti-photographic negative tags, while an `animation` or `riddle` project excludes tags appropriate to its visual aesthetic.

**Acceptance Scenarios**:

1. **Given** a project with `cinematic_story` genre and photorealistic art style, **When** compiling generation parameters, **Then** negative prompts exclude anti-realism terms and focus on motion jitter, anatomical distortion, and compression artifacts.
2. **Given** a project with 3D animation style, **When** compiling parameters, **Then** negative prompts appropriately penalize photorealistic photographic textures to maintain stylized coherence.

---

### User Story 5 - Multi-Reference Character Consistency Across Hard Cuts (Priority: P3)

As a creator producing multi-scene narratives with recurring characters across non-consecutive scenes or hard cuts, I want the system to supply character reference assets to models supporting multi-reference inputs, so that facial features and wardrobe remain consistent without requiring seamless frame-to-frame chaining.

**Why this priority**: Solves the biggest challenge in multi-shot AI storytelling: preventing character identity drift across camera cuts where previous-frame chaining is physically impossible.

**Independent Test**: Can be tested by defining a character reference image for a story and verifying that scenes with camera cuts pass the reference image payload to supported models (e.g. Kling 2.0+, Wan 3.0, Veo 3).

**Acceptance Scenarios**:

1. **Given** a project with character references defined, **When** rendering a beat with a model supporting reference images, **Then** the system passes up to the model's maximum allowed reference images in the API payload.
2. **Given** a model that does not support reference images, **When** rendering, **Then** the system gracefully omits the unsupported field without failing the generation request.

---

### Edge Cases

- What happens when a user requests an obscure or deprecated Gemini model via CLI flag `--model`?
  - System logs an informational deprecation notice and automatically maps to `gemini-3.8-flash`.
- What happens if the video prompt's entire text consists of static descriptions (e.g. "A red car parked on a quiet street") in I2V mode?
  - Kinetic filter must provide a safe default motion vector (e.g. "Slow atmospheric camera push-in, subtle environmental ambient motion") rather than sending an empty string to the video model.
- How does the prompt adapter handle multi-lingual dialogue in native audio mode?
  - Spoken lines must be passed in their original language inside audio directive tags, while visual motion directives remain in high-precision cinematic English.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST configure `gemini-3.8-flash` as the default Tier 1 primary frontier model in the Gemini cascade, followed by `gemini-3.5-flash`, `gemini-3.1-flash-lite`, and `gemini-flash-latest`.
- **FR-002**: System MUST deprecate references to `gemini-2.5-flash`, `gemini-2.5-pro`, and `gemini-2.0-flash`, providing automatic fallback aliasing to `gemini-3.8-flash`.
- **FR-003**: Storyboard planning (`StoryWriterGateway`) MUST generate model-agnostic canonical dual prompts (`image_prompt` and `motion_prompt`) and MUST NOT hardcode model-specific formatting or token budgets at the planning stage.
- **FR-004**: Prompt adaptation and token budgeting MUST execute late in the pipeline at render dispatch time (`route_and_execute_beat`), compiling prompts against the active target model's profile.
- **FR-005**: For Image-to-Video (I2V) rendering, prompt compilation MUST suppress static visual descriptors while retaining kinetic actions, physics, and camera vectors.
- **FR-006**: Kinetic filtering MUST preserve active object interactions and prepositions that denote action (e.g., "strikes with", "holding", "interacts with").
- **FR-007**: System MUST replace static negative prompt strings with dynamic, genre-aware negative prompt profiles calibrated for photorealistic cinematic, 3D animated, and stylized aesthetics.
- **FR-008**: System MUST pass bound character reference images to video models that advertise `supports_reference_images=True` in their profile, respecting `max_reference_images`.
- **FR-009**: In native clip audio mode, prompt compilation MUST inject the appropriate syntax for the target model family (`<d>...</d>` for MiniMax, `Spoken line: "..."` for Kling/Veo).

### Key Entities

- **ModelCascadeConfig**: Defines prioritized LLM tiers for narrative synthesis, with `gemini-3.8-flash` at the top of the Gemini candidate queue.
- **VideoModelProfile**: Metadata catalog defining token/character limits, native audio syntax, reference image capacities, and prompt grammar for each video model version.
- **AdaptedPromptResult**: Contains original prompt, model-specific adapted prompt, compression ratio, and modality flags.
- **NegativePromptProfile**: Context-aware negative prompts categorized by genre, aesthetic style, and target diffusion engine.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of storyboard synthesis requests using default Gemini configurations execute against `gemini-3.8-flash` without deprecation warnings or runtime errors.
- **SC-002**: First-Take Yield (FTY) for Image-to-Video generation increases by at least 25% due to the elimination of static prompt fighting.
- **SC-003**: 0% prompt truncation or token overflow errors across all supported video model profiles during beat rendering.
- **SC-004**: Storyboard generation latency remains under 4.0 seconds for a typical 4-scene beat breakdown on Tier 1.
- **SC-005**: Photorealistic cinematic renders contain zero contradictory anti-photographic negative tags.

## Assumptions

- Target Gemini API keys support Gemini 3.x series models through the unified Google GenAI SDK.
- Video models supporting `reference_images` accept standard publicly accessible HTTP image URLs or base64 data payloads as defined in their provider documentation.
- The user retains full manual override capability in the Studio interface to edit both `image_prompt` and `motion_prompt` independently prior to rendering.
