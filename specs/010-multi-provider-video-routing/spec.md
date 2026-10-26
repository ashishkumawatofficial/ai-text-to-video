# Feature Specification: Multi-Provider Video Routing with Dynamic Cost Arbitrage & Multimodal Generation

**Feature Branch**: `010-multi-provider-video-routing`

**Created**: 2026-10-25

**Status**: Draft

**Input**: User description: "channelize video rendering into 2: 1. self deployed model on serverless + audio synthesis, 2. multi model api provider like apidot ai, fal ai & kie ai. Route and pick best provider based on realtime checking and comparing price based on model picked by user whichever passes the lower cost job is assigned to that. Research API documentation, pricing documentation, failure handling, does failure cost or not, links bank, show sensitive information in UI, future expandability, T2V, I2V, T+I, audio on/off, prompt character limit per model version, motion prompting, Remotion audio mastering bypass, video extending, and video upscaling."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Dynamic Lowest-Cost Provider Routing & Pre-Flight Cost Audit (Priority: P1)

As a video creator, I want the system to dynamically inspect live pricing across supported third-party providers (such as fal.ai, apidot.ai, kie.ai) for my selected video model and route the rendering job to the provider offering the lowest verified cost, so that video generations are executed at optimal cost efficiency with zero manual research.

**Why this priority**: Core value driver of Channel 2. Without real-time price arbitrage, creators either overpay or are forced to manually juggle multiple consoles, API tokens, and pricing sheets.

**Independent Test**: Can be tested by requesting a 5-second video beat for a target model (e.g., Kling or Seedance), verifying that the system queries provider rate quotes, selects the lowest-priced provider, and successfully delivers the rendered clip.

**Acceptance Scenarios**:

1. **Given** a scene beat configured with model "Kling" for 5 seconds, **When** the render button is clicked, **Then** the system checks current quotes from all providers offering Kling (fal.ai, apidot.ai, kie.ai), identifies the lowest price, and dispatches the job to that winning provider.
2. **Given** the winning provider experiences a 5xx server failure or timeout, **When** the failure occurs, **Then** the system verifies zero cost was incurred for the failed job and automatically cascades to the second-lowest cost provider without user intervention.
3. **Given** a creator who prefers a specific vendor, **When** they set a provider manual override in the Studio UI, **Then** the system respects the override and bypasses automatic price routing.

---

### User Story 2 - Model-Aware Prompt Adaptation & Character Limit Budgeting (Priority: P1)

As a video director, when I select or change a video model (e.g., Kling, Seedance, Runway, MiniMax, Google Veo, Wan), I want the system to automatically adjust and compress the scene prompt within that specific model's version-bound character and token limits without altering the story plot or character actions, so that rendering requests are never rejected by API gateways or silently truncated by neural text encoders.

**Why this priority**: Foundational reliability requirement. Models enforce strict character limits (e.g., Runway: 1,000 chars; Kling: 3,072 chars; Seedance: 2,000 chars; CogVideoX: 226 tokens). Without model-aware adaptation, cross-model switching results in HTTP 422 errors or silent truncation of scene dynamics.

**Independent Test**: Can be tested by creating a 2,200-character descriptive storyboard beat, switching the model from Kling (limit: 3,072) to Runway (limit: 1,000), and verifying that the prompt is automatically compressed under 1,000 characters while preserving all subject actions, camera paths, and dialogue lines.

**Acceptance Scenarios**:

1. **Given** a storyboard prompt of 1,800 characters, **When** the user assigns the scene to Runway Gen-3 (1,000 character limit), **Then** the system condenses the prompt under 1,000 characters, preserving core visual actions, camera vectors, and emotional cues.
2. **Given** any storyboard card in Web Studio, **When** the user views the card, **Then** a dynamic character counter displays current length alongside the selected model's limit (e.g., `420 / 1000 chars [Runway]`).
3. **Given** an open-weights model with a strict token context window (e.g., Wan 2.1 or CogVideoX), **When** a prompt is prepared, **Then** the system ensures the prompt fits within the model's safe token window to prevent silent attention degradation.

---

### User Story 3 - Multimodal Generation (Text-to-Video, Image-to-Video, Dual Frame Pinning) (Priority: P2)

As a creator, I want to choose between pure Text-to-Video (T2V), Image-to-Video (I2V), and Start/End Frame interpolation, with the system automatically formatting prompts—differentiating between comprehensive scene descriptions (T2V) and motion-only prompts (I2V)—so that visual assets are animated accurately without introducing duplicate subjects or visual artifacts.

**Why this priority**: High creative impact. AI video models behave fundamentally differently when an image is provided: re-describing static elements confuses diffusion models, whereas motion-only prompts deliver clean, stable motion.

**Independent Test**: Can be tested by providing a keyframe image and selecting I2V, verifying that the prompt generated describes only kinetics and camera movement, and that the resulting video adheres to the source image composition.

**Acceptance Scenarios**:

1. **Given** a storyboard beat in Image-to-Video (I2V) mode with an attached start frame, **When** the prompt is prepared, **Then** the system formats it as a motion-only prompt focusing on camera vectors, character kinetics, and environmental dynamics, omitting descriptions of static objects already in the image.
2. **Given** a beat with both a start frame and an end frame, **When** routed to an interpolation-capable model (e.g., Kling, MiniMax H3, Luma Ray, Seedance 2.0), **Then** the system supplies both frames and prompts the model to generate the physical motion transition bridging them.
3. **Given** a beat with multiple character reference images, **When** routed to a multi-reference model (e.g., Seedance 2.0/2.5 or MiniMax), **Then** the system attaches the reference assets to maintain character identity consistency.

---

### User Story 4 - Native Clip Audio Integration & Remotion Mastering Bypass (Priority: P2)

As a creator, when I enable native audio on models that support it (e.g., Kling, MiniMax, Seedance, Google Veo), I want the system to inject dialogue lines and acoustic environmental descriptors into the clip prompt, and automatically instruct the final video mastering engine (Remotion) to preserve the clip's native soundtrack while bypassing overlapping synthetic voiceovers, so that character speech and Foley sound clear and natural without audio collisions.

**Why this priority**: Essential audio-visual harmony. Playing synthetic voiceover tracks on top of clips that already have embedded speech creates chaotic double-talking.

**Independent Test**: Can be tested by generating a scene with "Audio ON" on Kling or MiniMax, verifying that the output clip has native dialogue/Foley, and that Remotion plays the clip's audio at full volume while muting the external TTS voiceover.

**Acceptance Scenarios**:

1. **Given** a beat with dialogue and "Native Audio = ON", **When** the prompt is generated, **Then** the prompt incorporates the dialogue text and acoustic environmental descriptors formatted to the target model's syntax.
2. **Given** a project containing clips rendered with native audio, **When** Remotion compiles the master timeline, **Then** Remotion passes through the clip's native audio and disables the external synthetic voiceover for those beats.
3. **Given** a project containing clips rendered with "Native Audio = OFF", **When** Remotion compiles the master timeline, **Then** Remotion applies its standard full audio suite (TTS voiceover, cinematic background music, SFX cues, ducking, and kinetic subtitles).

---

### User Story 5 - Real-Time Cost Transparency & Sensitive Provider Insights in Web Studio (Priority: P3)

As a studio user, I want to inspect a live comparison table of provider quotes, failure-cost policies, official documentation links, and prompt length limits in the Web Studio UI, so that I have complete transparency and confidence before initiating a render.

**Why this priority**: Provides complete cost transparency and builds trust by exposing pricing breakdowns, failure insurance policies, and direct links to official documentation.

**Independent Test**: Can be tested by opening the "Provider & Cost Insights" modal in the Studio UI, verifying that live quotes for all providers are displayed alongside clickable official links and failure refund badges.

**Acceptance Scenarios**:

1. **Given** the Web Studio interface, **When** a user clicks on the "Cost & Provider Insights" button, **Then** a modal opens displaying live prices across fal.ai, apidot.ai, and kie.ai for the selected model, duration, and resolution.
2. **Given** any provider row in the modal, **When** viewed, **Then** it displays a clickable link to official documentation, official pricing, and a badge confirming failure billing policy ("Zero Cost on Failed Job").
3. **Given** any storyboard card, **When** displayed, **Then** a badge shows the currently selected provider, estimated cost in USD, and active modality (T2V / I2V).

---

### User Story 6 - Video Extending & On-Demand Video Upscaling (Priority: P3)

As a creator, I want to be able to extend an existing generated clip by +4s/+5s seamless narrative continuation, or upscale the draft clip to 4K resolution on demand, being billed strictly for the incremental extension or upscaling pass without re-rendering the parent clip.

**Why this priority**: High production value. Allows iterative sequence expansion and sharp 4K mastering while keeping drafting costs low.

**Independent Test**: Can be tested by taking an existing rendered 5-second clip, clicking "Extend Video", supplying a continuation prompt, and verifying that the resulting video is seamlessly lengthened by +5 seconds.

**Acceptance Scenarios**:

1. **Given** an existing completed video clip, **When** the user clicks "Extend Video" and inputs a continuation prompt, **Then** the system invokes the model's extension endpoint (e.g., Kling Extend or Runway Extend) and appends the new sequence.
2. **Given** a completed video extension, **When** the job is billed, **Then** the cost reflects only the newly added duration, not the initial clip duration.
3. **Given** a project ready for final export, **When** the user toggles "4K Neural Upscale", **Then** the system passes the master clips through the designated upscaler (e.g., Topaz Video AI or Real-ESRGAN) to produce a 4K master.

---

### Edge Cases

- **Provider Pricing API Downtime**: If a provider's live pricing endpoint is unreachable or times out, the system falls back to cached official rate sheets and displays a "Cached Rate (Updated < 24h)" indicator.
- **Provider Out of Credits**: If an API returns an "Insufficient Quota / Credits" error (HTTP 402), the system immediately marks that provider as degraded, flags an alert in the UI, and routes to the next lowest provider.
- **Content Filter / Safety Trigger (HTTP 422)**: If a prompt triggers an upstream safety filter, the system catches the violation, refunds or confirms zero charge, and prompts the user in the Studio UI with the flagged trigger words for revision.
- **Partial Native Audio**: In a multi-scene project where Scene 1 has Native Audio ON and Scene 2 has Native Audio OFF, Remotion seamlessly transitions: Scene 1 plays clip audio with gentle ducked background music, while Scene 2 activates synthetic TTS voiceover and full audio ducking.
- **Prompt Token Boundary on Multibyte Characters**: When counting characters for models with byte limits (e.g., PixVerse 2,048 UTF-8 bytes) or models using non-English text, the system calculates UTF-8 byte length to prevent silent truncation.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST maintain a dual-channel rendering architecture: Channel 1 (Self-Deployed Serverless/Pod Infra) and Channel 2 (Multi-Model Third-Party Provider Gateway).
- **FR-002**: System MUST integrate an extensible provider registry supporting **fal.ai**, **apidot.ai**, and **kie.ai** with modular adapter interfaces for future provider expansion.
- **FR-003**: System MUST maintain an official documentation and pricing link bank stored in the system configuration, containing verified documentation URLs, pricing pages, and failure policies for all supported providers.
- **FR-004**: System MUST perform pre-flight real-time cost checks across all providers supporting the selected model and automatically select the provider with the lowest estimated cost.
- **FR-005**: System MUST allow users to manually override the automatic cost router and pin a preferred provider per project or per storyboard beat.
- **FR-006**: System MUST automatically cascade to the next-cheapest provider if the selected provider returns a 5xx server error, network timeout, or infrastructure crash.
- **FR-007**: System MUST track and verify that failed rendering jobs (5xx errors or network drops) incur $0.00 charge, alerting the user if any provider deducts quota for a failed task.
- **FR-008**: System MUST maintain version-specific character and token limit profiles for every supported model (e.g., Kling 1.0 vs 1.5 vs 2.0; Seedance 1.0 vs 2.0 vs 2.5; Runway Gen-2 vs Gen-3; MiniMax Hailuo vs H3; Google Veo 1 vs 2/3; Wan 2.1 vs 2.5).
- **FR-009**: System MUST dynamically adapt and compress prompts when a model change occurs, ensuring prompts fit within the new model's character and token budget without altering the underlying narrative or action continuity.
- **FR-010**: System MUST support three distinct visual generation modalities: Text-to-Video (T2V), Image-to-Video (I2V), and Start/End Frame Interpolation.
- **FR-011**: System MUST format I2V prompts as kinetic motion prompts (focusing on camera paths, character actions, and environmental physics) while suppressing redundant descriptions of static elements present in the source image.
- **FR-012**: System MUST provide an "Audio ON/OFF" toggle per beat and per project. When Audio is ON, the system injects dialogue tags, room acoustics, and Foley descriptors into the prompt.
- **FR-013**: System MUST update the Remotion video synthesis bridge to inspect clip audio metadata and automatically bypass synthetic voiceover mastering for clips containing native embedded audio.
- **FR-014**: System MUST display a real-time Cost and Provider Transparency modal in the Web Studio UI, showing live pricing comparison across providers, character limits, official docs links, and zero-cost failure policies.
- **FR-015**: System MUST support video extension workflows, allowing users to append +4s to +5s narrative continuations to existing clips, billing strictly for the incremental duration.
- **FR-016**: System MUST support on-demand video upscaling (e.g., via Topaz Video AI or Real-ESRGAN) to upgrade draft 720p/1080p clips to 4K resolution on export.

---

### Key Entities *(include if feature involves data)*

- **VideoProvider**: Represents an external API provider (fal.ai, apidot.ai, kie.ai). Attributes include `provider_id`, `name`, `official_docs_url`, `pricing_docs_url`, `failure_refund_policy`, `supported_models`, and `health_status`.
- **ModelProfile**: Represents a specific foundation video model version (e.g., `kling-v1.5`, `bytedance-seedance-2.5`, `runway-gen3-turbo`). Attributes include `family`, `version`, `hard_char_limit`, `safe_char_limit`, `token_encoder_type`, `supports_native_audio`, `supports_i2v`, `supports_dual_frame`, `supports_extend`, and `native_resolutions`.
- **ProviderPriceQuote**: Represents a real-time price estimation for a specific generation task. Attributes include `provider_id`, `model_id`, `duration_sec`, `resolution`, `estimated_cost_usd`, `billing_unit` (per second or per task), `is_available`, and `quoted_at_timestamp`.
- **RenderingJobTicket**: Represents an execution unit dispatched to an external provider. Attributes include `job_id`, `provider_id`, `model_id`, `beat_index`, `modality` (T2V/I2V), `has_native_audio`, `prompt`, `estimated_cost_usd`, `actual_cost_usd`, `status` (PENDING, RUNNING, COMPLETED, FAILED, CASCADED), and `output_video_path`.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of video generation jobs in Channel 2 perform a real-time price comparison and route to the lowest-cost verified provider unless manually overridden.
- **SC-002**: Prompt character limit compliance reaches 100%: zero rendering jobs fail due to character limit exceeding or payload size rejection (HTTP 422).
- **SC-003**: 0% audio collision rate: in projects containing native audio clips, Remotion never plays overlapping synthetic voiceover on top of native character speech.
- **SC-004**: System achieves 100% automated recovery on provider infrastructure failure (5xx/timeout): the system automatically cascades to the secondary provider within 5 seconds without user intervention and with $0.00 incurred on the failed attempt.
- **SC-005**: Studio users can view the real-time cost comparison across all providers and click through to official documentation links within 2 clicks from any storyboard card.
- **SC-006**: Video extension operations bill strictly for newly generated incremental seconds, maintaining a 0% billing overhead on previously rendered footage.

---

## Assumptions

- Users maintain funded API accounts or API keys for the external providers they choose to enable (fal.ai, apidot.ai, kie.ai).
- External provider pricing endpoints or official rate tables remain accessible via HTTP requests with reasonable availability (< 2.0s response latency).
- Models supporting native audio output their sound as standard AAC/MP3 audio streams embedded directly within the returned MP4 container.
- For open-weights models deployed on serverless infrastructure (Channel 1), GPU second metering remains the primary cost basis as established in Feature 005.
- The Studio UI dev server and Remotion renderer have access to ffmpeg for media inspection and stream validation.
