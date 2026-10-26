import React from 'react';
import {
  AbsoluteFill,
  Series,
  Video,
  Img,
  staticFile,
  useCurrentFrame,
  interpolate,
} from 'remotion';
import { UniversalVideoProps, SceneConfig } from './types';
import { KineticSubtitles } from './components/KineticSubtitles';
import { AudioMixer } from './components/AudioMixer';
import { RiddleTemplate } from './templates/RiddleTemplate';
import { StoryTemplate } from './templates/StoryTemplate';
import { ActionTemplate } from './templates/ActionTemplate';

const resolveSrc = (path?: string) => {
  if (!path) return '';
  if (path.startsWith('http') || path.startsWith('data:') || path.startsWith('file://')) {
    return path;
  }
  return staticFile(path);
};

// 2.5D Ken Burns Camera Pan & Zoom for static plates
const AnimatedPlate: React.FC<{
  mediaSrc: string;
  durationInFrames: number;
  idx: number;
}> = ({ mediaSrc, durationInFrames, idx }) => {
  const frame = useCurrentFrame();
  const scale = interpolate(frame, [0, durationInFrames], [1.0, 1.14], {
    extrapolateRight: 'clamp',
  });
  const panX = interpolate(
    frame,
    [0, durationInFrames],
    [0, idx % 2 === 0 ? -2.5 : 2.5],
    { extrapolateRight: 'clamp' }
  );
  const panY = interpolate(
    frame,
    [0, durationInFrames],
    [0, idx % 2 === 0 ? 1.5 : -1.5],
    { extrapolateRight: 'clamp' }
  );

  return (
    <div
      style={{
        width: '100%',
        height: '100%',
        overflow: 'hidden',
      }}
    >
      <Img
        src={resolveSrc(mediaSrc)}
        style={{
          width: '100%',
          height: '100%',
          objectFit: 'cover',
          transform: `scale(${scale}) translate(${panX}%, ${panY}%)`,
        }}
      />
    </div>
  );
};

export const UniversalComposition: React.FC<UniversalVideoProps> = ({
  genre,
  totalDurationFrames,
  fps,
  width,
  height,
  scenes,
  subtitles,
  audio,
}) => {
  return (
    <AbsoluteFill style={{ backgroundColor: '#000000', overflow: 'hidden' }}>
      {/* 1. Visual Scenes Sequencer */}
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

              {scene.type === 'static_plate' && scene.mediaSrc && (
                <AnimatedPlate
                  mediaSrc={scene.mediaSrc}
                  durationInFrames={scene.durationInFrames}
                  idx={idx}
                />
              )}

              {/* Default fallback if media missing and not handled by riddle template */}
              {!scene.mediaSrc && scene.type !== 'countdown_timer' && genre !== 'riddle' && (
                <div
                  style={{
                    width: '100%',
                    height: '100%',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    backgroundColor: '#111827',
                    color: '#9CA3AF',
                    fontFamily: 'sans-serif',
                    fontSize: 32,
                  }}
                >
                  Scene: {scene.id}
                </div>
              )}

              {/* Genre Templates & Overlays */}
              {genre === 'riddle' && (
                <RiddleTemplate scene={scene} fps={fps} />
              )}
              {genre === 'cinematic_story' && (
                <StoryTemplate scene={scene} fps={fps} />
              )}
              {genre === 'action' && (
                <ActionTemplate scene={scene} fps={fps} />
              )}
            </AbsoluteFill>
          </Series.Sequence>
        ))}
      </Series>

      {/* 2. Kinetic Subtitles Layer */}
      <KineticSubtitles subtitles={subtitles} fps={fps} />

      {/* 3. Audio Mixer & Ducking Layer */}
      <AudioMixer audio={audio} subtitles={subtitles} fps={fps} scenes={scenes} />
    </AbsoluteFill>
  );
};
