import React from 'react';
import { useCurrentFrame } from 'remotion';
import { SubtitlesConfig } from '../types';

interface KineticSubtitlesProps {
  subtitles: SubtitlesConfig;
  fps: number;
}

export const KineticSubtitles: React.FC<KineticSubtitlesProps> = ({ subtitles, fps }) => {
  const frame = useCurrentFrame();
  const currentMs = (frame / fps) * 1000;

  if (!subtitles.words || subtitles.words.length === 0) {
    return null;
  }

  // Find the current active word index
  const activeIndex = subtitles.words.findIndex(
    (w) => currentMs >= w.startMs && currentMs <= w.endMs
  );

  // If no word is currently active, find closest upcoming or recent word within 300ms
  let displayIndex = activeIndex;
  if (displayIndex === -1) {
    displayIndex = subtitles.words.findIndex(
      (w) => Math.abs(currentMs - w.startMs) < 300
    );
  }

  if (displayIndex === -1) {
    return null;
  }

  // Window of words around the active one (e.g. 3 words visible at a time)
  const windowSize = 4;
  const startIdx = Math.max(0, displayIndex - 1);
  const endIdx = Math.min(subtitles.words.length, startIdx + windowSize);
  const visibleWords = subtitles.words.slice(startIdx, endIdx);

  return (
    <div
      style={{
        position: 'absolute',
        bottom: 220,
        left: 0,
        right: 0,
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        flexWrap: 'wrap',
        gap: '12px',
        padding: '0 40px',
        zIndex: 50,
        pointerEvents: 'none',
      }}
    >
      <div
        style={{
          background: 'rgba(0, 0, 0, 0.45)',
          backdropFilter: 'blur(8px)',
          padding: '12px 28px',
          borderRadius: '24px',
          display: 'flex',
          gap: '14px',
          alignItems: 'center',
          boxShadow: '0 8px 32px rgba(0, 0, 0, 0.5)',
        }}
      >
        {visibleWords.map((wordObj, i) => {
          const isCurrent = currentMs >= wordObj.startMs && currentMs <= wordObj.endMs;
          return (
            <span
              key={`${wordObj.word}-${startIdx + i}`}
              style={{
                fontFamily: 'Inter, system-ui, -apple-system, sans-serif',
                fontSize: isCurrent ? '46px' : '40px',
                fontWeight: 900,
                textTransform: 'uppercase',
                color: isCurrent ? '#FFE600' : '#FFFFFF',
                textShadow: isCurrent
                  ? '0 0 20px rgba(255, 230, 0, 0.8), 2px 2px 4px #000000'
                  : '2px 2px 4px rgba(0, 0, 0, 0.8)',
                transform: isCurrent ? 'scale(1.12)' : 'scale(1.0)',
                transition: 'all 0.08s ease-out',
                letterSpacing: '1px',
              }}
            >
              {wordObj.word}
            </span>
          );
        })}
      </div>
    </div>
  );
};
