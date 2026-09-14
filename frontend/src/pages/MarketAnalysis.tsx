import React, { useState } from 'react';
import { AlertCircle, RotateCcw } from 'lucide-react';
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

  const handleAnalyze = async (request: PipelineRequest) => {
    setIsLoading(true);
    setCurrentEvent({
      pipeline_id: 'pending',
      stage: 'received',
      status: 'running',
      message: 'Initializing research pipeline and semantic models...',
      progress_percent: 5,
      timestamp: new Date().toISOString(),
    });
    setResult(null);
    setErrorMessage(null);

    try {
      // Use direct pipeline analyze endpoint for dependable execution
      const data = await apiService.analyzeMarket(request);
      setResult(data);
      setCurrentEvent({
        pipeline_id: data.pipeline_id,
        stage: 'completed',
        status: 'completed',
        message: 'Market analysis and triangulation completed successfully.',
        progress_percent: 100,
        timestamp: new Date().toISOString(),
      });
    } catch (err: any) {
      console.error('Market analysis execution failed:', err);
      setErrorMessage(
        err.message || 'Market analysis could not be completed. Please check network connection or try again.'
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
    setIsLoading(false);
  };

  return (
    <div className="app-container">
      {/* App Header */}
      <header className="app-header no-print">
        <div className="brand-badge">
          Deterministic Market Intelligence Engine
        </div>
        <h1 className="brand-title">
          AI TAM / SAM / SOM Analyzer
        </h1>
        <p className="brand-subtitle">
          Transform unstructured business ideas into defensible, evidence-backed market valuations using multi-source web discovery and verifiable unit economics.
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

      {/* Error Alert */}
      {errorMessage && (
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
              Analysis Execution Note
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
