import React, { useState, useRef, useEffect } from 'react';
import {
  Film,
  MoreVertical,
  Play,
  Copy,
  Trash2,
  Edit3,
  Clock,
  Layers,
  Folder,
  FolderOpen,
  Check,
} from 'lucide-react';
import type { ProjectSummary } from '../types/project';

interface ProjectCardProps {
  project: ProjectSummary;
  onOpen: (projectId: string) => void;
  onRename: (projectId: string, currentTitle: string) => void;
  onDuplicate: (projectId: string) => void;
  onDelete: (projectId: string) => void;
  onRevealFolder?: (projectId: string) => void;
}

export function ProjectCard({
  project,
  onOpen,
  onRename,
  onDuplicate,
  onDelete,
  onRevealFolder,
}: ProjectCardProps) {
  const [menuOpen, setMenuOpen] = useState(false);
  const [imgError, setImgError] = useState(false);
  const [copied, setCopied] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  // Close menu on click outside
  useEffect(() => {
    if (!menuOpen) return;
    const handleClickOutside = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setMenuOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [menuOpen]);

  const formattedDate = new Date(project.updated_at || project.created_at).toLocaleDateString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });

  return (
    <div
      className={`project-card ${menuOpen ? 'menu-active' : ''}`}
      style={{ zIndex: menuOpen ? 60 : 1 }}
      onClick={() => onOpen(project.project_id)}
    >
      {/* Thumbnail Container */}
      <div className="project-thumb-container">
        {project.thumbnail_url && !imgError ? (
          <img
            src={project.thumbnail_url}
            alt=""
            className="project-thumb-img"
            loading="lazy"
            onError={() => setImgError(true)}
          />
        ) : (
          <div className="project-thumb-placeholder">
            <div className="project-thumb-placeholder-icon">
              <Film size={24} />
            </div>
            <span>Story Plan</span>
          </div>
        )}

        {/* Badges Overlay */}
        <div className="project-thumb-badges">
          <span className="badge-aspect">{project.aspect_ratio}</span>
          <span className={`badge-status ${project.status}`}>{project.status}</span>
        </div>
      </div>

      {/* Card Body */}
      <div className="project-card-body">
        <div className="project-title-row">
          <h3 className="project-card-title" title={project.title}>
            {project.title}
          </h3>

          <div
            ref={menuRef}
            style={{ position: 'relative' }}
            onClick={(e) => {
              e.stopPropagation();
            }}
          >
            <button
              className="card-action-menu-btn"
              onClick={(e) => {
                e.stopPropagation();
                setMenuOpen((prev) => !prev);
              }}
              title="Project Actions"
            >
              <MoreVertical size={16} />
            </button>

            {menuOpen && (
              <div
                className="card-dropdown-menu"
                onClick={(e) => e.stopPropagation()}
              >
                <button
                  className="dropdown-item"
                  onClick={() => {
                    setMenuOpen(false);
                    onOpen(project.project_id);
                  }}
                >
                  <Play size={14} /> Open Studio
                </button>
                <button
                  className="dropdown-item"
                  onClick={() => {
                    setMenuOpen(false);
                    onRename(project.project_id, project.title);
                  }}
                >
                  <Edit3 size={14} /> Rename
                </button>
                <button
                  className="dropdown-item"
                  onClick={() => {
                    setMenuOpen(false);
                    onDuplicate(project.project_id);
                  }}
                >
                  <Copy size={14} /> Duplicate
                </button>
                <div className="dropdown-divider" />
                <button
                  className="dropdown-item"
                  onClick={() => {
                    setMenuOpen(false);
                    onRevealFolder?.(project.project_id);
                  }}
                  title="Reveal project folder on your system"
                >
                  <FolderOpen size={14} /> Reveal in Finder
                </button>
                <button
                  className="dropdown-item"
                  onClick={() => {
                    const loc = project.project_location || `outputs/projects/${project.project_id}`;
                    navigator.clipboard.writeText(loc);
                    setCopied(true);
                    setTimeout(() => setCopied(false), 2000);
                  }}
                  title="Copy project storage path"
                >
                  {copied ? <Check size={14} color="#10b981" /> : <Copy size={14} />}
                  {copied ? 'Copied Path!' : 'Copy Path'}
                </button>
                <div className="dropdown-divider" />
                <button
                  className="dropdown-item danger"
                  onClick={() => {
                    setMenuOpen(false);
                    onDelete(project.project_id);
                  }}
                >
                  <Trash2 size={14} /> Delete Project
                </button>
              </div>
            )}
          </div>
        </div>

        <p className="project-card-prompt" title={project.concept_prompt}>
          {project.concept_prompt || 'No concept description provided.'}
        </p>

        {/* Project Location Pill */}
        {project.project_location && (
          <div
            className="project-location-pill"
            title={`Workspace Location: ${project.project_location}\nClick to reveal in Finder`}
            onClick={(e) => {
              e.stopPropagation();
              onRevealFolder?.(project.project_id);
            }}
          >
            <Folder size={11} className="location-icon" />
            <span className="location-path">{project.project_location}</span>
          </div>
        )}

        {/* Card Metadata Footer */}
        <div className="project-card-meta">
          <div className="meta-item" title="Scene beats / Total takes">
            <Layers size={13} color="var(--accent-cyan)" />
            <span>
              {project.beat_count} {project.beat_count === 1 ? 'beat' : 'beats'}
              {project.total_takes_count > 0 && ` • ${project.total_takes_count} takes`}
            </span>
          </div>

          <div className="meta-item" title="Last modified date">
            <Clock size={13} color="var(--text-dim)" />
            <span>{formattedDate}</span>
          </div>
        </div>
      </div>
    </div>
  );
}
