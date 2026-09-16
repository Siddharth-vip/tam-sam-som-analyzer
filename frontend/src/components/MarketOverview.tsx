import React from 'react';
import { Briefcase, Target, MapPin, DollarSign, Layers, HelpCircle, Award, CheckCircle, Stethoscope, ShieldCheck, Cpu } from 'lucide-react';
import { BusinessAnalysis } from '../types/api';

interface Props {
  analysis?: BusinessAnalysis | null;
}

export const MarketOverview: React.FC<Props> = ({ analysis }) => {
  if (!analysis) return null;

  const items = [
    {
      label: 'Healthcare SaaS Category',
      value: analysis.healthcare_saas_category || analysis.industry || 'Healthcare SaaS',
      icon: Stethoscope,
      color: '#06b6d4',
    },
    {
      label: 'Target Healthcare Customer',
      value: analysis.customer_type ? analysis.customer_type.replace(/_/g, ' ').toUpperCase() : analysis.target_customer,
      icon: Target,
      color: '#10b981',
    },
    {
      label: 'Target Geography & Market',
      value: `${analysis.target_country || analysis.geography || 'Global'}${analysis.target_state_region ? ` (${analysis.target_state_region})` : ''}`,
      icon: MapPin,
      color: '#f59e0b',
    },
    {
      label: 'Pricing Model & Unit Economics',
      value: analysis.pricing_basis
        ? `${analysis.pricing_basis.replace(/_/g, ' ')} ${
            analysis.annual_subscription_price
              ? `(@ ₹${analysis.annual_subscription_price.toLocaleString()}/yr)`
              : analysis.per_facility_price
              ? `(@ ₹${analysis.per_facility_price.toLocaleString()}/facility)`
              : ''
          }`
        : analysis.pricing_model,
      icon: DollarSign,
      color: '#ec4899',
    },
    {
      label: 'Clinical / Administrative Workflow',
      value: analysis.clinical_or_non_clinical ? analysis.clinical_or_non_clinical.toUpperCase() : 'Healthcare Workflow',
      icon: Layers,
      color: '#818cf8',
    },
    {
      label: 'Regulatory & Compliance Framework',
      value: analysis.regulatory_market || 'ABDM / HIPAA / NABH Compliant',
      icon: ShieldCheck,
      color: '#34d399',
    },
    {
      label: 'EMR / EHR Interoperability',
      value: analysis.emr_integration_required ? 'Required (HL7 / FHIR / ABDM M1 & M2)' : 'Standalone SaaS',
      icon: Cpu,
      color: '#a855f7',
    },
    {
      label: 'Core Product / Solution',
      value: analysis.product || analysis.product_description,
      icon: Briefcase,
      color: '#38bdf8',
    },
    {
      label: 'Primary Healthcare Pain Point',
      value: analysis.primary_problem || analysis.customer_problem,
      icon: HelpCircle,
      color: '#f43f5e',
      fullWidth: true,
    },
    {
      label: 'Unique Value Proposition',
      value: analysis.unique_value_proposition || analysis.value_proposition,
      icon: Award,
      color: '#34d399',
      fullWidth: true,
    },
  ];

  return (
    <div className="glass-card animate-fade-in" style={{ marginBottom: '2rem' }}>
      <div className="section-header">
        <h2 className="section-title">
          <Stethoscope size={20} color="#06b6d4" />
          Healthcare SaaS Venture Profile
        </h2>
        <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
          Clinical & Commercial Parameters
        </span>
      </div>

      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
          gap: '1rem',
        }}
      >
        {items.map((item, idx) => {
          const Icon = item.icon;
          const displayVal = item.value ? String(item.value).trim() : 'Not specified';

          return (
            <div
              key={idx}
              style={{
                background: 'rgba(255, 255, 255, 0.02)',
                border: '1px solid rgba(255, 255, 255, 0.05)',
                borderRadius: 'var(--radius-md)',
                padding: '1rem',
                gridColumn: item.fullWidth ? '1 / -1' : undefined,
              }}
            >
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.5rem',
                  marginBottom: '0.35rem',
                  fontSize: '0.75rem',
                  fontWeight: 600,
                  color: 'var(--text-muted)',
                  textTransform: 'uppercase',
                  letterSpacing: '0.05em',
                }}
              >
                <Icon size={14} color={item.color} />
                {item.label}
              </div>
              <div
                style={{
                  fontSize: '0.925rem',
                  color: 'var(--text-primary)',
                  fontWeight: 500,
                  lineHeight: 1.4,
                }}
              >
                {displayVal}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
