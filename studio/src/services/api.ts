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
  resolution?: string;
  model_id?: string;
  provider_override?: string;
  allow_provider_cascade?: boolean;
  modality?: string;
  native_audio?: boolean;
  has_clip_audio?: boolean;
  start_frame_path?: string | null;
  end_frame_path?: string | null;
  reference_image_paths?: string[];
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
  provider_id?: string;
  model_id?: string;
  api_status?: string;
  status_detail?: string;
  quoted_price_usd?: number;
}

export interface TelemetryState {
  total_workers: number;
  active_workers: number;
  elapsed_seconds: number;
  estimated_cost_usd: number;
  active_provider?: string;
  active_api_status?: string;
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
  voicePersona: string = 'auto',
  sessionId?: string
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
      session_id: sessionId,
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
  file: File,
  frameType: 'start_frame' | 'end_frame' | 'reference_image' = 'start_frame'
): Promise<StoryboardCard> {
  const formData = new FormData();
  formData.append('session_id', sessionId);
  formData.append('beat_index', beatIndex.toString());
  formData.append('frame_type', frameType);
  formData.append('file', file);

  const res = await fetch('/api/storyboard/upload-image', {
    method: 'POST',
    body: formData,
  });
  if (!res.ok) throw new Error(`Image upload failed: ${res.statusText}`);
  return res.json();
}

export async function removeBeatFrame(
  sessionId: string,
  beatIndex: number,
  frameType: 'start_frame' | 'end_frame' | 'reference_image' = 'start_frame',
  imageIndex?: number
): Promise<StoryboardCard> {
  const res = await fetch('/api/storyboard/remove-frame', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      session_id: sessionId,
      beat_index: beatIndex,
      frame_type: frameType,
      image_index: imageIndex,
    }),
  });
  if (!res.ok) throw new Error(`Remove frame failed: ${res.statusText}`);
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
  modelId?: string;
  providerOverride?: string;
  resolution?: string;
  modality?: string;
  nativeAudio?: boolean;
  allowProviderCascade?: boolean;
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
      model_id: params.modelId,
      provider_override: params.providerOverride,
      allow_provider_cascade: params.allowProviderCascade,
      resolution: params.resolution,
      modality: params.modality,
      native_audio: params.nativeAudio,
      has_clip_audio: params.nativeAudio,
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

export async function renderBeat(
  sessionId: string,
  beatIndex: number,
  backend?: string,
  modelId?: string,
  providerOverride?: string,
  resolution?: string,
  modality?: string,
  hasNativeAudio?: boolean,
  allowProviderCascade?: boolean,
) {
  const res = await fetch('/api/render/beat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      session_id: sessionId,
      beat_index: beatIndex,
      backend,
      model_id: modelId,
      provider_override: providerOverride,
      resolution,
      modality,
      has_native_audio: hasNativeAudio,
      allow_provider_cascade: allowProviderCascade,
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

// --- Feature 010: Multi-Provider Video Routing & Real-Time Cost Arbitrage ---

export interface ProviderDocsEntry {
  provider_id: string;
  name: string;
  official_docs_url: string;
  pricing_docs_url: string;
  failure_billing_policy: string;
  zero_cost_on_failure: boolean;
  api_status_url?: string | null;
  last_verified: string;
  is_configured: boolean;
  supported_models_count: number;
}

export interface VideoModelProfile {
  model_id: string;
  display_name: string;
  family: string;
  version: string;
  hard_char_limit: number;
  safe_char_limit: number;
  token_encoder?: string | null;
  supports_native_audio: boolean;
  supports_i2v: boolean;
  supports_dual_frame: boolean;
  supports_reference_images: boolean;
  max_reference_images: number;
  first_frame_param_name?: string;
  end_frame_param_name?: string;
  reference_param_name?: string;
  supports_extend: boolean;
  supported_providers: string[];
  default_duration_sec: number;
  allowed_durations: number[];
  allowed_resolutions: string[];
}

export interface ProviderPriceQuote {
  provider_id: string;
  model_id: string;
  duration_sec: number;
  resolution: string;
  native_audio_enabled: boolean;
  rate_per_sec_usd: number;
  estimated_total_usd: number;
  billing_unit: string;
  is_available: boolean;
  is_cheapest: boolean;
  discount_pct?: number;
  is_promotional?: boolean;
  promo_description?: string;
  free_tier_applicable?: boolean;
}

export interface QuotesResponse {
  model_id: string;
  recommended_provider: string | null;
  quotes: ProviderPriceQuote[];
}

export interface AdaptedPromptResponse {
  adapted_prompt: string;
  original_length: number;
  adapted_length: number;
  target_limit: number;
  is_within_limit: boolean;
  is_compressed: boolean;
  reduction_ratio: number;
}

export async function fetchProvidersRegistry(): Promise<{ providers: ProviderDocsEntry[] }> {
  const res = await fetch('/api/providers/registry');
  if (!res.ok) throw new Error(`Failed to fetch provider registry: ${res.statusText}`);
  return res.json();
}

export async function fetchProvidersModels(): Promise<{ models: VideoModelProfile[] }> {
  const res = await fetch('/api/providers/models');
  if (!res.ok) throw new Error(`Failed to fetch video models: ${res.statusText}`);
  return res.json();
}

export async function fetchProviderQuotes(
  modelId: string,
  durationSec: number = 5.0,
  resolution: string = '720p',
  hasNativeAudio: boolean = false
): Promise<QuotesResponse> {
  const res = await fetch('/api/providers/quotes', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      model_id: modelId,
      duration_sec: durationSec,
      resolution,
      has_native_audio: hasNativeAudio,
    }),
  });
  if (!res.ok) throw new Error(`Failed to fetch live quotes: ${res.statusText}`);
  return res.json();
}

export async function adaptPrompt(
  rawPrompt: string,
  targetModelId: string,
  modality: string = 't2v',
  hasNativeAudio: boolean = false,
  dialogueText?: string
): Promise<AdaptedPromptResponse> {
  const res = await fetch('/api/providers/adapt-prompt', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      raw_prompt: rawPrompt,
      target_model_id: targetModelId,
      modality,
      has_native_audio: hasNativeAudio,
      dialogue_text: dialogueText,
    }),
  });
  if (!res.ok) throw new Error(`Failed to adapt prompt: ${res.statusText}`);
  return res.json();
}

export interface ExtendVideoRequest {
  session_id: string;
  beat_index: number;
  parent_video_path: string;
  extension_sec?: number;
  continuation_prompt: string;
  provider_id?: string;
  model_id?: string;
}

export interface ExtendVideoResponse {
  status: string;
  extended_video_path: string;
  added_seconds: number;
  billed_cost_usd: number;
}

export interface VideoUpscaleRequest {
  video_path: string;
  target_resolution?: string;
  engine?: string;
}

export interface VideoUpscaleResponse {
  status: string;
  upscaled_video_path: string;
  target_resolution: string;
}

export async function extendVideoJob(req: ExtendVideoRequest): Promise<ExtendVideoResponse> {
  const res = await fetch('/api/render/extend-job', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(req),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Extend video failed: ${res.statusText}`);
  }
  return res.json();
}

export async function upscaleVideoJob(req: VideoUpscaleRequest): Promise<VideoUpscaleResponse> {
  const res = await fetch('/api/render/upscale-job', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(req),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Upscale video failed: ${res.statusText}`);
  }
  return res.json();
}




