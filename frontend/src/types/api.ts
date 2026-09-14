/**
 * TypeScript definitions mapping to the Python FastAPI backend Pydantic models.
 * Strictly adheres to backend schemas without inventing non-existent fields.
 */

export type PipelineStage =
  | 'received'
  | 'business_analysis'
  | 'query_generation'
  | 'discovery'
  | 'fetching'
  | 'extraction'
  | 'validation'
  | 'triangulation'
  | 'calculation'
  | 'completed'
  | 'failed';

export type PipelineStatus =
  | 'pending'
  | 'running'
  | 'completed'
  | 'partial'
  | 'failed'
  | 'insufficient_evidence'
  | 'conflict';

export type EvidenceConfidence = 'low' | 'medium' | 'high' | 'very_high';

export type DivergenceSeverity = 'acceptable' | 'warning' | 'severe_divergence';

export type CalculationStatus =
  | 'calculated'
  | 'insufficient_evidence'
  | 'conflict'
  | 'invalid_input';

export interface CalculationAssumption {
  name: string;
  value: number;
  unit: string;
  justification: string;
  is_user_provided?: boolean;
}

export interface PipelineRequest {
  business_idea: string;
  max_sources?: number;
  enable_calculation?: boolean;
  explicit_assumptions?: CalculationAssumption[];
  preferred_geography?: string | null;
  preferred_year?: number | null;
}

export interface PipelineProgressEvent {
  pipeline_id: string;
  stage: PipelineStage;
  status: PipelineStatus;
  message: string;
  progress_percent: number;
  timestamp: string;
  metadata?: Record<string, any>;
}

export interface BusinessAnalysis {
  business_idea: string;
  industry?: string | null;
  product?: string | null;
  target_customer?: string | null;
  geography?: string | null;
  business_model?: string | null;
  pricing_model?: string | null;
  customer_problem?: string | null;
  value_proposition?: string | null;
}

export interface CompetitorInfo {
  name: string;
  product_service?: string | null;
  target_market?: string | null;
  pricing?: string | null;
  differentiators?: string | null;
  source_url?: string | null;
  source_name?: string | null;
  confidence?: string | null;
}

export interface ResearchQuery {
  query_id?: string;
  query_text: string;
  purpose: string;
  target_metric: string;
  geography?: string | null;
  year?: number | null;
}

export type SourceQualityTier =
  | 'tier_1_government_official'
  | 'tier_2_academic_trade'
  | 'tier_3_analyst_press'
  | 'tier_4_general_unverified';

export type EvidenceQualityRating = 'HIGH' | 'MEDIUM' | 'LOW' | 'INSUFFICIENT';

export interface DiscoveredSource {
  source_id?: string;
  url: string;
  title?: string | null;
  snippet?: string | null;
  source_name?: string | null;
  domain?: string | null;
  category?: string | null;
  source_quality_tier?: string | null;
  query_used?: string | null;
  lifecycle_stage?: string | null;
  published_year?: number | null;
  publication_date?: string | null;
  relevance_score?: number | null;
  is_mock?: boolean;
  relevance_status?: string;
  relevance_reason?: string | null;
}

export interface FetchedSource {
  source_id?: string;
  url?: string;
  original_url?: string;
  final_url?: string | null;
  title?: string | null;
  domain?: string | null;
  source_name?: string | null;
  lifecycle_stage?: string | null;
  content_type?: string | null;
  status_code?: number | null;
  http_status?: number | null;
  content_length?: number | null;
  content_length_bytes?: number | null;
  content?: string | null;
  extracted_text?: string | null;
  fetch_status?: string | null;
  error_message?: string | null;
  is_redirected?: boolean;
  is_cross_domain_redirect?: boolean;
}

export interface ExtractedEvidenceCandidate {
  candidate_id?: string;
  metric?: string;
  metric_name?: string;
  raw_value?: any;
  value?: number | null;
  normalized_value?: number | null;
  unit?: string | null;
  currency?: string | null;
  year?: number | null;
  geography?: string | null;
  source_url?: string;
  source_context?: string | null;
  source_title?: string | null;
  source_name?: string | null;
  confidence?: string | null;
  is_assumption?: boolean;
}

export interface SourceProvenance {
  source_id?: string;
  source_url: string;
  source_title?: string | null;
  source_name?: string | null;
  domain?: string | null;
  category?: string | null;
  source_quality_tier?: string | null;
  is_syndicated_copy?: boolean;
  published_year?: number | null;
  quality_score?: number | null;
  source_quality_score?: number | null;
  lifecycle_stage?: string | null;
}

export interface EvidenceValidationResult {
  candidate_id?: string;
  metric?: string;
  metric_name?: string;
  metric_type?: string | null;
  is_valid?: boolean;
  validation_status?: string;
  value?: number | null;
  normalized_value?: number | null;
  unit?: string | null;
  currency?: string | null;
  year?: number | null;
  geography?: string | null;
  source_url?: string;
  source_context?: string | null;
  source_name?: string | null;
  source_quality_tier?: string | null;
  is_syndicated_copy?: boolean;
  evidence_quality_rating?: string | null;
  source_quality_score?: number | null;
  confidence?: string | null;
  lifecycle_stage?: string | null;
  provenance?: SourceProvenance;
  corroborating_sources?: SourceProvenance[];
  errors?: string[];
  warnings?: string[];
}

export interface ConflictGroup {
  metric_name: string;
  conflicting_values: number[];
  unit: string;
  sources: string[];
  description?: string;
}

export interface TriangulationResult {
  validated_items: EvidenceValidationResult[];
  verified_items: EvidenceValidationResult[];
  duplicate_groups: any[];
  conflict_groups: ConflictGroup[];
  overall_confidence: string;
  warnings: string[];
}

export interface UncertaintyInterval {
  lower?: number | null;
  point?: number | null;
  upper?: number | null;
}

export interface CalculationStep {
  step_number: number;
  description: string;
  formula: string;
  operands: Record<string, any>;
  result?: number | null;
  result_interval?: UncertaintyInterval | null;
  unit: string;
  evidence_references: string[];
  assumptions: string[];
  warnings: string[];
}

export interface MetricCalculationResult {
  status: CalculationStatus;
  estimate?: number | null;
  interval?: UncertaintyInterval | null;
  unit?: string | null;
  currency?: string | null;
  year?: number | null;
  geography?: string | null;
  confidence?: string | null;
  evidence_quality?: string | null;
  evidence_quality_reasons?: string[];
  steps: CalculationStep[];
  assumptions_used: CalculationAssumption[];
  warnings: string[];
  message?: string | null;
}

export type TAMResult = MetricCalculationResult;
export type SAMResult = MetricCalculationResult;
export type SOMResult = MetricCalculationResult;

export interface MethodComparison {
  top_down_tam?: number | null;
  bottom_up_tam?: number | null;
  top_down_estimate?: number | null;
  bottom_up_estimate?: number | null;
  currency?: string | null;
  absolute_difference?: number | null;
  percentage_difference?: number | null;
  relative_ratio?: number | null;
  divergence_severity?: DivergenceSeverity | null;
  divergence_explanation?: string | null;
  triangulation_confidence?: string | null;
  root_cause_diagnostics?: string[];
  sam_comparison?: Record<string, any> | null;
  som_comparison?: Record<string, any> | null;
  explanation?: string | null;
}

export interface AssumptionItem {
  id: string;
  name: string;
  value: number;
  unit: string;
  category: string;
  source_type: string;
  source_reference?: string | null;
  confidence?: string | null;
  justification: string;
  is_user_provided: boolean;
  is_evidence_based: boolean;
  is_model_derived: boolean;
  impact: string;
  affects: string[];
  min_value?: number | null;
  max_value?: number | null;
  uncertainty_status: string;
}

export interface AssumptionRegistry {
  items: AssumptionItem[];
  total_count: number;
  user_provided_count: number;
  model_derived_count: number;
  critical_assumptions_count: number;
  high_impact_count: number;
}

export interface ScenarioEstimate {
  low?: number | null;
  base?: number | null;
  high?: number | null;
  unit?: string | null;
  currency?: string | null;
}

export interface UncertaintyAnalysis {
  status: string;
  tam_scenario?: ScenarioEstimate | null;
  sam_scenario?: ScenarioEstimate | null;
  som_scenario?: ScenarioEstimate | null;
  basis: string;
  explanation: string;
}

export interface SensitivityParameter {
  parameter: string;
  base_value: number;
  unit: string;
  impact: string;
  elasticity: number;
  explanation: string;
}

export interface ReliabilityAssessment {
  level: string;
  reason: string;
  evidence_strength: string;
  assumption_risk: string;
  freshness: string;
  methodology_agreement: string;
  double_counting_risk: boolean;
  geography_consistency: string;
  temporal_consistency: string;
  currency_consistency: string;
}

export interface CalculationReport {
  calculation_id: string;
  status: CalculationStatus;
  target_geography?: string | null;
  target_year?: number | null;
  currency?: string | null;
  top_down_tam?: TAMResult | null;
  top_down_sam?: SAMResult | null;
  top_down_som?: SOMResult | null;
  bottom_up_tam?: TAMResult | null;
  bottom_up_sam?: SAMResult | null;
  bottom_up_som?: SOMResult | null;
  method_comparison?: MethodComparison | null;
  confidence: string;
  evidence_quality?: string | null;
  evidence_quality_reasons?: string[];
  assumption_registry?: AssumptionRegistry | null;
  uncertainty_analysis?: UncertaintyAnalysis | null;
  sensitivity_analysis?: SensitivityParameter[];
  reliability_assessment?: ReliabilityAssessment | null;
  unit_compatibility_warnings?: string[];
  all_steps: CalculationStep[];
  all_assumptions: CalculationAssumption[];
  conflicts: any[];
  warnings: string[];
  message?: string | null;
}

export interface StateTransitionRecord {
  transition_id: string;
  from_state?: string | null;
  to_state: string;
  timestamp: string;
  message?: string | null;
  duration_ms?: number | null;
  error?: string | null;
}

export interface PipelineResult {
  pipeline_id: string;
  status: PipelineStatus;
  business_idea: string;
  business_analysis?: BusinessAnalysis | null;
  research_queries: ResearchQuery[];
  discovered_sources: DiscoveredSource[];
  fetched_sources: FetchedSource[];
  extracted_candidates: ExtractedEvidenceCandidate[];
  validation_results: EvidenceValidationResult[];
  triangulation_result?: TriangulationResult | null;
  calculation_report?: CalculationReport | null;
  tam?: TAMResult | null;
  sam?: SAMResult | null;
  som?: SOMResult | null;
  confidence: string;
  evidence_quality_rating?: string | null;
  research_provider?: string | null;
  rejected_sources?: DiscoveredSource[];
  rejected_candidates?: ExtractedEvidenceCandidate[];
  competitors?: CompetitorInfo[] | null;
  conflicts: ConflictGroup[];
  errors: string[];
  warnings: string[];
  audit_trail: StateTransitionRecord[];
  provenance: SourceProvenance[];
  started_at: string;
  completed_at?: string | null;
}
