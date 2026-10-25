# Feature Specification: Dynamic AI Story Writer & Narrative Cascade

**Feature Directory**: `specs/004-dynamic-story-writer`  
**Created**: 2026-10-23  
**Status**: Draft  
**Input**: User description: "Dynamic LLM Story Writer Engine with latest models version and fallback to older versions"

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Prompt-to-Narrative Dynamic Expansion (Priority: P1) 🎯 MVP

As a video creator,  
I want to provide a short natural language concept or idea,  
So that the AI story writer dynamically authors an original multi-beat script with unique dialogue, pacing, cinematic visual descriptions, and sound cues, rather than relying on fixed or hardcoded templates.

**Why this priority**: Solves the core creative bottleneck by producing authentic, customized, and genre-specific storytelling for any arbitrary prompt before sending the plan to the visual storyboard approval gate.

**Independent Test**: Provide a prompt such as *"A clumsy time-traveling barista accidentally serves coffee to Napoleon"* via the director interface. Verify that the output contains a tailored narrative arc with customized comedic dialogue, distinct visual beats, and matching sound effects rather than generic placeholder sentences.

**Acceptance Scenarios**:

1. **Given** a user inputs a creative concept prompt, **When** the director initiates storyboard creation, **Then** the system produces a dynamic multi-scene script (2 to 5 beats) with distinct narrative titles, character dialogues, and visual scene prompts matching the requested tone.
2. **Given** a prompt implying a specific tone (e.g., suspense, humor, educational, drama), **When** the narrative is synthesized, **Then** the generated dialogue, background music mood, and sound effect cues align with that tone.
3. **Given** the generated story script is completed, **When** formatted for review, **Then** each scene beat specifies duration, camera motion, visual prompt, and voiceover text ready for the approval gate.

---

### User Story 2 - Full Script & Long-Form Text Ingestion (Priority: P2)

As a content creator or educator with existing text,  
I want to paste an entire article, fable, blog post, or pre-written script,  
So that the AI intelligently segments and adapts the text into vertical 9:16 scene beats while preserving my original narrative words and intent.

**Why this priority**: Creators frequently arrive with finished scripts or articles and need automated adaptation into vertical video scenes without the AI rewriting their core message or altering their exact words.

**Independent Test**: Submit a 3-paragraph story text into the director. Verify that the engine splits the text into logical scene beats, retains the author's original dialogue across sequential scenes, and generates corresponding visual camera directions and sound cues.

**Acceptance Scenarios**:

1. **Given** a multi-paragraph text or script, **When** submitted to the story writer, **Then** the system partitions the text across sequential scenes without truncating or inventing unintended dialogue.
2. **Given** a long-form script with character speech and descriptive exposition, **When** parsed into beats, **Then** the spoken text is assigned to voiceover narration and the descriptive text is transformed into visual diffusion prompts.
3. **Given** a script exceeding standard short-form length, **When** processed, **Then** the system paces the narrative beats to fit vertical video timing constraints while maintaining narrative coherence.

---

### User Story 3 - Multi-Tier Model Cascade & Resilient Offline Fallback (Priority: P3)

As a developer and studio operator,  
I want the story writer to query the latest available artificial intelligence model generation,  
So that I get the highest narrative quality while automatically cascading to stable predecessor models upon rate limits or errors, and falling back to a deterministic offline engine when unauthenticated.

**Why this priority**: Model availability, rate limits, and network connectivity fluctuate. A multi-tier cascade guarantees uninterrupted operation, allowing the system to run locally offline with zero crashes while automatically upgrading to frontier models when credentials are present.

**Independent Test**: Simulate an unavailability or quota error on the primary latest model. Verify that the story engine automatically queries the secondary model tier in under 1 second without throwing an unhandled exception or interrupting the user.

**Acceptance Scenarios**:

1. **Given** valid credentials for a supported provider, **When** a story request is initiated, **Then** the engine automatically attempts generation using the latest available frontier model version.
2. **Given** the primary latest model encounters a rate limit (HTTP 429), temporary outage, or quota restriction, **When** the error is caught, **Then** the engine immediately cascades down to the secondary stable high-throughput model tier.
3. **Given** no external credentials are configured or network access is unavailable, **When** a story request is made, **Then** the system seamlessly falls back to the deterministic local rule engine without crashing, producing a valid storyboard plan.

---

### User Story 4 - Multi-Aspect Ratio Framing & Canvas Adaptation (Priority: P2)

As a multi-platform video creator,  
I want to specify my desired video aspect ratio (`9:16`, `16:9`, `1:1`, or `4:5`),  
So that the AI story writer tailors its visual composition prompts for that specific framing (e.g., panoramic widescreen vs vertical mobile) and the pipeline renders the master video at the exact requested canvas resolution.

**Why this priority**: Creators publish across diverse platforms (YouTube horizontal 16:9, Shorts/TikTok 9:16, Instagram square 1:1 and portrait 4:5). Visual storytelling prompts and rendering must adapt dynamically to avoid awkward cropping, black pillarbox bars, or visual distortion.

**Independent Test**: Run `python -m core.cli direct --prompt "A space freighter docking at Saturn" --aspect-ratio 16:9`. Verify that the generated visual prompts specify widescreen 16:9 composition, keyframe images are synthesized at 1920x1080, and the compiled master video is rendered at 1920x1080.

**Acceptance Scenarios**:

1. **Given** a user specifies `--aspect-ratio 16:9`, **When** the story writer plans scenes, **Then** all visual prompts specify widescreen horizontal framing and the plan sets canvas resolution to 1920x1080.
2. **Given** a user specifies `--aspect-ratio 1:1`, **When** the story writer plans scenes, **Then** visual prompts specify square composition and the plan sets canvas resolution to 1080x1080.
3. **Given** a user specifies `--aspect-ratio 4:5`, **When** the story writer plans scenes, **Then** visual prompts specify portrait feed composition and the plan sets canvas resolution to 1080x1350.
4. **Given** no aspect ratio is specified, **When** the plan is created, **Then** the system defaults to mobile vertical `9:16` (1080x1920).

---

### Edge Cases

- **Empty or Gibberish Input**: How does the system handle single-word or non-sensical inputs (e.g., `"asdf"` or `""`)?  
  *The system provides a polite clarification message or applies a default creative interpretation rather than failing.*
- **Excessively Long Input**: What happens if a user inputs an entire 5,000-word essay?  
  *The system summarizes or extracts the core narrative arc into a maximum of 6 vertical video scenes (under 60 seconds total duration) rather than generating an unrenderable video length.*
- **Provider API Outage / Missing Keys**: How does the engine behave when all external providers fail?  
  *The engine automatically activates the offline deterministic heuristic fallback, ensuring 100% operational uptime.*
- **Strict Content / Safety Filtering**: What happens if a provider flags a benign dramatic prompt?  
  *The engine catches the content safety exception and routes the prompt through an alternative model tier or the local rule engine.*
- **Invalid Aspect Ratio String**: What happens if a user inputs `--aspect-ratio 21:9`?  
  *The system validates the argument against supported ratios (`9:16`, `16:9`, `1:1`, `4:5`) and provides a clear error listing the valid choices.*

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST accept natural language prompts or multi-paragraph text scripts as input for narrative generation.
- **FR-002**: System MUST dynamically determine scene count (between 2 and 6 beats) based on narrative pacing and input length.
- **FR-003**: System MUST author unique dialogue or narration text for each scene beat matching the detected or requested genre.
- **FR-004**: System MUST author detailed visual prompts tailored to the configured aspect ratio (`9:16` vertical, `16:9` widescreen, `1:1` square, `4:5` portrait), including camera movement, lighting, subject placement, and environment.
- **FR-005**: System MUST assign contextual audio cues (background music genre/mood and specific sound effect triggers with timing offsets) tailored to the narrative.
- **FR-006**: System MUST enforce structured data output conforming to the director master plan schema.
- **FR-007**: System MUST support a multi-tier model cascade that attempts generation using the newest available model version first before falling back to stable predecessor tiers upon error.
- **FR-008**: System MUST provide a deterministic offline fallback mode that operates with zero external network or credential dependencies.
- **FR-009**: System MUST allow conversational delta adjustments to the generated story plan (e.g., tone shift, dialogue rewrite, pacing tweak) while preserving unaffected beats.
- **FR-010**: System MUST support configurable video aspect ratios (`9:16` 1080x1920, `16:9` 1920x1080, `1:1` 1080x1080, `4:5` 1080x1350) and output keyframe assets and master video matching the exact specified canvas resolution.

---

### Key Entities

- **NarrativeBrief**: Represents the user's initial creative prompt or supplied script, including optional tone hints, character tags, target genre, and requested aspect ratio.
- **VideoAspectRatio**: Enumeration of supported aspect ratios (`9:16`, `16:9`, `1:1`, `4:5`) with corresponding width and height dimensions.
- **StoryScript**: Represents the authored multi-scene narrative comprising ordered scene beats, character dialogues, visual staging prompts, and sound design.
- **ModelCascadeConfig**: Represents the ordered list of AI model candidates and fallback policies (Primary Frontier ➔ Stable High-Throughput ➔ Lightweight Legacy ➔ Offline Local).
- **DirectorMasterPlan**: The standardized domain contract representing the approved multi-beat roadmap ready for visual keyframing and approval gating.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Dynamic narrative generation from prompt to structured storyboard plan completes in under 4.0 seconds when using cloud AI models.
- **SC-002**: 100% of generated story plans strictly validate against the director master plan schema without manual schema correction.
- **SC-003**: System maintains 100% service uptime by falling back to secondary models or the offline rule engine with 0% unhandled crash rate.
- **SC-004**: When provided with a multi-paragraph existing script, 100% of the author's primary dialogue lines are preserved across the partitioned scenes without accidental truncation.
- **SC-005**: Master video and keyframe plates render with 0% pillarboxing or aspect ratio distortion matching the selected target ratio (`9:16`, `16:9`, `1:1`, `4:5`).

---

## Assumptions

- Users may or may not possess cloud AI API credentials; the system must function gracefully in both environments.
- Video duration for vertical short-form content defaults to between 5 and 60 seconds (typically 2 to 5 scenes of 3 to 6 seconds each).
- The story writer produces structured text plans; visual image generation and audio synthesis are handled by downstream pipeline stages after user approval.
- Default language for narrative synthesis is English, with voiceover personas matching standard neural speech profiles.
