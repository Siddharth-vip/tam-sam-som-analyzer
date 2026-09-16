import React from 'react';
import { TrendingUp, ShieldAlert } from 'lucide-react';
import { TAMResult, SAMResult, SOMResult } from '../types/api';
import { ConfidenceBadge } from './ConfidenceBadge';
import { formatCurrencyValue } from '../services/api';

interface Props {
  tam?: TAMResult | null;
  sam?: SAMResult | null;
  som?: SOMResult | null;
  currency?: string | null;
}

export const MarketSizeCards: React.FC<Props> = ({ tam, sam, som, currency = 'INR' }) => {
  const activeCurrency = currency || tam?.currency || sam?.currency || 'INR';

  // Format interval string
  const getIntervalString = (item?: TAMResult | SAMResult | SOMResult | null) => {
    if (!item || !item.interval || (item.interval.lower === null && item.interval.upper === null)) {
      return null;
    }
    const lower = item.interval.lower != null ? formatCurrencyValue(item.interval.lower, activeCurrency) : '—';
    const upper = item.interval.upper != null ? formatCurrencyValue(item.interval.upper, activeCurrency) : '—';
    return `Range: ${lower} – ${upper}`;
  };

  // Helper to determine status badge text and style
  const getStatusDisplay = (item?: TAMResult | SAMResult | SOMResult | null) => {
    if (!item || item.estimate === null || item.estimate === undefined || item.status === 'insufficient_evidence') {
      return {
        label: 'NOT CALCULABLE',
        badgeClass: 'badge-medium',
        isCalculated: false,
      };
    }
    const conf = (item.confidence || '').toLowerCase();
    if (conf === 'low') {
      return {
        label: 'ESTIMATED — LOW CONFIDENCE',
        badgeClass: 'badge-medium',
        isCalculated: true,
      };
    } else if (conf === 'medium') {
      return {
        label: 'CALCULATED — MEDIUM CONFIDENCE',
        badgeClass: 'badge-verified',
        isCalculated: true,
      };
    }
    return {
      label: 'CALCULATED',
      badgeClass: 'badge-verified',
      isCalculated: true,
    };
  };

  const tamStatus = getStatusDisplay(tam);
  const samStatus = getStatusDisplay(sam);
  const somStatus = getStatusDisplay(som);
  const isSamInsufficient = !sam || sam.estimate == null || sam.status !== 'calculated';
  const isSomInsufficient = !som || som.estimate == null || som.status !== 'calculated';

  return (
    <div style={{ marginBottom: '2rem' }}>
      <div className="section-header">
        <h2 className="section-title">
          <TrendingUp size={20} color="#818cf8" />
          Market Sizing Estimates (TAM / SAM / SOM)
        </h2>
        <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
          Deterministic Calculation Output
        </span>
      </div>

      <div className="grid-3">
        {/* TAM Card */}
        <div
          className="glass-card animate-fade-in"
          style={{
            position: 'relative',
            borderTop: '4px solid #6366f1',
            background: 'linear-gradient(180deg, rgba(99, 102, 241, 0.08) 0%, rgba(17, 24, 39, 0.8) 100%)',
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.75rem' }}>
            <div>
              <span style={{ fontSize: '0.75rem', fontWeight: 700, color: '#a5b4fc', letterSpacing: '0.05em' }}>
                TOTAL ADDRESSABLE MARKET
              </span>
              <h3 style={{ fontSize: '1.4rem', fontWeight: 800, marginTop: '0.2rem' }}>TAM</h3>
            </div>
            <ConfidenceBadge confidence={tam?.confidence} />
          </div>

          <div style={{ margin: '1.25rem 0' }}>
            <div
              style={{
                fontSize: '2rem',
                fontWeight: 800,
                color: '#ffffff',
                letterSpacing: '-0.02em',
                fontFamily: 'var(--font-sans)',
              }}
            >
              {tam && tam.estimate !== null && tam.estimate !== undefined
                ? formatCurrencyValue(tam.estimate, activeCurrency, '/yr')
                : 'Not calculable'}
            </div>

            <div style={{ marginTop: '0.35rem', display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
              <span className={`badge ${tamStatus.badgeClass}`} style={{ fontSize: '0.7rem' }}>
                {tamStatus.label}
              </span>
              {getIntervalString(tam) && (
                <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                  {getIntervalString(tam)}
                </span>
              )}
            </div>
          </div>

          <p style={{ fontSize: '0.825rem', color: 'var(--text-secondary)', lineHeight: 1.4 }}>
            Total aggregate market demand across the entire identified category and target geography.
          </p>
        </div>

        {/* SAM Card */}
        <div
          className="glass-card animate-fade-in"
          style={{
            position: 'relative',
            borderTop: `4px solid ${isSamInsufficient ? '#f59e0b' : '#06b6d4'}`,
            background: isSamInsufficient
              ? 'linear-gradient(180deg, rgba(245, 158, 11, 0.08) 0%, rgba(17, 24, 39, 0.8) 100%)'
              : 'linear-gradient(180deg, rgba(6, 182, 212, 0.08) 0%, rgba(17, 24, 39, 0.8) 100%)',
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.75rem' }}>
            <div>
              <span style={{ fontSize: '0.75rem', fontWeight: 700, color: isSamInsufficient ? '#fcd34d' : '#67e8f9', letterSpacing: '0.05em' }}>
                SERVICEABLE ADDRESSABLE MARKET
              </span>
              <h3 style={{ fontSize: '1.4rem', fontWeight: 800, marginTop: '0.2rem' }}>SAM</h3>
            </div>
            {isSamInsufficient ? (
              <span className="badge badge-medium">
                <ShieldAlert size={13} />
                INSUFFICIENT EVIDENCE
              </span>
            ) : (
              <ConfidenceBadge confidence={sam?.confidence} />
            )}
          </div>

          <div style={{ margin: '1.25rem 0' }}>
            {isSamInsufficient ? (
              <div>
                <div
                  style={{
                    fontSize: '1.4rem',
                    fontWeight: 700,
                    color: '#fbbf24',
                    letterSpacing: '-0.01em',
                  }}
                >
                  Pending Evidence
                </div>
                <p style={{ fontSize: '0.8rem', color: '#fef3c7', marginTop: '0.4rem', lineHeight: 1.4 }}>
                  {sam?.message || 'No validated serviceable market evidence or user constraint was provided.'}
                </p>
              </div>
            ) : (
              <div>
                <div
                  style={{
                    fontSize: '2rem',
                    fontWeight: 800,
                    color: '#ffffff',
                    letterSpacing: '-0.02em',
                    fontFamily: 'var(--font-sans)',
                  }}
                >
                  {formatCurrencyValue(sam!.estimate, activeCurrency, '/yr')}
                </div>

                <div style={{ marginTop: '0.35rem', display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
                  <span className={`badge ${samStatus.badgeClass}`} style={{ fontSize: '0.7rem' }}>
                    {samStatus.label}
                  </span>
                  {sam?.sam_percentage_of_tam != null && (
                    <span style={{ fontSize: '0.8rem', color: '#38bdf8', fontWeight: 600 }}>
                      {sam.sam_percentage_of_tam}% of TAM
                    </span>
                  )}
                  {sam?.serviceable_customer_count != null && (
                    <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                      • {sam.serviceable_customer_count.toLocaleString()} customers
                    </span>
                  )}
                  {getIntervalString(sam) && (
                    <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                      ({getIntervalString(sam)})
                    </span>
                  )}
                </div>
              </div>
            )}
          </div>

          <p style={{ fontSize: '0.825rem', color: 'var(--text-secondary)', lineHeight: 1.4 }}>
            The specific portion of TAM reachable based on customer persona, geography, and serviceability constraints.
          </p>
        </div>

        {/* SOM Card */}
        <div
          className="glass-card animate-fade-in"
          style={{
            position: 'relative',
            borderTop: `4px solid ${isSomInsufficient ? '#f59e0b' : '#10b981'}`,
            background: isSomInsufficient
              ? 'linear-gradient(180deg, rgba(245, 158, 11, 0.08) 0%, rgba(17, 24, 39, 0.8) 100%)'
              : 'linear-gradient(180deg, rgba(16, 185, 129, 0.08) 0%, rgba(17, 24, 39, 0.8) 100%)',
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.75rem' }}>
            <div>
              <span
                style={{
                  fontSize: '0.75rem',
                  fontWeight: 700,
                  color: isSomInsufficient ? '#fcd34d' : '#6ee7b7',
                  letterSpacing: '0.05em',
                }}
              >
                SERVICEABLE OBTAINABLE MARKET
              </span>
              <h3 style={{ fontSize: '1.4rem', fontWeight: 800, marginTop: '0.2rem' }}>SOM</h3>
            </div>
            {isSomInsufficient ? (
              <span className="badge badge-medium">
                <ShieldAlert size={13} />
                UNAVAILABLE
              </span>
            ) : (
              <ConfidenceBadge confidence={som?.confidence} />
            )}
          </div>

          <div style={{ margin: '1.25rem 0' }}>
            {isSomInsufficient ? (
              <div>
                <div
                  style={{
                    fontSize: '1.4rem',
                    fontWeight: 700,
                    color: '#fbbf24',
                    letterSpacing: '-0.01em',
                  }}
                >
                  Insufficient Evidence
                </div>
                <div
                  style={{
                    fontSize: '0.8rem',
                    color: '#fbbf24',
                    marginTop: '0.35rem',
                    lineHeight: 1.4,
                  }}
                >
                  An obtainable market share or customer volume was not available, so SOM was not calculated.
                </div>
              </div>
            ) : (
              <div>
                <div
                  style={{
                    fontSize: '2rem',
                    fontWeight: 800,
                    color: '#ffffff',
                    letterSpacing: '-0.02em',
                  }}
                >
                  {formatCurrencyValue(som?.estimate, activeCurrency, '/yr')}
                </div>
                <div style={{ marginTop: '0.35rem', display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
                  <span className={`badge ${somStatus.badgeClass}`} style={{ fontSize: '0.7rem' }}>
                    {somStatus.label}
                  </span>
                  {som?.som_percentage_of_sam != null && (
                    <span style={{ fontSize: '0.8rem', color: '#34d399', fontWeight: 600 }}>
                      {som.som_percentage_of_sam}% of SAM
                    </span>
                  )}
                  {som?.obtainable_customer_count != null && (
                    <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                      • {Number(som.obtainable_customer_count).toLocaleString()} customers
                    </span>
                  )}
                  {getIntervalString(som) && (
                    <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                      ({getIntervalString(som)})
                    </span>
                  )}
                </div>
              </div>
            )}
          </div>

          <p style={{ fontSize: '0.825rem', color: 'var(--text-secondary)', lineHeight: 1.4 }}>
            The realistic market share captured within Year 1–3 under current distribution capability.
          </p>
        </div>
      </div>
    </div>
  );
};
