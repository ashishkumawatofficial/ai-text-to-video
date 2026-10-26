import React, { useState, useEffect } from 'react';
import { Video, Cpu, Sparkles, ChevronLeft, Zap } from 'lucide-react';
import {
  StudioSession,
  TelemetryState,
  fetchHealth,
  generateStoryboard,
  rerollBeat,
  uploadBeatImage,
  removeBeatFrame,
  sendDirectorChat,
  startRender,
  cancelRender,
  subscribeToTelemetry,
  updateStoryboardBeat,
  renderBeat,
  chainFrame,
  unlinkChain,
  compileMaster,
  getProject,
  updateProject,
  setActiveTake,
} from './services/api';
import { ProjectDashboard } from './components/ProjectDashboard';
import { DirectorSidebar } from './components/DirectorSidebar';
import { StoryboardCanvas } from './components/StoryboardCanvas';
import { RemotionPlayerPane } from './components/RemotionPlayerPane';
import { TelemetryGrid } from './components/TelemetryGrid';
import './styles/studio.css';

export function App() {
  const [currentView, setCurrentView] = useState<'dashboard' | 'studio'>('dashboard');
  const [prompt, setPrompt] = useState('A brave astronaut discovering an ancient crystal on Mars under a red dust storm');
  const [aspectRatio, setAspectRatio] = useState<'16:9' | '9:16' | '1:1'>('16:9');
  const [directingMode, setDirectingMode] = useState<'auto' | 'pro'>('pro');
  const [backend, setBackend] = useState<'serverless' | 'pod' | 'local'>('serverless');
  const [voicePersona, setVoicePersona] = useState<string>('auto');
  const [projectTitle, setProjectTitle] = useState('Untitled Project');

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

    // Check for ?project= query parameter for direct deep-linking
    const searchParams = new URLSearchParams(window.location.search);
    const initialProjectId = searchParams.get('project');
    if (initialProjectId) {
      handleOpenProject(initialProjectId);
    }

    return () => unsubscribe();
  }, []);

  // Handle Opening a Project (from Dashboard or URL)
  const handleOpenProject = async (projectId: string) => {
    try {
      const proj = await getProject(projectId);
      setSession(proj);
      setProjectTitle(proj.title || proj.concept_prompt.slice(0, 36) || 'Untitled Video');
      if (proj.concept_prompt) setPrompt(proj.concept_prompt);
      if (proj.aspect_ratio) setAspectRatio(proj.aspect_ratio);
      if (proj.directing_mode) setDirectingMode(proj.directing_mode as any);
      if (proj.backend_strategy) setBackend(proj.backend_strategy as any);

      // Synchronize browser URL without page reload
      const url = new URL(window.location.href);
      url.searchParams.set('project', projectId);
      window.history.pushState({}, '', url.toString());

      setCurrentView('studio');
    } catch (err: any) {
      console.error('Failed to load project:', err);
      alert(`Could not load project: ${err.message}`);
      setCurrentView('dashboard');
    }
  };

  // Return from Studio to Dashboard
  const handleBackToDashboard = () => {
    const url = new URL(window.location.href);
    url.searchParams.delete('project');
    window.history.pushState({}, '', url.pathname);
    setCurrentView('dashboard');
  };

  // In-header Project Title Rename
  const handleTitleBlur = async () => {
    if (!session || !projectTitle.trim() || projectTitle === session.title) return;
    try {
      await updateProject(session.session_id, projectTitle.trim());
      setSession((prev) => (prev ? { ...prev, title: projectTitle.trim() } : prev));
    } catch (err) {
      console.error('Failed to update title:', err);
    }
  };

  // Storyboard Planning Generator
  const handleGenerateStoryboard = async (preserveSessionId: boolean = false) => {
    if (!prompt.trim()) return;
    setIsGenerating(true);
    try {
      const targetSessionId = preserveSessionId && session ? session.session_id : undefined;
      const newSession = await generateStoryboard(
        prompt,
        aspectRatio,
        directingMode,
        backend,
        voicePersona,
        targetSessionId
      );
      setSession(newSession);
      setProjectTitle(newSession.title || prompt.slice(0, 36) || 'Untitled Video');
      
      // Update URL with session ID
      const url = new URL(window.location.href);
      url.searchParams.set('project', newSession.session_id);
      window.history.pushState({}, '', url.toString());
    } catch (err: any) {
      console.error('Storyboard generation error:', err);
      alert(err?.message || 'Failed to generate storyboard plan. Ensure backend is running.');
    } finally {
      setIsGenerating(false);
    }
  };

  // Beat Keyframe Reroll
  const handleRerollBeat = async (beatIndex: number, promptOverride?: string, promptType: 'image' | 'motion' = 'image') => {
    if (!session) return;
    try {
      const updatedCard = await rerollBeat(session.session_id, beatIndex, promptOverride, promptType);
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

  // Custom Keyframe / End Frame / Reference Image Upload
  const handleUploadBeatImage = async (
    beatIndex: number,
    file: File,
    frameType: 'start_frame' | 'end_frame' | 'reference_image' = 'start_frame'
  ) => {
    if (!session) return;
    try {
      const updatedCard = await uploadBeatImage(session.session_id, beatIndex, file, frameType);
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
      alert(`Failed to upload ${frameType.replace('_', ' ')} for beat ${beatIndex + 1}.`);
    }
  };

  // Remove Frame or Reference Image
  const handleRemoveBeatFrame = async (
    beatIndex: number,
    frameType: 'start_frame' | 'end_frame' | 'reference_image',
    imageIndex?: number
  ) => {
    if (!session) return;
    try {
      const updatedCard = await removeBeatFrame(session.session_id, beatIndex, frameType, imageIndex);
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
      console.error('Remove frame error:', err);
      alert(`Failed to remove ${frameType.replace('_', ' ')} for beat ${beatIndex + 1}.`);
    }
  };

  // Directorial Beat Updates (Speaker, Voice Persona, Prompt, Dialogue, Routing)
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
        imagePrompt: updates.image_prompt,
        motionPrompt: updates.motion_prompt,
        cameraMotion: updates.camera_motion,
        modelId: updates.model_id,
        providerOverride: updates.provider_override,
        resolution: updates.resolution,
        modality: updates.modality,
        nativeAudio: updates.native_audio ?? updates.has_clip_audio,
        allowProviderCascade: updates.allow_provider_cascade ?? updates.allowProviderCascade,
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

  // Single-Beat Video Render (Multi-Take Recording with selected Model, Provider, Resolution, Modality)
  const handleRenderBeat = async (beatIndex: number) => {
    if (!session) return;
    const targetCard = session.beats.find((b) => b.beat_index === beatIndex);

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

      const res = await renderBeat(
        session.session_id,
        beatIndex,
        backend,
        targetCard?.model_id,
        targetCard?.provider_override,
        targetCard?.resolution,
        targetCard?.modality,
        targetCard?.native_audio ?? targetCard?.has_clip_audio,
        targetCard?.allow_provider_cascade
      );
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

  // Multi-Take Selection Switcher
  const handleSelectTake = async (beatIndex: number, takeId: string) => {
    if (!session) return;
    try {
      const res = await setActiveTake(session.session_id, beatIndex, takeId);
      setSession((prev) => {
        if (!prev) return prev;
        const newBeats = [...prev.beats];
        const targetIdx = newBeats.findIndex((b) => b.beat_index === beatIndex);
        if (targetIdx !== -1) {
          newBeats[targetIdx] = {
            ...newBeats[targetIdx],
            active_take_id: res.active_take_id,
            output_video_path: res.output_video_path,
          };
        }
        return { ...prev, beats: newBeats };
      });
    } catch (err: any) {
      console.error('Take switch error:', err);
      alert(`Failed to switch take: ${err.message}`);
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
    } catch (err: any) {
      console.error('Chat error:', err);
      alert(`Failed to send director note: ${err?.message || 'Server error'}`);
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

  // 1. If currently on Dashboard view, render Project Dashboard
  if (currentView === 'dashboard') {
    return (
      <ProjectDashboard
        onOpenProject={handleOpenProject}
        healthStatus={healthStatus}
      />
    );
  }

  // 2. Otherwise render Studio Editing Workspace
  const completedBeatsCount = session ? session.beats.filter((b) => b.render_status === 'completed').length : 0;

  return (
    <div className="studio-container">
      {/* Studio Header */}
      <header className="studio-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
          <button
            className="btn-back-projects"
            onClick={handleBackToDashboard}
            title="Return to Projects Dashboard"
          >
            <ChevronLeft size={16} />
            <span>Projects</span>
          </button>

          <span style={{ color: 'var(--border-subtle)' }}>|</span>

          <div className="studio-logo-badge">
            <Video size={18} />
          </div>

          <input
            type="text"
            className="editable-title-input"
            value={projectTitle}
            onChange={(e) => setProjectTitle(e.target.value)}
            onBlur={handleTitleBlur}
            onKeyDown={(e) => {
              if (e.key === 'Enter') {
                (e.target as HTMLInputElement).blur();
              }
            }}
            title="Click to rename project"
          />
        </div>

        {/* Global Cluster Status Indicators */}
        <div className="cluster-status-pill">
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span className="status-dot" />
            <span>FastAPI: Online</span>
          </div>

          <span style={{ color: 'var(--border-subtle)' }}>|</span>

          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <Cpu size={14} color="var(--text-muted)" />
            <span>Serverless: {healthStatus?.serverless_healthy ? 'Ready (RTX 4090/A5000)' : 'Connected'}</span>
          </div>

          <span style={{ color: 'var(--border-subtle)' }}>|</span>

          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <Sparkles size={14} color="var(--text-muted)" />
            <span>Gemini Director: {healthStatus?.gemini_active ? 'Active' : 'Offline'}</span>
          </div>

          <span style={{ color: 'var(--border-subtle)' }}>|</span>

          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <Zap size={14} color={isRendering ? 'var(--accent-blue)' : 'var(--accent-emerald)'} className={isRendering ? 'spin-slow' : ''} />
            <span style={{ color: isRendering ? 'var(--accent-blue)' : 'inherit' }}>
              {isRendering
                ? `Video API: ${session?.telemetry?.active_provider || 'fal.ai'} [${session?.telemetry?.active_api_status || 'IN_PROGRESS'}]`
                : 'Video API: Gateway Online'}
            </span>
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
          savedConceptPrompt={session?.concept_prompt}
        />

        {/* Column 2: Visual Storyboard Canvas */}
        <StoryboardCanvas
          beats={session?.beats || []}
          aspectRatio={aspectRatio}
          conceptPrompt={session?.concept_prompt || prompt}
          projectId={session?.session_id}
          onSelectTake={handleSelectTake}
          onRerollBeat={handleRerollBeat}
          onUploadBeatImage={handleUploadBeatImage}
          onRemoveBeatFrame={handleRemoveBeatFrame}
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
            beats={session?.beats || []}
            isRendering={isRendering}
            onCancelRender={handleCancelRender}
          />
        </div>
      </main>
    </div>
  );
}

export default App;
