import React, { useState } from 'react';
import { Calculator, ChevronDown, ChevronUp, Link as LinkIcon, AlertTriangle } from 'lucide-react';
import { CalculationStep } from '../types/api';
import { formatNumberOnly } from '../services/api';

interface Props {
  steps?: CalculationStep[];
}

export const CalculationTransparency: React.FC<Props> = ({ steps = [] }) => {
  const [isExpanded, setIsExpanded] = useState(false);

  if (!steps || steps.length === 0) {
    return null;
  }

  return (
    <div className="glass-card animate-fade-in" style={{ marginBottom: '2rem' }}>
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          cursor: 'pointer',
          userSelect: 'none',
        }}
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="section-title" style={{ margin: 0 }}>
          <Calculator size={20} color="#818cf8" />
          <span>Calculation Audit Trail ({steps.length} Steps)</span>
        </div>
        <button
          type="button"
          className="btn-secondary"
          style={{ fontSize: '0.8rem', padding: '0.35rem 0.75rem' }}
        >
          {isExpanded ? (
            <>
              Hide Steps <ChevronUp size={14} />
            </>
          ) : (
            <>
              How was this calculated? <ChevronDown size={14} />
            </>
          )}
        </button>
      </div>

      {isExpanded && (
        <div style={{ marginTop: '1.5rem', borderTop: '1px solid var(--border-subtle)', paddingTop: '1.25rem' }}>
          <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '1.25rem' }}>
            Every mathematical step is deterministically verified with operands, formula algebra, source URLs, and explicit assumptions.
          </p>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            {steps.map((step) => (
              <div
                key={step.step_number}
                style={{
                  background: 'rgba(0, 0, 0, 0.3)',
                  border: '1px solid rgba(255, 255, 255, 0.06)',
                  borderRadius: 'var(--radius-md)',
                  padding: '1.25rem',
                }}
              >
                {/* Step Header */}
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.5rem' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <span
                      style={{
                        background: 'rgba(99, 102, 241, 0.2)',
                        color: '#a5b4fc',
                        fontFamily: 'var(--font-mono)',
                        fontWeight: 700,
                        fontSize: '0.8rem',
                        padding: '0.15rem 0.55rem',
                        borderRadius: 'var(--radius-sm)',
                        border: '1px solid rgba(99, 102, 241, 0.3)',
                      }}
                    >
                      STEP {step.step_number}
                    </span>
                    <strong style={{ fontSize: '0.95rem', color: '#ffffff' }}>{step.description}</strong>
                  </div>
                  <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                    Unit: {step.unit}
                  </span>
                </div>

                {/* Formula & Result */}
                <div
                  style={{
                    background: 'rgba(15, 23, 42, 0.6)',
                    borderRadius: 'var(--radius-sm)',
                    padding: '0.75rem 1rem',
                    margin: '0.75rem 0',
                    fontFamily: 'var(--font-mono)',
                    fontSize: '0.85rem',
                  }}
                >
                  <div style={{ color: '#94a3b8', marginBottom: '0.35rem' }}>
                    <span style={{ color: '#64748b' }}>Formula: </span>
                    <span style={{ color: '#cbd5e1' }}>{step.formula}</span>
                  </div>
                  <div style={{ color: '#38bdf8', fontWeight: 600 }}>
                    <span style={{ color: '#64748b' }}>Result: </span>
                    <span>{step.result != null ? formatNumberOnly(step.result) : 'N/A'} {step.unit}</span>
                    {step.result_interval && (step.result_interval.lower != null || step.result_interval.upper != null) && (
                      <span style={{ color: '#94a3b8', fontSize: '0.75rem', marginLeft: '0.5rem' }}>
                        [{formatNumberOnly(step.result_interval.lower)} – {formatNumberOnly(step.result_interval.upper)}]
                      </span>
                    )}
                  </div>
                </div>

                {/* Operands */}
                {step.operands && Object.keys(step.operands).length > 0 && (
                  <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>
                    <span style={{ fontWeight: 600, color: 'var(--text-muted)' }}>Operands: </span>
                    {Object.entries(step.operands).map(([k, v], idx) => (
                      <span key={k} style={{ fontFamily: 'var(--font-mono)', marginRight: '0.75rem' }}>
                        {k} = {typeof v === 'number' ? formatNumberOnly(v) : JSON.stringify(v)}
                        {idx < Object.keys(step.operands).length - 1 ? ',' : ''}
                      </span>
                    ))}
                  </div>
                )}

                {/* Evidence References */}
                {step.evidence_references && step.evidence_references.length > 0 && (
                  <div style={{ fontSize: '0.78rem', color: '#38bdf8', display: 'flex', alignItems: 'center', gap: '0.35rem', flexWrap: 'wrap', marginTop: '0.4rem' }}>
                    <LinkIcon size={12} />
                    <span style={{ color: 'var(--text-muted)' }}>Sources / Evidence:</span>
                    {step.evidence_references.map((ref, idx) => (
                      <span
                        key={idx}
                        style={{
                          background: 'rgba(6, 182, 212, 0.1)',
                          padding: '0.1rem 0.4rem',
                          borderRadius: '4px',
                          border: '1px solid rgba(6, 182, 212, 0.2)',
                          maxWidth: '280px',
                          overflow: 'hidden',
                          textOverflow: 'ellipsis',
                          whiteSpace: 'nowrap',
                        }}
                        title={ref}
                      >
                        {ref}
                      </span>
                    ))}
                  </div>
                )}

                {/* Warnings */}
                {step.warnings && step.warnings.length > 0 && (
                  <div style={{ marginTop: '0.5rem', display: 'flex', alignItems: 'center', gap: '0.35rem', fontSize: '0.78rem', color: '#fbbf24' }}>
                    <AlertTriangle size={12} />
                    <span>{step.warnings.join('; ')}</span>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
