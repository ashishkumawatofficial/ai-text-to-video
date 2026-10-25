import React, { useState } from 'react';
import { Sliders, MessageSquare, Sparkles, Rocket, CheckCircle, Send, Cpu, Layers, Mic, Film } from 'lucide-react';
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
  onGenerateStoryboard: () => Promise<void>;
  onSynthesizeVideo: () => Promise<void>;
  onCompileMaster?: () => Promise<void>;
  completedBeatsCount?: number;
  chatHistory: ChatMessage[];
  onSendMessage: (msg: string) => Promise<void>;
  isGenerating: boolean;
  isRendering: boolean;
  hasStoryboard: boolean;
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
}) => {
  const [activeTab, setActiveTab] = useState<'controls' | 'copilot'>('controls');
  const [chatInput, setChatInput] = useState('');
  const [isSendingChat, setIsSendingChat] = useState(false);

  const handleChatSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
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

  return (
    <div className="director-sidebar">
      {/* Navigation Tabs */}
      <div className="sidebar-tabs">
        <button
          type="button"
          className={`tab-btn ${activeTab === 'controls' ? 'active' : ''}`}
          onClick={() => setActiveTab('controls')}
        >
          <Sliders size={16} />
          <span>Directing Panel</span>
        </button>

        <button
          type="button"
          className={`tab-btn ${activeTab === 'copilot' ? 'active' : ''}`}
          onClick={() => setActiveTab('copilot')}
        >
          <MessageSquare size={16} />
          <span>AI Copilot</span>
        </button>
      </div>

      {activeTab === 'controls' ? (
        <div className="sidebar-content">
          {/* Concept Script Input */}
          <div>
            <span className="label-title">Concept / Narrative Prompt</span>
            <textarea
              className="prompt-textarea"
              placeholder="e.g. A brave astronaut discovering an ancient crystal on Mars, glowing purple under red dust storm..."
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              disabled={isGenerating || isRendering}
            />
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
              <Mic size={14} style={{ color: 'var(--accent-cyan)' }} />
              Character Voice Persona
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
              <option value="kid">🧸 Kid / Child (Kevin / Ivy / Thalia)</option>
              <option value="cartoon_animal">🐿️ Cartoon / Animal (Hermes / Ana +20Hz)</option>
              <option value="deep_villain">👿 Deep Villain / Monster (Zeus / Devil -12Hz)</option>
              <option value="female_narrator">👩 Female Narrator (Asteria / Joanna)</option>
              <option value="male_narrator">👨 Cinematic Male (Orion / Christopher)</option>
              <option value="energetic_action">⚡ Energetic / Fast Paced (Apollo)</option>
            </select>
          </div>

          {/* Directing Workflow Mode */}
          <div>
            <span className="label-title">Production Workflow</span>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
              <button
                type="button"
                className={`aspect-btn ${directingMode === 'pro' ? 'active' : ''}`}
                onClick={() => setDirectingMode('pro')}
                disabled={isGenerating || isRendering}
              >
                <Layers size={16} />
                <span>Pro Director</span>
                <span style={{ fontSize: '0.68rem', color: 'var(--text-dim)' }}>Review & Approve</span>
              </button>

              <button
                type="button"
                className={`aspect-btn ${directingMode === 'auto' ? 'active' : ''}`}
                onClick={() => setDirectingMode('auto')}
                disabled={isGenerating || isRendering}
              >
                <Rocket size={16} />
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
                <Cpu size={14} />
                <span style={{ fontSize: '0.75rem' }}>Serverless</span>
              </button>

              <button
                type="button"
                className={`aspect-btn ${backend === 'pod' ? 'active' : ''}`}
                onClick={() => setBackend('pod')}
                disabled={isRendering}
              >
                <span style={{ fontSize: '0.75rem' }}>Dedicated Pod</span>
              </button>

              <button
                type="button"
                className={`aspect-btn ${backend === 'local' ? 'active' : ''}`}
                onClick={() => setBackend('local')}
                disabled={isRendering}
              >
                <span style={{ fontSize: '0.75rem' }}>Local Mock</span>
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
                onClick={async () => {
                  await onGenerateStoryboard();
                  await onSynthesizeVideo();
                }}
              >
                <Rocket size={18} />
                <span>{isRendering ? 'Rendering Video...' : '1-Click Full Auto Generate'}</span>
              </button>
            ) : !hasStoryboard ? (
              <button
                type="button"
                disabled={!prompt.trim() || isGenerating}
                className="btn-primary"
                onClick={onGenerateStoryboard}
              >
                <Sparkles size={18} />
                <span>{isGenerating ? 'Synthesizing Storyboard...' : 'Generate Storyboard (Pro Mode)'}</span>
              </button>
            ) : (
              <>
                {onCompileMaster && completedBeatsCount !== undefined && completedBeatsCount > 0 && (
                  <button
                    type="button"
                    disabled={isRendering}
                    className="btn-primary"
                    onClick={onCompileMaster}
                    style={{
                      background: 'linear-gradient(135deg, #8b5cf6 0%, #ec4899 100%)',
                      boxShadow: '0 4px 14px rgba(236, 72, 153, 0.35)',
                    }}
                    title="Assemble pre-rendered clips into final video with audio & subtitles in < 15s"
                  >
                    <Film size={18} />
                    <span>{isRendering ? 'Assembling Master...' : `Compile Master (${completedBeatsCount} Clips)`}</span>
                  </button>
                )}

                <button
                  type="button"
                  disabled={isRendering}
                  className="btn-primary"
                  onClick={onSynthesizeVideo}
                  style={{ background: 'linear-gradient(135deg, #10b981 0%, #00f0ff 100%)' }}
                >
                  <CheckCircle size={18} />
                  <span>{isRendering ? 'Synthesizing Parallel Beats...' : 'Batch Render All Beats'}</span>
                </button>
              </>
            )}
          </div>
        </div>
      ) : (
        /* Gemini AI Co-Director Chat Sidebar */
        <div className="sidebar-content" style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
          <div style={{ paddingBottom: '8px', borderBottom: '1px solid var(--border-subtle)' }}>
            <span style={{ fontSize: '0.82rem', fontWeight: 700, color: 'var(--accent-purple)', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <Sparkles size={14} /> Gemini Director Copilot
            </span>
            <p style={{ fontSize: '0.72rem', color: 'var(--text-dim)', marginTop: '2px' }}>
              Type natural language notes to tweak scenes, adjust prompts, or switch framing.
            </p>
          </div>

          <div className="chat-thread">
            {chatHistory.length === 0 ? (
              <div style={{ textAlign: 'center', padding: '24px 8px', color: 'var(--text-dim)', fontSize: '0.8rem' }}>
                <p>No notes yet.</p>
                <p style={{ marginTop: '6px', fontSize: '0.74rem' }}>
                  Try: <em>"Switch voice to cartoon animal"</em>, <em>"Make beat 2 darker and add rain"</em> or <em>"Switch to 9:16 vertical shorts"</em>
                </p>
              </div>
            ) : (
              chatHistory.map((msg) => (
                <div key={msg.message_id} className={`chat-bubble ${msg.sender === 'user' ? 'user' : 'ai'}`}>
                  {msg.text}
                </div>
              ))
            )}
          </div>

          {/* Chat Input */}
          <form onSubmit={handleChatSubmit} style={{ marginTop: 'auto', display: 'flex', gap: '8px' }}>
            <input
              type="text"
              placeholder={hasStoryboard ? "Give directing note..." : "Plan storyboard first..."}
              disabled={!hasStoryboard || isSendingChat}
              value={chatInput}
              onChange={(e) => setChatInput(e.target.value)}
              style={{
                flex: 1,
                padding: '10px 12px',
                borderRadius: '8px',
                background: 'var(--bg-input)',
                border: '1px solid var(--border-subtle)',
                color: 'var(--text-main)',
                fontSize: '0.82rem',
                outline: 'none',
              }}
            />
            <button
              type="submit"
              disabled={!chatInput.trim() || isSendingChat || !hasStoryboard}
              className="btn-primary"
              style={{ padding: '0 14px' }}
            >
              <Send size={15} />
            </button>
          </form>
        </div>
      )}
    </div>
  );
};
