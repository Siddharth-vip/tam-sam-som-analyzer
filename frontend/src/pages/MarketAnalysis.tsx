import React, { useState } from 'react';
import { AlertCircle, RotateCcw, Activity, ShieldCheck, CheckCircle2, TrendingUp, AlertTriangle } from 'lucide-react';
import { PipelineRequest, PipelineResult, PipelineProgressEvent } from '../types/api';
import * as apiService from '../services/api';
import { BusinessIdeaForm } from '../components/BusinessIdeaForm';
import { AnalysisProgress } from '../components/AnalysisProgress';
import { MarketOverview } from '../components/MarketOverview';
import { MarketSizeCards } from '../components/MarketSizeCards';
import { MarketFunnel } from '../components/MarketFunnel';
import { MethodComparison } from '../components/MethodComparison';
import { AssumptionsPanel } from '../components/AssumptionsPanel';
import { SourcesPanel } from '../components/SourcesPanel';
import { CalculationTransparency } from '../components/CalculationTransparency';
import { CompetitorPanel } from '../components/CompetitorPanel';
import { RisksPanel } from '../components/RisksPanel';
import { ReportPanel } from '../components/ReportPanel';

export const MarketAnalysisPage: React.FC = () => {
  const [isLoading, setIsLoading] = useState(false);
  const [currentEvent, setCurrentEvent] = useState<PipelineProgressEvent | null>(null);
  const [result, setResult] = useState<PipelineResult | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [missingFields, setMissingFields] = useState<string[]>([]);

  const handleAnalyze = async (request: PipelineRequest) => {
    setIsLoading(true);
    setMissingFields([]);
    setCurrentEvent({
      pipeline_id: 'pending',
      stage: 'received',
      status: 'running',
      message: 'Analyzing Healthcare SaaS requirements and querying market intelligence...',
      progress_percent: 10,
      timestamp: new Date().toISOString(),
    });
    setResult(null);
    setErrorMessage(null);

    try {
      const data = await apiService.analyzeMarket(request);
      
      // Check if backend returned INCOMPLETE_INPUT
      if (data.status === 'INCOMPLETE_INPUT' || (data.missing_fields && data.missing_fields.length > 0)) {
        setMissingFields(data.missing_fields || []);
        setErrorMessage(data.errors?.[0] || 'Additional Healthcare SaaS parameters are required to perform accurate market sizing.');
        setResult(null);
        setCurrentEvent(null);
        return;
      }

      setResult(data);
      setCurrentEvent({
        pipeline_id: data.pipeline_id,
        stage: 'completed',
        status: 'completed',
        message: 'Healthcare SaaS market sizing completed deterministically.',
        progress_percent: 100,
        timestamp: new Date().toISOString(),
      });
    } catch (err: any) {
      console.error('Market analysis execution failed:', err);
      setErrorMessage(
        err.message || 'Healthcare SaaS market analysis could not be completed. Please check your inputs or network connection.'
      );
      setCurrentEvent(null);
    } finally {
      setIsLoading(false);
    }
  };

  const handleReset = () => {
    setResult(null);
    setCurrentEvent(null);
    setErrorMessage(null);
    setMissingFields([]);
    setIsLoading(false);
  };

  const attractiveness = result?.market_attractiveness;

  return (
    <div className="app-container">
      {/* App Header */}
      <header className="app-header no-print">
        <div className="brand-badge" style={{ display: 'inline-flex', alignItems: 'center', gap: '0.4rem' }}>
          <Activity size={14} color="#06b6d4" />
          Healthcare SaaS Market Intelligence Engine
        </div>
        <h1 className="brand-title">
          AI Healthcare SaaS TAM / SAM / SOM Analyzer
        </h1>
        <p className="brand-subtitle">
          Defensible, bottom-up and top-down market sizing for Healthcare SaaS ventures with verified clinical provider counts, regulatory constraints, and unit economics.
        </p>
      </header>

      {/* Input Section */}
      <div className="no-print">
        <BusinessIdeaForm onSubmit={handleAnalyze} isLoading={isLoading} />
      </div>

      {/* Loading Progress State */}
      {isLoading && (
        <div className="no-print">
          <AnalysisProgress currentEvent={currentEvent} isLoading={isLoading} />
        </div>
      )}

      {/* Incomplete Input / Missing Fields Alert */}
      {missingFields.length > 0 && (
        <div
          className="glass-card animate-fade-in no-print"
          style={{
            marginBottom: '2rem',
            background: 'rgba(245, 158, 11, 0.1)',
            borderColor: 'rgba(245, 158, 11, 0.4)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'flex-start', gap: '1rem' }}>
            <AlertTriangle size={24} color="#f59e0b" style={{ flexShrink: 0, marginTop: '0.2rem' }} />
            <div style={{ flex: 1 }}>
              <h3 style={{ fontSize: '1rem', fontWeight: 700, color: '#fbbf24', marginBottom: '0.25rem' }}>
                Incomplete Healthcare SaaS Input
              </h3>
              <p style={{ fontSize: '0.875rem', color: '#fde68a', lineHeight: 1.5, marginBottom: '0.75rem' }}>
                The engine strictly avoids generating fabricated market figures. Please provide the following required parameters:
              </p>
              <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                {missingFields.map((field, idx) => (
                  <span
                    key={idx}
                    style={{
                      background: 'rgba(245, 158, 11, 0.2)',
                      border: '1px solid rgba(245, 158, 11, 0.5)',
                      color: '#fef08a',
                      padding: '0.25rem 0.6rem',
                      borderRadius: '4px',
                      fontSize: '0.8rem',
                      fontFamily: 'var(--font-mono)',
                    }}
                  >
                    {field}
                  </span>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Error Alert */}
      {errorMessage && missingFields.length === 0 && (
        <div
          className="glass-card animate-fade-in no-print"
          style={{
            marginBottom: '2rem',
            background: 'rgba(244, 63, 94, 0.1)',
            borderColor: 'rgba(244, 63, 94, 0.4)',
            display: 'flex',
            alignItems: 'flex-start',
            gap: '1rem',
          }}
        >
          <AlertCircle size={24} color="#f43f5e" style={{ flexShrink: 0, marginTop: '0.2rem' }} />
          <div style={{ flex: 1 }}>
            <h3 style={{ fontSize: '1rem', fontWeight: 700, color: '#fda4af', marginBottom: '0.25rem' }}>
              Execution Note
            </h3>
            <p style={{ fontSize: '0.875rem', color: '#fecdd3', lineHeight: 1.5 }}>
              {errorMessage}
            </p>
          </div>
          <button
            type="button"
            className="btn-secondary"
            onClick={handleReset}
            style={{ fontSize: '0.8rem', padding: '0.35rem 0.75rem', gap: '0.3rem' }}
          >
            <RotateCcw size={13} /> Reset
          </button>
        </div>
      )}

      {/* Analysis Results Display */}
      {result && (
        <div className="animate-fade-in">
          {/* Market Attractiveness Banner */}
          {attractiveness && (
            <div
              className="glass-card"
              style={{
                marginBottom: '2rem',
                borderLeft: `4px solid ${
                  attractiveness.rating === 'HIGH'
                    ? '#10b981'
                    : attractiveness.rating === 'MEDIUM'
                    ? '#f59e0b'
                    : '#f43f5e'
                }`,
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem' }}>
                <div>
                  <span style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                    Market Attractiveness Assessment
                  </span>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginTop: '0.25rem' }}>
                    <span
                      style={{
                        fontSize: '1.25rem',
                        fontWeight: 800,
                        color:
                          attractiveness.rating === 'HIGH'
                            ? '#34d399'
                            : attractiveness.rating === 'MEDIUM'
                            ? '#fbbf24'
                            : '#f87171',
                      }}
                    >
                      {attractiveness.rating} ATTRACTIVENESS
                    </span>
                    <span
                      style={{
                        fontSize: '0.85rem',
                        padding: '0.2rem 0.5rem',
                        borderRadius: '9999px',
                        background: 'rgba(255, 255, 255, 0.05)',
                        border: '1px solid var(--border-subtle)',
                        color: 'var(--text-secondary)',
                      }}
                    >
                      Score: {attractiveness.score}/10
                    </span>
                  </div>
                </div>
                <div style={{ flex: 1, minWidth: '260px' }}>
                  <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', lineHeight: 1.4 }}>
                    {attractiveness.explanation}
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Market Overview */}
          <MarketOverview analysis={result.business_analysis} />

          {/* TAM / SAM / SOM Cards */}
          <MarketSizeCards
            tam={result.tam || result.calculation_report?.top_down_tam}
            sam={result.sam || result.calculation_report?.top_down_sam}
            som={result.som || result.calculation_report?.top_down_som}
            currency={result.calculation_report?.currency}
          />

          {/* Visual Market Funnel */}
          <MarketFunnel
            tam={result.tam || result.calculation_report?.top_down_tam}
            sam={result.sam || result.calculation_report?.top_down_sam}
            som={result.som || result.calculation_report?.top_down_som}
            currency={result.calculation_report?.currency}
          />

          {/* Top-Down vs Bottom-Up Methodology Comparison */}
          {result.calculation_report?.method_comparison && (
            <MethodComparison
              comparison={result.calculation_report.method_comparison}
              currency={result.calculation_report.currency}
            />
          )}

          {/* Calculation Transparency (Auditable steps) */}
          <CalculationTransparency steps={result.calculation_report?.all_steps || []} />

          {/* Assumptions Panel */}
          <AssumptionsPanel assumptions={result.calculation_report?.all_assumptions || []} />

          {/* Sources & Empirical Evidence */}
          <SourcesPanel
            validationResults={result.validation_results}
            discoveredSources={result.discovered_sources}
            fetchedSources={result.fetched_sources}
            rejectedSources={result.rejected_sources}
            researchProvider={result.research_provider}
          />

          {/* Competitive Landscape */}
          <CompetitorPanel competitors={result.competitors} />

          {/* Risks & Warnings */}
          <RisksPanel
            warnings={result.warnings}
            errors={result.errors}
          />

          {/* Exportable Full Report */}
          <ReportPanel result={result} />
        </div>
      )}
    </div>
  );
};
