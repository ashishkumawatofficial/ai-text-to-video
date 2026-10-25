# Data Model: Project Workspace Management, Dedicated Dashboard & Multi-Take History

## Entities & Schemas

### 1. ProjectSummary (Dashboard Item)
Represents a lightweight project overview returned when browsing the dashboard.

```typescript
interface ProjectSummary {
  project_id: string;              // Unique project ID (e.g., "proj_c8769d67" or legacy UUID)
  title: string;                   // Project title
  concept_prompt: string;          // Initial idea / prompt
  aspect_ratio: '16:9' | '9:16' | '1:1';
  directing_mode: 'auto' | 'pro';
  status: 'draft' | 'in_progress' | 'completed' | 'failed';
  total_duration_sec: number;
  beat_count: number;
  completed_beats_count: number;
  total_takes_count: number;
  thumbnail_url: string | null;    // URL to beat 0 keyframe or master thumbnail
  master_video_path: string | null;
  created_at: string;              // ISO timestamp
  updated_at: string;              // ISO timestamp
  is_legacy: boolean;              // True if originating from outputs/temp/sessions/
}
```

### 2. RenderTake
Represents a single video generation take for an individual scene beat.

```typescript
interface RenderTake {
  take_id: string;                 // Unique ID (e.g., "take_1_7a2f")
  beat_index: number;              // 0-indexed beat number
  take_index: number;              // 1-indexed sequential take number (Take 1, Take 2, etc.)
  video_path: string;              // URL or relative path to MP4 (/outputs/projects/...)
  prompt: string;                  // Exact visual prompt used for this take
  camera_motion: string;           // Camera motion preset
  backend: 'serverless' | 'pod' | 'local';
  duration_sec: number;            // Clip duration in seconds
  created_at: string;              // ISO timestamp
}
```

### 3. StoryboardCard (Narrative Beat - Enhanced)
Extends the existing beat card model with take history while preserving backward compatibility.

```typescript
interface StoryboardCard {
  beat_id: string;
  beat_index: number;
  visual_prompt: string;
  keyframe_path: string | null;
  speaker?: string;
  dialogue_text: string;
  voice_actor: string;
  camera_motion: string;
  duration_seconds: number;
  duration_frames: number;
  render_status: 'pending' | 'in_queue' | 'rendering' | 'completed' | 'failed';
  
  // Multi-Take Management
  active_take_id: string | null;   // ID of the currently selected take
  takes: RenderTake[];             // Complete history of all rendered takes for this beat
  output_video_path: string | null;// Points to active_take.video_path (100% backward compatible!)

  is_custom_image?: boolean;
  is_chained?: boolean;
  chained_from_beat?: number | null;
  chain_out_of_sync?: boolean;
  error_message?: string | null;
}
```

### 4. ProjectDetail (Full Project Workspace)
Complete serialized representation stored on disk in `outputs/projects/{project_id}/project.json` and consumed by the Studio UI.

```typescript
interface ProjectDetail {
  project_id: string;
  title: string;
  concept_prompt: string;
  aspect_ratio: '16:9' | '9:16' | '1:1';
  directing_mode: 'auto' | 'pro';
  backend_strategy: 'serverless' | 'pod' | 'local';
  voice_persona: string;
  status: 'draft' | 'in_progress' | 'completed' | 'failed';
  beats: StoryboardCard[];
  chat_history: ChatMessage[];
  telemetry?: TelemetryState;
  master_video_path: string | null;
  created_at: string;
  updated_at: string;
}
```

## Storage Directory Layout

```text
outputs/
├── projects/
│   └── proj_5a4d7a96_squirrel/
│       ├── project.json             <-- ProjectDetail metadata
│       └── media/
│           ├── keyframes/           <-- keyframe_beat_0.jpg, keyframe_beat_1.jpg
│           ├── audio/               <-- vo_beat_0.mp3, vo_beat_1.mp3
│           ├── clips/               <-- beat_0_take_1.mp4, beat_0_take_2.mp4
│           └── exports/             <-- master_SquirrelStory_1080p.mp4
│
└── temp/                            <-- Preserved for legacy session access
    └── sessions/                    <-- 59 legacy session JSON files
```

## State Transitions

### Beat Render Take Flow
```
[Beat in Pending/Ready]
       │
       ▼  User triggers "Render Beat"
[Status: rendering]
       │
       ▼  RunPod Serverless / Pod returns video MP4
[Generate RenderTake (take_index = len(takes) + 1)]
       │
       ▼
[Save to media/clips/beat_{idx}_take_{take_idx}.mp4]
       │
       ▼
[takes.append(new_take)]
[active_take_id = new_take.take_id]
[output_video_path = new_take.video_path]
[render_status = 'completed']
       │
       ▼
[Save project.json]
```

### Take Switching Flow
```
User clicks "Take 1" from Take Switcher
       │
       ▼
[Find take in beat.takes where take_id == target]
       │
       ▼
[active_take_id = target.take_id]
[output_video_path = target.video_path]
       │
       ▼
[Update project.json]
[Remotion Player updates active clip preview]
```
