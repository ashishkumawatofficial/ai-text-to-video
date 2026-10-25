# API Contracts: Project Workspace Management & Multi-Take History

## Endpoints

### 1. `GET /api/projects`
Lists all available projects (both dedicated project workspaces and discovered legacy sessions).

#### Response (200 OK):
```json
[
  {
    "project_id": "proj_c8769d67-083a-4d60-9d20-4d6aeb7bd384",
    "title": "The Corporate Cow's Tea Break",
    "concept_prompt": "Four cows sitting at a roadside tea stall laughing...",
    "aspect_ratio": "16:9",
    "directing_mode": "pro",
    "status": "completed",
    "total_duration_sec": 21.0,
    "beat_count": 4,
    "completed_beats_count": 4,
    "total_takes_count": 7,
    "thumbnail_url": "/outputs/temp/keyframe_743d7cde0c2b.jpg",
    "master_video_path": "/outputs/c8769d67-083a-4d60-9d20-4d6aeb7bd384_master.mp4",
    "created_at": "2026-10-25T08:34:22.969822+00:00",
    "updated_at": "2026-10-25T10:52:41.076045+00:00",
    "is_legacy": false
  }
]
```

---

### 2. `POST /api/projects`
Initializes a new project workspace directory and default `project.json`.

#### Request Body:
```json
{
  "title": "Cyberpunk Tokyo Drift",
  "prompt": "Neon-lit cybernetic street racers speeding through Shinjuku rain",
  "aspect_ratio": "16:9",
  "directing_mode": "pro",
  "backend": "serverless",
  "voice_persona": "auto"
}
```

#### Response (201 Created):
```json
{
  "status": "created",
  "project_id": "proj_a1b2c3d4",
  "project": {
    "project_id": "proj_a1b2c3d4",
    "title": "Cyberpunk Tokyo Drift",
    "concept_prompt": "Neon-lit cybernetic street racers speeding through Shinjuku rain",
    "aspect_ratio": "16:9",
    "status": "draft",
    "beats": [],
    "chat_history": []
  }
}
```

---

### 3. `GET /api/projects/{project_id}`
Retrieves full project state by ID (compatible with `StudioSession`).

#### Response (200 OK):
Returns full `ProjectDetail` JSON matching the schema in `data-model.md`.

---

### 4. `PATCH /api/projects/{project_id}`
Updates project title or metadata.

#### Request Body:
```json
{
  "title": "Updated Title Here"
}
```

#### Response (200 OK):
```json
{
  "status": "updated",
  "project_id": "proj_a1b2c3d4",
  "title": "Updated Title Here"
}
```

---

### 5. `DELETE /api/projects/{project_id}`
Deletes the project and cleans up its isolated directory on disk.

#### Response (200 OK):
```json
{
  "status": "deleted",
  "project_id": "proj_a1b2c3d4"
}
```

---

### 6. `POST /api/projects/{project_id}/duplicate`
Duplicates an existing project into a new workspace with " (Copy)".

#### Response (201 Created):
```json
{
  "status": "duplicated",
  "original_project_id": "proj_a1b2c3d4",
  "new_project_id": "proj_e5f6g7h8",
  "new_title": "Cyberpunk Tokyo Drift (Copy)"
}
```

---

### 7. `POST /api/projects/{project_id}/beats/{beat_index}/active-take`
Switches which take is active for a beat.

#### Request Body:
```json
{
  "take_id": "take_2_9a8b"
}
```

#### Response (200 OK):
```json
{
  "status": "active_take_updated",
  "beat_index": 1,
  "active_take_id": "take_2_9a8b",
  "output_video_path": "/outputs/projects/proj_a1b2c3d4/media/clips/beat_1_take_2.mp4"
}
```
