import React, { useState, useRef, useEffect } from 'react';
import { createPortal } from 'react-dom';
import {
  RefreshCw,
  Video,
  Camera,
  Sparkles,
  CheckCircle2,
  Clock,
  Upload,
  Mic,
  Play,
  Link as LinkIcon,
  Unlink as UnlinkIcon,
  AlertTriangle,
  AlertCircle,
  Copy,
  Check,
  ImageIcon,
  Film,
  FastForward,
  Maximize2,
  ChevronDown,
  Search,
  X,
  Plus,
  Trash2,
  ImagePlus,
  Layers,
  ShieldCheck,
  ShieldAlert,
} from 'lucide-react';
import { StoryboardCard, adaptPrompt, extendVideoJob, upscaleVideoJob } from '../services/api';
import { TakeSwitcher } from './TakeSwitcher';
import { CostTransparencyModal } from './CostTransparencyModal';

export interface VideoModelItem {
  id: string;
  name: string;
  version: string;
  family: string;
  limit: number;
  supportsAudio: boolean;
  badge?: string;
  supportsI2V?: boolean;
  supportsDualFrame?: boolean;
  supportsReferenceImages?: boolean;
  maxReferenceImages?: number;
}

export const VIDEO_MODEL_GROUPS: { family: string; label: string; models: VideoModelItem[] }[] = [
  {
    family: 'flux',
    label: 'FLUX Video (fal / BFL)',
    models: [
      { id: 'flux-3-max', name: 'FLUX 3 Max (Audio + Dual Frame)', version: '3-max', family: 'flux', limit: 4000, supportsAudio: true, badge: '🎁 75% OFF / Free Sandbox', supportsI2V: true, supportsDualFrame: true, supportsReferenceImages: true, maxReferenceImages: 4 },
      { id: 'flux-3', name: 'FLUX 3 Video (Black Forest Labs)', version: 'v3.0', family: 'flux', limit: 3000, supportsAudio: true, badge: 'BFL', supportsI2V: true, supportsDualFrame: true, supportsReferenceImages: false, maxReferenceImages: 0 },
    ],
  },
  {
    family: 'kling',
    label: 'Kling AI',
    models: [
      { id: 'kling-v4.0', name: 'Kling 4.0 Omni Multi-Keyframe', version: 'v4.0', family: 'kling', limit: 5000, supportsAudio: true, badge: 'Omni 4.0', supportsI2V: true, supportsDualFrame: true, supportsReferenceImages: true, maxReferenceImages: 4 },
      { id: 'kling-v3.0', name: 'Kling 3.0 Omni Director 4K', version: 'v3.0', family: 'kling', limit: 5000, supportsAudio: true, badge: '4K', supportsI2V: true, supportsDualFrame: true, supportsReferenceImages: true, maxReferenceImages: 4 },
      { id: 'kling-v2.5', name: 'Kling 2.5 Turbo Cinema', version: 'v2.5', family: 'kling', limit: 4000, supportsAudio: true, badge: 'Turbo', supportsI2V: true, supportsDualFrame: true, supportsReferenceImages: true, maxReferenceImages: 4 },
      { id: 'kling-v2.0', name: 'Kling 2.0 Omni', version: 'v2.0', family: 'kling', limit: 3072, supportsAudio: true, badge: 'Omni', supportsI2V: true, supportsDualFrame: true, supportsReferenceImages: true, maxReferenceImages: 2 },
      { id: 'kling-v1.5', name: 'Kling 1.5 Pro', version: 'v1.5-pro', family: 'kling', limit: 3072, supportsAudio: true, badge: 'Pro', supportsI2V: true, supportsDualFrame: true, supportsReferenceImages: false, maxReferenceImages: 0 },
      { id: 'kling-v1.5-std', name: 'Kling 1.5 Standard', version: 'v1.5-std', family: 'kling', limit: 2500, supportsAudio: false, supportsI2V: true, supportsDualFrame: true, supportsReferenceImages: false, maxReferenceImages: 0 },
      { id: 'kling-v1.0-pro', name: 'Kling 1.0 Pro', version: 'v1.0-pro', family: 'kling', limit: 2000, supportsAudio: false, supportsI2V: true, supportsDualFrame: false, supportsReferenceImages: false, maxReferenceImages: 0 },
      { id: 'kling-v1.0', name: 'Kling 1.0 Standard', version: 'v1.0', family: 'kling', limit: 1500, supportsAudio: false, supportsI2V: true, supportsDualFrame: false, supportsReferenceImages: false, maxReferenceImages: 0 },
    ],
  },
  {
    family: 'seedance',
    label: 'ByteDance Seedance',
    models: [
      { id: 'seedance-2.5', name: 'Seedance 2.5 Cinema', version: 'v2.5', family: 'seedance', limit: 5000, supportsAudio: true, badge: '5k Chars', supportsI2V: true, supportsDualFrame: true, supportsReferenceImages: true, maxReferenceImages: 4 },
      { id: 'seedance-2.0', name: 'Seedance 2.0 Multimodal', version: 'v2.0', family: 'seedance', limit: 2000, supportsAudio: true, supportsI2V: true, supportsDualFrame: true, supportsReferenceImages: true, maxReferenceImages: 4 },
      { id: 'seedance-1.5', name: 'Seedance 1.5 Pro', version: 'v1.5', family: 'seedance', limit: 2000, supportsAudio: false, supportsI2V: true, supportsDualFrame: false, supportsReferenceImages: false, maxReferenceImages: 0 },
      { id: 'seedance-1.0', name: 'Seedance 1.0', version: 'v1.0', family: 'seedance', limit: 1500, supportsAudio: false, supportsI2V: true, supportsDualFrame: false, supportsReferenceImages: false, maxReferenceImages: 0 },
    ],
  },
  {
    family: 'runway',
    label: 'Runway Gen',
    models: [
      { id: 'runway-gen3-turbo', name: 'Runway Gen-3 Alpha Turbo', version: 'gen3-turbo', family: 'runway', limit: 1000, supportsAudio: false, badge: 'Fast', supportsI2V: true, supportsDualFrame: true, supportsReferenceImages: false, maxReferenceImages: 0 },
      { id: 'runway-gen3-alpha', name: 'Runway Gen-3 Alpha', version: 'gen3-alpha', family: 'runway', limit: 1000, supportsAudio: false, supportsI2V: true, supportsDualFrame: true, supportsReferenceImages: false, maxReferenceImages: 0 },
      { id: 'runway-gen2', name: 'Runway Gen-2', version: 'gen2', family: 'runway', limit: 500, supportsAudio: false, supportsI2V: true, supportsDualFrame: false, supportsReferenceImages: false, maxReferenceImages: 0 },
    ],
  },
  {
    family: 'minimax',
    label: 'MiniMax Hailuo',
    models: [
      { id: 'minimax-h3', name: 'MiniMax H3 Max (Audio)', version: 'h3-max', family: 'minimax', limit: 2000, supportsAudio: true, badge: 'Audio', supportsI2V: true, supportsDualFrame: true, supportsReferenceImages: true, maxReferenceImages: 2 },
      { id: 'minimax-hailuo-live', name: 'MiniMax Hailuo Live 01', version: 'live-01', family: 'minimax', limit: 1500, supportsAudio: false, supportsI2V: true, supportsDualFrame: false, supportsReferenceImages: false, maxReferenceImages: 0 },
      { id: 'minimax-hailuo-01', name: 'MiniMax Hailuo Video-01', version: 'video-01', family: 'minimax', limit: 1000, supportsAudio: false, supportsI2V: true, supportsDualFrame: false, supportsReferenceImages: false, maxReferenceImages: 0 },
    ],
  },
  {
    family: 'veo',
    label: 'Google Veo',
    models: [
      { id: 'veo-3.1', name: 'Google Veo 3.1 Cinematic Audio', version: 'v3.1', family: 'veo', limit: 4000, supportsAudio: true, badge: 'Audio', supportsI2V: true, supportsDualFrame: true, supportsReferenceImages: true, maxReferenceImages: 3 },
      { id: 'veo-3', name: 'Google Veo 3 Preview', version: 'v3.0', family: 'veo', limit: 3000, supportsAudio: true, badge: 'Next-Gen', supportsI2V: true, supportsDualFrame: true, supportsReferenceImages: true, maxReferenceImages: 3 },
      { id: 'veo-2', name: 'Google Veo 2', version: 'v2.0', family: 'veo', limit: 1500, supportsAudio: true, supportsI2V: true, supportsDualFrame: false, supportsReferenceImages: false, maxReferenceImages: 0 },
    ],
  },
  {
    family: 'wan',
    label: 'Alibaba Wan',
    models: [
      { id: 'wan-3.0', name: 'Alibaba Wan 3.0 Prime (Audio)', version: 'v3.0', family: 'wan', limit: 5000, supportsAudio: true, badge: 'Audio', supportsI2V: true, supportsDualFrame: true, supportsReferenceImages: true, maxReferenceImages: 5 },
      { id: 'wan-2.2', name: 'Alibaba Wan 2.2 Turbo', version: 'v2.2', family: 'wan', limit: 2500, supportsAudio: false, badge: 'Turbo', supportsI2V: true, supportsDualFrame: true, supportsReferenceImages: true, maxReferenceImages: 4 },
      { id: 'wan-2.1', name: 'Alibaba Wan 2.1 (14B HQ)', version: 'v2.1-14b', family: 'wan', limit: 1200, supportsAudio: false, badge: 'HQ', supportsI2V: true, supportsDualFrame: true, supportsReferenceImages: true, maxReferenceImages: 4 },
      { id: 'wan-2.1-t2v-1.3b', name: 'Alibaba Wan 2.1 (1.3B Fast)', version: 'v2.1-1.3b', family: 'wan', limit: 1200, supportsAudio: false, badge: 'Fast', supportsI2V: false, supportsDualFrame: false, supportsReferenceImages: false, maxReferenceImages: 0 },
      { id: 'wan-2.1-i2v-720p', name: 'Alibaba Wan 2.1 I2V (720p)', version: 'v2.1-i2v', family: 'wan', limit: 1200, supportsAudio: false, supportsI2V: true, supportsDualFrame: true, supportsReferenceImages: true, maxReferenceImages: 4 },
    ],
  },
  {
    family: 'grok',
    label: 'xAI Grok',
    models: [
      { id: 'grok-video-1.5', name: 'xAI Grok Imagine Video 1.5 (Audio)', version: 'v1.5', family: 'grok', limit: 3000, supportsAudio: true, badge: 'Audio', supportsI2V: true, supportsDualFrame: false, supportsReferenceImages: false, maxReferenceImages: 0 },
    ],
  },
  {
    family: 'luma',
    label: 'Luma Dream Machine',
    models: [
      { id: 'luma-ray2', name: 'Luma Ray 2', version: 'ray-2', family: 'luma', limit: 5000, supportsAudio: false, badge: '5k Chars', supportsI2V: true, supportsDualFrame: true, supportsReferenceImages: true, maxReferenceImages: 3 },
      { id: 'luma-ray1', name: 'Luma Ray 1', version: 'ray-1', family: 'luma', limit: 2000, supportsAudio: false, supportsI2V: true, supportsDualFrame: false, supportsReferenceImages: false, maxReferenceImages: 0 },
    ],
  },
  {
    family: 'pixverse',
    label: 'PixVerse',
    models: [
      { id: 'pixverse-v3', name: 'PixVerse v3.5 (Audio)', version: 'v3.5', family: 'pixverse', limit: 1500, supportsAudio: true, supportsI2V: true, supportsDualFrame: true, supportsReferenceImages: true, maxReferenceImages: 3 },
      { id: 'pixverse-v2', name: 'PixVerse v2', version: 'v2.0', family: 'pixverse', limit: 1000, supportsAudio: false, supportsI2V: true, supportsDualFrame: false, supportsReferenceImages: false, maxReferenceImages: 0 },
    ],
  },
  {
    family: 'pika',
    label: 'Pika',
    models: [
      { id: 'pika-2.0', name: 'Pika 2.0 (SFX)', version: 'v2.0', family: 'pika', limit: 1500, supportsAudio: true, supportsI2V: true, supportsDualFrame: false, supportsReferenceImages: false, maxReferenceImages: 0 },
      { id: 'pika-1.0', name: 'Pika 1.0', version: 'v1.0', family: 'pika', limit: 1000, supportsAudio: false, supportsI2V: true, supportsDualFrame: false, supportsReferenceImages: false, maxReferenceImages: 0 },
    ],
  },
  {
    family: 'vidu',
    label: 'ShengShu Vidu',
    models: [
      { id: 'vidu-2.0', name: 'ShengShu Vidu 2.0 (Audio)', version: 'v2.0', family: 'vidu', limit: 2000, supportsAudio: true, supportsI2V: true, supportsDualFrame: true, supportsReferenceImages: true, maxReferenceImages: 3 },
      { id: 'vidu-1.5', name: 'ShengShu Vidu 1.5', version: 'v1.5', family: 'vidu', limit: 1500, supportsAudio: false, supportsI2V: true, supportsDualFrame: false, supportsReferenceImages: false, maxReferenceImages: 0 },
    ],
  },
  {
    family: 'budget',
    label: 'Open-Weights / Budget',
    models: [
      { id: 'hunyuan-video', name: 'Tencent Hunyuan Video', version: 'v1.0', family: 'budget', limit: 2500, supportsAudio: false, supportsI2V: true, supportsDualFrame: false, supportsReferenceImages: false, maxReferenceImages: 0 },
      { id: 'cogvideox-5b', name: 'CogVideoX 5B', version: 'v5b', family: 'budget', limit: 800, supportsAudio: false, supportsI2V: true, supportsDualFrame: false, supportsReferenceImages: false, maxReferenceImages: 0 },
      { id: 'cogvideox-2b', name: 'CogVideoX 2B Fast', version: 'v2b', family: 'budget', limit: 600, supportsAudio: false, supportsI2V: true, supportsDualFrame: false, supportsReferenceImages: false, maxReferenceImages: 0 },
      { id: 'mochi-1', name: 'Genmo Mochi 1 Preview', version: 'v1.0', family: 'budget', limit: 1500, supportsAudio: false, supportsI2V: false, supportsDualFrame: false, supportsReferenceImages: false, maxReferenceImages: 0 },
    ],
  },
];

export const VIDEO_MODELS: Record<string, {
  name: string;
  limit: number;
  supportsAudio: boolean;
  version?: string;
  supportsI2V: boolean;
  supportsDualFrame: boolean;
  supportsReferenceImages: boolean;
  maxReferenceImages: number;
}> =
  VIDEO_MODEL_GROUPS.flatMap((g) => g.models).reduce((acc, m) => {
    acc[m.id] = {
      name: m.name,
      limit: m.limit,
      supportsAudio: m.supportsAudio,
      version: m.version,
      supportsI2V: m.supportsI2V ?? true,
      supportsDualFrame: m.supportsDualFrame ?? false,
      supportsReferenceImages: m.supportsReferenceImages ?? false,
      maxReferenceImages: m.maxReferenceImages ?? 0,
    };
    return acc;
  }, {} as Record<string, {
    name: string;
    limit: number;
    supportsAudio: boolean;
    version?: string;
    supportsI2V: boolean;
    supportsDualFrame: boolean;
    supportsReferenceImages: boolean;
    maxReferenceImages: number;
  }>);


export interface ProviderRateInfo {
  fal: number;
  apidot: number;
  kie: number;
  cheapest: 'fal' | 'apidot' | 'kie';
}

export const MODEL_PROVIDER_RATES: Record<string, ProviderRateInfo> = {
  // FLUX Video (fal Research Launch Promotion: 75% OFF)
  'flux-3-max': { fal: 0.02125, apidot: 0.085, kie: 0.085, cheapest: 'fal' },
  'flux-3': { fal: 0.085, apidot: 0.085, kie: 0.085, cheapest: 'fal' },

  // Kling AI
  'kling-v4.0': { fal: 0.160, apidot: 0.140, kie: 0.1425, cheapest: 'apidot' },
  'kling-v3.0': { fal: 0.140, apidot: 0.125, kie: 0.130, cheapest: 'apidot' },
  'kling-v2.5': { fal: 0.125, apidot: 0.110, kie: 0.118, cheapest: 'apidot' },
  'kling-v2.0': { fal: 0.115, apidot: 0.100, kie: 0.110, cheapest: 'apidot' },
  'kling-v1.5': { fal: 0.090, apidot: 0.080, kie: 0.085, cheapest: 'apidot' },
  'kling-v1.5-std': { fal: 0.075, apidot: 0.068, kie: 0.072, cheapest: 'apidot' },
  'kling-v1.0-pro': { fal: 0.075, apidot: 0.065, kie: 0.070, cheapest: 'apidot' },
  'kling-v1.0': { fal: 0.065, apidot: 0.055, kie: 0.060, cheapest: 'apidot' },

  // ByteDance Seedance
  'seedance-2.5': { fal: 0.080, apidot: 0.070, kie: 0.068, cheapest: 'kie' },
  'seedance-2.0': { fal: 0.060, apidot: 0.050, kie: 0.048, cheapest: 'kie' },
  'seedance-1.5': { fal: 0.040, apidot: 0.030, kie: 0.028, cheapest: 'kie' },
  'seedance-1.0': { fal: 0.030, apidot: 0.025, kie: 0.022, cheapest: 'kie' },

  // Runway
  'runway-gen3-alpha': { fal: 0.100, apidot: 0.095, kie: 0.090, cheapest: 'kie' },
  'runway-gen3-turbo': { fal: 0.050, apidot: 0.048, kie: 0.045, cheapest: 'kie' },
  'runway-gen2': { fal: 0.030, apidot: 0.028, kie: 0.025, cheapest: 'kie' },

  // MiniMax Hailuo
  'minimax-h3': { fal: 0.095, apidot: 0.085, kie: 0.088, cheapest: 'apidot' },
  'minimax-hailuo-live': { fal: 0.075, apidot: 0.068, kie: 0.070, cheapest: 'apidot' },
  'minimax-hailuo-01': { fal: 0.060, apidot: 0.055, kie: 0.058, cheapest: 'apidot' },

  // Google Veo
  'veo-3.1': { fal: 0.320, apidot: 0.290, kie: 0.300, cheapest: 'apidot' },
  'veo-3': { fal: 0.280, apidot: 0.260, kie: 0.270, cheapest: 'apidot' },
  'veo-2': { fal: 0.190, apidot: 0.175, kie: 0.180, cheapest: 'apidot' },

  // Alibaba Wan
  'wan-3.0': { fal: 0.100, apidot: 0.090, kie: 0.092, cheapest: 'apidot' },
  'wan-2.2': { fal: 0.065, apidot: 0.055, kie: 0.058, cheapest: 'apidot' },
  'wan-2.1': { fal: 0.045, apidot: 0.038, kie: 0.040, cheapest: 'apidot' },
  'wan-2.1-t2v-1.3b': { fal: 0.020, apidot: 0.018, kie: 0.019, cheapest: 'apidot' },
  'wan-2.1-i2v-720p': { fal: 0.045, apidot: 0.038, kie: 0.040, cheapest: 'apidot' },

  // xAI Grok
  'grok-video-1.5': { fal: 0.035, apidot: 0.028, kie: 0.0225, cheapest: 'kie' },

  // Luma Dream Machine
  'luma-ray2': { fal: 0.100, apidot: 0.090, kie: 0.095, cheapest: 'apidot' },
  'luma-ray1': { fal: 0.060, apidot: 0.055, kie: 0.058, cheapest: 'apidot' },

  // PixVerse
  'pixverse-v3': { fal: 0.070, apidot: 0.065, kie: 0.068, cheapest: 'apidot' },
  'pixverse-v2': { fal: 0.040, apidot: 0.035, kie: 0.038, cheapest: 'apidot' },

  // Pika
  'pika-2.0': { fal: 0.065, apidot: 0.060, kie: 0.058, cheapest: 'kie' },
  'pika-1.0': { fal: 0.035, apidot: 0.032, kie: 0.030, cheapest: 'kie' },

  // ShengShu Vidu
  'vidu-2.0': { fal: 0.080, apidot: 0.075, kie: 0.078, cheapest: 'apidot' },
  'vidu-1.5': { fal: 0.050, apidot: 0.045, kie: 0.048, cheapest: 'apidot' },

  // Open-Weights / Budget
  'hunyuan-video': { fal: 0.050, apidot: 0.042, kie: 0.045, cheapest: 'apidot' },
  'cogvideox-5b': { fal: 0.035, apidot: 0.030, kie: 0.032, cheapest: 'apidot' },
  'cogvideox-2b': { fal: 0.018, apidot: 0.015, kie: 0.016, cheapest: 'apidot' },
  'mochi-1': { fal: 0.055, apidot: 0.048, kie: 0.050, cheapest: 'apidot' },
};

export function getResolutionMultiplier(provider: 'fal' | 'apidot' | 'kie', resolution: string = '720p'): number {
  const res = (resolution || '720p').toLowerCase();
  if (res === '480p') {
    return provider === 'kie' ? 0.55 : 0.60;
  }
  if (res === '1080p') {
    return provider === 'fal' ? 1.35 : provider === 'kie' ? 1.45 : 1.25;
  }
  if (res === '4k') {
    return provider === 'fal' ? 2.00 : provider === 'kie' ? 2.10 : 1.85;
  }
  return 1.0; // 720p baseline
}

export function getRatesForResolution(rates: ProviderRateInfo, resolution: string = '720p'): ProviderRateInfo {
  const res = (resolution || '720p').toLowerCase();
  const multFal = getResolutionMultiplier('fal', res);
  const multApi = getResolutionMultiplier('apidot', res);
  const multKie = getResolutionMultiplier('kie', res);

  const falRate = +(rates.fal * multFal).toFixed(3);
  const apidotRate = +(rates.apidot * multApi).toFixed(3);
  const kieRate = +(rates.kie * multKie).toFixed(3);

  let cheapest: 'fal' | 'apidot' | 'kie' = 'apidot';
  const minRate = Math.min(falRate, apidotRate, kieRate);
  if (minRate === falRate) cheapest = 'fal';
  else if (minRate === apidotRate) cheapest = 'apidot';
  else cheapest = 'kie';

  return { fal: falRate, apidot: apidotRate, kie: kieRate, cheapest };
}

const getVoicePersonaLabel = (actor?: string) => {
  if (!actor || actor === 'auto') return 'Auto Voice';
  if (actor.includes('kid')) return 'Kid Voice';
  if (actor.includes('cartoon') || actor.includes('animal')) return 'Cartoon Animal';
  if (actor.includes('villain') || actor.includes('monster')) return 'Deep Villain';
  if (actor.includes('female') || actor.includes('Jenny') || actor.includes('Joanna') || actor.includes('asteria')) return 'Female Narrator';
  if (actor.includes('male') || actor.includes('Christopher') || actor.includes('Matthew') || actor.includes('orion')) return 'Christopher (Deep Male)';
  if (actor.includes('energetic')) return 'Action Voice';
  return actor.replace('en-US-', '').replace('Neural', '');
};

const getCardMotionPrompt = (c: StoryboardCard): string => {
  if (c.motion_prompt && c.image_prompt && c.motion_prompt !== c.image_prompt) {
    return c.motion_prompt;
  }
  if (c.motion_prompt && c.motion_prompt !== c.visual_prompt) {
    return c.motion_prompt;
  }
  const cam = (c.camera_motion || 'slow_push_in').replace(/_/g, ' ');
  const camTitle = cam.charAt(0).toUpperCase() + cam.slice(1);
  return `${camTitle} camera movement, dynamic subject motion and environmental physics: ${c.visual_prompt}`;
};

interface BeatCardProps {
  card: StoryboardCard;
  aspectRatio: string;
  projectId?: string;
  onSelectTake?: (beatIndex: number, takeId: string) => Promise<void>;
  onReroll: (beatIndex: number, promptOverride?: string, promptType?: 'image' | 'motion') => Promise<void>;
  onUploadImage?: (beatIndex: number, file: File, frameType?: 'start_frame' | 'end_frame' | 'reference_image') => Promise<void>;
  onRemoveFrame?: (beatIndex: number, frameType: 'start_frame' | 'end_frame' | 'reference_image', imageIndex?: number) => Promise<void>;
  onUpdateCard?: (beatIndex: number, updates: Partial<StoryboardCard>) => Promise<void>;
  onRenderBeat?: (beatIndex: number) => Promise<void>;
  onChainFrame?: (sourceBeatIndex: number) => Promise<void>;
  onUnlinkChain?: (beatIndex: number) => Promise<void>;
  isRendering?: boolean;
  totalBeats?: number;
}

export const BeatCard: React.FC<BeatCardProps> = ({
  card,
  aspectRatio,
  projectId,
  onSelectTake,
  onReroll,
  onUploadImage,
  onRemoveFrame,
  onUpdateCard,
  onRenderBeat,
  onChainFrame,
  onUnlinkChain,
  isRendering,
  totalBeats = 4,
}) => {
  const [isRerolling, setIsRerolling] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadingTarget, setUploadingTarget] = useState<'start_frame' | 'end_frame' | 'reference_image' | null>(null);
  const [isRenderingBeat, setIsRenderingBeat] = useState(false);
  const [isChaining, setIsChaining] = useState(false);
  const [isUnlinking, setIsUnlinking] = useState(false);

  // Dual-Prompt Inspector State
  const [activePromptTab, setActivePromptTab] = useState<'image' | 'motion'>('image');
  const [imagePromptText, setImagePromptText] = useState(card.image_prompt || card.visual_prompt);
  const [motionPromptText, setMotionPromptText] = useState(getCardMotionPrompt(card));
  const [isEditingImagePrompt, setIsEditingImagePrompt] = useState(false);
  const [isEditingMotionPrompt, setIsEditingMotionPrompt] = useState(false);
  const [copiedTab, setCopiedTab] = useState<'image' | 'motion' | null>(null);

  // Multi-Provider & Model Routing State
  const [selectedModel, setSelectedModel] = useState<string>((card as any).model_id || 'kling-v2.5');
  const [resolution, setResolution] = useState<string>((card as any).resolution || '720p');
  const [previewResolution, setPreviewResolution] = useState<string>((card as any).resolution || '720p');
  const [modality, setModality] = useState<'t2v' | 'i2v'>(((card as any).modality as 't2v' | 'i2v') || 't2v');
  const [hasNativeAudio, setHasNativeAudio] = useState<boolean>((card as any).native_audio || (card as any).has_clip_audio || false);
  const [isCostModalOpen, setIsCostModalOpen] = useState<boolean>(false);
  const [selectedProviderOverride, setSelectedProviderOverride] = useState<string | null>(
    (card as any).provider_override && (card as any).provider_override !== 'auto' ? (card as any).provider_override : null
  );
  const [allowProviderCascade, setAllowProviderCascade] = useState<boolean>(
    typeof (card as any).allow_provider_cascade === 'boolean' ? (card as any).allow_provider_cascade : true
  );
  const [isAdaptingPrompt, setIsAdaptingPrompt] = useState<boolean>(false);
  const [isExtending, setIsExtending] = useState<boolean>(false);
  const [isUpscaling, setIsUpscaling] = useState<boolean>(false);
  const [videoDimensions, setVideoDimensions] = useState<{ width: number; height: number } | null>(null);

  // Sync state if card properties are updated externally
  useEffect(() => {
    if ((card as any).model_id) setSelectedModel((card as any).model_id);
    if ((card as any).resolution) {
      setResolution((card as any).resolution);
      setPreviewResolution((card as any).resolution);
    }
    if ((card as any).modality) setModality((card as any).modality);
    if (typeof (card as any).native_audio === 'boolean') setHasNativeAudio((card as any).native_audio);
    if ((card as any).provider_override) {
      setSelectedProviderOverride((card as any).provider_override === 'auto' ? null : (card as any).provider_override);
    }
    if (typeof (card as any).allow_provider_cascade === 'boolean') {
      setAllowProviderCascade((card as any).allow_provider_cascade);
    }
  }, [card.beat_index, (card as any).model_id, (card as any).resolution, (card as any).modality, (card as any).native_audio, (card as any).provider_override, (card as any).allow_provider_cascade]);

  const [isModelMenuOpen, setIsModelMenuOpen] = useState<boolean>(false);
  const [modelSearchQuery, setModelSearchQuery] = useState<string>('');
  const [selectedFamilyFilter, setSelectedFamilyFilter] = useState<string>('all');
  const [popoverCoords, setPopoverCoords] = useState<{
    top?: number;
    bottom?: number;
    left: number;
    width: number;
    maxHeight: number;
    isCentered?: boolean;
  }>({ left: 0, width: 480, maxHeight: 500 });

  const modelMenuRef = useRef<HTMLDivElement>(null);
  const triggerBtnRef = useRef<HTMLButtonElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const fileInputStartRef = useRef<HTMLInputElement>(null);
  const fileInputEndRef = useRef<HTMLInputElement>(null);
  const fileInputRefImagesRef = useRef<HTMLInputElement>(null);

  const updatePopoverPosition = () => {
    if (!triggerBtnRef.current) return;
    const rect = triggerBtnRef.current.getBoundingClientRect();
    const popoverWidth = Math.min(500, window.innerWidth - 32);
    const desiredHeight = 520;

    // Center on very compact screens or mobile viewports
    if (window.innerWidth < 640 || window.innerHeight < 550) {
      setPopoverCoords({
        left: Math.max(16, (window.innerWidth - popoverWidth) / 2),
        top: Math.max(20, (window.innerHeight - desiredHeight) / 2),
        width: popoverWidth,
        maxHeight: Math.min(desiredHeight, window.innerHeight - 40),
        isCentered: true,
      });
      return;
    }

    // Horizontal alignment: match trigger button left, constrained by screen boundaries
    let left = rect.left;
    if (left + popoverWidth > window.innerWidth - 16) {
      left = window.innerWidth - popoverWidth - 16;
    }
    if (left < 16) left = 16;

    // Vertical placement: evaluate available vertical clearance
    const spaceBelow = window.innerHeight - rect.bottom - 12;
    const spaceAbove = rect.top - 12;

    if (spaceBelow >= 340 || spaceBelow >= spaceAbove) {
      // Space is comfortable below
      const maxHeight = Math.min(desiredHeight, Math.max(280, spaceBelow));
      setPopoverCoords({
        top: rect.bottom + 6,
        left,
        width: popoverWidth,
        maxHeight,
        isCentered: false,
      });
    } else {
      // Space is better above
      const maxHeight = Math.min(desiredHeight, Math.max(280, spaceAbove));
      setPopoverCoords({
        bottom: window.innerHeight - rect.top + 6,
        left,
        width: popoverWidth,
        maxHeight,
        isCentered: false,
      });
    }
  };

  useEffect(() => {
    if (!isModelMenuOpen) return;
    updatePopoverPosition();

    const handleWindowChange = () => {
      updatePopoverPosition();
    };

    window.addEventListener('resize', handleWindowChange);
    window.addEventListener('scroll', handleWindowChange, true);
    return () => {
      window.removeEventListener('resize', handleWindowChange);
      window.removeEventListener('scroll', handleWindowChange, true);
    };
  }, [isModelMenuOpen]);

  // Sync state if card updates from external sources
  useEffect(() => {
    if (!isEditingImagePrompt) {
      setImagePromptText(card.image_prompt || card.visual_prompt);
    }
    if (!isEditingMotionPrompt) {
      setMotionPromptText(getCardMotionPrompt(card));
    }
  }, [card.image_prompt, card.motion_prompt, card.visual_prompt, card.camera_motion, isEditingImagePrompt, isEditingMotionPrompt]);

  const handleExtendVideo = async () => {
    if (!card.output_video_path) return;
    setIsExtending(true);
    try {
      const res = await extendVideoJob({
        session_id: projectId || 'default_session',
        beat_index: card.beat_index,
        parent_video_path: card.output_video_path,
        extension_sec: 5.0,
        continuation_prompt: motionPromptText || card.visual_prompt,
        provider_id: selectedProviderOverride || undefined,
        model_id: selectedModel,
      });
      if (onUpdateCard && res.extended_video_path) {
        await onUpdateCard(card.beat_index, {
          output_video_path: res.extended_video_path,
          duration_seconds: (card.duration_seconds || 5.0) + res.added_seconds,
        });
      }
    } catch (err: any) {
      alert(`Extend Video failed: ${err.message}`);
    } finally {
      setIsExtending(false);
    }
  };

  const handleUpscaleVideo = async () => {
    if (!card.output_video_path) return;
    setIsUpscaling(true);
    try {
      const res = await upscaleVideoJob({
        video_path: card.output_video_path,
        target_resolution: '4k',
        engine: 'real_esrgan',
      });
      if (onUpdateCard && res.upscaled_video_path) {
        await onUpdateCard(card.beat_index, {
          output_video_path: res.upscaled_video_path,
        });
      }
    } catch (err: any) {
      alert(`4K Upscale failed: ${err.message}`);
    } finally {
      setIsUpscaling(false);
    }
  };

  const activePromptText = activePromptTab === 'image' ? imagePromptText : motionPromptText;
  const currentModelConfig = VIDEO_MODELS[selectedModel] || VIDEO_MODELS['kling-v2.5'] || VIDEO_MODELS['kling-v1.5'];
  const currentModelRates = MODEL_PROVIDER_RATES[selectedModel] || { fal: 0.05, apidot: 0.05, kie: 0.05, cheapest: 'fal' };
  const activeResolutionRates = getRatesForResolution(currentModelRates, resolution);
  const charLimit = currentModelConfig.limit;
  const isOverLimit = activePromptText.length > charLimit;
  const isNearLimit = activePromptText.length > charLimit * 0.9;

  const filteredModelGroups = VIDEO_MODEL_GROUPS.map((group) => {
    if (selectedFamilyFilter !== 'all' && group.family !== selectedFamilyFilter) {
      return null;
    }
    const filteredModels = group.models.filter(
      (m) =>
        m.name.toLowerCase().includes(modelSearchQuery.toLowerCase()) ||
        m.id.toLowerCase().includes(modelSearchQuery.toLowerCase()) ||
        group.label.toLowerCase().includes(modelSearchQuery.toLowerCase()) ||
        (m.badge && m.badge.toLowerCase().includes(modelSearchQuery.toLowerCase()))
    );
    if (filteredModels.length === 0) return null;
    return { ...group, models: filteredModels };
  }).filter(Boolean) as typeof VIDEO_MODEL_GROUPS;

  const totalFilteredCount = filteredModelGroups.reduce((acc, g) => acc + g.models.length, 0);

  const handleAutoFitPrompt = async () => {
    setIsAdaptingPrompt(true);
    try {
      const res = await adaptPrompt(
        activePromptText,
        selectedModel,
        modality,
        hasNativeAudio,
        card.dialogue_text
      );
      if (activePromptTab === 'image') {
        setImagePromptText(res.adapted_prompt);
        if (onUpdateCard) {
          await onUpdateCard(card.beat_index, {
            image_prompt: res.adapted_prompt,
          });
        }
      } else {
        setMotionPromptText(res.adapted_prompt);
        if (onUpdateCard) {
          await onUpdateCard(card.beat_index, {
            motion_prompt: res.adapted_prompt,
          });
        }
      }
    } catch (err) {
      console.error('Failed to auto-fit prompt:', err);
    } finally {
      setIsAdaptingPrompt(false);
    }
  };

  const handleCopyPrompt = async (type: 'image' | 'motion') => {
    const textToCopy = type === 'image' ? imagePromptText : motionPromptText;
    try {
      await navigator.clipboard.writeText(textToCopy);
      setCopiedTab(type);
      setTimeout(() => setCopiedTab((curr) => (curr === type ? null : curr)), 2000);
    } catch (err) {
      console.error('Failed to copy prompt:', err);
    }
  };

  const handleSaveImagePrompt = async () => {
    const promptToUse = imagePromptText.trim() || card.image_prompt || card.visual_prompt;
    if (onUpdateCard) {
      await onUpdateCard(card.beat_index, { image_prompt: promptToUse });
    }
    setIsEditingImagePrompt(false);
  };

  const handleGenerateImageClick = async () => {
    setIsRerolling(true);
    try {
      const promptToUse = imagePromptText.trim() || card.image_prompt || card.visual_prompt;
      if (onUpdateCard && promptToUse !== card.image_prompt) {
        await onUpdateCard(card.beat_index, { image_prompt: promptToUse });
      }
      await onReroll(card.beat_index, promptToUse, 'image');
    } finally {
      setIsRerolling(false);
      setIsEditingImagePrompt(false);
    }
  };

  const handleSaveMotionPrompt = async () => {
    if (onUpdateCard) {
      const promptToUse = motionPromptText.trim() || card.motion_prompt || card.visual_prompt;
      await onUpdateCard(card.beat_index, {
        motion_prompt: promptToUse,
      });
    }
    setIsEditingMotionPrompt(false);
  };

  const handleFrameUpload = async (
    e: React.ChangeEvent<HTMLInputElement>,
    frameType: 'start_frame' | 'end_frame' | 'reference_image'
  ) => {
    const file = e.target.files?.[0];
    if (!file || !onUploadImage) return;
    setUploadingTarget(frameType);
    try {
      await onUploadImage(card.beat_index, file, frameType);
      if (frameType === 'start_frame' || frameType === 'end_frame') {
        if (modality === 't2v') {
          setModality('i2v');
          onUpdateCard?.(card.beat_index, { modality: 'i2v' } as any);
        }
      }
    } finally {
      setUploadingTarget(null);
      e.target.value = '';
    }
  };

  const handleRemoveFrameClick = async (
    frameType: 'start_frame' | 'end_frame' | 'reference_image',
    imageIndex?: number
  ) => {
    if (!onRemoveFrame) return;
    try {
      await onRemoveFrame(card.beat_index, frameType, imageIndex);
    } catch (err) {
      console.error(`Failed to remove ${frameType}:`, err);
    }
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    await handleFrameUpload(e, 'start_frame');
  };

  const handleRenderBeatClick = async () => {
    if (!onRenderBeat) return;
    setIsRenderingBeat(true);
    try {
      await onRenderBeat(card.beat_index);
    } finally {
      setIsRenderingBeat(false);
    }
  };

  const handleChainFrameClick = async () => {
    if (!onChainFrame) return;
    setIsChaining(true);
    try {
      await onChainFrame(card.beat_index);
    } finally {
      setIsChaining(false);
    }
  };

  const handleUnlinkClick = async () => {
    if (!onUnlinkChain) return;
    setIsUnlinking(true);
    try {
      await onUnlinkChain(card.beat_index);
    } finally {
      setIsUnlinking(false);
    }
  };

  const isVertical = aspectRatio === '9:16';
  const isCardBusy = isRendering || isRenderingBeat || card.render_status === 'rendering';
  const isLastShot = card.beat_index >= totalBeats - 1;
  const startFrameSrc = card.start_frame_path || card.keyframe_path;

  return (
    <div className={`beat-card ${card.is_chained ? 'beat-card-chained' : ''}`}>
      {/* 1. ElevenLabs Document Header: Scene Number + Duration + Clean Status */}
      <div className="beat-card-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span className="beat-scene-tag">SCENE {(card.beat_index + 1).toString().padStart(2, '0')}</span>
          <span className="beat-duration-pill">{card.duration_seconds || 5.0}s</span>

          {card.is_chained && (
            <span
              style={{
                fontSize: '0.68rem',
                color: '#60a5fa',
                background: 'rgba(59, 130, 246, 0.1)',
                border: '1px solid rgba(59, 130, 246, 0.25)',
                padding: '2px 7px',
                borderRadius: '4px',
                display: 'inline-flex',
                alignItems: 'center',
                gap: '4px',
                fontWeight: 500,
              }}
              title={`Anchored to final frame of Scene ${(card.chained_from_beat ?? (card.beat_index - 1)) + 1}`}
            >
              <LinkIcon size={11} /> Chained
            </span>
          )}

          {card.is_custom_image && (
            <span
              style={{
                fontSize: '0.68rem',
                color: 'var(--text-muted)',
                background: 'rgba(255, 255, 255, 0.06)',
                padding: '2px 6px',
                borderRadius: '4px',
              }}
            >
              Custom Plate
            </span>
          )}
        </div>

        {/* Minimalist Status Indicator */}
        <div className="beat-status-badge">
          {card.render_status === 'completed' ? (
            <span className="beat-status-badge completed">
              <CheckCircle2 size={13} /> Ready
            </span>
          ) : isCardBusy ? (
            <span className="beat-status-badge rendering">
              <RefreshCw size={13} className="spin-slow" /> Rendering
            </span>
          ) : card.render_status === 'failed' ? (
            <span className="beat-status-badge failed" title={card.error_message || 'Render failed'}>
              <AlertCircle size={13} /> Error
            </span>
          ) : (
            <span className="beat-status-badge pending">
              <Clock size={13} /> Standby
            </span>
          )}
        </div>
      </div>

      {/* Upstream Invalidation Alert */}
      {card.chain_out_of_sync && (
        <div
          style={{
            margin: '8px 12px 0',
            padding: '6px 10px',
            background: 'var(--accent-amber-subtle)',
            border: '1px solid rgba(245, 158, 11, 0.3)',
            borderRadius: '6px',
            fontSize: '0.72rem',
            color: '#fbbf24',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: '8px',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
            <AlertTriangle size={13} />
            <span>Upstream scene re-rendered</span>
          </div>
          <button
            type="button"
            onClick={handleChainFrameClick}
            disabled={isChaining}
            className="btn-secondary"
            style={{ padding: '2px 8px', fontSize: '0.68rem', borderColor: 'rgba(245, 158, 11, 0.4)', color: '#fbbf24' }}
          >
            {isChaining ? 'Updating...' : 'Update Chain'}
          </button>
        </div>
      )}

      {/* 2. Visual Keyframe Viewport with Hover Actions Overlay */}
      <div className={`keyframe-container ${isVertical ? 'vertical' : ''}`}>
        {/* Floating overlay actions on hover */}
        <div className="keyframe-overlay-actions">
          <button
            type="button"
            disabled={isUploading || isCardBusy}
            className="keyframe-action-pill"
            onClick={() => fileInputRef.current?.click()}
            title="Upload custom keyframe photo"
          >
            <Upload size={12} className={isUploading ? 'spin-slow' : ''} />
            <span>{isUploading ? '...' : 'Upload'}</span>
          </button>

          <button
            type="button"
            disabled={isRerolling || isCardBusy}
            className="keyframe-action-pill"
            onClick={handleGenerateImageClick}
            title="Re-generate keyframe image plate"
          >
            <RefreshCw size={12} className={isRerolling ? 'spin-slow' : ''} />
            <span>{isRerolling ? '...' : 'Re-roll'}</span>
          </button>
        </div>

        <input
          ref={fileInputRef}
          type="file"
          accept="image/*"
          style={{ display: 'none' }}
          onChange={handleFileChange}
        />

        {card.output_video_path ? (
          <>
            <video
              src={card.output_video_path}
              controls
              autoPlay
              loop
              muted
              className="keyframe-video"
              style={{ width: '100%', height: '100%', objectFit: 'contain' }}
              onLoadedMetadata={(e) => {
                const v = e.currentTarget;
                if (v.videoWidth && v.videoHeight) {
                  setVideoDimensions({ width: v.videoWidth, height: v.videoHeight });
                }
              }}
            />
            {videoDimensions && (
              <div className="video-dimension-badge" title="Native Video Dimensions">
                {videoDimensions.width}×{videoDimensions.height}
              </div>
            )}
          </>
        ) : startFrameSrc ? (
          <img
            src={startFrameSrc}
            alt={`Scene ${card.beat_index + 1}`}
            className="keyframe-img"
          />
        ) : (
          <div className="keyframe-placeholder">
            <Video size={28} />
            <span>Scene artwork pending...</span>
          </div>
        )}
      </div>

      <div className="card-body">
        {/* 3. ElevenLabs Signature Voice & Screenplay Dialogue Block */}
        <div className="eleven-dialogue-block">
          <div className="eleven-voice-row">
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <div className="eleven-voice-chip">
                <Mic size={12} color="var(--accent-emerald)" />
                <span>{getVoicePersonaLabel(card.voice_actor)}</span>
                <span className="waveform-mini">
                  <span className="waveform-bar" />
                  <span className="waveform-bar" />
                  <span className="waveform-bar" />
                  <span className="waveform-bar" />
                  <span className="waveform-bar" />
                </span>
              </div>
              {card.speaker && card.speaker !== 'Voiceover' && (
                <span style={{ fontSize: '0.72rem', color: 'var(--text-dim)' }}>
                  ({card.speaker})
                </span>
              )}
            </div>

            <select
              value={card.voice_actor || 'auto'}
              disabled={isCardBusy}
              onChange={(e) => {
                if (onUpdateCard) {
                  onUpdateCard(card.beat_index, { voice_actor: e.target.value });
                }
              }}
              style={{
                background: 'transparent',
                border: '1px solid var(--border-subtle)',
                borderRadius: '5px',
                color: 'var(--text-muted)',
                fontSize: '0.72rem',
                padding: '2px 6px',
                cursor: 'pointer',
                outline: 'none',
              }}
            >
              <option value="auto">✨ Auto Inferred</option>
              <option value="en-US-ChristopherNeural">🎙️ Christopher (Deep Male)</option>
              <option value="female_narrator">👩 Ava (Female Narrator)</option>
              <option value="male_casual">👨 Casual Male</option>
              <option value="female_sarcastic">😏 Female Sarcastic</option>
              <option value="deep_villain">👿 Deep Villain</option>
              <option value="kid">🧸 Kid Voice</option>
              <option value="cartoon_animal">🐿️ Cartoon Animal</option>
              <option value="energetic_action">⚡ Action Voice</option>
            </select>
          </div>

          {card.dialogue_text && card.dialogue_text.trim() ? (
            <p className="eleven-dialogue-text">
              “{card.dialogue_text}”
            </p>
          ) : (
            <p style={{ margin: 0, fontSize: '0.76rem', color: 'var(--text-dim)', fontStyle: 'normal' }}>
              Silent scene (Atmospheric sound & score)
            </p>
          )}
        </div>

        {/* 4. Prompt Studio (Segmented Visual Plate vs Video Motion) */}
        <div className="eleven-prompt-box">
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div className="segmented-control">
              <button
                type="button"
                className={`segment-btn ${activePromptTab === 'image' ? 'active' : ''}`}
                onClick={() => setActivePromptTab('image')}
              >
                <ImageIcon size={12} />
                <span>Visual Plate</span>
              </button>
              <button
                type="button"
                className={`segment-btn ${activePromptTab === 'motion' ? 'active' : ''}`}
                onClick={() => setActivePromptTab('motion')}
              >
                <Film size={12} />
                <span>Video Motion</span>
              </button>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <button
                type="button"
                onClick={() => handleCopyPrompt(activePromptTab)}
                style={{
                  background: 'transparent',
                  border: 'none',
                  color: copiedTab === activePromptTab ? 'var(--accent-emerald)' : 'var(--text-dim)',
                  fontSize: '0.7rem',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '3px',
                }}
              >
                {copiedTab === activePromptTab ? <Check size={11} /> : <Copy size={11} />}
                <span>{copiedTab === activePromptTab ? 'Copied' : 'Copy'}</span>
              </button>

              {activePromptTab === 'image' ? (
                <button
                  type="button"
                  onClick={() => {
                    if (isEditingImagePrompt) {
                      setImagePromptText(card.image_prompt || card.visual_prompt);
                    }
                    setIsEditingImagePrompt(!isEditingImagePrompt);
                  }}
                  style={{
                    background: 'transparent',
                    border: 'none',
                    color: 'var(--text-muted)',
                    fontSize: '0.7rem',
                    cursor: 'pointer',
                    fontWeight: 500,
                  }}
                >
                  {isEditingImagePrompt ? 'Cancel' : 'Edit'}
                </button>
              ) : (
                <button
                  type="button"
                  onClick={() => {
                    if (isEditingMotionPrompt) {
                      setMotionPromptText(getCardMotionPrompt(card));
                    }
                    setIsEditingMotionPrompt(!isEditingMotionPrompt);
                  }}
                  style={{
                    background: 'transparent',
                    border: 'none',
                    color: 'var(--text-muted)',
                    fontSize: '0.7rem',
                    cursor: 'pointer',
                    fontWeight: 500,
                  }}
                >
                  {isEditingMotionPrompt ? 'Cancel' : 'Edit'}
                </button>
              )}
            </div>
          </div>

          {/* Prompt Body */}
          {activePromptTab === 'image' ? (
            isEditingImagePrompt ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                <textarea
                  className="prompt-textarea"
                  style={{ minHeight: '64px', fontSize: '0.8rem' }}
                  value={imagePromptText}
                  onChange={(e) => setImagePromptText(e.target.value)}
                  placeholder="Describe keyframe image artwork..."
                />
                <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '6px' }}>
                  <button
                    type="button"
                    className="btn-secondary"
                    style={{ padding: '5px 10px', fontSize: '0.74rem' }}
                    onClick={handleSaveImagePrompt}
                  >
                    <Check size={12} />
                    <span>Save Plate</span>
                  </button>
                  <button
                    type="button"
                    disabled={isRerolling || isCardBusy}
                    className="btn-primary"
                    style={{ padding: '5px 12px', fontSize: '0.74rem' }}
                    onClick={handleGenerateImageClick}
                  >
                    <Sparkles size={12} className={isRerolling ? 'spin-slow' : ''} />
                    <span>{isRerolling ? 'Generating...' : 'Save & Generate'}</span>
                  </button>
                </div>
              </div>
            ) : (
              <p style={{ margin: 0, fontSize: '0.8rem', color: 'var(--text-main)', lineHeight: 1.45 }}>
                {imagePromptText}
              </p>
            )
          ) : (
            isEditingMotionPrompt ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                <textarea
                  className="prompt-textarea"
                  style={{ minHeight: '64px', fontSize: '0.8rem' }}
                  value={motionPromptText}
                  onChange={(e) => setMotionPromptText(e.target.value)}
                  placeholder="Describe camera movement and temporal motion..."
                />
                <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '6px' }}>
                  <button
                    type="button"
                    className="btn-primary"
                    style={{ padding: '5px 12px', fontSize: '0.74rem' }}
                    onClick={handleSaveMotionPrompt}
                  >
                    <Check size={12} />
                    <span>Save Motion</span>
                  </button>
                </div>
              </div>
            ) : (
              <p style={{ margin: 0, fontSize: '0.8rem', color: 'var(--text-main)', lineHeight: 1.45 }}>
                {motionPromptText}
              </p>
            )
          )}

          {/* Budget & Auto-fit line */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', paddingTop: '4px' }}>
            <span style={{
              fontSize: '0.68rem',
              fontFamily: 'var(--font-mono)',
              color: isOverLimit ? '#f87171' : 'var(--text-dim)',
            }}>
              {activePromptText.length} / {charLimit} chars
            </span>

            {isOverLimit && (
              <button
                type="button"
                disabled={isAdaptingPrompt}
                onClick={handleAutoFitPrompt}
                className="btn-secondary"
                style={{ padding: '2px 6px', fontSize: '0.66rem', color: 'var(--accent-amber)' }}
              >
                <span>{isAdaptingPrompt ? 'Fitting...' : '✨ Auto-Fit Prompt'}</span>
              </button>
            )}
          </div>
        </div>

        {/* Frame Conditioning & Visual Assets (First Frame, Dual-Frame Interpolation, References) */}
        <div className="conditioning-panel">
          <div className="conditioning-panel-header">
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <Layers size={13} color="var(--accent-cyan)" />
              <span className="conditioning-title">Frame Conditioning & Assets</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '4px', flexWrap: 'wrap' }}>
              {currentModelConfig.supportsI2V ? (
                <span className="conditioning-pill active" title="Supports First Frame / Start Frame conditioning">
                  First Frame
                </span>
              ) : (
                <span className="conditioning-pill disabled" title="Model does not support image conditioning (T2V only)">
                  T2V Only
                </span>
              )}
              {currentModelConfig.supportsDualFrame ? (
                <span className="conditioning-pill active" title="Supports Start + End Frame Interpolation">
                  Dual Frame
                </span>
              ) : (
                <span className="conditioning-pill disabled" title="End Frame interpolation not supported by this model">
                  No Dual Frame
                </span>
              )}
              {currentModelConfig.supportsReferenceImages ? (
                <span className="conditioning-pill active" title={`Supports up to ${currentModelConfig.maxReferenceImages} reference images`}>
                  Refs ({card.reference_image_paths?.length || 0}/{currentModelConfig.maxReferenceImages})
                </span>
              ) : (
                <span className="conditioning-pill disabled" title="Reference images not supported by this model">
                  No Refs
                </span>
              )}
            </div>
          </div>

          {/* Hidden inputs for start, end, and reference image uploads */}
          <input
            ref={fileInputStartRef}
            type="file"
            accept="image/*"
            style={{ display: 'none' }}
            onChange={(e) => handleFrameUpload(e, 'start_frame')}
          />
          <input
            ref={fileInputEndRef}
            type="file"
            accept="image/*"
            style={{ display: 'none' }}
            onChange={(e) => handleFrameUpload(e, 'end_frame')}
          />
          <input
            ref={fileInputRefImagesRef}
            type="file"
            accept="image/*"
            style={{ display: 'none' }}
            onChange={(e) => handleFrameUpload(e, 'reference_image')}
          />

          <div className="conditioning-slots-row">
            {/* Slot 1: First / Start Frame */}
            <div className={`conditioning-slot ${!currentModelConfig.supportsI2V ? 'slot-disabled' : ''}`}>
              <div className="conditioning-slot-label">
                <span>First Frame</span>
                {card.is_chained && (
                  <span className="slot-badge-chained">Chained</span>
                )}
              </div>
              {!currentModelConfig.supportsI2V ? (
                <div className="conditioning-disabled-placeholder" title={`${currentModelConfig.name} is Text-to-Video only`}>
                  <span>T2V Only</span>
                </div>
              ) : startFrameSrc ? (
                <div className="conditioning-thumb-wrapper">
                  <img src={startFrameSrc} alt="Start frame" className="conditioning-thumb" />
                  <div className="conditioning-thumb-overlay">
                    <button
                      type="button"
                      disabled={uploadingTarget === 'start_frame' || isCardBusy}
                      onClick={() => fileInputStartRef.current?.click()}
                      className="conditioning-icon-btn"
                      title="Replace start frame"
                    >
                      <Upload size={11} className={uploadingTarget === 'start_frame' ? 'spin-slow' : ''} />
                    </button>
                    <button
                      type="button"
                      disabled={isCardBusy}
                      onClick={() => handleRemoveFrameClick('start_frame')}
                      className="conditioning-icon-btn danger"
                      title="Clear start frame"
                    >
                      <Trash2 size={11} />
                    </button>
                  </div>
                </div>
              ) : (
                <button
                  type="button"
                  disabled={uploadingTarget === 'start_frame' || isCardBusy}
                  onClick={() => fileInputStartRef.current?.click()}
                  className="conditioning-dropzone"
                  title="Upload First Frame for Image-to-Video"
                >
                  <Upload size={12} className={uploadingTarget === 'start_frame' ? 'spin-slow' : ''} />
                  <span>{uploadingTarget === 'start_frame' ? '...' : '+ Start'}</span>
                </button>
              )}
            </div>

            {/* Slot 2: Last / End Frame (Dual-Frame Interpolation) */}
            <div className={`conditioning-slot ${!currentModelConfig.supportsDualFrame ? 'slot-disabled' : ''}`}>
              <div className="conditioning-slot-label">
                <span>Last Frame</span>
                {currentModelConfig.supportsDualFrame && <span className="slot-badge-subtle">Morph</span>}
              </div>
              {!currentModelConfig.supportsDualFrame ? (
                <div className="conditioning-disabled-placeholder" title={`${currentModelConfig.name} does not support dual-frame interpolation`}>
                  <span>N/A</span>
                </div>
              ) : card.end_frame_path ? (
                <div className="conditioning-thumb-wrapper">
                  <img src={card.end_frame_path} alt="End frame" className="conditioning-thumb" />
                  <div className="conditioning-thumb-overlay">
                    <button
                      type="button"
                      disabled={uploadingTarget === 'end_frame' || isCardBusy}
                      onClick={() => fileInputEndRef.current?.click()}
                      className="conditioning-icon-btn"
                      title="Replace end frame"
                    >
                      <Upload size={11} className={uploadingTarget === 'end_frame' ? 'spin-slow' : ''} />
                    </button>
                    <button
                      type="button"
                      disabled={isCardBusy}
                      onClick={() => handleRemoveFrameClick('end_frame')}
                      className="conditioning-icon-btn danger"
                      title="Clear end frame"
                    >
                      <Trash2 size={11} />
                    </button>
                  </div>
                </div>
              ) : (
                <button
                  type="button"
                  disabled={uploadingTarget === 'end_frame' || isCardBusy}
                  onClick={() => fileInputEndRef.current?.click()}
                  className="conditioning-dropzone"
                  title="Upload End Frame for start-to-end interpolation"
                >
                  <Plus size={12} className={uploadingTarget === 'end_frame' ? 'spin-slow' : ''} />
                  <span>{uploadingTarget === 'end_frame' ? '...' : '+ End'}</span>
                </button>
              )}
            </div>

            {/* Slot 3: Reference Images (Subject / Character Sheet) */}
            <div className={`conditioning-slot ref-slot ${!currentModelConfig.supportsReferenceImages ? 'slot-disabled' : ''}`}>
              <div className="conditioning-slot-label">
                <span>References</span>
                {currentModelConfig.supportsReferenceImages && (
                  <span className="slot-badge-subtle">
                    {card.reference_image_paths?.length || 0}/{currentModelConfig.maxReferenceImages}
                  </span>
                )}
              </div>
              {!currentModelConfig.supportsReferenceImages ? (
                <div className="conditioning-disabled-placeholder" title={`${currentModelConfig.name} does not support reference images`}>
                  <span>N/A</span>
                </div>
              ) : (
                <div className="ref-images-container">
                  {(card.reference_image_paths || []).map((imgUrl, idx) => (
                    <div key={idx} className="ref-thumb-box" title={`Reference asset ${idx + 1}`}>
                      <img src={imgUrl} alt={`Reference ${idx + 1}`} className="ref-thumb-img" />
                      <button
                        type="button"
                        disabled={isCardBusy}
                        onClick={() => handleRemoveFrameClick('reference_image', idx)}
                        className="ref-remove-btn"
                        title="Remove reference"
                      >
                        <X size={10} />
                      </button>
                    </div>
                  ))}

                  {(card.reference_image_paths?.length || 0) < currentModelConfig.maxReferenceImages && (
                    <button
                      type="button"
                      disabled={uploadingTarget === 'reference_image' || isCardBusy}
                      onClick={() => fileInputRefImagesRef.current?.click()}
                      className="ref-add-btn"
                      title={`Upload reference image (${(card.reference_image_paths?.length || 0) + 1}/${currentModelConfig.maxReferenceImages})`}
                    >
                      <ImagePlus size={12} className={uploadingTarget === 'reference_image' ? 'spin-slow' : ''} />
                      <span>{uploadingTarget === 'reference_image' ? '...' : '+ Ref'}</span>
                    </button>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* 5. Clean Model & Provider Routing Toolbar */}
        <div className="model-routing-bar">
          {/* Tier 1: Model Selector Trigger & Rates Inspector */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', width: '100%' }}>
            <button
              ref={triggerBtnRef}
              type="button"
              className="model-pill-trigger"
              onClick={() => {
                updatePopoverPosition();
                setIsModelMenuOpen(!isModelMenuOpen);
              }}
              style={{ flex: 1, minWidth: 0 }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', minWidth: 0, overflow: 'hidden' }}>
                <span style={{ fontSize: '0.74rem', fontWeight: 600, color: 'var(--text-main)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                  {currentModelConfig.name}
                </span>
                <span style={{ fontSize: '0.62rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', whiteSpace: 'nowrap' }}>
                  <strong style={{ color: 'var(--accent-emerald)' }}>${(activeResolutionRates as any)[activeResolutionRates.cheapest]?.toFixed(3)}/s</strong> ({activeResolutionRates.cheapest})
                </span>
              </div>
              <ChevronDown size={13} color="var(--text-muted)" style={{ transform: isModelMenuOpen ? 'rotate(180deg)' : 'none', transition: 'transform 0.15s ease', flexShrink: 0 }} />
            </button>

            <button
              type="button"
              onClick={() => setIsCostModalOpen(true)}
              className="btn-secondary"
              style={{
                padding: '3px 9px',
                fontSize: '0.68rem',
                height: '32px',
                color: 'var(--accent-emerald)',
                whiteSpace: 'nowrap',
                flexShrink: 0,
              }}
              title="View live provider rate comparison"
            >
              <span>Rates</span>
            </button>

            <button
              type="button"
              onClick={() => {
                const nextVal = !allowProviderCascade;
                setAllowProviderCascade(nextVal);
                onUpdateCard?.(card.beat_index, { allow_provider_cascade: nextVal } as any);
              }}
              className="btn-secondary"
              style={{
                padding: '3px 8px',
                fontSize: '0.68rem',
                height: '32px',
                display: 'flex',
                alignItems: 'center',
                gap: '4px',
                color: allowProviderCascade ? 'var(--accent-emerald)' : '#f87171',
                borderColor: allowProviderCascade ? 'rgba(16, 185, 129, 0.35)' : 'rgba(239, 68, 68, 0.35)',
                background: allowProviderCascade ? 'rgba(16, 185, 129, 0.08)' : 'rgba(239, 68, 68, 0.08)',
                whiteSpace: 'nowrap',
                flexShrink: 0,
                cursor: 'pointer',
              }}
              title={
                allowProviderCascade
                  ? 'Auto-Cascade Failover ON: If the chosen provider fails (5xx/quota), automatically cascades down to next cheapest provider at $0 failure cost. Click to disable.'
                  : 'Auto-Cascade Failover OFF: Strict mode. Will NOT cascade to secondary providers if rendering fails. Click to enable.'
              }
            >
              {allowProviderCascade ? <ShieldCheck size={12} /> : <ShieldAlert size={12} />}
              <span>{allowProviderCascade ? 'Cascade ON' : 'Cascade OFF'}</span>
            </button>
          </div>

          {/* Tier 2: Modality (T2V/I2V), Resolution (480P/720P/1080P/4K), and Audio */}
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '6px', width: '100%' }}>
            {/* T2V / I2V Modality */}
            <div className="segmented-control" title="Generation Modality (T2V: Pure Text | I2V: Keyframe guided)">
              <button
                type="button"
                className={`segment-btn ${modality === 't2v' ? 'active' : ''}`}
                onClick={() => {
                  setModality('t2v');
                  onUpdateCard?.(card.beat_index, { modality: 't2v' } as any);
                }}
                style={{ padding: '2px 8px', fontSize: '0.68rem', height: '24px' }}
              >
                T2V
              </button>
              <button
                type="button"
                className={`segment-btn ${modality === 'i2v' ? 'active' : ''}`}
                onClick={() => {
                  setModality('i2v');
                  onUpdateCard?.(card.beat_index, { modality: 'i2v' } as any);
                }}
                style={{ padding: '2px 8px', fontSize: '0.68rem', height: '24px' }}
              >
                I2V
              </button>
            </div>

            {/* Target Resolution Switcher: 480P, 720P, 1080P, 4K */}
            <div className="segmented-control" title="Target Render Resolution (Rates scale with resolution)">
              {(['480p', '720p', '1080p', '4k'] as const).map((r) => (
                <button
                  key={r}
                  type="button"
                  className={`segment-btn ${resolution === r ? 'active' : ''}`}
                  onClick={() => {
                    setResolution(r);
                    setPreviewResolution(r);
                    onUpdateCard?.(card.beat_index, { resolution: r } as any);
                  }}
                  style={{
                    padding: '2px 6px',
                    fontSize: '0.65rem',
                    height: '24px',
                    fontWeight: resolution === r ? 700 : 500,
                    color: resolution === r ? 'var(--accent-cyan)' : 'var(--text-muted)',
                  }}
                >
                  {r.toUpperCase()}
                </button>
              ))}
            </div>

            {currentModelConfig.supportsAudio && (
              <button
                type="button"
                onClick={() => {
                  const nextAudio = !hasNativeAudio;
                  setHasNativeAudio(nextAudio);
                  onUpdateCard?.(card.beat_index, { native_audio: nextAudio, has_clip_audio: nextAudio } as any);
                }}
                className="btn-secondary"
                style={{
                  padding: '2px 7px',
                  fontSize: '0.66rem',
                  height: '24px',
                  whiteSpace: 'nowrap',
                  color: hasNativeAudio ? 'var(--accent-emerald)' : 'var(--text-muted)',
                  borderColor: hasNativeAudio ? 'var(--accent-emerald-border)' : 'var(--border-subtle)',
                  background: hasNativeAudio ? 'var(--accent-emerald-subtle)' : undefined,
                }}
                title={hasNativeAudio ? 'Native Clip Audio active' : 'Clip Audio off'}
              >
                <Mic size={11} />
                <span>{hasNativeAudio ? 'Audio ON' : 'Audio OFF'}</span>
              </button>
            )}
          </div>
        </div>

        {/* Multi-Take History Switcher */}
        {card.takes && card.takes.length > 0 && (
          <TakeSwitcher
            projectId={projectId || ''}
            beatIndex={card.beat_index}
            takes={card.takes}
            activeTakeId={card.active_take_id}
            onSelectTake={(takeId) => {
              if (onSelectTake) {
                onSelectTake(card.beat_index, takeId);
              }
            }}
          />
        )}
      </div>

      {/* 6. Card Action Footer: Clean Camera Meta & Primary Action */}
      <div className="card-footer">
        <div style={{ display: 'flex', alignItems: 'center', gap: '5px', fontSize: '0.74rem', color: 'var(--text-dim)', whiteSpace: 'nowrap', flexShrink: 0 }}>
          <Camera size={13} />
          <span style={{ textTransform: 'capitalize' }}>{card.camera_motion.replace('_', ' ')}</span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flexWrap: 'wrap', justifyContent: 'flex-end' }}>
          {card.render_status === 'completed' && !isLastShot && onChainFrame && (
            <button
              type="button"
              disabled={isChaining || isCardBusy}
              onClick={handleChainFrameClick}
              className="btn-secondary"
              style={{ padding: '5px 9px', fontSize: '0.74rem' }}
              title={`Anchor final frame to Scene ${card.beat_index + 2}`}
            >
              <LinkIcon size={12} className={isChaining ? 'spin-slow' : ''} />
              <span>{isChaining ? 'Chaining...' : `Chain to Scene ${card.beat_index + 2}`}</span>
            </button>
          )}

          {(card.output_video_path || card.render_status === 'completed') && (
            <>
              <button
                type="button"
                disabled={isExtending || isCardBusy}
                onClick={handleExtendVideo}
                className="btn-secondary"
                style={{ padding: '5px 8px', fontSize: '0.74rem' }}
                title="Extend this shot by +5s continuation"
              >
                <FastForward size={12} className={isExtending ? 'spin-slow' : ''} />
                <span>+5s</span>
              </button>

              <button
                type="button"
                disabled={isUpscaling || isCardBusy}
                onClick={handleUpscaleVideo}
                className="btn-secondary"
                style={{ padding: '5px 8px', fontSize: '0.74rem' }}
                title="Upscale to 4K Ultra-HD"
              >
                <Maximize2 size={12} className={isUpscaling ? 'spin-slow' : ''} />
                <span>4K</span>
              </button>
            </>
          )}

          {card.is_chained && onUnlinkChain && (
            <button
              type="button"
              disabled={isUnlinking || isCardBusy}
              onClick={handleUnlinkClick}
              className="btn-secondary"
              style={{ padding: '5px 8px', fontSize: '0.74rem', color: 'var(--accent-rose)' }}
              title="Unlink chained frame"
            >
              <UnlinkIcon size={12} />
            </button>
          )}

          {onRenderBeat && (
            <button
              type="button"
              disabled={isCardBusy}
              onClick={handleRenderBeatClick}
              className={card.render_status === 'completed' ? 'btn-secondary' : 'btn-primary'}
              style={{ padding: '6px 14px', fontSize: '0.76rem' }}
            >
              {isRenderingBeat || card.render_status === 'rendering' ? (
                <>
                  <RefreshCw size={12} className="spin-slow" />
                  <span>Rendering...</span>
                </>
              ) : card.render_status === 'completed' ? (
                <>
                  <RefreshCw size={12} />
                  <span>Re-render</span>
                </>
              ) : (
                <>
                  <Play size={12} />
                  <span>Render Clip</span>
                </>
              )}
            </button>
          )}
        </div>
      </div>

      <CostTransparencyModal
        isOpen={isCostModalOpen}
        onClose={() => setIsCostModalOpen(false)}
        modelId={selectedModel}
        durationSec={card.duration_seconds || 5.0}
        resolution={resolution}
        onSelectResolution={(res) => {
          setResolution(res);
          setPreviewResolution(res);
          onUpdateCard?.(card.beat_index, { resolution: res } as any);
        }}
        hasNativeAudio={hasNativeAudio}
        selectedProviderOverride={selectedProviderOverride}
        allowProviderCascade={allowProviderCascade}
        onSelectProvider={(p) => {
          setSelectedProviderOverride(p);
          onUpdateCard?.(card.beat_index, { provider_override: p || 'auto' } as any);
        }}
        onToggleCascade={(val) => {
          setAllowProviderCascade(val);
          onUpdateCard?.(card.beat_index, { allow_provider_cascade: val } as any);
        }}
        onChangeModel={(m) => {
          setSelectedModel(m);
          onUpdateCard?.(card.beat_index, { model_id: m } as any);
        }}
      />

      {/* Floating Model Picker Popover rendered via React Portal */}
      {isModelMenuOpen && typeof document !== 'undefined' && createPortal(
        <div
          className="model-picker-backdrop"
          onClick={() => setIsModelMenuOpen(false)}
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(0, 0, 0, 0.45)',
            backdropFilter: 'blur(3px)',
            WebkitBackdropFilter: 'blur(3px)',
            zIndex: 9998,
            display: 'flex',
            alignItems: popoverCoords.isCentered ? 'center' : 'flex-start',
            justifyContent: popoverCoords.isCentered ? 'center' : 'flex-start',
          }}
        >
          <div
            ref={modelMenuRef}
            className="model-picker-popover"
            style={{
              position: 'fixed',
              top: popoverCoords.top !== undefined ? `${popoverCoords.top}px` : undefined,
              bottom: popoverCoords.bottom !== undefined ? `${popoverCoords.bottom}px` : undefined,
              left: `${popoverCoords.left}px`,
              width: `${popoverCoords.width}px`,
              maxHeight: `${popoverCoords.maxHeight}px`,
              background: 'var(--bg-elevated)',
              border: '1px solid var(--border-medium)',
              borderRadius: '12px',
              boxShadow: '0 24px 60px rgba(0, 0, 0, 0.95), 0 0 1px rgba(255, 255, 255, 0.2)',
              zIndex: 9999,
              display: 'flex',
              flexDirection: 'column',
              overflow: 'hidden',
              animation: 'scaleUp 0.15s cubic-bezier(0.16, 1, 0.3, 1)',
            }}
            onClick={(e) => e.stopPropagation()}
          >
            {/* Header */}
            <div style={{
              padding: '12px 16px',
              borderBottom: '1px solid var(--border-subtle)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              background: 'rgba(0, 0, 0, 0.2)'
            }}>
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <h4 style={{ margin: 0, fontSize: '0.88rem', fontWeight: 700, color: 'var(--text-main)' }}>
                    Select Video Diffusion Model
                  </h4>
                  <span style={{
                    fontSize: '0.65rem',
                    fontWeight: 600,
                    padding: '1px 6px',
                    borderRadius: '10px',
                    background: 'rgba(255, 255, 255, 0.08)',
                    color: 'var(--text-muted)'
                  }}>
                    Scene #{card.beat_index + 1}
                  </span>
                </div>
                <p style={{ margin: '2px 0 0 0', fontSize: '0.7rem', color: 'var(--text-dim)' }}>
                  34 production video models with real-time multi-provider cost arbitrage
                </p>
              </div>
              <button
                type="button"
                onClick={() => setIsModelMenuOpen(false)}
                className="modal-close-btn"
                title="Close model picker"
              >
                <X size={16} />
              </button>
            </div>

            {/* Search & Family Filter Bar */}
            <div style={{ padding: '10px 14px 8px', borderBottom: '1px solid var(--border-subtle)', display: 'flex', flexDirection: 'column', gap: '8px' }}>
              <div style={{ position: 'relative' }}>
                <Search size={14} style={{ position: 'absolute', left: '10px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-dim)' }} />
                <input
                  type="text"
                  placeholder="Search 34 models (e.g. Kling 3.0, Seedance, 4K, Audio)..."
                  value={modelSearchQuery}
                  onChange={(e) => setModelSearchQuery(e.target.value)}
                  autoFocus
                  style={{
                    width: '100%',
                    background: 'var(--bg-input)',
                    border: '1px solid var(--border-subtle)',
                    borderRadius: '8px',
                    padding: '7px 30px 7px 32px',
                    fontSize: '0.78rem',
                    color: 'var(--text-main)',
                    outline: 'none',
                  }}
                />
                {modelSearchQuery && (
                  <button
                    type="button"
                    onClick={() => setModelSearchQuery('')}
                    style={{
                      position: 'absolute',
                      right: '8px',
                      top: '50%',
                      transform: 'translateY(-50%)',
                      background: 'transparent',
                      border: 'none',
                      color: 'var(--text-dim)',
                      cursor: 'pointer',
                      padding: '2px',
                    }}
                  >
                    <X size={12} />
                  </button>
                )}
              </div>

              {/* Family Filters Tabs */}
              <div style={{ display: 'flex', gap: '4px', overflowX: 'auto', paddingBottom: '2px' }}>
                {[
                  { id: 'all', label: 'All Models' },
                  { id: 'kling', label: 'Kling AI' },
                  { id: 'seedance', label: 'Seedance' },
                  { id: 'runway', label: 'Runway' },
                  { id: 'minimax', label: 'MiniMax' },
                  { id: 'veo', label: 'Veo' },
                  { id: 'wan', label: 'Wan' },
                  { id: 'grok', label: 'Grok' },
                  { id: 'luma', label: 'Luma' },
                  { id: 'budget', label: 'Budget' },
                ].map((cat) => (
                  <button
                    key={cat.id}
                    type="button"
                    onClick={() => setSelectedFamilyFilter(cat.id)}
                    style={{
                      padding: '3px 8px',
                      borderRadius: '6px',
                      fontSize: '0.68rem',
                      fontWeight: 500,
                      whiteSpace: 'nowrap',
                      background: selectedFamilyFilter === cat.id ? 'var(--text-main)' : 'rgba(255, 255, 255, 0.04)',
                      color: selectedFamilyFilter === cat.id ? '#0a0b0d' : 'var(--text-muted)',
                      border: selectedFamilyFilter === cat.id ? 'none' : '1px solid var(--border-subtle)',
                      cursor: 'pointer',
                      transition: 'all 0.12s ease',
                    }}
                  >
                    {cat.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Resolution Rate Preview Switcher */}
            <div style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              padding: '6px 14px',
              borderBottom: '1px solid var(--border-subtle)',
              background: 'rgba(255, 255, 255, 0.02)',
            }}>
              <span style={{ fontSize: '0.68rem', color: 'var(--text-dim)', fontWeight: 500 }}>
                Live rates shown for:
              </span>
              <div className="segmented-control">
                {(['480p', '720p', '1080p', '4k'] as const).map((r) => (
                  <button
                    key={r}
                    type="button"
                    className={`segment-btn ${previewResolution === r ? 'active' : ''}`}
                    onClick={(e) => {
                      e.stopPropagation();
                      setPreviewResolution(r);
                    }}
                    style={{
                      padding: '2px 7px',
                      fontSize: '0.64rem',
                      fontWeight: previewResolution === r ? 700 : 500,
                      color: previewResolution === r ? 'var(--accent-cyan)' : 'var(--text-muted)',
                    }}
                  >
                    {r.toUpperCase()}
                  </button>
                ))}
              </div>
            </div>

            {/* Scrollable Model List */}
            <div style={{ flex: 1, overflowY: 'auto', padding: '10px 14px' }}>
              {totalFilteredCount === 0 ? (
                <div style={{ textAlign: 'center', padding: '28px', color: 'var(--text-dim)', fontSize: '0.8rem' }}>
                  No models matching "{modelSearchQuery}"
                </div>
              ) : (
                filteredModelGroups.map((group) => (
                  <div key={group.family} style={{ marginBottom: '12px' }}>
                    <div style={{
                      fontSize: '0.66rem',
                      fontWeight: 700,
                      color: 'var(--text-dim)',
                      textTransform: 'uppercase',
                      letterSpacing: '0.05em',
                      padding: '2px 4px',
                      marginBottom: '4px',
                    }}>
                      {group.label}
                    </div>

                    {group.models.map((m) => {
                      const isSelected = selectedModel === m.id;
                      const baseRates = MODEL_PROVIDER_RATES[m.id] || { fal: 0.05, apidot: 0.05, kie: 0.05, cheapest: 'apidot' };
                      const rates = getRatesForResolution(baseRates, previewResolution);

                      return (
                        <div
                          key={m.id}
                          onClick={() => {
                            setSelectedModel(m.id);
                            setIsModelMenuOpen(false);
                            onUpdateCard?.(card.beat_index, { model_id: m.id } as any);
                          }}
                          style={{
                            padding: '8px 10px',
                            borderRadius: '8px',
                            cursor: 'pointer',
                            background: isSelected ? 'rgba(16, 185, 129, 0.1)' : 'var(--bg-input)',
                            border: isSelected ? '1px solid var(--accent-emerald-border)' : '1px solid var(--border-subtle)',
                            marginBottom: '6px',
                            transition: 'all 0.12s ease',
                          }}
                          onMouseEnter={(e) => {
                            if (!isSelected) {
                              e.currentTarget.style.background = 'rgba(255, 255, 255, 0.05)';
                              e.currentTarget.style.borderColor = 'var(--border-medium)';
                            }
                          }}
                          onMouseLeave={(e) => {
                            if (!isSelected) {
                              e.currentTarget.style.background = 'var(--bg-input)';
                              e.currentTarget.style.borderColor = 'var(--border-subtle)';
                            }
                          }}
                        >
                          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '3px' }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                              <span style={{ fontSize: '0.8rem', fontWeight: 600, color: isSelected ? 'var(--text-main)' : '#e2e8f0' }}>
                                {m.name}
                              </span>
                              {m.badge && (
                                <span style={{ fontSize: '0.6rem', padding: '1px 5px', borderRadius: '4px', background: 'rgba(255, 255, 255, 0.08)', color: 'var(--text-muted)', fontWeight: 600 }}>
                                  {m.badge}
                                </span>
                              )}
                              {m.supportsAudio && (
                                <span style={{ fontSize: '0.62rem', color: 'var(--accent-emerald)', background: 'var(--accent-emerald-subtle)', padding: '1px 5px', borderRadius: '4px', fontWeight: 600 }}>
                                  🎵 Audio
                                </span>
                              )}
                            </div>
                            {isSelected && (
                              <Check size={14} color="var(--accent-emerald)" />
                            )}
                          </div>

                          {/* Single Line Rates beneath model name scaled by resolution */}
                          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.68rem', color: 'var(--text-dim)', fontFamily: 'var(--font-mono)' }}>
                            <span style={{
                              fontSize: '0.58rem',
                              padding: '1px 4px',
                              borderRadius: '3px',
                              background: 'rgba(255, 255, 255, 0.07)',
                              color: 'var(--accent-cyan)',
                              fontWeight: 700,
                              letterSpacing: '0.02em',
                            }}>
                              {previewResolution.toUpperCase()}
                            </span>
                            <span>fal: <strong style={{ color: rates.cheapest === 'fal' ? 'var(--accent-emerald)' : 'var(--text-muted)' }}>${rates.fal.toFixed(3)}/s</strong></span>
                            <span>•</span>
                            <span>apidot: <strong style={{ color: rates.cheapest === 'apidot' ? 'var(--accent-emerald)' : 'var(--text-muted)' }}>${rates.apidot.toFixed(3)}/s</strong></span>
                            <span>•</span>
                            <span>kie: <strong style={{ color: rates.cheapest === 'kie' ? 'var(--accent-emerald)' : 'var(--text-muted)' }}>${rates.kie.toFixed(3)}/s</strong></span>
                            <span style={{ marginLeft: 'auto', fontSize: '0.64rem', fontWeight: 600, color: 'var(--accent-emerald)' }}>
                              Lowest: {rates.cheapest}
                            </span>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                ))
              )}
            </div>

            {/* Footer */}
            <div style={{
              padding: '10px 14px',
              borderTop: '1px solid var(--border-subtle)',
              background: 'rgba(0, 0, 0, 0.25)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              fontSize: '0.72rem',
              color: 'var(--text-dim)'
            }}>
              <span>Failures guaranteed $0.00 across all verified providers</span>
              <button
                type="button"
                onClick={() => {
                  setIsModelMenuOpen(false);
                  setIsCostModalOpen(true);
                }}
                style={{
                  background: 'transparent',
                  border: 'none',
                  color: 'var(--accent-emerald)',
                  fontSize: '0.72rem',
                  fontWeight: 600,
                  cursor: 'pointer',
                  padding: 0,
                }}
              >
                View Live Rates Matrix →
              </button>
            </div>
          </div>
        </div>,
        document.body
      )}
    </div>
  );
};
