import React from 'react';
import { Play, Download, Film, Sparkles } from 'lucide-react';
import { StoryboardCard } from '../services/api';

interface RemotionPlayerPaneProps {
  masterVideoPath?: string | null;
  beats: StoryboardCard[];
  aspectRatio: string;
  sessionId?: string;
  isRendering?: boolean;
}

export const RemotionPlayerPane: React.FC<RemotionPlayerPaneProps> = ({
  masterVideoPath,
  beats,
  aspectRatio,
  sessionId,
  isRendering,
}) => {
  const isVertical = aspectRatio === '9:16';

  const handleDownload = () => {
    if (!sessionId || !masterVideoPath) return;
    window.open(`/api/export/${sessionId}`, '_blank');
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span style={{ fontSize: '0.82rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.04em' }}>
          Live Studio Player
        </span>
        <span style={{ fontSize: '0.72rem', color: 'var(--text-dim)' }}>
          Kinetic Subtitles • 60 FPS
        </span>
      </div>

      <div
        className="player-wrapper"
        style={{
          width: '100%',
          aspectRatio: isVertical ? '9 / 16' : '16 / 9',
          maxHeight: isVertical ? '440px' : '260px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          position: 'relative',
        }}
      >
        {masterVideoPath ? (
          <video
            src={masterVideoPath}
            controls
            autoPlay
            loop
            style={{ width: '100%', height: '100%', objectFit: 'contain' }}
          />
        ) : isRendering ? (
          <div style={{ textAlign: 'center', color: 'var(--text-muted)', padding: '20px' }}>
            <div className="spin-slow" style={{ display: 'inline-block', marginBottom: '8px', color: 'var(--accent-cyan)' }}>
              <Film size={28} />
            </div>
            <p style={{ fontSize: '0.85rem' }}>Synthesizing Master Video...</p>
            <p style={{ fontSize: '0.72rem', color: 'var(--text-dim)', marginTop: '4px' }}>
              Diffusing shots across parallel cloud workers
            </p>
          </div>
        ) : (
          <div style={{ textAlign: 'center', color: 'var(--text-dim)', padding: '20px' }}>
            <Film size={32} style={{ marginBottom: '8px', opacity: 0.4 }} />
            <p style={{ fontSize: '0.82rem' }}>Video will appear here once synthesized</p>
          </div>
        )}
      </div>

      {masterVideoPath && (
        <button
          type="button"
          onClick={handleDownload}
          className="btn-primary"
          style={{ width: '100%', background: 'linear-gradient(135deg, #8b5cf6 0%, #00f0ff 100%)' }}
        >
          <Download size={16} />
          <span>Export Master 1080p MP4</span>
        </button>
      )}
    </div>
  );
};
