import { PipelineResult } from '../types/api';
import { formatCurrencyValue, formatNumberOnly } from './api';

export interface ExportReportOptions {
  filename?: string;
}

export interface ExportResult {
  success: boolean;
  filename: string;
  sizeBytes: number;
  mimeType: string;
}

/**
 * Generate a complete, standalone, styled HTML document for the Market Sizing Analysis Report.
 */
export function generateReportHTML(result: PipelineResult): string {
  if (!result) {
    throw new Error('Cannot generate report: result data is null or undefined.');
  }

  const bAnalysis = result.business_analysis;
  const currency = result.calculation_report?.currency || result.tam?.currency || 'INR';
  const tam = result.tam || result.calculation_report?.top_down_tam || result.calculation_report?.bottom_up_tam;
  const sam = result.sam || result.calculation_report?.top_down_sam || result.calculation_report?.bottom_up_sam;
  const som = result.som || result.calculation_report?.top_down_som || result.calculation_report?.bottom_up_som;
  const assumptions = result.calculation_report?.all_assumptions || [];
  const sources = result.validation_results || [];
  const attractiveness = result.market_attractiveness;
  const sections20 = result.final_report_sections;
  const steps = result.calculation_report?.all_steps || [];
  const competitors = result.competitors || [];
  const warnings = result.warnings || [];

  const businessName = bAnalysis?.business_name || bAnalysis?.product || 'B2B SaaS Market Sizing Report';
  const businessIdea = result.business_idea || bAnalysis?.business_idea || 'B2B SaaS Business Concept';
  const category = bAnalysis?.category || bAnalysis?.healthcare_saas_category || 'B2B SaaS';
  const customer = bAnalysis?.target_customer || (bAnalysis?.customer_type ? bAnalysis.customer_type.replace(/_/g, ' ') : 'Target Customers');
  const geography = bAnalysis?.target_country || bAnalysis?.geography || 'Global';
  const dateStr = result.started_at ? new Date(result.started_at).toLocaleDateString() : new Date().toLocaleDateString();
  const runId = result.pipeline_id || 'N/A';
  const researchProvider = (result.research_provider || 'mock').toUpperCase();

  const isSomUnavailable = !som || som.status === 'insufficient_evidence' || som.estimate === null || som.estimate === undefined;

  // Format customer counts safely for integer presentation
  const formatCustomerCount = (count?: number | null) => {
    if (count === null || count === undefined || isNaN(count)) return null;
    const rounded = Math.round(count);
    return rounded === count ? `${count.toLocaleString()}` : `~${rounded.toLocaleString()}`;
  };

  const samCustomersFormatted = formatCustomerCount(sam?.serviceable_customer_count);
  const somCustomersFormatted = formatCustomerCount(som?.obtainable_customer_count);

  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>${businessName} — Market Valuation & Sizing Report</title>
  <style>
    :root {
      --bg: #0b0f19;
      --card-bg: #111827;
      --border: #1f2937;
      --border-accent: #374151;
      --text-main: #f9fafb;
      --text-muted: #9ca3af;
      --primary: #6366f1;
      --cyan: #06b6d4;
      --emerald: #10b981;
      --amber: #f59e0b;
      --rose: #f43f5e;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
      background-color: var(--bg);
      color: var(--text-main);
      padding: 2.5rem 1.5rem;
      line-height: 1.6;
    }
    .container {
      max-width: 960px;
      margin: 0 auto;
      background: var(--card-bg);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 2.5rem;
      box-shadow: 0 10px 25px rgba(0, 0, 0, 0.5);
    }
    .header {
      border-bottom: 2px solid var(--border-accent);
      padding-bottom: 1.5rem;
      margin-bottom: 2rem;
    }
    .badge-bar {
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 0.75rem;
      margin-bottom: 0.75rem;
    }
    .category-tag {
      font-size: 0.75rem;
      font-weight: 700;
      color: var(--cyan);
      letter-spacing: 0.05em;
      text-transform: uppercase;
    }
    .badges {
      display: flex;
      gap: 0.5rem;
      align-items: center;
    }
    .badge {
      font-size: 0.75rem;
      font-weight: 700;
      padding: 0.25rem 0.65rem;
      border-radius: 9999px;
      border: 1px solid currentColor;
    }
    .badge-live { color: #34d399; background: rgba(16, 185, 129, 0.15); }
    .badge-mock { color: #fbbf24; background: rgba(245, 158, 11, 0.15); }
    .badge-high { color: #34d399; background: rgba(16, 185, 129, 0.15); }
    .badge-med { color: #fbbf24; background: rgba(245, 158, 11, 0.15); }
    .badge-low { color: #f87171; background: rgba(239, 68, 68, 0.15); }
    h1 {
      font-size: 2rem;
      font-weight: 800;
      color: #ffffff;
      margin-bottom: 0.5rem;
    }
    .meta-grid {
      display: flex;
      flex-wrap: wrap;
      gap: 1.25rem;
      font-size: 0.85rem;
      color: var(--text-muted);
      margin-top: 0.5rem;
    }
    .meta-grid strong { color: #ffffff; }
    .section {
      margin-bottom: 2rem;
    }
    .section h2 {
      font-size: 1.25rem;
      font-weight: 700;
      color: #ffffff;
      margin-bottom: 0.75rem;
      border-bottom: 1px solid var(--border);
      padding-bottom: 0.4rem;
    }
    p {
      font-size: 0.95rem;
      color: #d1d5db;
      line-height: 1.6;
      margin-bottom: 0.75rem;
    }
    table {
      width: 100%;
      border-collapse: collapse;
      font-size: 0.9rem;
      margin: 1rem 0;
    }
    th, td {
      padding: 0.75rem 0.5rem;
      text-align: left;
      border-bottom: 1px solid var(--border);
    }
    th {
      color: var(--text-muted);
      font-weight: 600;
      font-size: 0.8rem;
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }
    .tam-color { color: #818cf8; font-weight: 700; }
    .sam-color { color: #06b6d4; font-weight: 700; }
    .som-color { color: #10b981; font-weight: 700; }
    .val-highlight { font-size: 1.05rem; font-weight: 700; color: #ffffff; }
    .cards-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
      gap: 1rem;
      margin: 1rem 0;
    }
    .card {
      background: rgba(255, 255, 255, 0.03);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 1.25rem;
    }
    .card-title {
      font-size: 0.75rem;
      font-weight: 700;
      color: var(--text-muted);
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }
    .card-val {
      font-size: 1.4rem;
      font-weight: 800;
      color: #ffffff;
      margin-top: 0.35rem;
    }
    .card-sub {
      font-size: 0.8rem;
      color: var(--text-muted);
      margin-top: 0.25rem;
    }
    ul {
      padding-left: 1.5rem;
      font-size: 0.9rem;
      color: #d1d5db;
    }
    li { margin-bottom: 0.5rem; }
    .footer {
      margin-top: 3rem;
      padding-top: 1.5rem;
      border-top: 1px solid var(--border);
      font-size: 0.8rem;
      color: var(--text-muted);
      text-align: center;
    }
    @media print {
      body { background: #ffffff !important; color: #111827 !important; padding: 0; }
      .container { border: none; box-shadow: none; padding: 1.5rem; max-width: 100%; }
      h1, .section h2, .val-highlight { color: #111827 !important; }
      p, ul, td { color: #374151 !important; }
      .card { background: #f9fafb !important; border: 1px solid #e5e7eb !important; }
      .card-val { color: #111827 !important; }
      th, td { border-bottom: 1px solid #e5e7eb !important; }
      .meta-grid strong { color: #111827 !important; }
    }
  </style>
</head>
<body>
  <div class="container" id="printable-report">
    <!-- Header -->
    <div class="header">
      <div class="badge-bar">
        <span class="category-tag">${category.toUpperCase()} MARKET VALUATION & SIZING REPORT</span>
        <div class="badges">
          <span class="badge ${researchProvider === 'LIVE' ? 'badge-live' : 'badge-mock'}">RESEARCH: ${researchProvider}</span>
          ${attractiveness ? `<span class="badge ${attractiveness.rating === 'HIGH' ? 'badge-high' : attractiveness.rating === 'MEDIUM' ? 'badge-med' : 'badge-low'}">ATTRACTIVENESS: ${attractiveness.rating} (${attractiveness.score}/10)</span>` : ''}
        </div>
      </div>
      <h1>${businessName}</h1>
      <div class="meta-grid">
        <span>Category: <strong>${category}</strong></span>
        <span>Target Customer: <strong>${customer}</strong></span>
        <span>Geography: <strong>${geography}</strong></span>
        <span>Run ID: <code>${runId}</code></span>
        <span>Date: ${dateStr}</span>
      </div>
    </div>

    <!-- 1. Executive Summary -->
    <div class="section">
      <h2>1. Executive Summary</h2>
      <p>
        ${sections20?.['1_executive_summary'] || sections20?.['1. Executive Summary'] || `
          Market evaluation for venture: <em style="color:#ffffff;">"${businessIdea}"</em> in <strong>${geography}</strong>.
          Deterministic market sizing established a Total Addressable Market (TAM) of 
          <strong class="tam-color">${tam?.estimate != null ? formatCurrencyValue(tam.estimate, currency, '/yr') : 'Not calculable'}</strong> 
          and a Serviceable Addressable Market (SAM) of 
          <strong class="sam-color">${sam?.estimate != null ? formatCurrencyValue(sam.estimate, currency, '/yr') : 'Not calculable'}</strong>${sam?.sam_percentage_of_tam != null ? ` (${sam.sam_percentage_of_tam}% of TAM)` : ''}.
          The Serviceable Obtainable Market (SOM) is projected at 
          <strong class="som-color">${som?.estimate != null ? formatCurrencyValue(som.estimate, currency, '/yr') : 'Insufficient data'}</strong>${som?.som_percentage_of_sam != null ? ` (${som.som_percentage_of_sam}% capture rate)` : ''}.
        `}
      </p>
    </div>

    <!-- 2. Value Proposition & Solution Architecture -->
    ${result.value_proposition_analysis ? `
    <div class="section">
      <h2>2. Value Proposition & Solution Architecture</h2>
      <table>
        <tbody>
          <tr>
            <td style="width: 30%; color: var(--text-muted);">Core Problem</td>
            <td><strong>${result.value_proposition_analysis.customer_problem}</strong></td>
          </tr>
          <tr>
            <td style="color: var(--text-muted);">Current Pain Point</td>
            <td>${result.value_proposition_analysis.current_pain_point}</td>
          </tr>
          <tr>
            <td style="color: var(--text-muted);">Product Solution</td>
            <td><strong>${result.value_proposition_analysis.product_solution}</strong></td>
          </tr>
          <tr>
            <td style="color: var(--text-muted);">Measurable ROI</td>
            <td>${result.value_proposition_analysis.operational_benefit} ${result.value_proposition_analysis.financial_time_saving_benefit ? `• ${result.value_proposition_analysis.financial_time_saving_benefit}` : ''}</td>
          </tr>
          <tr>
            <td style="color: var(--text-muted);">Competitive Moat</td>
            <td style="color: #a5b4fc; font-style: italic;">${result.value_proposition_analysis.differentiation_opportunity}</td>
          </tr>
        </tbody>
      </table>
    </div>` : ''}

    <!-- 3. Business Concept & Parameters -->
    <div class="section">
      <h2>3. Business Concept & Parameters</h2>
      <table>
        <tbody>
          <tr>
            <td style="width: 35%; color: var(--text-muted);">SaaS Category</td>
            <td><strong>${category}</strong></td>
          </tr>
          <tr>
            <td style="color: var(--text-muted);">Target Paying Customer</td>
            <td><strong>${customer}</strong></td>
          </tr>
          <tr>
            <td style="color: var(--text-muted);">Geography</td>
            <td><strong>${geography}</strong></td>
          </tr>
          <tr>
            <td style="color: var(--text-muted);">Pricing & Unit Economics</td>
            <td><strong>${bAnalysis?.pricing_basis || bAnalysis?.pricing_model || 'Subscription'} ${bAnalysis?.annual_revenue_per_customer ? `(@ ${formatCurrencyValue(bAnalysis.annual_revenue_per_customer, currency, '/yr')})` : ''}</strong></td>
          </tr>
          <tr>
            <td style="color: var(--text-muted);">Primary Problem Solved</td>
            <td>${bAnalysis?.primary_problem || bAnalysis?.customer_problem || 'Workflow Optimization & Digital Automation'}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- 4. Market Sizing Table (TAM / SAM / SOM) -->
    <div class="section">
      <h2>4. Deterministic Market Sizing (TAM / SAM / SOM)</h2>
      <table>
        <thead>
          <tr>
            <th>Metric</th>
            <th>Valuation</th>
            <th>Derived Customer Count / Share</th>
            <th>Status</th>
            <th>Confidence</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td class="tam-color">TAM (Total Addressable Market)</td>
            <td class="val-highlight">${tam?.estimate != null ? formatCurrencyValue(tam.estimate, currency, '/yr') : 'Not calculable'}</td>
            <td>100% Total Population</td>
            <td>${tam?.status ? String(tam.status).toUpperCase() : 'CALCULATED'}</td>
            <td>${String(tam?.confidence || 'HIGH').toUpperCase()}</td>
          </tr>
          <tr>
            <td class="sam-color">SAM (Serviceable Addressable Market)</td>
            <td class="val-highlight">${sam?.estimate != null ? formatCurrencyValue(sam.estimate, currency, '/yr') : 'Not calculable'}</td>
            <td>${sam?.sam_percentage_of_tam != null ? `${sam.sam_percentage_of_tam}% of TAM` : 'Target Segment'}${samCustomersFormatted ? ` • ${samCustomersFormatted} customers` : ''}</td>
            <td>${sam?.status ? String(sam.status).toUpperCase() : 'CALCULATED'}</td>
            <td>${String(sam?.confidence || 'HIGH').toUpperCase()}</td>
          </tr>
          <tr>
            <td class="som-color">SOM (Serviceable Obtainable Market)</td>
            <td class="val-highlight" style="color: ${isSomUnavailable ? '#fbbf24' : '#ffffff'};">${isSomUnavailable ? 'Insufficient Evidence' : formatCurrencyValue(som?.estimate, currency, '/yr')}</td>
            <td>${som?.som_percentage_of_sam != null ? `${som.som_percentage_of_sam}% of SAM` : 'Capacity-Derived'}${somCustomersFormatted ? ` • ${somCustomersFormatted} customers` : ''}</td>
            <td>${som?.status ? String(som.status).toUpperCase() : 'CALCULATED'}</td>
            <td>${String(som?.confidence || 'MEDIUM').toUpperCase()}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- 5. Market Growth & Trends -->
    ${(result.market_growth || (result.market_trends && result.market_trends.length > 0)) ? `
    <div class="section">
      <h2>5. Market Growth & B2B Industry Trends</h2>
      ${result.market_growth ? `
      <p style="margin-bottom: 0.75rem;">
        <strong>Sector CAGR:</strong> <span style="color: #34d399; font-weight: 700;">${result.market_growth.cagr_percentage_string || `${((result.market_growth.cagr || 0.168) * 100).toFixed(1)}% CAGR`}</span>
        <span class="badge badge-live" style="margin-left: 0.5rem;">${result.market_growth.cagr_type}</span>
        (Period: ${result.market_growth.forecast_period || '2024-2030'})
      </p>` : ''}
      ${(result.market_trends && result.market_trends.length > 0) ? `
      <ul>
        ${result.market_trends.map((t: any) => `<li><strong>${t.trend}:</strong> ${t.explanation} <em style="color:#a78bfa;">(Impact: ${t.impact_on_market})</em></li>`).join('')}
      </ul>` : ''}
    </div>` : ''}

    <!-- 6. Customer Tier Segmentation -->
    ${(result.customer_segmentation && result.customer_segmentation.length > 0) ? `
    <div class="section">
      <h2>6. Customer Tier Segmentation</h2>
      <table>
        <thead>
          <tr>
            <th>Segment Tier</th>
            <th>Description</th>
            <th>Business Need</th>
            <th>Pricing Fit</th>
          </tr>
        </thead>
        <tbody>
          ${result.customer_segmentation.map((s: any) => `
            <tr>
              <td><strong>${s.segment_name}</strong></td>
              <td>${s.description}</td>
              <td>${s.business_need || 'Standard automation'}</td>
              <td style="color: #60a5fa;">${s.pricing_relevance || 'Tiered'}</td>
            </tr>
          `).join('')}
        </tbody>
      </table>
    </div>` : ''}

    <!-- 7. Competitor Analysis & Comparison Matrix -->
    ${competitors.length > 0 ? `
    <div class="section">
      <h2>7. Competitor Analysis & Comparison Matrix</h2>
      <table>
        <thead>
          <tr>
            <th>Competitor</th>
            <th>Target Customer</th>
            <th>Geography</th>
            <th>Pricing</th>
            <th>Positioning</th>
          </tr>
        </thead>
        <tbody>
          ${competitors.map((c: any) => `
            <tr>
              <td><strong>${c.name}</strong></td>
              <td>${c.target_customers || c.target_market || 'Businesses'}</td>
              <td>${c.geography || 'Global'}</td>
              <td style="color: #34d399;">${c.public_pricing || c.pricing || 'Pricing not publicly available'}</td>
              <td style="color: #c7d2fe; font-style: italic;">${c.differentiators || c.product_service || 'Active Player'}</td>
            </tr>
          `).join('')}
        </tbody>
      </table>
    </div>` : ''}

    <!-- 8. Empirical Evidence & Sources -->
    <div class="section">
      <h2>8. Empirical Evidence & Verified Sources</h2>
      ${sources.length > 0 ? `
      <ul>
        ${sources.map((s: any) => {
          const metricLabel = String(s?.metric || s?.metric_name || 'Metric').replace(/_/g, ' ');
          const sourceName = s?.source_name || s?.source_url || 'Verified Sourced Evidence';
          const valDisplay = s?.value != null ? (s.unit?.includes('INR') || s.unit?.includes('USD') ? formatCurrencyValue(s.value, currency) : `${formatNumberOnly(s.value)} ${s.unit || ''}`) : '';
          return `<li><strong>${metricLabel}:</strong> ${valDisplay ? `${valDisplay} — ` : ''}${sourceName} <span class="badge badge-live">${s?.source_quality_tier || s?.data_type || 'SOURCED'}</span></li>`;
        }).join('')}
      </ul>` : `<p style="color: var(--text-muted); font-style: italic;">Empirical source evidence recorded in calculation trace.</p>`}
    </div>

    <!-- 9. Strategic Assumptions -->
    ${assumptions.length > 0 ? `
    <div class="section">
      <h2>9. Strategic Assumptions & Model Constraints</h2>
      <ul>
        ${assumptions.map((a: any) => `<li><strong>${String(a.metric || a.name || 'Assumption').replace(/_/g, ' ')}:</strong> ${a.description || a.rationale || a.justification || `${a.value} ${a.unit || ''}`}</li>`).join('')}
      </ul>
    </div>` : ''}

    <!-- 10. Calculation Audit Trail -->
    ${steps.length > 0 ? `
    <div class="section">
      <h2>10. Calculation Audit Trail</h2>
      <table>
        <thead>
          <tr>
            <th>Step</th>
            <th>Description</th>
            <th>Formula</th>
            <th>Result</th>
          </tr>
        </thead>
        <tbody>
          ${steps.map((st: any) => `
            <tr>
              <td>#${st.step_number}</td>
              <td>${st.description}</td>
              <td><code>${st.formula}</code></td>
              <td><strong>${st.result != null ? (st.unit?.includes('INR') || st.unit?.includes('USD') ? formatCurrencyValue(st.result, currency) : `${formatNumberOnly(st.result)} ${st.unit || ''}`) : 'N/A'}</strong></td>
            </tr>
          `).join('')}
        </tbody>
      </table>
    </div>` : ''}

    <!-- 11. Warnings & Evidentiary Caveats -->
    ${warnings.length > 0 ? `
    <div class="section">
      <h2>11. Analysis Notes & Evidentiary Caveats</h2>
      <ul>
        ${warnings.map((w: string) => `<li style="color: #fbbf24;">${w}</li>`).join('')}
      </ul>
    </div>` : ''}

    <!-- Footer -->
    <div class="footer">
      <p>Generated deterministically by AI TAM/SAM/SOM Market Intelligence Engine. Run ID: ${runId}</p>
    </div>
  </div>
</body>
</html>`;
}

/**
 * Trigger browser download of the generated report with rigorous validation.
 */
export function downloadReportFile(result: PipelineResult, options: ExportReportOptions = {}): ExportResult {
  if (!result) {
    throw new Error('Report generation failed: No analysis result available to export.');
  }

  const htmlContent = generateReportHTML(result);

  if (!htmlContent || typeof htmlContent !== 'string' || htmlContent.trim().length === 0) {
    throw new Error('Report generation failed: Generated content is empty.');
  }

  const mimeType = 'text/html;charset=utf-8';
  const blob = new Blob([htmlContent], { type: mimeType });

  if (!blob || blob.size === 0) {
    throw new Error('Report generation failed: Generated file has 0 bytes.');
  }

  // Create sanitized filename
  const rawName = result.business_analysis?.business_name || result.business_analysis?.product || 'market-analysis';
  const sanitizedName = rawName.toLowerCase().replace(/[^a-z0-9_-]/g, '-').replace(/-+/g, '-').slice(0, 50);
  const timestamp = new Date().toISOString().split('T')[0];
  const filename = options.filename || `${sanitizedName}-report-${timestamp}.html`;

  // Create download link and trigger download
  if (typeof window !== 'undefined' && typeof document !== 'undefined') {
    const url = URL.createObjectURL(blob);
    try {
      const anchor = document.createElement('a');
      anchor.href = url;
      anchor.download = filename;
      anchor.style.display = 'none';
      document.body.appendChild(anchor);
      anchor.click();
      document.body.removeChild(anchor);
    } finally {
      setTimeout(() => {
        try {
          URL.revokeObjectURL(url);
        } catch {
          // ignore cleanup errors
        }
      }, 1500);
    }
  }

  return {
    success: true,
    filename,
    sizeBytes: blob.size,
    mimeType,
  };
}
