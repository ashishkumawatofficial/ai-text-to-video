import type { RenderTake, ProjectSummary, CreateProjectParams } from '../types/project';

export interface StoryboardCard {
  beat_id: string;
  beat_index: number;
  image_prompt?: string;
  motion_prompt?: string;
  visual_prompt: string;
  keyframe_path: string | null;
  speaker?: string;
  dialogue_text: string;
  voice_actor: string;
  camera_motion: string;
  duration_seconds: number;
  duration_frames: number;
  render_status: 'pending' | 'in_queue' | 'rendering' | 'completed' | 'failed';
  output_video_path: string | null;
  active_take_id?: string | null;
  takes?: RenderTake[];
  edited_by_ai?: boolean;
  is_custom_image?: boolean;
  is_chained?: boolean;
  chained_from_beat?: number | null;
  chain_out_of_sync?: boolean;
  error_message?: string | null;
}

export interface ChatMessage {
  message_id: string;
  sender: 'user' | 'director_ai';
  text: string;
  timestamp: string;
  applied_delta?: any;
}

export interface TelemetryWorkerTile {
  worker_id: string;
  beat_index: number;
  status: string;
  elapsed_seconds: number;
  progress_percent: number;
}

export interface TelemetryState {
  total_workers: number;
  active_workers: number;
  elapsed_seconds: number;
  estimated_cost_usd: number;
  worker_tiles: TelemetryWorkerTile[];
}

export interface StudioSession {
  session_id: string;
  title?: string;
  concept_prompt: string;
  aspect_ratio: '16:9' | '9:16' | '1:1';
  directing_mode: 'auto' | 'pro';
  backend_strategy: 'serverless' | 'pod' | 'local';
  beats: StoryboardCard[];
  chat_history: ChatMessage[];
  telemetry?: TelemetryState;
  master_video_path?: string | null;
  project_location?: string | null;
  status: string;
}

export async function fetchHealth() {
  const res = await fetch('/api/health');
  if (!res.ok) throw new Error('Health check failed');
  return res.json();
}

export async function generateStoryboard(
  prompt: string,
  aspectRatio: string = '16:9',
  directingMode: string = 'pro',
  backend: string = 'serverless',
  voicePersona: string = 'auto'
): Promise<StudioSession> {
  const res = await fetch('/api/storyboard/generate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      prompt,
      aspect_ratio: aspectRatio,
      directing_mode: directingMode,
      backend,
      voice_persona: voicePersona,
    }),
  });
  if (!res.ok) throw new Error(`Storyboard generation failed: ${res.statusText}`);
  return res.json();
}

export async function rerollBeat(
  sessionId: string,
  beatIndex: number,
  promptOverride?: string,
  promptType: 'image' | 'motion' = 'image'
): Promise<StoryboardCard> {
  const res = await fetch('/api/storyboard/reroll', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      session_id: sessionId,
      beat_index: beatIndex,
      prompt_override: promptOverride,
      target_prompt_type: promptType,
    }),
  });
  if (!res.ok) throw new Error(`Re-roll failed: ${res.statusText}`);
  return res.json();
}

export async function uploadBeatImage(
  sessionId: string,
  beatIndex: number,
  file: File
): Promise<StoryboardCard> {
  const formData = new FormData();
  formData.append('session_id', sessionId);
  formData.append('beat_index', beatIndex.toString());
  formData.append('file', file);

  const res = await fetch('/api/storyboard/upload-image', {
    method: 'POST',
    body: formData,
  });
  if (!res.ok) throw new Error(`Image upload failed: ${res.statusText}`);
  return res.json();
}

export async function sendDirectorChat(
  sessionId: string,
  message: string
): Promise<{ reply: string; applied_delta: any; updated_beats: StoryboardCard[]; session: StudioSession }> {
  const res = await fetch('/api/director/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      session_id: sessionId,
      message,
    }),
  });
  if (!res.ok) throw new Error(`Chat failed: ${res.statusText}`);
  return res.json();
}

export interface UpdateBeatParams {
  sessionId: string;
  beatIndex: number;
  speaker?: string;
  voicePersona?: string;
  dialogueText?: string;
  visualPrompt?: string;
  imagePrompt?: string;
  motionPrompt?: string;
  cameraMotion?: string;
}

export async function updateStoryboardBeat(params: UpdateBeatParams): Promise<{ status: string; session_id: string; beat: StoryboardCard }> {
  const res = await fetch('/api/storyboard/beat', {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      session_id: params.sessionId,
      beat_index: params.beatIndex,
      speaker: params.speaker,
      voice_persona: params.voicePersona,
      dialogue_text: params.dialogueText,
      visual_prompt: params.visualPrompt,
      image_prompt: params.imagePrompt,
      motion_prompt: params.motionPrompt,
      camera_motion: params.cameraMotion,
    }),
  });
  if (!res.ok) throw new Error(`Beat update failed: ${res.statusText}`);
  return res.json();
}

export async function startRender(sessionId: string, backend: string = 'serverless') {
  const res = await fetch('/api/render/start', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      session_id: sessionId,
      backend,
    }),
  });
  if (!res.ok) throw new Error(`Render dispatch failed: ${res.statusText}`);
  return res.json();
}

export async function cancelRender(sessionId: string) {
  const res = await fetch('/api/render/cancel', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: sessionId }),
  });
  if (!res.ok) throw new Error(`Render cancellation failed: ${res.statusText}`);
  return res.json();
}

export async function renderBeat(sessionId: string, beatIndex: number, backend?: string) {
  const res = await fetch('/api/render/beat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      session_id: sessionId,
      beat_index: beatIndex,
      backend,
    }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Render beat failed: ${res.statusText}`);
  }
  return res.json();
}

export async function chainFrame(sessionId: string, sourceBeatIndex: number) {
  const res = await fetch('/api/storyboard/chain-frame', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      session_id: sessionId,
      source_beat_index: sourceBeatIndex,
    }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Chain frame failed: ${res.statusText}`);
  }
  return res.json();
}

export async function unlinkChain(sessionId: string, beatIndex: number) {
  const res = await fetch('/api/storyboard/unlink-chain', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      session_id: sessionId,
      beat_index: beatIndex,
    }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Unlink chain failed: ${res.statusText}`);
  }
  return res.json();
}

export async function compileMaster(sessionId: string, allowPartial: boolean = false) {
  const res = await fetch('/api/render/compile', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      session_id: sessionId,
      allow_partial: allowPartial,
    }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Master compilation failed: ${res.statusText}`);
  }
  return res.json();
}

export function subscribeToTelemetry(onTelemetry: (t: TelemetryState) => void): () => void {
  const source = new EventSource('/api/events');
  source.addEventListener('telemetry', (e: MessageEvent) => {
    try {
      const data = JSON.parse(e.data);
      onTelemetry(data);
    } catch (err) {
      console.error('Failed to parse SSE telemetry:', err);
    }
  });

  return () => {
    source.close();
  };
}

// --- Project Workspace & Take History API ---

export async function fetchProjects(): Promise<ProjectSummary[]> {
  const res = await fetch('/api/projects');
  if (!res.ok) throw new Error(`Failed to fetch projects: ${res.statusText}`);
  return res.json();
}

export async function createProject(params: CreateProjectParams): Promise<StudioSession> {
  const res = await fetch('/api/projects', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Failed to create project: ${res.statusText}`);
  }
  const data = await res.json();
  return data.project || data;
}

export async function getProject(projectId: string): Promise<StudioSession> {
  const res = await fetch(`/api/projects/${projectId}`);
  if (!res.ok) throw new Error(`Failed to load project ${projectId}: ${res.statusText}`);
  return res.json();
}

export async function updateProject(
  projectId: string,
  title?: string,
  prompt?: string
): Promise<StudioSession> {
  const res = await fetch(`/api/projects/${projectId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title, prompt }),
  });
  if (!res.ok) throw new Error(`Failed to update project: ${res.statusText}`);
  return res.json();
}

export async function deleteProject(projectId: string): Promise<{ status: string; project_id: string }> {
  const res = await fetch(`/api/projects/${projectId}`, {
    method: 'DELETE',
  });
  if (!res.ok) throw new Error(`Failed to delete project: ${res.statusText}`);
  return res.json();
}

export async function duplicateProject(projectId: string): Promise<StudioSession> {
  const res = await fetch(`/api/projects/${projectId}/duplicate`, {
    method: 'POST',
  });
  if (!res.ok) throw new Error(`Failed to duplicate project: ${res.statusText}`);
  const data = await res.json();
  return data.project || data;
}

export async function setActiveTake(
  projectId: string,
  beatIndex: number,
  takeId: string
): Promise<{ status: string; beat_index: number; active_take_id: string; output_video_path: string }> {
  const res = await fetch(`/api/projects/${projectId}/beats/${beatIndex}/active-take`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ take_id: takeId }),
  });
  if (!res.ok) throw new Error(`Failed to set active take: ${res.statusText}`);
  return res.json();
}

export async function revealProjectFolder(projectId: string): Promise<{ status: string; project_id: string }> {
  const res = await fetch(`/api/projects/${projectId}/reveal-folder`, {
    method: 'POST',
  });
  if (!res.ok) throw new Error(`Failed to reveal project folder: ${res.statusText}`);
  return res.json();
}

export async function pickDirectory(): Promise<string | null> {
  const res = await fetch('/api/filesystem/pick-directory', {
    method: 'POST',
  });
  if (!res.ok) throw new Error(`Failed to open folder picker: ${res.statusText}`);
  const data = await res.json();
  return data.selected_path || null;
}



