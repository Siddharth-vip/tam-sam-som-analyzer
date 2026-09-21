import React from 'react';
import { TrendingUp, Target, Lightbulb, DollarSign, Award, Layers, ShieldCheck, Zap } from 'lucide-react';
import {
  MarketTrendItem,
  MarketGrowthItem,
  CustomerSegmentItem,
  ValuePropositionAnalysis,
  BusinessModelAnalysis,
  MarketAttractivenessAssessment,
} from '../types/api';

interface Props {
  trends?: MarketTrendItem[] | null;
  growth?: MarketGrowthItem | null;
  segmentation?: CustomerSegmentItem[] | null;
  valueProp?: ValuePropositionAnalysis | null;
  businessModel?: BusinessModelAnalysis | null;
  attractiveness?: MarketAttractivenessAssessment | null;
}

export const MarketInsightsPanel: React.FC<Props> = ({
  trends,
  growth,
  segmentation,
  valueProp,
  businessModel,
  attractiveness,
}) => {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem', marginBottom: '2rem' }}>
      {/* 1. Value Proposition & Competitive Differentiation */}
      {valueProp && (
        <div className="glass-card animate-fade-in">
          <div className="section-header">
            <h2 className="section-title">
              <Lightbulb size={20} color="#fbbf24" />
              Value Proposition & Solution Architecture
            </h2>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '1.25rem' }}>
            <div style={{ background: 'rgba(255, 255, 255, 0.02)', padding: '1rem', borderRadius: 'var(--radius-md)', border: '1px solid rgba(255, 255, 255, 0.05)' }}>
              <h4 style={{ color: '#f87171', fontSize: '0.85rem', marginBottom: '0.5rem', display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                <Target size={14} /> Core Problem & Pain Point
              </h4>
              <p style={{ fontSize: '0.85rem', color: '#cbd5e1', marginBottom: '0.5rem' }}>{valueProp.customer_problem}</p>
              <p style={{ fontSize: '0.8rem', color: '#94a3b8', fontStyle: 'italic' }}>Limitation: {valueProp.current_pain_point}</p>
            </div>

            <div style={{ background: 'rgba(255, 255, 255, 0.02)', padding: '1rem', borderRadius: 'var(--radius-md)', border: '1px solid rgba(255, 255, 255, 0.05)' }}>
              <h4 style={{ color: '#34d399', fontSize: '0.85rem', marginBottom: '0.5rem', display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                <Zap size={14} /> SaaS Product Solution
              </h4>
              <p style={{ fontSize: '0.85rem', color: '#cbd5e1', marginBottom: '0.5rem' }}>{valueProp.product_solution}</p>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.35rem' }}>
                {valueProp.key_capabilities.map((cap, i) => (
                  <span key={i} style={{ fontSize: '0.7rem', background: 'rgba(52, 211, 153, 0.1)', color: '#34d399', padding: '0.2rem 0.5rem', borderRadius: '4px' }}>
                    {cap}
                  </span>
                ))}
              </div>
            </div>

            <div style={{ background: 'rgba(255, 255, 255, 0.02)', padding: '1rem', borderRadius: 'var(--radius-md)', border: '1px solid rgba(255, 255, 255, 0.05)' }}>
              <h4 style={{ color: '#818cf8', fontSize: '0.85rem', marginBottom: '0.5rem', display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                <Award size={14} /> Measurable Benefits & Whitespace Moat
              </h4>
              <p style={{ fontSize: '0.85rem', color: '#cbd5e1', marginBottom: '0.35rem' }}><strong>Operational:</strong> {valueProp.operational_benefit}</p>
              {valueProp.financial_time_saving_benefit && (
                <p style={{ fontSize: '0.85rem', color: '#cbd5e1', marginBottom: '0.35rem' }}><strong>ROI:</strong> {valueProp.financial_time_saving_benefit}</p>
              )}
              <p style={{ fontSize: '0.8rem', color: '#a5b4fc', fontStyle: 'italic' }}>Moat: {valueProp.differentiation_opportunity}</p>
            </div>
          </div>

          {valueProp.value_proposition_statement && (
            <div style={{ marginTop: '1rem', padding: '0.85rem', background: 'rgba(99, 102, 241, 0.08)', borderRadius: 'var(--radius-md)', borderLeft: '4px solid #6366f1' }}>
              <span style={{ fontSize: '0.85rem', color: '#e0e7ff', fontWeight: 500 }}>
                💡 {valueProp.value_proposition_statement}
              </span>
            </div>
          )}
        </div>
      )}

      {/* 2. Market Growth & Trends */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '1.5rem' }}>
        {/* Market Growth & Deterministic CAGR */}
        {growth && (
          <div className="glass-card animate-fade-in">
            <div className="section-header">
              <h2 className="section-title">
                <TrendingUp size={20} color="#34d399" />
                Market Growth & CAGR
              </h2>
              <span
                className="badge"
                style={{
                  background: growth.cagr_type === 'CALCULATED_CAGR' ? 'rgba(52, 211, 153, 0.15)' : 'rgba(99, 102, 241, 0.15)',
                  color: growth.cagr_type === 'CALCULATED_CAGR' ? '#34d399' : '#818cf8',
                  fontSize: '0.75rem',
                }}
              >
                {growth.cagr_type === 'CALCULATED_CAGR' ? 'CALCULATED_CAGR' : 'SOURCE_REPORTED_CAGR'}
              </span>
            </div>

            <div style={{ display: 'flex', alignItems: 'baseline', gap: '0.75rem', marginBottom: '1rem' }}>
              <span style={{ fontSize: '2rem', fontWeight: 700, color: '#34d399' }}>
                {growth.cagr_percentage_string || `${((growth.cagr || 0.168) * 100).toFixed(1)}% CAGR`}
              </span>
              <span style={{ fontSize: '0.85rem', color: '#94a3b8' }}>
                Forecast Horizon: {growth.forecast_period || '2024-2030'}
              </span>
            </div>

            {growth.growth_drivers && growth.growth_drivers.length > 0 && (
              <div>
                <h4 style={{ fontSize: '0.8rem', color: '#94a3b8', textTransform: 'uppercase', marginBottom: '0.5rem' }}>
                  Macro Growth Catalysts
                </h4>
                <ul style={{ margin: 0, paddingLeft: '1.25rem', fontSize: '0.85rem', color: '#cbd5e1', display: 'flex', flexDirection: 'column', gap: '0.35rem' }}>
                  {growth.growth_drivers.map((d, i) => (
                    <li key={i}>{d}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}

        {/* Business Model Analysis */}
        {businessModel && (
          <div className="glass-card animate-fade-in">
            <div className="section-header">
              <h2 className="section-title">
                <DollarSign size={20} color="#60a5fa" />
                Business & Monetization Model
              </h2>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', fontSize: '0.85rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid rgba(255, 255, 255, 0.05)', paddingBottom: '0.4rem' }}>
                <span style={{ color: '#94a3b8' }}>Model Architecture:</span>
                <span style={{ color: '#ffffff', fontWeight: 600 }}>{businessModel.business_model}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid rgba(255, 255, 255, 0.05)', paddingBottom: '0.4rem' }}>
                <span style={{ color: '#94a3b8' }}>Pricing Unit:</span>
                <span style={{ color: '#60a5fa', fontWeight: 600 }}>{businessModel.pricing_model} ({businessModel.pricing_unit})</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid rgba(255, 255, 255, 0.05)', paddingBottom: '0.4rem' }}>
                <span style={{ color: '#94a3b8' }}>Billing Terms:</span>
                <span style={{ color: '#ffffff' }}>{businessModel.billing_frequency}</span>
              </div>
              <div>
                <span style={{ color: '#94a3b8', display: 'block', marginBottom: '0.35rem' }}>Expansion Revenue Vectors:</span>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.35rem' }}>
                  {businessModel.possible_expansion_revenue.map((v, i) => (
                    <span key={i} style={{ fontSize: '0.75rem', background: 'rgba(96, 165, 250, 0.1)', color: '#93c5fd', padding: '0.2rem 0.5rem', borderRadius: '4px' }}>
                      {v}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* 3. Market Trends */}
      {trends && trends.length > 0 && (
        <div className="glass-card animate-fade-in">
          <div className="section-header">
            <h2 className="section-title">
              <TrendingUp size={20} color="#a78bfa" />
              B2B SaaS Market Trends & Evidence
            </h2>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1rem' }}>
            {trends.map((t, idx) => (
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
                  <strong style={{ color: '#ffffff', fontSize: '0.95rem' }}>{t.trend}</strong>
                  <span className="badge" style={{ background: 'rgba(167, 139, 250, 0.1)', color: '#c4b5fd', fontSize: '0.7rem' }}>
                    {t.confidence || 'medium'}
                  </span>
                </div>
                <p style={{ fontSize: '0.85rem', color: '#cbd5e1', margin: 0 }}>{t.explanation}</p>
                <div style={{ fontSize: '0.75rem', color: '#a78bfa', marginTop: 'auto', paddingTop: '0.5rem', borderTop: '1px solid rgba(255, 255, 255, 0.04)' }}>
                  <strong>Impact:</strong> {t.impact_on_market}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 4. Customer Tier Segmentation */}
      {segmentation && segmentation.length > 0 && (
        <div className="glass-card animate-fade-in">
          <div className="section-header">
            <h2 className="section-title">
              <Layers size={20} color="#38bdf8" />
              Customer Tier Segmentation
            </h2>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1rem' }}>
            {segmentation.map((s, idx) => (
              <div
                key={idx}
                style={{
                  background: 'rgba(255, 255, 255, 0.02)',
                  border: '1px solid rgba(255, 255, 255, 0.06)',
                  borderRadius: 'var(--radius-md)',
                  padding: '1rem',
                }}
              >
                <h4 style={{ color: '#38bdf8', fontSize: '0.95rem', marginBottom: '0.35rem' }}>{s.segment_name}</h4>
                <p style={{ fontSize: '0.8rem', color: '#94a3b8', marginBottom: '0.5rem' }}>{s.description}</p>
                <div style={{ fontSize: '0.8rem', color: '#cbd5e1', display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
                  {s.business_need && <div><strong>Need:</strong> {s.business_need}</div>}
                  {s.pricing_relevance && <div><strong>Pricing Fit:</strong> {s.pricing_relevance}</div>}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 5. Explainable Market Attractiveness */}
      {attractiveness && (
        <div className="glass-card animate-fade-in">
          <div className="section-header">
            <h2 className="section-title">
              <ShieldCheck size={20} color="#10b981" />
              Market Attractiveness & Strategic Feasibility
            </h2>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <span
                className="badge"
                style={{
                  background: attractiveness.rating === 'HIGH' ? 'rgba(16, 185, 129, 0.2)' : 'rgba(245, 158, 11, 0.2)',
                  color: attractiveness.rating === 'HIGH' ? '#34d399' : '#fbbf24',
                  fontSize: '0.85rem',
                  fontWeight: 700,
                  padding: '0.3rem 0.75rem',
                }}
              >
                Rating: {attractiveness.rating} ({attractiveness.score}/10)
              </span>
            </div>
          </div>

          <p style={{ fontSize: '0.9rem', color: '#cbd5e1', marginBottom: '1rem', lineHeight: 1.5 }}>
            {attractiveness.rationale}
          </p>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '0.75rem', fontSize: '0.8rem' }}>
            <div style={{ background: 'rgba(255, 255, 255, 0.02)', padding: '0.75rem', borderRadius: '4px' }}>
              <span style={{ color: '#94a3b8', display: 'block' }}>Market Size Appeal</span>
              <strong style={{ color: '#ffffff' }}>{attractiveness.market_size_appeal || 'MEDIUM'}</strong>
            </div>
            <div style={{ background: 'rgba(255, 255, 255, 0.02)', padding: '0.75rem', borderRadius: '4px' }}>
              <span style={{ color: '#94a3b8', display: 'block' }}>Competitive Density</span>
              <strong style={{ color: '#ffffff' }}>{attractiveness.competitive_intensity || 'MODERATE'}</strong>
            </div>
            <div style={{ background: 'rgba(255, 255, 255, 0.02)', padding: '0.75rem', borderRadius: '4px' }}>
              <span style={{ color: '#94a3b8', display: 'block' }}>Procurement Friction</span>
              <strong style={{ color: '#ffffff' }}>{attractiveness.procurement_friction || 'MODERATE'}</strong>
            </div>
            <div style={{ background: 'rgba(255, 255, 255, 0.02)', padding: '0.75rem', borderRadius: '4px' }}>
              <span style={{ color: '#94a3b8', display: 'block' }}>Regulatory Readiness</span>
              <strong style={{ color: '#ffffff' }}>{attractiveness.regulatory_readiness || 'MANAGEABLE'}</strong>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
