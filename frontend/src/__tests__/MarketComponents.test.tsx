import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';

import { BusinessIdeaForm } from '../components/BusinessIdeaForm';
import { MarketOverview } from '../components/MarketOverview';
import { MarketSizeCards } from '../components/MarketSizeCards';
import { MarketFunnel } from '../components/MarketFunnel';
import { MethodComparison } from '../components/MethodComparison';
import { AssumptionsPanel } from '../components/AssumptionsPanel';
import { SourcesPanel } from '../components/SourcesPanel';
import { CalculationTransparency } from '../components/CalculationTransparency';
import { ConfidenceBadge } from '../components/ConfidenceBadge';
import { ReportPanel } from '../components/ReportPanel';
import { AnalysisProgress } from '../components/AnalysisProgress';
import { CompetitorPanel } from '../components/CompetitorPanel';
import { RisksPanel } from '../components/RisksPanel';
import { MarketAnalysisPage } from '../pages/MarketAnalysis';
import * as apiService from '../services/api';
import { PipelineResult, TAMResult, SAMResult, SOMResult } from '../types/api';

describe('Market Sizing UI Components & Integration Suite', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  // 1. Business Idea Form Tests
  it('renders BusinessIdeaForm and handles validation & preset selection', () => {
    const handleSubmit = vi.fn();
    render(<BusinessIdeaForm onSubmit={handleSubmit} isLoading={false} />);

    expect(screen.getByText(/Enter Your Business Idea/i)).toBeInTheDocument();
    const textarea = screen.getByPlaceholderText(/I want to build an affordable online programming platform/i);
    expect(textarea).toBeInTheDocument();

    // Select preset
    const presetBtn = screen.getByText('EdTech / India');
    fireEvent.click(presetBtn);
    expect((textarea as HTMLTextAreaElement).value).toContain('programming platform');

    // Submit form
    const submitBtn = screen.getByRole('button', { name: /Analyze Market/i });
    fireEvent.click(submitBtn);

    expect(handleSubmit).toHaveBeenCalledWith(
      expect.objectContaining({
        business_idea: expect.stringContaining('programming platform'),
        preferred_geography: 'India',
        preferred_year: 2024,
      })
    );
  });

  // 2. Currency and Number Formatting Utilities
  it('formats currency values cleanly without throwing or fabricating', () => {
    expect(apiService.formatCurrencyValue(150000000, 'INR')).toBe('₹15 Cr');
    expect(apiService.formatCurrencyValue(500000, 'INR')).toBe('₹5 Lakh');
    expect(apiService.formatCurrencyValue(1000000000, 'USD')).toBe('$1B');
    expect(apiService.formatCurrencyValue(null)).toBe('Not calculated');
    expect(apiService.formatNumberOnly(1234567.89)).toBe('1,234,567.89');
    expect(apiService.formatNumberOnly(null)).toBe('N/A');
  });

  // 3. Confidence Badge Test
  it('renders ConfidenceBadge with correct classes and icons', () => {
    const { rerender } = render(<ConfidenceBadge confidence="high" />);
    expect(screen.getByText('HIGH')).toBeInTheDocument();

    rerender(<ConfidenceBadge confidence="low" />);
    expect(screen.getByText('LOW')).toBeInTheDocument();
  });

  // 4. Market Overview Rendering
  it('renders MarketOverview with extracted fields or "Not available"', () => {
    render(
      <MarketOverview
        analysis={{
          business_idea: 'Test Idea',
          industry: 'EdTech',
          product: 'Coding Platform',
          target_customer: 'College Students',
          geography: 'India',
          business_model: 'B2C',
          pricing_model: null,
          customer_problem: 'High tuition fees',
          value_proposition: 'Affordable interactive coding courses',
        }}
      />
    );

    expect(screen.getByText('EdTech')).toBeInTheDocument();
    expect(screen.getByText('Coding Platform')).toBeInTheDocument();
    expect(screen.getByText('College Students')).toBeInTheDocument();
    expect(screen.getByText('Not available')).toBeInTheDocument();
  });

  // 5. Market Size Cards with Valid Values
  it('renders MarketSizeCards with valid TAM, SAM, SOM estimates', () => {
    const tam: TAMResult = {
      status: 'calculated',
      estimate: 500000000, // 50 Cr
      unit: 'INR/yr',
      currency: 'INR',
      confidence: 'high',
      steps: [],
      assumptions_used: [],
      warnings: [],
    };
    const sam: SAMResult = {
      status: 'calculated',
      estimate: 100000000, // 10 Cr
      unit: 'INR/yr',
      currency: 'INR',
      confidence: 'medium',
      steps: [],
      assumptions_used: [],
      warnings: [],
    };
    const som: SOMResult = {
      status: 'calculated',
      estimate: 10000000, // 1 Cr
      unit: 'INR/yr',
      currency: 'INR',
      confidence: 'low',
      steps: [],
      assumptions_used: [],
      warnings: [],
    };

    render(<MarketSizeCards tam={tam} sam={sam} som={som} currency="INR" />);

    expect(screen.getByText('TAM')).toBeInTheDocument();
    expect(screen.getByText('SAM')).toBeInTheDocument();
    expect(screen.getByText('SOM')).toBeInTheDocument();
    expect(screen.getByText('₹50 Cr /yr')).toBeInTheDocument();
    expect(screen.getByText('₹10 Cr /yr')).toBeInTheDocument();
    expect(screen.getByText('₹1 Cr /yr')).toBeInTheDocument();
  });

  // 6. SOM SAFETY RULE TEST
  it('strictly complies with SOM safety rule when SOM has insufficient evidence', () => {
    const tam: TAMResult = {
      status: 'calculated',
      estimate: 500000000,
      unit: 'INR/yr',
      currency: 'INR',
      confidence: 'medium',
      steps: [],
      assumptions_used: [],
      warnings: [],
    };
    const sam: SAMResult = {
      status: 'calculated',
      estimate: 100000000,
      unit: 'INR/yr',
      currency: 'INR',
      confidence: 'low',
      steps: [],
      assumptions_used: [],
      warnings: [],
    };
    const som: SOMResult = {
      status: 'insufficient_evidence',
      estimate: null,
      unit: null,
      currency: 'INR',
      confidence: 'low',
      steps: [],
      assumptions_used: [],
      warnings: ['Missing empirical market share'],
      message: 'Obtainable market share missing',
    };

    render(<MarketSizeCards tam={tam} sam={sam} som={som} currency="INR" />);

    expect(screen.getByText('Insufficient Evidence')).toBeInTheDocument();
    expect(
      screen.getByText(/An obtainable market share or customer volume was not available, so SOM was not calculated/i)
    ).toBeInTheDocument();
    expect(screen.queryByText('₹0 Cr')).not.toBeInTheDocument();
  });

  // 7. Market Funnel Rendering
  it('renders MarketFunnel with percentage narrowing and uncalculated indicator', () => {
    const tam: TAMResult = {
      status: 'calculated',
      estimate: 100000000,
      steps: [],
      assumptions_used: [],
      warnings: [],
    };
    const sam: SAMResult = {
      status: 'calculated',
      estimate: 20000000,
      steps: [],
      assumptions_used: [],
      warnings: [],
    };

    render(<MarketFunnel tam={tam} sam={sam} som={null} currency="INR" />);

    expect(screen.getByText(/Market Sizing Funnel/i)).toBeInTheDocument();
    expect(screen.getByText(/20.0% of Total Market/i)).toBeInTheDocument();
    expect(screen.getByText(/Insufficient Evidence/i)).toBeInTheDocument();
  });

  // 8. Methodology Comparison Rendering
  it('renders MethodComparison with divergence severity badge and explanation', () => {
    render(
      <MethodComparison
        comparison={{
          top_down_tam: 100000000,
          bottom_up_tam: 120000000,
          currency: 'INR',
          absolute_difference: 20000000,
          percentage_difference: 20.0,
          relative_ratio: 1.2,
          divergence_severity: 'acceptable',
          explanation: 'Top-down and bottom-up models are within 20% divergence.',
        }}
        currency="INR"
      />
    );

    expect(screen.getByText(/ACCEPTABLE/i)).toBeInTheDocument();
    expect(screen.getByText(/20.0%/i)).toBeInTheDocument();
    expect(screen.getByText(/1.20x/i)).toBeInTheDocument();
    expect(screen.getByText(/Top-down and bottom-up models are within 20% divergence/i)).toBeInTheDocument();
  });

  // 9. Calculation Transparency Audit Steps
  it('renders expandable CalculationTransparency steps', () => {
    const steps = [
      {
        step_number: 1,
        description: 'Compute serviceable students count',
        formula: 'total_students * stem_percentage',
        operands: { total_students: 40000000, stem_percentage: 0.25 },
        result: 10000000,
        unit: 'students',
        evidence_references: ['https://aishe.gov.in'],
        assumptions: [],
        warnings: [],
      },
    ];

    render(<CalculationTransparency steps={steps} />);

    expect(screen.getByText(/Calculation Audit Trail \(1 Steps\)/i)).toBeInTheDocument();
    const expandBtn = screen.getByText(/How was this calculated\?/i);
    fireEvent.click(expandBtn);

    expect(screen.getByText('Compute serviceable students count')).toBeInTheDocument();
    expect(screen.getByText('total_students * stem_percentage')).toBeInTheDocument();
    expect(screen.getByText('https://aishe.gov.in')).toBeInTheDocument();
  });

  // 10. Assumptions Panel
  it('renders AssumptionsPanel distinguishing user assumptions', () => {
    const assumptions = [
      {
        name: 'annual_subscription_fee',
        value: 1200,
        unit: 'INR/yr',
        justification: 'Survey of peer B2C edtech products in India',
        is_user_provided: true,
      },
    ];

    render(<AssumptionsPanel assumptions={assumptions} />);

    expect(screen.getByText('annual subscription fee')).toBeInTheDocument();
    expect(screen.getByText('1,200 INR/yr')).toBeInTheDocument();
    expect(screen.getByText('User Provided')).toBeInTheDocument();
  });

  // 11. Sources & Empirical Evidence Panel
  it('renders SourcesPanel with validation lifecycle badges', () => {
    const validationResults = [
      {
        metric_name: 'college_student_population',
        is_valid: true,
        validation_status: 'valid',
        normalized_value: 41380000,
        unit: 'students',
        source_url: 'https://aishe.gov.in/reports',
        source_name: 'Ministry of Education AISHE Report',
        source_quality_score: 0.95,
        confidence: 'high',
        lifecycle_stage: 'VERIFIED',
        source_context: 'Total enrollment in higher education stands at 41.4 million.',
      },
    ];

    render(<SourcesPanel validationResults={validationResults} />);

    expect(screen.getByText('college student population')).toBeInTheDocument();
    expect(screen.getByText('VERIFIED')).toBeInTheDocument();
    expect(screen.getByText(/Total enrollment in higher education stands at 41.4 million/i)).toBeInTheDocument();
    expect(screen.getByText('Quality: 95%')).toBeInTheDocument();
  });

  // 12. Full Report Panel
  it('renders complete ReportPanel with Executive Summary and Print Button', () => {
    const mockResult: PipelineResult = {
      pipeline_id: 'pipe_test123',
      status: 'completed',
      business_idea: 'Online programming platform for college students in India',
      business_analysis: {
        business_idea: 'Online programming platform for college students in India',
        industry: 'EdTech',
        product: 'Coding Platform',
        target_customer: 'College Students',
        geography: 'India',
        business_model: 'B2C',
        pricing_model: 'Annual Subscription',
        customer_problem: 'High tuition fees',
        value_proposition: 'Affordable hands-on learning',
      },
      research_queries: [],
      discovered_sources: [],
      fetched_sources: [],
      extracted_candidates: [],
      validation_results: [],
      tam: {
        status: 'calculated',
        estimate: 500000000,
        currency: 'INR',
        confidence: 'high',
        steps: [],
        assumptions_used: [],
        warnings: [],
      },
      sam: {
        status: 'calculated',
        estimate: 100000000,
        currency: 'INR',
        confidence: 'medium',
        steps: [],
        assumptions_used: [],
        warnings: [],
      },
      som: {
        status: 'insufficient_evidence',
        estimate: null,
        currency: 'INR',
        confidence: 'low',
        steps: [],
        assumptions_used: [],
        warnings: [],
      },
      confidence: 'medium',
      conflicts: [],
      errors: [],
      warnings: ['SOM could not be calculated due to lack of market share empirical data'],
      audit_trail: [],
      provenance: [],
      started_at: new Date().toISOString(),
    };

    render(<ReportPanel result={mockResult} />);

    expect(screen.getByText(/Complete Market Analysis Report/i)).toBeInTheDocument();
    expect(screen.getByText(/Download \/ Print Report/i)).toBeInTheDocument();
    expect(screen.getByText(/1. Executive Summary/i)).toBeInTheDocument();
    expect(screen.getByText(/2. Business Concept Parameters/i)).toBeInTheDocument();
    expect(screen.getByText(/3. Market Sizing Findings/i)).toBeInTheDocument();
  });

  // 13. Progress and Status Loading UI
  it('renders AnalysisProgress correctly during pipeline execution', () => {
    render(
      <AnalysisProgress
        isLoading={true}
        currentEvent={{
          pipeline_id: 'pipe_progress_1',
          stage: 'extraction',
          status: 'running',
          message: 'Extracting factual numbers from source documents...',
          progress_percent: 60,
          timestamp: new Date().toISOString(),
        }}
      />
    );

    expect(screen.getByText(/Market Sizing Pipeline in Progress/i)).toBeInTheDocument();
    expect(screen.getByText('60%')).toBeInTheDocument();
    expect(screen.getByText(/Extracting factual numbers from source documents/i)).toBeInTheDocument();
  });

  // 14. Competitor & Risk Panels without data fabrication
  it('renders CompetitorPanel and RisksPanel safely when data is unavailable', () => {
    const { rerender } = render(<CompetitorPanel competitors={null} />);
    expect(screen.getByText(/Competitive analysis data is not available in this analysis/i)).toBeInTheDocument();

    rerender(<RisksPanel warnings={['Test market constraint warning']} errors={[]} />);
    expect(screen.getByText('Test market constraint warning')).toBeInTheDocument();
  });

  // 15. MarketAnalysisPage Integration Flow (Success, Error & Reset)
  it('executes full MarketAnalysisPage pipeline lifecycle with mock API', async () => {
    const mockSuccessResult: PipelineResult = {
      pipeline_id: 'pipe_success_99',
      status: 'completed',
      business_idea: 'I want to build an affordable online programming platform for college students in India.',
      business_analysis: {
        business_idea: 'I want to build an affordable online programming platform for college students in India.',
        industry: 'EdTech / Online Education',
        product: 'Affordable online programming platform',
        target_customer: 'College students',
        geography: 'India',
        business_model: 'B2C',
        pricing_model: null,
        customer_problem: 'Need for accessible programming education',
        value_proposition: 'High quality affordable online coding education',
      },
      research_queries: [],
      discovered_sources: [],
      fetched_sources: [],
      extracted_candidates: [],
      validation_results: [],
      calculation_report: {
        calculation_id: 'calc_99',
        status: 'calculated',
        currency: 'INR',
        top_down_tam: {
          status: 'calculated',
          estimate: 4500000000,
          currency: 'INR',
          confidence: 'high',
          steps: [],
          assumptions_used: [],
          warnings: [],
        },
        confidence: 'high',
        all_steps: [],
        all_assumptions: [],
        conflicts: [],
        warnings: [],
      },
      tam: {
        status: 'calculated',
        estimate: 4500000000,
        currency: 'INR',
        confidence: 'high',
        steps: [],
        assumptions_used: [],
        warnings: [],
      },
      sam: {
        status: 'calculated',
        estimate: 900000000,
        currency: 'INR',
        confidence: 'medium',
        steps: [],
        assumptions_used: [],
        warnings: [],
      },
      som: {
        status: 'insufficient_evidence',
        estimate: null,
        currency: 'INR',
        confidence: 'low',
        steps: [],
        assumptions_used: [],
        warnings: ['Missing empirical market share'],
      },
      confidence: 'high',
      conflicts: [],
      errors: [],
      warnings: [],
      audit_trail: [],
      provenance: [],
      started_at: new Date().toISOString(),
    };

    const analyzeSpy = vi.spyOn(apiService, 'analyzeMarket').mockResolvedValue(mockSuccessResult);

    render(<MarketAnalysisPage />);

    // Click preset button
    const presetBtn = screen.getByText('EdTech / India');
    fireEvent.click(presetBtn);

    const textarea = screen.getByPlaceholderText(/I want to build an affordable online programming platform/i) as HTMLTextAreaElement;
    expect(textarea.value).toContain('programming platform');

    // Submit the form
    fireEvent.submit(textarea.closest('form')!);

    await waitFor(() => {
      expect(analyzeSpy).toHaveBeenCalledTimes(1);
    });

    // Check that results rendered across dashboard and report panels
    await waitFor(() => {
      expect(screen.getAllByText('EdTech / Online Education').length).toBeGreaterThanOrEqual(1);
      expect(screen.getAllByText(/₹450 Cr/i).length).toBeGreaterThanOrEqual(1);
      expect(screen.getAllByText(/₹90 Cr/i).length).toBeGreaterThanOrEqual(1);
      expect(screen.getAllByText(/Insufficient Evidence/i).length).toBeGreaterThanOrEqual(1);
    });
  });

  it('handles backend API errors gracefully on MarketAnalysisPage', async () => {
    vi.spyOn(apiService, 'analyzeMarket').mockRejectedValue(
      new Error('Market analysis service is temporarily unavailable. Please verify the AI backend is running.')
    );

    render(<MarketAnalysisPage />);

    const presetBtn = screen.getByText('EdTech / India');
    fireEvent.click(presetBtn);

    const textarea = screen.getByPlaceholderText(/I want to build an affordable online programming platform/i) as HTMLTextAreaElement;
    expect(textarea.value).toContain('programming platform');

    fireEvent.submit(textarea.closest('form')!);

    await waitFor(() => {
      expect(
        screen.getByText(/Market analysis service is temporarily unavailable/i)
      ).toBeInTheDocument();
    });

    // Reset button
    const resetBtn = screen.getByRole('button', { name: /Reset/i });
    fireEvent.click(resetBtn);

    expect(screen.queryByText(/Market analysis service is temporarily unavailable/i)).not.toBeInTheDocument();
  });

  // 16. Defensive SourcesPanel: Null URLs, Null Titles, Null Snippets, and Fetch Failures
  it('renders SourcesPanel safely with null final_url, null title, null snippet, and fetch_failed status', () => {
    const rawSources = [
      {
        source_id: 'src_null_fields',
        url: 'https://example.com/null-test',
        title: null,
        domain: null,
        query: 'market size edtech',
        fetch_status: 'fetch_failed',
        error_message: 'HTTP 403 Forbidden',
        final_url: null,
        content: null,
        snippet: null,
      },
      {
        source_id: 'src_success_partial',
        url: 'https://aishe.gov.in/stats',
        title: 'AISHE 2024 Higher Education',
        domain: 'aishe.gov.in',
        query: 'college student population India',
        fetch_status: 'success',
        final_url: 'https://aishe.gov.in/stats/en',
        content: 'College enrollment data...',
        snippet: null,
      },
    ];

    const validationResults = [
      {
        metric: 'student_count', // note: using metric instead of metric_name
        is_valid: true,
        validation_status: 'valid',
        value: 43000000,
        unit: 'students',
        source_url: null,
        source_name: null,
        source_quality_score: null,
        confidence: 'medium',
        lifecycle_stage: 'VALIDATED',
        source_context: null,
      },
    ];

    render(
      <SourcesPanel
        discoveredSources={rawSources}
        fetchedSources={rawSources}
        validationResults={validationResults as any}
      />
    );

    // Metric should be rendered safely without crashing on replace
    expect(screen.getByText('student count')).toBeInTheDocument();
    expect(screen.getByText('VALIDATED')).toBeInTheDocument();

    // Source audit trail shows fetch_failed and error message safely
    expect(screen.getByText(/Source Fetch Audit Notes/i)).toBeInTheDocument();
    expect(screen.getByText('HTTP 403 Forbidden')).toBeInTheDocument();
  });

  // 17. Defensive ReportPanel: Missing Optional Fields & Fallbacks
  it('renders ReportPanel safely when optional fields, metrics, and justifications are missing or null', () => {
    const minimalResult: PipelineResult = {
      pipeline_id: 'pipe_minimal',
      status: 'completed',
      business_idea: 'B2B SaaS tool',
      business_analysis: {
        business_idea: 'B2B SaaS tool',
        industry: null,
        product: null,
        target_customer: null,
        geography: null,
        business_model: null,
        pricing_model: null,
        customer_problem: null,
        value_proposition: null,
      },
      research_queries: [],
      discovered_sources: [],
      fetched_sources: [],
      extracted_candidates: [],
      validation_results: [
        {
          metric: 'tam_base_market',
          metric_name: undefined,
          is_valid: true,
          validation_status: 'valid',
          normalized_value: 100000000,
          value: 100000000,
          unit: 'INR',
          source_url: null,
          source_name: null,
          lifecycle_stage: 'DISCOVERED',
        } as any,
      ],
      calculation_report: {
        calculation_id: 'calc_min',
        status: 'calculated',
        currency: 'INR',
        confidence: 'low',
        top_down_tam: {
          status: 'calculated',
          estimate: null,
          currency: 'INR',
          confidence: 'low',
          steps: [],
          assumptions_used: [],
          warnings: [],
        },
        method_comparison: {
          top_down_tam: null,
          bottom_up_tam: null,
          currency: 'INR',
          divergence_severity: null,
          explanation: null,
        },
        all_steps: [],
        all_assumptions: [
          {
            name: 'conversion_rate',
            value: 0.05,
            unit: '%',
            justification: null as any,
            is_user_provided: false,
          },
        ],
        conflicts: [],
        warnings: [],
      },
      tam: null,
      sam: null,
      som: null,
      confidence: null as any,
      conflicts: [],
      errors: [],
      warnings: [],
      audit_trail: [],
      provenance: [],
      started_at: null as any,
    };

    render(<ReportPanel result={minimalResult} />);

    expect(screen.getByText(/AI Market Sizing Assessment/i)).toBeInTheDocument();
    expect(screen.getAllByText('Not available').length).toBeGreaterThanOrEqual(4);
    expect(screen.getByText('conversion rate:')).toBeInTheDocument();
    expect(screen.getByText('tam base market:')).toBeInTheDocument();
    expect(screen.getByText(/Unknown Source/i)).toBeInTheDocument();
  });
});
