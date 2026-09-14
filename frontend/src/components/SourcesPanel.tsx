import React, { useState } from 'react';
import { BookOpen, ExternalLink, Award, CheckCircle, Search, FileText, AlertCircle, ShieldAlert, ChevronDown, ChevronUp } from 'lucide-react';
import { DiscoveredSource, EvidenceValidationResult, FetchedSource } from '../types/api';

interface Props {
  validationResults?: EvidenceValidationResult[];
  discoveredSources?: DiscoveredSource[];
  fetchedSources?: FetchedSource[];
  rejectedSources?: DiscoveredSource[];
  researchProvider?: string | null;
}

export const SourcesPanel: React.FC<Props> = ({
  validationResults = [],
  discoveredSources = [],
  fetchedSources = [],
  rejectedSources = [],
  researchProvider = 'mock',
}) => {
  const [showRejected, setShowRejected] = useState(false);

  // Combine sources or show validated evidence
  const hasValidated = Array.isArray(validationResults) && validationResults.length > 0;
  const hasDiscovered = Array.isArray(discoveredSources) && discoveredSources.length > 0;
  const hasFetched = Array.isArray(fetchedSources) && fetchedSources.length > 0;
  const hasRejected = Array.isArray(rejectedSources) && rejectedSources.length > 0;

  if (!hasValidated && !hasDiscovered && !hasFetched && !hasRejected) {
    return (
      <div className="glass-card animate-fade-in" style={{ marginBottom: '2rem' }}>
        <div className="section-header">
          <h2 className="section-title">
            <BookOpen size={20} color="#818cf8" />
            Sources & Evidence
          </h2>
        </div>
        <p style={{ fontSize: '0.875rem', color: 'var(--text-muted)', fontStyle: 'italic' }}>
          No external sources were retrieved for this analysis.
        </p>
      </div>
    );
  }

  const getLifecycleBadge = (stage?: string | null) => {
    const s = String(stage || 'DISCOVERED').toUpperCase();
    if (s === 'VERIFIED') {
      return (
        <span className="badge badge-high" style={{ fontSize: '0.7rem' }}>
          <CheckCircle size={10} /> VERIFIED
        </span>
      );
    }
    if (s === 'VALIDATED') {
      return (
        <span className="badge badge-info" style={{ fontSize: '0.7rem' }}>
          <CheckCircle size={10} /> VALIDATED
        </span>
      );
    }
    if (s === 'EXTRACTED') {
      return (
        <span className="badge" style={{ background: 'rgba(168, 85, 247, 0.2)', color: '#c084fc', border: '1px solid rgba(168,85,247,0.3)', fontSize: '0.7rem' }}>
          <FileText size={10} /> EXTRACTED
        </span>
      );
    }
    if (s === 'FETCHED') {
      return (
        <span className="badge" style={{ background: 'rgba(255, 255, 255, 0.1)', color: '#cbd5e1', fontSize: '0.7rem' }}>
          FETCHED
        </span>
      );
    }
    return (
      <span className="badge badge-low" style={{ fontSize: '0.7rem' }}>
        <Search size={10} /> DISCOVERED ONLY
      </span>
    );
  };

  const getTierBadge = (tier?: string | null) => {
    if (!tier) return null;
    const t = tier.toLowerCase();
    let label = 'Tier 4: General';
    let color = '#9ca3af';
    let bg = 'rgba(156, 163, 175, 0.15)';
    if (t.includes('tier_1')) {
      label = 'Tier 1: Govt/Official';
      color = '#34d399';
      bg = 'rgba(16, 185, 129, 0.15)';
    } else if (t.includes('tier_2')) {
      label = 'Tier 2: Academic/Trade';
      color = '#60a5fa';
      bg = 'rgba(59, 130, 246, 0.15)';
    } else if (t.includes('tier_3')) {
      label = 'Tier 3: Analyst/Press';
      color = '#a78bfa';
      bg = 'rgba(139, 92, 246, 0.15)';
    }
    return (
      <span
        style={{
          fontSize: '0.65rem',
          fontWeight: 700,
          padding: '0.15rem 0.4rem',
          borderRadius: '4px',
          background: bg,
          color: color,
        }}
      >
        {label}
      </span>
    );
  };

  const isMock = String(researchProvider).toLowerCase() === 'mock';

  return (
    <div className="glass-card animate-fade-in" style={{ marginBottom: '2rem' }}>
      <div className="section-header">
        <div>
          <h2 className="section-title">
            <BookOpen size={20} color="#818cf8" />
            Sources & Empirical Evidence ({hasValidated ? validationResults.length : discoveredSources.length})
          </h2>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginTop: '0.25rem' }}>
            <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
              Traceable Web Intelligence
            </span>
            <span
              className="badge"
              style={{
                fontSize: '0.65rem',
                background: isMock ? 'rgba(245, 158, 11, 0.15)' : 'rgba(16, 185, 129, 0.15)',
                color: isMock ? '#fbbf24' : '#34d399',
                border: `1px solid ${isMock ? 'rgba(245, 158, 11, 0.3)' : 'rgba(16, 185, 129, 0.3)'}`,
              }}
            >
              PROVIDER: {isMock ? 'MOCK FIXTURE' : 'LIVE SEARCH'}
            </span>
          </div>
        </div>
      </div>

      {hasValidated ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          {validationResults.map((item, idx) => {
            let domain = item.provenance?.domain;
            if (!domain && item.source_url) {
              try {
                domain = new URL(item.source_url).hostname;
              } catch {
                domain = item.source_url;
              }
            }
            domain = domain || item.source_name || 'source';
            const qualityScore = item.source_quality_score ?? item.provenance?.quality_score;
            const rawMetric = item.metric || item.metric_name || 'Metric';
            const metricDisplay = String(rawMetric).replace(/_/g, ' ');
            const extractedVal = item.value !== undefined && item.value !== null ? item.value : item.normalized_value;

            return (
              <div
                key={idx}
                style={{
                  background: 'rgba(255, 255, 255, 0.02)',
                  border: '1px solid rgba(255, 255, 255, 0.06)',
                  borderRadius: 'var(--radius-md)',
                  padding: '1.1rem 1.25rem',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.5rem' }}>
                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.2rem' }}>
                      <strong style={{ fontSize: '0.95rem', color: '#ffffff' }}>
                        {metricDisplay}
                      </strong>
                      {getLifecycleBadge(item.lifecycle_stage || 'VALIDATED')}
                      {getTierBadge(item.source_quality_tier || item.provenance?.source_quality_tier)}
                    </div>
                    <div style={{ fontSize: '0.8rem', color: '#38bdf8', display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                      <span>{item.source_name || domain}</span>
                      {item.year && <span style={{ color: 'var(--text-muted)' }}>({item.year})</span>}
                    </div>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                    {qualityScore !== undefined && qualityScore !== null && (
                      <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                        <Award size={12} color="#f59e0b" /> Quality: {(Number(qualityScore) * 100).toFixed(0)}%
                      </span>
                    )}
                    {item.source_url && (
                      <a
                        href={item.source_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="btn-secondary"
                        style={{ fontSize: '0.75rem', padding: '0.25rem 0.6rem', gap: '0.25rem' }}
                      >
                        Visit <ExternalLink size={12} />
                      </a>
                    )}
                  </div>
                </div>

                {/* Evidence Context / Snippet */}
                {item.source_context && (
                  <div
                    style={{
                      background: 'rgba(0, 0, 0, 0.25)',
                      padding: '0.65rem 0.85rem',
                      borderRadius: 'var(--radius-sm)',
                      fontSize: '0.825rem',
                      color: 'var(--text-secondary)',
                      fontStyle: 'italic',
                      lineHeight: 1.4,
                      marginTop: '0.5rem',
                      borderLeft: '2px solid #06b6d4',
                    }}
                  >
                    "{item.source_context}"
                  </div>
                )}

                {/* Metric Value */}
                {extractedVal !== null && extractedVal !== undefined && (
                  <div style={{ marginTop: '0.5rem', fontSize: '0.8rem', color: '#a5b4fc', fontFamily: 'var(--font-mono)' }}>
                    Extracted Value: {Number(extractedVal).toLocaleString()} {item.unit || ''}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      ) : (
        /* Discovered Sources Fallback */
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
          {discoveredSources.map((source, idx) => {
            const title = source.title || (source.url ? `Document at ${source.domain || source.url}` : 'Untitled Source');
            const snippet = source.snippet || 'No context snippet available.';

            return (
              <div
                key={idx}
                style={{
                  background: 'rgba(255, 255, 255, 0.02)',
                  border: '1px solid rgba(255, 255, 255, 0.06)',
                  borderRadius: 'var(--radius-md)',
                  padding: '1rem',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', marginBottom: '0.25rem' }}>
                      <strong style={{ fontSize: '0.9rem', color: '#ffffff' }}>{title}</strong>
                      {getLifecycleBadge(source.lifecycle_stage)}
                    </div>
                    <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>{snippet}</p>
                  </div>
                  {source.url && (
                    <a
                      href={source.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="btn-secondary"
                      style={{ fontSize: '0.75rem', padding: '0.25rem 0.6rem' }}
                    >
                      Open <ExternalLink size={12} />
                    </a>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Rejected / Filtered Noise Sources Audit Section */}
      {hasRejected && (
        <div style={{ marginTop: '1.25rem', paddingTop: '1rem', borderTop: '1px solid rgba(255, 255, 255, 0.05)' }}>
          <button
            type="button"
            onClick={() => setShowRejected(!showRejected)}
            style={{
              background: 'transparent',
              border: 'none',
              color: 'var(--text-muted)',
              fontSize: '0.75rem',
              display: 'flex',
              alignItems: 'center',
              gap: '0.4rem',
              cursor: 'pointer',
              padding: 0,
              textTransform: 'uppercase',
              letterSpacing: '0.05em',
            }}
          >
            <ShieldAlert size={12} color="#f59e0b" />
            Filtered Irrelevant Sources ({rejectedSources.length})
            {showRejected ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
          </button>

          {showRejected && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', marginTop: '0.75rem' }}>
              {rejectedSources.map((src, idx) => (
                <div
                  key={idx}
                  style={{
                    fontSize: '0.75rem',
                    color: '#94a3b8',
                    background: 'rgba(255, 255, 255, 0.01)',
                    border: '1px dashed rgba(255, 255, 255, 0.1)',
                    padding: '0.5rem 0.75rem',
                    borderRadius: '4px',
                  }}
                >
                  <div style={{ fontWeight: 600, color: '#e2e8f0' }}>{src.title}</div>
                  <div style={{ color: '#f87171', fontSize: '0.7rem', marginTop: '0.2rem' }}>
                    Reason: {src.relevance_reason || 'Filtered: Non-market topic / low relevance.'}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Optional: Show fetch failed sources if any exist */}
      {hasFetched && fetchedSources.some(f => f.fetch_status && f.fetch_status !== 'success') && (
        <div style={{ marginTop: '1.25rem', paddingTop: '1rem', borderTop: '1px solid rgba(255, 255, 255, 0.05)' }}>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase', display: 'flex', alignItems: 'center', gap: '0.3rem', marginBottom: '0.5rem' }}>
            <AlertCircle size={12} color="#f43f5e" /> Source Fetch Audit Notes:
          </span>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
            {fetchedSources
              .filter(f => f.fetch_status && f.fetch_status !== 'success')
              .map((f, idx) => (
                <div key={idx} style={{ fontSize: '0.75rem', color: '#fda4af', background: 'rgba(244, 63, 94, 0.05)', padding: '0.4rem 0.6rem', borderRadius: '4px' }}>
                  <strong>{f.title || f.final_url || f.original_url || 'External Document'}:</strong> {f.error_message || `Fetch status: ${f.fetch_status}`}
                </div>
              ))}
          </div>
        </div>
      )}
    </div>
  );
};
