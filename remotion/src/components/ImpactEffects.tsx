import React from 'react';
import { useCurrentFrame, interpolate } from 'remotion';

interface ImpactEffectsProps {
  triggerFrame?: number;
  durationInFrames: number;
}

export const ImpactEffects: React.FC<ImpactEffectsProps> = ({ triggerFrame = 0, durationInFrames }) => {
  const frame = useCurrentFrame();
  const relFrame = frame - triggerFrame;

  // Flash: strong at triggerFrame, fades in 6 frames
  const flashOpacity = relFrame >= 0 && relFrame <= 6
    ? interpolate(relFrame, [0, 1, 6], [0.75, 0.5, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' })
    : 0;

  // Shake: high frequency dampening sine wave over 12 frames
  let shakeX = 0;
  let shakeY = 0;
  if (relFrame >= 0 && relFrame <= 12) {
    const intensity = interpolate(relFrame, [0, 12], [24, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
    shakeX = Math.sin(relFrame * 2.8) * intensity;
    shakeY = Math.cos(relFrame * 3.2) * (intensity * 0.7);
  }

  return (
    <>
      {/* Screen Shake Transform Applied via Wrapper */}
      <div
        style={{
          position: 'absolute',
          inset: 0,
          transform: `translate(${shakeX}px, ${shakeY}px)`,
          pointerEvents: 'none',
          zIndex: 15,
        }}
      />

      {/* White Impact Flash Overlay */}
      {flashOpacity > 0 && (
        <div
          style={{
            position: 'absolute',
            inset: 0,
            backgroundColor: '#FFFFFF',
            opacity: flashOpacity,
            mixBlendMode: 'overlay',
            pointerEvents: 'none',
            zIndex: 30,
          }}
        />
      )}
    </>
  );
};
