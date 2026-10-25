import React, { useState } from 'react';
import { X, Sparkles, Film, Smartphone, Square, Folder, FolderOpen } from 'lucide-react';
import type { CreateProjectParams } from '../types/project';
import { pickDirectory } from '../services/api';

interface NewProjectModalProps {
  isOpen: boolean;
  onClose: () => void;
  onCreate: (params: CreateProjectParams) => Promise<void>;
}

export function NewProjectModal({ isOpen, onClose, onCreate }: NewProjectModalProps) {
  const [title, setTitle] = useState('');
  const [prompt, setPrompt] = useState('');
  const [customLocation, setCustomLocation] = useState('');
  const [aspectRatio, setAspectRatio] = useState<'16:9' | '9:16' | '1:1'>('16:9');
  const [directingMode, setDirectingMode] = useState<'auto' | 'pro'>('pro');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isBrowsing, setIsBrowsing] = useState(false);

  if (!isOpen) return null;

  const handleBrowseDirectory = async () => {
    setIsBrowsing(true);
    try {
      const selected = await pickDirectory();
      if (selected) {
        setCustomLocation(selected);
      }
    } catch (err) {
      console.error('Failed to open directory picker:', err);
    } finally {
      setIsBrowsing(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!prompt.trim()) return;

    setIsSubmitting(true);
    try {
      await onCreate({
        title: title.trim() || prompt.trim().slice(0, 36),
        prompt: prompt.trim(),
        aspect_ratio: aspectRatio,
        directing_mode: directingMode,
        custom_location: customLocation.trim() || undefined,
      });
      setTitle('');
      setPrompt('');
      setCustomLocation('');
      onClose();
    } catch (err) {
      console.error('Failed to create project:', err);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-window" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3>Create New Video Project</h3>
          <button className="modal-close-btn" onClick={onClose}>
            <X size={18} />
          </button>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="modal-body">
            <div className="form-group">
              <label>Project Title (Optional)</label>
              <input
                type="text"
                className="form-input"
                placeholder="e.g., Cyberpunk Tokyo Chase"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
              />
            </div>

            <div className="form-group">
              <label style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <Folder size={14} color="var(--accent-cyan)" />
                <span>Project Storage Location (Optional)</span>
              </label>
              <div style={{ display: 'flex', gap: '8px' }}>
                <input
                  type="text"
                  className="form-input"
                  placeholder="Default: outputs/projects/ (or browse custom folder)"
                  value={customLocation}
                  onChange={(e) => setCustomLocation(e.target.value)}
                  style={{ flex: 1 }}
                />
                <button
                  type="button"
                  className="btn-secondary"
                  onClick={handleBrowseDirectory}
                  disabled={isBrowsing}
                  title="Browse local folders on your system"
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px',
                    whiteSpace: 'nowrap',
                    padding: '0 14px',
                    fontSize: '0.85rem',
                  }}
                >
                  <FolderOpen size={15} color="var(--accent-cyan)" />
                  <span>{isBrowsing ? 'Selecting...' : 'Browse...'}</span>
                </button>
              </div>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted, #94a3b8)', marginTop: '4px', display: 'block' }}>
                Leave empty to use standard isolated directory in outputs/projects/, or click <strong>Browse...</strong> to select any folder on your computer.
              </span>
            </div>

            <div className="form-group">
              <label>Story Concept / Prompt *</label>
              <textarea
                className="form-textarea"
                placeholder="Describe your story, world, characters, and visual atmosphere..."
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                required
                rows={3}
              />
            </div>

            <div className="form-group">
              <label>Aspect Ratio</label>
              <div className="aspect-options">
                <button
                  type="button"
                  className={`aspect-btn ${aspectRatio === '16:9' ? 'selected' : ''}`}
                  onClick={() => setAspectRatio('16:9')}
                >
                  <Film size={20} />
                  <span>16:9 Cinema</span>
                </button>
                <button
                  type="button"
                  className={`aspect-btn ${aspectRatio === '9:16' ? 'selected' : ''}`}
                  onClick={() => setAspectRatio('9:16')}
                >
                  <Smartphone size={20} />
                  <span>9:16 Mobile</span>
                </button>
                <button
                  type="button"
                  className={`aspect-btn ${aspectRatio === '1:1' ? 'selected' : ''}`}
                  onClick={() => setAspectRatio('1:1')}
                >
                  <Square size={20} />
                  <span>1:1 Square</span>
                </button>
              </div>
            </div>

            <div className="form-group">
              <label>Directing Mode</label>
              <div style={{ display: 'flex', gap: '10px' }}>
                <button
                  type="button"
                  className={`filter-tab ${directingMode === 'pro' ? 'active' : ''}`}
                  style={{ flex: 1, padding: '10px' }}
                  onClick={() => setDirectingMode('pro')}
                >
                  Pro Director (Iterative Beat & Frame Chaining)
                </button>
                <button
                  type="button"
                  className={`filter-tab ${directingMode === 'auto' ? 'active' : ''}`}
                  style={{ flex: 1, padding: '10px' }}
                  onClick={() => setDirectingMode('auto')}
                >
                  Auto Director (Fully Autonomous)
                </button>
              </div>
            </div>
          </div>

          <div className="modal-footer">
            <button
              type="button"
              className="btn-secondary"
              onClick={onClose}
              disabled={isSubmitting}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="btn-primary"
              disabled={!prompt.trim() || isSubmitting}
            >
              {isSubmitting ? (
                'Initializing Workspace...'
              ) : (
                <>
                  <Sparkles size={16} style={{ display: 'inline', marginRight: '6px' }} />
                  Create Project
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
