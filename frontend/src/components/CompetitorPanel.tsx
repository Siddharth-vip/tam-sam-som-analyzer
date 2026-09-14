import React from 'react';
import { Users, Info, ExternalLink, Tag } from 'lucide-react';
import { CompetitorInfo } from '../types/api';

interface Props {
  competitors?: CompetitorInfo[] | null;
}

export const CompetitorPanel: React.FC<Props> = ({ competitors }) => {
  const hasCompetitors = competitors && competitors.length > 0;

  return (
    <div className="glass-card animate-fade-in" style={{ marginBottom: '2rem' }}>
      <div className="section-header">
        <h2 className="section-title">
          <Users size={20} color="#818cf8" />
          Competitive Landscape
        </h2>
      </div>

      {hasCompetitors ? (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: '1rem' }}>
          {competitors.map((c, idx) => (
            <div
              key={idx}
              style={{
                background: 'rgba(255, 255, 255, 0.02)',
                border: '1px solid rgba(255, 255, 255, 0.06)',
                borderRadius: 'var(--radius-md)',
                padding: '1rem',
                display: 'flex',
                flexDirection: 'column',
                gap: '0.5rem',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <strong style={{ color: '#ffffff', fontSize: '1rem' }}>{c.name}</strong>
                {c.pricing && (
                  <span className="badge" style={{ background: 'rgba(16, 185, 129, 0.1)', color: '#34d399', fontSize: '0.7rem' }}>
                    <Tag size={10} style={{ marginRight: '0.2rem' }} />
                    {c.pricing}
                  </span>
                )}
              </div>

              {c.product_service && (
                <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', margin: 0 }}>
                  {c.product_service}
                </p>
              )}

              {c.differentiators && (
                <p style={{ fontSize: '0.75rem', color: '#a5b4fc', margin: 0, fontStyle: 'italic' }}>
                  Positioning: {c.differentiators}
                </p>
              )}

              {c.source_url && (
                <div style={{ marginTop: 'auto', paddingTop: '0.5rem', borderTop: '1px solid rgba(255, 255, 255, 0.04)' }}>
                  <a
                    href={c.source_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    style={{
                      fontSize: '0.7rem',
                      color: 'var(--color-primary)',
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '0.25rem',
                      textDecoration: 'none',
                    }}
                  >
                    <span>{c.source_name || 'Source Evidence'}</span>
                    <ExternalLink size={10} />
                  </a>
                </div>
              )}
            </div>
          ))}
        </div>
      ) : (
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--text-muted)', fontSize: '0.875rem' }}>
          <Info size={16} />
          <span>Competitive analysis data is not available in this analysis.</span>
        </div>
      )}
    </div>
  );
};

