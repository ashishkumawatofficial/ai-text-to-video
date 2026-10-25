import React from 'react';
import { Composition } from 'remotion';
import { UniversalComposition } from './Composition';
import { UniversalVideoProps } from './types';

const defaultProps: UniversalVideoProps = {
  genre: 'riddle',
  totalDurationFrames: 150,
  fps: 30,
  width: 1080,
  height: 1920,
  scenes: [
    {
      id: 'scene_01',
      startFrame: 0,
      durationInFrames: 150,
      type: 'static_plate',
      mediaSrc: '',
    },
  ],
  subtitles: {
    stylePreset: 'bold_yellow_glow',
    words: [
      { word: 'CAN', startMs: 200, endMs: 500 },
      { word: 'YOU', startMs: 520, endMs: 800 },
      { word: 'SOLVE', startMs: 820, endMs: 1200 },
      { word: 'THIS?', startMs: 1220, endMs: 1800 },
    ],
  },
  audio: {
    voiceoverSrc: '',
    musicSrc: '',
    musicBaseVolume: 0.35,
    musicDuckedVolume: 0.10,
    sfxCues: [],
  },
};

export const RemotionRoot: React.FC = () => {
  return (
    <Composition
      id="UniversalComposition"
      component={UniversalComposition}
      durationInFrames={defaultProps.totalDurationFrames}
      fps={defaultProps.fps}
      width={defaultProps.width}
      height={defaultProps.height}
      defaultProps={defaultProps}
      calculateMetadata={async ({ props }) => {
        return {
          durationInFrames: props.totalDurationFrames || 150,
          fps: props.fps || 30,
          width: props.width || 1080,
          height: props.height || 1920,
          props,
        };
      }}
    />
  );
};
