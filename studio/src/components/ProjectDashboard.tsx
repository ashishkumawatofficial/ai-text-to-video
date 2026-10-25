import React, { useState, useEffect, useMemo } from 'react';
import { Video, Plus, Search, Sparkles, Cpu, RefreshCw, Trash2, AlertTriangle, X } from 'lucide-react';
import { ProjectCard } from './ProjectCard';
import { NewProjectModal } from './NewProjectModal';
import {
  fetchProjects,
  createProject,
  deleteProject,
  duplicateProject,
  updateProject,
  revealProjectFolder,
} from '../services/api';
import type { ProjectSummary, CreateProjectParams } from '../types/project';

interface ProjectDashboardProps {
  onOpenProject: (projectId: string) => void;
  healthStatus?: any;
}

export function ProjectDashboard({ onOpenProject, healthStatus }: ProjectDashboardProps) {
  const [projects, setProjects] = useState<ProjectSummary[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<'all' | 'completed' | 'draft'>('all');
  const [isNewModalOpen, setIsNewModalOpen] = useState(false);
  const [renameTarget, setRenameTarget] = useState<{ id: string; currentTitle: string } | null>(null);
  const [newTitle, setNewTitle] = useState('');
  const [deleteTarget, setDeleteTarget] = useState<{ id: string; title: string } | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);

  // Load project list on mount
  const loadProjects = async () => {
    setIsLoading(true);
    try {
      const data = await fetchProjects();
      setProjects(data);
    } catch (err) {
      console.error('Error fetching projects:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadProjects();
  }, []);

  // Filter and search projects
  const filteredProjects = useMemo(() => {
    return projects.filter((p) => {
      const matchesSearch =
        p.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
        p.concept_prompt.toLowerCase().includes(searchQuery.toLowerCase());

      if (!matchesSearch) return false;

      if (statusFilter === 'all') return true;
      if (statusFilter === 'completed') return p.status === 'completed';
      if (statusFilter === 'draft') return p.status !== 'completed';

      return true;
    });
  }, [projects, searchQuery, statusFilter]);

  // Handle Project Creation
  const handleCreateProject = async (params: CreateProjectParams) => {
    const created = await createProject(params);
    onOpenProject(created.session_id);
  };

  // Trigger Delete Confirmation Modal
  const handleDeleteProject = (projectId: string) => {
    const proj = projects.find((p) => p.project_id === projectId);
    setDeleteTarget({
      id: projectId,
      title: proj?.title || 'Untitled Project',
    });
  };

  // Perform Confirmed Deletion
  const handleConfirmDelete = async () => {
    if (!deleteTarget) return;
    setIsDeleting(true);
    try {
      await deleteProject(deleteTarget.id);
      setProjects((prev) => prev.filter((p) => p.project_id !== deleteTarget.id));
      setDeleteTarget(null);
    } catch (err: any) {
      console.error('Delete failed:', err);
      alert(`Failed to delete project: ${err.message}`);
    } finally {
      setIsDeleting(false);
    }
  };

  // Handle Project Duplication
  const handleDuplicateProject = async (projectId: string) => {
    try {
      const cloned = await duplicateProject(projectId);
      await loadProjects();
      onOpenProject(cloned.session_id);
    } catch (err: any) {
      console.error('Duplicate failed:', err);
      alert(`Failed to duplicate project: ${err.message}`);
    }
  };

  // Handle Reveal in File Manager (macOS Finder / Explorer)
  const handleRevealFolder = async (projectId: string) => {
    try {
      await revealProjectFolder(projectId);
    } catch (err: any) {
      console.error('Reveal folder failed:', err);
      alert(`Could not open project folder: ${err.message}`);
    }
  };

  // Handle Rename Submit
  const handleRenameSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!renameTarget || !newTitle.trim()) return;

    try {
      await updateProject(renameTarget.id, newTitle.trim());
      setProjects((prev) =>
        prev.map((p) =>
          p.project_id === renameTarget.id ? { ...p, title: newTitle.trim() } : p
        )
      );
      setRenameTarget(null);
    } catch (err: any) {
      console.error('Rename failed:', err);
      alert(`Failed to rename project: ${err.message}`);
    }
  };

  return (
    <div className="dashboard-container">
      {/* Dashboard Top Header */}
      <header className="dashboard-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div className="studio-logo-badge">
            <Video size={18} />
          </div>
          <div>
            <h1 className="studio-title">AI Video Production Studio</h1>
            <span className="studio-subtitle">Project Workspaces & Narrative Filmmaking</span>
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

      {/* Main Content Area */}
      <main className="dashboard-main">
        {/* Hero Title & Actions */}
        <div className="dashboard-hero">
          <div className="dashboard-title-group">
            <h2>
              Video Projects
              <span className="dashboard-count-badge">
                {projects.length} {projects.length === 1 ? 'Project' : 'Projects'}
              </span>
            </h2>
            <p className="dashboard-subtitle">
              Manage your video productions, multi-take renders, and directorial storyboards.
            </p>
          </div>

          <div style={{ display: 'flex', gap: '12px' }}>
            <button
              className="btn-secondary"
              onClick={loadProjects}
              title="Refresh projects list"
              style={{ display: 'flex', alignItems: 'center', gap: '6px' }}
            >
              <RefreshCw size={15} className={isLoading ? 'animate-spin' : ''} />
              Refresh
            </button>
            <button
              className="btn-new-project"
              onClick={() => setIsNewModalOpen(true)}
            >
              <Plus size={18} />
              New Project
            </button>
          </div>
        </div>

        {/* Search & Filter Controls */}
        <div className="dashboard-controls">
          <div className="dashboard-search-box">
            <Search size={16} className="dashboard-search-icon" />
            <input
              type="text"
              placeholder="Search projects by title or concept prompt..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>

          <div className="filter-tabs">
            <button
              className={`filter-tab ${statusFilter === 'all' ? 'active' : ''}`}
              onClick={() => setStatusFilter('all')}
            >
              All Projects
            </button>
            <button
              className={`filter-tab ${statusFilter === 'completed' ? 'active' : ''}`}
              onClick={() => setStatusFilter('completed')}
            >
              Completed Masters
            </button>
            <button
              className={`filter-tab ${statusFilter === 'draft' ? 'active' : ''}`}
              onClick={() => setStatusFilter('draft')}
            >
              In Progress / Drafts
            </button>
          </div>
        </div>

        {/* Projects Grid or Empty State */}
        {isLoading ? (
          <div style={{ textAlign: 'center', padding: '60px 0', color: 'var(--text-muted)' }}>
            <RefreshCw size={28} className="animate-spin" style={{ margin: '0 auto 12px' }} />
            <p>Scanning project workspaces...</p>
          </div>
        ) : filteredProjects.length === 0 ? (
          <div
            className="glass-panel"
            style={{
              textAlign: 'center',
              padding: '60px 20px',
              maxWidth: '520px',
              margin: '40px auto',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              gap: '14px',
            }}
          >
            <Video size={42} color="var(--accent-cyan)" />
            <h3 style={{ fontFamily: 'var(--font-display)', fontSize: '1.25rem' }}>
              {searchQuery ? 'No matching projects found' : 'No projects yet'}
            </h3>
            <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem', lineHeight: '1.5' }}>
              {searchQuery
                ? `No projects matched "${searchQuery}". Try a different search term or clear the filter.`
                : 'Start your first cinematic AI video production! Describe your story concept to get started.'}
            </p>
            {!searchQuery && (
              <button
                className="btn-new-project"
                style={{ marginTop: '8px' }}
                onClick={() => setIsNewModalOpen(true)}
              >
                <Plus size={16} /> Create Your First Project
              </button>
            )}
          </div>
        ) : (
          <div className="projects-grid">
            {filteredProjects.map((project) => (
              <ProjectCard
                key={project.project_id}
                project={project}
                onOpen={onOpenProject}
                onRename={(id, currentTitle) => {
                  setRenameTarget({ id, currentTitle });
                  setNewTitle(currentTitle);
                }}
                onDuplicate={handleDuplicateProject}
                onDelete={handleDeleteProject}
                onRevealFolder={handleRevealFolder}
              />
            ))}
          </div>
        )}
      </main>

      {/* New Project Modal */}
      <NewProjectModal
        isOpen={isNewModalOpen}
        onClose={() => setIsNewModalOpen(false)}
        onCreate={handleCreateProject}
      />

      {/* Rename Modal */}
      {renameTarget && (
        <div className="modal-backdrop" onClick={() => setRenameTarget(null)}>
          <div className="modal-window" style={{ maxWidth: '440px' }} onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>Rename Project</h3>
              <button className="modal-close-btn" onClick={() => setRenameTarget(null)}>
                <X size={18} />
              </button>
            </div>
            <form onSubmit={handleRenameSubmit}>
              <div className="modal-body">
                <div className="form-group">
                  <label>Project Title</label>
                  <input
                    type="text"
                    className="form-input"
                    value={newTitle}
                    onChange={(e) => setNewTitle(e.target.value)}
                    autoFocus
                    required
                  />
                </div>
              </div>
              <div className="modal-footer">
                <button
                  type="button"
                  className="btn-secondary"
                  onClick={() => setRenameTarget(null)}
                >
                  Cancel
                </button>
                <button type="submit" className="btn-primary" disabled={!newTitle.trim()}>
                  Save Title
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Delete Confirmation Modal */}
      {deleteTarget && (
        <div className="modal-backdrop" onClick={() => !isDeleting && setDeleteTarget(null)}>
          <div
            className="modal-window"
            style={{ maxWidth: '460px', borderColor: 'rgba(244, 63, 94, 0.4)' }}
            onClick={(e) => e.stopPropagation()}
          >
            <div className="modal-header">
              <h3 style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#fb7185' }}>
                <AlertTriangle size={20} /> Delete Project?
              </h3>
              <button
                className="modal-close-btn"
                disabled={isDeleting}
                onClick={() => setDeleteTarget(null)}
              >
                <X size={18} />
              </button>
            </div>

            <div className="modal-body">
              <p style={{ color: 'var(--text-main)', fontSize: '0.95rem', lineHeight: '1.5', marginBottom: '12px' }}>
                Are you sure you want to permanently delete{' '}
                <strong style={{ color: 'var(--accent-cyan)' }}>"{deleteTarget.title}"</strong>?
              </p>
              <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', lineHeight: '1.5' }}>
                This will delete the project workspace, all recorded video takes, character voiceovers, and generated keyframes. This action cannot be undone.
              </p>
            </div>

            <div className="modal-footer" style={{ justifyContent: 'flex-end', gap: '10px' }}>
              <button
                type="button"
                className="btn-secondary"
                disabled={isDeleting}
                onClick={() => setDeleteTarget(null)}
              >
                Cancel
              </button>
              <button
                type="button"
                className="btn-primary"
                style={{
                  background: 'linear-gradient(135deg, #f43f5e 0%, #be123c 100%)',
                  boxShadow: '0 4px 16px rgba(244, 63, 94, 0.35)',
                }}
                disabled={isDeleting}
                onClick={handleConfirmDelete}
              >
                {isDeleting ? (
                  <>
                    <RefreshCw size={15} className="animate-spin" /> Deleting...
                  </>
                ) : (
                  <>
                    <Trash2 size={15} /> Delete Permanently
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
