import React from 'react';
import { Download, FileText } from 'lucide-react';
import { PipelineResult } from '../types/api';
import { formatCurrencyValue, formatNumberOnly } from '../services/api';

interface Props {
  result: PipelineResult;
}

export const ReportPanel: React.FC<Props> = ({ result }) => {
  const handlePrint = () => {
    window.print();
  };

  const bAnalysis = result.business_analysis;
  const currency = result.calculation_report?.currency || result.tam?.currency || 'INR';
  const tam = result.tam || result.calculation_report?.top_down_tam;
  const sam = result.sam || result.calculation_report?.top_down_sam;
  const som = result.som || result.calculation_report?.top_down_som;
  const methodComp = result.calculation_report?.method_comparison;
  const assumptions = result.calculation_report?.all_assumptions || [];
  const sources = result.validation_results || [];

  const isSomUnavailable = !som || som.status === 'insufficient_evidence' || som.estimate === null;

  const isExecutionFailed = result.status === 'failed' || (result.errors && result.errors.length > 0);

  return (
    <div className="glass-card animate-fade-in" style={{ marginBottom: '2rem' }}>
      <div className="section-header">
        <h2 className="section-title">
          <FileText size={20} color="#818cf8" />
          Complete Market Analysis Report
        </h2>
        <div className="no-print" style={{ display: 'flex', gap: '0.5rem' }}>
          <button
            type="button"
            className="btn-primary"
            onClick={handlePrint}
            style={{ fontSize: '0.85rem', padding: '0.45rem 1rem' }}
          >
            <Download size={15} /> Download / Print Report
          </button>
        </div>
      </div>

      <div
        id="printable-report"
        style={{
          background: 'rgba(0, 0, 0, 0.2)',
          padding: '1.75rem',
          borderRadius: 'var(--radius-md)',
          border: '1px solid var(--border-subtle)',
        }}
      >
        {/* Report Header */}
        <div style={{ borderBottom: '2px solid var(--border-subtle)', paddingBottom: '1rem', marginBottom: '1.5rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '0.5rem' }}>
            <span style={{ fontSize: '0.75rem', fontWeight: 700, color: '#818cf8', letterSpacing: '0.05em', textTransform: 'uppercase' }}>
              CONFIDENTIAL MARKET ASSESSMENT REPORT
            </span>
            <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
              <span
                style={{
                  fontSize: '0.75rem',
                  fontWeight: 700,
                  padding: '0.2rem 0.6rem',
                  borderRadius: '9999px',
                  background: (result.research_provider || 'mock').toLowerCase() === 'live' ? 'rgba(16, 185, 129, 0.2)' : 'rgba(245, 158, 11, 0.2)',
                  color: (result.research_provider || 'mock').toLowerCase() === 'live' ? '#34d399' : '#fbbf24',
                  border: `1px solid ${(result.research_provider || 'mock').toLowerCase() === 'live' ? '#10b981' : '#f59e0b'}`,
                }}
              >
                PROVIDER: {(result.research_provider || 'mock').toUpperCase()}
              </span>
              <span
                style={{
                  fontSize: '0.75rem',
                  fontWeight: 700,
                  padding: '0.2rem 0.6rem',
                  borderRadius: '9999px',
                  background:
                    result.evidence_quality_rating === 'HIGH'
                      ? 'rgba(16, 185, 129, 0.2)'
                      : result.evidence_quality_rating === 'MEDIUM'
                      ? 'rgba(59, 130, 246, 0.2)'
                      : 'rgba(239, 68, 68, 0.2)',
                  color:
                    result.evidence_quality_rating === 'HIGH'
                      ? '#34d399'
                      : result.evidence_quality_rating === 'MEDIUM'
                      ? '#60a5fa'
                      : '#f87171',
                  border: '1px solid currentColor',
                }}
              >
                EVIDENCE QUALITY: {result.evidence_quality_rating || (result.calculation_report?.evidence_quality ? String(result.calculation_report.evidence_quality).toUpperCase() : 'INSUFFICIENT')}
              </span>
            </div>
          </div>
          <h1 style={{ fontSize: '1.6rem', fontWeight: 800, marginTop: '0.35rem', color: '#ffffff' }}>
            {bAnalysis?.product || 'AI Market Sizing Assessment'}
          </h1>
          <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap', fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '0.35rem' }}>
            <span>Pipeline ID: <code>{result.pipeline_id || 'N/A'}</code></span>
            <span>Date: {result.started_at ? new Date(result.started_at).toLocaleDateString() : new Date().toLocaleDateString()}</span>
            <span>Confidence: <strong style={{ color: '#ffffff' }}>{String(result.confidence || 'low').toUpperCase()}</strong></span>
          </div>

          {isExecutionFailed && (
            <div
              style={{
                marginTop: '0.85rem',
                padding: '0.65rem 1rem',
                borderRadius: 'var(--radius-sm)',
                background: 'rgba(239, 68, 68, 0.15)',
                border: '1px solid rgba(239, 68, 68, 0.4)',
                color: '#f87171',
                fontSize: '0.85rem',
                fontWeight: 600,
              }}
            >
              🚨 Analysis Execution Interrupted: The pipeline encountered an error during execution (e.g. LLM service runtime issue). Results below reflect an incomplete analysis state.
            </div>
          )}

          {(result.research_provider || 'mock').toLowerCase() === 'mock' && !isExecutionFailed && (
            <div
              style={{
                marginTop: '0.85rem',
                padding: '0.65rem 1rem',
                borderRadius: 'var(--radius-sm)',
                background: 'rgba(245, 158, 11, 0.15)',
                border: '1px solid rgba(245, 158, 11, 0.4)',
                color: '#fbbf24',
                fontSize: '0.85rem',
                fontWeight: 600,
              }}
            >
              ⚠️ Mock Fixture Notice: These figures are development/test fixtures and should not be used as real-world market estimates.
            </div>
          )}
        </div>

        {/* 1. Executive Summary */}
        <div style={{ marginBottom: '1.5rem' }}>
          <h3 style={{ fontSize: '1.1rem', fontWeight: 700, color: '#ffffff', marginBottom: '0.5rem' }}>
            1. Executive Summary
          </h3>
          <p style={{ fontSize: '0.9rem', color: 'var(--text-secondary)', lineHeight: 1.6 }}>
            This market sizing evaluation assessed the business concept: <em style={{ color: '#ffffff' }}>"{result.business_idea || 'Idea'}"</em>.
            Deterministic analysis yielded a Total Addressable Market (TAM) of{' '}
            <strong style={{ color: '#818cf8' }}>
              {tam?.estimate != null ? formatCurrencyValue(tam.estimate, currency, '/yr') : 'Not calculable'}
            </strong>{' '}
            and a Serviceable Addressable Market (SAM) of{' '}
            <strong style={{ color: '#06b6d4' }}>
              {sam?.estimate != null ? formatCurrencyValue(sam.estimate, currency, '/yr') : 'Not calculable'}
            </strong>
            .{' '}
            {isSomUnavailable ? (
              <span style={{ color: '#fbbf24' }}>
                Serviceable Obtainable Market (SOM) was not calculated due to insufficient empirical evidence for short-term capture rate.
              </span>
            ) : (
              <span>
                The Serviceable Obtainable Market (SOM) is estimated at{' '}
                <strong style={{ color: '#10b981' }}>{formatCurrencyValue(som?.estimate, currency, '/yr')}</strong>.
              </span>
            )}
          </p>
        </div>

        {/* 2. Business Concept Overview */}
        <div style={{ marginBottom: '1.5rem' }}>
          <h3 style={{ fontSize: '1.1rem', fontWeight: 700, color: '#ffffff', marginBottom: '0.5rem' }}>
            2. Business Concept Parameters
          </h3>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem' }}>
            <tbody>
              <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                <td style={{ padding: '0.5rem 0', color: 'var(--text-muted)', width: '35%' }}>Industry / Domain</td>
                <td style={{ padding: '0.5rem 0', color: '#ffffff' }}>{bAnalysis?.industry || 'Not available'}</td>
              </tr>
              <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                <td style={{ padding: '0.5rem 0', color: 'var(--text-muted)' }}>Target Customer</td>
                <td style={{ padding: '0.5rem 0', color: '#ffffff' }}>{bAnalysis?.target_customer || 'Not available'}</td>
              </tr>
              <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                <td style={{ padding: '0.5rem 0', color: 'var(--text-muted)' }}>Geography</td>
                <td style={{ padding: '0.5rem 0', color: '#ffffff' }}>{bAnalysis?.geography || 'Not available'}</td>
              </tr>
              <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                <td style={{ padding: '0.5rem 0', color: 'var(--text-muted)' }}>Business Model</td>
                <td style={{ padding: '0.5rem 0', color: '#ffffff' }}>{bAnalysis?.business_model || 'Not available'}</td>
              </tr>
              <tr>
                <td style={{ padding: '0.5rem 0', color: 'var(--text-muted)' }}>Value Proposition</td>
                <td style={{ padding: '0.5rem 0', color: '#ffffff' }}>{bAnalysis?.value_proposition || 'Not available'}</td>
              </tr>
            </tbody>
          </table>
        </div>

        {/* 3. Market Sizing Summary Table */}
        <div style={{ marginBottom: '1.5rem' }}>
          <h3 style={{ fontSize: '1.1rem', fontWeight: 700, color: '#ffffff', marginBottom: '0.5rem' }}>
            3. Market Sizing Findings (TAM / SAM / SOM)
          </h3>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--border-subtle)', textAlign: 'left', color: 'var(--text-muted)' }}>
                <th style={{ padding: '0.5rem 0' }}>Metric</th>
                <th style={{ padding: '0.5rem 0' }}>Point Estimate</th>
                <th style={{ padding: '0.5rem 0' }}>Status</th>
                <th style={{ padding: '0.5rem 0' }}>Confidence</th>
              </tr>
            </thead>
            <tbody>
              <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                <td style={{ padding: '0.6rem 0', fontWeight: 700, color: '#818cf8' }}>TAM</td>
                <td style={{ padding: '0.6rem 0', color: '#ffffff', fontWeight: 600 }}>
                  {tam?.estimate != null ? formatCurrencyValue(tam.estimate, currency, '/yr') : 'Not calculable'}
                </td>
                <td style={{ padding: '0.6rem 0' }}>
                  {tam?.status ? String(tam.status).toUpperCase() : (tam?.estimate != null ? 'CALCULATED' : 'NOT_CALCULABLE')}
                </td>
                <td style={{ padding: '0.6rem 0' }}>{tam?.estimate != null ? String(tam?.confidence || 'LOW').toUpperCase() : 'N/A'}</td>
              </tr>
              <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                <td style={{ padding: '0.6rem 0', fontWeight: 700, color: '#06b6d4' }}>SAM</td>
                <td style={{ padding: '0.6rem 0', color: '#ffffff', fontWeight: 600 }}>
                  {sam?.estimate != null ? formatCurrencyValue(sam.estimate, currency, '/yr') : 'Not calculable'}
                </td>
                <td style={{ padding: '0.6rem 0' }}>
                  {sam?.status ? String(sam.status).toUpperCase() : (sam?.estimate != null ? 'CALCULATED' : 'NOT_CALCULABLE')}
                </td>
                <td style={{ padding: '0.6rem 0' }}>{sam?.estimate != null ? String(sam?.confidence || 'LOW').toUpperCase() : 'N/A'}</td>
              </tr>
              <tr>
                <td style={{ padding: '0.6rem 0', fontWeight: 700, color: '#10b981' }}>SOM</td>
                <td style={{ padding: '0.6rem 0', color: isSomUnavailable ? '#fbbf24' : '#ffffff', fontWeight: 600 }}>
                  {isSomUnavailable ? 'Insufficient Evidence' : formatCurrencyValue(som?.estimate, currency, '/yr')}
                </td>
                <td style={{ padding: '0.6rem 0' }}>
                  {som?.status ? String(som.status).toUpperCase() : (isSomUnavailable ? 'INSUFFICIENT_EVIDENCE' : 'CALCULATED')}
                </td>
                <td style={{ padding: '0.6rem 0' }}>{isSomUnavailable ? 'N/A' : String(som?.confidence || 'LOW').toUpperCase()}</td>
              </tr>
            </tbody>
          </table>
        </div>

        {/* 4. Evidence-Based Reliability Assessment */}
        {result.calculation_report?.reliability_assessment && (
          <div style={{ marginBottom: '1.5rem', background: 'rgba(255, 255, 255, 0.02)', padding: '1rem', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem', flexWrap: 'wrap', gap: '0.5rem' }}>
              <h3 style={{ fontSize: '1.1rem', fontWeight: 700, color: '#ffffff', margin: 0 }}>
                4. Evidence-Based Estimate Reliability
              </h3>
              <span
                style={{
                  fontSize: '0.75rem',
                  fontWeight: 700,
                  padding: '0.2rem 0.6rem',
                  borderRadius: '9999px',
                  background:
                    result.calculation_report.reliability_assessment.level === 'HIGH'
                      ? 'rgba(16, 185, 129, 0.2)'
                      : result.calculation_report.reliability_assessment.level === 'MEDIUM'
                      ? 'rgba(59, 130, 246, 0.2)'
                      : 'rgba(239, 68, 68, 0.2)',
                  color:
                    result.calculation_report.reliability_assessment.level === 'HIGH'
                      ? '#34d399'
                      : result.calculation_report.reliability_assessment.level === 'MEDIUM'
                      ? '#60a5fa'
                      : '#f87171',
                  border: '1px solid currentColor',
                }}
              >
                RELIABILITY: {result.calculation_report.reliability_assessment.level}
              </span>
            </div>
            <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', lineHeight: 1.5, marginBottom: '0.75rem' }}>
              {result.calculation_report.reliability_assessment.reason}
            </p>
            <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              <span>Evidence: <strong style={{ color: '#ffffff' }}>{result.calculation_report.reliability_assessment.evidence_strength}</strong></span>
              <span>Assumption Risk: <strong style={{ color: '#ffffff' }}>{result.calculation_report.reliability_assessment.assumption_risk}</strong></span>
              <span>Freshness: <strong style={{ color: '#ffffff' }}>{result.calculation_report.reliability_assessment.freshness}</strong></span>
              <span>Agreement: <strong style={{ color: '#ffffff' }}>{result.calculation_report.reliability_assessment.methodology_agreement}</strong></span>
              {result.calculation_report.reliability_assessment.double_counting_risk && (
                <span style={{ color: '#f87171', fontWeight: 600 }}>⚠️ Double Counting Risk</span>
              )}
            </div>
          </div>
        )}

        {/* 5. Uncertainty Scenarios (Low / Base / High) */}
        {result.calculation_report?.uncertainty_analysis && (
          <div style={{ marginBottom: '1.5rem' }}>
            <h3 style={{ fontSize: '1.1rem', fontWeight: 700, color: '#ffffff', marginBottom: '0.5rem' }}>
              5. Deterministic Uncertainty Scenarios
            </h3>
            {result.calculation_report.uncertainty_analysis.status === 'AVAILABLE' ? (
              <div>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem', marginBottom: '0.5rem' }}>
                  <thead>
                    <tr style={{ borderBottom: '1px solid var(--border-subtle)', textAlign: 'left', color: 'var(--text-muted)' }}>
                      <th style={{ padding: '0.4rem 0' }}>Metric</th>
                      <th style={{ padding: '0.4rem 0' }}>Low Estimate</th>
                      <th style={{ padding: '0.4rem 0' }}>Base Estimate</th>
                      <th style={{ padding: '0.4rem 0' }}>High Estimate</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.calculation_report.uncertainty_analysis.tam_scenario && (
                      <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                        <td style={{ padding: '0.5rem 0', fontWeight: 700, color: '#818cf8' }}>TAM</td>
                        <td style={{ padding: '0.5rem 0', color: '#94a3b8' }}>{formatCurrencyValue(result.calculation_report.uncertainty_analysis.tam_scenario.low, currency)}</td>
                        <td style={{ padding: '0.5rem 0', color: '#ffffff', fontWeight: 600 }}>{formatCurrencyValue(result.calculation_report.uncertainty_analysis.tam_scenario.base, currency)}</td>
                        <td style={{ padding: '0.5rem 0', color: '#94a3b8' }}>{formatCurrencyValue(result.calculation_report.uncertainty_analysis.tam_scenario.high, currency)}</td>
                      </tr>
                    )}
                    {result.calculation_report.uncertainty_analysis.sam_scenario && (
                      <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                        <td style={{ padding: '0.5rem 0', fontWeight: 700, color: '#06b6d4' }}>SAM</td>
                        <td style={{ padding: '0.5rem 0', color: '#94a3b8' }}>{formatCurrencyValue(result.calculation_report.uncertainty_analysis.sam_scenario.low, currency)}</td>
                        <td style={{ padding: '0.5rem 0', color: '#ffffff', fontWeight: 600 }}>{formatCurrencyValue(result.calculation_report.uncertainty_analysis.sam_scenario.base, currency)}</td>
                        <td style={{ padding: '0.5rem 0', color: '#94a3b8' }}>{formatCurrencyValue(result.calculation_report.uncertainty_analysis.sam_scenario.high, currency)}</td>
                      </tr>
                    )}
                    {result.calculation_report.uncertainty_analysis.som_scenario && (
                      <tr>
                        <td style={{ padding: '0.5rem 0', fontWeight: 700, color: '#10b981' }}>SOM</td>
                        <td style={{ padding: '0.5rem 0', color: '#94a3b8' }}>{formatCurrencyValue(result.calculation_report.uncertainty_analysis.som_scenario.low, currency)}</td>
                        <td style={{ padding: '0.5rem 0', color: '#ffffff', fontWeight: 600 }}>{formatCurrencyValue(result.calculation_report.uncertainty_analysis.som_scenario.base, currency)}</td>
                        <td style={{ padding: '0.5rem 0', color: '#94a3b8' }}>{formatCurrencyValue(result.calculation_report.uncertainty_analysis.som_scenario.high, currency)}</td>
                      </tr>
                    )}
                  </tbody>
                </table>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontStyle: 'italic' }}>
                  Basis: {result.calculation_report.uncertainty_analysis.basis}
                </div>
              </div>
            ) : (
              <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', fontStyle: 'italic' }}>
                Uncertainty range unavailable — insufficient empirical range evidence. Point estimates only.
              </p>
            )}
          </div>
        )}

        {/* 6. Deterministic Sensitivity Analysis */}
        {result.calculation_report?.sensitivity_analysis && result.calculation_report.sensitivity_analysis.length > 0 && (
          <div style={{ marginBottom: '1.5rem' }}>
            <h3 style={{ fontSize: '1.1rem', fontWeight: 700, color: '#ffffff', marginBottom: '0.5rem' }}>
              6. Deterministic Sensitivity Analysis
            </h3>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--border-subtle)', textAlign: 'left', color: 'var(--text-muted)' }}>
                  <th style={{ padding: '0.4rem 0' }}>Driver Parameter</th>
                  <th style={{ padding: '0.4rem 0' }}>Base Value</th>
                  <th style={{ padding: '0.4rem 0' }}>Impact Level</th>
                  <th style={{ padding: '0.4rem 0' }}>Elasticity</th>
                </tr>
              </thead>
              <tbody>
                {result.calculation_report.sensitivity_analysis.map((s, idx) => (
                  <tr key={idx} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                    <td style={{ padding: '0.45rem 0', color: '#ffffff', fontWeight: 600 }}>
                      {String(s.parameter).replace(/_/g, ' ')}
                    </td>
                    <td style={{ padding: '0.45rem 0', color: 'var(--text-secondary)' }}>
                      {formatNumberOnly(s.base_value)} {s.unit}
                    </td>
                    <td style={{ padding: '0.45rem 0' }}>
                      <span
                        style={{
                          fontSize: '0.7rem',
                          fontWeight: 700,
                          padding: '0.1rem 0.4rem',
                          borderRadius: '4px',
                          background:
                            s.impact === 'HIGH'
                              ? 'rgba(239, 68, 68, 0.2)'
                              : s.impact === 'MEDIUM'
                              ? 'rgba(245, 158, 11, 0.2)'
                              : 'rgba(59, 130, 246, 0.2)',
                          color:
                            s.impact === 'HIGH'
                              ? '#f87171'
                              : s.impact === 'MEDIUM'
                              ? '#fbbf24'
                              : '#60a5fa',
                        }}
                      >
                        {s.impact}
                      </span>
                    </td>
                    <td style={{ padding: '0.45rem 0', color: 'var(--text-muted)' }}>
                      {s.elasticity.toFixed(1)}x
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* 7. Methodology Triangulation */}
        {methodComp && (
          <div style={{ marginBottom: '1.5rem' }}>
            <h3 style={{ fontSize: '1.1rem', fontWeight: 700, color: '#ffffff', marginBottom: '0.5rem' }}>
              7. Methodology Triangulation & Cross-Validation
            </h3>
            <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', lineHeight: 1.5, marginBottom: '0.5rem' }}>
              {methodComp.explanation || 'Methodology cross-comparison conducted.'}
            </p>
            <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
              Top-Down TAM: <strong>{formatCurrencyValue(methodComp.top_down_tam, currency)}</strong> | Bottom-Up TAM:{' '}
              <strong>{formatCurrencyValue(methodComp.bottom_up_tam, currency)}</strong> | Divergence Severity:{' '}
              <strong style={{ color: '#ffffff' }}>{String(methodComp.divergence_severity || 'LOW').toUpperCase()}</strong>
            </div>
          </div>
        )}

        {/* 8. Modeling Assumptions */}
        {assumptions.length > 0 && (
          <div style={{ marginBottom: '1.5rem' }}>
            <h3 style={{ fontSize: '1.1rem', fontWeight: 700, color: '#ffffff', marginBottom: '0.5rem' }}>
              8. Modeling Assumptions
            </h3>
            <ul style={{ paddingLeft: '1.25rem', fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
              {assumptions.map((a, idx) => (
                <li key={idx} style={{ marginBottom: '0.35rem' }}>
                  <strong style={{ color: '#ffffff' }}>{String(a?.name || 'Assumption').replace(/_/g, ' ')}:</strong>{' '}
                  {formatNumberOnly(a?.value)} {a?.unit || ''} —{' '}
                  <span style={{ fontStyle: 'italic' }}>{a?.justification || 'Assumption used for estimation'}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* 9. Empirical Evidence & Sources */}
        <div style={{ marginBottom: '1.5rem' }}>
          <h3 style={{ fontSize: '1.1rem', fontWeight: 700, color: '#ffffff', marginBottom: '0.5rem' }}>
            9. Empirical Evidence & Sources
          </h3>
          {sources.length > 0 ? (
            <ul style={{ paddingLeft: '1.25rem', fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
              {sources.map((s, idx) => {
                const metricLabel = String(s?.metric || s?.metric_name || 'Metric').replace(/_/g, ' ');
                const tierStr = (s?.source_quality_tier || s?.provenance?.source_quality_tier || '').toLowerCase();
                let tierLabel = 'Tier 4: General/Unverified';
                let tierColor = '#9ca3af';
                let tierBg = 'rgba(156, 163, 175, 0.15)';
                if (tierStr.includes('tier_1')) {
                  tierLabel = 'Tier 1: Official/Govt';
                  tierColor = '#34d399';
                  tierBg = 'rgba(16, 185, 129, 0.15)';
                } else if (tierStr.includes('tier_2')) {
                  tierLabel = 'Tier 2: Academic/Trade';
                  tierColor = '#60a5fa';
                  tierBg = 'rgba(59, 130, 246, 0.15)';
                } else if (tierStr.includes('tier_3')) {
                  tierLabel = 'Tier 3: Analyst/Press';
                  tierColor = '#a78bfa';
                  tierBg = 'rgba(139, 92, 246, 0.15)';
                }

                return (
                  <li key={idx} style={{ marginBottom: '0.6rem' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
                      <strong style={{ color: '#ffffff' }}>{metricLabel}:</strong>{' '}
                      <span>{s?.source_name || s?.source_url || 'Unknown Source'}</span>
                      <span
                        style={{
                          fontSize: '0.7rem',
                          fontWeight: 700,
                          padding: '0.1rem 0.45rem',
                          borderRadius: '4px',
                          background: tierBg,
                          color: tierColor,
                        }}
                      >
                        {tierLabel}
                      </span>
                      <span
                        style={{
                          fontSize: '0.7rem',
                          fontWeight: 600,
                          padding: '0.1rem 0.45rem',
                          borderRadius: '4px',
                          background: 'rgba(255, 255, 255, 0.05)',
                          color: '#e2e8f0',
                        }}
                      >
                        {s?.lifecycle_stage || 'DISCOVERED'}
                      </span>
                      {s?.is_syndicated_copy && (
                        <span
                          style={{
                            fontSize: '0.7rem',
                            fontWeight: 600,
                            padding: '0.1rem 0.45rem',
                            borderRadius: '4px',
                            background: 'rgba(245, 158, 11, 0.15)',
                            color: '#fbbf24',
                          }}
                        >
                          Syndicated Copy
                        </span>
                      )}
                    </div>
                    {s?.source_context && (
                      <div style={{ marginTop: '0.2rem', fontStyle: 'italic', color: 'var(--text-muted)' }}>
                        "{s.source_context}"
                      </div>
                    )}
                  </li>
                );
              })}
            </ul>
          ) : (
            <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', fontStyle: 'italic', margin: 0 }}>
              {isExecutionFailed
                ? 'Evidence discovery was not completed because upstream business analysis encountered an error.'
                : 'No external empirical evidence sources were retrieved.'}
            </p>
          )}
        </div>

        {/* 10. Pipeline Diagnostics & Errors */}
        {(result.errors || []).length > 0 && (
          <div style={{ marginBottom: '1.5rem', background: 'rgba(239, 68, 68, 0.1)', padding: '1rem', borderRadius: 'var(--radius-md)', border: '1px solid rgba(239, 68, 68, 0.3)' }}>
            <h3 style={{ fontSize: '1.1rem', fontWeight: 700, color: '#f87171', marginBottom: '0.5rem' }}>
              10. Pipeline Execution Diagnostics & Errors
            </h3>
            <ul style={{ paddingLeft: '1.25rem', fontSize: '0.85rem', color: '#fca5a5' }}>
              {(result.errors || []).map((e, idx) => (
                <li key={idx} style={{ marginBottom: '0.25rem' }}>{e}</li>
              ))}
            </ul>
          </div>
        )}

        {/* 11. Warnings & Strategic Caveats */}
        {(result.warnings || []).length > 0 && (
          <div>
            <h3 style={{ fontSize: '1.1rem', fontWeight: 700, color: '#fbbf24', marginBottom: '0.5rem' }}>
              {(result.errors || []).length > 0 ? '11.' : '10.'} Warnings & Strategic Caveats
            </h3>
            <ul style={{ paddingLeft: '1.25rem', fontSize: '0.85rem', color: '#fcd34d' }}>
              {(result.warnings || []).map((w, idx) => (
                <li key={idx} style={{ marginBottom: '0.25rem' }}>{w}</li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
};
