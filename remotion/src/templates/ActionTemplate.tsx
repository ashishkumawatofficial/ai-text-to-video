import React from 'react';
import { AbsoluteFill } from 'remotion';
import { SceneConfig } from '../types';
import { ImpactEffects } from '../components/ImpactEffects';

interface ActionTemplateProps {
  scene: SceneConfig;
  fps: number;
}

export const ActionTemplate: React.FC<ActionTemplateProps> = ({ scene }) => {
  return (
    <AbsoluteFill style={{ pointerEvents: 'none' }}>
      {/* 1. Impact Flash & Screen Shake on Scene Cut */}
      <ImpactEffects triggerFrame={0} durationInFrames={scene.durationInFrames} />

      {/* 2. Kinetic Speed Lines Vignette */}
      <div
        style={{
          position: 'absolute',
          inset: 0,
          background:
            'radial-gradient(ellipse at center, transparent 40%, rgba(2, 6, 23, 0.6) 100%)',
          zIndex: 10,
        }}
      />
    </AbsoluteFill>
  );
};
