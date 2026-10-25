# Feature Specification: 006 Web Studio Interface & AI Director Copilot

**Feature Branch**: `006-web-studio-interface`

**Created**: 2026-10-24

**Status**: Draft

**Input**: User description: "Localhost web studio interface supporting both 9:16 vertical and 16:9 widescreen formats, dual directing workflows (1-click autonomous generation and controlled parameter pro-director mode), conversational Gemini AI co-director chat window for real-time natural language script/beat modifications, embedded in-browser Remotion player with live scrubbing, and real-time RunPod serverless cloud worker telemetry with USD billing calculation."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Visual Storyboard Canvas & Parameter Controls (Priority: P1)

As a content creator or video director, I want a visual canvas on localhost that displays each narrative beat as an interactive visual card showing keyframe image preview, visual prompt, dialogue, camera motion, and duration, with controls for aspect ratio (`9:16` vs `16:9`), voiceover actor, and backend selection (`serverless` vs `pod`), so that I have complete creative oversight over my video production.

**Why this priority**: Forms the core visual foundation of the studio interface, eliminating the need to read raw terminal output or edit JSON files to inspect storyboard beats.

**Independent Test**: Can be tested independently by creating a project with a 4-beat script, confirming all beat cards render with keyframes, and verifying that modifying a beat prompt or aspect ratio updates the session state immediately.

**Acceptance Scenarios**:

1. **Given** a user navigates to the localhost studio interface, **When** they enter a concept prompt and select aspect ratio `16:9` or `9:16`, **Then** the canvas renders all generated narrative beats as visual cards with keyframe image previews, camera motion badges, dialogue, and audio indicators.
2. **Given** an existing storyboard session on canvas, **When** the user clicks "Re-roll Beat" on a specific card, **Then** only that single beat regenerates its visual keyframe and prompt without modifying or invalidating other beats in the project.
3. **Given** the canvas view, **When** the user toggles aspect ratio between `9:16` (Vertical Short) and `16:9` (Widescreen), **Then** the canvas framing and preview player adapt their dimensions dynamically.

---

### User Story 2 - Conversational Gemini AI Co-Director Chat Sidebar (Priority: P1)

As a creator, I want an embedded conversational chat window where I can give natural language directions to an AI Director (powered by Gemini), asking for changes like *"make scene 2 darker and add heavy rain"*, *"rewrite the dialogue to sound like a noir detective"*, or *"shorten the story to 3 beats"*, so that I can iteratively shape the story without manually retyping every parameter.

**Why this priority**: Enables fluid, creative human-AI collaboration, turning static storyboard editing into an intelligent conversational directing session.

**Independent Test**: Can be tested independently by typing a modification prompt in the chat window, verifying the AI understands the intent, and checking that the target beat card on the canvas updates its prompt/dialogue in real time.

**Acceptance Scenarios**:

1. **Given** an active storyboard session on canvas, **When** the user sends a message *"Make beat 2 more dramatic and raining"*, **Then** the AI co-director replies with a confirmation and surgically updates Beat 2's visual prompt on the canvas without altering beats 1, 3, or 4.
2. **Given** an active storyboard session, **When** the user sends *"Change the overall tone to suspenseful horror and regenerate dialogue"*, **Then** the AI updates the voiceover script across all beats and reflects changes on the cards.
3. **Given** any conversational modification, **When** the update is applied, **Then** a visible delta badge appears on modified cards indicating they have been updated by the AI co-director.

---

### User Story 3 - Dual Directing Modes (1-Click Auto vs Pro-Director Approval) (Priority: P2)

As a creator, I want the choice between two production workflows: a streamlined "1-Click Full Auto" mode that writes, plans, diffuses, and renders the master video without stopping, and a "Pro-Director Mode" where I inspect keyframes, approve beats, and trigger synthesis only when satisfied.

**Why this priority**: Accommodates both fast automated batch production (e.g. content creators making multiple daily shorts) and high-touch artistic projects requiring meticulous scene-by-scene approval.

**Independent Test**: Can be tested independently by running a prompt in 1-Click Auto mode and verifying a completed master video is produced with zero manual prompts, then running in Pro-Director mode and verifying rendering halts at the approval gate until the user clicks "Synthesize Video".

**Acceptance Scenarios**:

1. **Given** a concept prompt, **When** the user clicks "1-Click Generate (Full Auto)", **Then** the system autonomously plans beats, generates keyframes, renders video clips via the selected backend, and compiles the final video directly to the player.
2. **Given** a concept prompt, **When** the user clicks "Generate Storyboard (Pro Mode)", **Then** the system generates keyframes and halts at the canvas gate, enabling manual edits, re-rolls, or AI chat adjustments.
3. **Given** an approved storyboard in Pro-Director mode, **When** the user clicks "Synthesize Master Video", **Then** the system dispatches parallel rendering across the configured backend workers.

---

### User Story 4 - Live In-Browser Remotion Player & Serverless Telemetry (Priority: P2)

As a creator, I want an embedded video player powered by Remotion to scrub, preview, and play the final master video with word-by-word kinetic animated subtitles and audio-ducked background music, along with a real-time RunPod Serverless worker grid displaying active GPU states, elapsed seconds, and live USD billing calculation.

**Why this priority**: Closes the loop from creation to consumption, providing instant visual validation of the compiled video and complete transparency over cloud compute costs.

**Independent Test**: Can be tested independently by loading a completed project into the embedded player, scrubbing the timeline to verify 60fps subtitle/audio sync, and checking that the worker telemetry panel reflects active GPU jobs and calculated USD cost.

**Acceptance Scenarios**:

1. **Given** a finished video synthesis, **When** the user views the player panel, **Then** the video plays smoothly with synchronized kinetic subtitles, sound effects, and audio-ducked voiceover.
2. **Given** active cloud generation, **When** jobs are running on RunPod Serverless, **Then** the UI displays real-time worker tiles (`IN_QUEUE`, `IN_PROGRESS`, `COMPLETED`), individual elapsed timers, and a live aggregate cost meter in USD (e.g., `$0.052`).
3. **Given** an ongoing generation batch, **When** the user clicks "Cancel All", **Then** the system dispatches immediate cancellation requests to all active cloud jobs and resets worker states to avoid unnecessary billing.
4. **Given** a finished video, **When** the user clicks "Export MP4", **Then** the master 1080p video file downloads directly to the user's local machine.

---

### Edge Cases

- **Backend Offline / Unreachable**: If the serverless endpoint or local pod is offline when synthesis is requested, the UI must alert the user immediately with fallback options (`Local Mock` or `Dedicated Pod`) rather than freezing.
- **Aspect Ratio Shift Mid-Session**: If the user switches from `9:16` to `16:9` after keyframes are generated, the canvas must warn that existing keyframes will be reframed or allow re-generating keyframes for the new aspect ratio.
- **Long Script / Multi-Beat Scaling**: The storyboard canvas must support horizontal or grid scrolling cleanly when a video exceeds 6 narrative beats without breaking layout responsiveness.
- **Network / Job Disconnection**: If the browser tab is refreshed while serverless workers are rendering, the studio session must re-attach to the ongoing job IDs and resume live telemetry polling without restarting from scratch.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide a localhost web studio interface accessible via modern desktop web browsers.
- **FR-002**: System MUST support selecting both `9:16` (Vertical / Shorts / Reels) and `16:9` (Widescreen / Landscape) aspect ratios, with appropriate canvas dimensions and video resolution profiles.
- **FR-003**: System MUST display each storyboard beat as an editable visual card with keyframe image preview, visual prompt, dialogue, camera motion, audio duration, and individual beat status.
- **FR-004**: System MUST allow users to trigger single-beat re-rolls (`regenerate_beat`), updating only the selected scene without affecting neighboring beats.
- **FR-005**: System MUST provide an integrated AI Co-Director Chat sidebar powered by Gemini, allowing users to direct story changes via natural language messages.
- **FR-006**: System MUST parse conversational chat directions and apply surgical delta updates to specific storyboard beat cards, reflecting updates visually in real time.
- **FR-007**: System MUST support both "1-Click Full Auto" (unattended pipeline run) and "Pro-Director" (interactive canvas review and approval gate) execution modes.
- **FR-008**: System MUST integrate an embedded Remotion Player in the browser for smooth 60 FPS playback with timeline scrubbing, play/pause, and volume controls.
- **FR-009**: System MUST render word-by-word kinetic animated subtitles and audio-ducked background music in the live preview player.
- **FR-010**: System MUST display a real-time Cloud Worker Telemetry grid showing concurrent RunPod GPU statuses (`IN_QUEUE`, `IN_PROGRESS`, `COMPLETED`), elapsed time per worker, and total USD billing accumulation.
- **FR-011**: System MUST provide a prominent "Cancel All" button that immediately terminates all in-flight cloud serverless jobs to prevent orphaned GPU billing.
- **FR-012**: System MUST provide a one-click "Export MP4" button that renders or downloads the compiled 1080p master video to the local filesystem.

---

### Key Entities

- **`StudioSession`**: Represents the current active production workspace, containing session ID, concept prompt, selected aspect ratio, directing mode, backend strategy, narrative beats, and compilation state.
- **`StoryboardCard`**: Represents a single scene beat on the canvas, containing beat index, start keyframe URL/path, visual prompt text, dialogue voiceover text, camera motion type, duration in frames/seconds, and status (`PENDING`, `RENDERING`, `COMPLETED`, `FAILED`).
- **`CoDirectorChatMessage`**: Represents a message in the conversational director chat, containing message ID, sender (`user` vs `director_ai`), timestamp, message text, and optional target beat modification delta.
- **`RenderTelemetryState`**: Represents real-time cloud and local compute metrics, containing active worker count, per-worker job states, elapsed compute seconds, and cumulative USD cost calculation.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user can launch the studio on localhost, input a concept prompt, and view a fully planned visual storyboard canvas in under 15 seconds.
- **SC-002**: Applying a surgical beat edit via the Gemini AI Co-Director Chat updates the canvas card and keyframe in under 8 seconds.
- **SC-003**: In 1-Click Auto mode with Serverless backend, an entire 4-beat video is planned, diffused in parallel across 4 cloud GPUs, Remotion-compiled, and ready to play in under 3 minutes total.
- **SC-004**: The live cost meter accurately reports cumulative RunPod compute duration and dollar expense within ±$0.005 of actual cloud billing.
- **SC-005**: The in-browser player maintains smooth 60 FPS playback with zero dropped frames during kinetic subtitle animation.

---

## Assumptions

- **Host Environment**: The studio will run locally on the user's development machine (`http://localhost:3000` or `5173` for frontend, `http://localhost:8000` for Python FastAPI backend).
- **Backend Architecture**: The web frontend communicates with a local Python FastAPI service that imports and wraps existing core engines (`InteractiveDirector`, `RunPodServerlessClient`, `RemotionBridge`, `AudioEngine`).
- **API Keys**: Standard credentials configured in `.env` (`GEMINI_API_KEY`, `RUNPOD_API_KEY`, `RUNPOD_SERVERLESS_ENDPOINT_ID`) are automatically utilized by the studio backend without requiring re-entry in the browser.
- **Supported Browsers**: Modern evergreen browsers (Chrome, Edge, Safari, Firefox) with Web Audio API, Canvas, and HTML5 video support.
