# Feature Specification: Project Workspace Management, Dedicated Dashboard & Multi-Take History

**Feature Branch**: `009-project-workspace-dashboard`

**Created**: 2026-10-25

**Status**: Draft

**Input**: User description: "introduce project concept in our project, how complex it is to implement without affecting working functionality of project; maintain history when user renders clip 1 2 or more times (Option B); separate UI dashboard; test implementation in real time; project and its related files (metadata, media files) separated per project"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Dedicated Project Dashboard & Project Creation (Priority: P1)

As a creator, I want to arrive at a dedicated Project Dashboard that displays all my existing video projects in visual cards, so that I can easily browse past creations, review their status and duration, and launch into an existing or brand-new project.

**Why this priority**: Essential entry-point and hub for project-centric workflows. Without a dashboard, users are stuck in an ephemeral single-session interface where reloading the page loses sight of past work.

**Independent Test**: Can be tested independently by launching the application, verifying the dashboard loads displaying existing projects with visual thumbnails and metadata, creating a new project with a prompt and aspect ratio, and confirming it navigates smoothly into the editing workspace.

**Acceptance Scenarios**:

1. **Given** the application is opened without an active project query, **When** the home view loads, **Then** the user sees a full-screen Project Dashboard presenting all available projects in a responsive card grid.
2. **Given** existing projects exist, **When** viewed on the dashboard, **Then** each project card displays its title, concept prompt excerpt, aspect ratio badge, target duration, creation date, and a visual cover thumbnail extracted from the project's first scene keyframe.
3. **Given** a user is on the dashboard, **When** they click "New Project" and submit a title, initial concept prompt, and aspect ratio, **Then** a new project workspace is initialized and the user is transitioned directly into the editing studio for that project.
4. **Given** a user clicks on an existing project card, **When** selected, **Then** the studio workspace loads that project's complete storyboard, character dialogue, chat history, and rendered media without any missing state.

---

### User Story 2 - Isolated Per-Project Workspace & Asset Encapsulation (Priority: P1)

As a creator, I want every video project to maintain its own dedicated, isolated workspace folder that strictly separates lightweight project metadata from heavy binary media files, so that my projects never collide, corrupt each other, or pollute a shared temporary folder.

**Why this priority**: Core architectural guarantee of Option B. Prevents hundreds of loose video clips and images from mixing together in a flat folder, enabling clean project exports, backups, and safe deletions.

**Independent Test**: Can be tested independently by creating two distinct projects, rendering assets in both, and inspecting the file structure to verify that Project A's media and metadata reside strictly inside Project A's directory and Project B's media reside strictly inside Project B's directory.

**Acceptance Scenarios**:

1. **Given** a new project is created, **When** the project is initialized on disk, **Then** a dedicated directory is provisioned containing a clean `project.json` for metadata and structured subdirectories for keyframes, audio voiceovers, video takes, and compiled exports.
2. **Given** image keyframes, voiceovers, or video clips are generated for a project, **When** files are written, **Then** all generated assets are saved within that specific project's media subdirectories.
3. **Given** multiple distinct projects, **When** assets are generated across them, **Then** neither project can overwrite, reference, or alter the media assets of the other project.

---

### User Story 3 - Multi-Take Render History & Version Switching per Beat (Priority: P1)

As a director in the studio, when I re-render a specific narrative beat multiple times with different prompts or camera dynamics, I want the system to preserve every generation as a distinct "Take" (Take 1, Take 2, Take 3), so that I can compare variations, audition different takes, and switch which take is active without losing earlier good results.

**Why this priority**: Fulfills the explicit user requirement of Option B. Re-rendering a clip must never overwrite or delete previous renders, protecting user credits, compute time, and creative iterations.

**Independent Test**: Can be tested independently by rendering Scene Beat 1 once (producing Take 1), adjusting the prompt or camera movement, rendering Scene Beat 1 a second time (producing Take 2), and verifying that both video files exist, with an interactive selector allowing the user to switch between Take 1 and Take 2 for master timeline playback.

**Acceptance Scenarios**:

1. **Given** an approved scene beat on the storyboard canvas, **When** the user renders the beat for the first time, **Then** the clip is recorded as Take 1, marked as the active take, and made playable inline.
2. **Given** a scene beat that already has an existing render, **When** the user clicks "Render Beat" again, **Then** the new video is saved as a new take (e.g., Take 2) with its generation timestamp and prompt, without overwriting Take 1.
3. **Given** a beat with multiple recorded takes, **When** the user opens the take selector on the beat card, **Then** the user can preview each take independently and choose which take is set as active.
4. **Given** a specific take is selected as active for a beat, **When** the user plays the full master video or initiates master video compilation, **Then** the master sequence uses the currently active take for that beat.

---

### User Story 4 - Seamless Studio Navigation & Legacy Project Discovery (Priority: P2)

As a creator working in the studio workspace, I want clear navigation controls to return to the project dashboard or switch projects, and I want all my pre-existing past sessions to be automatically surfaced as projects, so that I experience zero loss of historical work.

**Why this priority**: Guarantees zero regression and continuous workflow. Creators must never feel trapped in a project or lose access to their pre-existing sessions.

**Independent Test**: Can be tested independently by clicking the "← Projects" navigation link from the studio header to return to the dashboard, verifying all 59 pre-existing legacy sessions appear on the dashboard, and opening a legacy session to verify its storyboard and media load seamlessly.

**Acceptance Scenarios**:

1. **Given** a user is inside the studio workspace, **When** they look at the studio top bar, **Then** a prominent "← Projects" button and an editable project title are clearly accessible.
2. **Given** a user clicks "← Projects", **When** invoked, **Then** the interface transitions back to the Project Dashboard while preserving the current project's saved state.
3. **Given** pre-existing legacy session files exist from earlier versions of the application, **When** the dashboard loads, **Then** the system automatically discovers and indexes these sessions, presenting them as playable, editable projects with their existing beats and master videos.

---

### User Story 5 - Project Lifecycle: Rename, Duplicate & Safe Deletion (Priority: P3)

As a creator, I want to rename my project, duplicate a project to try an alternative storyline branch, or delete an unwanted project along with its files, so that I can organize my video production catalog efficiently.

**Why this priority**: Fundamental project management ergonomics. Allows safe experimentation via duplication and prevents disk exhaustion via deletion.

**Independent Test**: Can be tested independently by renaming a project from the dashboard card or studio header, duplicating a project and verifying an independent clone is created, and deleting a test project to verify its directory is safely removed from disk.

**Acceptance Scenarios**:

1. **Given** a project on the dashboard or in the studio header, **When** the user edits the title, **Then** the project metadata updates immediately and reflects everywhere.
2. **Given** an existing project, **When** the user selects "Duplicate Project", **Then** a new project is created with a copy of the story plan, script, beats, and metadata with " (Copy)" appended to its title.
3. **Given** a project the user wishes to remove, **When** the user confirms deletion, **Then** the project entry is removed from the dashboard and its isolated directory is cleaned up.

---

### Edge Cases

- **In-flight Render during Project Switching**: If a user switches projects or navigates back to the dashboard while a serverless GPU job is rendering, the job continues processing in the background, updating the project's take history upon completion.
- **Corrupted or Incomplete Legacy Sessions**: If a legacy session file is missing required fields or has broken JSON syntax, the dashboard skips or flags it with a fallback "Unrecovered Project" card without crashing the entire dashboard.
- **Missing Media File References**: If a keyframe or clip file was deleted externally from the filesystem, the project loads gracefully, showing a placeholder with a "Re-render" button instead of breaking the UI.
- **Simultaneous Multiple Takes Generation**: The system queues or assigns distinct take identifiers to concurrent renders of the same beat, preventing race conditions or filename collisions.
- **Browser Refresh Preservation**: When refreshing the browser inside a project workspace, the application reads the project identifier from the URL and reopens the exact same project without kicking the user back to the dashboard.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide a Project Dashboard displaying all available video projects with cover thumbnail, title, prompt excerpt, aspect ratio, duration, and last updated time.
- **FR-002**: System MUST allow users to initialize a new project by specifying title, concept prompt, and target aspect ratio (16:9, 9:16, 1:1).
- **FR-003**: System MUST provide a dedicated directory for each project that completely isolates its assets from all other projects.
- **FR-004**: System MUST store lightweight project metadata (settings, beat descriptions, dialogue, director notes, take index) in a structured metadata file separate from binary media files.
- **FR-005**: System MUST organize project media into designated subdirectories for keyframes, audio tracks, video clips/takes, and compiled master videos.
- **FR-006**: System MUST record each video generation for a narrative beat as an independent take entity preserving timestamp, prompt, and output file reference.
- **FR-007**: System MUST track the currently active take for each narrative beat.
- **FR-008**: System MUST allow users to audition, preview, and switch the active take for any beat that has multiple recorded takes.
- **FR-009**: Master video compilation and timeline playback MUST always incorporate the currently active take of each beat.
- **FR-010**: System MUST automatically discover and display pre-existing legacy sessions on the Project Dashboard without requiring manual data conversion.
- **FR-011**: System MUST support renaming project titles both from the dashboard and directly inside the studio workspace header.
- **FR-012**: System MUST allow users to duplicate an existing project, generating a separate project with cloned metadata.
- **FR-013**: System MUST allow users to permanently delete a project and safely remove its isolated directory upon confirmation.
- **FR-014**: System MUST persist the active project reference in the browser URL, ensuring page reloads maintain the active project context.
- **FR-015**: System MUST provide a clear "← Projects" navigation action in the studio workspace to return to the Project Dashboard at any time.

### Key Entities

- **Project**: Represents a complete video production. Contains unique project ID, title, concept prompt, aspect ratio, directing mode, backend strategy, status (draft, in_progress, completed), created timestamp, updated timestamp, and collection of narrative beats.
- **RenderTake**: Represents a single video generation take of a narrative beat. Contains take ID, beat index, take index (1, 2, 3...), video media path, creation timestamp, prompt used, and duration.
- **NarrativeBeat (StoryboardCard)**: Represents a single sequential scene in the video. Contains beat index, visual prompt, camera motion, dialogue text, speaker, voice actor, active keyframe path, collection of render takes, and active take ID.
- **ProjectMetadata**: Encapsulates configuration settings, AI director chat history, reference assets, and timeline composition settings for a project.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can navigate between the Project Dashboard and any project's Studio Workspace in under 1 second.
- **SC-002**: 100% of pre-existing legacy sessions are automatically discovered and accessible from the Project Dashboard upon first launch.
- **SC-003**: Re-rendering a narrative beat preserves all previous takes with 0% data loss or accidental overwrites.
- **SC-004**: Deleting or modifying a project affects 0 files belonging to any other project.
- **SC-005**: Page refresh within an active project reloads the exact project workspace and beat states in 100% of test cases.

## Assumptions

- Users interact primarily through modern desktop web browsers capable of playing HTML5 H.264/MP4 video.
- All project data and media assets are stored locally within the application workspace outputs directory, with future extensibility for remote object storage.
- Legacy session files follow the established JSON schema found in `outputs/temp/sessions/`.
- Project deletion is an explicit user action requiring confirmation.
