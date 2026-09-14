import React from 'react';
import { AlertOctagon, Info, AlertTriangle } from 'lucide-react';

interface Props {
  risks?: any[] | null;
  warnings?: string[];
  errors?: string[];
}

export const RisksPanel: React.FC<Props> = ({ risks, warnings = [], errors = [] }) => {
  const hasRisks = risks && risks.length > 0;
  const hasWarnings = warnings.length > 0;
  const hasErrors = errors.length > 0;

  return (
    <div className="glass-card animate-fade-in" style={{ marginBottom: '2rem' }}>
      <div className="section-header">
        <h2 className="section-title">
          <AlertOctagon size={20} color="#f43f5e" />
          Risks, Gaps & Warnings
        </h2>
      </div>

      {/* Backend Warnings & Caveats */}
      {hasWarnings && (
        <div style={{ marginBottom: '1.25rem' }}>
          <span style={{ fontSize: '0.8rem', fontWeight: 700, color: '#fbbf24', textTransform: 'uppercase', display: 'flex', alignItems: 'center', gap: '0.35rem', marginBottom: '0.5rem' }}>
            <AlertTriangle size={14} /> Pipeline Warnings & Caveats:
          </span>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
            {warnings.map((w, idx) => (
              <div
                key={idx}
                style={{
                  background: 'rgba(245, 158, 11, 0.08)',
                  borderLeft: '3px solid #f59e0b',
                  padding: '0.6rem 0.85rem',
                  borderRadius: '0 var(--radius-sm) var(--radius-sm) 0',
                  fontSize: '0.85rem',
                  color: '#fcd34d',
                }}
              >
                {w}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Errors */}
      {hasErrors && (
        <div style={{ marginBottom: '1.25rem' }}>
          <span style={{ fontSize: '0.8rem', fontWeight: 700, color: '#f43f5e', textTransform: 'uppercase', display: 'flex', alignItems: 'center', gap: '0.35rem', marginBottom: '0.5rem' }}>
            <AlertOctagon size={14} /> Execution Errors:
          </span>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
            {errors.map((e, idx) => (
              <div
                key={idx}
                style={{
                  background: 'rgba(244, 63, 94, 0.08)',
                  borderLeft: '3px solid #f43f5e',
                  padding: '0.6rem 0.85rem',
                  borderRadius: '0 var(--radius-sm) var(--radius-sm) 0',
                  fontSize: '0.85rem',
                  color: '#fda4af',
                }}
              >
                {e}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Explicit Risk Items */}
      {hasRisks ? (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '1rem' }}>
          {risks.map((r: any, idx: number) => (
            <div
              key={idx}
              style={{
                background: 'rgba(255, 255, 255, 0.02)',
                border: '1px solid rgba(255, 255, 255, 0.06)',
                borderRadius: 'var(--radius-md)',
                padding: '1rem',
              }}
            >
              <strong style={{ color: '#ffffff' }}>{r.title || 'Risk Factor'}</strong>
              <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: '0.35rem' }}>
                {r.description || JSON.stringify(r)}
              </p>
            </div>
          ))}
        </div>
      ) : (
        !hasWarnings && !hasErrors && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--text-muted)', fontSize: '0.875rem' }}>
            <Info size={16} />
            <span>Risk information is not available in this analysis.</span>
          </div>
        )
      )}
    </div>
  );
};
