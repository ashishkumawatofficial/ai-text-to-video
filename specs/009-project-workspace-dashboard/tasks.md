# Tasks: Project Workspace Management, Dedicated Dashboard & Multi-Take History

**Branch**: `009-project-workspace-dashboard` | **Spec**: [specs/009-project-workspace-dashboard/spec.md](file:///Users/ashishkumavat/Projects/ai-text-to-video/specs/009-project-workspace-dashboard/spec.md) | **Plan**: [specs/009-project-workspace-dashboard/plan.md](file:///Users/ashishkumavat/Projects/ai-text-to-video/specs/009-project-workspace-dashboard/plan.md)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Initialize directory structure and shared data models for projects and multi-take support.

- [x] T001 Create project workspace directory at `outputs/projects/` and verify `.gitignore` ignores all user project media in `.gitignore`
- [x] T002 [P] Define `RenderTake`, `ProjectSummary`, and updated `StoryboardCard` Pydantic models in `core/models.py`
- [x] T003 [P] Define TypeScript interfaces for `ProjectSummary`, `RenderTake`, and `ProjectDetail` in `studio/src/types/project.ts`

---

## Phase 2: Foundational (Blocking Core Services)

**Purpose**: Core project management service and foundational API routes required by all user stories.

**⚠️ CRITICAL**: No user story implementation can begin until this phase is complete.

- [x] T004 Implement `core/project_manager.py` with directory provisioning, `project.json` CRUD, and dual-scanner for `outputs/projects/` and legacy `outputs/temp/sessions/`
- [x] T005 [P] Implement API client methods for projects in `studio/src/services/api.ts` (`fetchProjects`, `createProject`, `getProject`, `updateProject`, `deleteProject`, `duplicateProject`, `setActiveTake`)
- [x] T006 Add core REST endpoints (`GET /api/projects`, `POST /api/projects`, `GET /api/projects/{project_id}`) in `core/server.py`

**Checkpoint**: Foundation ready — Project manager and basic CRUD endpoints operational.

---

## Phase 3: User Story 1 - Dedicated Project Dashboard & Project Creation (Priority: P1) 🎯 MVP

**Goal**: Provide creators with a full-screen Project Dashboard showing all projects with cover thumbnails, duration, status, and a "New Project" modal that launches directly into the studio workspace.

**Independent Test**: Load the root app in the browser, verify the dashboard renders with real project cards, create a new project with title and aspect ratio, and verify it transitions smoothly into the studio editor.

- [x] T007 [P] [US1] Create Project Dashboard styles in `studio/src/styles/studio.css` (responsive grid, glassmorphism cards, hover effects, status badges, modal backdrop)
- [x] T008 [P] [US1] Create `ProjectCard.tsx` component in `studio/src/components/ProjectCard.tsx` with cover thumbnail, aspect ratio badge, duration, and status indicators
- [x] T009 [US1] Create `NewProjectModal.tsx` component in `studio/src/components/NewProjectModal.tsx` with title, prompt, aspect ratio selector, and directing mode options
- [x] T010 [US1] Implement `ProjectDashboard.tsx` in `studio/src/components/ProjectDashboard.tsx` combining top search bar, status filter tabs, card grid, and new project modal
- [x] T011 [US1] Implement view-switching state (`currentView: 'dashboard' | 'studio'`) and URL search param synchronization (`?project=<id>`) in `studio/src/App.tsx`

**Checkpoint**: User Story 1 MVP is fully testable and operational. Creators can browse and create projects from the dashboard.

---

## Phase 4: User Story 2 - Isolated Per-Project Workspace & Asset Encapsulation (Priority: P1)

**Goal**: Guarantee that each project maintains its own isolated folder structure separating lightweight `project.json` from media (`keyframes/`, `audio/`, `clips/`, `exports/`), preventing asset collisions.

**Independent Test**: Create two projects and generate keyframes and audio in both; verify that each project's files reside strictly within `outputs/projects/<project_id>/` without leaking into shared folders.

- [x] T012 [US2] Implement isolated media directory layout (`media/keyframes/`, `media/audio/`, `media/clips/`, `media/exports/`) inside `core/project_manager.py`
- [x] T013 [US2] Update keyframe generation and audio voiceover saving in `core/server.py` to route file writes to the active project's media subdirectories
- [x] T014 [US2] Update master video compilation in `core/server.py` to save compiled MP4 into `outputs/projects/{project_id}/media/exports/`

**Checkpoint**: User Story 2 complete. Projects are completely self-contained and isolated.

---

## Phase 5: User Story 3 - Multi-Take Render History & Version Switching per Beat (Priority: P1)

**Goal**: Record every re-rendered clip of a scene beat as an independent `RenderTake` (Take 1, Take 2, etc.), provide an interactive switcher on each beat card, and compile the master video using active takes.

**Independent Test**: Render Beat 1 to produce Take 1, modify prompt and render Beat 1 again to produce Take 2; verify both takes exist, switch between them using the take switcher, and verify the video player and master compilation reflect the active take.

- [x] T015 [US3] Implement sequential take recording in `core/project_manager.py` to save clips as `media/clips/beat_{idx}_take_{take_idx}.mp4` and append to `beat.takes`
- [x] T016 [US3] Add `POST /api/projects/{project_id}/beats/{beat_index}/active-take` endpoint in `core/server.py` to update the active take selection
- [x] T017 [P] [US3] Implement `TakeSwitcher.tsx` component in `studio/src/components/TakeSwitcher.tsx` with auditioning buttons, take preview player, and active toggle
- [x] T018 [US3] Integrate `TakeSwitcher.tsx` into `studio/src/components/BeatCard.tsx` with take count badge and active take video binding
- [x] T019 [US3] Update master video compilation in `core/server.py` to dynamically assemble the active take of each scene beat

**Checkpoint**: User Story 3 complete. Full multi-take history is functional with zero data loss on re-render.

---

## Phase 6: User Story 4 - Seamless Studio Navigation & Legacy Project Discovery (Priority: P2)

**Goal**: Provide effortless navigation between Studio and Dashboard, and automatically discover all 59 existing legacy sessions so zero past work is lost.

**Independent Test**: Click "← Projects" in the studio header to return to the dashboard; confirm all 59 legacy sessions appear with titles and thumbnails, and open a legacy session to verify full state restoration.

- [x] T020 [US4] Add "← Projects" navigation link and in-header editable project title with auto-save in `studio/src/App.tsx`
- [x] T021 [US4] Implement legacy session adapter in `core/project_manager.py` scanning `outputs/temp/sessions/*.json` into `ProjectSummary`
- [x] T022 [US4] Add legacy session backward compatibility in `GET /api/projects/{id}` in `core/server.py` so legacy sessions load seamlessly into `StudioSession`

**Checkpoint**: User Story 4 complete. Full legacy continuity and effortless navigation.

---

## Phase 7: User Story 5 - Project Lifecycle: Rename, Duplicate & Safe Deletion (Priority: P3)

**Goal**: Enable creators to rename projects, duplicate projects to explore story branches, and safely delete projects along with their disk files.

**Independent Test**: Rename a project and verify persistence; duplicate a project and verify an independent clone is created; delete a project and verify its directory is removed.

- [x] T023 [US5] Add `PATCH /api/projects/{project_id}` endpoint in `core/server.py` for project title and metadata updates
- [x] T024 [US5] Add `POST /api/projects/{project_id}/duplicate` endpoint in `core/server.py` and `core/project_manager.py` to clone project state
- [x] T025 [US5] Add `DELETE /api/projects/{project_id}` endpoint in `core/server.py` and `core/project_manager.py` to safely delete project directory
- [x] T026 [US5] Implement card actions menu (Rename modal, Duplicate action, Delete confirmation dialog) in `studio/src/components/ProjectCard.tsx`

**Checkpoint**: User Story 5 complete. Full lifecycle management operational.

---

## Phase 8: Polish & Real-Time Validation

**Purpose**: Cross-cutting polish, performance check, and end-to-end verification.

- [x] T027 [P] Add empty state graphic and total project counter badge in `studio/src/components/ProjectDashboard.tsx`
- [x] T028 [P] Validate TypeScript compilation (`npm run build` or `tsc`) in `studio` and verify zero type errors
- [x] T029 Execute live validation scenarios from `specs/009-project-workspace-dashboard/quickstart.md` in browser

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: Can start immediately.
- **Foundational (Phase 2)**: Depends on Phase 1 completion — blocks all user stories.
- **User Story 1 (Phase 3)**: Depends on Phase 2. Delivers the core MVP dashboard.
- **User Story 2 (Phase 4)**: Depends on Phase 2. Delivers isolated project storage.
- **User Story 3 (Phase 5)**: Depends on Phase 4 (relies on isolated clips storage for takes).
- **User Story 4 (Phase 6)**: Depends on Phase 3 and Phase 2.
- **User Story 5 (Phase 7)**: Depends on Phase 3 and Phase 4.
- **Polish (Phase 8)**: Depends on completion of User Stories 1 through 5.

### Parallel Opportunities

- **Phase 1**: T002 (Python models) and T003 (TypeScript types) can execute in parallel.
- **Phase 3**: T007 (CSS styles) and T008 (`ProjectCard.tsx`) can execute in parallel.
- **Phase 5**: T017 (`TakeSwitcher.tsx`) can be developed in parallel with backend endpoints.
- **Phase 8**: T027 (Empty states) and T028 (TypeScript build validation) can execute in parallel.

---

## Implementation Strategy: MVP First

1. **Step 1**: Complete Phase 1 & Phase 2 (Data models & Core `project_manager.py`).
2. **Step 2**: Complete Phase 3 (User Story 1 - Dashboard & New Project flow).
   - **Validation Point (MVP)**: Open browser at `http://localhost:5173`, see Project Dashboard, create a project, and enter studio!
3. **Step 3**: Complete Phase 4 & Phase 5 (Isolated storage & Multi-Take history).
   - **Validation Point**: Re-render a scene beat twice, test Take 1 vs Take 2 switcher.
4. **Step 4**: Complete Phase 6 & Phase 7 (Navigation, legacy session discovery, rename, duplicate, delete).
5. **Step 5**: Run Phase 8 verification across all scenarios in `quickstart.md`.
