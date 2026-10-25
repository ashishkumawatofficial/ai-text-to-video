import React from 'react';
import { useCurrentFrame, interpolate, spring } from 'remotion';

interface CountdownDialProps {
  countdownSeconds?: number;
  durationInFrames: number;
  fps: number;
}

export const CountdownDial: React.FC<CountdownDialProps> = ({
  countdownSeconds = 7,
  durationInFrames,
  fps,
}) => {
  const frame = useCurrentFrame();

  // Progress from 0.0 (start) to 1.0 (end)
  const progress = Math.min(1.0, frame / durationInFrames);
  const secondsLeft = Math.max(0, Math.ceil(countdownSeconds * (1.0 - progress)));

  // SVG Circular parameters
  const size = 260;
  const strokeWidth = 16;
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference * progress;

  // Pulse effect on second change
  const currentSecondFraction = (frame % fps) / fps;
  const pulseScale = interpolate(currentSecondFraction, [0, 0.2, 1], [1.12, 1.0, 1.0]);

  return (
    <div
      style={{
        position: 'absolute',
        top: 280,
        left: '50%',
        transform: 'translateX(-50%)',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 40,
        pointerEvents: 'none',
      }}
    >
      <div
        style={{
          position: 'relative',
          width: size,
          height: size,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          background: 'rgba(15, 23, 42, 0.75)',
          backdropFilter: 'blur(16px)',
          borderRadius: '50%',
          boxShadow: '0 20px 50px rgba(0, 0, 0, 0.8), 0 0 40px rgba(234, 179, 8, 0.3)',
        }}
      >
        <svg
          width={size}
          height={size}
          style={{ transform: 'rotate(-90deg)', position: 'absolute' }}
        >
          {/* Background Track */}
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            stroke="rgba(255, 255, 255, 0.12)"
            strokeWidth={strokeWidth}
            fill="transparent"
          />
          {/* Glowing Animated Progress Bar */}
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            stroke="#EAB308"
            strokeWidth={strokeWidth}
            fill="transparent"
            strokeDasharray={circumference}
            strokeDashoffset={strokeDashoffset}
            strokeLinecap="round"
            style={{
              transition: 'stroke-dashoffset 0.1s linear',
              filter: 'drop-shadow(0 0 12px #EAB308)',
            }}
          />
        </svg>

        {/* Big Number Display */}
        <div
          style={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            transform: `scale(${pulseScale})`,
          }}
        >
          <span
            style={{
              fontFamily: 'system-ui, sans-serif',
              fontSize: '84px',
              fontWeight: 900,
              color: '#FFFFFF',
              lineHeight: 1,
              textShadow: '0 4px 16px rgba(0, 0, 0, 0.9)',
            }}
          >
            {secondsLeft}
          </span>
          <span
            style={{
              fontFamily: 'system-ui, sans-serif',
              fontSize: '18px',
              fontWeight: 700,
              color: '#FACC15',
              letterSpacing: '3px',
              textTransform: 'uppercase',
              marginTop: '6px',
            }}
          >
            PAUSE
          </span>
        </div>
      </div>
    </div>
  );
};
