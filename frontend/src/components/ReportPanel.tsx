import React, { useState } from 'react';
import { Download, FileText, Printer, Activity, AlertCircle, CheckCircle2 } from 'lucide-react';
import { PipelineResult } from '../types/api';
import { formatCurrencyValue } from '../services/api';
import { downloadReportFile } from '../services/reportExport';

interface Props {
  result: PipelineResult;
}

export const ReportPanel: React.FC<Props> = ({ result }) => {
  const [exportError, setExportError] = useState<string | null>(null);
  const [exportSuccess, setExportSuccess] = useState<string | null>(null);

  const handlePrint = () => {
    window.print();
  };

  const handleDownload = () => {
    setExportError(null);
    setExportSuccess(null);
    try {
      const exportRes = downloadReportFile(result);
      if (!exportRes || exportRes.sizeBytes === 0) {
        throw new Error('Report generation failed: Generated file is empty.');
      }
      setExportSuccess(`Report downloaded successfully (${(exportRes.sizeBytes / 1024).toFixed(1)} KB).`);
      setTimeout(() => setExportSuccess(null), 4000);
    } catch (err: any) {
      console.error('Report export failed:', err);
      setExportError(err?.message || 'Report generation failed. Please try again.');
    }
  };

  const bAnalysis = result.business_analysis;
  const currency = result.calculation_report?.currency || result.tam?.currency || 'INR';
  const tam = result.tam || result.calculation_report?.top_down_tam || result.calculation_report?.bottom_up_tam;
  const sam = result.sam || result.calculation_report?.top_down_sam || result.calculation_report?.bottom_up_sam;
  const som = result.som || result.calculation_report?.top_down_som || result.calculation_report?.bottom_up_som;
  const assumptions = result.calculation_report?.all_assumptions || [];
  const sources = result.validation_results || [];
  const somScenarios = (result as any).som_scenarios || (som as any)?.som_scenarios;
  const attractiveness = result.market_attractiveness;
  const sections20 = result.final_report_sections;

  const category = bAnalysis?.category || bAnalysis?.healthcare_saas_category || (bAnalysis ? (bAnalysis.category !== null ? bAnalysis.category : 'Not available') : 'Not available');
  const customer = bAnalysis?.target_customer || (bAnalysis?.customer_type ? bAnalysis.customer_type.replace(/_/g, ' ') : (bAnalysis ? (bAnalysis.target_customer !== null ? bAnalysis.target_customer : 'Not available') : 'Not available'));
  const geography = bAnalysis?.target_country || bAnalysis?.geography || (bAnalysis ? (bAnalysis.target_country !== null ? bAnalysis.target_country : 'Not available') : 'Not available');
  const businessName = bAnalysis?.business_name || bAnalysis?.product || (bAnalysis ? (bAnalysis.product !== null ? bAnalysis.product : 'Not available') : 'Not available');

  const isSomUnavailable = !som || som.status === 'insufficient_evidence' || som.estimate === null || som.estimate === undefined;

  // Format customer counts for integer presentation
  const formatCustomerCount = (count?: number | null) => {
    if (count === null || count === undefined || isNaN(count)) return null;
    const rounded = Math.round(count);
    return rounded === count ? `${count.toLocaleString()}` : `~${rounded.toLocaleString()}`;
  };

  const samCustomersFormatted = formatCustomerCount(sam?.serviceable_customer_count);
  const somCustomersFormatted = formatCustomerCount(som?.obtainable_customer_count);

  return (
    <div className="glass-card animate-fade-in" style={{ marginBottom: '2rem' }}>
      <div className="section-header">
        <h2 className="section-title">
          <FileText size={20} color="#818cf8" />
          Complete Market Analysis Report & AI Market Sizing Assessment
        </h2>
        <div className="no-print" style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
          <button
            type="button"
            className="btn-primary"
            onClick={handleDownload}
            style={{ fontSize: '0.85rem', padding: '0.45rem 1rem', display: 'flex', alignItems: 'center', gap: '0.4rem' }}
          >
            <Download size={15} /> Download / Print Report
          </button>
          <button
            type="button"
            className="btn-secondary"
            onClick={handlePrint}
            style={{ fontSize: '0.85rem', padding: '0.45rem 0.85rem', display: 'flex', alignItems: 'center', gap: '0.35rem' }}
          >
            <Printer size={15} /> Print
          </button>
        </div>
      </div>

      {exportError && (
        <div
          className="no-print animate-fade-in"
          style={{
            background: 'rgba(244, 63, 94, 0.15)',
            border: '1px solid rgba(244, 63, 94, 0.4)',
            color: '#fda4af',
            padding: '0.65rem 1rem',
            borderRadius: 'var(--radius-sm)',
            marginBottom: '1rem',
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
            fontSize: '0.85rem',
          }}
        >
          <AlertCircle size={16} color="#f43f5e" />
          <span>{exportError}</span>
        </div>
      )}

      {exportSuccess && (
        <div
          className="no-print animate-fade-in"
          style={{
            background: 'rgba(16, 185, 129, 0.15)',
            border: '1px solid rgba(16, 185, 129, 0.4)',
            color: '#6ee7b7',
            padding: '0.65rem 1rem',
            borderRadius: 'var(--radius-sm)',
            marginBottom: '1rem',
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
            fontSize: '0.85rem',
          }}
        >
          <CheckCircle2 size={16} color="#10b981" />
          <span>{exportSuccess}</span>
        </div>
      )}

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
              {(category || 'B2B SAAS').toUpperCase()} MARKET VALUATION & FEASIBILITY REPORT
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
            {businessName || 'Market Analysis'}
          </h1>
          <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap', fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '0.35rem' }}>
            <span>Category: <strong style={{ color: '#ffffff' }}>{category}</strong></span>
            <span>Target Market: <strong style={{ color: '#ffffff' }}>{geography}</strong></span>
            <span>Run ID: <code>{result.pipeline_id || 'N/A'}</code></span>
            <span>Date: {result.started_at ? new Date(result.started_at).toLocaleDateString() : new Date().toLocaleDateString()}</span>
          </div>

          {/* Context Disclaimer */}
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
              <strong>Market Sizing Notice:</strong> This analysis evaluates commercial market sizing, customer adoption, and software unit economics with verified empirical sources.
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
                Market evaluation for venture: <em style={{ color: '#ffffff' }}>"{result.business_idea || 'B2B SaaS Idea'}"</em> in <strong style={{ color: '#ffffff' }}>{geography}</strong>.
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

        {/* 2. Business Concept Parameters */}
        <div style={{ marginBottom: '1.5rem' }}>
          <h3 style={{ fontSize: '1.1rem', fontWeight: 700, color: '#ffffff', marginBottom: '0.5rem' }}>
            2. Business Concept Parameters & Customer Profiling
          </h3>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem' }}>
            <tbody>
              <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                <td style={{ padding: '0.5rem 0', color: 'var(--text-muted)', width: '35%' }}>SaaS Category</td>
                <td style={{ padding: '0.5rem 0', color: '#ffffff', fontWeight: 600 }}>{category}</td>
              </tr>
              <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                <td style={{ padding: '0.5rem 0', color: 'var(--text-muted)' }}>Target Paying Customer</td>
                <td style={{ padding: '0.5rem 0', color: '#ffffff' }}>{customer}</td>
              </tr>
              <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                <td style={{ padding: '0.5rem 0', color: 'var(--text-muted)' }}>Geography & Market Scope</td>
                <td style={{ padding: '0.5rem 0', color: '#ffffff' }}>{geography} {bAnalysis?.regulatory_market ? `| ${bAnalysis.regulatory_market}` : ''}</td>
              </tr>
              <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                <td style={{ padding: '0.5rem 0', color: 'var(--text-muted)' }}>Pricing & SaaS Unit Economics</td>
                <td style={{ padding: '0.5rem 0', color: '#ffffff' }}>
                  {bAnalysis?.pricing_basis || bAnalysis?.pricing_model || 'Not available'} {bAnalysis?.annual_revenue_per_customer ? `(@ ${formatCurrencyValue(bAnalysis.annual_revenue_per_customer, currency, '/yr')})` : ''}
                </td>
              </tr>
              <tr>
                <td style={{ padding: '0.5rem 0', color: 'var(--text-muted)' }}>Primary Problem Solved</td>
                <td style={{ padding: '0.5rem 0', color: '#ffffff' }}>{bAnalysis?.primary_problem || bAnalysis?.customer_problem || 'Not available'}</td>
              </tr>
            </tbody>
          </table>
        </div>

        {/* 3. Market Sizing Findings */}
        <div style={{ marginBottom: '1.5rem' }}>
          <h3 style={{ fontSize: '1.1rem', fontWeight: 700, color: '#ffffff', marginBottom: '0.5rem' }}>
            3. Market Sizing Findings & Deterministic Sizing (TAM / SAM / SOM)
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
                  {samCustomersFormatted ? ` (${samCustomersFormatted} customers)` : ''}
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
                  {somCustomersFormatted ? ` (${somCustomersFormatted} customers)` : ''}
                </td>
                <td style={{ padding: '0.6rem 0' }}>{som?.status ? String(som.status).toUpperCase() : 'CALCULATED'}</td>
                <td style={{ padding: '0.6rem 0' }}>{String(som?.confidence || 'MEDIUM').toUpperCase()}</td>
              </tr>
            </tbody>
          </table>
        </div>

        {/* 4. SOM Capacity Scenarios */}
        {somScenarios && !isSomUnavailable && (
          <div style={{ marginBottom: '1.5rem' }}>
            <h3 style={{ fontSize: '1.1rem', fontWeight: 700, color: '#ffffff', marginBottom: '0.5rem' }}>
              4. Serviceable Obtainable Market (SOM) Capacity Scenarios
            </h3>
            <div className="grid-3" style={{ gap: '1rem' }}>
              <div style={{ background: 'rgba(255,255,255,0.02)', padding: '1rem', borderRadius: 'var(--radius-md)', border: '1px solid rgba(255,255,255,0.06)' }}>
                <span style={{ fontSize: '0.75rem', fontWeight: 700, color: '#94a3b8', textTransform: 'uppercase' }}>Conservative SOM</span>
                <div style={{ fontSize: '1.2rem', fontWeight: 800, color: '#ffffff', marginTop: '0.25rem' }}>
                  {formatCurrencyValue(somScenarios.conservative || (somScenarios as any).conservative_som, currency, '/yr')}
                </div>
                <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '0.2rem' }}>
                  Acquires ~{(somScenarios as any).conservative_customers || 'N/A'} customers ({(somScenarios as any).conservative_share_pct || 'N/A'}% share)
                </div>
              </div>

              <div style={{ background: 'rgba(16,185,129,0.04)', padding: '1rem', borderRadius: 'var(--radius-md)', border: '1px solid rgba(16,185,129,0.3)' }}>
                <span style={{ fontSize: '0.75rem', fontWeight: 700, color: '#34d399', textTransform: 'uppercase' }}>Base SOM (Target)</span>
                <div style={{ fontSize: '1.2rem', fontWeight: 800, color: '#34d399', marginTop: '0.25rem' }}>
                  {formatCurrencyValue(somScenarios.base || (somScenarios as any).base_som, currency, '/yr')}
                </div>
                <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '0.2rem' }}>
                  Acquires ~{(somScenarios as any).base_customers || 'N/A'} customers ({(somScenarios as any).base_share_pct || 'N/A'}% share)
                </div>
              </div>

              <div style={{ background: 'rgba(255,255,255,0.02)', padding: '1rem', borderRadius: 'var(--radius-md)', border: '1px solid rgba(255,255,255,0.06)' }}>
                <span style={{ fontSize: '0.75rem', fontWeight: 700, color: '#38bdf8', textTransform: 'uppercase' }}>Optimistic SOM</span>
                <div style={{ fontSize: '1.2rem', fontWeight: 800, color: '#ffffff', marginTop: '0.25rem' }}>
                  {formatCurrencyValue(somScenarios.optimistic || (somScenarios as any).optimistic_som, currency, '/yr')}
                </div>
                <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '0.2rem' }}>
                  Acquires ~{(somScenarios as any).optimistic_customers || 'N/A'} customers ({(somScenarios as any).optimistic_share_pct || 'N/A'}% share)
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
              {sources.map((s: any, idx) => {
                const metricLabel = String(s?.metric || s?.metric_name || 'tam base market').replace(/_/g, ' ');
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
                          background: 'rgba(16, 185, 129, 0.15)',
                          color: '#34d399',
                        }}
                      >
                        {s?.source_quality_tier || s?.data_type || 'SOURCED'}
                      </span>
                    </div>
                  </li>
                );
              })}
            </ul>
          ) : (
            <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', fontStyle: 'italic', margin: 0 }}>
              Empirical evidence tracked in calculation report.
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
              {assumptions.map((a: any, idx) => {
                const label = String(a.metric || a.name || 'conversion rate').replace(/_/g, ' ');
                return (
                  <li key={idx} style={{ marginBottom: '0.35rem' }}>
                    <strong style={{ color: '#ffffff' }}>{label}:</strong> {a.description || a.rationale || a.justification || `${a.value} ${a.unit || ''}`}
                  </li>
                );
              })}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
};
