# Feature Specification: Iterative Shot Chaining & Single-Beat Rendering in Pro Director

**Feature Branch**: `008-iterative-shot-chaining`

**Created**: 2026-10-25

**Status**: Draft

**Input**: User description: "in pro director we should have option of user can render first clip than if he find it correct then he render next and so on and final video. this opens many options and control for the user like user can capture the last frame of clip and can use the first frame for the next clip and so on."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Single-Beat Video Synthesis (Priority: P1)

As a creator using Pro Director mode, I want to trigger video rendering for a single specific narrative beat on the storyboard canvas, so that I can evaluate the visual quality and motion dynamics of that shot in isolation without having to commit resources to rendering the rest of the project.

**Why this priority**: Essential foundation of the step-by-step workflow. Without individual beat rendering, creators are forced to render all beats at once, incurring avoidable compute expense and making iterative refinement impractical.

**Independent Test**: Can be tested independently by planning a 3-beat storyboard, clicking "Render Beat" on Shot 1 only, verifying Shot 1 renders and becomes playable inline while Shots 2 and 3 remain untouched in their pending state.

**Acceptance Scenarios**:

1. **Given** an approved or edited storyboard in Pro Director mode, **When** the user clicks "Render Beat" on a specific card, **Then** only that selected beat begins rendering while all other beat cards remain in their current state.
2. **Given** an individual beat render is in progress, **When** the video generation completes, **Then** the card displays an inline video player that automatically previews the finished clip, updates its badge to "Ready", and stores the clip output.
3. **Given** a user inspects a rendered beat clip and wants to refine the camera motion, prompt, or character voice, **When** they update the beat and click "Render Beat" again, **Then** only that card re-renders without invalidating other completed clips.

---

### User Story 2 - Tail-to-Head Frame Chaining Across Consecutive Shots (Priority: P1)

As a creator who has successfully rendered and approved a scene clip, I want to capture the exact final frame of that clip and assign it as the initial starting frame of the next consecutive scene, so that the transition between the two shots has seamless visual continuity and zero jump cuts.

**Why this priority**: Solves the fundamental continuity problem in AI filmmaking where character faces, wardrobe, lighting, and camera positions randomly reset across cuts. Chaining the terminal frame guarantees physical and optical continuity.

**Independent Test**: Can be tested independently by rendering Shot 1, clicking "Chain to Next Shot", confirming Shot 2's starting image updates to the exact ending frame of Shot 1, and rendering Shot 2 to verify that the start of Shot 2 seamlessly matches the end of Shot 1.

**Acceptance Scenarios**:

1. **Given** a beat card with a completed video clip, **When** the user clicks "Chain to Next Shot", **Then** the system extracts the exact final frame from the video clip and sets it as the starting image and keyframe preview of the next consecutive beat.
2. **Given** a beat has received a chained frame from the preceding shot, **When** viewed on the storyboard canvas, **Then** the card displays a prominent "Chained from Shot K" badge to clearly communicate the visual link.
3. **Given** a chained beat, **When** the user clicks "Render Beat", **Then** the video generator uses the chained image as its initial visual anchor, creating seamless motion continuity from the preceding clip.

---

### User Story 3 - Selective Unlinking & Chain Overrides (Priority: P2)

As a creator, I want the freedom to unlink a chained frame, replace it with a fresh keyframe or custom upload, or update the chained frame if an earlier clip was re-rendered, so that I maintain complete artistic flexibility over when to maintain continuity versus when to perform a hard visual cut.

**Why this priority**: Filmmakers occasionally require hard cuts, scene jumps, or fresh perspectives. Users must not be locked into an automatic chain if the narrative calls for a scene transition or location change.

**Independent Test**: Can be tested independently by chaining Shot 1 to Shot 2, clicking "Unlink Chain", and verifying Shot 2 returns to its independent keyframe without affecting Shot 1.

**Acceptance Scenarios**:

1. **Given** a beat that is currently chained to a previous shot, **When** the user clicks "Unlink Chain", **Then** the chain link is removed and the beat returns to its original standalone keyframe.
2. **Given** Shot 1 is re-rendered with new motion or styling while Shot 2 is already chained, **When** Shot 1 finishes, **Then** Shot 2 displays an alert indicating that its chained anchor is out of sync, with an option to "Update Chained Frame".
3. **Given** a chained beat, **When** the user uploads a custom image or clicks "Re-roll Keyframe", **Then** the user is informed that this replaces the chained frame with a custom anchor.

---

### User Story 4 - Master Video Compilation from Individually Rendered Clips (Priority: P1)

As a creator who has iteratively rendered and approved individual clips across the storyboard, I want to compile all clips into a finalized master video with synchronized character dialogue, background music, audio ducking, and kinetic subtitles, without having to re-render the video clips.

**Why this priority**: Completes the end-to-end production loop. Allows creators to inspect and polish each clip step-by-step, then assemble the final export in seconds.

**Independent Test**: Can be tested independently by rendering 3 separate beat clips, clicking "Compile Master Video", and verifying that a complete stitched video with audio dialogue, sound effects, and kinetic subtitles plays in the studio player.

**Acceptance Scenarios**:

1. **Given** all narrative beats have completed video clips, **When** the user clicks "Compile Master Video", **Then** the system stitches the clips in sequential order, synchronizes the multi-speaker audio tracks, overlays sound effects, generates word-by-word kinetic subtitles, and presents the master 1080p video in the Live Studio Player.
2. **Given** some beats remain unrendered when compilation is requested, **When** the user clicks "Compile Master Video", **Then** the system provides clear options to either automatically render remaining beats or compile only the currently completed segments as a work-in-progress preview.
3. **Given** a compiled master video, **When** the user clicks "Export Master 1080p MP4", **Then** the file downloads cleanly with all visual and audio elements preserved.

---

### Edge Cases

- **Corrupted / Empty Video Output**: What happens if an individual clip render fails or yields a 0-byte file? The system must mark the card as failed, display a clear error message with a retry option, and prevent the user from chaining an empty or nonexistent frame.
- **Upstream Re-renders**: What happens if the creator re-renders Beat 1 after Beat 2 and Beat 3 have already been chained and rendered? The system must warn the user that downstream clips were generated from an earlier version of Beat 1's final frame, allowing the user to either keep the existing clips or re-render the chain.
- **Pacing & Duration Mismatches**: What happens if the rendered clip duration differs slightly from the spoken dialogue duration? The system must automatically ensure the video covers the full duration of the spoken audio so dialogue is never cut off.
- **Terminal Beat Chaining**: What happens on the final shot of the storyboard? The "Chain to Next Shot" button must be disabled or hidden on the last beat since there is no subsequent shot to link.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide an interactive "Render Clip" button on each individual storyboard beat card in Pro Director mode.
- **FR-002**: System MUST support independent single-beat video generation without triggering batch rendering of any other scene beats in the project.
- **FR-003**: System MUST embed an inline video player within each beat card to preview and play back the individual clip as soon as rendering completes.
- **FR-004**: System MUST provide an action on completed beat cards to extract the exact final frame (terminal frame) of that clip.
- **FR-005**: System MUST bind the extracted terminal frame as the starting visual anchor (`START_FRAME`) and keyframe preview of the immediate next beat.
- **FR-006**: System MUST visibly mark chained beats on the canvas with a continuity badge indicating the source shot (e.g., "Chained from Shot 1").
- **FR-007**: System MUST allow creators to unlink a chained frame and revert to an independent keyframe or upload custom artwork.
- **FR-008**: System MUST provide a "Compile Master Video" action that stitches existing rendered scene clips with synthesized character dialogue, sound effects, background music, and kinetic subtitles without re-rendering existing video clips.
- **FR-009**: System MUST support single-beat rendering across all configured inference backends (Serverless Cloud GPUs, Dedicated Pods, and Local Mock).
- **FR-010**: System MUST track individual render states per card (`pending`, `rendering`, `completed`, `failed`) and persist these states across browser refreshes.

### Key Entities

- **Storyboard Card / Beat**: Represents an individual shot in the storyboard, holding visual prompts, dialogue, camera movements, render status, keyframe image, and output video clip.
- **Continuity Link**: The metadata linking consecutive shots, storing whether a shot is chained, the source shot index, and the file path of the extracted terminal frame.
- **Master Video Composition**: The assembled project timeline that aggregates all individual scene clips, synchronized dialogue audio, background score, and word-level subtitle tokens into the final exportable MP4.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Creators can render an individual beat clip in under 90 seconds on Serverless GPU or under 5 seconds in Local Mock mode without triggering any other scenes.
- **SC-002**: 100% optical continuity between chained consecutive shots: the starting frame of clip $K+1$ matches the ending frame of clip $K$ with zero visual jump cuts.
- **SC-003**: Zero wasted compute credits: Creators can review, approve, or discard shot $K$ before committing any GPU compute to shot $K+1$.
- **SC-004**: Final master video compilation from pre-rendered clips completes in under 15 seconds.
- **SC-005**: 100% of individual clip states and chained frame links persist accurately across studio session reloads.

## Assumptions

- Users understand that chaining Shot $K$ to Shot $K+1$ requires Shot $K$ to be rendered first so that its final frame can be extracted.
- Video clips are rendered in standard H.264 MP4 format with accessible frame indices.
- When compiling the master video, existing completed clips are utilized directly without re-encoding unless necessary for timescale or container normalization.
