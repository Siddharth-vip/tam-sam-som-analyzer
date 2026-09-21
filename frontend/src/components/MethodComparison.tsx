import React from 'react';
import { Scale, CheckCircle2, AlertTriangle, AlertOctagon } from 'lucide-react';
import { MethodComparison as MethodComparisonType } from '../types/api';
import { formatCurrencyValue } from '../services/api';

interface Props {
  comparison?: MethodComparisonType | null;
  currency?: string | null;
}

export const MethodComparison: React.FC<Props> = ({ comparison, currency = 'INR' }) => {
  if (!comparison) return null;

  const activeCurrency = comparison.currency || currency || 'INR';
  const severity = (comparison.divergence_severity || '').toLowerCase();

  let severityBadge = (
    <span className="badge badge-high" style={{ display: 'inline-flex', alignItems: 'center', gap: '0.35rem' }}>
      <CheckCircle2 size={13} /> ✓ ACCEPTABLE
    </span>
  );

  if (severity === 'warning') {
    severityBadge = (
      <span className="badge badge-medium" style={{ display: 'inline-flex', alignItems: 'center', gap: '0.35rem' }}>
        <AlertTriangle size={13} /> ⚠ WARNING
      </span>
    );
  } else if (severity === 'severe_divergence' || severity === 'severe divergence') {
    severityBadge = (
      <span className="badge badge-low" style={{ display: 'inline-flex', alignItems: 'center', gap: '0.35rem' }}>
        <AlertOctagon size={13} /> ✕ SEVERE DIVERGENCE
      </span>
    );
  }

  const tdEstimate = comparison.top_down_estimate ?? comparison.top_down_tam;
  const buEstimate = comparison.bottom_up_estimate ?? comparison.bottom_up_tam;

  return (
    <div className="glass-card animate-fade-in" style={{ marginBottom: '2rem' }}>
      <div className="section-header">
        <h2 className="section-title">
          <Scale size={20} color="#818cf8" />
          Market Estimate Validation
        </h2>
        <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
          {comparison.triangulation_confidence && (
            <span
              className="badge"
              style={{
                background: 'rgba(255, 255, 255, 0.05)',
                color: 'var(--text-secondary)',
                fontSize: '0.75rem',
                border: '1px solid rgba(255, 255, 255, 0.1)',
              }}
            >
              Confidence: {comparison.triangulation_confidence.toUpperCase()}
            </span>
          )}
          {severityBadge}
        </div>
      </div>

      <div className="grid-2" style={{ marginBottom: '1.25rem' }}>
        {/* Top-Down Panel */}
        <div
          style={{
            background: 'rgba(255, 255, 255, 0.02)',
            border: '1px solid rgba(255, 255, 255, 0.06)',
            borderRadius: 'var(--radius-md)',
            padding: '1.25rem',
          }}
        >
          <div style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '0.35rem' }}>
            Top-Down TAM (Industry Spend Slicing)
          </div>
          <div style={{ fontSize: '1.6rem', fontWeight: 800, color: '#818cf8', fontFamily: 'var(--font-sans)' }}>
            {tdEstimate != null
              ? formatCurrencyValue(tdEstimate, activeCurrency, '/yr')
              : 'Not calculated'}
          </div>
          <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: '0.4rem' }}>
            Calculated by starting with total macro-market aggregate revenue and applying serviceable segment percentages.
          </p>
        </div>

        {/* Bottom-Up Panel */}
        <div
          style={{
            background: 'rgba(255, 255, 255, 0.02)',
            border: '1px solid rgba(255, 255, 255, 0.06)',
            borderRadius: 'var(--radius-md)',
            padding: '1.25rem',
          }}
        >
          <div style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '0.35rem' }}>
            Bottom-Up TAM (Unit Economics & Customers)
          </div>
          <div style={{ fontSize: '1.6rem', fontWeight: 800, color: '#06b6d4', fontFamily: 'var(--font-sans)' }}>
            {buEstimate != null
              ? formatCurrencyValue(buEstimate, activeCurrency, '/yr')
              : 'Not calculated'}
          </div>
          <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: '0.4rem' }}>
            Calculated directly from customer population headcount multiplied by average annual revenue per customer (ARPU).
          </p>
        </div>
      </div>

      {/* Divergence Metrics */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
          gap: '1rem',
          background: 'rgba(0, 0, 0, 0.25)',
          borderRadius: 'var(--radius-md)',
          padding: '1rem',
          marginBottom: '1.25rem',
        }}
      >
        <div>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Absolute Difference</span>
          <div style={{ fontSize: '1.05rem', fontWeight: 700, color: '#ffffff', fontFamily: 'var(--font-mono)' }}>
            {comparison.absolute_difference != null
              ? formatCurrencyValue(comparison.absolute_difference, activeCurrency)
              : 'N/A'}
          </div>
        </div>

        <div>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Percentage Difference (Midpoint)</span>
          <div style={{ fontSize: '1.05rem', fontWeight: 700, color: '#ffffff', fontFamily: 'var(--font-mono)' }}>
            {comparison.percentage_difference != null
              ? `${comparison.percentage_difference.toFixed(1)}%`
              : 'N/A'}
          </div>
        </div>

        <div>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Relative Ratio (Max/Min)</span>
          <div style={{ fontSize: '1.05rem', fontWeight: 700, color: '#ffffff', fontFamily: 'var(--font-mono)' }}>
            {comparison.relative_ratio != null
              ? `${comparison.relative_ratio.toFixed(2)}x`
              : 'N/A'}
          </div>
        </div>
      </div>

      {/* Root-Cause Diagnostics if Divergent */}
      {comparison.root_cause_diagnostics && comparison.root_cause_diagnostics.length > 0 && (
        <div
          style={{
            background: 'rgba(239, 68, 68, 0.05)',
            borderLeft: '3px solid #ef4444',
            padding: '0.85rem 1rem',
            borderRadius: '0 var(--radius-sm) var(--radius-sm) 0',
            fontSize: '0.85rem',
            color: 'var(--text-secondary)',
            marginBottom: '1rem',
          }}
        >
          <strong style={{ color: '#fca5a5', display: 'block', marginBottom: '0.35rem' }}>
            Divergence Diagnostic Root Causes:
          </strong>
          <ul style={{ margin: 0, paddingLeft: '1.25rem' }}>
            {comparison.root_cause_diagnostics.map((diag: string, i: number) => (
              <li key={i} style={{ marginBottom: '0.2rem' }}>
                {diag}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Narrative Explanation */}
      {(comparison.divergence_explanation || comparison.explanation) && (
        <div
          style={{
            background: 'rgba(99, 102, 241, 0.05)',
            borderLeft: '3px solid #6366f1',
            padding: '0.85rem 1rem',
            borderRadius: '0 var(--radius-sm) var(--radius-sm) 0',
            fontSize: '0.875rem',
            color: 'var(--text-secondary)',
            lineHeight: 1.5,
          }}
        >
          <strong style={{ color: '#ffffff' }}>Triangulation Analysis: </strong>
          {comparison.divergence_explanation || comparison.explanation}
        </div>
      )}
    </div>
  );
};

