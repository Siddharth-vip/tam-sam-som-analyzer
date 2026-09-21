import { describe, it, expect, vi, beforeEach } from 'vitest';
import { generateReportHTML, downloadReportFile } from '../services/reportExport';
import { PipelineResult } from '../types/api';

describe('Report Export Pipeline & Validation Suite', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  const baseResult: PipelineResult = {
    pipeline_id: 'pipe_export_test_1',
    status: 'completed',
    business_idea: 'Cloud-based HR and payroll management platform for small and medium-sized businesses in India',
    business_analysis: {
      business_name: 'PayFlow HR',
      business_idea: 'Cloud-based HR and payroll management platform for small and medium-sized businesses in India',
      category: 'HR & Workforce Management',
      target_customer: 'Small & Medium Businesses (SMBs)',
      target_country: 'India',
      geography: 'India',
      business_model: 'B2B SaaS',
      pricing_basis: 'per_user',
      annual_revenue_per_customer: 37500,
      primary_problem: 'Manual payroll errors and compliance overhead',
    },
    research_queries: [],
    discovered_sources: [],
    fetched_sources: [],
    extracted_candidates: [],
    validation_results: [
      {
        metric: 'smb_employer_count',
        value: 1200000,
        unit: 'businesses',
        source_name: 'Ministry of MSME Annual Report',
        source_url: 'https://msme.gov.in',
        source_quality_tier: 'tier_1_government_official',
      },
      {
        metric: 'annual_payroll_software_arpu',
        value: 36000,
        unit: 'INR/yr',
        source_name: 'India SaaS Benchmark Report',
        source_url: 'https://saasboomiorg.in',
        source_quality_tier: 'tier_2_academic_trade',
      },
    ],
    calculation_report: {
      calculation_id: 'calc_export_1',
      status: 'calculated',
      currency: 'INR',
      confidence: 'high',
      top_down_tam: {
        status: 'calculated',
        estimate: 43200000000,
        currency: 'INR',
        confidence: 'high',
        steps: [],
        assumptions_used: [],
        warnings: [],
      },
      bottom_up_tam: {
        status: 'calculated',
        estimate: 43200000000,
        currency: 'INR',
        confidence: 'high',
        steps: [],
        assumptions_used: [],
        warnings: [],
      },
      bottom_up_sam: {
        status: 'calculated',
        estimate: 8640000000,
        currency: 'INR',
        confidence: 'medium',
        sam_percentage_of_tam: 20.0,
        serviceable_customer_count: 240000,
        steps: [],
        assumptions_used: [],
        warnings: [],
      },
      bottom_up_som: {
        status: 'calculated',
        estimate: 86400000,
        currency: 'INR',
        confidence: 'medium',
        som_percentage_of_sam: 1.0,
        obtainable_customer_count: 2400,
        steps: [],
        assumptions_used: [],
        warnings: [],
      },
      all_steps: [
        {
          step_number: 1,
          description: 'Calculate Total Addressable Market (TAM)',
          formula: 'potential_customers * annual_arpu',
          operands: { potential_customers: 1200000, annual_arpu: 36000 },
          result: 43200000000,
          unit: 'INR/yr',
          evidence_references: ['https://msme.gov.in'],
          assumptions: [],
          warnings: [],
        },
      ],
      all_assumptions: [
        {
          name: 'serviceable_digital_adoption',
          value: 0.20,
          unit: '%',
          justification: 'Estimated 20% of Indian MSMEs have active cloud accounting adoption.',
        },
      ],
      warnings: [],
    },
    tam: {
      status: 'calculated',
      estimate: 43200000000,
      currency: 'INR',
      confidence: 'high',
      steps: [],
      assumptions_used: [],
      warnings: [],
    },
    sam: {
      status: 'calculated',
      estimate: 8640000000,
      currency: 'INR',
      confidence: 'medium',
      sam_percentage_of_tam: 20.0,
      serviceable_customer_count: 240000,
      steps: [],
      assumptions_used: [],
      warnings: [],
    },
    som: {
      status: 'calculated',
      estimate: 86400000,
      currency: 'INR',
      confidence: 'medium',
      som_percentage_of_sam: 1.0,
      obtainable_customer_count: 2400,
      steps: [],
      assumptions_used: [],
      warnings: [],
    },
    som_scenarios: {
      conservative: 43200000,
      base: 86400000,
      optimistic: 172800000,
      conservative_customers: 1200,
      base_customers: 2400,
      optimistic_customers: 4800,
      conservative_share_pct: 0.5,
      base_share_pct: 1.0,
      optimistic_share_pct: 2.0,
    },
    market_attractiveness: {
      rating: 'HIGH',
      score: 8.5,
      market_size_appeal: 'Large addressable MSME workforce market.',
      growth_outlook: 'Strong digital adoption tailwinds.',
      competitive_intensity: 'Moderate fragmented local competitors.',
      procurement_friction: 'Low friction self-serve onboarding.',
      regulatory_readiness: 'High statutory compliance requirement.',
      rationale: 'High recurring SaaS revenue potential with defensible market size.',
    },
    competitors: [
      {
        name: 'Keka HR',
        product_service: 'HR & Payroll SaaS',
        target_market: 'Indian SMBs',
        differentiators: 'Automated statutory compliance and payroll',
      },
    ],
    confidence: 'high',
    conflicts: [],
    errors: [],
    warnings: [],
    audit_trail: [],
    provenance: [],
    started_at: '2026-09-17T12:00:00Z',
  };

  // A. Valid report -> non-empty generated HTML & download file
  it('A. generates non-empty HTML with valid metadata and size > 0', () => {
    const html = generateReportHTML(baseResult);
    expect(html).toBeDefined();
    expect(html.length).toBeGreaterThan(500);
    expect(html).toContain('PayFlow HR');
    expect(html).toContain('HR & Workforce Management');
    expect(html).toContain('₹4,320 Cr');
    expect(html).toContain('₹864 Cr');
    expect(html).toContain('₹8.64 Cr');
  });

  // B. Large report -> non-empty downloaded file with verified Blob
  it('B. creates a verified Blob with size > 0 and correct MIME text/html', () => {
    const exportResult = downloadReportFile(baseResult);
    expect(exportResult.success).toBe(true);
    expect(exportResult.sizeBytes).toBeGreaterThan(1000);
    expect(exportResult.mimeType).toBe('text/html;charset=utf-8');
    expect(exportResult.filename).toContain('payflow-hr-report');
  });

  // C. Report with SOM = INSUFFICIENT_EVIDENCE -> export still works safely
  it('C. exports safely when SOM has insufficient evidence', () => {
    const insufficientSomResult: PipelineResult = {
      ...baseResult,
      som: {
        status: 'insufficient_evidence',
        estimate: null,
        currency: 'INR',
        confidence: 'low',
        steps: [],
        assumptions_used: [],
        warnings: ['Missing empirical market share evidence'],
      },
      som_scenarios: null,
    };

    const html = generateReportHTML(insufficientSomResult);
    expect(html).toContain('Insufficient Evidence');
    expect(html).not.toContain('NaN');

    const exportResult = downloadReportFile(insufficientSomResult);
    expect(exportResult.success).toBe(true);
    expect(exportResult.sizeBytes).toBeGreaterThan(500);
  });

  // D. Report with complete TAM/SAM/SOM -> export works with all sections
  it('D. includes all core report sections and calculation trace in export', () => {
    const html = generateReportHTML(baseResult);
    expect(html).toContain('Executive Summary');
    expect(html).toContain('Business Concept & Parameters');
    expect(html).toContain('Deterministic Market Sizing (TAM / SAM / SOM)');
    expect(html).toContain('Empirical Evidence & Verified Sources');
    expect(html).toContain('Strategic Assumptions & Model Constraints');
    expect(html).toContain('Calculation Audit Trail');
    expect(html).toContain('Competitor');
  });

  // E. Missing optional fields -> export still works safely
  it('E. exports safely without errors when optional fields are null', () => {
    const minimalResult: PipelineResult = {
      pipeline_id: 'pipe_min_export',
      status: 'completed',
      business_idea: 'Developer Observability Tool',
      business_analysis: null,
      research_queries: [],
      discovered_sources: [],
      fetched_sources: [],
      extracted_candidates: [],
      validation_results: [],
      calculation_report: null,
      tam: null,
      sam: null,
      som: null,
      confidence: 'low',
      conflicts: [],
      errors: [],
      warnings: [],
      audit_trail: [],
      provenance: [],
      started_at: '2026-09-17T12:00:00Z',
    };

    const html = generateReportHTML(minimalResult);
    expect(html).toBeDefined();
    expect(html.length).toBeGreaterThan(300);
    expect(html).toContain('Developer Observability Tool');

    const exportResult = downloadReportFile(minimalResult);
    expect(exportResult.success).toBe(true);
    expect(exportResult.sizeBytes).toBeGreaterThan(300);
  });

  // F. Export attempted with null data -> handled safely throwing clear Error
  it('F. throws meaningful Error without creating a 0 KB file if result is null', () => {
    expect(() => generateReportHTML(null as any)).toThrow(/result data is null or undefined/i);
    expect(() => downloadReportFile(null as any)).toThrow(/No analysis result available/i);
  });

  // G. Category and customer consistency across diverse B2B SaaS sectors
  it('G. preserves consistency across multiple B2B SaaS categories without hardcoding', () => {
    const devToolsResult: PipelineResult = {
      ...baseResult,
      business_idea: 'Real-time API error monitoring and distributed tracing for software engineering teams',
      business_analysis: {
        business_name: 'TracePulse',
        business_idea: 'Real-time API error monitoring and distributed tracing for software engineering teams',
        category: 'Developer Tools',
        target_customer: 'Software Developers & DevOps Engineers',
        target_country: 'United States',
        geography: 'United States',
        business_model: 'B2B SaaS',
        pricing_basis: 'per_user',
        annual_revenue_per_customer: 2400,
        primary_problem: 'Slow distributed system debugging and outage resolution',
      },
    };

    const html = generateReportHTML(devToolsResult);
    expect(html).toContain('DEVELOPER TOOLS MARKET VALUATION');
    expect(html).toContain('TracePulse');
    expect(html).toContain('Software Developers & DevOps Engineers');
    expect(html).not.toContain('Dental');
    expect(html).not.toContain('Hospital');
  });

  // H. Customer count presentation validation (integer representation)
  it('H. formats customer counts as integer estimates without altering financial values', () => {
    const fractionalResult: PipelineResult = {
      ...baseResult,
      sam: {
        status: 'calculated',
        estimate: 855000,
        currency: 'INR',
        confidence: 'high',
        serviceable_customer_count: 23.75, // 23.75 fractional
        steps: [],
        assumptions_used: [],
        warnings: [],
      },
    };

    const html = generateReportHTML(fractionalResult);
    expect(html).toContain('~24 customers');
    expect(html).toContain('₹8.55 Lakh');
  });
});
