import React from 'react';
import { AbsoluteFill } from 'remotion';
import { SceneConfig } from '../types';
import { CountdownDial } from '../components/CountdownDial';
import { SpriteLayer } from '../components/SpriteLayer';

interface RiddleTemplateProps {
  scene: SceneConfig;
  fps: number;
}

export const RiddleTemplate: React.FC<RiddleTemplateProps> = ({ scene, fps }) => {
  const isPauseScene =
    scene.type === 'countdown_timer' ||
    scene.id.includes('pause') ||
    scene.id === 'scene_2';

  return (
    <AbsoluteFill>
      {/* 1. Procedural 6-Glasses SVG Background (renders if mediaSrc is missing) */}
      {!scene.mediaSrc && (
        <AbsoluteFill
          style={{
            backgroundColor: '#0F172A',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          {/* Header Badge */}
          <div
            style={{
              position: 'absolute',
              top: '220px',
              backgroundColor: 'rgba(30, 41, 59, 0.9)',
              border: '3px solid #38BDF8',
              borderRadius: '24px',
              padding: '20px 48px',
              color: '#FFFFFF',
              fontFamily: 'Inter, sans-serif',
              fontSize: '36px',
              fontWeight: 800,
              letterSpacing: '2px',
              textTransform: 'uppercase',
            }}
          >
            The Six Glasses Riddle
          </div>

          {/* 6 Glasses SVG Container */}
          <svg
            width="960"
            height="320"
            viewBox="0 0 960 320"
            style={{ position: 'absolute', top: '900px' }}
          >
            {/* Table Line */}
            <line x1="0" y1="260" x2="960" y2="260" stroke="#38BDF8" strokeWidth="4" />

            {/* 6 Glasses */}
            {[0, 1, 2, 3, 4, 5].map((idx) => {
              const x = 50 + idx * 150;
              const isFull = idx < 3;
              return (
                <g key={`svg-glass-${idx}`}>
                  {/* Liquid if full */}
                  {isFull && (
                    <rect
                      x={x + 8}
                      y={80}
                      width={84}
                      height={170}
                      rx={10}
                      fill="#0EA5E9"
                      opacity="0.9"
                    />
                  )}
                  {/* Glass Outline */}
                  <rect
                    x={x}
                    y={20}
                    width={100}
                    height={235}
                    rx={18}
                    fill="none"
                    stroke="#E2E8F0"
                    strokeWidth="5"
                  />
                  {/* Glass Reflection Highlight */}
                  <line
                    x1={x + 15}
                    y1={35}
                    x2={x + 15}
                    y2={220}
                    stroke="#FFFFFF"
                    strokeWidth="3"
                    strokeOpacity="0.6"
                  />
                  {/* Badge Number */}
                  <circle cx={x + 50} cy={295} r={22} fill="#334155" stroke="#38BDF8" strokeWidth="2" />
                  <text
                    x={x + 50}
                    y={302}
                    textAnchor="middle"
                    fill="#FFFFFF"
                    fontSize="20"
                    fontWeight="bold"
                    fontFamily="Inter, sans-serif"
                  >
                    {idx + 1}
                  </text>
                </g>
              );
            })}
          </svg>
        </AbsoluteFill>
      )}

      {/* 2. Countdown Dial during pause beat */}
      {isPauseScene && (
        <CountdownDial
          countdownSeconds={scene.timerConfig?.countdownSeconds ?? 7}
          durationInFrames={scene.durationInFrames}
          fps={fps}
        />
      )}

      {/* 3. Interactive Sprite Overlays */}
      {scene.spriteOverlays &&
        scene.spriteOverlays.map((sprite, i) => (
          <SpriteLayer key={`riddle-sprite-${i}`} config={sprite} />
        ))}
    </AbsoluteFill>
  );
};
