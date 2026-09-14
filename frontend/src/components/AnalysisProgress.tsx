import React from 'react';
import { CheckCircle2, Circle, Loader2 } from 'lucide-react';
import { PipelineProgressEvent, PipelineStage } from '../types/api';

interface Props {
  currentEvent?: PipelineProgressEvent | null;
  isLoading: boolean;
}

const STAGES: { key: PipelineStage; label: string }[] = [
  { key: 'business_analysis', label: 'Business Analysis' },
  { key: 'discovery', label: 'Discovering Evidence' },
  { key: 'fetching', label: 'Fetching Sources' },
  { key: 'extraction', label: 'Extracting Evidence' },
  { key: 'validation', label: 'Validating Evidence' },
  { key: 'triangulation', label: 'Triangulating Evidence' },
  { key: 'calculation', label: 'Calculating Market' },
  { key: 'completed', label: 'Completed' },
];

export const AnalysisProgress: React.FC<Props> = ({ currentEvent, isLoading }) => {
  if (!isLoading && !currentEvent) return null;

  const currentStage = currentEvent?.stage || 'business_analysis';
  const currentPercent = currentEvent?.progress_percent ?? 15;
  const currentMessage = currentEvent?.message || 'Analyzing business concept and market semantics...';

  const getStageStatus = (stageKey: PipelineStage) => {
    const stageOrder: PipelineStage[] = [
      'received',
      'business_analysis',
      'query_generation',
      'discovery',
      'fetching',
      'extraction',
      'validation',
      'triangulation',
      'calculation',
      'completed',
    ];

    const currentIndex = stageOrder.indexOf(currentStage);
    const thisIndex = stageOrder.indexOf(stageKey);

    if (thisIndex < currentIndex) return 'completed';
    if (thisIndex === currentIndex) return 'active';
    return 'pending';
  };

  return (
    <div className="glass-card animate-fade-in" style={{ marginBottom: '2rem', borderColor: 'rgba(99, 102, 241, 0.4)' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
          <Loader2 className="pulse-glow" size={20} color="#818cf8" style={{ animation: 'spin 2s linear infinite' }} />
          <h3 style={{ fontSize: '1.05rem', fontWeight: 600 }}>Market Sizing Pipeline in Progress</h3>
        </div>
        <span style={{ fontSize: '0.9rem', fontWeight: 700, color: '#818cf8', fontFamily: 'var(--font-mono)' }}>
          {currentPercent}%
        </span>
      </div>

      {/* Progress Bar */}
      <div
        style={{
          width: '100%',
          height: '6px',
          background: 'rgba(255, 255, 255, 0.08)',
          borderRadius: 'var(--radius-full)',
          overflow: 'hidden',
          marginBottom: '1.25rem',
        }}
      >
        <div
          style={{
            width: `${Math.max(5, currentPercent)}%`,
            height: '100%',
            background: 'linear-gradient(90deg, #6366f1 0%, #06b6d4 100%)',
            transition: 'width 0.4s ease',
            borderRadius: 'var(--radius-full)',
          }}
        />
      </div>

      <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', marginBottom: '1.25rem', fontStyle: 'italic' }}>
        {currentMessage}
      </p>

      {/* Stage Indicators */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))',
          gap: '0.75rem',
        }}
      >
        {STAGES.map((s) => {
          const status = getStageStatus(s.key);
          const isDone = status === 'completed';
          const isActive = status === 'active';

          return (
            <div
              key={s.key}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.4rem',
                fontSize: '0.8rem',
                color: isDone ? '#34d399' : isActive ? '#a5b4fc' : 'var(--text-muted)',
                fontWeight: isActive ? 600 : 400,
              }}
            >
              {isDone ? (
                <CheckCircle2 size={15} color="#34d399" />
              ) : isActive ? (
                <Loader2 size={15} color="#818cf8" style={{ animation: 'spin 1.5s linear infinite' }} />
              ) : (
                <Circle size={15} color="rgba(255,255,255,0.2)" />
              )}
              <span>{s.label}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
};
