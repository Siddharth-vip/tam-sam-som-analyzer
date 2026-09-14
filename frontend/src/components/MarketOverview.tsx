import React from 'react';
import { Briefcase, Target, MapPin, DollarSign, Layers, HelpCircle, Award, CheckCircle } from 'lucide-react';
import { BusinessAnalysis } from '../types/api';

interface Props {
  analysis?: BusinessAnalysis | null;
}

export const MarketOverview: React.FC<Props> = ({ analysis }) => {
  if (!analysis) return null;

  const items = [
    {
      label: 'Industry / Domain',
      value: analysis.industry,
      icon: Briefcase,
      color: '#818cf8',
    },
    {
      label: 'Core Product / Solution',
      value: analysis.product,
      icon: Layers,
      color: '#06b6d4',
    },
    {
      label: 'Target Customer Persona',
      value: analysis.target_customer,
      icon: Target,
      color: '#10b981',
    },
    {
      label: 'Target Geography',
      value: analysis.geography,
      icon: MapPin,
      color: '#f59e0b',
    },
    {
      label: 'Business Model',
      value: analysis.business_model,
      icon: CheckCircle,
      color: '#a855f7',
    },
    {
      label: 'Pricing / Revenue Model',
      value: analysis.pricing_model,
      icon: DollarSign,
      color: '#ec4899',
    },
    {
      label: 'Customer Pain Point',
      value: analysis.customer_problem,
      icon: HelpCircle,
      color: '#f43f5e',
      fullWidth: true,
    },
    {
      label: 'Value Proposition',
      value: analysis.value_proposition,
      icon: Award,
      color: '#34d399',
      fullWidth: true,
    },
  ];

  return (
    <div className="glass-card animate-fade-in" style={{ marginBottom: '2rem' }}>
      <div className="section-header">
        <h2 className="section-title">
          <Briefcase size={20} color="#818cf8" />
          Market & Business Overview
        </h2>
        <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
          Extracted Concept Parameters
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
          const displayVal = item.value ? item.value.trim() : 'Not available';
          const isAvailable = Boolean(item.value && item.value.trim() !== '');

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
                  gap: '0.4rem',
                  fontSize: '0.8rem',
                  color: 'var(--text-muted)',
                  marginBottom: '0.35rem',
                  fontWeight: 600,
                  textTransform: 'uppercase',
                  letterSpacing: '0.03em',
                }}
              >
                <Icon size={14} color={item.color} />
                <span>{item.label}</span>
              </div>
              <div
                style={{
                  fontSize: '0.95rem',
                  color: isAvailable ? 'var(--text-primary)' : 'var(--text-muted)',
                  fontStyle: isAvailable ? 'normal' : 'italic',
                  lineHeight: 1.5,
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
