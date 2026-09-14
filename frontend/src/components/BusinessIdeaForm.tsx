import React, { useState } from 'react';
import { Sparkles, Globe, Calendar, ArrowRight, Lightbulb } from 'lucide-react';
import { PipelineRequest } from '../types/api';

interface Props {
  onSubmit: (request: PipelineRequest) => void;
  isLoading: boolean;
}

const PRESET_IDEAS = [
  {
    title: 'EdTech / India',
    idea: 'I want to build an affordable online programming platform for college students in India.',
    geography: 'India',
    year: 2024,
  },
  {
    title: 'Food Delivery / Chennai',
    idea: 'I want to start a healthy food delivery service for college students in Chennai.',
    geography: 'Chennai, India',
    year: 2024,
  },
  {
    title: 'FinTech / SaaS / India',
    idea: 'I want to build a SaaS accounting platform for small businesses in India.',
    geography: 'India',
    year: 2024,
  },
];

export const BusinessIdeaForm: React.FC<Props> = ({ onSubmit, isLoading }) => {
  const [businessIdea, setBusinessIdea] = useState('');
  const [geography, setGeography] = useState('');
  const [year, setYear] = useState<string>('');
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = businessIdea.trim();
    if (!trimmed) {
      setError('Please enter your business idea to proceed.');
      return;
    }
    if (trimmed.length < 5) {
      setError('Please describe your business idea in at least 5 characters.');
      return;
    }

    setError(null);
    const parsedYear = year ? parseInt(year, 10) : undefined;

    onSubmit({
      business_idea: trimmed,
      preferred_geography: geography.trim() || undefined,
      preferred_year: !isNaN(Number(parsedYear)) && parsedYear ? parsedYear : undefined,
      max_sources: 5,
      enable_calculation: true,
    });
  };

  const selectPreset = (preset: typeof PRESET_IDEAS[0]) => {
    setBusinessIdea(preset.idea);
    setGeography(preset.geography);
    setYear(preset.year.toString());
    setError(null);
  };

  return (
    <div className="glass-card" style={{ marginBottom: '2rem' }}>
      <div className="section-header">
        <h2 className="section-title">
          <Sparkles size={20} color="#818cf8" />
          Enter Your Business Idea
        </h2>
        <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
          Step 1: Define Target Concept
        </span>
      </div>

      <form onSubmit={handleSubmit}>
        <div className="form-group">
          <label htmlFor="business-idea-input" className="form-label">
            Describe what you want to build & target audience:
          </label>
          <textarea
            id="business-idea-input"
            className="form-textarea"
            placeholder="e.g. I want to build an affordable online programming platform for college students in India..."
            value={businessIdea}
            onChange={(e) => {
              setBusinessIdea(e.target.value);
              if (error) setError(null);
            }}
            disabled={isLoading}
            rows={3}
            required
          />
          {error && (
            <p style={{ color: 'var(--accent-rose)', fontSize: '0.85rem', marginTop: '0.4rem' }}>
              {error}
            </p>
          )}
        </div>

        <div className="grid-2" style={{ marginBottom: '1.25rem' }}>
          <div className="form-group" style={{ marginBottom: 0 }}>
            <label htmlFor="geography-input" className="form-label" style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
              <Globe size={14} color="#38bdf8" /> Target Geography (Optional):
            </label>
            <input
              id="geography-input"
              type="text"
              className="form-input"
              placeholder="e.g. India, US, Global, Chennai"
              value={geography}
              onChange={(e) => setGeography(e.target.value)}
              disabled={isLoading}
            />
          </div>

          <div className="form-group" style={{ marginBottom: 0 }}>
            <label htmlFor="year-input" className="form-label" style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
              <Calendar size={14} color="#34d399" /> Target Reference Year (Optional):
            </label>
            <input
              id="year-input"
              type="number"
              className="form-input"
              placeholder="e.g. 2024"
              value={year}
              onChange={(e) => setYear(e.target.value)}
              disabled={isLoading}
              min="2020"
              max="2035"
            />
          </div>
        </div>

        {/* Quick Example Presets */}
        <div style={{ marginBottom: '1.5rem' }}>
          <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '0.35rem', marginBottom: '0.5rem' }}>
            <Lightbulb size={13} color="#f59e0b" /> Try one of these real-world business scenarios:
          </span>
          <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
            {PRESET_IDEAS.map((preset, idx) => (
              <button
                key={idx}
                type="button"
                className="btn-secondary"
                style={{ fontSize: '0.8rem', padding: '0.35rem 0.75rem' }}
                onClick={() => selectPreset(preset)}
                disabled={isLoading}
              >
                {preset.title}
              </button>
            ))}
          </div>
        </div>

        <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
          <button
            id="analyze-market-btn"
            type="submit"
            className="btn-primary"
            disabled={isLoading || !businessIdea.trim()}
          >
            {isLoading ? (
              <>
                <span className="pulse-glow">Analyzing Market...</span>
              </>
            ) : (
              <>
                Analyze Market <ArrowRight size={18} />
              </>
            )}
          </button>
        </div>
      </form>
    </div>
  );
};
