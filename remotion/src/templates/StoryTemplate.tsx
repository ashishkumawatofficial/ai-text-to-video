import React from 'react';
import { AbsoluteFill } from 'remotion';
import { SceneConfig } from '../types';

interface StoryTemplateProps {
  scene: SceneConfig;
  fps: number;
}

export const StoryTemplate: React.FC<StoryTemplateProps> = ({ scene }) => {
  return (
    <AbsoluteFill style={{ pointerEvents: 'none' }}>
      {/* Subtle cinematic vignette */}
      <div
        style={{
          position: 'absolute',
          inset: 0,
          background:
            'radial-gradient(circle at center, transparent 60%, rgba(0, 0, 0, 0.4) 100%)',
          zIndex: 10,
        }}
      />
      {/* Subtle top/bottom framing line */}
      <div
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          right: 0,
          height: '60px',
          background: 'linear-gradient(to bottom, rgba(0,0,0,0.8), transparent)',
          zIndex: 12,
        }}
      />
      <div
        style={{
          position: 'absolute',
          bottom: 0,
          left: 0,
          right: 0,
          height: '140px',
          background: 'linear-gradient(to top, rgba(0,0,0,0.8), transparent)',
          zIndex: 12,
        }}
      />
    </AbsoluteFill>
  );
};
