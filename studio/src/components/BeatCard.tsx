import React, { useState, useRef } from 'react';
import {
  RefreshCw,
  Video,
  Camera,
  Sparkles,
  CheckCircle2,
  Clock,
  Upload,
  Mic,
  Play,
  Link as LinkIcon,
  Unlink as UnlinkIcon,
  AlertTriangle,
  AlertCircle
} from 'lucide-react';
import { StoryboardCard } from '../services/api';

const getVoicePersonaLabel = (actor?: string) => {
  if (!actor || actor === 'auto') return '✨ Auto Voice';
  if (actor.includes('kid')) return '🧸 Kid Voice';
  if (actor.includes('cartoon') || actor.includes('animal')) return '🐿️ Cartoon Animal';
  if (actor.includes('villain') || actor.includes('monster')) return '👿 Deep Villain';
  if (actor.includes('female') || actor.includes('Jenny') || actor.includes('Joanna') || actor.includes('asteria')) return '👩 Female Voice';
  if (actor.includes('male') || actor.includes('Christopher') || actor.includes('Matthew') || actor.includes('orion')) return '👨 Male Voice';
  if (actor.includes('energetic')) return '⚡ Action Voice';
  return `🎙️ ${actor.replace('en-US-', '').replace('Neural', '')}`;
};

interface BeatCardProps {
  card: StoryboardCard;
  aspectRatio: string;
  onReroll: (beatIndex: number, promptOverride?: string) => Promise<void>;
  onUploadImage?: (beatIndex: number, file: File) => Promise<void>;
  onUpdateCard?: (beatIndex: number, updates: Partial<StoryboardCard>) => Promise<void>;
  onRenderBeat?: (beatIndex: number) => Promise<void>;
  onChainFrame?: (sourceBeatIndex: number) => Promise<void>;
  onUnlinkChain?: (beatIndex: number) => Promise<void>;
  isRendering?: boolean;
  totalBeats?: number;
}

export const BeatCard: React.FC<BeatCardProps> = ({
  card,
  aspectRatio,
  onReroll,
  onUploadImage,
  onUpdateCard,
  onRenderBeat,
  onChainFrame,
  onUnlinkChain,
  isRendering,
  totalBeats = 4,
}) => {
  const [isRerolling, setIsRerolling] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [isRenderingBeat, setIsRenderingBeat] = useState(false);
  const [isChaining, setIsChaining] = useState(false);
  const [isUnlinking, setIsUnlinking] = useState(false);
  const [isEditingPrompt, setIsEditingPrompt] = useState(false);
  const [promptText, setPromptText] = useState(card.visual_prompt);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleRerollClick = async () => {
    setIsRerolling(true);
    try {
      await onReroll(card.beat_index, promptText !== card.visual_prompt ? promptText : undefined);
    } finally {
      setIsRerolling(false);
      setIsEditingPrompt(false);
    }
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || !onUploadImage) return;
    setIsUploading(true);
    try {
      await onUploadImage(card.beat_index, file);
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  const handleRenderBeatClick = async () => {
    if (!onRenderBeat) return;
    setIsRenderingBeat(true);
    try {
      await onRenderBeat(card.beat_index);
    } finally {
      setIsRenderingBeat(false);
    }
  };

  const handleChainFrameClick = async () => {
    if (!onChainFrame) return;
    setIsChaining(true);
    try {
      await onChainFrame(card.beat_index);
    } finally {
      setIsChaining(false);
    }
  };

  const handleUnlinkClick = async () => {
    if (!onUnlinkChain) return;
    setIsUnlinking(true);
    try {
      await onUnlinkChain(card.beat_index);
    } finally {
      setIsUnlinking(false);
    }
  };

  const isVertical = aspectRatio === '9:16';
  const isCardBusy = isRendering || isRenderingBeat || card.render_status === 'rendering';
  const isLastShot = card.beat_index >= totalBeats - 1;

  return (
    <div className={`beat-card ${card.is_chained ? 'beat-card-chained' : ''}`}>
      <div className="beat-card-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
          <span className="beat-badge">SHOT {card.beat_index + 1}</span>

          {card.is_chained && (
            <span
              style={{
                fontSize: '0.68rem',
                color: '#38bdf8',
                background: 'rgba(56, 189, 248, 0.14)',
                border: '1px solid rgba(56, 189, 248, 0.3)',
                padding: '1px 6px',
                borderRadius: '4px',
                display: 'inline-flex',
                alignItems: 'center',
                gap: '4px',
                fontWeight: 600
              }}
              title={`Anchored to final frame of Shot ${(card.chained_from_beat ?? (card.beat_index - 1)) + 1}`}
            >
              <LinkIcon size={11} /> Chained from Shot {(card.chained_from_beat ?? (card.beat_index - 1)) + 1}
            </span>
          )}

          {card.is_custom_image ? (
            <span style={{ fontSize: '0.7rem', color: 'var(--accent-cyan)', display: 'flex', alignItems: 'center', gap: '3px' }}>
              <Upload size={12} /> Custom Keyframe
            </span>
          ) : card.edited_by_ai ? (
            <span style={{ fontSize: '0.7rem', color: 'var(--accent-purple)', display: 'flex', alignItems: 'center', gap: '3px' }}>
              <Sparkles size={12} /> AI Edited
            </span>
          ) : null}
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.75rem' }}>
          {card.render_status === 'completed' ? (
            <span style={{ color: 'var(--accent-emerald)', display: 'flex', alignItems: 'center', gap: '4px', fontWeight: 600 }}>
              <CheckCircle2 size={14} /> Ready
            </span>
          ) : isCardBusy ? (
            <span style={{ color: 'var(--accent-cyan)', display: 'flex', alignItems: 'center', gap: '4px', fontWeight: 600 }}>
              <RefreshCw size={14} className="spin-slow" /> Rendering...
            </span>
          ) : card.render_status === 'failed' ? (
            <span style={{ color: '#ef4444', display: 'flex', alignItems: 'center', gap: '4px', fontWeight: 600 }} title={card.error_message || 'Render failed'}>
              <AlertCircle size={14} /> Failed
            </span>
          ) : (
            <span style={{ color: 'var(--text-dim)', display: 'flex', alignItems: 'center', gap: '4px' }}>
              <Clock size={14} /> Pending
            </span>
          )}
        </div>
      </div>

      {/* Upstream Invalidation Alert */}
      {card.chain_out_of_sync && (
        <div
          style={{
            margin: '6px 12px 0',
            padding: '4px 8px',
            background: 'rgba(245, 158, 11, 0.15)',
            border: '1px solid rgba(245, 158, 11, 0.4)',
            borderRadius: '4px',
            fontSize: '0.72rem',
            color: '#fbbf24',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: '6px'
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
            <AlertTriangle size={13} />
            <span>Upstream Shot re-rendered</span>
          </div>
          <button
            type="button"
            onClick={handleChainFrameClick}
            disabled={isChaining}
            style={{
              background: '#f59e0b',
              color: '#000',
              border: 'none',
              borderRadius: '3px',
              padding: '2px 6px',
              fontSize: '0.68rem',
              fontWeight: 700,
              cursor: 'pointer'
            }}
          >
            {isChaining ? 'Updating...' : 'Update Chain'}
          </button>
        </div>
      )}

      {/* Visual Keyframe Plate or Video */}
      <div className={`keyframe-container ${isVertical ? 'vertical' : ''}`}>
        {card.output_video_path ? (
          <video
            src={card.output_video_path}
            controls
            autoPlay
            loop
            muted
            style={{ width: '100%', height: '100%', objectFit: 'cover' }}
          />
        ) : card.keyframe_path ? (
          <img
            src={card.keyframe_path}
            alt={`Keyframe Shot ${card.beat_index + 1}`}
            className="keyframe-img"
          />
        ) : (
          <div className="keyframe-placeholder">
            <Video size={32} />
            <span>Generating Scene Artwork...</span>
          </div>
        )}
      </div>

      <div className="card-body">
        {/* Visual Prompt Section */}
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
            <span style={{ fontSize: '0.7rem', color: 'var(--text-dim)', textTransform: 'uppercase', fontWeight: 700 }}>
              Diffusion Prompt
            </span>
            <button
              type="button"
              onClick={() => setIsEditingPrompt(!isEditingPrompt)}
              style={{ background: 'transparent', border: 'none', color: 'var(--accent-cyan)', fontSize: '0.72rem', cursor: 'pointer' }}
            >
              {isEditingPrompt ? 'Cancel' : 'Edit'}
            </button>
          </div>

          {isEditingPrompt ? (
            <textarea
              className="prompt-textarea"
              style={{ minHeight: '60px', fontSize: '0.8rem' }}
              value={promptText}
              onChange={(e) => setPromptText(e.target.value)}
            />
          ) : (
            <p className="prompt-text">{card.visual_prompt}</p>
          )}
        </div>

        {/* Character Dialogue Attribution & Voice Persona */}
        {card.dialogue_text && (
          <div className="dialogue-box">
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '6px', flexWrap: 'wrap', gap: '4px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <span style={{ fontSize: '0.68rem', color: '#f59e0b', background: 'rgba(245, 158, 11, 0.12)', padding: '2px 6px', borderRadius: '4px', fontWeight: 700 }}>
                  👤 {card.speaker || 'Narrator'}
                </span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                <Mic size={11} style={{ color: 'var(--accent-cyan)' }} />
                <select
                  value={card.voice_actor || 'auto'}
                  disabled={isCardBusy}
                  onChange={(e) => {
                    if (onUpdateCard) {
                      onUpdateCard(card.beat_index, { voice_actor: e.target.value });
                    }
                  }}
                  style={{
                    background: '#0f172a',
                    border: '1px solid rgba(255, 255, 255, 0.15)',
                    borderRadius: '4px',
                    color: '#e2e8f0',
                    fontSize: '0.68rem',
                    padding: '2px 4px',
                    cursor: 'pointer',
                  }}
                >
                  <option value="auto">✨ Auto Inferred</option>
                  <option value="cartoon_animal">🐿️ Cartoon Animal</option>
                  <option value="male_casual">👨 Male Casual</option>
                  <option value="en-US-ChristopherNeural">🎙️ Deep Male (Christopher)</option>
                  <option value="female_narrator">👩 Female Narrator (Ava)</option>
                  <option value="female_sarcastic">😏 Female Sarcastic</option>
                  <option value="deep_villain">👿 Deep Villain</option>
                  <option value="kid">🧸 Kid Voice</option>
                  <option value="energetic_action">⚡ Action Hype</option>
                  <option value="hi-IN-MadhurNeural">🇮🇳 Hindi Male (Madhur)</option>
                  <option value="hi-IN-SwaraNeural">🇮🇳 Hindi Female (Swara)</option>
                </select>
              </div>
            </div>
            <p style={{ margin: 0, fontStyle: 'italic', fontSize: '0.82rem', color: '#cbd5e1' }}>
              "{card.dialogue_text}"
            </p>
          </div>
        )}
      </div>

      <div className="card-footer" style={{ flexDirection: 'column', gap: '8px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', width: '100%' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.72rem', color: 'var(--text-dim)' }}>
            <Camera size={14} />
            <span>{card.camera_motion.replace('_', ' ')} • {card.duration_seconds}s</span>
          </div>

          <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
            <input
              ref={fileInputRef}
              type="file"
              accept="image/*"
              style={{ display: 'none' }}
              onChange={handleFileChange}
            />

            <button
              type="button"
              disabled={isUploading || isCardBusy}
              className="btn-secondary"
              style={{ padding: '3px 6px', fontSize: '0.72rem', display: 'flex', alignItems: 'center', gap: '4px' }}
              onClick={() => fileInputRef.current?.click()}
              title="Upload custom artwork or photo for this scene"
            >
              <Upload size={11} className={isUploading ? 'spin-slow' : ''} />
              <span>{isUploading ? '...' : 'Upload'}</span>
            </button>

            <button
              type="button"
              disabled={isRerolling || isCardBusy}
              className="btn-secondary"
              style={{ padding: '3px 6px', fontSize: '0.72rem', display: 'flex', alignItems: 'center', gap: '4px' }}
              onClick={handleRerollClick}
              title="Re-generate image via AI prompt"
            >
              <RefreshCw size={11} className={isRerolling ? 'spin-slow' : ''} />
              <span>{isRerolling ? '...' : 'Re-roll'}</span>
            </button>

            {card.is_chained && onUnlinkChain && (
              <button
                type="button"
                disabled={isUnlinking || isCardBusy}
                className="btn-secondary"
                style={{ padding: '3px 6px', fontSize: '0.72rem', display: 'flex', alignItems: 'center', gap: '3px', color: '#f87171' }}
                onClick={handleUnlinkClick}
                title="Unlink chained frame and revert to standalone keyframe"
              >
                <UnlinkIcon size={11} />
                <span>{isUnlinking ? '...' : 'Unlink'}</span>
              </button>
            )}
          </div>
        </div>

        {/* Primary Pro Director Actions: Render Beat & Chain to Next Shot */}
        <div style={{ display: 'flex', gap: '8px', width: '100%', marginTop: '2px' }}>
          {onRenderBeat && (
            <button
              type="button"
              disabled={isCardBusy}
              onClick={handleRenderBeatClick}
              style={{
                flex: 1,
                padding: '6px 10px',
                fontSize: '0.76rem',
                fontWeight: 700,
                borderRadius: '6px',
                border: 'none',
                background: card.render_status === 'completed'
                  ? 'linear-gradient(135deg, #10b981 0%, #059669 100%)'
                  : 'linear-gradient(135deg, #0ea5e9 0%, #2563eb 100%)',
                color: '#fff',
                cursor: isCardBusy ? 'not-allowed' : 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '5px',
                boxShadow: '0 2px 8px rgba(0, 0, 0, 0.2)'
              }}
            >
              {isRenderingBeat || card.render_status === 'rendering' ? (
                <>
                  <RefreshCw size={12} className="spin-slow" />
                  <span>Rendering Shot...</span>
                </>
              ) : card.render_status === 'completed' ? (
                <>
                  <RefreshCw size={12} />
                  <span>Re-render Clip</span>
                </>
              ) : (
                <>
                  <Play size={12} />
                  <span>Render Clip</span>
                </>
              )}
            </button>
          )}

          {card.render_status === 'completed' && !isLastShot && onChainFrame && (
            <button
              type="button"
              disabled={isChaining || isCardBusy}
              onClick={handleChainFrameClick}
              style={{
                flex: 1,
                padding: '6px 10px',
                fontSize: '0.76rem',
                fontWeight: 700,
                borderRadius: '6px',
                border: '1px solid rgba(56, 189, 248, 0.4)',
                background: 'rgba(56, 189, 248, 0.12)',
                color: '#38bdf8',
                cursor: isChaining ? 'not-allowed' : 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '5px',
              }}
              title={`Capture final frame of Shot ${card.beat_index + 1} and set as starting frame of Shot ${card.beat_index + 2}`}
            >
              <LinkIcon size={12} className={isChaining ? 'spin-slow' : ''} />
              <span>{isChaining ? 'Chaining...' : `Chain to Shot ${card.beat_index + 2}`}</span>
            </button>
          )}
        </div>
      </div>
    </div>
  );
};
