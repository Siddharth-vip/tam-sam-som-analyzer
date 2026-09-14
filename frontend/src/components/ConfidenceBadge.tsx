import React from 'react';
import { ShieldCheck, ShieldAlert, Shield } from 'lucide-react';

interface Props {
  confidence?: string | null;
  label?: string;
}

export const ConfidenceBadge: React.FC<Props> = ({ confidence, label }) => {
  const level = (confidence || 'low').toLowerCase();

  let badgeClass = 'badge-low';
  let Icon = ShieldAlert;
  let text = 'LOW';

  if (level === 'very_high' || level === 'very high') {
    badgeClass = 'badge-high';
    Icon = ShieldCheck;
    text = 'VERY HIGH';
  } else if (level === 'high') {
    badgeClass = 'badge-high';
    Icon = ShieldCheck;
    text = 'HIGH';
  } else if (level === 'medium') {
    badgeClass = 'badge-medium';
    Icon = Shield;
    text = 'MEDIUM';
  } else {
    badgeClass = 'badge-low';
    Icon = ShieldAlert;
    text = 'LOW';
  }

  return (
    <span className={`badge ${badgeClass}`} title={`Confidence: ${text}`}>
      <Icon size={13} />
      {label ? `${label}: ` : ''}{text}
    </span>
  );
};
