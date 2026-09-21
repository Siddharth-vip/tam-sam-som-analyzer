import React, { useState } from 'react';
import { Sparkles, Globe, ArrowRight, Lightbulb, Building2, DollarSign, Sliders, Briefcase } from 'lucide-react';
import { PipelineRequest } from '../types/api';

interface Props {
  onSubmit: (request: PipelineRequest) => void;
  isLoading: boolean;
}

const ALL_CATEGORIES = [
  { value: 'HR & Workforce Management', label: 'HR & Workforce Management' },
  { value: 'CRM & Sales', label: 'CRM & Sales' },
  { value: 'Education & Learning Management', label: 'Education & Learning Management (EdTech)' },
  { value: 'Developer Tools', label: 'Developer Tools & DevOps' },
  { value: 'Accounting & Finance', label: 'Accounting & Finance' },
  { value: 'Project & Task Management', label: 'Project & Task Management' },
  { value: 'Marketing & Marketing Automation', label: 'Marketing Automation' },
  { value: 'Customer Support & Helpdesk', label: 'Customer Support & Helpdesk' },
  { value: 'Cybersecurity', label: 'Cybersecurity & Compliance' },
  { value: 'Data & Analytics / Business Intelligence', label: 'Data & Analytics / BI' },
  { value: 'Healthcare Business Software', label: 'Healthcare Business Software' },
  { value: 'Dental Practice Management SaaS', label: 'Dental Practice Management SaaS' },
  { value: 'Clinic Management SaaS', label: 'Clinic Management SaaS' },
  { value: 'Hospital Management SaaS', label: 'Hospital Management SaaS' },
  { value: 'EHR/EMR SaaS', label: 'EHR / EMR SaaS' },
  { value: 'Telemedicine SaaS', label: 'Telemedicine & Virtual Care SaaS' },
  { value: 'Diagnostic Management SaaS', label: 'Diagnostic / Pathology Lab SaaS' },
  { value: 'Medical Billing SaaS', label: 'Medical Billing & RCM SaaS' },
  { value: 'E-commerce & Retail Operations', label: 'E-commerce & Retail Operations' },
  { value: 'Logistics & Transportation Management', label: 'Logistics & Transportation' },
  { value: 'Real Estate & Property Management', label: 'Real Estate & Property' },
  { value: 'Other B2B SaaS', label: 'Other B2B SaaS' },
];

const CUSTOMER_TYPES = [
  { value: 'smb', label: 'Small & Medium Businesses (SMBs)' },
  { value: 'enterprise', label: 'Mid-Market & Large Enterprises' },
  { value: 'startups', label: 'Startups & Fast-Growing Teams' },
  { value: 'college_students', label: 'College Students & Learners' },
  { value: 'software_developers', label: 'Software Developers & Engineers' },
  { value: 'dental_clinics', label: 'Dental Clinics / Practices' },
  { value: 'clinics', label: 'Outpatient Clinics / Poly-clinics' },
  { value: 'hospitals', label: 'Hospitals & Medical Centers' },
  { value: 'diagnostic_laboratories', label: 'Diagnostic / Pathology Laboratories' },
  { value: 'pharmacies', label: 'Retail & Hospital Pharmacies' },
  { value: 'individual_professionals', label: 'Individual Professionals / Consultants' },
  { value: 'other_customers', label: 'Other Target Customers' },
];

const PRESET_IDEAS = [
  {
    title: 'EdTech / India',
    business_name: 'CodeCamp India',
    idea: 'I want to build an affordable online programming platform for college students in India.',
    category: 'Education & Learning Management',
    customer_type: 'college_students',
    country: 'India',
    pricing_basis: 'subscription_annual',
    annual_price: 1200,
    facility_price: '',
  },
  {
    title: 'HR & Payroll / India',
    business_name: 'PayFlow HR',
    idea: 'Cloud-based HR and payroll management platform for small and medium-sized businesses in India.',
    category: 'HR & Workforce Management',
    customer_type: 'smb',
    country: 'India',
    pricing_basis: 'per_user',
    per_user_price: 1500,
    expected_users: 25,
    facility_price: '',
  },
  {
    title: 'Dental SaaS / India',
    business_name: 'DentisFlow India',
    idea: 'Cloud-based dental practice management and digital imaging SaaS for private dental clinics in India.',
    category: 'Dental Practice Management SaaS',
    customer_type: 'dental_clinics',
    country: 'India',
    pricing_basis: 'per_facility',
    facility_price: '36000',
    clinical: 'clinical',
    regulatory: 'ABDM (Ayushman Bharat Digital Mission) compliant',
  },
  {
    title: 'Radiology AI Tele-Diagnostic / India',
    business_name: 'RadAI Cloud',
    idea: 'AI-assisted radiology triaging and PACS cloud reporting SaaS for diagnostic centers and mid-sized hospitals in India.',
    category: 'Diagnostic Management SaaS',
    customer_type: 'diagnostic_laboratories',
    country: 'India',
    pricing_basis: 'subscription_annual',
    annual_price: 180000,
    facility_price: '',
    clinical: 'clinical',
    regulatory: 'NABH / ABDM M2 Interoperability',
  },
  {
    title: 'CRM & Sales / US',
    business_name: 'PipeLead Pro',
    idea: 'AI-powered sales engagement and CRM lead scoring platform for B2B tech startups in the United States.',
    category: 'CRM & Sales',
    customer_type: 'startups',
    country: 'United States',
    pricing_basis: 'subscription_annual',
    annual_price: 48000,
    facility_price: '',
  },
];

export const BusinessIdeaForm: React.FC<Props> = ({ onSubmit, isLoading }) => {
  const [businessName, setBusinessName] = useState('');
  const [businessIdea, setBusinessIdea] = useState('');
  const [category, setCategory] = useState<string>('Auto-detect');
  const [customerType, setCustomerType] = useState<string>('Auto-detect');
  const [targetCountry, setTargetCountry] = useState('India');
  const [targetState, setTargetState] = useState('');
  const [pricingBasis, setPricingBasis] = useState<string>('subscription_annual');
  const [annualPrice, setAnnualPrice] = useState<string>('');
  const [monthlyPrice, setMonthlyPrice] = useState<string>('');
  const [facilityPrice, setFacilityPrice] = useState<string>('');
  const [perUserPrice, setPerUserPrice] = useState<string>('');
  const [expectedUsers, setExpectedUsers] = useState<string>('5');
  const [clinicalUse, setClinicalUse] = useState<string>('non_clinical');
  const [regulatoryMarket, setRegulatoryMarket] = useState('');
  const [emrIntegration, setEmrIntegration] = useState(false);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmedIdea = businessIdea.trim();
    if (!trimmedIdea) {
      setError('Please provide a business idea description.');
      return;
    }
    if (trimmedIdea.length < 3) {
      setError('Please describe your business idea with at least 3 characters.');
      return;
    }

    if (!targetCountry.trim()) {
      setError('Target country is required for accurate market sizing.');
      return;
    }

    setError(null);

    const isHealthcare = category.toLowerCase().includes('health') || category.toLowerCase().includes('clinic') || category.toLowerCase().includes('dental') || category.toLowerCase().includes('hospital') || category.toLowerCase().includes('diagnostic') || category.toLowerCase().includes('ehr') || category.toLowerCase().includes('telemedicine');

    const payload: PipelineRequest = {
      business_idea: trimmedIdea,
      business_name: businessName.trim() || undefined,
      healthcare_saas_category: (category !== 'Auto-detect' && isHealthcare) ? category : undefined,
      customer_type: customerType !== 'Auto-detect' ? customerType : undefined,
      target_country: targetCountry.trim(),
      preferred_geography: targetCountry.trim(),
      preferred_year: 2024,
      target_state_region: targetState.trim() || undefined,
      pricing_basis: pricingBasis,
      annual_subscription_price: annualPrice ? parseFloat(annualPrice) : undefined,
      annual_price: annualPrice ? parseFloat(annualPrice) : undefined,
      monthly_subscription_price: monthlyPrice ? parseFloat(monthlyPrice) : undefined,
      monthly_price: monthlyPrice ? parseFloat(monthlyPrice) : undefined,
      per_facility_price: facilityPrice ? parseFloat(facilityPrice) : undefined,
      per_user_price: perUserPrice ? parseFloat(perUserPrice) : undefined,
      expected_users_per_customer: expectedUsers ? parseInt(expectedUsers, 10) : undefined,
      number_of_employees: expectedUsers ? parseInt(expectedUsers, 10) : undefined,
      clinical_or_non_clinical: clinicalUse,
      clinical_use: clinicalUse === 'clinical' ? true : false,
      regulatory_market: regulatoryMarket.trim() || undefined,
      emr_integration_required: emrIntegration,
      emr_ehr_integration_required: emrIntegration,
      max_sources: 5,
      enable_calculation: true,
    };

    onSubmit(payload);
  };

  const applyPreset = (preset: typeof PRESET_IDEAS[0]) => {
    setBusinessName(preset.business_name || '');
    setBusinessIdea(preset.idea);
    setCategory(preset.category);
    setCustomerType(preset.customer_type);
    setTargetCountry(preset.country);
    setPricingBasis(preset.pricing_basis);
    if (preset.facility_price) setFacilityPrice(preset.facility_price.toString());
    else setFacilityPrice('');
    if (preset.annual_price) setAnnualPrice(preset.annual_price.toString());
    else setAnnualPrice('');
    if ((preset as any).per_user_price) setPerUserPrice((preset as any).per_user_price.toString());
    else setPerUserPrice('');
    if ((preset as any).expected_users) setExpectedUsers((preset as any).expected_users.toString());
    if ((preset as any).clinical) setClinicalUse((preset as any).clinical);
    if ((preset as any).regulatory) setRegulatoryMarket((preset as any).regulatory);
    setError(null);
  };

  return (
    <div className="glass-card" style={{ marginBottom: '2rem' }}>
      <div className="section-header">
        <h2 className="section-title">
          <Briefcase size={20} color="#818cf8" />
          Enter Your Business Idea
        </h2>
        <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
          AI Market Sizing & Strategy Engine
        </span>
      </div>

      <form onSubmit={handleSubmit}>
        {/* Presets */}
        <div style={{ marginBottom: '1.25rem' }}>
          <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '0.35rem', marginBottom: '0.5rem' }}>
            <Lightbulb size={13} color="#f59e0b" /> Select a Scenario Preset:
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
            Business Idea Description & Value Proposition:
          </label>
          <textarea
            id="business-idea-input"
            className="form-textarea"
            placeholder="I want to build an affordable online programming platform for college students in India..."
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
              B2B SaaS Category:
            </label>
            <select
              id="category-select"
              className="form-input"
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              disabled={isLoading}
            >
              <option value="Auto-detect">✨ Auto-Detect from Business Idea</option>
              {ALL_CATEGORIES.map((cat) => (
                <option key={cat.value} value={cat.value}>
                  {cat.label}
                </option>
              ))}
            </select>
          </div>

          <div className="form-group" style={{ marginBottom: 0 }}>
            <label htmlFor="customer-type-select" className="form-label" style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
              <Building2 size={14} color="#34d399" />
              Target Paying Customer:
            </label>
            <select
              id="customer-type-select"
              className="form-input"
              value={customerType}
              onChange={(e) => setCustomerType(e.target.value)}
              disabled={isLoading}
            >
              <option value="Auto-detect">✨ Auto-Detect from Business Idea</option>
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
              onChange={(e) => setPricingBasis(e.target.value)}
              disabled={isLoading}
            >
              <option value="subscription_annual">Annual Subscription per Customer</option>
              <option value="subscription_monthly">Monthly Subscription (12x)</option>
              <option value="per_user">Per User / Seat (Annual)</option>
              <option value="per_facility">Per Facility / Organization (Annual)</option>
              <option value="per_provider">Per Active Professional (Annual)</option>
            </select>
          </div>
        </div>

        {/* Pricing inputs depending on basis */}
        <div className="grid-2" style={{ marginBottom: '1.25rem' }}>
          {pricingBasis === 'per_facility' && (
            <div className="form-group" style={{ marginBottom: 0 }}>
              <label htmlFor="facility-price-input" className="form-label">
                Annual Price per Facility / Organization:
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
                  Annual Price per User / Seat:
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
                  Avg Users / Seats per Customer:
                </label>
                <input
                  id="expected-users-input"
                  type="number"
                  className="form-input"
                  placeholder="e.g. 5"
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
              placeholder="e.g. Acme SaaS"
              value={businessName}
              onChange={(e) => setBusinessName(e.target.value)}
              disabled={isLoading}
            />
          </div>
        </div>

        {/* Toggle Advanced Parameters */}
        <div style={{ marginBottom: '1.25rem' }}>
          <button
            type="button"
            className="btn-secondary"
            onClick={() => setShowAdvanced(!showAdvanced)}
            style={{ fontSize: '0.8rem', padding: '0.35rem 0.75rem', display: 'flex', alignItems: 'center', gap: '0.35rem' }}
          >
            <Sliders size={13} /> {showAdvanced ? 'Hide Advanced Details' : 'Configure Advanced & Compliance Details'}
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
                <label className="form-label">Target State / Region (Optional):</label>
                <input
                  type="text"
                  className="form-input"
                  placeholder="e.g. Tamil Nadu, California, Bavaria"
                  value={targetState}
                  onChange={(e) => setTargetState(e.target.value)}
                  disabled={isLoading}
                />
              </div>

              <div className="form-group">
                <label className="form-label">Regulatory & Compliance Standards (Optional):</label>
                <input
                  type="text"
                  className="form-input"
                  placeholder="e.g. SOC 2, ISO 27001, HIPAA, GDPR, ABDM"
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
                Requires Enterprise API / EMR / Interoperability Integration
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
            {isLoading ? 'Analyzing Market Opportunity...' : 'Analyze Market'}
            <ArrowRight size={16} />
          </button>
        </div>
      </form>
    </div>
  );
};
