import React from 'react';
import { Filter, ArrowDown, HelpCircle } from 'lucide-react';
import { TAMResult, SAMResult, SOMResult } from '../types/api';
import { formatCurrencyValue } from '../services/api';

interface Props {
  tam?: TAMResult | null;
  sam?: SAMResult | null;
  som?: SOMResult | null;
  currency?: string | null;
}

export const MarketFunnel: React.FC<Props> = ({ tam, sam, som, currency = 'INR' }) => {
  const activeCurrency = currency || tam?.currency || 'INR';

  const tamVal = tam?.estimate;
  const samVal = sam?.estimate;
  const somVal = som?.status === 'insufficient_evidence' ? null : som?.estimate;

  // Percentage calculations if both exist
  const samPctOfTam = tamVal && samVal ? ((samVal / tamVal) * 100).toFixed(1) : null;
  const somPctOfSam = samVal && somVal ? ((somVal / samVal) * 100).toFixed(1) : null;

  return (
    <div className="glass-card animate-fade-in" style={{ marginBottom: '2rem' }}>
      <div className="section-header">
        <h2 className="section-title">
          <Filter size={20} color="#818cf8" />
          Market Sizing Funnel
        </h2>
        <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
          TAM → SAM → SOM Progressive Narrowing
        </span>
      </div>

      <div style={{ maxWidth: '720px', margin: '0 auto', padding: '1rem 0' }}>
        {/* TAM Level */}
        <div
          style={{
            width: '100%',
            background: 'linear-gradient(90deg, rgba(99, 102, 241, 0.25) 0%, rgba(99, 102, 241, 0.1) 100%)',
            border: '1px solid rgba(99, 102, 241, 0.4)',
            borderRadius: 'var(--radius-md)',
            padding: '1.25rem 1.5rem',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            boxShadow: '0 4px 15px rgba(99, 102, 241, 0.1)',
          }}
        >
          <div>
            <span style={{ fontSize: '0.75rem', fontWeight: 700, color: '#a5b4fc', textTransform: 'uppercase' }}>
              Total Addressable Market (TAM)
            </span>
            <div style={{ fontSize: '1.25rem', fontWeight: 800, color: '#ffffff' }}>
              {tamVal != null ? formatCurrencyValue(tamVal, activeCurrency, '/yr') : 'Not calculable'}
            </div>
          </div>
          <span className="badge badge-info" style={{ fontSize: '0.8rem' }}>
            100% Demand Base
          </span>
        </div>

        {/* Transition Down 1 */}
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', margin: '0.5rem 0' }}>
          <ArrowDown size={20} color="#818cf8" />
          {samPctOfTam && (
            <span style={{ fontSize: '0.75rem', color: '#38bdf8', fontWeight: 600 }}>
              {samPctOfTam}% of Total Market
            </span>
          )}
        </div>

        {/* SAM Level */}
        <div
          style={{
            width: '85%',
            margin: '0 auto',
            background: 'linear-gradient(90deg, rgba(6, 182, 212, 0.25) 0%, rgba(6, 182, 212, 0.1) 100%)',
            border: '1px solid rgba(6, 182, 212, 0.4)',
            borderRadius: 'var(--radius-md)',
            padding: '1.1rem 1.5rem',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            boxShadow: '0 4px 15px rgba(6, 182, 212, 0.1)',
          }}
        >
          <div>
            <span style={{ fontSize: '0.75rem', fontWeight: 700, color: '#67e8f9', textTransform: 'uppercase' }}>
              Serviceable Addressable Market (SAM)
            </span>
            <div style={{ fontSize: '1.15rem', fontWeight: 800, color: '#ffffff' }}>
              {samVal != null ? formatCurrencyValue(samVal, activeCurrency, '/yr') : 'Not calculable'}
            </div>
          </div>
          <span className="badge" style={{ background: 'rgba(6, 182, 212, 0.15)', color: '#67e8f9', border: '1px solid rgba(6,182,212,0.3)' }}>
            Serviceable Scope
          </span>
        </div>

        {/* Transition Down 2 */}
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', margin: '0.5rem 0' }}>
          <ArrowDown size={20} color="#06b6d4" />
          {somPctOfSam && (
            <span style={{ fontSize: '0.75rem', color: '#34d399', fontWeight: 600 }}>
              {somPctOfSam}% of Serviceable Market
            </span>
          )}
        </div>

        {/* SOM Level */}
        <div
          style={{
            width: '70%',
            margin: '0 auto',
            background: somVal != null
              ? 'linear-gradient(90deg, rgba(16, 185, 129, 0.25) 0%, rgba(16, 185, 129, 0.1) 100%)'
              : 'linear-gradient(90deg, rgba(245, 158, 11, 0.15) 0%, rgba(245, 158, 11, 0.05) 100%)',
            border: somVal != null
              ? '1px solid rgba(16, 185, 129, 0.4)'
              : '1px dashed rgba(245, 158, 11, 0.4)',
            borderRadius: 'var(--radius-md)',
            padding: '1rem 1.5rem',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            boxShadow: '0 4px 15px rgba(0, 0, 0, 0.2)',
          }}
        >
          <div>
            <span
              style={{
                fontSize: '0.75rem',
                fontWeight: 700,
                color: somVal != null ? '#6ee7b7' : '#fcd34d',
                textTransform: 'uppercase',
              }}
            >
              Serviceable Obtainable Market (SOM)
            </span>
            <div style={{ fontSize: '1.05rem', fontWeight: 700, color: somVal != null ? '#ffffff' : '#fbbf24' }}>
              {somVal != null ? formatCurrencyValue(somVal, activeCurrency, '/yr') : 'Insufficient Evidence'}
            </div>
          </div>
          {somVal == null && (
            <span
              title="Obtainable market share was not backed by empirical source or explicit assumption."
              style={{ display: 'flex', alignItems: 'center', gap: '0.25rem', fontSize: '0.75rem', color: '#fbbf24' }}
            >
              <HelpCircle size={14} /> Uncalculated
            </span>
          )}
        </div>
      </div>
    </div>
  );
};
