/**
 * TypeScript definitions mapping to the B2B SaaS and Healthcare FastAPI backend Pydantic models.
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
  | 'INCOMPLETE_INPUT'
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

export type HealthcareSaaSCategory = string;
export type HealthcareCustomerType = string;
export type HealthcarePricingBasis = string;

export interface CalculationAssumption {
  name?: string;
  metric?: string;
  value: number;
  unit: string;
  justification?: string;
  rationale?: string;
  description?: string;
  is_user_provided?: boolean;
}

export type AssumptionItem = CalculationAssumption;

export interface AssumptionRegistry {
  items: AssumptionItem[];
  total_count?: number;
  user_provided_count?: number;
  high_impact_count?: number;
  model_derived_count?: number;
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
  target_state_region?: string | null;
  target_state_or_region?: string | null;
  target_city?: string | null;
  target_healthcare_market?: string | null;
  customer_type?: string | null;
  organization_size?: string | null;
  number_of_employees?: number | null;
  number_of_facilities?: number | null;
  target_customer_segment?: string | null;
  business_model?: string | null;
  pricing_basis?: string | null;
  pricing_model?: string | null;
  monthly_price?: number | null;
  annual_price?: number | null;
  annual_subscription_price?: number | null;
  monthly_subscription_price?: number | null;
  per_user_price?: number | null;
  per_provider_price?: number | null;
  per_facility_price?: number | null;
  expected_users_per_customer?: number | null;
  currency?: string | null;
  allow_estimated_pricing?: boolean;
  healthcare_domain?: string | null;
  clinical_use?: boolean | null;
  clinical_or_non_clinical?: string | null;
  provider_type?: string | null;
  patient_involvement?: boolean | null;
  healthcare_workflow?: string | null;
  emr_integration_required?: boolean | null;
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

export type ClassificationStatus = 'IN_SCOPE' | 'OUT_OF_SCOPE' | 'AMBIGUOUS';

export interface ClassificationProvenance {
  data_type: string;
  source: string;
  model: string;
  confidence: number;
}

export interface B2BSaaSClassification {
  sector: string;
  classification_status: ClassificationStatus;
  sector_confidence: number;
  category?: string | null;
  category_id?: string | null;
  subcategory?: string | null;
  category_confidence: number;
  business_model: string;
  customer_type: string;
  target_segment?: string | null;
  target_customer?: string | null;
  primary_buyer?: string | null;
  use_cases: string[];
  reasoning: string;
  missing_information?: string[] | null;
  provenance: ClassificationProvenance;
}

export interface BusinessAnalysis {
  business_name?: string | null;
  business_idea: string;
  b2b_saas_classification?: B2BSaaSClassification | null;
  is_b2b_saas?: boolean;
  classification_status?: string | null;
  category?: string | null;
  subcategory?: string | null;
  target_industry?: string | null;
  primary_buyer?: string | null;
  use_cases?: string[];
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
  pricing_basis?: string | null;
  pricing_model?: string | null;
  revenue_model?: string | null;
  monthly_price?: number | null;
  annual_price?: number | null;
  annual_subscription_price?: number | null;
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
  emr_integration_required?: boolean | null;
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
  website?: string | null;
  product_service?: string | null;
  category?: string | null;
  target_market?: string | null;
  target_customers?: string | null;
  geography?: string | null;
  key_features?: string[];
  pricing_model?: string | null;
  pricing?: string | null;
  public_pricing?: string | null;
  deployment_model?: string | null;
  differentiators?: string | null;
  source_url?: string | null;
  source_name?: string | null;
  confidence?: string | null;
}

export interface MarketTrendItem {
  trend: string;
  explanation: string;
  affected_customer_segment?: string | null;
  impact_on_market?: string | null;
  evidence_source?: string | null;
  source_url?: string | null;
  publication_date?: string | null;
  confidence?: string;
}

export interface MarketGrowthItem {
  current_market_size?: number | null;
  historical_market_size?: number | null;
  projected_market_size?: number | null;
  cagr?: number | null;
  cagr_percentage_string?: string | null;
  cagr_type: 'CALCULATED_CAGR' | 'SOURCE_REPORTED_CAGR' | 'INSUFFICIENT_EVIDENCE' | string;
  forecast_period?: string | null;
  geography?: string | null;
  category?: string | null;
  growth_drivers?: string[];
  source_name?: string | null;
  source_url?: string | null;
}

export interface CustomerSegmentItem {
  segment_name: string;
  description: string;
  estimated_population?: number | null;
  population_unit?: string | null;
  business_need?: string | null;
  likely_use_case?: string | null;
  pricing_relevance?: string | null;
  evidence?: string | null;
  confidence?: string;
}

export interface ValuePropositionAnalysis {
  customer_problem: string;
  current_pain_point: string;
  target_customer: string;
  product_solution: string;
  key_capabilities: string[];
  business_benefit: string;
  operational_benefit: string;
  financial_time_saving_benefit?: string | null;
  differentiation_opportunity: string;
  value_proposition_statement: string;
}

export interface BusinessModelAnalysis {
  business_model: string;
  pricing_model: string;
  billing_frequency: string;
  target_customer: string;
  revenue_mechanism: string;
  pricing_unit: string;
  possible_expansion_revenue: string[];
  evidence_source?: string | null;
}

export interface MarketAttractivenessAssessment {
  rating: 'HIGH' | 'MEDIUM' | 'LOW';
  score: number;
  scale?: string;
  market_size_appeal?: string;
  growth_outlook?: string;
  competitive_intensity?: string;
  procurement_friction?: string;
  regulatory_readiness?: string;
  component_factors?: Record<string, any>;
  rationale?: string;
  explanation?: string;
  limitations?: string[];
}

export type HealthcareMarketAttractiveness = MarketAttractivenessAssessment;


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
  query?: string | null;
  relevance_reason?: string | null;
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
  snippet?: string | null;
  query?: string | null;
  fetch_status?: string | null;
  error_message?: string | null;
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
  quality_score?: number | null;
  published_year?: number | null;
}

export interface EvidenceValidationResult {
  candidate_id?: string;
  metric?: string;
  metric_name?: string | null;
  value?: number | null;
  normalized_value?: number | null;
  unit?: string | null;
  currency?: string | null;
  year?: number | null;
  geography?: string | null;
  source_url?: string | null;
  source_name?: string | null;
  source_quality_tier?: string | null;
  source_quality_score?: number | null;
  data_type?: string | null;
  lifecycle_stage?: string | null;
  source_context?: string | null;
  is_valid?: boolean;
  validation_status?: string | null;
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

export interface SOMScenarios {
  conservative?: number | null;
  base?: number | null;
  optimistic?: number | null;
  conservative_som?: number | null;
  base_som?: number | null;
  optimistic_som?: number | null;
  conservative_customers?: number | null;
  base_customers?: number | null;
  optimistic_customers?: number | null;
  conservative_share_pct?: number | null;
  base_share_pct?: number | null;
  optimistic_share_pct?: number | null;
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
  som_scenarios?: SOMScenarios | null;
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
  explanation?: string | null;
  triangulation_confidence?: string | null;
  root_cause_diagnostics?: string[] | null;
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
  conflicts?: any[];
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
  calculation_trace?: any;
  tam?: TAMResult | null;
  sam?: SAMResult | null;
  som?: SOMResult | null;
  som_scenarios?: SOMScenarios | null;
  market_attractiveness?: HealthcareMarketAttractiveness | null;
  confidence: string;
  evidence_quality_rating?: string | null;
  research_provider?: string | null;
  rejected_sources?: DiscoveredSource[];
  rejected_candidates?: ExtractedEvidenceCandidate[];
  competitors?: CompetitorInfo[] | null;
  competitor_comparison?: Record<string, any>[] | null;
  market_trends?: MarketTrendItem[] | null;
  market_growth?: MarketGrowthItem | null;
  customer_segmentation?: CustomerSegmentItem[] | null;
  value_proposition_analysis?: ValuePropositionAnalysis | null;
  business_model_analysis?: BusinessModelAnalysis | null;
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
