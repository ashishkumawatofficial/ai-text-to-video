import React from 'react';
import { Audio, Sequence, useCurrentFrame, staticFile } from 'remotion';
import { AudioConfig, SubtitlesConfig, SceneConfig } from '../types';

interface AudioMixerProps {
  audio: AudioConfig;
  subtitles?: SubtitlesConfig;
  fps: number;
  scenes?: SceneConfig[];
}

export const AudioMixer: React.FC<AudioMixerProps> = ({ audio, subtitles, fps, scenes }) => {
  const frame = useCurrentFrame();
  const currentMs = (frame / fps) * 1000;

  // Determine if active scene is playing embedded native clip audio
  const activeSceneHasNativeAudio = Boolean(
    scenes?.some(
      (s) => s.hasClipAudio && frame >= s.startFrame && frame < (s.startFrame + s.durationInFrames)
    )
  );

  // Determine if speech is currently active (within word timestamps +/- 200ms)
  const isSpeechActive = Boolean(
    subtitles?.words?.some(
      (w) => currentMs >= w.startMs - 200 && currentMs <= w.endMs + 200
    )
  );

  const baseVolume = audio.musicBaseVolume ?? 0.35;
  const duckedVolume = audio.musicDuckedVolume ?? 0.10;
  // When native clip audio or speech is active, duck music down to ambient bed
  const isDucking = isSpeechActive || activeSceneHasNativeAudio;
  const currentMusicVolume = isDucking ? (activeSceneHasNativeAudio ? 0.08 : duckedVolume) : baseVolume;

  // Mute synthetic voiceover completely if the scene has its own native audio to prevent collision
  const currentVoiceoverVolume = activeSceneHasNativeAudio ? 0.0 : 1.0;

  const resolveMediaUrl = (path: string) => {
    if (path.startsWith('http') || path.startsWith('data:')) {
      return path;
    }
    // Relative to public or assets
    return staticFile(path);
  };

  return (
    <>
      {/* 1. Voiceover Narration (bypassed if native audio is playing) */}
      {audio.voiceoverSrc && (
        <Audio
          src={resolveMediaUrl(audio.voiceoverSrc)}
          volume={currentVoiceoverVolume}
        />
      )}

      {/* 2. Background Music with Dynamic Speech Ducking */}
      {audio.musicSrc && (
        <Audio
          src={resolveMediaUrl(audio.musicSrc)}
          volume={currentMusicVolume}
          loop
        />
      )}

      {/* 3. Timed Sound Effects */}
      {audio.sfxCues &&
        audio.sfxCues.map((cue, index) => (
          <Sequence
            key={`sfx-${cue.src}-${cue.startFrame}-${index}`}
            from={cue.startFrame}
            durationInFrames={Math.max(1, Math.round(fps * 3))} // Allow 3s sound tail
          >
            <Audio
              src={resolveMediaUrl(cue.src)}
              volume={cue.volume ?? 1.0}
            />
          </Sequence>
        ))}
    </>
  );
};
