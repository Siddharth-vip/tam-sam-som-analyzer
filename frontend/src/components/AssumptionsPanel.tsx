import React from 'react';
import { HelpCircle, User, Cpu, AlertCircle, ShieldAlert, CheckCircle, Database } from 'lucide-react';
import { CalculationAssumption, AssumptionRegistry, AssumptionItem } from '../types/api';
import { formatNumberOnly } from '../services/api';

interface Props {
  assumptions?: CalculationAssumption[];
  assumptionRegistry?: AssumptionRegistry | null;
}

export const AssumptionsPanel: React.FC<Props> = ({ assumptions = [], assumptionRegistry }) => {
  const hasRegistry = assumptionRegistry && assumptionRegistry.items && assumptionRegistry.items.length > 0;
  const items: (AssumptionItem | CalculationAssumption)[] = hasRegistry ? assumptionRegistry.items : assumptions;

  if (!items || items.length === 0) {
    return (
      <div className="glass-card animate-fade-in" style={{ marginBottom: '2rem' }}>
        <div className="section-header">
          <h2 className="section-title">
            <HelpCircle size={20} color="#f59e0b" />
            Assumption Registry & Epistemic Audit
          </h2>
        </div>
        <p style={{ fontSize: '0.875rem', color: 'var(--text-muted)', fontStyle: 'italic' }}>
          No explicit modeling assumptions were used. All values were derived strictly from external evidence sources.
        </p>
      </div>
    );
  }

  return (
    <div className="glass-card animate-fade-in" style={{ marginBottom: '2rem' }}>
      <div className="section-header">
        <h2 className="section-title">
          <HelpCircle size={20} color="#f59e0b" />
          Assumption Registry & Epistemic Audit ({items.length})
        </h2>
        <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
          Facts vs User Assumptions vs Model Heuristics
        </span>
      </div>

      {hasRegistry && (
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))',
            gap: '0.75rem',
            marginBottom: '1rem',
          }}
        >
          <div style={{ background: 'rgba(255, 255, 255, 0.03)', padding: '0.6rem 0.8rem', borderRadius: 'var(--radius-sm)', border: '1px solid rgba(255,255,255,0.06)' }}>
            <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Total Parameters</div>
            <div style={{ fontSize: '1.2rem', fontWeight: 700, color: '#ffffff' }}>{assumptionRegistry.total_count}</div>
          </div>
          <div style={{ background: 'rgba(99, 102, 241, 0.08)', padding: '0.6rem 0.8rem', borderRadius: 'var(--radius-sm)', border: '1px solid rgba(99, 102, 241, 0.2)' }}>
            <div style={{ fontSize: '0.7rem', color: '#a5b4fc' }}>User Provided</div>
            <div style={{ fontSize: '1.2rem', fontWeight: 700, color: '#818cf8' }}>{assumptionRegistry.user_provided_count}</div>
          </div>
          <div style={{ background: 'rgba(245, 158, 11, 0.08)', padding: '0.6rem 0.8rem', borderRadius: 'var(--radius-sm)', border: '1px solid rgba(245, 158, 11, 0.2)' }}>
            <div style={{ fontSize: '0.7rem', color: '#fcd34d' }}>Critical / High Impact</div>
            <div style={{ fontSize: '1.2rem', fontWeight: 700, color: '#f59e0b' }}>{assumptionRegistry.high_impact_count}</div>
          </div>
          <div style={{ background: 'rgba(16, 185, 129, 0.08)', padding: '0.6rem 0.8rem', borderRadius: 'var(--radius-sm)', border: '1px solid rgba(16, 185, 129, 0.2)' }}>
            <div style={{ fontSize: '0.7rem', color: '#6ee7b7' }}>Model Derived</div>
            <div style={{ fontSize: '1.2rem', fontWeight: 700, color: '#10b981' }}>{assumptionRegistry.model_derived_count}</div>
          </div>
        </div>
      )}

      <div
        style={{
          background: 'rgba(245, 158, 11, 0.08)',
          borderLeft: '3px solid #f59e0b',
          padding: '0.75rem 1rem',
          borderRadius: '0 var(--radius-sm) var(--radius-sm) 0',
          fontSize: '0.825rem',
          color: '#fcd34d',
          marginBottom: '1.25rem',
          display: 'flex',
          alignItems: 'center',
          gap: '0.5rem',
        }}
      >
        <AlertCircle size={16} />
        <span>
          Every operand is classified by its epistemic origin. Derived mathematical values and assumptions are never misrepresented as factual evidence.
        </span>
      </div>

      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
          gap: '1rem',
        }}
      >
        {items.map((rawItem, idx) => {
          const item = rawItem as any;
          const sourceType = item.source_type || (item.is_user_provided ? 'USER_ASSUMPTION' : 'MODEL_ASSUMPTION');
          const impact = item.impact || (item.is_user_provided ? 'HIGH_IMPACT' : 'MEDIUM_IMPACT');

          let badgeBg = 'rgba(255, 255, 255, 0.08)';
          let badgeColor = '#94a3b8';
          let badgeLabel = sourceType;
          let icon = <Cpu size={11} />;

          if (sourceType === 'VERIFIED_EVIDENCE' || sourceType === 'VALIDATED_EVIDENCE') {
            badgeBg = 'rgba(16, 185, 129, 0.15)';
            badgeColor = '#34d399';
            badgeLabel = sourceType === 'VERIFIED_EVIDENCE' ? 'VERIFIED FACT' : 'VALIDATED FACT';
            icon = <CheckCircle size={11} />;
          } else if (sourceType === 'USER_ASSUMPTION' || item?.is_user_provided) {
            badgeBg = 'rgba(99, 102, 241, 0.2)';
            badgeColor = '#a5b4fc';
            badgeLabel = 'User Provided';
            icon = <User size={11} />;
          } else if (sourceType === 'DERIVED_VALUE') {
            badgeBg = 'rgba(6, 182, 212, 0.15)';
            badgeColor = '#22d3ee';
            badgeLabel = 'DERIVED VALUE';
            icon = <Database size={11} />;
          } else {
            badgeBg = 'rgba(245, 158, 11, 0.15)';
            badgeColor = '#fbbf24';
            badgeLabel = 'Model Heuristic';
            icon = <Cpu size={11} />;
          }

          let impactColor = '#94a3b8';
          if (impact === 'CRITICAL') impactColor = '#ef4444';
          else if (impact === 'HIGH_IMPACT' || impact === 'HIGH') impactColor = '#f97316';
          else if (impact === 'MEDIUM_IMPACT' || impact === 'MEDIUM') impactColor = '#facc15';

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
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.4rem', gap: '0.5rem' }}>
                <strong style={{ fontSize: '0.9rem', color: '#ffffff' }}>
                  {String(item?.name || 'Assumption').replace(/_/g, ' ')}
                </strong>
                <span
                  style={{
                    fontSize: '0.65rem',
                    fontWeight: 700,
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '0.25rem',
                    padding: '0.15rem 0.45rem',
                    borderRadius: '4px',
                    background: badgeBg,
                    color: badgeColor,
                    whiteSpace: 'nowrap',
                  }}
                >
                  {icon}
                  {badgeLabel}
                </span>
              </div>

              <div style={{ display: 'flex', alignItems: 'baseline', gap: '0.5rem', margin: '0.3rem 0' }}>
                <span style={{ fontSize: '1.15rem', fontWeight: 700, color: '#f59e0b', fontFamily: 'var(--font-mono)' }}>
                  {formatNumberOnly(item?.value)} {item?.unit || ''}
                </span>
                {item?.category && (
                  <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                    [{String(item.category)}]
                  </span>
                )}
              </div>

              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.725rem', marginTop: '0.4rem', borderTop: '1px solid rgba(255,255,255,0.04)', paddingTop: '0.4rem' }}>
                <span style={{ color: impactColor, display: 'flex', alignItems: 'center', gap: '0.25rem', fontWeight: 600 }}>
                  <ShieldAlert size={12} />
                  Impact: {String(impact).replace('_IMPACT', '')}
                </span>
                {item?.affects && item.affects.length > 0 && (
                  <span style={{ color: 'var(--text-muted)' }}>
                    Affects: {item.affects.join(', ')}
                  </span>
                )}
              </div>

              <p style={{ fontSize: '0.775rem', color: 'var(--text-secondary)', lineHeight: 1.4, marginTop: '0.4rem' }}>
                <span style={{ color: 'var(--text-muted)', fontWeight: 600 }}>Justification / Origin: </span>
                {item?.justification || item?.source_reference || 'Modeling heuristic parameter'}
              </p>
            </div>
          );
        })}
      </div>
    </div>
  );
};

