import React, { useState, useRef, useEffect } from 'react';
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
  AlertCircle,
  Copy,
  Check,
  Image as ImageIcon,
  Film
} from 'lucide-react';
import { StoryboardCard } from '../services/api';
import { TakeSwitcher } from './TakeSwitcher';

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
  projectId?: string;
  onSelectTake?: (beatIndex: number, takeId: string) => Promise<void>;
  onReroll: (beatIndex: number, promptOverride?: string, promptType?: 'image' | 'motion') => Promise<void>;
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
  projectId,
  onSelectTake,
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

  // Dual-Prompt Inspector State
  const [activePromptTab, setActivePromptTab] = useState<'image' | 'motion'>('image');
  const [imagePromptText, setImagePromptText] = useState(card.image_prompt || card.visual_prompt);
  const [motionPromptText, setMotionPromptText] = useState(card.motion_prompt || card.visual_prompt);
  const [isEditingImagePrompt, setIsEditingImagePrompt] = useState(false);
  const [isEditingMotionPrompt, setIsEditingMotionPrompt] = useState(false);
  const [copiedTab, setCopiedTab] = useState<'image' | 'motion' | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);

  // Sync state if card updates from external sources
  useEffect(() => {
    if (!isEditingImagePrompt) {
      setImagePromptText(card.image_prompt || card.visual_prompt);
    }
    if (!isEditingMotionPrompt) {
      setMotionPromptText(card.motion_prompt || card.visual_prompt);
    }
  }, [card.image_prompt, card.motion_prompt, card.visual_prompt, isEditingImagePrompt, isEditingMotionPrompt]);

  const handleCopyPrompt = async (type: 'image' | 'motion') => {
    const textToCopy = type === 'image' ? imagePromptText : motionPromptText;
    try {
      await navigator.clipboard.writeText(textToCopy);
      setCopiedTab(type);
      setTimeout(() => setCopiedTab((curr) => (curr === type ? null : curr)), 2000);
    } catch (err) {
      console.error('Failed to copy prompt:', err);
    }
  };

  const handleGenerateImageClick = async () => {
    setIsRerolling(true);
    try {
      const promptToUse = imagePromptText.trim() || card.image_prompt || card.visual_prompt;
      await onReroll(card.beat_index, promptToUse, 'image');
      if (onUpdateCard && promptToUse !== card.image_prompt) {
        await onUpdateCard(card.beat_index, { image_prompt: promptToUse });
      }
    } finally {
      setIsRerolling(false);
      setIsEditingImagePrompt(false);
    }
  };

  const handleSaveMotionPrompt = async () => {
    if (onUpdateCard) {
      const promptToUse = motionPromptText.trim() || card.motion_prompt || card.visual_prompt;
      await onUpdateCard(card.beat_index, {
        motion_prompt: promptToUse,
        visual_prompt: promptToUse,
      });
    }
    setIsEditingMotionPrompt(false);
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
        {/* Dual-Prompt Inspector (Image Plate vs Video Diffusion Motion) */}
        <div className="prompt-inspector" style={{ marginBottom: '10px' }}>
          {/* Tab Selector Header */}
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: '1px solid rgba(255, 255, 255, 0.08)', paddingBottom: '6px', marginBottom: '8px' }}>
            <div style={{ display: 'flex', gap: '4px' }}>
              <button
                type="button"
                onClick={() => setActivePromptTab('image')}
                style={{
                  background: activePromptTab === 'image' ? 'rgba(56, 189, 248, 0.18)' : 'transparent',
                  border: activePromptTab === 'image' ? '1px solid rgba(56, 189, 248, 0.4)' : '1px solid transparent',
                  borderRadius: '5px',
                  color: activePromptTab === 'image' ? '#38bdf8' : 'var(--text-dim)',
                  fontSize: '0.72rem',
                  fontWeight: 600,
                  padding: '3px 8px',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '5px',
                  transition: 'all 0.15s ease'
                }}
              >
                <ImageIcon size={12} />
                <span>Image Plate</span>
              </button>
              <button
                type="button"
                onClick={() => setActivePromptTab('motion')}
                style={{
                  background: activePromptTab === 'motion' ? 'rgba(168, 85, 247, 0.18)' : 'transparent',
                  border: activePromptTab === 'motion' ? '1px solid rgba(168, 85, 247, 0.4)' : '1px solid transparent',
                  borderRadius: '5px',
                  color: activePromptTab === 'motion' ? '#c084fc' : 'var(--text-dim)',
                  fontSize: '0.72rem',
                  fontWeight: 600,
                  padding: '3px 8px',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '5px',
                  transition: 'all 0.15s ease'
                }}
              >
                <Film size={12} />
                <span>Video Motion</span>
              </button>
            </div>

            {/* Quick Actions (Copy & Edit Toggle) */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <button
                type="button"
                onClick={() => handleCopyPrompt(activePromptTab)}
                style={{
                  background: 'rgba(255, 255, 255, 0.05)',
                  border: '1px solid rgba(255, 255, 255, 0.1)',
                  borderRadius: '4px',
                  color: copiedTab === activePromptTab ? '#10b981' : 'var(--text-muted)',
                  fontSize: '0.68rem',
                  padding: '2px 6px',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '3px',
                }}
                title={`Copy ${activePromptTab === 'image' ? 'Image' : 'Motion'} Prompt to clipboard`}
              >
                {copiedTab === activePromptTab ? <Check size={11} /> : <Copy size={11} />}
                <span>{copiedTab === activePromptTab ? 'Copied!' : 'Copy'}</span>
              </button>

              {activePromptTab === 'image' ? (
                <button
                  type="button"
                  onClick={() => setIsEditingImagePrompt(!isEditingImagePrompt)}
                  style={{
                    background: 'transparent',
                    border: 'none',
                    color: 'var(--accent-cyan)',
                    fontSize: '0.7rem',
                    cursor: 'pointer',
                    fontWeight: 600,
                  }}
                >
                  {isEditingImagePrompt ? 'Cancel' : 'Edit'}
                </button>
              ) : (
                <button
                  type="button"
                  onClick={() => setIsEditingMotionPrompt(!isEditingMotionPrompt)}
                  style={{
                    background: 'transparent',
                    border: 'none',
                    color: '#c084fc',
                    fontSize: '0.7rem',
                    cursor: 'pointer',
                    fontWeight: 600,
                  }}
                >
                  {isEditingMotionPrompt ? 'Cancel' : 'Edit'}
                </button>
              )}
            </div>
          </div>

          {/* Prompt Body */}
          {activePromptTab === 'image' ? (
            <div>
              {isEditingImagePrompt ? (
                <div>
                  <textarea
                    className="prompt-textarea"
                    style={{
                      minHeight: '68px',
                      fontSize: '0.78rem',
                      width: '100%',
                      background: 'rgba(15, 23, 42, 0.7)',
                      borderColor: 'rgba(56, 189, 248, 0.4)',
                      padding: '8px',
                      borderRadius: '6px'
                    }}
                    value={imagePromptText}
                    onChange={(e) => setImagePromptText(e.target.value)}
                    placeholder="Enter prompt for generating keyframe image..."
                  />
                  <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '6px', marginTop: '6px' }}>
                    <button
                      type="button"
                      disabled={isRerolling || isCardBusy}
                      onClick={handleGenerateImageClick}
                      style={{
                        background: 'linear-gradient(135deg, #0284c7 0%, #2563eb 100%)',
                        color: '#fff',
                        border: 'none',
                        borderRadius: '5px',
                        padding: '4px 10px',
                        fontSize: '0.72rem',
                        fontWeight: 700,
                        cursor: (isRerolling || isCardBusy) ? 'not-allowed' : 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '4px',
                        boxShadow: '0 2px 6px rgba(2, 132, 199, 0.3)'
                      }}
                    >
                      <Sparkles size={11} className={isRerolling ? 'spin-slow' : ''} />
                      <span>{isRerolling ? 'Generating Image...' : 'Generate New Image'}</span>
                    </button>
                  </div>
                </div>
              ) : (
                <div>
                  <p className="prompt-text" style={{ fontSize: '0.78rem', lineHeight: '1.4', margin: 0 }}>
                    {imagePromptText}
                  </p>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '6px' }}>
                    <span style={{ fontSize: '0.66rem', color: 'var(--text-dim)' }}>
                      🎨 FLUX.1 static plate synthesis
                    </span>
                    <button
                      type="button"
                      disabled={isRerolling || isCardBusy}
                      onClick={handleGenerateImageClick}
                      style={{
                        background: 'rgba(56, 189, 248, 0.12)',
                        border: '1px solid rgba(56, 189, 248, 0.3)',
                        color: '#38bdf8',
                        borderRadius: '4px',
                        padding: '3px 8px',
                        fontSize: '0.68rem',
                        fontWeight: 600,
                        cursor: (isRerolling || isCardBusy) ? 'not-allowed' : 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '4px'
                      }}
                      title="Re-generate keyframe image with current prompt"
                    >
                      <RefreshCw size={10} className={isRerolling ? 'spin-slow' : ''} />
                      <span>Generate Image</span>
                    </button>
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div>
              {isEditingMotionPrompt ? (
                <div>
                  <textarea
                    className="prompt-textarea"
                    style={{
                      minHeight: '68px',
                      fontSize: '0.78rem',
                      width: '100%',
                      background: 'rgba(15, 23, 42, 0.7)',
                      borderColor: 'rgba(168, 85, 247, 0.4)',
                      padding: '8px',
                      borderRadius: '6px'
                    }}
                    value={motionPromptText}
                    onChange={(e) => setMotionPromptText(e.target.value)}
                    placeholder="Enter motion dynamics and temporal prompt for video diffusion..."
                  />
                  <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '6px', marginTop: '6px' }}>
                    <button
                      type="button"
                      onClick={handleSaveMotionPrompt}
                      style={{
                        background: 'linear-gradient(135deg, #7c3aed 0%, #6366f1 100%)',
                        color: '#fff',
                        border: 'none',
                        borderRadius: '5px',
                        padding: '4px 10px',
                        fontSize: '0.72rem',
                        fontWeight: 700,
                        cursor: 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '4px',
                      }}
                    >
                      <Check size={11} />
                      <span>Save Motion Prompt</span>
                    </button>
                  </div>
                </div>
              ) : (
                <div>
                  <p className="prompt-text" style={{ fontSize: '0.78rem', lineHeight: '1.4', margin: 0 }}>
                    {motionPromptText}
                  </p>
                  <div style={{ display: 'flex', justifyContent: 'flex-start', marginTop: '6px' }}>
                    <span style={{ fontSize: '0.66rem', color: 'var(--text-dim)' }}>
                      🎬 Wan 2.1 I2V diffusion & physics
                    </span>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Character Dialogue Attribution & Voice Persona (Optional & Situational) */}
        {card.dialogue_text && card.dialogue_text.trim() ? (
          <div className="dialogue-box">
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '6px', flexWrap: 'wrap', gap: '4px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <span style={{
                  fontSize: '0.68rem',
                  color: card.speaker && card.speaker.toLowerCase().includes('narrat') ? '#94a3b8' : '#f59e0b',
                  background: card.speaker && card.speaker.toLowerCase().includes('narrat') ? 'rgba(148, 163, 184, 0.15)' : 'rgba(245, 158, 11, 0.12)',
                  padding: '2px 6px',
                  borderRadius: '4px',
                  fontWeight: 700
                }}>
                  {card.speaker && card.speaker.toLowerCase().includes('narrat')
                    ? `🎙️ ${card.speaker}`
                    : `👤 ${card.speaker || 'Voiceover'}`}
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
        ) : (
          <div style={{
            padding: '5px 8px',
            background: 'rgba(255, 255, 255, 0.03)',
            border: '1px dashed rgba(255, 255, 255, 0.08)',
            borderRadius: '4px',
            fontSize: '0.68rem',
            color: 'var(--text-dim)',
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            marginBottom: '6px'
          }}>
            <span style={{ color: 'var(--text-muted)' }}>🔇 Non-verbal / Silent Atmosphere</span>
            {card.speaker && <span>(Subject: {card.speaker})</span>}
          </div>
        )}

        {/* Multi-Take History Switcher */}
        {card.takes && card.takes.length > 0 && (
          <TakeSwitcher
            projectId={projectId || ''}
            beatIndex={card.beat_index}
            takes={card.takes}
            activeTakeId={card.active_take_id}
            onSelectTake={(takeId) => {
              if (onSelectTake) {
                onSelectTake(card.beat_index, takeId);
              }
            }}
          />
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
              onClick={handleGenerateImageClick}
              title="Re-generate keyframe image via Image Prompt"
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
