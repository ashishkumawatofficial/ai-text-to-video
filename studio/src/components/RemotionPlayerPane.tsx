import React, { useState } from 'react';
import { Download, Film, Maximize2 } from 'lucide-react';
import { StoryboardCard, upscaleVideoJob } from '../services/api';

interface RemotionPlayerPaneProps {
  masterVideoPath?: string | null;
  beats: StoryboardCard[];
  aspectRatio: string;
  sessionId?: string;
  isRendering?: boolean;
}

export const RemotionPlayerPane: React.FC<RemotionPlayerPaneProps> = ({
  masterVideoPath,
  aspectRatio,
  sessionId,
  isRendering,
}) => {
  const isVertical = aspectRatio === '9:16';

  const [isUpscalingMaster, setIsUpscalingMaster] = useState(false);
  const [upscaledUrl, setUpscaledUrl] = useState<string | null>(null);

  const handleDownload = () => {
    if (!sessionId || !masterVideoPath) return;
    window.open(`/api/export/${sessionId}`, '_blank');
  };

  const handleUpscaleMaster = async () => {
    const targetVideo = upscaledUrl || masterVideoPath;
    if (!targetVideo) return;
    setIsUpscalingMaster(true);
    try {
      const res = await upscaleVideoJob({
        video_path: targetVideo,
        target_resolution: '4k',
        engine: 'real_esrgan',
      });
      setUpscaledUrl(res.upscaled_video_path);
      alert(`Master video successfully upscaled to 4K Ultra-HD! File: ${res.upscaled_video_path}`);
    } catch (err: any) {
      alert(`4K Upscale failed: ${err.message}`);
    } finally {
      setIsUpscalingMaster(false);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span style={{ fontSize: '0.78rem', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.04em', color: 'var(--text-dim)' }}>
          Master Preview Player
        </span>
        <span style={{ fontSize: '0.72rem', color: 'var(--text-dim)', fontFamily: 'var(--font-mono)' }}>
          60 FPS • Full Audio
        </span>
      </div>

      <div
        className="player-wrapper"
        style={{
          width: '100%',
          aspectRatio: isVertical ? '9 / 16' : '16 / 9',
          maxHeight: isVertical ? '420px' : '240px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          position: 'relative',
        }}
      >
        {upscaledUrl || masterVideoPath ? (
          <video
            src={upscaledUrl || masterVideoPath || undefined}
            controls
            autoPlay
            loop
            style={{ width: '100%', height: '100%', objectFit: 'contain' }}
          />
        ) : isRendering ? (
          <div style={{ textAlign: 'center', color: 'var(--text-muted)', padding: '20px' }}>
            <div className="spin-slow" style={{ display: 'inline-block', marginBottom: '8px', color: 'var(--accent-emerald)' }}>
              <Film size={26} />
            </div>
            <p style={{ fontSize: '0.82rem', fontWeight: 500 }}>Synthesizing Master Video...</p>
            <p style={{ fontSize: '0.7rem', color: 'var(--text-dim)', marginTop: '4px' }}>
              Diffusing scenes across parallel cloud workers
            </p>
          </div>
        ) : (
          <div style={{ textAlign: 'center', color: 'var(--text-dim)', padding: '20px' }}>
            <Film size={28} style={{ marginBottom: '8px', opacity: 0.3 }} />
            <p style={{ fontSize: '0.8rem' }}>Master preview will appear here</p>
          </div>
        )}
      </div>

      {masterVideoPath && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          <button
            type="button"
            onClick={handleDownload}
            className="btn-primary"
            style={{ width: '100%', padding: '10px' }}
          >
            <Download size={15} />
            <span>Export Master 1080p MP4</span>
          </button>

          <button
            type="button"
            disabled={isUpscalingMaster}
            onClick={handleUpscaleMaster}
            className="btn-secondary"
            style={{
              width: '100%',
              padding: '8px',
              fontSize: '0.78rem',
              color: 'var(--text-main)',
            }}
          >
            <Maximize2 size={14} className={isUpscalingMaster ? 'spin-slow' : ''} />
            <span>{isUpscalingMaster ? 'Upscaling to 4K Ultra-HD...' : (upscaledUrl ? '✨ 4K Ultra-HD Master Ready' : '✨ 4K Super-Resolution Upscale')}</span>
          </button>
        </div>
      )}
    </div>
  );
};
