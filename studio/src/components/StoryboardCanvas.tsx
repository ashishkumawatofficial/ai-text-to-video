import React from 'react';
import { Film, Layers } from 'lucide-react';
import { StoryboardCard } from '../services/api';
import { BeatCard } from './BeatCard';

interface StoryboardCanvasProps {
  beats: StoryboardCard[];
  aspectRatio: string;
  conceptPrompt: string;
  onRerollBeat: (beatIndex: number, promptOverride?: string) => Promise<void>;
  onUploadBeatImage?: (beatIndex: number, file: File) => Promise<void>;
  onUpdateCard?: (beatIndex: number, updates: Partial<StoryboardCard>) => Promise<void>;
  onRenderBeat?: (beatIndex: number) => Promise<void>;
  onChainFrame?: (sourceBeatIndex: number) => Promise<void>;
  onUnlinkChain?: (beatIndex: number) => Promise<void>;
  isRendering?: boolean;
}

export const StoryboardCanvas: React.FC<StoryboardCanvasProps> = ({
  beats,
  aspectRatio,
  conceptPrompt,
  onRerollBeat,
  onUploadBeatImage,
  onUpdateCard,
  onRenderBeat,
  onChainFrame,
  onUnlinkChain,
  isRendering,
}) => {
  const totalDuration = beats.reduce((acc, b) => acc + b.duration_seconds, 0);

  return (
    <div className="canvas-pane">
      <div className="canvas-header">
        <div>
          <h2 className="canvas-title">Visual Storyboard Canvas</h2>
          <p style={{ fontSize: '0.82rem', color: 'var(--text-muted)', marginTop: '4px' }}>
            {beats.length > 0
              ? `${beats.length} Narrative Beats • Total Duration: ${totalDuration.toFixed(1)}s • Aspect Ratio: ${aspectRatio}`
              : 'Enter a concept prompt on the left to synthesize the director storyboard'}
          </p>
        </div>

        {beats.length > 0 && (
          <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
            <span className="glass-panel" style={{ padding: '6px 12px', fontSize: '0.78rem', color: 'var(--accent-cyan)', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <Layers size={14} /> {aspectRatio === '16:9' ? 'Widescreen (832x480)' : 'Vertical Short (576x1024)'}
            </span>
          </div>
        )}
      </div>

      {beats.length === 0 ? (
        <div
          className="glass-panel"
          style={{
            flex: 1,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '40px',
            textAlign: 'center',
            gap: '16px',
            borderStyle: 'dashed',
          }}
        >
          <div
            style={{
              width: '64px',
              height: '64px',
              borderRadius: '50%',
              background: 'rgba(0, 240, 255, 0.08)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: 'var(--accent-cyan)',
            }}
          >
            <Film size={32} />
          </div>

          <div>
            <h3 style={{ fontFamily: 'var(--font-display)', fontSize: '1.2rem', marginBottom: '6px' }}>
              No Storyboard Planned Yet
            </h3>
            <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', maxWidth: '420px', lineHeight: 1.5 }}>
              Type your creative idea or script in the Directing Panel on the left, then click <strong>"Generate Storyboard"</strong> to create visual scene keyframes.
            </p>
          </div>
        </div>
      ) : (
        <div className="cards-grid">
          {beats.map((card) => (
            <BeatCard
              key={card.beat_id}
              card={card}
              aspectRatio={aspectRatio}
              onReroll={onRerollBeat}
              onUploadImage={onUploadBeatImage}
              onUpdateCard={onUpdateCard}
              onRenderBeat={onRenderBeat}
              onChainFrame={onChainFrame}
              onUnlinkChain={onUnlinkChain}
              isRendering={isRendering}
              totalBeats={beats.length}
            />
          ))}
        </div>
      )}
    </div>
  );
};
