import React from 'react';
import { Download, FileText, Activity, ShieldCheck, CheckCircle2, TrendingUp, AlertCircle, AlertTriangle } from 'lucide-react';
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
  const somScenarios = result.som_scenarios || result.som?.som_scenarios;
  const attractiveness = result.market_attractiveness;
  const sections20 = result.final_report_sections;

  const isSomUnavailable = !som || som.status === 'insufficient_evidence' || som.estimate === null;
  const isExecutionFailed = result.status === 'failed' || (result.errors && result.errors.length > 0);

  return (
    <div className="glass-card animate-fade-in" style={{ marginBottom: '2rem' }}>
      <div className="section-header">
        <h2 className="section-title">
          <FileText size={20} color="#818cf8" />
          Comprehensive Healthcare SaaS Analysis Report
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
            <span style={{ fontSize: '0.75rem', fontWeight: 700, color: '#06b6d4', letterSpacing: '0.05em', textTransform: 'uppercase' }}>
              HEALTHCARE SAAS MARKET VALUATION & FEASIBILITY REPORT
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
                RESEARCH: {(result.research_provider || 'mock').toUpperCase()}
              </span>
              {attractiveness && (
                <span
                  style={{
                    fontSize: '0.75rem',
                    fontWeight: 700,
                    padding: '0.2rem 0.6rem',
                    borderRadius: '9999px',
                    background:
                      attractiveness.rating === 'HIGH'
                        ? 'rgba(16, 185, 129, 0.2)'
                        : attractiveness.rating === 'MEDIUM'
                        ? 'rgba(245, 158, 11, 0.2)'
                        : 'rgba(239, 68, 68, 0.2)',
                    color:
                      attractiveness.rating === 'HIGH'
                        ? '#34d399'
                        : attractiveness.rating === 'MEDIUM'
                        ? '#fbbf24'
                        : '#f87171',
                    border: '1px solid currentColor',
                  }}
                >
                  ATTRACTIVENESS: {attractiveness.rating} ({attractiveness.score}/10)
                </span>
              )}
            </div>
          </div>
          <h1 style={{ fontSize: '1.6rem', fontWeight: 800, marginTop: '0.35rem', color: '#ffffff' }}>
            {bAnalysis?.business_name || bAnalysis?.product || 'Healthcare SaaS Market Analysis'}
          </h1>
          <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap', fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '0.35rem' }}>
            <span>Category: <strong style={{ color: '#ffffff' }}>{bAnalysis?.healthcare_saas_category || 'Healthcare SaaS'}</strong></span>
            <span>Target Market: <strong style={{ color: '#ffffff' }}>{bAnalysis?.target_country || bAnalysis?.geography || 'India'}</strong></span>
            <span>Run ID: <code>{result.pipeline_id || 'N/A'}</code></span>
            <span>Date: {result.started_at ? new Date(result.started_at).toLocaleDateString() : new Date().toLocaleDateString()}</span>
          </div>

          {/* Non-Medical Disclaimer */}
          <div
            style={{
              marginTop: '0.85rem',
              padding: '0.55rem 0.85rem',
              borderRadius: 'var(--radius-sm)',
              background: 'rgba(6, 182, 212, 0.1)',
              border: '1px solid rgba(6, 182, 212, 0.3)',
              color: '#67e8f9',
              fontSize: '0.78rem',
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
            }}
          >
            <Activity size={15} color="#06b6d4" style={{ flexShrink: 0 }} />
            <span>
              <strong>Healthcare SaaS Market Notice:</strong> This analysis evaluates commercial market sizing, provider adoption, and software economics. It does not constitute medical, diagnostic, or clinical advice.
            </span>
          </div>
        </div>

        {/* 1. Executive Summary */}
        <div style={{ marginBottom: '1.5rem' }}>
          <h3 style={{ fontSize: '1.1rem', fontWeight: 700, color: '#ffffff', marginBottom: '0.5rem' }}>
            1. Executive Summary
          </h3>
          <p style={{ fontSize: '0.9rem', color: 'var(--text-secondary)', lineHeight: 1.6 }}>
            {sections20?.['1. Executive Summary'] || (
              <>
                Market evaluation for Healthcare SaaS venture: <em style={{ color: '#ffffff' }}>"{result.business_idea || 'Healthcare SaaS Idea'}"</em> in <strong style={{ color: '#ffffff' }}>{bAnalysis?.target_country || 'Target Country'}</strong>.
                Deterministic bottom-up sizing established a Total Addressable Market (TAM) of{' '}
                <strong style={{ color: '#818cf8' }}>
                  {tam?.estimate != null ? formatCurrencyValue(tam.estimate, currency, '/yr') : 'Not calculable'}
                </strong>{' '}
                and a Serviceable Addressable Market (SAM) of{' '}
                <strong style={{ color: '#06b6d4' }}>
                  {sam?.estimate != null ? formatCurrencyValue(sam.estimate, currency, '/yr') : 'Not calculable'}
                </strong>
                {sam?.sam_percentage_of_tam != null ? ` (${sam.sam_percentage_of_tam}% of TAM)` : ''}.
                The Serviceable Obtainable Market (SOM) is projected at{' '}
                <strong style={{ color: '#10b981' }}>
                  {som?.estimate != null ? formatCurrencyValue(som.estimate, currency, '/yr') : 'Insufficient data'}
                </strong>
                {som?.som_percentage_of_sam != null ? ` (${som.som_percentage_of_sam}% capture rate)` : ''}.
              </>
            )}
          </p>
        </div>

        {/* 2. Healthcare SaaS Parameters */}
        <div style={{ marginBottom: '1.5rem' }}>
          <h3 style={{ fontSize: '1.1rem', fontWeight: 700, color: '#ffffff', marginBottom: '0.5rem' }}>
            2. Healthcare SaaS Parameters & Customer Profiling
          </h3>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem' }}>
            <tbody>
              <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                <td style={{ padding: '0.5rem 0', color: 'var(--text-muted)', width: '35%' }}>Healthcare SaaS Category</td>
                <td style={{ padding: '0.5rem 0', color: '#ffffff', fontWeight: 600 }}>{bAnalysis?.healthcare_saas_category || 'Healthcare SaaS'}</td>
              </tr>
              <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                <td style={{ padding: '0.5rem 0', color: 'var(--text-muted)' }}>Target Paying Customer</td>
                <td style={{ padding: '0.5rem 0', color: '#ffffff' }}>{bAnalysis?.customer_type ? bAnalysis.customer_type.replace(/_/g, ' ').toUpperCase() : bAnalysis?.target_customer || 'Healthcare Providers'}</td>
              </tr>
              <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                <td style={{ padding: '0.5rem 0', color: 'var(--text-muted)' }}>Geography & Regulatory Scope</td>
                <td style={{ padding: '0.5rem 0', color: '#ffffff' }}>{bAnalysis?.target_country || bAnalysis?.geography || 'India'} | {bAnalysis?.regulatory_market || 'ABDM / NABH / HIPAA Compliant'}</td>
              </tr>
              <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                <td style={{ padding: '0.5rem 0', color: 'var(--text-muted)' }}>Pricing & SaaS Unit Economics</td>
                <td style={{ padding: '0.5rem 0', color: '#ffffff' }}>{bAnalysis?.pricing_basis || 'Subscription'} {bAnalysis?.annual_subscription_price ? `(@ ₹${bAnalysis.annual_subscription_price.toLocaleString()}/yr)` : bAnalysis?.per_facility_price ? `(@ ₹${bAnalysis.per_facility_price.toLocaleString()}/facility/yr)` : ''}</td>
              </tr>
              <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                <td style={{ padding: '0.5rem 0', color: 'var(--text-muted)' }}>EMR / EHR Interoperability</td>
                <td style={{ padding: '0.5rem 0', color: '#ffffff' }}>{bAnalysis?.emr_integration_required ? 'Required (FHIR / HL7 / ABDM M1&M2)' : 'Standalone SaaS'}</td>
              </tr>
              <tr>
                <td style={{ padding: '0.5rem 0', color: 'var(--text-muted)' }}>Primary Healthcare Problem Solved</td>
                <td style={{ padding: '0.5rem 0', color: '#ffffff' }}>{bAnalysis?.primary_problem || bAnalysis?.customer_problem || 'Clinical / Administrative Workflow Optimization'}</td>
              </tr>
            </tbody>
          </table>
        </div>

        {/* 3. Market Sizing Summary Table */}
        <div style={{ marginBottom: '1.5rem' }}>
          <h3 style={{ fontSize: '1.1rem', fontWeight: 700, color: '#ffffff', marginBottom: '0.5rem' }}>
            3. Deterministic Market Sizing (TAM / SAM / SOM)
          </h3>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--border-subtle)', textAlign: 'left', color: 'var(--text-muted)' }}>
                <th style={{ padding: '0.5rem 0' }}>Metric</th>
                <th style={{ padding: '0.5rem 0' }}>Valuation</th>
                <th style={{ padding: '0.5rem 0' }}>Derived Population / Share</th>
                <th style={{ padding: '0.5rem 0' }}>Status</th>
                <th style={{ padding: '0.5rem 0' }}>Confidence</th>
              </tr>
            </thead>
            <tbody>
              <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                <td style={{ padding: '0.6rem 0', fontWeight: 700, color: '#818cf8' }}>TAM (Total Addressable Market)</td>
                <td style={{ padding: '0.6rem 0', color: '#ffffff', fontWeight: 600 }}>
                  {tam?.estimate != null ? formatCurrencyValue(tam.estimate, currency, '/yr') : 'Not calculable'}
                </td>
                <td style={{ padding: '0.6rem 0', color: 'var(--text-secondary)' }}>100% Total Population</td>
                <td style={{ padding: '0.6rem 0' }}>{tam?.status ? String(tam.status).toUpperCase() : 'CALCULATED'}</td>
                <td style={{ padding: '0.6rem 0' }}>{String(tam?.confidence || 'HIGH').toUpperCase()}</td>
              </tr>
              <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                <td style={{ padding: '0.6rem 0', fontWeight: 700, color: '#06b6d4' }}>SAM (Serviceable Addressable Market)</td>
                <td style={{ padding: '0.6rem 0', color: '#ffffff', fontWeight: 600 }}>
                  {sam?.estimate != null ? formatCurrencyValue(sam.estimate, currency, '/yr') : 'Not calculable'}
                </td>
                <td style={{ padding: '0.6rem 0', color: '#38bdf8', fontWeight: 600 }}>
                  {sam?.sam_percentage_of_tam != null ? `${sam.sam_percentage_of_tam}% of TAM` : 'Target Segment'}
                </td>
                <td style={{ padding: '0.6rem 0' }}>{sam?.status ? String(sam.status).toUpperCase() : 'CALCULATED'}</td>
                <td style={{ padding: '0.6rem 0' }}>{String(sam?.confidence || 'HIGH').toUpperCase()}</td>
              </tr>
              <tr>
                <td style={{ padding: '0.6rem 0', fontWeight: 700, color: '#10b981' }}>SOM (Serviceable Obtainable Market)</td>
                <td style={{ padding: '0.6rem 0', color: isSomUnavailable ? '#fbbf24' : '#ffffff', fontWeight: 600 }}>
                  {isSomUnavailable ? 'Insufficient Evidence' : formatCurrencyValue(som?.estimate, currency, '/yr')}
                </td>
                <td style={{ padding: '0.6rem 0', color: '#34d399', fontWeight: 600 }}>
                  {som?.som_percentage_of_sam != null ? `${som.som_percentage_of_sam}% of SAM` : 'Capacity-Derived'}
                </td>
                <td style={{ padding: '0.6rem 0' }}>{som?.status ? String(som.status).toUpperCase() : 'CALCULATED'}</td>
                <td style={{ padding: '0.6rem 0' }}>{String(som?.confidence || 'MEDIUM').toUpperCase()}</td>
              </tr>
            </tbody>
          </table>
        </div>

        {/* 4. SOM Capacity Scenarios */}
        {somScenarios && (
          <div style={{ marginBottom: '1.5rem' }}>
            <h3 style={{ fontSize: '1.1rem', fontWeight: 700, color: '#ffffff', marginBottom: '0.5rem' }}>
              4. Serviceable Obtainable Market (SOM) Capacity Scenarios
            </h3>
            <div className="grid-3" style={{ gap: '1rem' }}>
              <div style={{ background: 'rgba(255,255,255,0.02)', padding: '1rem', borderRadius: 'var(--radius-md)', border: '1px solid rgba(255,255,255,0.06)' }}>
                <span style={{ fontSize: '0.75rem', fontWeight: 700, color: '#94a3b8', textTransform: 'uppercase' }}>Conservative SOM</span>
                <div style={{ fontSize: '1.2rem', fontWeight: 800, color: '#ffffff', marginTop: '0.25rem' }}>
                  {formatCurrencyValue(somScenarios.conservative_som, currency, '/yr')}
                </div>
                <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '0.2rem' }}>
                  Acquires ~{somScenarios.conservative_customers} customers ({somScenarios.conservative_share_pct}% share)
                </div>
              </div>

              <div style={{ background: 'rgba(16,185,129,0.04)', padding: '1rem', borderRadius: 'var(--radius-md)', border: '1px solid rgba(16,185,129,0.3)' }}>
                <span style={{ fontSize: '0.75rem', fontWeight: 700, color: '#34d399', textTransform: 'uppercase' }}>Base SOM (Target)</span>
                <div style={{ fontSize: '1.2rem', fontWeight: 800, color: '#34d399', marginTop: '0.25rem' }}>
                  {formatCurrencyValue(somScenarios.base_som, currency, '/yr')}
                </div>
                <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '0.2rem' }}>
                  Acquires ~{somScenarios.base_customers} customers ({somScenarios.base_share_pct}% share)
                </div>
              </div>

              <div style={{ background: 'rgba(255,255,255,0.02)', padding: '1rem', borderRadius: 'var(--radius-md)', border: '1px solid rgba(255,255,255,0.06)' }}>
                <span style={{ fontSize: '0.75rem', fontWeight: 700, color: '#38bdf8', textTransform: 'uppercase' }}>Optimistic SOM</span>
                <div style={{ fontSize: '1.2rem', fontWeight: 800, color: '#ffffff', marginTop: '0.25rem' }}>
                  {formatCurrencyValue(somScenarios.optimistic_som, currency, '/yr')}
                </div>
                <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '0.2rem' }}>
                  Acquires ~{somScenarios.optimistic_customers} customers ({somScenarios.optimistic_share_pct}% share)
                </div>
              </div>
            </div>
          </div>
        )}

        {/* 5. Empirical Sources & Provenance */}
        <div style={{ marginBottom: '1.5rem' }}>
          <h3 style={{ fontSize: '1.1rem', fontWeight: 700, color: '#ffffff', marginBottom: '0.5rem' }}>
            5. Empirical Evidence & Market Sources
          </h3>
          {sources.length > 0 ? (
            <ul style={{ paddingLeft: '1.25rem', fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
              {sources.map((s, idx) => {
                const metricLabel = String(s?.metric || s?.metric_name || 'Metric').replace(/_/g, ' ');
                return (
                  <li key={idx} style={{ marginBottom: '0.6rem' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
                      <strong style={{ color: '#ffffff' }}>{metricLabel}:</strong>{' '}
                      <span>{s?.source_name || s?.source_url || 'Verified Industry Source'}</span>
                      <span
                        style={{
                          fontSize: '0.7rem',
                          fontWeight: 700,
                          padding: '0.1rem 0.45rem',
                          borderRadius: '4px',
                          background: 'rgba(16, 185, 129, 0.15)',
                          color: '#34d399',
                        }}
                      >
                        {s?.data_type || 'SOURCED'}
                      </span>
                    </div>
                  </li>
                );
              })}
            </ul>
          ) : (
            <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', fontStyle: 'italic', margin: 0 }}>
              Empirical healthcare provider evidence tracked in calculation report.
            </p>
          )}
        </div>

        {/* 6. Strategic Assumptions */}
        {assumptions.length > 0 && (
          <div style={{ marginBottom: '1.5rem' }}>
            <h3 style={{ fontSize: '1.1rem', fontWeight: 700, color: '#ffffff', marginBottom: '0.5rem' }}>
              6. Strategic Assumptions & Operational Caveats
            </h3>
            <ul style={{ paddingLeft: '1.25rem', fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
              {assumptions.map((a, idx) => (
                <li key={idx} style={{ marginBottom: '0.35rem' }}>
                  <strong style={{ color: '#ffffff' }}>{a.metric}:</strong> {a.description || a.rationale}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
};
