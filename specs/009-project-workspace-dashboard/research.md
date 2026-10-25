# Research: Project Workspace Management, Dedicated Dashboard & Multi-Take History

## Technical Unknowns & Decisions

### 1. Project Storage & Encapsulation Layout

- **Decision**: Store all new projects in dedicated directories under `outputs/projects/{project_id}/`, separating lightweight metadata from binary media.
- **Rationale**: Currently, `outputs/temp/` holds over 250+ loose files from 59 sessions without isolation. A dedicated folder per project makes deletion, export, backup, and take organization clean and safe with zero file collisions.
- **Alternatives Considered**:
  - *SQLite Database for metadata*: Adds an extra dependency and migration overhead, whereas JSON files on disk (`project.json`) match the existing `session_manager.py` pattern, are human-readable, and gitignore-friendly.
  - *Single monolithic archive (zip)*: Inefficient for live video streaming and frame extraction.
  - *Keeping flat `outputs/temp/`*: Rejected because it overwrites clips on re-render and mixes all assets.

### 2. Backward Compatibility with Existing 59 Sessions

- **Decision**: Implement a unified `ProjectManager` that scans both `outputs/projects/` (new format) and `outputs/temp/sessions/` (legacy format).
- **Rationale**: The user has 59 existing sessions. If a user selects a legacy session from the dashboard, it opens seamlessly without requiring a destructive batch migration. When an existing project is updated or saved, it can optionally be migrated or updated in place.
- **Alternatives Considered**:
  - *Hard migration script on startup*: Risky if an existing session JSON is malformed or if migration fails mid-way.
  - *Ignoring legacy sessions*: Violates zero data loss requirement.

### 3. Multi-Take Architecture for Scene Beats

- **Decision**: Introduce a `RenderTake` schema on each beat:
  ```python
  class RenderTake(BaseModel):
      take_id: str
      take_index: int
      video_path: str
      created_at: str
      prompt: str
      backend: str
      duration_sec: float
  ```
  Each beat keeps `takes: List[RenderTake]` and `active_take_id: Optional[str]`. The existing `output_video_path` field remains synchronized to the active take's video path.
- **Rationale**: Completely backwards compatible with Remotion player, master compilation, and frame chaining. All downstream consumers read `beat.output_video_path` as before, but the user gains full take history (Take 1, Take 2, etc.) and can switch between takes at will.
- **Alternatives Considered**:
  - *Storing separate branches of the entire project per take*: Too heavy; users just want to audition takes for specific scenes/beats.
  - *Overwriting files with backups (e.g. .bak)*: Cluttered and error-prone.

### 4. Frontend View Management & Routing

- **Decision**: State-driven view switching (`currentView: 'dashboard' | 'studio'`) synchronized with URL query parameter (`?project={id}`).
- **Rationale**: Fast, zero-dependency, works seamlessly with existing Vite + React 19 configuration without introducing heavy router packages. Deep-linking allows refreshing the browser inside a project to stay in that project.
- **Alternatives Considered**:
  - *Adding `react-router-dom`*: Adds unnecessary bundle weight and requires wrapping the root component, risking compatibility issues with Remotion Player in React 19.

### 5. Media URL Serving & Asset Resolution

- **Decision**: Keep FastAPI static mounts (`/outputs` and `/cache`) as-is. Mount `outputs/projects` automatically under `/outputs/projects/`.
- **Rationale**: Browsers, Remotion, and video tags can stream media directly over HTTP via relative URLs (`/outputs/projects/{id}/media/clips/beat_0_take_1.mp4`).
