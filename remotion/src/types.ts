export type SceneType = 'video_clip' | 'static_plate' | 'sprite_sequence' | 'countdown_timer';

export interface SpriteKeyframe {
  frame: number;
  x: number;
  y: number;
  opacity?: number;
  scale?: number;
  rotation?: number;
}

export interface SpriteOverlayConfig {
  src: string;
  width?: number;
  height?: number;
  keyframes: SpriteKeyframe[];
}

export interface SceneConfig {
  id: string;
  startFrame: number;
  durationInFrames: number;
  type: SceneType;
  mediaSrc?: string;
  spriteOverlays?: SpriteOverlayConfig[];
  timerConfig?: {
    countdownSeconds?: number;
    showRadialDial?: boolean;
  };
}

export interface SubtitleWord {
  word: string;
  startMs: number;
  endMs: number;
}

export interface SubtitlesConfig {
  stylePreset?: string;
  words: SubtitleWord[];
}

export interface AudioCueConfig {
  src: string;
  startFrame: number;
  volume?: number;
}

export interface AudioConfig {
  voiceoverSrc?: string;
  musicSrc?: string;
  musicBaseVolume?: number;
  musicDuckedVolume?: number;
  sfxCues?: AudioCueConfig[];
}

export interface UniversalVideoProps {
  genre: 'riddle' | 'cinematic_story' | 'action';
  totalDurationFrames: number;
  fps: number;
  width: number;
  height: number;
  scenes: SceneConfig[];
  subtitles: SubtitlesConfig;
  audio: AudioConfig;
}
