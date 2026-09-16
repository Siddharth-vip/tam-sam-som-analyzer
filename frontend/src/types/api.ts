/**
 * TypeScript definitions mapping to the Healthcare SaaS FastAPI backend Pydantic models.
 */

export type PipelineStage =
  | 'received'
  | 'input_validation'
  | 'business_analysis'
  | 'query_generation'
  | 'discovery'
  | 'fetching'
  | 'extraction'
  | 'validation'
  | 'triangulation'
  | 'calculation'
  | 'report_generation'
  | 'completed'
  | 'failed';

export type PipelineStatus =
  | 'pending'
  | 'running'
  | 'completed'
  | 'partial'
  | 'failed'
  | 'insufficient_evidence'
  | 'incomplete_input'
  | 'conflict';

export type EvidenceConfidence = 'low' | 'medium' | 'high' | 'very_high';

export type DivergenceSeverity = 'acceptable' | 'warning' | 'severe_divergence';

export type CalculationStatus =
  | 'calculated'
  | 'insufficient_evidence'
  | 'conflict'
  | 'invalid_input'
  | 'not_calculable'
  | 'execution_failed';

export interface CalculationAssumption {
  name: string;
  value: number;
  unit: string;
  justification: string;
  is_user_provided?: boolean;
}

export interface PipelineRequest {
  business_name?: string | null;
  business_idea: string;
  healthcare_saas_category?: string | null;
  product_description?: string | null;
  primary_problem?: string | null;
  primary_use_case?: string | null;
  key_features?: string[];
  unique_value_proposition?: string | null;
  target_country?: string | null;
  target_state_or_region?: string | null;
  target_city?: string | null;
  target_healthcare_market?: string | null;
  customer_type?: string | null;
  organization_size?: string | null;
  number_of_employees?: number | null;
  number_of_facilities?: number | null;
  target_customer_segment?: string | null;
  business_model?: string | null;
  pricing_model?: string | null;
  monthly_price?: number | null;
  annual_price?: number | null;
  per_user_price?: number | null;
  per_provider_price?: number | null;
  per_facility_price?: number | null;
  currency?: string | null;
  allow_estimated_pricing?: boolean;
  healthcare_domain?: string | null;
  clinical_use?: boolean | null;
  provider_type?: string | null;
  patient_involvement?: boolean | null;
  healthcare_workflow?: string | null;
  emr_ehr_integration_required?: boolean | null;
  interoperability_standards?: string | null;
  regulatory_market?: string | null;
  regulatory_constraints?: string | null;
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
  business_name?: string | null;
  business_idea: string;
  sector?: string | null;
  healthcare_saas_category?: string | null;
  industry?: string | null;
  product?: string | null;
  product_description?: string | null;
  target_country?: string | null;
  target_region?: string | null;
  target_city?: string | null;
  geography?: string | null;
  customer_type?: string | null;
  target_customer?: string | null;
  target_customer_segment?: string | null;
  organization_size?: string | null;
  number_of_facilities?: number | null;
  number_of_employees?: number | null;
  business_model?: string | null;
  pricing_model?: string | null;
  revenue_model?: string | null;
  monthly_price?: number | null;
  annual_price?: number | null;
  per_user_price?: number | null;
  per_provider_price?: number | null;
  per_facility_price?: number | null;
  currency?: string | null;
  annual_revenue_per_customer?: number | null;
  healthcare_domain?: string | null;
  clinical_use?: boolean | null;
  provider_type?: string | null;
  patient_involvement?: boolean | null;
  healthcare_workflow?: string | null;
  emr_ehr_integration_required?: boolean | null;
  interoperability_standards?: string | null;
  regulatory_market?: string | null;
  regulatory_constraints?: string | null;
  primary_problem?: string | null;
  customer_problem?: string | null;
  primary_use_case?: string | null;
  key_features?: string[];
  unique_value_proposition?: string | null;
  value_proposition?: string | null;
  market_category?: string | null;
  market_definition?: string | null;
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
  metric_required: string;
  geography?: string | null;
  year?: number | null;
  industry_topic?: string | null;
  target_population?: string | null;
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
  relevance_score?: number | null;
  is_mock?: boolean;
}

export interface FetchedSource {
  source_id?: string;
  url?: string;
  original_url?: string;
  final_url?: string | null;
  title?: string | null;
  domain?: string | null;
  source_name?: string | null;
  content_type?: string | null;
  http_status_code?: number | null;
  content?: string | null;
}

export interface ExtractedEvidenceCandidate {
  candidate_id?: string;
  metric: string;
  value?: number | null;
  unit?: string | null;
  currency?: string | null;
  year?: number | null;
  geography?: string | null;
  source_url?: string | null;
  source_name?: string | null;
  confidence?: string | null;
}

export interface SourceProvenance {
  source_url: string;
  source_title?: string | null;
  source_name?: string | null;
  domain?: string | null;
  category?: string | null;
  source_quality_tier?: string | null;
  published_year?: number | null;
}

export interface EvidenceValidationResult {
  candidate_id?: string;
  metric?: string;
  value?: number | null;
  unit?: string | null;
  currency?: string | null;
  year?: number | null;
  geography?: string | null;
  source_url?: string;
  source_name?: string | null;
  source_quality_tier?: string | null;
  provenance?: SourceProvenance;
  confidence?: string | null;
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
  serviceable_customer_count?: number | null;
  serviceability_constraints?: string[];
  serviceability_evidence?: string[];
  serviceability_factor?: number | null;
  obtainable_customer_count?: number | null;
  obtainable_percentage_of_sam?: number | null;
  obtainable_percentage_of_tam?: number | null;
  capacity_assumptions?: string[];
  calculation_method?: string | null;
  inputs?: Record<string, any>;
  sam_percentage_of_tam?: number | null;
  som_percentage_of_sam?: number | null;
  som_scenarios?: {
    conservative?: number | null;
    base?: number | null;
    optimistic?: number | null;
  } | null;
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
  divergence_severity?: DivergenceSeverity | null;
  divergence_explanation?: string | null;
  explanation?: string | null;
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
  all_steps: CalculationStep[];
  all_assumptions: CalculationAssumption[];
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

export interface HealthcareMarketAttractiveness {
  rating: 'HIGH' | 'MEDIUM' | 'LOW';
  score: number;
  market_size_appeal: string;
  growth_outlook: string;
  competitive_intensity: string;
  procurement_friction: string;
  regulatory_readiness: string;
  rationale: string;
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
  calculation_trace?: any;
  tam?: TAMResult | null;
  sam?: SAMResult | null;
  som?: SOMResult | null;
  som_scenarios?: {
    conservative?: number | null;
    base?: number | null;
    optimistic?: number | null;
  } | null;
  market_attractiveness?: HealthcareMarketAttractiveness | null;
  confidence: string;
  evidence_quality_rating?: string | null;
  research_provider?: string | null;
  rejected_sources?: DiscoveredSource[];
  rejected_candidates?: ExtractedEvidenceCandidate[];
  competitors?: CompetitorInfo[] | null;
  conflicts: ConflictGroup[];
  final_report_sections?: Record<string, any> | null;
  errors: string[];
  warnings: string[];
  missing_fields?: string[];
  audit_trail: StateTransitionRecord[];
  provenance: SourceProvenance[];
  started_at: string;
  completed_at?: string | null;
}
