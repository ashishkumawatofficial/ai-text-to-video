# Feature Specification: Multi-Character Dialogue Attribution and Continuous Video Motion Synthesis

**Feature Branch**: `007-character-dialogue-motion-synthesis`

**Created**: 2026-10-25

**Status**: Draft

**Input**: User description: "let's specify on all above conversation"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Multi-Character Spoken Dialogue Attribution (Priority: P1)

When a creator requests a story involving multiple subjects (e.g. four cows having tea while teasing a passerby), the system automatically analyzes the narrative to identify distinct speakers, assigns dialogue lines to specific characters, and synthesizes each line with a unique vocal persona tailored to that character's personality, gender, and archetype, eliminating single-narrator monologues.

**Why this priority**: Stories with multiple interacting characters feel unnatural and robotic when read by a single narrator. Delivering character-specific voices is the essential foundation for engaging cinematic dialogue.

**Independent Test**: Provide a prompt with at least two conversing characters. Verify that the generated plan assigns distinct speakers to dialogue lines, synthesizes each line with its assigned vocal persona, and plays distinct character voices sequentially.

**Acceptance Scenarios**:

1. **Given** a concept prompt describing an interaction between two or more characters, **When** the story plan is generated, **Then** each spoken dialogue line is explicitly tagged with a specific speaking character name and a corresponding vocal persona.
2. **Given** scene beats with different assigned speakers, **When** the video's audio is synthesized, **Then** each character speaks in their unique distinct vocal persona rather than a single unified voiceover track.
3. **Given** non-verbal or narrative-only scenes, **When** no character is speaking dialogue, **Then** the system gracefully omits dialogue or attributes ambient voiceover without forcing an artificial character voice.

---

### User Story 2 - Fluid Continuous Video Animation from Keyframe Anchors (Priority: P1)

When a creator approves a storyboard keyframe image, the video generation engine smoothly animates movement *directly from that approved image* across the scene's entire duration, ensuring smooth visual flow and optical motion rather than rapid strobe-like flashing of disconnected still images or premature freeze frames.

**Why this priority**: Rapid flashing of unrelated still images completely breaks viewer immersion and ruins visual quality. Continuous temporal video motion starting from approved artwork is the core promise of the studio.

**Independent Test**: Generate a video beat starting from an approved keyframe image. Verify that the output video preserves character appearance and environment from frame 0 and demonstrates continuous temporal movement across all frames without flashing or freezing before the scene concludes.

**Acceptance Scenarios**:

1. **Given** an approved storyboard keyframe image, **When** video synthesis executes, **Then** frame 0 matches the keyframe artwork, and subsequent frames animate smoothly from that visual state.
2. **Given** a scene beat of duration T seconds, **When** the video clip is synthesized, **Then** active visual motion continues for the full T seconds without holding on a static frozen frame while speech is still active.
3. **Given** sequential continuous shots within the same location, **When** transitioning from one beat to the next, **Then** character designs, costume, and lighting remain visually coherent between cuts.

---

### User Story 3 - Kinetic 4-Part Motion Prompting & Pacing Alignment (Priority: P2)

When translating narrative beats into motion directives, the system automatically deconstructs each beat into four distinct kinetic layers (primary subject action, secondary interaction, environmental physics, and camera movement). It aligns the motion duration strictly with spoken dialogue pacing so action and speech conclude in harmony.

**Why this priority**: Static prompts describing colors and textures lead video diffusion models to hallucinate random still images. Prompting explicitly for action vectors and matching duration ensures natural, cinematic pacing.

**Independent Test**: Inspect generated beat prompts to verify presence of subject action, secondary interaction, environmental dynamics, and camera kinetics. Verify that clip duration accommodates dialogue plus natural speech pauses.

**Acceptance Scenarios**:

1. **Given** an approved scene beat, **When** visual motion prompts are authored, **Then** the prompt explicitly defines primary character movement, secondary reactions, ambient environmental physics, and camera path.
2. **Given** a dialogue line lasting D seconds, **When** the scene beat duration is calculated, **Then** the duration equals D plus pre-roll and post-roll breathing room, and video rendering length matches this exact duration.

---

### User Story 4 - Interactive Speaker & Voice Direction in Web Studio (Priority: P2)

In the Web Studio visual interface, creators can see exactly which character is speaking on each storyboard card, preview and change individual character voice assignments, and modify camera motion directions before committing to synthesis.

**Why this priority**: Creators require directorial control over who speaks each line and how their characters sound without needing to write code or modify configuration files.

**Independent Test**: Open Web Studio, verify character attribution badges appear on beat cards, change a character's assigned voice, click approve, and verify the resulting video reflects the user-selected voice.

**Acceptance Scenarios**:

1. **Given** a generated storyboard in Web Studio, **When** viewing any scene beat with spoken dialogue, **Then** a visible speaker badge identifies the active character and their assigned voice persona.
2. **Given** a creator wanting to change a character's vocal style, **When** selecting an alternative voice from the card's persona options, **Then** the updated voice is saved and used for subsequent synthesis of that specific character.

---

### Edge Cases

- **Fast-Paced Dialogue**: What happens when multiple characters speak in rapid succession within a single 5-second scene beat? The system must support sequential speaker segments within a single beat or split them into sub-beat audio cues with exact start and end offsets.
- **Narrative Without Spoken Dialogue**: What happens when a scene has ambient sound effects but no character dialogue? The system marks dialogue as null and allocates full scene duration to environmental soundscapes and camera movement.
- **Extreme Emotion/Screaming**: What happens when a character's dialogue expresses extreme laughter, shouting, or whispering? The voice persona modulation parameters (rate, pitch, inflection) must reflect the emotional tone indicated in the script.
- **Mismatched Audio and Video Durations**: What happens if video generation completes slightly shorter or longer than spoken audio? The master compositor must gracefully adapt playback speed or extend ambient scene padding without abrupt cuts or frozen frames.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST identify distinct speaking characters and assign each dialogue line to a specific character during story generation.
- **FR-002**: System MUST assign a unique, genre- and role-appropriate vocal persona to each distinct character in the story plan.
- **FR-003**: System MUST synthesize spoken audio on a per-scene basis using the specific character's assigned vocal persona.
- **FR-004**: System MUST anchor video generation to approved storyboard keyframe images so that frame 0 starts from the approved artwork.
- **FR-005**: System MUST generate temporal video motion across time using continuous video latent structures rather than independent 2D image batches.
- **FR-006**: System MUST structure scene video prompts into four explicit kinetic components: primary subject action, secondary interaction, environmental physics, and camera movement.
- **FR-007**: System MUST synchronize the duration of each video clip with the duration of the corresponding spoken dialogue plus natural conversational pauses.
- **FR-008**: System MUST display speaker attribution badges and editable voice selectors on each storyboard card in Web Studio.
- **FR-009**: System MUST allow users to reassign character voice personas per card prior to initiating final video synthesis.
- **FR-010**: System MUST maintain visual character and environment consistency across sequential beats through shot continuity chaining.
- **FR-011**: System MUST generate word-level kinetic subtitle timestamps corresponding to the multi-speaker dialogue track.
- **FR-012**: System MUST assemble final compositions with synchronized multi-character dialogue, background score, and sound effects without freezing on terminal frames.

### Key Entities

- **Character Profile**: Represents a distinct narrative actor with a name, role, visual description, gender/age archetype, and assigned vocal persona.
- **Scene Beat**: Represents a sequential shot containing visual prompt, camera kinetics, duration, assigned speaker, dialogue line, keyframe artwork, and rendered video clip.
- **Vocal Persona**: Represents an audio synthesis profile defining language, gender, pitch modulation, speech rate, and emotional tone.
- **Continuity Link**: Represents the optical bridge connecting sequential shots, ensuring character and environmental fidelity across camera cuts.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of generated scene dialogue lines are explicitly attributed to a named character rather than an anonymous narration block.
- **SC-002**: Multi-character stories play with at least two acoustically distinct vocal personas across sequential dialogue turns.
- **SC-003**: 100% of rendered video beats display continuous optical motion across all frames with zero rapid strobe/shutter flickering of disconnected still images.
- **SC-004**: Zero video beats experience frozen terminal frames exceeding 0.5 seconds while spoken dialogue is active.
- **SC-005**: Users in Web Studio can customize any scene's character voice actor in under two clicks with immediate visual feedback.

## Assumptions

- Stories may feature between one and six distinct speaking characters within a single video project.
- Visual generation services support both initial-image-conditioned video synthesis and pure text-conditioned video synthesis.
- Vocal synthesis services provide a sufficient catalog of male, female, comedic/cartoon, and emotional voices to differentiate characters.
- Audio synchronization tolerance between dialogue and subtitle word highlights is within 100 milliseconds.
