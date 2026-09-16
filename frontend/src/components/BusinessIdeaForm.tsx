import React, { useState } from 'react';
import { Sparkles, Globe, Calendar, ArrowRight, Lightbulb, Stethoscope, Building2, DollarSign, ShieldAlert, CheckCircle2, Sliders } from 'lucide-react';
import { PipelineRequest, HealthcareSaaSCategory, HealthcareCustomerType, HealthcarePricingBasis } from '../types/api';

interface Props {
  onSubmit: (request: PipelineRequest) => void;
  isLoading: boolean;
}

const HEALTHCARE_CATEGORIES: { value: HealthcareSaaSCategory; label: string }[] = [
  { value: 'Dental Practice Management SaaS', label: 'Dental Practice Management SaaS' },
  { value: 'Clinic Management SaaS', label: 'Clinic Management SaaS' },
  { value: 'Hospital Management SaaS', label: 'Hospital Management SaaS' },
  { value: 'EHR/EMR SaaS', label: 'EHR / EMR SaaS' },
  { value: 'Telemedicine SaaS', label: 'Telemedicine & Virtual Care SaaS' },
  { value: 'Diagnostic Management SaaS', label: 'Diagnostic / Pathology Lab SaaS' },
  { value: 'Medical Billing SaaS', label: 'Medical Billing & Revenue Cycle SaaS' },
  { value: 'Healthcare Analytics SaaS', label: 'Healthcare Analytics & Clinical AI SaaS' },
  { value: 'Pharmacy Management SaaS', label: 'Pharmacy & Drug Supply Chain SaaS' },
  { value: 'Remote Patient Monitoring SaaS', label: 'Remote Patient Monitoring SaaS' },
  { value: 'Healthcare Workforce SaaS', label: 'Healthcare Workforce & Staffing SaaS' },
  { value: 'Other Healthcare SaaS', label: 'Other Healthcare SaaS' },
];

const CUSTOMER_TYPES: { value: HealthcareCustomerType; label: string }[] = [
  { value: 'dental_clinics', label: 'Dental Clinics / Practices' },
  { value: 'clinics', label: 'Outpatient Clinics / Poly-clinics' },
  { value: 'hospitals', label: 'Hospitals & Medical Centers' },
  { value: 'diagnostic_laboratories', label: 'Diagnostic / Pathology Laboratories' },
  { value: 'pharmacies', label: 'Retail & Hospital Pharmacies' },
  { value: 'telemedicine_providers', label: 'Telemedicine Providers' },
  { value: 'individual_healthcare_professionals', label: 'Individual Doctors / Practitioners' },
  { value: 'healthcare_networks', label: 'Healthcare Networks & Hospital Chains' },
  { value: 'nursing_homes', label: 'Nursing Homes & Long-Term Care' },
  { value: 'insurance_healthcare_organizations', label: 'Payers & Health Insurers' },
  { value: 'patients_consumers', label: 'B2C Patients & Caregivers' },
];

const PRESET_IDEAS = [
  {
    title: 'Dental SaaS / India',
    business_name: 'DentisFlow India',
    idea: 'Cloud-based dental practice management and digital imaging SaaS for private dental clinics in India.',
    category: 'Dental Practice Management SaaS' as HealthcareSaaSCategory,
    customer_type: 'dental_clinics' as HealthcareCustomerType,
    country: 'India',
    pricing_basis: 'per_facility' as HealthcarePricingBasis,
    facility_price: 36000,
    clinical: 'clinical',
    regulatory: 'ABDM (Ayushman Bharat Digital Mission) compliant',
  },
  {
    title: 'Radiology AI Tele-Diagnostic / India',
    business_name: 'RadAI Cloud',
    idea: 'AI-assisted radiology triaging and PACS cloud reporting SaaS for diagnostic centers and mid-sized hospitals in India.',
    category: 'Diagnostic Management SaaS' as HealthcareSaaSCategory,
    customer_type: 'diagnostic_laboratories' as HealthcareCustomerType,
    country: 'India',
    pricing_basis: 'subscription_annual' as HealthcarePricingBasis,
    annual_price: 180000,
    clinical: 'clinical',
    regulatory: 'NABH / ABDM M2 Interoperability',
  },
  {
    title: 'ABDM Clinic EMR / India',
    business_name: 'CareClinic ABDM',
    idea: 'Lightweight, rapid mobile-first EMR and prescription SaaS with WhatsApp patient engagement for single-doctor clinics in India.',
    category: 'Clinic Management SaaS' as HealthcareSaaSCategory,
    customer_type: 'clinics' as HealthcareCustomerType,
    country: 'India',
    pricing_basis: 'per_facility' as HealthcarePricingBasis,
    facility_price: 24000,
    clinical: 'clinical',
    regulatory: 'ABDM M1 & M2 Certified, HIPAA Aligned',
  },
  {
    title: 'Hospital Pharmacy Inventory SaaS / US',
    business_name: 'PharmLogic Pro',
    idea: 'Automated medication inventory, 340B compliance, and drug supply chain management SaaS for community hospitals in the United States.',
    category: 'Pharmacy Management SaaS' as HealthcareSaaSCategory,
    customer_type: 'hospitals' as HealthcareCustomerType,
    country: 'United States',
    pricing_basis: 'per_facility' as HealthcarePricingBasis,
    facility_price: 180000,
    clinical: 'non_clinical',
    regulatory: 'HIPAA & DSCSA Compliant',
  },
];

export const BusinessIdeaForm: React.FC<Props> = ({ onSubmit, isLoading }) => {
  const [businessName, setBusinessName] = useState('');
  const [businessIdea, setBusinessIdea] = useState('');
  const [category, setCategory] = useState<HealthcareSaaSCategory>('Clinic Management SaaS');
  const [customerType, setCustomerType] = useState<HealthcareCustomerType>('clinics');
  const [targetCountry, setTargetCountry] = useState('India');
  const [targetState, setTargetState] = useState('');
  const [pricingBasis, setPricingBasis] = useState<HealthcarePricingBasis>('per_facility');
  const [annualPrice, setAnnualPrice] = useState<string>('');
  const [monthlyPrice, setMonthlyPrice] = useState<string>('');
  const [facilityPrice, setFacilityPrice] = useState<string>('30000');
  const [perUserPrice, setPerUserPrice] = useState<string>('');
  const [expectedUsers, setExpectedUsers] = useState<string>('5');
  const [clinicalUse, setClinicalUse] = useState<string>('clinical');
  const [regulatoryMarket, setRegulatoryMarket] = useState('ABDM / NABH Compliant');
  const [emrIntegration, setEmrIntegration] = useState(true);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmedIdea = businessIdea.trim();
    if (!trimmedIdea) {
      setError('Please provide a Healthcare SaaS business idea description.');
      return;
    }
    if (trimmedIdea.length < 5) {
      setError('Please describe your Healthcare SaaS idea with at least 5 characters.');
      return;
    }

    if (!targetCountry.trim()) {
      setError('Target country is required for accurate Healthcare SaaS market sizing.');
      return;
    }

    setError(null);

    const payload: PipelineRequest = {
      business_idea: trimmedIdea,
      business_name: businessName.trim() || undefined,
      healthcare_saas_category: category,
      customer_type: customerType,
      target_country: targetCountry.trim(),
      target_state_region: targetState.trim() || undefined,
      pricing_basis: pricingBasis,
      annual_subscription_price: annualPrice ? parseFloat(annualPrice) : undefined,
      monthly_subscription_price: monthlyPrice ? parseFloat(monthlyPrice) : undefined,
      per_facility_price: facilityPrice ? parseFloat(facilityPrice) : undefined,
      per_user_price: perUserPrice ? parseFloat(perUserPrice) : undefined,
      expected_users_per_customer: expectedUsers ? parseInt(expectedUsers, 10) : undefined,
      clinical_or_non_clinical: clinicalUse,
      regulatory_market: regulatoryMarket.trim() || undefined,
      emr_integration_required: emrIntegration,
      preferred_geography: targetCountry.trim(),
      max_sources: 5,
      enable_calculation: true,
    };

    onSubmit(payload);
  };

  const applyPreset = (preset: typeof PRESET_IDEAS[0]) => {
    setBusinessName(preset.business_name);
    setBusinessIdea(preset.idea);
    setCategory(preset.category);
    setCustomerType(preset.customer_type);
    setTargetCountry(preset.country);
    setPricingBasis(preset.pricing_basis);
    if (preset.facility_price) setFacilityPrice(preset.facility_price.toString());
    if (preset.annual_price) setAnnualPrice(preset.annual_price.toString());
    setClinicalUse(preset.clinical);
    setRegulatoryMarket(preset.regulatory);
    setError(null);
  };

  return (
    <div className="glass-card" style={{ marginBottom: '2rem' }}>
      <div className="section-header">
        <h2 className="section-title">
          <Stethoscope size={20} color="#06b6d4" />
          Healthcare SaaS Market Analyzer
        </h2>
        <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
          Specialized Healthcare Market Intelligence
        </span>
      </div>

      <form onSubmit={handleSubmit}>
        {/* Presets */}
        <div style={{ marginBottom: '1.25rem' }}>
          <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '0.35rem', marginBottom: '0.5rem' }}>
            <Lightbulb size={13} color="#f59e0b" /> Select a Healthcare SaaS Scenario Preset:
          </span>
          <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
            {PRESET_IDEAS.map((preset, idx) => (
              <button
                key={idx}
                type="button"
                className="btn-secondary"
                style={{ fontSize: '0.8rem', padding: '0.35rem 0.75rem' }}
                onClick={() => applyPreset(preset)}
                disabled={isLoading}
              >
                {preset.title}
              </button>
            ))}
          </div>
        </div>

        {/* Business Idea Core */}
        <div className="form-group">
          <label htmlFor="business-idea-input" className="form-label" style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
            <Sparkles size={14} color="#818cf8" />
            Healthcare SaaS Business Idea & Value Proposition:
          </label>
          <textarea
            id="business-idea-input"
            className="form-textarea"
            placeholder="e.g. Cloud-based dental clinic management SaaS with digital imaging and ABDM compliance for private dental practices in India..."
            value={businessIdea}
            onChange={(e) => {
              setBusinessIdea(e.target.value);
              if (error) setError(null);
            }}
            disabled={isLoading}
            rows={3}
            required
          />
          {error && (
            <p style={{ color: 'var(--accent-rose)', fontSize: '0.85rem', marginTop: '0.4rem' }}>
              {error}
            </p>
          )}
        </div>

        {/* Category & Customer Type */}
        <div className="grid-2" style={{ marginBottom: '1.25rem' }}>
          <div className="form-group" style={{ marginBottom: 0 }}>
            <label htmlFor="category-select" className="form-label">
              Healthcare SaaS Category:
            </label>
            <select
              id="category-select"
              className="form-input"
              value={category}
              onChange={(e) => setCategory(e.target.value as HealthcareSaaSCategory)}
              disabled={isLoading}
            >
              {HEALTHCARE_CATEGORIES.map((cat) => (
                <option key={cat.value} value={cat.value}>
                  {cat.label}
                </option>
              ))}
            </select>
          </div>

          <div className="form-group" style={{ marginBottom: 0 }}>
            <label htmlFor="customer-type-select" className="form-label" style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
              <Building2 size={14} color="#34d399" />
              Target Healthcare Customer:
            </label>
            <select
              id="customer-type-select"
              className="form-input"
              value={customerType}
              onChange={(e) => setCustomerType(e.target.value as HealthcareCustomerType)}
              disabled={isLoading}
            >
              {CUSTOMER_TYPES.map((cust) => (
                <option key={cust.value} value={cust.value}>
                  {cust.label}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Geography & Pricing */}
        <div className="grid-2" style={{ marginBottom: '1.25rem' }}>
          <div className="form-group" style={{ marginBottom: 0 }}>
            <label htmlFor="geography-input" className="form-label" style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
              <Globe size={14} color="#38bdf8" /> Target Country / Geography:
            </label>
            <input
              id="geography-input"
              type="text"
              className="form-input"
              placeholder="e.g. India, United States, Germany"
              value={targetCountry}
              onChange={(e) => setTargetCountry(e.target.value)}
              disabled={isLoading}
              required
            />
          </div>

          <div className="form-group" style={{ marginBottom: 0 }}>
            <label htmlFor="pricing-basis-select" className="form-label" style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
              <DollarSign size={14} color="#f59e0b" /> SaaS Pricing Model:
            </label>
            <select
              id="pricing-basis-select"
              className="form-input"
              value={pricingBasis}
              onChange={(e) => setPricingBasis(e.target.value as HealthcarePricingBasis)}
              disabled={isLoading}
            >
              <option value="per_facility">Per Facility / Practice (Annual)</option>
              <option value="subscription_annual">Annual Subscription per Account</option>
              <option value="subscription_monthly">Monthly Subscription (12x)</option>
              <option value="per_user">Per Provider / User Seat (Annual)</option>
              <option value="per_provider">Per Active Doctor (Annual)</option>
            </select>
          </div>
        </div>

        {/* Pricing inputs depending on basis */}
        <div className="grid-2" style={{ marginBottom: '1.25rem' }}>
          {pricingBasis === 'per_facility' && (
            <div className="form-group" style={{ marginBottom: 0 }}>
              <label htmlFor="facility-price-input" className="form-label">
                Annual Price per Facility / Clinic (in local currency):
              </label>
              <input
                id="facility-price-input"
                type="number"
                className="form-input"
                placeholder="e.g. 36000"
                value={facilityPrice}
                onChange={(e) => setFacilityPrice(e.target.value)}
                disabled={isLoading}
              />
            </div>
          )}

          {pricingBasis === 'subscription_annual' && (
            <div className="form-group" style={{ marginBottom: 0 }}>
              <label htmlFor="annual-price-input" className="form-label">
                Annual Subscription Price:
              </label>
              <input
                id="annual-price-input"
                type="number"
                className="form-input"
                placeholder="e.g. 120000"
                value={annualPrice}
                onChange={(e) => setAnnualPrice(e.target.value)}
                disabled={isLoading}
              />
            </div>
          )}

          {pricingBasis === 'subscription_monthly' && (
            <div className="form-group" style={{ marginBottom: 0 }}>
              <label htmlFor="monthly-price-input" className="form-label">
                Monthly Subscription Price:
              </label>
              <input
                id="monthly-price-input"
                type="number"
                className="form-input"
                placeholder="e.g. 3000"
                value={monthlyPrice}
                onChange={(e) => setMonthlyPrice(e.target.value)}
                disabled={isLoading}
              />
            </div>
          )}

          {(pricingBasis === 'per_user' || pricingBasis === 'per_provider') && (
            <>
              <div className="form-group" style={{ marginBottom: 0 }}>
                <label htmlFor="per-user-price-input" className="form-label">
                  Annual Price per Provider / User:
                </label>
                <input
                  id="per-user-price-input"
                  type="number"
                  className="form-input"
                  placeholder="e.g. 15000"
                  value={perUserPrice}
                  onChange={(e) => setPerUserPrice(e.target.value)}
                  disabled={isLoading}
                />
              </div>
              <div className="form-group" style={{ marginBottom: 0 }}>
                <label htmlFor="expected-users-input" className="form-label">
                  Avg Providers/Users per Facility:
                </label>
                <input
                  id="expected-users-input"
                  type="number"
                  className="form-input"
                  placeholder="e.g. 3"
                  value={expectedUsers}
                  onChange={(e) => setExpectedUsers(e.target.value)}
                  disabled={isLoading}
                />
              </div>
            </>
          )}

          <div className="form-group" style={{ marginBottom: 0 }}>
            <label htmlFor="business-name-input" className="form-label">
              Product / Venture Name (Optional):
            </label>
            <input
              id="business-name-input"
              type="text"
              className="form-input"
              placeholder="e.g. MedVantage SaaS"
              value={businessName}
              onChange={(e) => setBusinessName(e.target.value)}
              disabled={isLoading}
            />
          </div>
        </div>

        {/* Toggle Advanced Healthcare Parameters */}
        <div style={{ marginBottom: '1.25rem' }}>
          <button
            type="button"
            className="btn-secondary"
            onClick={() => setShowAdvanced(!showAdvanced)}
            style={{ fontSize: '0.8rem', padding: '0.35rem 0.75rem', display: 'flex', alignItems: 'center', gap: '0.35rem' }}
          >
            <Sliders size={13} /> {showAdvanced ? 'Hide Clinical & Regulatory Details' : 'Configure Healthcare & Regulatory Details'}
          </button>
        </div>

        {showAdvanced && (
          <div
            style={{
              background: 'rgba(255, 255, 255, 0.02)',
              border: '1px solid rgba(255, 255, 255, 0.07)',
              borderRadius: 'var(--radius-md)',
              padding: '1rem',
              marginBottom: '1.25rem',
            }}
          >
            <div className="grid-2">
              <div className="form-group">
                <label className="form-label">Clinical vs Administrative Workflow:</label>
                <select
                  className="form-input"
                  value={clinicalUse}
                  onChange={(e) => setClinicalUse(e.target.value)}
                  disabled={isLoading}
                >
                  <option value="clinical">Direct Clinical / Diagnostic Workflow</option>
                  <option value="non_clinical">Administrative / Financial / Operations</option>
                  <option value="hybrid">Hybrid (Clinical + Operations)</option>
                </select>
              </div>

              <div className="form-group">
                <label className="form-label">Regulatory & Compliance Standard:</label>
                <input
                  type="text"
                  className="form-input"
                  placeholder="e.g. ABDM / NABH, HIPAA, EU MDR"
                  value={regulatoryMarket}
                  onChange={(e) => setRegulatoryMarket(e.target.value)}
                  disabled={isLoading}
                />
              </div>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginTop: '0.5rem' }}>
              <input
                id="emr-req-check"
                type="checkbox"
                checked={emrIntegration}
                onChange={(e) => setEmrIntegration(e.target.checked)}
                disabled={isLoading}
                style={{ width: '16px', height: '16px', accentColor: 'var(--primary)' }}
              />
              <label htmlFor="emr-req-check" style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', cursor: 'pointer' }}>
                Requires EMR / EHR & Interoperability Integration (HL7 / FHIR / ABDM M1/M2)
              </label>
            </div>
          </div>
        )}

        <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
          <button
            type="submit"
            className="btn-primary"
            disabled={isLoading}
            style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}
          >
            {isLoading ? 'Analyzing Healthcare SaaS Market...' : 'Run Healthcare SaaS Market Analysis'}
            <ArrowRight size={16} />
          </button>
        </div>
      </form>
    </div>
  );
};
