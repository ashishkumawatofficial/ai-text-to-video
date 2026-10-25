import React from 'react';
import { useCurrentFrame, interpolate, staticFile, Img } from 'remotion';
import { SpriteOverlayConfig } from '../types';

interface SpriteLayerProps {
  config: SpriteOverlayConfig;
}

export const SpriteLayer: React.FC<SpriteLayerProps> = ({ config }) => {
  const frame = useCurrentFrame();

  if (!config.keyframes || config.keyframes.length === 0) {
    return null;
  }

  const frames = config.keyframes.map((k) => k.frame);
  const xs = config.keyframes.map((k) => k.x);
  const ys = config.keyframes.map((k) => k.y);
  const opacities = config.keyframes.map((k) => k.opacity ?? 1);
  const scales = config.keyframes.map((k) => k.scale ?? 1);
  const rotations = config.keyframes.map((k) => k.rotation ?? 0);

  const currentX = interpolate(frame, frames, xs, { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const currentY = interpolate(frame, frames, ys, { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const currentOpacity = interpolate(frame, frames, opacities, { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const currentScale = interpolate(frame, frames, scales, { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const currentRotation = interpolate(frame, frames, rotations, { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });

  const resolveSrc = (path: string) => {
    if (path.startsWith('http') || path.startsWith('data:')) {
      return path;
    }
    return staticFile(path);
  };

  return (
    <div
      style={{
        position: 'absolute',
        left: currentX,
        top: currentY,
        opacity: currentOpacity,
        transform: `scale(${currentScale}) rotate(${currentRotation}deg)`,
        transformOrigin: 'center center',
        zIndex: 25,
        pointerEvents: 'none',
      }}
    >
      <Img
        src={resolveSrc(config.src)}
        style={{
          width: config.width ? `${config.width}px` : 'auto',
          height: config.height ? `${config.height}px` : 'auto',
          display: 'block',
        }}
      />
    </div>
  );
};
