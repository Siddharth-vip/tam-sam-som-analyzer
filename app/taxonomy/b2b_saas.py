import re
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class TaxonomyCategory(BaseModel):
    """Canonical B2B SaaS Taxonomy Category Definition."""

    category_id: str = Field(..., description="Unique slug identifier (e.g. crm_sales).")
    category_name: str = Field(..., description="Canonical human-readable category name.")
    description: str = Field(..., description="Scope and purpose of this B2B SaaS category.")
    typical_use_cases: List[str] = Field(default_factory=list, description="Common workflow use cases.")
    typical_buyers: List[str] = Field(default_factory=list, description="Typical organizational buyers / personas.")
    typical_customer_segments: List[str] = Field(
        default_factory=lambda: ["SMB", "Mid-Market", "Enterprise", "Startups"],
        description="Applicable customer company size tiers.",
    )
    example_products: List[str] = Field(default_factory=list, description="Reference benchmark products.")
    related_subcategories: List[str] = Field(default_factory=list, description="Recognized subcategories.")
    keywords: List[str] = Field(default_factory=list, description="Taxonomy matching keywords.")


B2B_SAAS_TAXONOMY: Dict[str, TaxonomyCategory] = {
    "crm_sales": TaxonomyCategory(
        category_id="crm_sales",
        category_name="CRM & Sales",
        description="Software for managing customer relationships, sales pipelines, lead generation, sales engagement, and revenue operations.",
        typical_use_cases=["Lead Management", "Sales Pipeline Tracking", "Contact Management", "Sales Automation", "Revenue Forecasting"],
        typical_buyers=["VP of Sales", "Chief Revenue Officer (CRO)", "Head of Business Development", "Sales Operations Manager"],
        typical_customer_segments=["SMB", "Mid-Market", "Enterprise", "Startups"],
        example_products=["Salesforce", "HubSpot CRM", "Pipedrive", "Close CRM"],
        related_subcategories=["Sales CRM", "Lead Management", "Sales Engagement", "Revenue Operations", "CPQ (Configure, Price, Quote)"],
        keywords=["crm", "sales", "pipeline", "lead", "leads", "prospect", "prospecting", "deal", "deals", "account executive", "bdr", "sdr", "revops", "cpq"],
    ),
    "hr_workforce": TaxonomyCategory(
        category_id="hr_workforce",
        category_name="HR & Workforce Management",
        description="Software for employee lifecycle management, payroll, attendance, talent acquisition, benefits, and performance tracking.",
        typical_use_cases=["Payroll Processing", "Employee Onboarding", "Applicant Tracking", "Attendance Tracking", "Performance Reviews"],
        typical_buyers=["Chief Human Resources Officer (CHRO)", "Head of People", "HR Manager", "Payroll Administrator"],
        typical_customer_segments=["SMB", "Mid-Market", "Enterprise", "Startups"],
        example_products=["Workday", "Rippling", "Gusto", "BambooHR", "Deel", "Keka"],
        related_subcategories=["HRIS / HRMS", "Payroll Software", "Recruitment / ATS", "Attendance & Time Tracking", "Performance Management", "Employee Engagement"],
        keywords=["hr", "hrms", "hris", "payroll", "workforce", "recruitment", "ats", "applicant tracking", "hiring", "attendance", "employee", "staff", "talent", "benefits"],
    ),
    "accounting_finance": TaxonomyCategory(
        category_id="accounting_finance",
        category_name="Accounting & Finance",
        description="Software for bookkeeping, invoicing, corporate expense management, financial reporting, taxation, and treasury management.",
        typical_use_cases=["Invoicing & Billing", "Corporate Expense Management", "Bookkeeping", "Tax Compliance", "Financial Planning & Analysis (FP&A)"],
        typical_buyers=["Chief Financial Officer (CFO)", "Finance Director", "Controller", "Head of Accounting"],
        typical_customer_segments=["SMB", "Mid-Market", "Enterprise", "Startups"],
        example_products=["QuickBooks", "Xero", "Brex", "Ramp", "Zoho Books", "Anaplan"],
        related_subcategories=["Accounting Software", "Invoicing & Billing", "Expense Management", "FP&A / Financial Planning", "Tax & Compliance"],
        keywords=["accounting", "finance", "invoice", "invoicing", "billing", "bookkeeping", "expense", "expenses", "tax", "gst", "cfo", "ledger", "audit", "treasury", "fpa"],
    ),
    "project_task_management": TaxonomyCategory(
        category_id="project_task_management",
        category_name="Project & Task Management",
        description="Software for team project tracking, agile workflows, sprint planning, task assignment, and portfolio management.",
        typical_use_cases=["Sprint Planning", "Task Assignment", "Milestone Tracking", "Resource Allocation", "Agile / Kanban Boards"],
        typical_buyers=["Head of Project Management", "VP of Engineering", "Operations Manager", "Scrum Master"],
        typical_customer_segments=["SMB", "Mid-Market", "Enterprise", "Startups"],
        example_products=["Asana", "Jira", "Monday.com", "ClickUp", "Linear", "Trello"],
        related_subcategories=["Project Management", "Task Tracking", "Agile / Scrum Tools", "Resource Management", "Product Roadmap Planning"],
        keywords=["project management", "task management", "tasks", "jira", "sprint", "kanban", "scrum", "milestones", "roadmap", "workflow", "work management"],
    ),
    "marketing_automation": TaxonomyCategory(
        category_id="marketing_automation",
        category_name="Marketing & Marketing Automation",
        description="Software for email marketing, campaign automation, social media scheduling, SEO intelligence, and marketing attribution.",
        typical_use_cases=["Email Campaigns", "Marketing Automation", "Content Management", "SEO & Keyword Research", "Ad Tracking & Attribution"],
        typical_buyers=["Chief Marketing Officer (CMO)", "VP of Marketing", "Growth Lead", "Demand Generation Manager"],
        typical_customer_segments=["SMB", "Mid-Market", "Enterprise", "Startups"],
        example_products=["HubSpot Marketing Hub", "Marketo", "Mailchimp", "Semrush", "Klaviyo"],
        related_subcategories=["Email Marketing", "Marketing Automation", "SEO & Content Tools", "Social Media Management", "Ad Optimization & Attribution"],
        keywords=["marketing", "email marketing", "campaign", "seo", "sem", "lead generation", "inbound", "outbound", "newsletter", "attribution", "growth marketing"],
    ),
    "customer_support_helpdesk": TaxonomyCategory(
        category_id="customer_support_helpdesk",
        category_name="Customer Support & Helpdesk",
        description="Software for ticketing, omni-channel customer service, live chat, AI support agents, knowledge bases, and customer success.",
        typical_use_cases=["Ticket Resolution", "Live Chat & Chatbots", "Knowledge Base Management", "Customer Satisfaction (CSAT) Tracking", "Customer Success Monitoring"],
        typical_buyers=["Head of Customer Support", "VP of Customer Experience (CX)", "Customer Success Lead", "Chief Operations Officer (COO)"],
        typical_customer_segments=["SMB", "Mid-Market", "Enterprise", "Startups"],
        example_products=["Zendesk", "Freshdesk", "Intercom", "Gainsight", "Help Scout"],
        related_subcategories=["Helpdesk & Ticketing", "Live Chat & AI Support", "Customer Success Platform", "Knowledge Base SaaS", "Contact Center SaaS"],
        keywords=["customer support", "helpdesk", "ticketing", "support ticket", "customer service", "live chat", "chatbot", "csat", "customer success", "cx"],
    ),
    "erp_operations": TaxonomyCategory(
        category_id="erp_operations",
        category_name="ERP & Business Operations",
        description="Comprehensive enterprise resource planning software connecting inventory, order processing, operations, and enterprise administration.",
        typical_use_cases=["Enterprise Resource Planning", "Order Management", "Operational Workflow Control", "Multi-Entity Management"],
        typical_buyers=["Chief Operating Officer (COO)", "Chief Information Officer (CIO)", "VP of Operations", "IT Director"],
        typical_customer_segments=["Mid-Market", "Enterprise"],
        example_products=["SAP S/4HANA", "Oracle NetSuite", "Microsoft Dynamics 365", "Odoo"],
        related_subcategories=["Cloud ERP", "Enterprise Operations", "Order Management", "Inventory Control"],
        keywords=["erp", "enterprise resource planning", "netsuite", "sap", "business operations", "order management", "multi-entity"],
    ),
    "procurement_supply_chain": TaxonomyCategory(
        category_id="procurement_supply_chain",
        category_name="Procurement & Supply Chain",
        description="Software for vendor management, purchase orders, sourcing, contract negotiation, inventory supply chain, and warehouse operations.",
        typical_use_cases=["Vendor Management", "Purchase Order Approval", "Strategic Sourcing", "Supply Chain Visibility", "Contract Management"],
        typical_buyers=["Chief Procurement Officer (CPO)", "Head of Supply Chain", "Vendor Manager", "Operations Director"],
        typical_customer_segments=["Mid-Market", "Enterprise"],
        example_products=["Coupa", "Ivalua", "SAP Ariba", "Zip", "Flexport"],
        related_subcategories=["Procurement SaaS", "Vendor Management", "Strategic Sourcing", "Supply Chain Management", "Warehouse Management"],
        keywords=["procurement", "supply chain", "vendor management", "purchase order", "sourcing", "supplier", "rfp", "rfq", "warehouse"],
    ),
    "cybersecurity": TaxonomyCategory(
        category_id="cybersecurity",
        category_name="Cybersecurity",
        description="Software for endpoint protection, cloud security, compliance automation (SOC 2, ISO 27001), threat detection, identity and access management.",
        typical_use_cases=["Compliance Automation (SOC 2, ISO)", "Identity & Access Management (IAM)", "Vulnerability Scanning", "Threat Detection & Response", "Cloud Security Posture"],
        typical_buyers=["Chief Information Security Officer (CISO)", "Head of Security", "Security Operations Manager", "IT Director"],
        typical_customer_segments=["SMB", "Mid-Market", "Enterprise", "Startups"],
        example_products=["Vanta", "Drata", "CrowdStrike", "Okta", "Palo Alto Networks", "Wiz"],
        related_subcategories=["Security Compliance SaaS", "Identity & Access Management (IAM)", "Cloud Security (CSPM)", "Threat Detection & SIEM", "Endpoint Security"],
        keywords=["cybersecurity", "security", "soc 2", "iso 27001", "hipaa compliance", "iam", "vulnerability", "threat detection", "ciso", "cloud security", "infosec"],
    ),
    "it_management_itsm": TaxonomyCategory(
        category_id="it_management_itsm",
        category_name="IT Management & IT Service Management",
        description="Software for IT asset management, device management (MDM), network monitoring, service desk, and internal IT infrastructure control.",
        typical_use_cases=["IT Asset Management", "Mobile Device Management (MDM)", "IT Service Desk", "Network & Infrastructure Monitoring", "Software License Management"],
        typical_buyers=["VP of IT", "IT Director", "System Administrator", "Head of IT Operations"],
        typical_customer_segments=["Mid-Market", "Enterprise", "SMB"],
        example_products=["ServiceNow", "Jira Service Management", "Datadog", "Jamf", "Kandji"],
        related_subcategories=["ITSM / IT Service Desk", "IT Asset Management (ITAM)", "Mobile Device Management (MDM)", "Network Monitoring", "SaaS Management Platform (SMP)"],
        keywords=["it management", "itsm", "it service desk", "itam", "mdm", "device management", "sysadmin", "infrastructure monitoring", "servicenow"],
    ),
    "collaboration_communication": TaxonomyCategory(
        category_id="collaboration_communication",
        category_name="Collaboration & Communication",
        description="Software for enterprise team messaging, video conferencing, internal documentation, team intranets, and asynchronous collaboration.",
        typical_use_cases=["Team Messaging", "Video Meetings", "Internal Knowledge Sharing", "Document Co-authoring", "Asynchronous Video"],
        typical_buyers=["Chief Information Officer (CIO)", "Head of Operations", "People Operations", "IT Director"],
        typical_customer_segments=["SMB", "Mid-Market", "Enterprise", "Startups"],
        example_products=["Slack", "Microsoft Teams", "Zoom", "Notion", "Miro", "Loom"],
        related_subcategories=["Team Messaging", "Video Conferencing", "Team Workspace & Wiki", "Virtual Whiteboarding", "Asynchronous Collaboration"],
        keywords=["collaboration", "communication", "messaging", "chat", "video conferencing", "wiki", "intranet", "whiteboard", "team workspace"],
    ),
    "legal_compliance": TaxonomyCategory(
        category_id="legal_compliance",
        category_name="Legal & Compliance",
        description="Software for contract lifecycle management (CLM), legal document automation, intellectual property management, and regulatory compliance.",
        typical_use_cases=["Contract Lifecycle Management (CLM)", "e-Signature & Approval", "Legal Matter Management", "Regulatory Tracking", "Privacy & GDPR Compliance"],
        typical_buyers=["General Counsel", "Chief Legal Officer (CLO)", "Head of Compliance", "Legal Operations Director"],
        typical_customer_segments=["Mid-Market", "Enterprise", "SMB"],
        example_products=["Ironclad", "DocuSign", "OneTrust", "ContractPodAi", "Clio"],
        related_subcategories=["Contract Lifecycle Management (CLM)", "e-Signature & Document Verification", "Legal Practice Management", "Privacy & Regulatory SaaS", "IP Management"],
        keywords=["legal", "compliance", "contract", "contracts", "clm", "e-signature", "gdpr", "law firm", "general counsel", "regulatory compliance"],
    ),
    "data_analytics_bi": TaxonomyCategory(
        category_id="data_analytics_bi",
        category_name="Data & Analytics / Business Intelligence",
        description="Software for data visualization, dashboarding, business intelligence, data pipeline integration, customer data platforms (CDP), and predictive analytics.",
        typical_use_cases=["Executive Dashboards", "Data Pipeline / ETL", "Customer Data Platform (CDP)", "Product Analytics", "Predictive Forecasting"],
        typical_buyers=["Head of Data", "Chief Analytics Officer (CAO)", "VP of BI", "Director of Product Analytics"],
        typical_customer_segments=["SMB", "Mid-Market", "Enterprise", "Startups"],
        example_products=["Tableau", "Power BI", "Snowflake", "Fivetran", "Mixpanel", "Segment"],
        related_subcategories=["Business Intelligence & Dashboards", "Data Pipelines / ETL SaaS", "Product Analytics", "Customer Data Platform (CDP)", "AI Analytics"],
        keywords=["data", "analytics", "bi", "business intelligence", "dashboard", "reporting", "etl", "cdp", "data warehouse", "visualization", "metrics"],
    ),
    "developer_tools": TaxonomyCategory(
        category_id="developer_tools",
        category_name="Developer Tools",
        description="Software for software engineering workflows, CI/CD, code repositories, API management, bug tracking, testing, and cloud infrastructure.",
        typical_use_cases=["Code Repository & Version Control", "Continuous Integration / CD", "Error Monitoring & Logging", "API Testing & Management", "Cloud Infrastructure Provisioning"],
        typical_buyers=["Chief Technology Officer (CTO)", "VP of Engineering", "Engineering Manager", "DevOps Lead"],
        typical_customer_segments=["Startups", "SMB", "Mid-Market", "Enterprise"],
        example_products=["GitHub", "GitLab", "Postman", "Sentry", "Datadog", "HashiCorp"],
        related_subcategories=["CI/CD & DevOps SaaS", "API Development & Testing", "Observability & Error Tracking", "Cloud Hosting & Deployment", "Code Review & Quality"],
        keywords=["developer tools", "devtools", "devops", "ci/cd", "api", "git", "github", "testing", "monitoring", "logging", "observability", "engineering"],
    ),
    "productivity_workflow_automation": TaxonomyCategory(
        category_id="productivity_workflow_automation",
        category_name="Productivity & Workflow Automation",
        description="Software for no-code automation, document processing, AI productivity workflows, scheduling, and repetitive business task elimination.",
        typical_use_cases=["No-Code Workflow Automation", "AI Document Summarization", "Calendar Scheduling", "Form Automation", "Robotic Process Automation (RPA)"],
        typical_buyers=["Head of Operations", "IT Manager", "Department Lead", "Chief Digital Officer"],
        typical_customer_segments=["SMB", "Mid-Market", "Enterprise", "Startups"],
        example_products=["Zapier", "Make.com", "Calendly", "UiPath", "Airtable"],
        related_subcategories=["iPaaS / Workflow Automation", "AI Productivity Tools", "Appointment Scheduling", "No-Code Database SaaS", "Document Automation"],
        keywords=["automation", "productivity", "workflow", "zapier", "scheduling", "no-code", "low-code", "rpa", "document processing"],
    ),
    "ecommerce_retail_operations": TaxonomyCategory(
        category_id="ecommerce_retail_operations",
        category_name="E-commerce & Retail Operations",
        description="Software for online store management, multichannel inventory, order fulfillment, shipping automation, POS systems, and return management.",
        typical_use_cases=["Multichannel Inventory Sync", "Order Fulfillment", "Shipping Label Automation", "Point of Sale (POS)", "Returns Management"],
        typical_buyers=["Head of E-commerce", "Retail Operations Director", "Store Manager", "Chief Commercial Officer"],
        typical_customer_segments=["SMB", "Mid-Market", "Enterprise"],
        example_products=["Shopify Plus", "ShipStation", "Cin7", "Loop Returns", "Square for Retail"],
        related_subcategories=["Multichannel Inventory SaaS", "Shipping & Fulfillment SaaS", "Retail POS SaaS", "E-commerce Operations", "Returns & Logistics SaaS"],
        keywords=["ecommerce", "e-commerce", "retail", "pos", "point of sale", "order fulfillment", "inventory sync", "shipping automation", "shopify", "store"],
    ),
    "education_learning_management": TaxonomyCategory(
        category_id="education_learning_management",
        category_name="Education & Learning Management",
        description="Software for corporate learning (LMS), employee skill development, school administration, online training delivery, and course compliance.",
        typical_use_cases=["Corporate Training & LMS", "Employee Compliance Certification", "School Management System", "Course Creation & Delivery"],
        typical_buyers=["Head of L&D (Learning & Development)", "Chief HR Officer", "School Principal", "University Administrator"],
        typical_customer_segments=["SMB", "Mid-Market", "Enterprise", "Educational Institutions"],
        example_products=["Docebo", "Cornerstone OnDemand", "Canvas LMS", "TalentLMS", "Coursera for Business"],
        related_subcategories=["Corporate LMS", "Higher Ed LMS", "K-12 School Management", "Course Authoring & Training", "Skills Assessment SaaS", "Student Information System (SIS)"],
        keywords=["education", "learning management", "lms", "corporate training", "e-learning", "skills development", "training", "school management", "school administration", "student management", "student", "school", "college", "edtech", "course"],
    ),
    "healthcare_business_software": TaxonomyCategory(
        category_id="healthcare_business_software",
        category_name="Healthcare Business Software",
        description="Software for clinic management, hospital administration (HIMS), electronic medical records (EMR/EHR), medical billing, telehealth, and practice workflows.",
        typical_use_cases=["Clinic / Practice Management", "Hospital Information Systems (HIMS)", "EMR / EHR Charting", "Medical Billing & RCM", "Telehealth Platform"],
        typical_buyers=["Clinic Owner / Doctor", "Hospital Medical Director", "Chief Medical Officer", "Practice Manager", "Healthcare Administrator"],
        typical_customer_segments=["Private Clinics", "Hospitals", "Diagnostic Labs", "Pharmacies", "Healthcare Networks"],
        example_products=["Epic", "Cerner", "Kareo", "Athenahealth", "Practo", "Clinicia"],
        related_subcategories=["Practice Management SaaS", "Dental Practice Management SaaS", "Clinic Management SaaS", "Hospital Management (HIMS)", "EHR / EMR SaaS", "Medical Billing & RCM", "Telemedicine SaaS", "Diagnostic Lab Management", "Patient Management SaaS"],
        keywords=["healthcare", "clinic", "hospital", "emr", "ehr", "hims", "telehealth", "telemedicine", "medical billing", "practice management", "dental", "dental practice", "diagnostic lab", "doctor", "physician", "patient", "patient management", "appointment", "clinic appointment"],
    ),
    "real_estate_property_management": TaxonomyCategory(
        category_id="real_estate_property_management",
        category_name="Real Estate & Property Management",
        description="Software for property leasing, tenant communication, rent collection, facility maintenance, real estate CRM, and commercial asset management.",
        typical_use_cases=["Tenant Lease Management", "Rent Collection & Invoicing", "Maintenance Work Orders", "Commercial Property Management", "Real Estate CRM"],
        typical_buyers=["Property Manager", "Real Estate Developer", "Asset Manager", "Landlord / Leasing Agent"],
        typical_customer_segments=["Property Management Firms", "Real Estate Agencies", "Commercial Landlords"],
        example_products=["AppFolio", "Buildium", "Yardi", "CoStar", "Entrata"],
        related_subcategories=["Residential Property Management", "Commercial Real Estate SaaS", "Tenant Portal & Lease SaaS", "Real Estate CRM"],
        keywords=["real estate", "property management", "tenant", "landlord", "leasing", "rent collection", "facility maintenance", "commercial real estate"],
    ),
    "construction_field_service": TaxonomyCategory(
        category_id="construction_field_service",
        category_name="Construction & Field Service Management",
        description="Software for job site management, subcontractor coordination, field worker dispatching, work order tracking, and equipment maintenance.",
        typical_use_cases=["Jobsite Scheduling", "Subcontractor Coordination", "Field Technician Dispatch", "Work Order Management", "Safety & Inspection Auditing"],
        typical_buyers=["General Contractor", "VP of Field Operations", "Service Manager", "Construction Project Manager"],
        typical_customer_segments=["Contractors", "Field Service Providers", "Construction Firms"],
        example_products=["Procore", "ServiceTitan", "Jobber", "Fieldwire", "Housecall Pro"],
        related_subcategories=["Construction Management SaaS", "Field Service Management (FSM)", "Dispatch & Work Order SaaS", "Safety Inspection SaaS"],
        keywords=["construction", "field service", "contractor", "subcontractor", "dispatch", "work order", "hvac", "plumbing", "jobsite", "technician"],
    ),
    "logistics_transportation": TaxonomyCategory(
        category_id="logistics_transportation",
        category_name="Logistics & Transportation Management",
        description="Software for freight management (TMS), fleet tracking, route optimization, carrier dispatch, third-party logistics (3PL), and warehouse logistics.",
        typical_use_cases=["Fleet Route Optimization", "Transportation Management (TMS)", "Freight Brokerage & Dispatch", "Carrier Rate Management", "3PL Warehouse Logistics"],
        typical_buyers=["Fleet Manager", "VP of Logistics", "Transportation Director", "Supply Chain Lead"],
        typical_customer_segments=["Logistics Providers", "Trucking Companies", "3PLs", "Shippers"],
        example_products=["Samsara", "project44", "FourKites", "Descartes", "Turvo"],
        related_subcategories=["Transportation Management System (TMS)", "Fleet Management & Telematics", "Route Optimization SaaS", "3PL Logistics Platform"],
        keywords=["logistics", "transportation", "tms", "fleet", "freight", "trucking", "route optimization", "carrier", "3pl", "dispatch"],
    ),
    "fintech_saas": TaxonomyCategory(
        category_id="fintech_saas",
        category_name="FinTech & Payment SaaS",
        description="Software for B2B payment processing, invoice financing, billing gateways, treasury operations, subscription billing, and banking integrations.",
        typical_use_cases=["B2B Payment Gateway", "Invoice Factoring / Financing", "Subscription Billing Automation", "Corporate Treasury Management", "Banking API Integration"],
        typical_buyers=["Chief Financial Officer (CFO)", "VP of Finance", "Head of Payments", "Treasury Director"],
        typical_customer_segments=["SMB", "Mid-Market", "Enterprise", "Startups"],
        example_products=["Stripe", "Razorpay", "Chargebee", "Plaid", "Brex", "Kyriba"],
        related_subcategories=["B2B Payment SaaS", "Subscription Billing SaaS", "Invoice Financing SaaS", "Corporate Treasury SaaS", "Embedded Banking SaaS"],
        keywords=["fintech", "payment", "payments", "invoice financing", "receivables", "treasury", "gateway", "subscription billing", "billing automation", "banking api"],
    ),
    "manufacturing_operations": TaxonomyCategory(
        category_id="manufacturing_operations",
        category_name="Manufacturing & Industrial Operations",
        description="Software for manufacturing execution systems (MES), plant floor control, equipment maintenance (CMMS), quality assurance, and industrial IoT monitoring.",
        typical_use_cases=["Manufacturing Execution (MES)", "Computerized Maintenance Management (CMMS)", "Quality Control & Assurance", "Plant Floor Scheduling", "Industrial IoT Telemetry"],
        typical_buyers=["VP of Manufacturing", "Plant Manager", "Head of Operations", "Quality Assurance Director"],
        typical_customer_segments=["Mid-Market", "Enterprise", "Industrial SMBs"],
        example_products=["Plex Systems", "Tulip", "MaintainX", "UpKeep", "Siemens Opcenter"],
        related_subcategories=["MES SaaS", "CMMS / Maintenance SaaS", "Plant Floor Management", "Quality Assurance SaaS", "Industrial IoT SaaS"],
        keywords=["manufacturing", "plant floor", "mes", "cmms", "industrial", "factory", "machinery maintenance", "quality control", "oee", "shop floor"],
    ),
    "hospitality_restaurant": TaxonomyCategory(
        category_id="hospitality_restaurant",
        category_name="Hospitality & Restaurant Management",
        description="Software for hotel property management (PMS), restaurant POS, kitchen display systems, table reservation, guest management, and food delivery integration.",
        typical_use_cases=["Restaurant POS & Ordering", "Hotel Property Management (PMS)", "Table Reservation Management", "Kitchen Display & Routing", "Guest Loyalty & CRM"],
        typical_buyers=["Restaurant Owner", "General Manager", "Food & Beverage Director", "Hotel Operations Director"],
        typical_customer_segments=["Restaurants", "Cafes", "Hotels", "Resorts", "Hospitality Groups"],
        example_products=["Toast", "Cloudbeds", "SevenRooms", "TouchBistro", "Mews", "Petpooja"],
        related_subcategories=["Restaurant Management SaaS", "Hotel PMS SaaS", "Table Booking SaaS", "Kitchen Display SaaS", "Bar & Food POS"],
        keywords=["hospitality", "restaurant", "hotel", "pms", "table booking", "kitchen display", "food and beverage", "bar pos", "resort management", "guest management"],
    ),
    "vertical_saas": TaxonomyCategory(
        category_id="vertical_saas",
        category_name="Industry-Specific Vertical SaaS",
        description="Specialized software tailored to the unique workflows of a specific industry vertical (e.g. legal, salons, fitness studios, agriculture).",
        typical_use_cases=["Industry-Specific Workflow", "Specialized Billing & Booking", "Vertical Regulatory Compliance"],
        typical_buyers=["Industry Business Owner", "General Manager", "Managing Partner"],
        typical_customer_segments=["Vertical SMBs", "Specialized Enterprises"],
        example_products=["Toast (Restaurants)", "Mindbody (Fitness/Salons)", "Clio (Legal)", "Veeva (Life Sciences)"],
        related_subcategories=["Restaurant SaaS", "Salon & Spa Management", "Agriculture / AgriTech SaaS", "Hospitality Management"],
        keywords=["vertical saas", "salon", "fitness studio", "agritech", "agriculture", "specialized saas"],
    ),
    "other_b2b_saas": TaxonomyCategory(
        category_id="other_b2b_saas",
        category_name="Other B2B SaaS",
        description="Other specialized or emerging business-to-business software as a service platform.",
        typical_use_cases=["B2B Workflow Automation", "Specialized Business Solutions"],
        typical_buyers=["Business Executive", "Department Head"],
        typical_customer_segments=["SMB", "Mid-Market", "Enterprise"],
        example_products=["Custom B2B SaaS"],
        related_subcategories=["General B2B SaaS", "Custom Enterprise SaaS"],
        keywords=["b2b saas", "software as a service", "enterprise software", "b2b software"],
    ),
}

# Synonym and alias dictionary mapping common variations to canonical category IDs
CATEGORY_SYNONYM_MAP: Dict[str, str] = {
    # CRM & Sales
    "crm": "crm_sales",
    "sales": "crm_sales",
    "sales crm": "crm_sales",
    "sales automation": "crm_sales",
    "lead management": "crm_sales",
    "customer relationship management": "crm_sales",
    "revenue operations": "crm_sales",
    "revops": "crm_sales",
    "sales engagement": "crm_sales",
    "cpq": "crm_sales",
    "sales platform": "crm_sales",
    "crm saas": "crm_sales",
    "crm & sales": "crm_sales",

    # HR & Workforce
    "hr": "hr_workforce",
    "human resources": "hr_workforce",
    "hr software": "hr_workforce",
    "hrms": "hr_workforce",
    "hris": "hr_workforce",
    "payroll": "hr_workforce",
    "payroll software": "hr_workforce",
    "workforce management": "hr_workforce",
    "recruitment": "hr_workforce",
    "ats": "hr_workforce",
    "applicant tracking": "hr_workforce",
    "applicant tracking system": "hr_workforce",
    "talent acquisition": "hr_workforce",
    "attendance": "hr_workforce",
    "employee management": "hr_workforce",
    "hr & workforce management": "hr_workforce",

    # Accounting & Finance
    "accounting": "accounting_finance",
    "finance": "accounting_finance",
    "invoicing": "accounting_finance",
    "billing": "accounting_finance",
    "expense management": "accounting_finance",
    "bookkeeping": "accounting_finance",
    "fp&a": "accounting_finance",
    "financial planning": "accounting_finance",
    "tax software": "accounting_finance",
    "accounting & finance": "accounting_finance",
    "fintech b2b": "accounting_finance",
    "corporate finance": "accounting_finance",

    # Project & Task Management
    "project management": "project_task_management",
    "task management": "project_task_management",
    "project & task management": "project_task_management",
    "project tracking": "project_task_management",
    "agile": "project_task_management",
    "kanban": "project_task_management",
    "scrum": "project_task_management",
    "work management": "project_task_management",

    # Marketing Automation
    "marketing": "marketing_automation",
    "marketing automation": "marketing_automation",
    "marketing & marketing automation": "marketing_automation",
    "email marketing": "marketing_automation",
    "seo": "marketing_automation",
    "social media management": "marketing_automation",
    "content marketing": "marketing_automation",

    # Customer Support & Helpdesk
    "customer support": "customer_support_helpdesk",
    "helpdesk": "customer_support_helpdesk",
    "customer support & helpdesk": "customer_support_helpdesk",
    "ticketing": "customer_support_helpdesk",
    "customer service": "customer_support_helpdesk",
    "customer success": "customer_support_helpdesk",
    "live chat": "customer_support_helpdesk",

    # ERP
    "erp": "erp_operations",
    "enterprise resource planning": "erp_operations",
    "erp & business operations": "erp_operations",
    "business operations": "erp_operations",
    "operations management": "erp_operations",

    # Procurement & Supply Chain
    "procurement": "procurement_supply_chain",
    "supply chain": "procurement_supply_chain",
    "procurement & supply chain": "procurement_supply_chain",
    "vendor management": "procurement_supply_chain",
    "sourcing": "procurement_supply_chain",

    # Cybersecurity
    "cybersecurity": "cybersecurity",
    "security": "cybersecurity",
    "information security": "cybersecurity",
    "infosec": "cybersecurity",
    "soc 2": "cybersecurity",
    "soc 2 compliance": "cybersecurity",
    "soc2 compliance": "cybersecurity",
    "cloud security": "cybersecurity",
    "compliance security": "cybersecurity",

    # IT Management / ITSM
    "it management": "it_management_itsm",
    "itsm": "it_management_itsm",
    "it service management": "it_management_itsm",
    "it management & it service management": "it_management_itsm",
    "it asset management": "it_management_itsm",
    "mdm": "it_management_itsm",

    # Collaboration & Communication
    "collaboration": "collaboration_communication",
    "communication": "collaboration_communication",
    "collaboration & communication": "collaboration_communication",
    "team messaging": "collaboration_communication",
    "video conferencing": "collaboration_communication",

    # Legal & Compliance
    "legal": "legal_compliance",
    "compliance": "legal_compliance",
    "legal & compliance": "legal_compliance",
    "contract management": "legal_compliance",
    "clm": "legal_compliance",

    # Data Analytics & BI
    "data & analytics": "data_analytics_bi",
    "analytics": "data_analytics_bi",
    "bi": "data_analytics_bi",
    "business intelligence": "data_analytics_bi",
    "data & analytics / business intelligence": "data_analytics_bi",
    "data pipeline": "data_analytics_bi",

    # Developer Tools
    "developer tools": "developer_tools",
    "devtools": "developer_tools",
    "devops": "developer_tools",
    "software engineering tools": "developer_tools",
    "ci/cd": "developer_tools",

    # Productivity & Workflow Automation
    "productivity": "productivity_workflow_automation",
    "workflow automation": "productivity_workflow_automation",
    "productivity & workflow automation": "productivity_workflow_automation",
    "no-code automation": "productivity_workflow_automation",

    # E-commerce & Retail Operations
    "e-commerce": "ecommerce_retail_operations",
    "ecommerce": "ecommerce_retail_operations",
    "retail operations": "ecommerce_retail_operations",
    "e-commerce & retail operations": "ecommerce_retail_operations",
    "pos": "ecommerce_retail_operations",
    "inventory management": "ecommerce_retail_operations",

    # Education & LMS
    "education": "education_learning_management",
    "lms": "education_learning_management",
    "learning management": "education_learning_management",
    "education & learning management": "education_learning_management",
    "corporate training": "education_learning_management",

    # Healthcare Business Software
    "healthcare": "healthcare_business_software",
    "healthcare saas": "healthcare_business_software",
    "healthcare business software": "healthcare_business_software",
    "clinic management": "healthcare_business_software",
    "clinic management saas": "healthcare_business_software",
    "hospital management": "healthcare_business_software",
    "hospital management saas": "healthcare_business_software",
    "ehr/emr": "healthcare_business_software",
    "ehr/emr saas": "healthcare_business_software",
    "telemedicine saas": "healthcare_business_software",
    "practice management": "healthcare_business_software",
    "dental practice management saas": "healthcare_business_software",

    # Real Estate
    "real estate": "real_estate_property_management",
    "property management": "real_estate_property_management",
    "real estate & property management": "real_estate_property_management",

    # Construction & Field Service
    "construction": "construction_field_service",
    "field service": "construction_field_service",
    "construction & field service management": "construction_field_service",
    "field service management": "construction_field_service",

    # Logistics & Transportation
    "logistics": "logistics_transportation",
    "transportation": "logistics_transportation",
    "logistics & transportation management": "logistics_transportation",
    "fleet management": "logistics_transportation",
    "tms": "logistics_transportation",

    # FinTech & Payment SaaS
    "fintech": "fintech_saas",
    "fintech saas": "fintech_saas",
    "fintech & payment saas": "fintech_saas",
    "payment gateway": "fintech_saas",
    "invoice financing": "fintech_saas",
    "treasury management": "fintech_saas",
    "subscription billing": "fintech_saas",

    # Manufacturing & Industrial Operations
    "manufacturing": "manufacturing_operations",
    "manufacturing saas": "manufacturing_operations",
    "manufacturing & industrial operations": "manufacturing_operations",
    "mes": "manufacturing_operations",
    "cmms": "manufacturing_operations",
    "plant operations": "manufacturing_operations",
    "factory management": "manufacturing_operations",

    # Hospitality & Restaurant Management
    "hospitality": "hospitality_restaurant",
    "restaurant": "hospitality_restaurant",
    "hospitality saas": "hospitality_restaurant",
    "restaurant saas": "hospitality_restaurant",
    "restaurant management": "hospitality_restaurant",
    "hotel pms": "hospitality_restaurant",
    "hospitality & restaurant management": "hospitality_restaurant",

    # Vertical SaaS
    "vertical saas": "vertical_saas",
    "industry-specific vertical saas": "vertical_saas",
}


def get_all_categories() -> List[TaxonomyCategory]:
    """Return all canonical taxonomy categories."""
    return list(B2B_SAAS_TAXONOMY.values())


def get_category_by_id(category_id: str) -> Optional[TaxonomyCategory]:
    """Retrieve category definition by canonical ID."""
    return B2B_SAAS_TAXONOMY.get(category_id.lower().strip())


def normalize_category_name(input_str: Optional[str]) -> Optional[TaxonomyCategory]:
    """Normalize raw category input or synonym into canonical TaxonomyCategory.
    
    Supports:
    1. Exact canonical ID match (e.g. 'crm_sales')
    2. Exact canonical name match (e.g. 'CRM & Sales')
    3. Synonym map lookup (e.g. 'HRMS', 'Sales CRM', 'DevOps')
    4. Substring and keyword match with length and boundary priority
    """
    if not input_str or not isinstance(input_str, str):
        return None

    cleaned = input_str.strip().lower()
    cleaned_no_punct = re.sub(r"[^\w\s]", " ", cleaned).strip()

    # 1. Direct ID match
    if cleaned in B2B_SAAS_TAXONOMY:
        return B2B_SAAS_TAXONOMY[cleaned]

    # 2. Direct Canonical Name Match
    for cat in B2B_SAAS_TAXONOMY.values():
        if cat.category_name.lower() == cleaned:
            return cat

    # 3. Direct Synonym Map Lookup
    if cleaned in CATEGORY_SYNONYM_MAP:
        return B2B_SAAS_TAXONOMY[CATEGORY_SYNONYM_MAP[cleaned]]
    if cleaned_no_punct in CATEGORY_SYNONYM_MAP:
        return B2B_SAAS_TAXONOMY[CATEGORY_SYNONYM_MAP[cleaned_no_punct]]

    # 4. Check subcategories
    for cat in B2B_SAAS_TAXONOMY.values():
        for sub in cat.related_subcategories:
            if sub.lower() == cleaned or sub.lower() in cleaned:
                return cat

    # 5. Synonym phrase match prioritized by descending length
    for syn in sorted(CATEGORY_SYNONYM_MAP.keys(), key=len, reverse=True):
        if len(syn) >= 3 and re.search(rf"\b{re.escape(syn)}\b", cleaned):
            return B2B_SAAS_TAXONOMY[CATEGORY_SYNONYM_MAP[syn]]

    # 6. Keywords match prioritized by descending length with word boundaries
    all_kws = []
    for cat in B2B_SAAS_TAXONOMY.values():
        for kw in cat.keywords:
            all_kws.append((kw.lower(), cat))
    all_kws.sort(key=lambda x: len(x[0]), reverse=True)

    for kw, cat in all_kws:
        if len(kw) >= 3 and re.search(rf"\b{re.escape(kw)}\b", cleaned):
            return cat

    return None
