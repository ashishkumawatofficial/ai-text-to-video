import React from 'react';
import { Film } from 'lucide-react';
import type { RenderTake } from '../types/project';

interface TakeSwitcherProps {
  projectId: string;
  beatIndex: number;
  takes: RenderTake[];
  activeTakeId?: string | null;
  onSelectTake: (takeId: string) => void;
}

export function TakeSwitcher({
  takes,
  activeTakeId,
  onSelectTake,
}: TakeSwitcherProps) {
  if (!takes || takes.length <= 1) {
    return null; // Only show take switcher when multiple takes or a completed take exists
  }

  return (
    <div className="take-switcher-container">
      <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
        <Film size={12} color="var(--text-muted)" />
        <span className="take-switcher-label">Takes ({takes.length}):</span>
      </div>

      <div style={{ display: 'flex', gap: '4px', flexWrap: 'wrap' }}>
        {takes.map((take) => {
          const isActive = take.take_id === activeTakeId || (!activeTakeId && take.take_index === takes.length);
          const timeStr = new Date(take.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
          const tooltip = `Take #${take.take_index} (${timeStr})\nPrompt: ${take.prompt || 'Default'}`;

          return (
            <button
              key={take.take_id}
              className={`take-pill ${isActive ? 'active' : ''}`}
              title={tooltip}
              onClick={(e) => {
                e.stopPropagation();
                onSelectTake(take.take_id);
              }}
            >
              Take {take.take_index} {isActive ? '★' : ''}
            </button>
          );
        })}
      </div>
    </div>
  );
}
