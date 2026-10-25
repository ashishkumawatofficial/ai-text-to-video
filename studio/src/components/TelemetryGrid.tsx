import React from 'react';
import { Cpu, DollarSign, Clock, AlertOctagon, CheckCircle2 } from 'lucide-react';
import { TelemetryState } from '../services/api';

interface TelemetryGridProps {
  telemetry?: TelemetryState;
  isRendering?: boolean;
  onCancelRender: () => Promise<void>;
}

export const TelemetryGrid: React.FC<TelemetryGridProps> = ({ telemetry, isRendering, onCancelRender }) => {
  const cost = telemetry?.estimated_cost_usd || 0.0;
  const elapsed = telemetry?.elapsed_seconds || 0.0;
  const workers = telemetry?.worker_tiles || [];

  return (
    <div className="telemetry-panel">
      <div className="telemetry-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Cpu size={16} color="var(--accent-cyan)" />
          <span style={{ fontSize: '0.82rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.04em' }}>
            Cloud Worker Telemetry
          </span>
        </div>

        <div className="cost-meter" style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
          <DollarSign size={13} />
          <span>${cost.toFixed(4)} USD</span>
        </div>
      </div>

      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.76rem', color: 'var(--text-muted)' }}>
        <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
          <Clock size={13} /> Elapsed: {elapsed.toFixed(1)}s
        </span>
        <span>
          Active Workers: {workers.filter((w) => w.status === 'in_progress').length} / {workers.length || 4}
        </span>
      </div>

      {/* Worker Tiles */}
      <div className="worker-tiles">
        {(workers.length > 0 ? workers : [
          { worker_id: 'worker-1', beat_index: 0, status: 'idle', elapsed_seconds: 0 },
          { worker_id: 'worker-2', beat_index: 1, status: 'idle', elapsed_seconds: 0 },
          { worker_id: 'worker-3', beat_index: 2, status: 'idle', elapsed_seconds: 0 },
          { worker_id: 'worker-4', beat_index: 3, status: 'idle', elapsed_seconds: 0 },
        ]).map((w) => {
          const isActive = w.status === 'in_progress';
          const isDone = w.status === 'completed';
          return (
            <div key={w.worker_id} className={`worker-tile ${isActive ? 'active' : ''}`}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontWeight: 600 }}>
                <span>GPU #{w.beat_index + 1}</span>
                <span style={{
                  color: isDone ? 'var(--accent-emerald)' : isActive ? 'var(--accent-cyan)' : 'var(--text-dim)',
                  fontSize: '0.68rem',
                  textTransform: 'uppercase',
                }}>
                  {w.status.replace('_', ' ')}
                </span>
              </div>
              <span style={{ fontSize: '0.68rem', color: 'var(--text-dim)' }}>
                RTX 24GB • {isActive ? `${w.elapsed_seconds.toFixed(0)}s` : isDone ? 'Done' : 'Standby'}
              </span>
            </div>
          );
        })}
      </div>

      {isRendering && (
        <button
          type="button"
          onClick={onCancelRender}
          style={{
            padding: '8px 12px',
            borderRadius: '6px',
            background: 'rgba(244, 63, 94, 0.12)',
            color: 'var(--accent-rose)',
            border: '1px solid rgba(244, 63, 94, 0.3)',
            fontWeight: 700,
            fontSize: '0.78rem',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '6px',
            marginTop: '4px',
          }}
        >
          <AlertOctagon size={14} />
          <span>Stop & Cancel Cloud Workers</span>
        </button>
      )}
    </div>
  );
};
