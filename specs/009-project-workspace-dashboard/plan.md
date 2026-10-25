# Implementation Plan: Project Workspace Management, Dedicated Dashboard & Multi-Take History

**Branch**: `009-project-workspace-dashboard` | **Date**: 2026-10-25 | **Spec**: [specs/009-project-workspace-dashboard/spec.md](file:///Users/ashishkumavat/Projects/ai-text-to-video/specs/009-project-workspace-dashboard/spec.md)

**Input**: Feature specification from `specs/009-project-workspace-dashboard/spec.md`

## Summary

Introduce a first-class **Project Workspace** architecture into the AI Video Web Studio. The feature elevates the existing ephemeral sessions into isolated, persistent projects stored under `outputs/projects/{project_id}/` with complete separation between metadata (`project.json`) and media (`keyframes/`, `audio/`, `clips/`, `exports/`). It adds a dedicated, full-screen **Project Dashboard** for browsing, searching, and managing projects, alongside a **Multi-Take Engine** that records repeated renders of scene beats as distinct takes (`Take 1`, `Take 2`, etc.) with interactive in-studio auditioning and switching. Pre-existing legacy sessions are automatically discovered and surfaced on the dashboard without data loss.

## Technical Context

**Language/Version**: Python 3.10+ (Backend), TypeScript 5.7+ / React 19 (Frontend)  
**Primary Dependencies**: FastAPI, Pydantic v2, Lucide React, Remotion Player  
**Storage**: File-system JSON metadata (`project.json`), structured media directories under `outputs/projects/`  
**Testing**: pytest (Backend test suite), Vitest / React testing  
**Target Platform**: Web (Desktop Chrome / Safari / Firefox)  
**Project Type**: Full-stack web application (FastAPI backend + Vite/React frontend)  
**Performance Goals**: Dashboard index generation <300ms for 100+ projects; instantaneous view transition (<100ms)  
**Constraints**: 100% backward compatibility with existing `/api/storyboard/*`, `/api/render/*`, and `/api/director/*` endpoints; zero overwriting of previous takes on re-render  
**Scale/Scope**: Local workstation and cloud deployment, supports dozens of projects with multi-gigabyte video assets  

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] **Zero Regressions**: Existing `session_id`-based render pipelines (RunPod Serverless, ComfyUI Pod, Local Mock) remain functional without modification.
- [x] **File Isolation**: Each project encapsulates its own media and metadata without leaking into other projects.
- [x] **Backward Compatibility**: All 59 legacy session files are automatically discovered and editable.
- [x] **Testable & Measurable**: Quantitative validation scenarios defined in `quickstart.md`.

## Project Structure

### Documentation (this feature)

```text
specs/009-project-workspace-dashboard/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
│   └── api-contracts.md # REST API interface specification
└── tasks.md             # Phase 2 output (/speckit-tasks command)
```

### Source Code (repository root)

```text
core/
├── project_manager.py       # NEW: Project discovery, creation, take tracking & lifecycle
├── models.py                # ENHANCED: RenderTake, ProjectSummary, StoryboardCard with takes
├── server.py                # ENHANCED: /api/projects routes, multi-take render & active take routes
└── session_manager.py       # PRESERVED: Legacy session compatibility bridge

studio/src/
├── components/
│   ├── ProjectDashboard.tsx # NEW: Dedicated full-screen Project Dashboard & Cards grid
│   ├── TakeSwitcher.tsx     # NEW: Interactive Take auditioning and selector for beat cards
│   ├── BeatCard.tsx         # ENHANCED: Embedded TakeSwitcher and take status badges
│   └── DirectorSidebar.tsx  # ENHANCED: Dynamic project title binding
├── services/
│   └── api.ts               # ENHANCED: Project & take API client methods
├── styles/
│   └── studio.css           # ENHANCED: Dashboard cards, modal, and take switcher styles
└── App.tsx                  # ENHANCED: Top-level view routing (Dashboard <-> Studio) & URL sync

outputs/
├── projects/                # NEW: Dedicated isolated per-project storage
└── temp/                    # PRESERVED: Legacy flat files and sessions
```

**Structure Decision**: Web application layout integrating FastAPI in `core/` and React 19 in `studio/src/`. All user project media is stored exclusively in `outputs/projects/` keeping application source code clean.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|---|---|---|
| None | All additions follow existing architecture patterns (Pydantic models, JSON storage, React components) | N/A |
