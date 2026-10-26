import React from 'react';
import { Film, Layers, Clock } from 'lucide-react';
import { StoryboardCard } from '../services/api';
import { BeatCard } from './BeatCard';

interface StoryboardCanvasProps {
  beats: StoryboardCard[];
  aspectRatio: string;
  conceptPrompt: string;
  projectId?: string;
  onSelectTake?: (beatIndex: number, takeId: string) => Promise<void>;
  onRerollBeat: (beatIndex: number, promptOverride?: string, promptType?: 'image' | 'motion') => Promise<void>;
  onUploadBeatImage?: (beatIndex: number, file: File, frameType?: 'start_frame' | 'end_frame' | 'reference_image') => Promise<void>;
  onRemoveBeatFrame?: (beatIndex: number, frameType: 'start_frame' | 'end_frame' | 'reference_image', imageIndex?: number) => Promise<void>;
  onUpdateCard?: (beatIndex: number, updates: Partial<StoryboardCard>) => Promise<void>;
  onRenderBeat?: (beatIndex: number) => Promise<void>;
  onChainFrame?: (sourceBeatIndex: number) => Promise<void>;
  onUnlinkChain?: (beatIndex: number) => Promise<void>;
  isRendering?: boolean;
}

export const StoryboardCanvas: React.FC<StoryboardCanvasProps> = ({
  beats,
  aspectRatio,
  projectId,
  onSelectTake,
  onRerollBeat,
  onUploadBeatImage,
  onRemoveBeatFrame,
  onUpdateCard,
  onRenderBeat,
  onChainFrame,
  onUnlinkChain,
  isRendering,
}) => {
  const totalDuration = beats.reduce((acc, b) => acc + (b.duration_seconds || 5.0), 0);

  return (
    <div className="canvas-pane">
      {/* Timeline Bar Header */}
      <div className="canvas-header">
        <div>
          <h2 className="canvas-title">Storyboard Timeline</h2>
          <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '4px' }}>
            {beats.length > 0
              ? `${beats.length} Scenes • Total Duration: ${totalDuration.toFixed(1)}s`
              : 'Enter a creative prompt on the left to synthesize the director storyboard'}
          </p>
        </div>

        {beats.length > 0 && (
          <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
            <span
              style={{
                padding: '4px 10px',
                fontSize: '0.74rem',
                color: 'var(--text-main)',
                background: 'rgba(255, 255, 255, 0.05)',
                border: '1px solid var(--border-subtle)',
                borderRadius: '6px',
                display: 'inline-flex',
                alignItems: 'center',
                gap: '5px',
              }}
            >
              <Clock size={12} color="var(--accent-emerald)" />
              <span>{totalDuration.toFixed(1)}s Runtime</span>
            </span>

            <span
              style={{
                padding: '4px 10px',
                fontSize: '0.74rem',
                color: 'var(--text-main)',
                background: 'rgba(255, 255, 255, 0.05)',
                border: '1px solid var(--border-subtle)',
                borderRadius: '6px',
                display: 'inline-flex',
                alignItems: 'center',
                gap: '5px',
              }}
            >
              <Layers size={12} />
              <span>{aspectRatio === '16:9' ? '16:9 Landscape' : aspectRatio === '9:16' ? '9:16 Vertical Short' : '1:1 Square'}</span>
            </span>
          </div>
        )}
      </div>

      {beats.length === 0 ? (
        <div
          style={{
            flex: 1,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '48px 24px',
            textAlign: 'center',
            gap: '16px',
            background: 'var(--bg-card)',
            border: '1px dashed var(--border-medium)',
            borderRadius: '12px',
          }}
        >
          <div
            style={{
              width: '56px',
              height: '56px',
              borderRadius: '12px',
              background: 'rgba(255, 255, 255, 0.05)',
              border: '1px solid var(--border-subtle)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: 'var(--text-muted)',
            }}
          >
            <Film size={26} />
          </div>

          <div>
            <h3 style={{ fontFamily: 'var(--font-display)', fontSize: '1.05rem', fontWeight: 600, marginBottom: '6px', color: 'var(--text-main)' }}>
              No Storyboard Generated Yet
            </h3>
            <p style={{ color: 'var(--text-muted)', fontSize: '0.82rem', maxWidth: '380px', lineHeight: 1.5 }}>
              Type your narrative script in the Director Settings panel on the left and click <strong>"Generate Storyboard"</strong> to synthesize scene keyframes.
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
              projectId={projectId}
              onSelectTake={onSelectTake}
              onReroll={onRerollBeat}
              onUploadImage={onUploadBeatImage}
              onRemoveFrame={onRemoveBeatFrame}
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
