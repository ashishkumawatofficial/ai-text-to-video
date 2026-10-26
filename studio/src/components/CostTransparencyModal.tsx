import React, { useEffect, useState } from 'react';
import { createPortal } from 'react-dom';
import { DollarSign, ShieldCheck, ExternalLink, X, RefreshCw, CheckCircle2, AlertCircle } from 'lucide-react';
import {
  fetchProvidersRegistry,
  fetchProviderQuotes,
  ProviderDocsEntry,
  ProviderPriceQuote,
} from '../services/api';
import { VIDEO_MODEL_GROUPS, MODEL_PROVIDER_RATES } from './BeatCard';

interface CostTransparencyModalProps {
  isOpen: boolean;
  onClose: () => void;
  modelId: string;
  durationSec?: number;
  resolution?: string;
  hasNativeAudio?: boolean;
  selectedProviderOverride?: string | null;
  allowProviderCascade?: boolean;
  onSelectProvider?: (providerId: string | null) => void;
  onChangeModel?: (modelId: string) => void;
  onSelectResolution?: (resolution: string) => void;
  onToggleCascade?: (enabled: boolean) => void;
}

export const CostTransparencyModal: React.FC<CostTransparencyModalProps> = ({
  isOpen,
  onClose,
  modelId,
  durationSec = 5.0,
  resolution = '720p',
  hasNativeAudio = false,
  selectedProviderOverride,
  allowProviderCascade = true,
  onSelectProvider,
  onChangeModel,
  onSelectResolution,
  onToggleCascade,
}) => {
  const [activeModelId, setActiveModelId] = useState<string>(modelId);
  const [activeResolution, setActiveResolution] = useState<string>(resolution || '720p');
  const [providers, setProviders] = useState<ProviderDocsEntry[]>([]);
  const [quotes, setQuotes] = useState<ProviderPriceQuote[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setActiveModelId(modelId);
  }, [modelId]);

  useEffect(() => {
    if (resolution) setActiveResolution(resolution);
  }, [resolution]);

  useEffect(() => {
    if (!isOpen) return;

    let isMounted = true;
    setLoading(true);
    setError(null);

    Promise.all([
      fetchProvidersRegistry().catch(() => ({ providers: [] })),
      fetchProviderQuotes(activeModelId, durationSec, activeResolution, hasNativeAudio).catch(() => ({
        quotes: [],
        model_id: activeModelId,
        recommended_provider: null,
      })),
    ])
      .then(([regData, quotesData]) => {
        if (!isMounted) return;
        setProviders(regData.providers || []);
        setQuotes(quotesData.quotes || []);
        setLoading(false);
      })
      .catch((err) => {
        if (!isMounted) return;
        setError(err.message);
        setLoading(false);
      });

    return () => {
      isMounted = false;
    };
  }, [isOpen, activeModelId, durationSec, activeResolution, hasNativeAudio]);

  if (!isOpen) return null;

  return createPortal(
    <div className="modal-backdrop" onClick={onClose}>
      <div
        className="modal-window"
        style={{
          maxWidth: '740px',
          maxHeight: '88vh',
          display: 'flex',
          flexDirection: 'column',
          background: 'var(--bg-card)',
          border: '1px solid var(--border-medium)',
          boxShadow: '0 24px 60px rgba(0, 0, 0, 0.85)',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Modal Header */}
        <div className="modal-header" style={{ padding: '16px 20px', borderBottom: '1px solid var(--border-subtle)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div
              style={{
                width: '36px',
                height: '36px',
                borderRadius: '10px',
                background: 'rgba(16, 185, 129, 0.15)',
                border: '1px solid rgba(16, 185, 129, 0.3)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                flexShrink: 0,
              }}
            >
              <DollarSign size={20} color="#10b981" />
            </div>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <h3 style={{ margin: 0, fontSize: '1.05rem', fontWeight: 700, color: '#f8fafc' }}>
                  Live Provider Cost Arbitrage
                </h3>
                <select
                  value={activeModelId}
                  onChange={(e) => {
                    const newModel = e.target.value;
                    setActiveModelId(newModel);
                    onChangeModel?.(newModel);
                  }}
                  style={{
                    background: 'rgba(30, 41, 59, 0.95)',
                    color: '#38bdf8',
                    border: '1px solid rgba(56, 189, 248, 0.4)',
                    borderRadius: '5px',
                    padding: '2px 6px',
                    fontSize: '0.72rem',
                    fontWeight: 600,
                    cursor: 'pointer',
                    outline: 'none',
                    maxWidth: '190px',
                  }}
                >
                  {VIDEO_MODEL_GROUPS.map((group) => (
                    <optgroup key={group.family} label={group.label} style={{ background: '#0f172a', color: '#94a3b8', fontWeight: 700 }}>
                      {group.models.map((m) => {
                        const r = MODEL_PROVIDER_RATES[m.id];
                        const multFal = activeResolution === '480p' ? 0.6 : activeResolution === '1080p' ? 1.35 : activeResolution === '4k' ? 2.0 : 1.0;
                        const multApi = activeResolution === '480p' ? 0.6 : activeResolution === '1080p' ? 1.25 : activeResolution === '4k' ? 1.85 : 1.0;
                        const multKie = activeResolution === '480p' ? 0.55 : activeResolution === '1080p' ? 1.45 : activeResolution === '4k' ? 2.10 : 1.0;
                        const rateStr = r ? ` [fal: $${(r.fal * multFal).toFixed(3)} | apidot: $${(r.apidot * multApi).toFixed(3)} | kie: $${(r.kie * multKie).toFixed(3)}]` : '';
                        return (
                          <option key={m.id} value={m.id} style={{ background: '#1e293b', color: '#f1f5f9' }}>
                            {m.name} ({m.limit}c{m.supportsAudio ? ' 🎵' : ''}){rateStr}
                          </option>
                        );
                      })}
                    </optgroup>
                  ))}
                </select>
              </div>

              {/* Interactive Target Resolution Selector */}
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: '4px', flexWrap: 'wrap' }}>
                <span style={{ fontSize: '0.72rem', color: 'var(--text-dim)', fontWeight: 600 }}>Target Resolution:</span>
                <div style={{ display: 'flex', gap: '3px', background: 'rgba(0, 0, 0, 0.4)', padding: '2px', borderRadius: '6px', border: '1px solid var(--border-subtle)' }}>
                  {(['480p', '720p', '1080p', '4k'] as const).map((r) => {
                    const isActive = activeResolution.toLowerCase() === r;
                    return (
                      <button
                        key={r}
                        type="button"
                        onClick={() => {
                          setActiveResolution(r);
                          onSelectResolution?.(r);
                        }}
                        style={{
                          padding: '2px 8px',
                          borderRadius: '4px',
                          fontSize: '0.68rem',
                          fontWeight: isActive ? 700 : 500,
                          background: isActive ? 'var(--text-main)' : 'transparent',
                          color: isActive ? '#0a0b0d' : 'var(--text-muted)',
                          border: 'none',
                          cursor: 'pointer',
                          transition: 'all 0.12s ease',
                        }}
                      >
                        {r.toUpperCase()}
                      </button>
                    );
                  })}
                </div>
                <span style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>
                  ({durationSec}s @ <strong style={{ color: 'var(--accent-emerald)' }}>{activeResolution.toUpperCase()}</strong> {hasNativeAudio ? '+ Audio' : ''})
                </span>
              </div>
            </div>
          </div>
          <button className="modal-close-btn" onClick={onClose} title="Close">
            <X size={18} />
          </button>
        </div>

        {/* Modal Body */}
        <div className="modal-body" style={{ padding: '20px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {/* Zero-Cost Failure Insurance Banner */}
          <div
            style={{
              padding: '12px 16px',
              borderRadius: '12px',
              background: 'linear-gradient(135deg, rgba(16, 185, 129, 0.1) 0%, rgba(15, 23, 42, 0.6) 100%)',
              border: '1px solid rgba(16, 185, 129, 0.3)',
              display: 'flex',
              alignItems: 'flex-start',
              gap: '12px',
            }}
          >
            <div
              style={{
                padding: '6px',
                borderRadius: '8px',
                background: 'rgba(16, 185, 129, 0.2)',
                color: '#34d399',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                flexShrink: 0,
                marginTop: '2px',
              }}
            >
              <ShieldCheck size={18} color="#34d399" />
            </div>
            <div>
              <h4 style={{ margin: 0, fontSize: '0.85rem', fontWeight: 700, color: '#6ee7b7' }}>
                Zero-Cost Failure Guarantee
              </h4>
              <p style={{ margin: '4px 0 0 0', fontSize: '0.74rem', color: '#cbd5e1', lineHeight: '1.45' }}>
                Server errors (HTTP 5xx), infrastructure crashes, and queue wait times are strictly <strong>$0.00</strong> across verified providers. Failed generation tasks automatically spare credits or trigger credit refunds.
              </p>
            </div>
          </div>

          {/* Auto-Failover / Cascade On-Off Switch */}
          <div
            style={{
              padding: '12px 16px',
              borderRadius: '10px',
              background: 'rgba(255, 255, 255, 0.03)',
              border: '1px solid rgba(255, 255, 255, 0.08)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              gap: '12px',
            }}
          >
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span style={{ fontSize: '0.82rem', fontWeight: 600, color: '#f1f5f9' }}>
                  Auto-Failover to Secondary Providers
                </span>
                <span
                  style={{
                    fontSize: '0.65rem',
                    padding: '2px 6px',
                    borderRadius: '4px',
                    background: allowProviderCascade ? 'rgba(16, 185, 129, 0.2)' : 'rgba(239, 68, 68, 0.2)',
                    color: allowProviderCascade ? '#34d399' : '#f87171',
                    fontWeight: 700,
                    textTransform: 'uppercase',
                  }}
                >
                  {allowProviderCascade ? 'ON (Auto-Cascade)' : 'OFF (Strict Provider)'}
                </span>
              </div>
              <p style={{ margin: '3px 0 0 0', fontSize: '0.72rem', color: '#94a3b8', lineHeight: '1.4' }}>
                {allowProviderCascade
                  ? 'If the primary or cheapest provider fails (5xx/quota), automatically cascades down the next cheapest provider to ensure video completes.'
                  : 'Fail-safe mode: Never tries more expensive providers. If the selected or cheapest provider fails, execution halts immediately with $0 charged.'}
              </p>
            </div>

            <button
              type="button"
              onClick={() => onToggleCascade?.(!allowProviderCascade)}
              style={{
                position: 'relative',
                width: '46px',
                height: '24px',
                borderRadius: '12px',
                background: allowProviderCascade ? '#10b981' : '#334155',
                border: 'none',
                cursor: 'pointer',
                transition: 'background 0.2s ease',
                flexShrink: 0,
              }}
              title={allowProviderCascade ? 'Click to disable auto-failover' : 'Click to enable auto-failover'}
            >
              <div
                style={{
                  position: 'absolute',
                  top: '2px',
                  left: allowProviderCascade ? '24px' : '2px',
                  width: '20px',
                  height: '20px',
                  borderRadius: '50%',
                  background: '#ffffff',
                  transition: 'left 0.2s ease',
                  boxShadow: '0 2px 4px rgba(0, 0, 0, 0.3)',
                }}
              />
            </button>
          </div>

          {/* Live Quotation Arbitrage Table */}
          <div>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
              <h4 style={{ margin: 0, fontSize: '0.85rem', fontWeight: 600, color: '#e2e8f0' }}>
                Live Rate Comparison
              </h4>
              <span style={{ fontSize: '0.7rem', color: 'var(--text-dim)' }}>Auto-routes to cheapest available</span>
            </div>

            {loading ? (
              <div style={{ padding: '28px', textAlign: 'center', color: 'var(--text-dim)', background: 'rgba(0, 0, 0, 0.3)', borderRadius: '10px', border: '1px solid rgba(255, 255, 255, 0.06)' }}>
                <RefreshCw size={20} className="spin-slow" style={{ margin: '0 auto 8px auto', display: 'block', color: 'var(--accent-cyan)' }} />
                <p style={{ fontSize: '0.78rem', margin: 0 }}>Fetching real-time quotes...</p>
              </div>
            ) : error ? (
              <div style={{ padding: '12px', borderRadius: '10px', background: 'rgba(239, 68, 68, 0.1)', border: '1px solid rgba(239, 68, 68, 0.3)', color: '#fca5a5', fontSize: '0.78rem' }}>
                {error}
              </div>
            ) : quotes.length === 0 ? (
              <div style={{ padding: '20px', textAlign: 'center', color: 'var(--text-dim)', background: 'rgba(0, 0, 0, 0.3)', borderRadius: '10px', border: '1px solid rgba(255, 255, 255, 0.06)', fontSize: '0.78rem' }}>
                No active provider quotes available for this model profile.
              </div>
            ) : (
              <div style={{ border: '1px solid rgba(255, 255, 255, 0.08)', borderRadius: '10px', overflow: 'hidden', background: 'rgba(0, 0, 0, 0.25)' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.76rem' }}>
                  <thead>
                    <tr style={{ background: 'rgba(255, 255, 255, 0.04)', color: 'var(--text-dim)', borderBottom: '1px solid rgba(255, 255, 255, 0.08)', textTransform: 'uppercase', fontSize: '0.68rem', letterSpacing: '0.04em' }}>
                      <th style={{ padding: '10px 12px' }}>Provider</th>
                      <th style={{ padding: '10px 12px' }}>Rate / Sec ({activeResolution.toUpperCase()})</th>
                      <th style={{ padding: '10px 12px' }}>Est. Total ({durationSec}s @ {activeResolution.toUpperCase()})</th>
                      <th style={{ padding: '10px 12px' }}>Status</th>
                      <th style={{ padding: '10px 12px', textAlign: 'right' }}>Routing</th>
                    </tr>
                  </thead>
                  <tbody>
                    {quotes.map((q) => {
                      const isCheapest = q.is_cheapest;
                      const isSelected = selectedProviderOverride === q.provider_id || (!selectedProviderOverride && isCheapest);

                      return (
                        <tr
                          key={q.provider_id}
                          style={{
                            borderBottom: '1px solid rgba(255, 255, 255, 0.04)',
                            background: isSelected ? 'rgba(16, 185, 129, 0.12)' : 'transparent',
                          }}
                        >
                          <td style={{ padding: '10px 12px', fontWeight: 600, color: '#f1f5f9' }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flexWrap: 'wrap' }}>
                              <span>{q.provider_id.replace('_', '.')}</span>
                              {q.free_tier_applicable && (
                                <span style={{ padding: '1px 5px', borderRadius: '4px', fontSize: '0.62rem', fontWeight: 700, background: 'rgba(168, 85, 247, 0.25)', color: '#c084fc', border: '1px solid rgba(168, 85, 247, 0.4)' }}>
                                  🎁 FREE TIER
                                </span>
                              )}
                              {q.is_promotional && (
                                <span style={{ padding: '1px 5px', borderRadius: '4px', fontSize: '0.62rem', fontWeight: 700, background: 'rgba(236, 72, 153, 0.2)', color: '#f472b6', border: '1px solid rgba(236, 72, 153, 0.4)' }} title={q.promo_description}>
                                  🔥 {q.discount_pct}% OFF
                                </span>
                              )}
                              {isCheapest && (
                                <span style={{ padding: '1px 5px', borderRadius: '4px', fontSize: '0.62rem', fontWeight: 700, background: 'rgba(16, 185, 129, 0.2)', color: '#34d399', border: '1px solid rgba(16, 185, 129, 0.4)' }}>
                                  LOWEST COST
                                </span>
                              )}
                            </div>
                          </td>
                          <td style={{ padding: '10px 12px', fontFamily: 'monospace', color: '#cbd5e1' }}>
                            ${q.rate_per_sec_usd.toFixed(4)}
                          </td>
                          <td style={{ padding: '10px 12px', fontFamily: 'monospace', fontWeight: 700, color: '#38bdf8' }}>
                            ${q.estimated_total_usd.toFixed(4)}
                          </td>
                          <td style={{ padding: '10px 12px' }}>
                            {q.is_available ? (
                              <span style={{ display: 'inline-flex', alignItems: 'center', gap: '4px', color: '#34d399', fontSize: '0.72rem' }}>
                                <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: '#34d399' }} />
                                Ready
                              </span>
                            ) : (
                              <span style={{ display: 'inline-flex', alignItems: 'center', gap: '4px', color: '#fbbf24', fontSize: '0.72rem' }}>
                                <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: '#fbbf24' }} />
                                Key Unset
                              </span>
                            )}
                          </td>
                          <td style={{ padding: '10px 12px', textAlign: 'right' }}>
                            <button
                              type="button"
                              onClick={() => onSelectProvider?.(isSelected ? null : q.provider_id)}
                              style={{
                                padding: '4px 10px',
                                borderRadius: '5px',
                                fontSize: '0.7rem',
                                fontWeight: 600,
                                border: 'none',
                                cursor: 'pointer',
                                background: isSelected
                                  ? 'linear-gradient(135deg, #10b981 0%, #059669 100%)'
                                  : 'rgba(255, 255, 255, 0.08)',
                                color: isSelected ? '#ffffff' : '#cbd5e1',
                              }}
                            >
                              {isSelected ? 'Active Target' : 'Force Route'}
                            </button>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {/* Official Documentation & Pricing Links Bank */}
          <div>
            <h4 style={{ margin: '0 0 8px 0', fontSize: '0.85rem', fontWeight: 600, color: '#e2e8f0' }}>
              Official Provider Documentation Bank
            </h4>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '10px' }}>
              {providers.map((p) => (
                <div
                  key={p.provider_id}
                  style={{
                    padding: '12px',
                    borderRadius: '10px',
                    background: 'rgba(0, 0, 0, 0.25)',
                    border: '1px solid rgba(255, 255, 255, 0.06)',
                    display: 'flex',
                    flexDirection: 'column',
                    justifyContent: 'space-between',
                  }}
                >
                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '6px' }}>
                      <span style={{ fontSize: '0.78rem', fontWeight: 700, color: '#f1f5f9' }}>{p.name}</span>
                      <span style={{ fontSize: '0.65rem', padding: '1px 5px', borderRadius: '4px', background: 'rgba(255, 255, 255, 0.08)', color: 'var(--text-dim)' }}>
                        {p.supported_models_count} Models
                      </span>
                    </div>
                    <p style={{ fontSize: '0.7rem', color: '#94a3b8', lineHeight: '1.4', margin: '0 0 10px 0', maxHeight: '50px', overflow: 'hidden' }}>
                      {p.failure_billing_policy}
                    </p>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', paddingTop: '8px', borderTop: '1px solid rgba(255, 255, 255, 0.06)' }}>
                    <a
                      href={p.official_docs_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      style={{ fontSize: '0.72rem', fontWeight: 600, color: 'var(--accent-cyan)', textDecoration: 'none', display: 'inline-flex', alignItems: 'center', gap: '3px' }}
                    >
                      <span>Docs</span>
                      <ExternalLink size={11} />
                    </a>
                    <span style={{ color: 'rgba(255, 255, 255, 0.2)' }}>•</span>
                    <a
                      href={p.pricing_docs_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      style={{ fontSize: '0.72rem', fontWeight: 600, color: '#34d399', textDecoration: 'none', display: 'inline-flex', alignItems: 'center', gap: '3px' }}
                    >
                      <span>Pricing</span>
                      <ExternalLink size={11} />
                    </a>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Modal Footer */}
        <div className="modal-footer" style={{ padding: '12px 20px', borderTop: '1px solid rgba(255, 255, 255, 0.08)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <button
            type="button"
            onClick={() => onSelectProvider?.(null)}
            style={{
              background: 'transparent',
              border: 'none',
              color: 'var(--text-dim)',
              fontSize: '0.72rem',
              cursor: 'pointer',
              textDecoration: 'underline',
            }}
          >
            Reset to Auto Arbitrage (Lowest Cost)
          </button>
          <button
            type="button"
            onClick={onClose}
            className="btn-primary"
            style={{ padding: '6px 16px', fontSize: '0.78rem' }}
          >
            Done
          </button>
        </div>
      </div>
    </div>,
    document.body
  );
};
