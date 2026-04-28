import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../api/client';
import {
  Zap, ArrowLeft, ArrowRight, Send, Users, ChevronDown,
  FileText, Link2, Upload, Globe, Building2, Target, Layers
} from 'lucide-react';

// ── Industry Taxonomy (HubSpot/LinkedIn-style) ──
const INDUSTRY_TAXONOMY = {
  "Financial Services": [
    "Banking & Credit Unions", "Insurance", "Investment Management",
    "Fintech & Payments", "Real Estate & Property Mgmt", "Accounting & Tax"
  ],
  "Technology & Software": [
    "SaaS", "Cloud Infrastructure", "Cybersecurity",
    "IT Services & Consulting", "Hardware & Equipment", "Telecom"
  ],
  "Healthcare": [
    "Hospitals & Health Systems", "Physician Practices & Clinics",
    "Pharma & Biotech", "Medical Devices", "Health Insurance", "Healthcare IT"
  ],
  "Manufacturing & Engineering": [
    "Industrial Manufacturing", "Construction & Engineering",
    "Automotive & Transportation", "Chemicals", "Aerospace & Defense"
  ],
  "Retail & Consumer": [
    "E-Commerce", "Brick-and-Mortar Retail", "Food & Beverage",
    "Apparel & Fashion", "Consumer Electronics"
  ],
  "Professional Services": [
    "Management Consulting", "Legal Services", "Marketing & Advertising",
    "HR & Recruiting", "Architecture & Design"
  ],
  "Education": [
    "Higher Education", "K-12 Schools", "EdTech & E-Learning",
    "Corporate Training"
  ],
  "Government & Public Sector": [
    "Federal Agencies", "State & Local Government",
    "Public Safety", "Military & Defense"
  ],
  "Energy & Utilities": [
    "Oil & Gas", "Electric Utilities", "Renewable Energy",
    "Water & Waste Management"
  ],
  "Transportation & Logistics": [
    "Airlines & Travel", "Trucking & Freight",
    "Shipping & Ports", "Warehousing & Distribution"
  ],
  "Media & Entertainment": [
    "Digital Media & Publishing", "Gaming",
    "Film & Video", "Sports & Recreation"
  ],
  "Hospitality": [
    "Hotels & Accommodations", "Restaurants & Food Service",
    "Travel & Tourism"
  ],
};

const INDUSTRIES = Object.keys(INDUSTRY_TAXONOMY);

// ── Audience Segments ──
const AUDIENCE_SEGMENTS = [
  { value: "general",            label: "General Audience",    desc: "Broad mix of company sizes and buying styles" },
  { value: "smb",                label: "SMB",                 desc: "Small & medium businesses (< 200 employees)" },
  { value: "mid-market",         label: "Mid-Market",          desc: "Growing companies (200–1,000 employees)" },
  { value: "small-enterprise",   label: "Small Enterprise",    desc: "Enterprise orgs (1,000–5,000 employees)" },
  { value: "medium-enterprise",  label: "Medium Enterprise",   desc: "Large enterprise (5,000–20,000 employees)" },
  { value: "large-enterprise",   label: "Large Enterprise",    desc: "Global enterprise (20,000+ employees)" },
];

// ── Pitch Input Methods ──
const PITCH_METHODS = [
  { id: "paste",    label: "Paste Text",       icon: FileText, desc: "Paste your pitch script or talking points" },
  { id: "url",      label: "Website URL",      icon: Link2,    desc: "We'll extract key messaging from a URL" },
  { id: "upload",   label: "Upload File",      icon: Upload,   desc: "PDF, PPTX, DOCX, or plain text" },
];

// ── Test Presets ──
const PRESETS = [
  {
    label: 'WireX Systems',
    color: 'bg-blue-50 border-blue-200 text-blue-700 hover:bg-blue-100',
    data: {
      pitch_title: 'WireX Systems Ne2ition — AI-Powered NDR',
      company_name: 'WireX Systems',
      industry: 'Technology & Software',
      sub_industry: 'Cybersecurity',
      audience_segment: 'mid-market',
      target_audience: 'CISOs and SOC teams',
      pitch_content: `WireX Systems Ne2ition Platform — AI-Powered Network Detection & Response (NDR)

Your SOC team is drowning in alerts. 95% are false positives. Meanwhile, real threats hide in encrypted traffic your current tools can't inspect. Ne2ition changes that.

Ne2ition is an AI-powered NDR platform that provides full-packet capture, real-time traffic analysis, and automated threat investigation. Unlike legacy tools that rely on signatures, Ne2ition uses behavioral AI to detect zero-day attacks, lateral movement, and data exfiltration — even inside encrypted tunnels.

Key Capabilities:
• Full packet capture at 100Gbps with intelligent indexing
• AI-driven threat detection that reduces false positives by 90%
• Automated investigation workflows that cut MTTR from hours to minutes
• Encrypted traffic analysis without decryption
• Seamless integration with SIEM, SOAR, and EDR stacks
• Cloud-native: AWS, Azure, GCP, or on-prem

ROI Reality:
• 85% reduction in alert fatigue
• 60% faster incident response times
• One Fortune 500 customer prevented a $12M ransomware attack within 30 days

SOC 2 Type II certified, FedRAMP authorized. Trusted by Fortune 500 enterprises and federal agencies.

30-minute live demo with YOUR network traffic — see what you've been missing.`,
    },
  },
  {
    label: 'Trustifi',
    color: 'bg-emerald-50 border-emerald-200 text-emerald-700 hover:bg-emerald-100',
    data: {
      pitch_title: 'Trustifi — AI-Powered Email Security',
      company_name: 'Trustifi',
      industry: 'Technology & Software',
      sub_industry: 'Cybersecurity',
      audience_segment: 'mid-market',
      target_audience: 'IT directors, CISOs, and compliance officers',
      pitch_content: `Trustifi — Stop Email Threats Before They Reach Your Users

Email is still the #1 attack vector. 91% of cyberattacks start with a phishing email. Your Microsoft 365 or Google Workspace built-in security catches less than 60% of advanced threats.

Trustifi is an AI-powered email security platform: inbound threat protection, outbound encryption, and DLP — deployed in minutes with no MX record changes.

• AI-powered inbound shield catches BEC, spear phishing, and zero-day malware
• One-click AES 256-bit encryption — recipients don't need an account
• Automatic DLP scanning prevents sensitive data leakage
• Deploys in under 10 minutes via API — no MX record changes
• HIPAA, GDPR, PCI-DSS, SOX, CCPA compliant out of the box

The Numbers: 99.7% phishing detection rate • 10-minute deployment • 40% reduction in email incidents within 30 days • $4.50/user/month

Trusted by 4,000+ organizations. Free 14-day trial.`,
    },
  },
  {
    label: 'NCC Group',
    color: 'bg-rose-50 border-rose-200 text-rose-700 hover:bg-rose-100',
    data: {
      pitch_title: 'NCC Group — Technical Assurance & Pen Testing',
      company_name: 'NCC Group',
      industry: 'Technology & Software',
      sub_industry: 'Cybersecurity',
      audience_segment: 'medium-enterprise',
      target_audience: 'CISOs, VPs of Engineering, and security teams',
      pitch_content: `NCC Group — Technical Assurance Services

Your security posture is only as strong as your weakest link. Compliance reports and vulnerability scans tell you what's broken, but they don't tell you if attackers can actually exploit those weaknesses.

NCC Group provides independent, expert-led penetration testing and security assessments — simulating real-world attacks to uncover what automated tools miss.

• Comprehensive pen testing — network, application, cloud, physical
• Red team exercises against your security teams
• Hardware security — chip-level and firmware analysis
• Managed detection services — continuous threat hunting & IR
• Framework alignment: NIST, ISO 27001, PCI-DSS, HIPAA, GDPR

Why NCC: 2,500+ consultants across 25+ countries. Independent validation. Vulnerability discovery rate 40% higher than automated tools.

Results: $45M fraud scheme prevented • 12 critical AWS misconfigs found • 80% faster MTTD • SOC 2 passed on first attempt.`,
    },
  },
  {
    label: 'SAP B1',
    color: 'bg-amber-50 border-amber-200 text-amber-700 hover:bg-amber-100',
    data: {
      pitch_title: 'SAP Business One — ERP for Growing Businesses',
      company_name: 'SAP',
      industry: 'Technology & Software',
      sub_industry: 'SaaS',
      audience_segment: 'smb',
      target_audience: 'CFOs, COOs, and operations leaders',
      pitch_content: `SAP Business One — The ERP That Grows With You

You've outgrown QuickBooks and spreadsheets. Orders slip through cracks, inventory is a guessing game, finance takes 3 days to close the books.

SAP Business One: one system for finance, sales, purchasing, inventory, manufacturing, and reporting — with SAP reliability behind it.

• Financial Management — real-time accounting, multi-currency, automated reconciliation
• Sales & CRM — pipeline, quote-to-cash, customer 360
• Inventory & Warehouse — real-time stock, batch/serial, multi-warehouse
• Manufacturing — BOM, production orders, MRP, capacity planning
• Reporting — drag-and-drop dashboards, 500+ pre-built reports

Implement in 8-12 weeks. Starting at $94/user/month. 70,000+ customers in 170 countries. Scales from 5 to 500 users.

ROI: 30% faster month-end close • 25% less inventory cost • 50% fewer data entry errors.`,
    },
  },
  {
    label: 'SecurityGate.io',
    color: 'bg-violet-50 border-violet-200 text-violet-700 hover:bg-violet-100',
    data: {
      pitch_title: 'SecurityGate.io — IRM for Critical Infrastructure',
      company_name: 'SecurityGate.io',
      industry: 'Energy & Utilities',
      sub_industry: 'Electric Utilities',
      audience_segment: 'medium-enterprise',
      target_audience: 'OT security leaders, risk managers, and CISOs',
      pitch_content: `SecurityGate.io — Integrated Risk Management for OT/ICS Environments

Your OT environment is increasingly connected and increasingly vulnerable. Traditional IT security tools don't understand OT protocols, Purdue Model architectures, or the reality that you can't just patch a running turbine.

SecurityGate.io: the integrated risk management platform purpose-built for critical infrastructure.

• Continuous risk assessment across IT and OT
• Framework alignment: NIST CSF, IEC 62443, NERC CIP, TSA directives
• Supply chain risk management for third-party vendors
• Automated evidence collection and audit prep
• Executive dashboards translating technical risk to business impact

Why Now: TSA directives require pipeline cybersecurity measures. NERC CIP fines reach $1M/violation/day. 68% of OT environments had a security incident last year.

Results: 70% less audit prep time • 40% risk score reduction in 6 months • 3x faster regulatory reporting.`,
    },
  },
];


export default function NewSimulation() {
  const navigate = useNavigate();
  const [step, setStep] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const fileInputRef = useRef(null);

  const [form, setForm] = useState({
    pitch_title: '',
    pitch_content: '',
    pitch_method: 'paste',
    pitch_url: '',
    company_name: '',
    industry: '',
    sub_industry: '',
    audience_segment: 'general',
    target_audience: '',
    num_tables: 3,
    personas_per_table: 5,
    debate_rounds: 2,
  });

  const update = (key) => (e) => setForm({ ...form, [key]: e.target.value });

  const loadPreset = (preset) => {
    setForm({ ...form, ...preset.data, pitch_method: 'paste' });
  };

  const subIndustries = form.industry ? (INDUSTRY_TAXONOMY[form.industry] || []) : [];

  // Handle file upload
  const handleFileUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    const ext = file.name.split('.').pop().toLowerCase();

    if (ext === 'txt' || ext === 'md') {
      const text = await file.text();
      setForm(f => ({
        ...f,
        pitch_content: text,
        pitch_title: f.pitch_title || file.name.replace(/\.[^.]+$/, ''),
      }));
    } else if (ext === 'pdf' || ext === 'docx' || ext === 'pptx') {
      // For binary formats, we'd need server-side extraction
      // For now, show a helpful message
      setError(`${ext.toUpperCase()} extraction coming soon. For now, paste the text content directly.`);
    } else {
      setError('Supported formats: .txt, .md, .pdf, .docx, .pptx');
    }
  };

  // Handle URL extraction (placeholder — will need backend endpoint)
  const handleUrlExtract = async () => {
    if (!form.pitch_url) return;
    setError('URL extraction coming soon. For now, paste the content from that page directly.');
  };

  const handleSubmit = async () => {
    setError('');
    setLoading(true);
    try {
      // Build the audience description from segment + custom text
      const segmentLabel = AUDIENCE_SEGMENTS.find(s => s.value === form.audience_segment)?.label || '';
      const audienceDesc = form.target_audience
        ? `${form.target_audience} (${segmentLabel})`
        : segmentLabel;

      // Build industry string (include sub-industry if selected)
      const industryStr = form.sub_industry
        ? `${form.industry} — ${form.sub_industry}`
        : form.industry;

      const payload = {
        pitch_title: form.pitch_title,
        pitch_content: form.pitch_content,
        company_name: form.company_name,
        industry: industryStr,
        target_audience: audienceDesc,
        num_personas: form.num_tables * form.personas_per_table,
        config: {
          num_tables: form.num_tables,
          personas_per_table: form.personas_per_table,
          debate_rounds: form.debate_rounds,
          company_size: form.audience_segment,
          sub_industry: form.sub_industry,
        },
      };
      const result = await api.createSimulation(payload);
      navigate(`/simulation/${result.id}`);
    } catch (err) {
      setError(err.message);
      setLoading(false);
    }
  };

  const canAdvanceStep1 = form.pitch_title && form.pitch_content;
  const canAdvanceStep2 = form.industry;

  return (
    <div className="max-w-3xl mx-auto">
      <button onClick={() => navigate('/')} className="flex items-center gap-1 text-gray-500 hover:text-gray-700 mb-6 text-sm">
        <ArrowLeft className="h-4 w-4" /> Back to Dashboard
      </button>

      <h1 className="text-2xl font-bold mb-1">Proof Your Pitch</h1>
      <p className="text-gray-500 text-sm mb-6">Test your pitch against AI buying committees before the real meeting.</p>

      {/* Progress steps */}
      <div className="flex gap-2 mb-8">
        {['Your Pitch', 'Target Market', 'Review & Launch'].map((label, i) => (
          <div key={i} className="flex-1">
            <div className={`h-1.5 rounded-full transition mb-1 ${i < step ? 'bg-primary-600' : i === step - 1 ? 'bg-primary-600' : 'bg-gray-200'}`} />
            <span className={`text-xs ${i <= step - 1 ? 'text-primary-600 font-medium' : 'text-gray-400'}`}>{label}</span>
          </div>
        ))}
      </div>

      {error && (
        <div className="bg-red-50 text-red-600 p-3 rounded-lg mb-4 text-sm flex justify-between items-center">
          <span>{error}</span>
          <button onClick={() => setError('')} className="text-red-400 hover:text-red-600 text-xs">dismiss</button>
        </div>
      )}

      {/* ═══════ STEP 1: YOUR PITCH ═══════ */}
      {step === 1 && (
        <div className="space-y-5">
          {/* Quick-Load Presets */}
          <div className="bg-gray-50 p-4 rounded-xl border border-gray-200">
            <p className="text-xs font-medium text-gray-500 mb-2 uppercase tracking-wide">Quick Load — Demo Pitches</p>
            <div className="grid grid-cols-5 gap-2">
              {PRESETS.map(preset => (
                <button
                  key={preset.label}
                  onClick={() => loadPreset(preset)}
                  className={`px-2 py-1.5 rounded-lg text-xs font-medium border transition ${preset.color}`}
                >
                  {preset.label}
                </button>
              ))}
            </div>
          </div>

          {/* Pitch Input Method */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">How would you like to provide your pitch?</label>
            <div className="grid grid-cols-3 gap-3">
              {PITCH_METHODS.map(method => {
                const Icon = method.icon;
                const active = form.pitch_method === method.id;
                return (
                  <button
                    key={method.id}
                    onClick={() => setForm({ ...form, pitch_method: method.id })}
                    className={`p-3 rounded-xl border-2 text-left transition ${
                      active
                        ? 'border-primary-500 bg-primary-50'
                        : 'border-gray-200 hover:border-gray-300 bg-white'
                    }`}
                  >
                    <Icon className={`h-5 w-5 mb-1.5 ${active ? 'text-primary-600' : 'text-gray-400'}`} />
                    <p className={`text-sm font-medium ${active ? 'text-primary-700' : 'text-gray-700'}`}>{method.label}</p>
                    <p className="text-xs text-gray-500 mt-0.5">{method.desc}</p>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Conditional Input Based on Method */}
          {form.pitch_method === 'paste' && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Pitch Content</label>
              <textarea
                value={form.pitch_content}
                onChange={update('pitch_content')}
                rows={10}
                placeholder="Paste your sales pitch, call script, white paper excerpt, or deck talking points..."
                className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent outline-none resize-none text-sm"
              />
              <p className="text-xs text-gray-400 mt-1">{form.pitch_content.length > 0 ? `${form.pitch_content.length} characters` : 'Tip: The more detail you give, the more realistic the committee feedback.'}</p>
            </div>
          )}

          {form.pitch_method === 'url' && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Website or Solution URL</label>
              <div className="flex gap-2">
                <div className="flex-1 relative">
                  <Globe className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
                  <input
                    type="url"
                    value={form.pitch_url}
                    onChange={update('pitch_url')}
                    placeholder="https://yourcompany.com/product"
                    className="w-full pl-10 pr-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent outline-none text-sm"
                  />
                </div>
                <button
                  onClick={handleUrlExtract}
                  className="px-4 py-2.5 bg-primary-600 text-white rounded-lg font-medium text-sm hover:bg-primary-700 transition"
                >
                  Extract
                </button>
              </div>
              <p className="text-xs text-gray-400 mt-1">We'll pull the key messaging, value props, and product details from this page.</p>
              {form.pitch_content && (
                <div className="mt-3">
                  <label className="block text-sm font-medium text-gray-700 mb-1">Extracted Content (edit as needed)</label>
                  <textarea
                    value={form.pitch_content}
                    onChange={update('pitch_content')}
                    rows={8}
                    className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent outline-none resize-none text-sm"
                  />
                </div>
              )}
            </div>
          )}

          {form.pitch_method === 'upload' && (
            <div>
              <input
                ref={fileInputRef}
                type="file"
                accept=".txt,.md,.pdf,.docx,.pptx"
                onChange={handleFileUpload}
                className="hidden"
              />
              <button
                onClick={() => fileInputRef.current?.click()}
                className="w-full p-8 border-2 border-dashed border-gray-300 rounded-xl hover:border-primary-400 transition text-center"
              >
                <Upload className="h-8 w-8 text-gray-400 mx-auto mb-2" />
                <p className="text-sm font-medium text-gray-700">Click to upload or drag & drop</p>
                <p className="text-xs text-gray-400 mt-1">Supports TXT, PDF, DOCX, PPTX</p>
              </button>
              {form.pitch_content && (
                <div className="mt-3">
                  <label className="block text-sm font-medium text-gray-700 mb-1">File Content (edit as needed)</label>
                  <textarea
                    value={form.pitch_content}
                    onChange={update('pitch_content')}
                    rows={8}
                    className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent outline-none resize-none text-sm"
                  />
                </div>
              )}
            </div>
          )}

          {/* Title & Company */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Pitch Title</label>
              <input
                type="text"
                value={form.pitch_title}
                onChange={update('pitch_title')}
                placeholder="e.g., Q2 Enterprise Launch"
                className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent outline-none text-sm"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Your Company</label>
              <input
                type="text"
                value={form.company_name}
                onChange={update('company_name')}
                placeholder="Company name"
                className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent outline-none text-sm"
              />
            </div>
          </div>

          <div className="flex justify-end">
            <button
              onClick={() => setStep(2)}
              disabled={!canAdvanceStep1}
              className="inline-flex items-center gap-2 bg-primary-600 text-white px-5 py-2.5 rounded-lg font-medium hover:bg-primary-700 transition disabled:opacity-50"
            >
              Next: Target Market <ArrowRight className="h-4 w-4" />
            </button>
          </div>
        </div>
      )}

      {/* ═══════ STEP 2: TARGET MARKET ═══════ */}
      {step === 2 && (
        <div className="space-y-6">

          {/* Industry Selection */}
          <div>
            <div className="flex items-center gap-2 mb-3">
              <Layers className="h-4 w-4 text-primary-600" />
              <label className="text-sm font-semibold text-gray-800">Target Industry</label>
            </div>
            <div className="grid grid-cols-3 gap-2">
              {INDUSTRIES.map(ind => (
                <button
                  key={ind}
                  onClick={() => setForm({ ...form, industry: ind, sub_industry: '' })}
                  className={`px-3 py-2 rounded-lg text-sm font-medium transition border text-left ${
                    form.industry === ind
                      ? 'bg-primary-600 text-white border-primary-600'
                      : 'bg-white text-gray-700 border-gray-200 hover:border-primary-300'
                  }`}
                >
                  {ind}
                </button>
              ))}
            </div>
          </div>

          {/* Sub-Industry (only shows when industry is selected) */}
          {subIndustries.length > 0 && (
            <div className="pl-4 border-l-2 border-primary-200">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Narrow it down <span className="text-gray-400 font-normal">(optional)</span>
              </label>
              <div className="flex flex-wrap gap-2">
                {subIndustries.map(sub => (
                  <button
                    key={sub}
                    onClick={() => setForm({ ...form, sub_industry: form.sub_industry === sub ? '' : sub })}
                    className={`px-3 py-1.5 rounded-lg text-sm font-medium transition border ${
                      form.sub_industry === sub
                        ? 'bg-primary-100 text-primary-700 border-primary-300'
                        : 'bg-white text-gray-600 border-gray-200 hover:border-primary-300'
                    }`}
                  >
                    {sub}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Audience Segment */}
          <div>
            <div className="flex items-center gap-2 mb-3">
              <Building2 className="h-4 w-4 text-primary-600" />
              <label className="text-sm font-semibold text-gray-800">Buyer Company Size</label>
            </div>
            <div className="grid grid-cols-3 gap-2">
              {AUDIENCE_SEGMENTS.map(seg => (
                <button
                  key={seg.value}
                  onClick={() => setForm({ ...form, audience_segment: seg.value })}
                  className={`p-3 rounded-xl border-2 text-left transition ${
                    form.audience_segment === seg.value
                      ? 'border-primary-500 bg-primary-50'
                      : 'border-gray-200 hover:border-gray-300 bg-white'
                  }`}
                >
                  <p className={`text-sm font-medium ${form.audience_segment === seg.value ? 'text-primary-700' : 'text-gray-700'}`}>
                    {seg.label}
                  </p>
                  <p className="text-xs text-gray-500 mt-0.5">{seg.desc}</p>
                </button>
              ))}
            </div>
          </div>

          {/* Target Audience (specific roles) */}
          <div>
            <div className="flex items-center gap-2 mb-2">
              <Target className="h-4 w-4 text-primary-600" />
              <label className="text-sm font-semibold text-gray-800">
                Target Roles <span className="text-gray-400 font-normal text-xs">(optional — helps focus the committee)</span>
              </label>
            </div>
            <input
              type="text"
              value={form.target_audience}
              onChange={update('target_audience')}
              placeholder="e.g., CISOs, VP of Engineering, IT Directors"
              className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent outline-none text-sm"
            />
          </div>

          <div className="flex justify-between">
            <button onClick={() => setStep(1)} className="text-gray-500 hover:text-gray-700 text-sm flex items-center gap-1">
              <ArrowLeft className="h-3.5 w-3.5" /> Back
            </button>
            <button
              onClick={() => setStep(3)}
              disabled={!canAdvanceStep2}
              className="inline-flex items-center gap-2 bg-primary-600 text-white px-5 py-2.5 rounded-lg font-medium hover:bg-primary-700 transition disabled:opacity-50"
            >
              Next: Review <ArrowRight className="h-4 w-4" />
            </button>
          </div>
        </div>
      )}

      {/* ═══════ STEP 3: REVIEW & LAUNCH ═══════ */}
      {step === 3 && (
        <div className="space-y-5">

          {/* Summary Card */}
          <div className="bg-white p-6 rounded-xl border border-gray-200 space-y-4">
            <div className="grid grid-cols-2 gap-x-8 gap-y-3">
              <div>
                <p className="text-xs text-gray-500 uppercase tracking-wide">Pitch</p>
                <p className="font-medium text-sm mt-0.5">{form.pitch_title}</p>
              </div>
              <div>
                <p className="text-xs text-gray-500 uppercase tracking-wide">Company</p>
                <p className="font-medium text-sm mt-0.5">{form.company_name || '—'}</p>
              </div>
              <div>
                <p className="text-xs text-gray-500 uppercase tracking-wide">Industry</p>
                <p className="font-medium text-sm mt-0.5">
                  {form.industry}{form.sub_industry ? ` → ${form.sub_industry}` : ''}
                </p>
              </div>
              <div>
                <p className="text-xs text-gray-500 uppercase tracking-wide">Audience</p>
                <p className="font-medium text-sm mt-0.5">
                  {AUDIENCE_SEGMENTS.find(s => s.value === form.audience_segment)?.label || 'General'}
                  {form.target_audience ? ` — ${form.target_audience}` : ''}
                </p>
              </div>
            </div>
            <div className="pt-3 border-t border-gray-100">
              <p className="text-xs text-gray-500 uppercase tracking-wide mb-1">Pitch Preview</p>
              <p className="text-sm text-gray-600 line-clamp-3">{form.pitch_content}</p>
            </div>
          </div>

          {/* Swarm Engine Configuration */}
          <div className="bg-white p-6 rounded-xl border border-gray-200 space-y-4">
            <div className="flex items-center gap-2 mb-1">
              <Users className="h-5 w-5 text-primary-600" />
              <h3 className="font-semibold text-sm">Buying Committee Configuration</h3>
            </div>

            <div className="grid grid-cols-3 gap-4">
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">
                  Committee Tables ({form.num_tables})
                </label>
                <input
                  type="range" min="1" max="5" value={form.num_tables}
                  onChange={(e) => setForm({ ...form, num_tables: parseInt(e.target.value) })}
                  className="w-full"
                />
                <div className="flex justify-between text-[10px] text-gray-400"><span>1</span><span>5</span></div>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">
                  Personas per Table ({form.personas_per_table})
                </label>
                <input
                  type="range" min="3" max="7" value={form.personas_per_table}
                  onChange={(e) => setForm({ ...form, personas_per_table: parseInt(e.target.value) })}
                  className="w-full"
                />
                <div className="flex justify-between text-[10px] text-gray-400"><span>3</span><span>7</span></div>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">
                  Debate Rounds ({form.debate_rounds})
                </label>
                <input
                  type="range" min="1" max="4" value={form.debate_rounds}
                  onChange={(e) => setForm({ ...form, debate_rounds: parseInt(e.target.value) })}
                  className="w-full"
                />
                <div className="flex justify-between text-[10px] text-gray-400"><span>1</span><span>4</span></div>
              </div>
            </div>

            <div className="bg-gray-50 rounded-lg p-3 text-xs text-gray-600">
              <strong>{form.num_tables * form.personas_per_table}</strong> AI buying committee members across{' '}
              <strong>{form.num_tables}</strong> tables, debating for{' '}
              <strong>{form.debate_rounds}</strong> rounds
              {' '}({form.num_tables * form.personas_per_table * (1 + form.debate_rounds) + form.num_tables + 2} LLM calls)
            </div>
          </div>

          <div className="flex justify-between">
            <button onClick={() => setStep(2)} className="text-gray-500 hover:text-gray-700 text-sm flex items-center gap-1">
              <ArrowLeft className="h-3.5 w-3.5" /> Back
            </button>
            <button
              onClick={handleSubmit}
              disabled={loading}
              className="inline-flex items-center gap-2 bg-primary-600 text-white px-6 py-2.5 rounded-lg font-medium hover:bg-primary-700 transition disabled:opacity-50 shadow-sm"
            >
              <Zap className="h-4 w-4" />
              {loading ? 'Launching...' : 'Proof This Pitch'}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
