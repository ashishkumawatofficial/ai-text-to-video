# Remotion Video Synthesis & Audio Pass-Through Contract

**Feature Branch**: `010-multi-provider-video-routing`
**Date**: 2026-10-25
**Interface**: `core/remotion_bridge.py` & `remotion/src/Composition.tsx`

This document defines how Remotion handles the dual audio track architecture when mixing video clips generated with native audio alongside synthetic voiceover and music.

---

## 1. Scene Props Schema Extension

In `remotion/src/types.ts`:
```typescript
export interface SceneConfig {
  id: string;
  startFrame: number;
  durationInFrames: number;
  type: 'video_clip' | 'static_plate' | 'countdown_timer';
  mediaSrc: string;
  hasClipAudio?: boolean;      // True if clip contains native audio/dialogue
  audioVolume?: number;        // Default 1.0 (full clip audio) or 0.0 (muted)
}
```

---

## 2. Audio Playback State Table in `Composition.tsx`

| Clip Condition | `<Video volume={...} />` | External Voiceover Track (`voiceoverSrc`) | Background Music (`musicSrc`) | SFX Cues |
| :--- | :--- | :--- | :--- | :--- |
| **`hasClipAudio == true`** (Native dialogue / Foley) | **`1.0`** (Full volume) | **MUTED (volume: 0.0)** for this scene | **DUCKED** to soft ambient bed (`0.08`) | Disabled or localized only |
| **`hasClipAudio == false`** (Silent video render) | **`0.0`** (Muted) | **ACTIVE (volume: 1.0)** via Edge-TTS / Cloudflare | **FULL DUCKED MIX** (base: `0.35`, ducked: `0.10`) | Active |
| **Static Plate (Ken Burns)** | N/A | **ACTIVE (volume: 1.0)** | **FULL DUCKED MIX** | Active |

---

## 3. Remotion Implementation Logic in `Composition.tsx`

```tsx
<Series>
  {scenes.map((scene, idx) => (
    <Series.Sequence
      key={`scene-${scene.id || idx}`}
      durationInFrames={scene.durationInFrames}
    >
      <AbsoluteFill>
        {scene.type === 'video_clip' && scene.mediaSrc && (
          <Video
            src={resolveSrc(scene.mediaSrc)}
            volume={scene.hasClipAudio ? (scene.audioVolume ?? 1.0) : 0}
            style={{
              width: '100%',
              height: '100%',
              objectFit: 'cover',
            }}
          />
        )}
      </AbsoluteFill>
    </Series.Sequence>
  ))}
</Series>
```

In `AudioMixer.tsx`:
```tsx
// If current active scene has native audio, suppress the synthetic voiceover stream:
const currentScene = scenes.find(
  (s) => frame >= s.startFrame && frame < s.startFrame + s.durationInFrames
);

const shouldPlayVoiceover = !currentScene?.hasClipAudio && audio.voiceoverSrc;
```
