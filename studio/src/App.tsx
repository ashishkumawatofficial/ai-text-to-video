import React, { useState, useEffect } from 'react';
import { Video, Cpu, Sparkles, CheckCircle2 } from 'lucide-react';
import {
  StudioSession,
  TelemetryState,
  fetchHealth,
  generateStoryboard,
  rerollBeat,
  uploadBeatImage,
  sendDirectorChat,
  startRender,
  cancelRender,
  subscribeToTelemetry,
  updateStoryboardBeat,
  renderBeat,
  chainFrame,
  unlinkChain,
  compileMaster,
} from './services/api';
import { DirectorSidebar } from './components/DirectorSidebar';
import { StoryboardCanvas } from './components/StoryboardCanvas';
import { RemotionPlayerPane } from './components/RemotionPlayerPane';
import { TelemetryGrid } from './components/TelemetryGrid';
import './styles/studio.css';

export function App() {
  const [prompt, setPrompt] = useState('A brave astronaut discovering an ancient crystal on Mars under a red dust storm');
  const [aspectRatio, setAspectRatio] = useState<'16:9' | '9:16' | '1:1'>('16:9');
  const [directingMode, setDirectingMode] = useState<'auto' | 'pro'>('pro');
  const [backend, setBackend] = useState<'serverless' | 'pod' | 'local'>('serverless');
  const [voicePersona, setVoicePersona] = useState<string>('auto');

  const [session, setSession] = useState<StudioSession | null>(null);
  const [telemetry, setTelemetry] = useState<TelemetryState | undefined>(undefined);
  const [healthStatus, setHealthStatus] = useState<any>(null);

  const [isGenerating, setIsGenerating] = useState(false);
  const [isRendering, setIsRendering] = useState(false);

  // Poll backend health & subscribe to live SSE telemetry on mount
  useEffect(() => {
    fetchHealth()
      .then(setHealthStatus)
      .catch((err) => console.error('Health fetch error:', err));

    const unsubscribe = subscribeToTelemetry((newTelemetry) => {
      setTelemetry(newTelemetry);
    });

    return () => unsubscribe();
  }, []);

  // Storyboard Planning Generator
  const handleGenerateStoryboard = async () => {
    if (!prompt.trim()) return;
    setIsGenerating(true);
    try {
      const newSession = await generateStoryboard(
        prompt,
        aspectRatio,
        directingMode,
        backend,
        voicePersona
      );
      setSession(newSession);
    } catch (err) {
      console.error('Storyboard generation error:', err);
      alert('Failed to generate storyboard plan. Ensure backend is running.');
    } finally {
      setIsGenerating(false);
    }
  };

  // Beat Keyframe Reroll
  const handleRerollBeat = async (beatIndex: number, promptOverride?: string) => {
    if (!session) return;
    try {
      const updatedCard = await rerollBeat(session.session_id, beatIndex, promptOverride);
      setSession((prev) => {
        if (!prev) return prev;
        const newBeats = [...prev.beats];
        const targetIdx = newBeats.findIndex((b) => b.beat_index === beatIndex);
        if (targetIdx !== -1) {
          newBeats[targetIdx] = updatedCard;
        }
        return { ...prev, beats: newBeats };
      });
    } catch (err) {
      console.error('Beat re-roll error:', err);
      alert(`Failed to re-roll beat ${beatIndex + 1}.`);
    }
  };

  // Custom Keyframe Upload
  const handleUploadBeatImage = async (beatIndex: number, file: File) => {
    if (!session) return;
    try {
      const updatedCard = await uploadBeatImage(session.session_id, beatIndex, file);
      setSession((prev) => {
        if (!prev) return prev;
        const newBeats = [...prev.beats];
        const targetIdx = newBeats.findIndex((b) => b.beat_index === beatIndex);
        if (targetIdx !== -1) {
          newBeats[targetIdx] = updatedCard;
        }
        return { ...prev, beats: newBeats };
      });
    } catch (err) {
      console.error('Image upload error:', err);
      alert(`Failed to upload custom image for beat ${beatIndex + 1}.`);
    }
  };

  // Directorial Beat Updates (Speaker, Voice Persona, Prompt, Dialogue)
  const handleUpdateBeat = async (beatIndex: number, updates: any) => {
    if (!session) return;
    try {
      const res = await updateStoryboardBeat({
        sessionId: session.session_id,
        beatIndex,
        speaker: updates.speaker,
        voicePersona: updates.voice_actor,
        dialogueText: updates.dialogue_text,
        visualPrompt: updates.visual_prompt,
        cameraMotion: updates.camera_motion,
      });
      setSession((prev) => {
        if (!prev) return prev;
        const newBeats = [...prev.beats];
        const targetIdx = newBeats.findIndex((b) => b.beat_index === beatIndex);
        if (targetIdx !== -1) {
          newBeats[targetIdx] = res.beat;
        }
        return { ...prev, beats: newBeats };
      });
    } catch (err) {
      console.error('Beat update error:', err);
    }
  };

  // Single-Beat Video Render
  const handleRenderBeat = async (beatIndex: number) => {
    if (!session) return;
    try {
      setSession((prev) => {
        if (!prev) return prev;
        const newBeats = [...prev.beats];
        const targetIdx = newBeats.findIndex((b) => b.beat_index === beatIndex);
        if (targetIdx !== -1) {
          newBeats[targetIdx] = { ...newBeats[targetIdx], render_status: 'rendering' };
        }
        return { ...prev, beats: newBeats };
      });

      const res = await renderBeat(session.session_id, beatIndex, backend);
      setSession((prev) => {
        if (!prev) return prev;
        const newBeats = [...prev.beats];
        const targetIdx = newBeats.findIndex((b) => b.beat_index === beatIndex);
        if (targetIdx !== -1) {
          newBeats[targetIdx] = res.beat;
        }
        // Flag downstream chained beats if out of sync
        newBeats.forEach((b, idx) => {
          if (b.is_chained && b.chained_from_beat === beatIndex) {
            newBeats[idx] = { ...b, chain_out_of_sync: true };
          }
        });
        return { ...prev, beats: newBeats };
      });
    } catch (err: any) {
      console.error('Single-beat render error:', err);
      alert(`Render failed for Beat ${beatIndex + 1}: ${err.message}`);
      setSession((prev) => {
        if (!prev) return prev;
        const newBeats = [...prev.beats];
        const targetIdx = newBeats.findIndex((b) => b.beat_index === beatIndex);
        if (targetIdx !== -1) {
          newBeats[targetIdx] = { ...newBeats[targetIdx], render_status: 'failed', error_message: err.message };
        }
        return { ...prev, beats: newBeats };
      });
    }
  };

  // Tail-to-Head Frame Chaining (Shot K -> Shot K+1)
  const handleChainFrame = async (sourceBeatIndex: number) => {
    if (!session) return;
    try {
      const res = await chainFrame(session.session_id, sourceBeatIndex);
      setSession((prev) => {
        if (!prev) return prev;
        const newBeats = [...prev.beats];
        const targetIdx = newBeats.findIndex((b) => b.beat_index === res.target_beat_index);
        if (targetIdx !== -1) {
          newBeats[targetIdx] = res.target_card;
        }
        return { ...prev, beats: newBeats };
      });
    } catch (err: any) {
      console.error('Frame chaining error:', err);
      alert(`Failed to chain frame: ${err.message}`);
    }
  };

  // Selective Unlinking
  const handleUnlinkChain = async (beatIndex: number) => {
    if (!session) return;
    try {
      const res = await unlinkChain(session.session_id, beatIndex);
      setSession((prev) => {
        if (!prev) return prev;
        const newBeats = [...prev.beats];
        const targetIdx = newBeats.findIndex((b) => b.beat_index === beatIndex);
        if (targetIdx !== -1) {
          newBeats[targetIdx] = res.target_card;
        }
        return { ...prev, beats: newBeats };
      });
    } catch (err: any) {
      console.error('Unlink chain error:', err);
      alert(`Failed to unlink chain: ${err.message}`);
    }
  };

  // Master Video Compilation from Pre-Rendered Clips
  const handleCompileMaster = async () => {
    if (!session) return;
    setIsRendering(true);
    try {
      const res = await compileMaster(session.session_id, true);
      setSession((prev) => {
        if (!prev) return prev;
        return {
          ...prev,
          master_video_path: res.master_video_path,
          status: 'completed',
        };
      });
    } catch (err: any) {
      console.error('Master compilation error:', err);
      alert(`Master compilation failed: ${err.message}`);
    } finally {
      setIsRendering(false);
    }
  };

  // Conversational Gemini Director Chat
  const handleSendMessage = async (msg: string) => {
    if (!session) return;
    try {
      const res = await sendDirectorChat(session.session_id, msg);
      setSession(res.session);
      if (res.session.aspect_ratio) {
        setAspectRatio(res.session.aspect_ratio);
      }
    } catch (err) {
      console.error('Chat error:', err);
      alert('Failed to send director note.');
    }
  };

  // Master Video Synthesis Trigger (Batch Mode)
  const handleSynthesizeVideo = async () => {
    if (!session) return;
    setIsRendering(true);
    try {
      await startRender(session.session_id, backend);
      const pollInterval = setInterval(async () => {
        try {
          const res = await fetch(`/api/session/${session.session_id}`);
          if (res.ok) {
            const updated = await res.json();
            setSession(updated);
            if (updated.status === 'completed' || updated.status === 'failed') {
              setIsRendering(false);
              clearInterval(pollInterval);
            }
          }
        } catch {
          // Keep polling
        }
      }, 3000);
    } catch (err) {
      console.error('Render start error:', err);
      setIsRendering(false);
      alert('Failed to dispatch render.');
    }
  };

  // Cancel Cloud Render
  const handleCancelRender = async () => {
    if (!session) return;
    try {
      await cancelRender(session.session_id);
      setIsRendering(false);
    } catch (err) {
      console.error('Cancel error:', err);
    }
  };

  const completedBeatsCount = session ? session.beats.filter((b) => b.render_status === 'completed').length : 0;

  return (
    <div className="studio-container">
      {/* Studio Header */}
      <header className="studio-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div className="studio-logo-badge">
            <Video size={18} />
          </div>
          <div>
            <h1 className="studio-title">AI Video Production Studio</h1>
            <span className="studio-subtitle">Next-Gen Autonomous Agentic Video Filmmaking</span>
          </div>
        </div>

        {/* Global Cluster Status Indicators */}
        <div className="cluster-status-pill">
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span className="status-dot" />
            <span>FastAPI: Online</span>
          </div>

          <span style={{ color: 'var(--border-subtle)' }}>|</span>

          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <Cpu size={14} color="var(--accent-cyan)" />
            <span>Serverless: {healthStatus?.serverless_healthy ? 'Ready (RTX 4090/A5000)' : 'Connected'}</span>
          </div>

          <span style={{ color: 'var(--border-subtle)' }}>|</span>

          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <Sparkles size={14} color="var(--accent-purple)" />
            <span>Gemini Director: {healthStatus?.gemini_active ? 'Active' : 'Offline'}</span>
          </div>
        </div>
      </header>

      {/* 3-Column Studio Workspace */}
      <main className="studio-layout">
        {/* Column 1: Directing Panel & AI Copilot Chat */}
        <DirectorSidebar
          prompt={prompt}
          setPrompt={setPrompt}
          aspectRatio={aspectRatio}
          setAspectRatio={setAspectRatio}
          voicePersona={voicePersona}
          setVoicePersona={setVoicePersona}
          directingMode={directingMode}
          setDirectingMode={setDirectingMode}
          backend={backend}
          setBackend={setBackend}
          onGenerateStoryboard={handleGenerateStoryboard}
          onSynthesizeVideo={handleSynthesizeVideo}
          onCompileMaster={handleCompileMaster}
          completedBeatsCount={completedBeatsCount}
          chatHistory={session?.chat_history || []}
          onSendMessage={handleSendMessage}
          isGenerating={isGenerating}
          isRendering={isRendering}
          hasStoryboard={Boolean(session && session.beats.length > 0)}
        />

        {/* Column 2: Visual Storyboard Canvas */}
        <StoryboardCanvas
          beats={session?.beats || []}
          aspectRatio={aspectRatio}
          conceptPrompt={session?.concept_prompt || prompt}
          onRerollBeat={handleRerollBeat}
          onUploadBeatImage={handleUploadBeatImage}
          onUpdateCard={handleUpdateBeat}
          onRenderBeat={handleRenderBeat}
          onChainFrame={handleChainFrame}
          onUnlinkChain={handleUnlinkChain}
          isRendering={isRendering}
        />

        {/* Column 3: Live Remotion Player & Cloud Telemetry */}
        <div className="studio-right-pane">
          <RemotionPlayerPane
            masterVideoPath={session?.master_video_path}
            beats={session?.beats || []}
            aspectRatio={aspectRatio}
            sessionId={session?.session_id}
            isRendering={isRendering}
          />

          <TelemetryGrid
            telemetry={telemetry}
            isRendering={isRendering}
            onCancelRender={handleCancelRender}
          />
        </div>
      </main>
    </div>
  );
}

export default App;
