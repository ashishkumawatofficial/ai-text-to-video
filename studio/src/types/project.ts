export interface RenderTake {
  take_id: string;
  beat_index: number;
  take_index: number;
  video_path: string;
  prompt: string;
  camera_motion?: string;
  backend?: string;
  duration_sec?: number;
  created_at: string;
}

export interface ProjectSummary {
  project_id: string;
  title: string;
  concept_prompt: string;
  aspect_ratio: '16:9' | '9:16' | '1:1';
  directing_mode: 'auto' | 'pro';
  status: 'draft' | 'in_progress' | 'completed' | 'failed';
  total_duration_sec: number;
  beat_count: number;
  completed_beats_count: number;
  total_takes_count: number;
  thumbnail_url: string | null;
  master_video_path: string | null;
  project_location?: string | null;
  created_at: string;
  updated_at: string;
  is_legacy: boolean;
}

export interface CreateProjectParams {
  title: string;
  prompt: string;
  aspect_ratio?: '16:9' | '9:16' | '1:1';
  directing_mode?: 'auto' | 'pro';
  backend?: 'serverless' | 'pod' | 'local';
  voice_persona?: string;
  custom_location?: string;
}
