import React from 'react';
import {
  Briefcase,
  Target,
  MapPin,
  DollarSign,
  Layers,
  HelpCircle,
  Award,
  Sparkles,
  AlertTriangle,
} from 'lucide-react';
import { BusinessAnalysis } from '../types/api';

interface Props {
  analysis?: BusinessAnalysis | null;
}

export const MarketOverview: React.FC<Props> = ({ analysis }) => {
  if (!analysis) return null;

  const classification = analysis.b2b_saas_classification;
  const isOutOfScope = analysis.classification_status === 'OUT_OF_SCOPE' || classification?.classification_status === 'OUT_OF_SCOPE';
  const isAmbiguous = analysis.classification_status === 'AMBIGUOUS' || classification?.classification_status === 'AMBIGUOUS';

  return (
    <div style={{ marginBottom: '2rem' }}>
      {/* Out of Scope Alert */}
      {isOutOfScope && (
        <div
          className="glass-card animate-fade-in"
          style={{
            marginBottom: '1.5rem',
            background: 'rgba(239, 68, 68, 0.1)',
            borderColor: 'rgba(239, 68, 68, 0.4)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'flex-start', gap: '1rem' }}>
            <AlertTriangle size={24} color="#f87171" style={{ flexShrink: 0, marginTop: '0.2rem' }} />
            <div>
              <h3 style={{ fontSize: '1.05rem', fontWeight: 700, color: '#fca5a5', marginBottom: '0.35rem' }}>
                Outside Current Scope — Non-B2B SaaS Business Concept
              </h3>
              <p style={{ fontSize: '0.875rem', color: '#fecaca', lineHeight: 1.5 }}>
                {classification?.reasoning || 'This analyzer strictly evaluates B2B SaaS ventures. The submitted business idea primarily targets individual consumers or operates outside the software-as-a-service model.'}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Ambiguous Alert */}
      {isAmbiguous && (
        <div
          className="glass-card animate-fade-in"
          style={{
            marginBottom: '1.5rem',
            background: 'rgba(245, 158, 11, 0.1)',
            borderColor: 'rgba(245, 158, 11, 0.4)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'flex-start', gap: '1rem' }}>
            <AlertTriangle size={24} color="#fbbf24" style={{ flexShrink: 0, marginTop: '0.2rem' }} />
            <div>
              <h3 style={{ fontSize: '1.05rem', fontWeight: 700, color: '#fcd34d', marginBottom: '0.35rem' }}>
                Ambiguous Business Concept
              </h3>
              <p style={{ fontSize: '0.875rem', color: '#fef08a', lineHeight: 1.5 }}>
                {classification?.reasoning || 'The business concept requires additional details regarding target customer industry, deployment model, or primary enterprise workflow.'}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Main B2B SaaS Classification Card */}
      {classification && (
        <div
          className="glass-card animate-fade-in"
          style={{
            marginBottom: '1.5rem',
            borderTop: '4px solid #6366f1',
            background: 'linear-gradient(180deg, rgba(99, 102, 241, 0.06) 0%, rgba(17, 24, 39, 0.8) 100%)',
          }}
        >
          <div className="section-header" style={{ marginBottom: '1rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <Sparkles size={18} color="#818cf8" />
              <h3 style={{ fontSize: '1.15rem', fontWeight: 700, color: '#ffffff' }}>
                B2B SaaS Business Classification
              </h3>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <span
                style={{
                  background: 'rgba(99, 102, 241, 0.2)',
                  border: '1px solid rgba(99, 102, 241, 0.5)',
                  color: '#c7d2fe',
                  fontSize: '0.75rem',
                  fontWeight: 600,
                  padding: '0.2rem 0.6rem',
                  borderRadius: '9999px',
                }}
              >
                Confidence: {Math.round(classification.category_confidence * 100)}%
              </span>
              <span
                style={{
                  background: 'rgba(16, 185, 129, 0.15)',
                  border: '1px solid rgba(16, 185, 129, 0.4)',
                  color: '#6ee7b7',
                  fontSize: '0.75rem',
                  fontWeight: 600,
                  padding: '0.2rem 0.6rem',
                  borderRadius: '9999px',
                }}
              >
                {classification.sector}
              </span>
            </div>
          </div>

          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
              gap: '0.85rem',
              marginBottom: '1rem',
            }}
          >
            <div style={{ background: 'rgba(255, 255, 255, 0.02)', padding: '0.75rem', borderRadius: '6px' }}>
              <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '0.2rem' }}>
                Category
              </div>
              <div style={{ fontSize: '0.95rem', fontWeight: 700, color: '#e0e7ff' }}>
                {classification.category || 'General B2B SaaS'}
              </div>
            </div>

            <div style={{ background: 'rgba(255, 255, 255, 0.02)', padding: '0.75rem', borderRadius: '6px' }}>
              <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '0.2rem' }}>
                Subcategory
              </div>
              <div style={{ fontSize: '0.95rem', fontWeight: 600, color: '#c7d2fe' }}>
                {classification.subcategory || 'Software Platform'}
              </div>
            </div>

            <div style={{ background: 'rgba(255, 255, 255, 0.02)', padding: '0.75rem', borderRadius: '6px' }}>
              <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '0.2rem' }}>
                Target Segment
              </div>
              <div style={{ fontSize: '0.95rem', fontWeight: 600, color: '#fde047' }}>
                {classification.target_segment || 'SMB / Enterprise'}
              </div>
            </div>

            <div style={{ background: 'rgba(255, 255, 255, 0.02)', padding: '0.75rem', borderRadius: '6px' }}>
              <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '0.2rem' }}>
                Primary Buyer
              </div>
              <div style={{ fontSize: '0.95rem', fontWeight: 600, color: '#6ee7b7' }}>
                {classification.primary_buyer || 'Department Head'}
              </div>
            </div>
          </div>

          {/* Use Cases */}
          {classification.use_cases && classification.use_cases.length > 0 && (
            <div style={{ marginTop: '0.5rem' }}>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '0.35rem', fontWeight: 600 }}>
                KEY ENTERPRISE USE CASES:
              </div>
              <div style={{ display: 'flex', gap: '0.4rem', flexWrap: 'wrap' }}>
                {classification.use_cases.map((uc, i) => (
                  <span
                    key={i}
                    style={{
                      background: 'rgba(99, 102, 241, 0.1)',
                      border: '1px solid rgba(99, 102, 241, 0.3)',
                      color: '#c7d2fe',
                      padding: '0.2rem 0.5rem',
                      borderRadius: '4px',
                      fontSize: '0.75rem',
                    }}
                  >
                    • {uc}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Classification Provenance Note */}
          <div style={{ marginTop: '0.85rem', fontSize: '0.72rem', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
            <span>Provenance: {classification.provenance?.data_type || 'AI_CLASSIFIED'} ({classification.provenance?.source || 'Ollama qwen3:8b'})</span>
          </div>
        </div>
      )}

      {/* Business Concept Details Grid */}
      <div className="glass-card animate-fade-in">
        <div className="section-header">
          <h2 className="section-title">
            <Briefcase size={20} color="#06b6d4" />
            B2B SaaS Business Profile
          </h2>
          <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
            Extracted Business & Market Attributes
          </span>
        </div>

        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))',
            gap: '1rem',
          }}
        >
          <div style={{ background: 'rgba(255, 255, 255, 0.02)', padding: '0.85rem', borderRadius: '6px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '0.25rem' }}>
              <Layers size={13} color="#06b6d4" /> Category & Industry
            </div>
            <div style={{ fontSize: '0.9rem', fontWeight: 600, color: 'var(--text-primary)' }}>
              {analysis.category || analysis.healthcare_saas_category || analysis.industry || 'Not available'}
            </div>
          </div>

          <div style={{ background: 'rgba(255, 255, 255, 0.02)', padding: '0.85rem', borderRadius: '6px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '0.25rem' }}>
              <Briefcase size={13} color="#818cf8" /> Product Offering
            </div>
            <div style={{ fontSize: '0.9rem', fontWeight: 600, color: 'var(--text-primary)' }}>
              {analysis.product || analysis.business_name || 'Not available'}
            </div>
          </div>

          <div style={{ background: 'rgba(255, 255, 255, 0.02)', padding: '0.85rem', borderRadius: '6px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '0.25rem' }}>
              <Target size={13} color="#10b981" /> Target Customer
            </div>
            <div style={{ fontSize: '0.9rem', fontWeight: 600, color: 'var(--text-primary)' }}>
              {analysis.target_customer || analysis.customer_type || 'Organizations'}
            </div>
          </div>

          <div style={{ background: 'rgba(255, 255, 255, 0.02)', padding: '0.85rem', borderRadius: '6px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '0.25rem' }}>
              <MapPin size={13} color="#f59e0b" /> Target Geography
            </div>
            <div style={{ fontSize: '0.9rem', fontWeight: 600, color: 'var(--text-primary)' }}>
              {analysis.target_country || analysis.geography || 'Global'}
            </div>
          </div>

          <div style={{ background: 'rgba(255, 255, 255, 0.02)', padding: '0.85rem', borderRadius: '6px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '0.25rem' }}>
              <DollarSign size={13} color="#ec4899" /> Pricing Model
            </div>
            <div style={{ fontSize: '0.9rem', fontWeight: 600, color: 'var(--text-primary)' }}>
              {analysis.pricing_model || analysis.pricing_basis || 'Not available'}
            </div>
          </div>

          {/* Value Proposition */}
          {(analysis.unique_value_proposition || analysis.value_proposition) && (
            <div style={{ gridColumn: '1 / -1', background: 'rgba(255, 255, 255, 0.02)', padding: '0.85rem', borderRadius: '6px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '0.25rem' }}>
                <Award size={13} color="#34d399" /> Value Proposition
              </div>
              <div style={{ fontSize: '0.875rem', color: 'var(--text-primary)', lineHeight: 1.4 }}>
                {analysis.unique_value_proposition || analysis.value_proposition}
              </div>
            </div>
          )}

          {/* Problem */}
          {(analysis.primary_problem || analysis.customer_problem) && (
            <div style={{ gridColumn: '1 / -1', background: 'rgba(255, 255, 255, 0.02)', padding: '0.85rem', borderRadius: '6px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '0.25rem' }}>
                <HelpCircle size={13} color="#f43f5e" /> Customer Problem Solved
              </div>
              <div style={{ fontSize: '0.875rem', color: 'var(--text-primary)', lineHeight: 1.4 }}>
                {analysis.primary_problem || analysis.customer_problem}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
