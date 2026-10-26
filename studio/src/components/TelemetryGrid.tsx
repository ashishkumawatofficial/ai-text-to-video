import React from 'react';
import { Cpu, DollarSign, Clock, CheckCircle2, RefreshCw, Zap, ShieldCheck } from 'lucide-react';
import type { TelemetryState, StoryboardCard } from '../services/api';
import { MODEL_PROVIDER_RATES } from './BeatCard';

interface TelemetryGridProps {
  telemetry?: TelemetryState;
  beats?: StoryboardCard[];
  isRendering?: boolean;
  onCancelRender: () => Promise<void>;
}

export const TelemetryGrid: React.FC<TelemetryGridProps> = ({ telemetry, beats, isRendering, onCancelRender }) => {
  const cost = telemetry?.estimated_cost_usd || 0.0;
  const elapsed = telemetry?.elapsed_seconds || 0.0;
  const workers = telemetry?.worker_tiles || [];
  const activeProvider = telemetry?.active_provider || 'fal.ai';
  const apiStatus = telemetry?.active_api_status || (isRendering ? 'IN_PROGRESS' : 'IDLE');

  const providerDisplayMap: Record<string, string> = {
    fal: 'fal.ai',
    apidot: 'apidot.ai',
    kie: 'kie.ai',
    runpod: 'runpod',
  };

  const standbyTiles = (beats && beats.length > 0)
    ? beats.map((b, idx) => {
        const modelId = (b as any).model_id || 'kling-v2.5';
        const rateInfo = MODEL_PROVIDER_RATES[modelId];
        const cheapestCode = rateInfo?.cheapest || 'apidot';
        const providerName = providerDisplayMap[cheapestCode] || 'apidot.ai';
        return {
          worker_id: `worker-${idx + 1}`,
          beat_index: idx,
          status: 'idle',
          elapsed_seconds: 0,
          provider_id: providerName,
          model_id: modelId,
          api_status: 'IDLE',
          status_detail: 'Standby',
        };
      })
    : [
        { worker_id: 'worker-1', beat_index: 0, status: 'idle', elapsed_seconds: 0, provider_id: 'fal.ai', model_id: 'kling-v2.5', api_status: 'IDLE', status_detail: 'Standby' },
        { worker_id: 'worker-2', beat_index: 1, status: 'idle', elapsed_seconds: 0, provider_id: 'apidot.ai', model_id: 'seedance-2.5', api_status: 'IDLE', status_detail: 'Standby' },
        { worker_id: 'worker-3', beat_index: 2, status: 'idle', elapsed_seconds: 0, provider_id: 'kie.ai', model_id: 'wan-2.1', api_status: 'IDLE', status_detail: 'Standby' },
        { worker_id: 'worker-4', beat_index: 3, status: 'idle', elapsed_seconds: 0, provider_id: 'fal.ai', model_id: 'minimax-h3', api_status: 'IDLE', status_detail: 'Standby' },
      ];

  const displayedWorkers = workers.length > 0 ? workers : standbyTiles;

  const getApiStatusBadge = (status: string) => {
    const s = status.toUpperCase();
    if (s.includes('IN_PROGRESS') || s.includes('PROCESSING') || s.includes('RUNNING')) {
      return {
        bg: 'rgba(59, 130, 246, 0.12)',
        border: '1px solid rgba(59, 130, 246, 0.3)',
        color: '#60a5fa',
        label: 'IN_PROGRESS',
        icon: <RefreshCw size={11} className="spin-slow" />,
      };
    }
    if (s.includes('IN_QUEUE') || s.includes('PENDING') || s.includes('WAITING') || s.includes('SUBMITTED')) {
      return {
        bg: 'rgba(245, 158, 11, 0.12)',
        border: '1px solid rgba(245, 158, 11, 0.3)',
        color: '#fbbf24',
        label: 'IN_QUEUE',
        icon: <Clock size={11} />,
      };
    }
    if (s.includes('COMPLETED') || s.includes('SUCCESS') || s.includes('DONE')) {
      return {
        bg: 'var(--accent-emerald-subtle)',
        border: '1px solid var(--accent-emerald-border)',
        color: 'var(--accent-emerald)',
        label: 'COMPLETED (200 OK)',
        icon: <CheckCircle2 size={11} />,
      };
    }
    if (s.includes('FAILED') || s.includes('FAIL')) {
      return {
        bg: 'rgba(244, 63, 94, 0.12)',
        border: '1px solid rgba(244, 63, 94, 0.3)',
        color: '#f43f5e',
        label: 'FAILED ($0.00)',
        icon: <ShieldCheck size={11} />,
      };
    }
    return {
      bg: 'rgba(255, 255, 255, 0.05)',
      border: '1px solid var(--border-subtle)',
      color: 'var(--text-dim)',
      label: 'STANDBY',
      icon: <Zap size={11} />,
    };
  };

  const headerBadge = getApiStatusBadge(apiStatus);

  return (
    <div className="telemetry-panel">
      {/* Telemetry Header */}
      <div className="telemetry-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <Cpu size={14} color="var(--text-muted)" />
          <span style={{ fontSize: '0.78rem', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.04em', color: 'var(--text-dim)' }}>
            Cloud Worker Telemetry
          </span>
        </div>

        <div className="cost-meter" style={{ display: 'flex', alignItems: 'center', gap: '3px' }}>
          <DollarSign size={12} />
          <span>${cost.toFixed(4)} USD</span>
        </div>
      </div>

      {/* Live Provider API Execution Status Banner */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '6px 10px',
          borderRadius: '6px',
          background: 'var(--bg-input)',
          border: '1px solid var(--border-subtle)',
          fontSize: '0.72rem',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <span style={{ color: 'var(--text-dim)' }}>API Gateway:</span>
          <span style={{ fontWeight: 600, color: 'var(--text-main)', fontFamily: 'var(--font-mono)' }}>{activeProvider}</span>
        </div>
        <div
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '4px',
            padding: '2px 6px',
            borderRadius: '4px',
            fontSize: '0.64rem',
            fontWeight: 600,
            background: headerBadge.bg,
            border: headerBadge.border,
            color: headerBadge.color,
          }}
        >
          {headerBadge.icon}
          <span>{headerBadge.label}</span>
        </div>
      </div>

      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.72rem', color: 'var(--text-dim)' }}>
        <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
          <Clock size={11} /> Elapsed: {elapsed.toFixed(1)}s
        </span>
        <span>
          Active: {displayedWorkers.filter((w) => (w.api_status || w.status || '').toLowerCase().includes('in_progress') || (w.api_status || w.status || '').toLowerCase().includes('running')).length} / {displayedWorkers.length}
        </span>
      </div>

      {/* Worker Tiles Tracking API Pipeline */}
      <div className="worker-tiles">
        {displayedWorkers.map((w) => {
          const rawStatus = (w.api_status || w.status || 'idle').toUpperCase();
          const badge = getApiStatusBadge(rawStatus);
          const isActive = rawStatus.includes('IN_PROGRESS') || rawStatus.includes('PROCESSING') || rawStatus.includes('RUNNING');

          return (
            <div key={w.worker_id} className={`worker-tile ${isActive ? 'active' : ''}`}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontWeight: 600, fontSize: '0.72rem', color: 'var(--text-main)' }}>
                  Scene #{w.beat_index + 1}
                </span>
                <span
                  style={{
                    padding: '1px 5px',
                    borderRadius: '3px',
                    fontSize: '0.6rem',
                    fontWeight: 600,
                    background: badge.bg,
                    border: badge.border,
                    color: badge.color,
                  }}
                >
                  {badge.label.split(' ')[0]}
                </span>
              </div>

              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.65rem', color: 'var(--text-dim)', fontFamily: 'var(--font-mono)', gap: '6px' }}>
                <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{w.provider_id || 'fal.ai'}</span>
                <span style={{ color: 'var(--border-subtle)', flexShrink: 0, opacity: 0.7 }}>•</span>
                <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', textAlign: 'right' }}>{w.model_id || 'kling-v2.5'}</span>
              </div>
            </div>
          );
        })}
      </div>

      {isRendering && (
        <button
          type="button"
          onClick={onCancelRender}
          className="btn-secondary"
          style={{ width: '100%', padding: '6px', fontSize: '0.74rem', color: 'var(--accent-rose)', borderColor: 'rgba(244, 63, 94, 0.3)' }}
        >
          Cancel Rendering Pipeline
        </button>
      )}
    </div>
  );
};
