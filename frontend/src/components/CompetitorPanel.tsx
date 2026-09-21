import React, { useState } from 'react';
import { Users, Info, ExternalLink, Tag, Table, LayoutGrid } from 'lucide-react';
import { CompetitorInfo } from '../types/api';

interface Props {
  competitors?: CompetitorInfo[] | null;
  competitorComparison?: Record<string, any>[] | null;
}

export const CompetitorPanel: React.FC<Props> = ({ competitors }) => {
  const [viewMode, setViewMode] = useState<'cards' | 'matrix'>('cards');
  const hasCompetitors = competitors && competitors.length > 0;

  return (
    <div className="glass-card animate-fade-in" style={{ marginBottom: '2rem' }}>
      <div className="section-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h2 className="section-title">
          <Users size={20} color="#818cf8" />
          Competitor Analysis & Comparison Matrix
        </h2>
        {hasCompetitors && (
          <div style={{ display: 'flex', gap: '0.5rem' }}>
            <button
              onClick={() => setViewMode('cards')}
              className={`btn ${viewMode === 'cards' ? 'btn-primary' : 'btn-outline'}`}
              style={{ padding: '0.35rem 0.75rem', fontSize: '0.8rem', display: 'flex', alignItems: 'center', gap: '0.25rem' }}
            >
              <LayoutGrid size={14} /> Cards
            </button>
            <button
              onClick={() => setViewMode('matrix')}
              className={`btn ${viewMode === 'matrix' ? 'btn-primary' : 'btn-outline'}`}
              style={{ padding: '0.35rem 0.75rem', fontSize: '0.8rem', display: 'flex', alignItems: 'center', gap: '0.25rem' }}
            >
              <Table size={14} /> Comparison Matrix
            </button>
          </div>
        )}
      </div>

      {hasCompetitors ? (
        viewMode === 'cards' ? (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1rem' }}>
            {competitors.map((c, idx) => (
              <div
                key={idx}
                style={{
                  background: 'rgba(255, 255, 255, 0.02)',
                  border: '1px solid rgba(255, 255, 255, 0.06)',
                  borderRadius: 'var(--radius-md)',
                  padding: '1.25rem',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '0.6rem',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                  <div>
                    <strong style={{ color: '#ffffff', fontSize: '1.05rem' }}>{c.name}</strong>
                    {c.category && (
                      <div style={{ fontSize: '0.75rem', color: '#94a3b8' }}>{c.category}</div>
                    )}
                  </div>
                  <span
                    className="badge"
                    style={{
                      background: (c.public_pricing && c.public_pricing !== 'Pricing not publicly available') ? 'rgba(16, 185, 129, 0.1)' : 'rgba(148, 163, 184, 0.1)',
                      color: (c.public_pricing && c.public_pricing !== 'Pricing not publicly available') ? '#34d399' : '#94a3b8',
                      fontSize: '0.75rem',
                    }}
                  >
                    <Tag size={11} style={{ marginRight: '0.2rem' }} />
                    {c.public_pricing || c.pricing || 'Pricing not publicly available'}
                  </span>
                </div>

                {c.product_service && (
                  <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', margin: 0 }}>
                    {c.product_service}
                  </p>
                )}

                {c.key_features && c.key_features.length > 0 && (
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.35rem', marginTop: '0.25rem' }}>
                    {c.key_features.map((f, fIdx) => (
                      <span key={fIdx} style={{ fontSize: '0.7rem', background: 'rgba(99, 102, 241, 0.1)', color: '#a5b4fc', padding: '0.15rem 0.4rem', borderRadius: '4px' }}>
                        {f}
                      </span>
                    ))}
                  </div>
                )}

                {c.differentiators && (
                  <p style={{ fontSize: '0.8rem', color: '#c7d2fe', margin: 0, fontStyle: 'italic' }}>
                    Positioning: {c.differentiators}
                  </p>
                )}

                {(c.source_url || c.website) && (
                  <div style={{ marginTop: 'auto', paddingTop: '0.6rem', borderTop: '1px solid rgba(255, 255, 255, 0.04)' }}>
                    <a
                      href={c.source_url || c.website || '#'}
                      target="_blank"
                      rel="noopener noreferrer"
                      style={{
                        fontSize: '0.75rem',
                        color: 'var(--color-primary)',
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '0.25rem',
                        textDecoration: 'none',
                      }}
                    >
                      <span>{c.source_name || c.website || 'Verified Source'}</span>
                      <ExternalLink size={11} />
                    </a>
                  </div>
                )}
              </div>
            ))}
          </div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table className="evidence-table" style={{ width: '100%', textAlign: 'left', borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid rgba(255, 255, 255, 0.1)', color: '#94a3b8', fontSize: '0.8rem' }}>
                  <th style={{ padding: '0.75rem' }}>Competitor</th>
                  <th style={{ padding: '0.75rem' }}>Target Customer</th>
                  <th style={{ padding: '0.75rem' }}>Geography</th>
                  <th style={{ padding: '0.75rem' }}>Key Features</th>
                  <th style={{ padding: '0.75rem' }}>Pricing Model</th>
                  <th style={{ padding: '0.75rem' }}>Public Pricing</th>
                  <th style={{ padding: '0.75rem' }}>Differentiators</th>
                </tr>
              </thead>
              <tbody>
                {competitors.map((c, idx) => (
                  <tr key={idx} style={{ borderBottom: '1px solid rgba(255, 255, 255, 0.04)', fontSize: '0.85rem' }}>
                    <td style={{ padding: '0.75rem', fontWeight: 600, color: '#ffffff' }}>{c.name}</td>
                    <td style={{ padding: '0.75rem', color: '#cbd5e1' }}>{c.target_customers || c.target_market || 'Businesses'}</td>
                    <td style={{ padding: '0.75rem', color: '#94a3b8' }}>{c.geography || 'Global'}</td>
                    <td style={{ padding: '0.75rem', color: '#a5b4fc' }}>
                      {(c.key_features && c.key_features.length > 0) ? c.key_features.join(', ') : 'Workflow Suite'}
                    </td>
                    <td style={{ padding: '0.75rem', color: '#cbd5e1' }}>{c.pricing_model || 'Subscription'}</td>
                    <td style={{ padding: '0.75rem', color: (c.public_pricing && c.public_pricing !== 'Pricing not publicly available') ? '#34d399' : '#94a3b8' }}>
                      {c.public_pricing || c.pricing || 'Pricing not publicly available'}
                    </td>
                    <td style={{ padding: '0.75rem', color: '#c7d2fe', fontStyle: 'italic' }}>{c.differentiators || 'Established player'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )
      ) : (
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--text-muted)', fontSize: '0.875rem' }}>
          <Info size={16} />
          <span>Competitive analysis data is not available in this analysis.</span>
        </div>
      )}
    </div>
  );
};


