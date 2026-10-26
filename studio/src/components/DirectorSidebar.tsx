import React, { useState, useRef, useEffect } from 'react';
import { Sliders, MessageSquare, Sparkles, Rocket, CheckCircle, Send, Cpu, Layers, Mic, Film, AlertTriangle, X } from 'lucide-react';
import { AspectRatioToggle } from './AspectRatioToggle';
import { ChatMessage } from '../services/api';

interface DirectorSidebarProps {
  prompt: string;
  setPrompt: (p: string) => void;
  aspectRatio: '16:9' | '9:16' | '1:1';
  setAspectRatio: (r: '16:9' | '9:16' | '1:1') => void;
  voicePersona: string;
  setVoicePersona: (v: string) => void;
  directingMode: 'auto' | 'pro';
  setDirectingMode: (m: 'auto' | 'pro') => void;
  backend: 'serverless' | 'pod' | 'local';
  setBackend: (b: 'serverless' | 'pod' | 'local') => void;
  onGenerateStoryboard: (preserveSession?: boolean) => Promise<void>;
  onSynthesizeVideo: () => Promise<void>;
  onCompileMaster?: () => Promise<void>;
  completedBeatsCount?: number;
  chatHistory: ChatMessage[];
  onSendMessage: (msg: string) => Promise<void>;
  isGenerating: boolean;
  isRendering: boolean;
  hasStoryboard: boolean;
  savedConceptPrompt?: string;
}

export const DirectorSidebar: React.FC<DirectorSidebarProps> = ({
  prompt,
  setPrompt,
  aspectRatio,
  setAspectRatio,
  voicePersona,
  setVoicePersona,
  directingMode,
  setDirectingMode,
  backend,
  setBackend,
  onGenerateStoryboard,
  onSynthesizeVideo,
  onCompileMaster,
  completedBeatsCount = 0,
  chatHistory,
  onSendMessage,
  isGenerating,
  isRendering,
  hasStoryboard,
  savedConceptPrompt,
}) => {
  const [activeTab, setActiveTab] = useState<'controls' | 'copilot'>('controls');
  const [chatInput, setChatInput] = useState('');
  const [isSendingChat, setIsSendingChat] = useState(false);
  const [showReplanModal, setShowReplanModal] = useState(false);
  const chatEndRef = useRef<HTMLDivElement>(null);

  const isPromptModified = Boolean(
    hasStoryboard &&
    prompt.trim().length > 0 &&
    savedConceptPrompt &&
    prompt.trim() !== savedConceptPrompt.trim()
  );

  useEffect(() => {
    if (activeTab === 'copilot') {
      chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [chatHistory, activeTab]);

  const handleChatSubmit = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!chatInput.trim() || isSendingChat) return;

    const msg = chatInput.trim();
    setChatInput('');
    setIsSendingChat(true);
    try {
      await onSendMessage(msg);
    } finally {
      setIsSendingChat(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter') {
      if (e.shiftKey) {
        // Shift + Enter: allow default newline insertion
        return;
      }
      // Enter without Shift: submit note
      e.preventDefault();
      handleChatSubmit();
    }
  };

  return (
    <div className="director-sidebar">
      {/* Navigation Tabs */}
      <div className="sidebar-tabs">
        <button
          type="button"
          className={`tab-btn ${activeTab === 'controls' ? 'active' : ''}`}
          onClick={() => setActiveTab('controls')}
        >
          <Sliders size={14} />
          <span>Director Settings</span>
        </button>

        <button
          type="button"
          className={`tab-btn ${activeTab === 'copilot' ? 'active' : ''}`}
          onClick={() => setActiveTab('copilot')}
        >
          <MessageSquare size={14} />
          <span>AI Copilot</span>
        </button>
      </div>

      {activeTab === 'controls' ? (
        <div className="sidebar-content">
          {/* Concept Script Input */}
          <div>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
              <span className="label-title" style={{ marginBottom: 0 }}>Story Concept / Script</span>
              {isPromptModified && (
                <span
                  style={{
                    fontSize: '0.68rem',
                    fontWeight: 700,
                    textTransform: 'uppercase',
                    letterSpacing: '0.04em',
                    color: '#f59e0b',
                    background: 'rgba(245, 158, 11, 0.12)',
                    border: '1px solid rgba(245, 158, 11, 0.3)',
                    padding: '2px 7px',
                    borderRadius: '12px',
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '4px',
                  }}
                >
                  <AlertTriangle size={11} />
                  Modified
                </span>
              )}
            </div>
            <textarea
              className="prompt-textarea"
              placeholder="Describe your story, scenes, characters, and atmosphere..."
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              disabled={isGenerating || isRendering}
              style={isPromptModified ? { borderColor: 'rgba(245, 158, 11, 0.55)' } : undefined}
            />

            {isPromptModified && (
              <div
                style={{
                  marginTop: '8px',
                  padding: '10px 12px',
                  borderRadius: '8px',
                  background: 'rgba(245, 158, 11, 0.08)',
                  border: '1px solid rgba(245, 158, 11, 0.25)',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '8px',
                  animation: 'fadeIn 0.2s ease',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <span style={{ fontSize: '0.74rem', fontWeight: 600, color: '#f59e0b', display: 'flex', alignItems: 'center', gap: '5px' }}>
                    <AlertTriangle size={13} /> Script modified from active storyboard
                  </span>
                  <button
                    type="button"
                    onClick={() => setPrompt(savedConceptPrompt || '')}
                    style={{
                      background: 'transparent',
                      border: 'none',
                      color: 'var(--text-dim)',
                      fontSize: '0.72rem',
                      cursor: 'pointer',
                      textDecoration: 'underline',
                      padding: '0 2px',
                    }}
                    title="Revert textarea to active storyboard's script"
                  >
                    Revert
                  </button>
                </div>
                <p style={{ fontSize: '0.72rem', color: 'var(--text-muted)', margin: 0, lineHeight: 1.45 }}>
                  Active storyboard cards reflect your previous script. Click below to re-plan cards from this new script.
                </p>
                <button
                  type="button"
                  className="btn-primary"
                  onClick={() => setShowReplanModal(true)}
                  disabled={isGenerating || isRendering}
                  style={{
                    padding: '7px 10px',
                    fontSize: '0.75rem',
                    background: 'rgba(245, 158, 11, 0.2)',
                    color: '#f59e0b',
                    border: '1px solid rgba(245, 158, 11, 0.4)',
                    borderRadius: '6px',
                    width: '100%',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: '6px',
                    cursor: 'pointer',
                  }}
                >
                  <Sparkles size={13} />
                  Re-plan Storyboard from Updated Script
                </button>
              </div>
            )}
          </div>

          {/* Aspect Ratio Selector */}
          <AspectRatioToggle
            value={aspectRatio}
            onChange={setAspectRatio}
            disabled={isGenerating || isRendering}
          />

          {/* Character Voice Persona Selector */}
          <div>
            <span className="label-title" style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <Mic size={13} color="var(--accent-emerald)" />
              Default Voice Persona
            </span>
            <select
              value={voicePersona}
              onChange={(e) => setVoicePersona(e.target.value)}
              disabled={isGenerating || isRendering}
              style={{
                width: '100%',
                padding: '9px 12px',
                borderRadius: '8px',
                background: 'var(--bg-input)',
                border: '1px solid var(--border-subtle)',
                color: 'var(--text-main)',
                fontSize: '0.82rem',
                outline: 'none',
                cursor: 'pointer',
              }}
            >
              <option value="auto">✨ Auto Detect (From Story Prompt)</option>
              <option value="en-US-ChristopherNeural">🎙️ Christopher (Deep Male)</option>
              <option value="female_narrator">👩 Ava (Female Narrator)</option>
              <option value="male_casual">👨 Casual Male</option>
              <option value="female_sarcastic">😏 Female Sarcastic</option>
              <option value="deep_villain">👿 Deep Villain</option>
              <option value="kid">🧸 Kid Voice</option>
              <option value="cartoon_animal">🐿️ Cartoon Animal</option>
              <option value="energetic_action">⚡ Action Hype</option>
            </select>
          </div>

          {/* Directing Workflow Mode */}
          <div>
            <span className="label-title">Workflow Mode</span>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
              <button
                type="button"
                className={`aspect-btn ${directingMode === 'pro' ? 'active' : ''}`}
                onClick={() => setDirectingMode('pro')}
                disabled={isGenerating || isRendering}
              >
                <Layers size={15} />
                <span>Pro Director</span>
                <span style={{ fontSize: '0.68rem', color: 'var(--text-dim)' }}>Review & Tweak</span>
              </button>

              <button
                type="button"
                className={`aspect-btn ${directingMode === 'auto' ? 'active' : ''}`}
                onClick={() => setDirectingMode('auto')}
                disabled={isGenerating || isRendering}
              >
                <Rocket size={15} />
                <span>1-Click Auto</span>
                <span style={{ fontSize: '0.68rem', color: 'var(--text-dim)' }}>Instant Render</span>
              </button>
            </div>
          </div>

          {/* Backend Strategy Switcher */}
          <div>
            <span className="label-title">Inference Engine Backend</span>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '6px' }}>
              <button
                type="button"
                className={`aspect-btn ${backend === 'serverless' ? 'active' : ''}`}
                onClick={() => setBackend('serverless')}
                disabled={isRendering}
              >
                <Cpu size={13} />
                <span style={{ fontSize: '0.74rem' }}>Serverless</span>
              </button>

              <button
                type="button"
                className={`aspect-btn ${backend === 'pod' ? 'active' : ''}`}
                onClick={() => setBackend('pod')}
                disabled={isRendering}
              >
                <span style={{ fontSize: '0.74rem' }}>Pod GPU</span>
              </button>

              <button
                type="button"
                className={`aspect-btn ${backend === 'local' ? 'active' : ''}`}
                onClick={() => setBackend('local')}
                disabled={isRendering}
              >
                <span style={{ fontSize: '0.74rem' }}>Local Mock</span>
              </button>
            </div>
          </div>

          {/* Action Trigger Buttons */}
          <div style={{ marginTop: 'auto', display: 'flex', flexDirection: 'column', gap: '10px' }}>
            {directingMode === 'auto' ? (
              <button
                type="button"
                disabled={!prompt.trim() || isGenerating || isRendering}
                className="btn-primary"
                style={{ padding: '12px' }}
                onClick={async () => {
                  if (hasStoryboard && isPromptModified) {
                    setShowReplanModal(true);
                  } else {
                    await onGenerateStoryboard(hasStoryboard);
                    await onSynthesizeVideo();
                  }
                }}
              >
                <Rocket size={16} />
                <span>
                  {isRendering
                    ? 'Rendering Video...'
                    : hasStoryboard && isPromptModified
                    ? 'Re-plan & 1-Click Auto Render'
                    : '1-Click Full Auto Generate'}
                </span>
              </button>
            ) : !hasStoryboard ? (
              <button
                type="button"
                disabled={!prompt.trim() || isGenerating}
                className="btn-primary"
                style={{ padding: '12px' }}
                onClick={() => onGenerateStoryboard(false)}
              >
                <Sparkles size={16} />
                <span>{isGenerating ? 'Synthesizing Storyboard...' : 'Generate Storyboard'}</span>
              </button>
            ) : (
              <>
                {isPromptModified && (
                  <button
                    type="button"
                    disabled={isGenerating || isRendering}
                    className="btn-primary"
                    style={{
                      padding: '11px',
                      background: 'linear-gradient(135deg, #f59e0b 0%, #d97706 100%)',
                      color: '#000',
                      fontWeight: 700,
                      border: 'none',
                      boxShadow: '0 4px 12px rgba(245, 158, 11, 0.25)',
                    }}
                    onClick={() => setShowReplanModal(true)}
                  >
                    <Sparkles size={16} />
                    <span>{isGenerating ? 'Re-planning Storyboard...' : 'Re-plan from Updated Script'}</span>
                  </button>
                )}

                {onCompileMaster && completedBeatsCount !== undefined && completedBeatsCount > 0 && (
                  <button
                    type="button"
                    disabled={isRendering}
                    className="btn-primary"
                    style={{ padding: '11px', background: 'var(--text-main)', color: '#0a0b0d' }}
                    onClick={onCompileMaster}
                    title="Assemble pre-rendered clips into final video with audio & subtitles in < 15s"
                  >
                    <Film size={16} />
                    <span>{isRendering ? 'Assembling Master...' : `Compile Master (${completedBeatsCount} Clips)`}</span>
                  </button>
                )}

                <button
                  type="button"
                  disabled={isRendering}
                  className="btn-secondary"
                  style={{ padding: '11px' }}
                  onClick={onSynthesizeVideo}
                >
                  <CheckCircle size={16} />
                  <span>{isRendering ? 'Synthesizing Parallel Beats...' : 'Batch Render All Beats'}</span>
                </button>
              </>
            )}
          </div>
        </div>
      ) : (
        /* Gemini AI Co-Director Chat Sidebar */
        <div className="sidebar-content chat-mode">
          <div style={{ paddingBottom: '8px', borderBottom: '1px solid var(--border-subtle)', flexShrink: 0 }}>
            <span style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-main)', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <Sparkles size={14} color="var(--accent-emerald)" /> Gemini Director Copilot
            </span>
            <p style={{ fontSize: '0.72rem', color: 'var(--text-dim)', marginTop: '2px' }}>
              Direct in natural language: adjust moods, edit dialogue, or refine scene framing.
            </p>
          </div>

          <div className="chat-thread">
            {chatHistory.length === 0 ? (
              <div style={{ textAlign: 'center', padding: '24px 8px', color: 'var(--text-dim)', fontSize: '0.78rem' }}>
                <p>No directing notes yet.</p>
                <p style={{ marginTop: '6px', fontSize: '0.72rem' }}>
                  Try: <em>"Switch voice to Christopher"</em>, <em>"Make Scene 2 darker with heavy rain"</em> or <em>"Switch to 9:16 Shorts"</em>
                </p>
              </div>
            ) : (
              chatHistory.map((msg) => (
                <div key={msg.message_id} className={`chat-bubble ${msg.sender === 'user' ? 'user' : 'ai'}`}>
                  {msg.text}
                </div>
              ))
            )}
            <div ref={chatEndRef} />
          </div>

          {/* Chat Input */}
          <form onSubmit={handleChatSubmit} style={{ marginTop: 'auto', display: 'flex', gap: '8px', flexShrink: 0, alignItems: 'flex-end' }}>
            <textarea
              placeholder={hasStoryboard ? "Give directing note... (Enter to send, Shift+Enter for new line)" : "Generate storyboard first..."}
              disabled={!hasStoryboard || isSendingChat}
              value={chatInput}
              onChange={(e) => setChatInput(e.target.value)}
              onKeyDown={handleKeyDown}
              rows={2}
              style={{
                flex: 1,
                padding: '9px 12px',
                borderRadius: '8px',
                background: 'var(--bg-input)',
                border: '1px solid var(--border-subtle)',
                color: 'var(--text-main)',
                fontSize: '0.82rem',
                outline: 'none',
                resize: 'none',
                fontFamily: 'inherit',
                lineHeight: 1.4,
                minHeight: '44px',
                maxHeight: '120px',
              }}
            />
            <button
              type="submit"
              disabled={!chatInput.trim() || isSendingChat || !hasStoryboard}
              className="btn-primary"
              style={{ padding: '0 12px', height: '44px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}
              title="Send note (Enter)"
            >
              <Send size={14} />
            </button>
          </form>
        </div>
      )}

      {/* Option A: Replan Confirmation Modal */}
      {showReplanModal && (
        <div className="modal-backdrop" onClick={() => !isGenerating && setShowReplanModal(false)}>
          <div className="modal-window" onClick={(e) => e.stopPropagation()} style={{ maxWidth: '480px' }}>
            <div className="modal-header">
              <h3 style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#f59e0b', fontSize: '1rem' }}>
                <AlertTriangle size={18} />
                Re-plan Storyboard from Updated Script?
              </h3>
              <button
                type="button"
                className="modal-close-btn"
                onClick={() => !isGenerating && setShowReplanModal(false)}
              >
                <X size={16} />
              </button>
            </div>

            <div className="modal-body" style={{ gap: '14px', fontSize: '0.84rem', color: 'var(--text-muted)', lineHeight: 1.5 }}>
              <p style={{ margin: 0 }}>
                You modified the story concept / script in Director Settings.
              </p>
              <div
                style={{
                  padding: '12px 14px',
                  background: 'rgba(245, 158, 11, 0.08)',
                  border: '1px solid rgba(245, 158, 11, 0.22)',
                  borderRadius: '8px',
                  fontSize: '0.8rem',
                  color: 'var(--text-main)',
                }}
              >
                <strong style={{ color: '#f59e0b', display: 'block', marginBottom: '6px' }}>
                  What will happen:
                </strong>
                <ul style={{ paddingLeft: '18px', margin: 0, display: 'flex', flexDirection: 'column', gap: '4px' }}>
                  <li>Brand new scenes, visual prompts, and camera movements will be synthesized.</li>
                  <li>Existing card prompt edits, uploaded plates, and rendered video clips will be replaced.</li>
                  <li>Your project ID, workspace location, and title will be preserved.</li>
                </ul>
              </div>
              <p style={{ margin: 0, fontSize: '0.78rem', color: 'var(--text-dim)' }}>
                To keep your active storyboard scenes and renders instead, click <strong>Cancel</strong>.
              </p>
            </div>

            <div className="modal-footer">
              <button
                type="button"
                className="btn-secondary"
                onClick={() => setShowReplanModal(false)}
                disabled={isGenerating}
              >
                Cancel
              </button>
              <button
                type="button"
                className="btn-primary"
                style={{ background: '#f59e0b', color: '#000', fontWeight: 700 }}
                disabled={isGenerating}
                onClick={async () => {
                  setShowReplanModal(false);
                  await onGenerateStoryboard(true);
                  if (directingMode === 'auto') {
                    await onSynthesizeVideo();
                  }
                }}
              >
                <Sparkles size={14} />
                {isGenerating ? 'Synthesizing...' : 'Yes, Re-plan Storyboard'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
