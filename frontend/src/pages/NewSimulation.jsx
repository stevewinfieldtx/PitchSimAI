import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../api/client';
import { Zap, ArrowLeft, ArrowRight, Send, Users, Settings2, Beaker } from 'lucide-react';

const INDUSTRIES = ['SaaS', 'Financial Services', 'Healthcare', 'Retail', 'Manufacturing', 'Cybersecurity'];
const COMPANY_SIZES = ['early-stage', 'mid-market', 'enterprise'];
const BUYING_STYLES = ['early-adopter', 'consensus-builder', 'risk-averse', 'analytical'];

// ── Test Presets ──
const PRESETS = [
  {
    label: 'WireX Systems',
    color: 'bg-blue-50 border-blue-200 text-blue-700 hover:bg-blue-100',
    data: {
      pitch_title: 'WireX Systems Ne2ition — AI-Powered Network Detection & Response',
      company_name: 'WireX Systems',
      industry: 'Cybersecurity',
      target_audience: 'CISOs and SOC teams at mid-market and enterprise companies',
      pitch_content: `WireX Systems Ne2ition Platform — AI-Powered Network Detection & Response (NDR)

Your SOC team is drowning in alerts. 95% are false positives. Meanwhile, real threats hide in encrypted traffic your current tools can't inspect. Ne2ition changes that.

Ne2ition is an AI-powered NDR platform that provides full-packet capture, real-time traffic analysis, and automated threat investigation. Unlike legacy tools that rely on signatures, Ne2ition uses behavioral AI to detect zero-day attacks, lateral movement, and data exfiltration — even inside encrypted tunnels.

Key Capabilities:
• Full packet capture at 100Gbps with intelligent indexing — never miss a packet
• AI-driven threat detection that reduces false positives by 90%
• Automated investigation workflows that cut mean-time-to-respond from hours to minutes
• Encrypted traffic analysis without decryption — maintain privacy while catching threats
• Seamless integration with your SIEM, SOAR, and EDR stack
• Cloud-native deployment — AWS, Azure, GCP, or on-prem

ROI Reality:
• Customers report 85% reduction in alert fatigue
• Average 60% faster incident response times
• One Fortune 500 customer prevented a $12M ransomware attack within 30 days of deployment

Ne2ition is trusted by Fortune 500 enterprises, federal agencies, and MSSPs worldwide. SOC 2 Type II certified, FedRAMP authorized.

We'd love to show you a live demo with YOUR network traffic. 30 minutes is all it takes to see what you've been missing.`,
    },
  },
  {
    label: 'Trustifi',
    color: 'bg-emerald-50 border-emerald-200 text-emerald-700 hover:bg-emerald-100',
    data: {
      pitch_title: 'Trustifi — AI-Powered Email Security & Encryption',
      company_name: 'Trustifi',
      industry: 'Cybersecurity',
      target_audience: 'IT directors, CISOs, and compliance officers at regulated industries',
      pitch_content: `Trustifi — Stop Email Threats Before They Reach Your Users

Email is still the #1 attack vector. 91% of cyberattacks start with a phishing email. Your Microsoft 365 or Google Workspace built-in security catches less than 60% of advanced threats. Trustifi closes the gap.

Trustifi is an AI-powered email security platform that provides inbound threat protection, outbound encryption, and DLP — all deployed in minutes with no MX record changes required.

Why Trustifi:
• AI-powered inbound shield catches BEC, spear phishing, and zero-day malware that native email security misses
• One-click AES 256-bit email encryption — recipients don't need an account or portal
• Automatic DLP scanning prevents sensitive data leakage (PII, PHI, PCI)
• Deploys in under 10 minutes via API — no MX record changes, no mail flow disruption
• Works with Microsoft 365, Google Workspace, and any SMTP system

Compliance Made Easy:
• HIPAA, GDPR, PCI-DSS, SOX, CCPA compliant out of the box
• Automatic compliance policy enforcement — no user training required
• Full audit trails and recall capability for every email

The Numbers:
• 99.7% phishing detection rate (independently verified)
• 10-minute average deployment time
• 40% reduction in email-related security incidents within 30 days
• $4.50/user/month — fraction of the cost of a breach

Trusted by 4,000+ organizations including healthcare systems, financial institutions, and law firms.

Let us show you what your current email security is missing. Free 14-day trial, no credit card required.`,
    },
  },
  {
    label: 'SecurityGate.io',
    color: 'bg-violet-50 border-violet-200 text-violet-700 hover:bg-violet-100',
    data: {
      pitch_title: 'SecurityGate.io — Integrated Risk Management for Critical Infrastructure',
      company_name: 'SecurityGate.io',
      industry: 'Cybersecurity',
      target_audience: 'OT security leaders, risk managers, and CISOs at critical infrastructure and industrial companies',
      pitch_content: `SecurityGate.io — Integrated Risk Management for OT/ICS Environments

Your operational technology (OT) environment is increasingly connected — and increasingly vulnerable. Traditional IT security tools don't understand OT protocols, Purdue Model architectures, or the reality that you can't just "patch and reboot" a running turbine.

SecurityGate.io is the integrated risk management platform purpose-built for critical infrastructure. We help you assess, score, and continuously monitor your OT/ICS cybersecurity posture against frameworks that matter: NIST CSF, IEC 62443, NERC CIP, and TSA Security Directives.

What SecurityGate Does:
• Continuous risk assessment and scoring across IT and OT environments
• Framework alignment — map your controls to NIST CSF, IEC 62443, NERC CIP, C2M2, and TSA directives
• Supply chain risk management — assess and monitor third-party vendor security
• Automated evidence collection and audit preparation
• Executive dashboards that translate technical risk into business impact
• Remediation tracking with priority scoring based on actual operational risk

Why It Matters Now:
• TSA Security Directives now require pipeline operators to implement cybersecurity measures
• NERC CIP fines can reach $1M per violation per day
• 68% of OT environments experienced a security incident in the past year
• Insurance carriers are requiring OT risk assessments for policy renewal

Customer Results:
• 70% reduction in audit preparation time
• Continuous compliance monitoring vs. point-in-time assessments
• One utility reduced their risk score by 40% in 6 months using our remediation workflows
• Average 3x faster regulatory reporting

Trusted by energy companies, water utilities, manufacturing plants, and pipeline operators across North America.

Request a demo to see your risk posture mapped against the frameworks your regulators require.`,
    },
  },
  {
    label: 'SAP Business One',
    color: 'bg-amber-50 border-amber-200 text-amber-700 hover:bg-amber-100',
    data: {
      pitch_title: 'SAP Business One — ERP for Growing Businesses',
      company_name: 'SAP',
      industry: 'SaaS',
      target_audience: 'CFOs, COOs, and operations leaders at small and mid-market businesses',
      pitch_content: `SAP Business One — The ERP That Grows With You

You've outgrown QuickBooks and spreadsheets. Orders are slipping through the cracks, inventory is a guessing game, and your finance team is spending 3 days closing the books every month. You need an ERP, but the big enterprise systems are overkill and take 18 months to implement.

SAP Business One is the ERP designed specifically for small and mid-sized businesses. One system for finance, sales, purchasing, inventory, manufacturing, and reporting — with the reliability of the SAP name behind it.

Core Capabilities:
• Financial Management — real-time accounting, multi-currency, automated bank reconciliation, instant financial statements
• Sales & CRM — full opportunity pipeline, quote-to-cash automation, customer 360 view
• Purchasing & Procurement — vendor management, automated POs, approval workflows
• Inventory & Warehouse — real-time stock tracking, batch/serial management, bin locations, multi-warehouse
• Manufacturing — BOM management, production orders, MRP, capacity planning
• Reporting — drag-and-drop dashboards, 500+ pre-built reports, Crystal Reports integration

Why SAP Business One:
• Implement in 8-12 weeks, not 18 months
• Affordable — starting at $94/user/month for cloud
• 70,000+ customers in 170 countries
• 500+ industry-specific add-ons from certified partners
• Cloud, on-premise, or hybrid deployment
• Scales from 5 to 500 users

The ROI:
• Customers report 30% faster month-end close
• 25% reduction in inventory carrying costs
• 50% fewer manual data entry errors
• One manufacturing customer recovered their investment in 9 months

Don't let your business outrun your systems. See SAP Business One in a personalized demo with YOUR data.`,
    },
  },
];

export default function NewSimulation() {
  const navigate = useNavigate();
  const [step, setStep] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [engineInfo, setEngineInfo] = useState(null);

  useEffect(() => {
    api.healthCheck()
      .then(h => setEngineInfo(h))
      .catch(() => setEngineInfo(null));
  }, []);

  const [form, setForm] = useState({
    pitch_title: '',
    pitch_content: '',
    company_name: '',
    industry: '',
    target_audience: '',
    num_personas: 10,
    num_tables: 3,
    personas_per_table: 5,
    debate_rounds: 2,
    persona_filters: {
      industries: [],
      company_sizes: [],
      buying_styles: [],
    },
  });

  const update = (key) => (e) => setForm({ ...form, [key]: e.target.value });

  const loadPreset = (preset) => {
    setForm({
      ...form,
      ...preset.data,
    });
  };

  const toggleFilter = (category, value) => {
    const current = form.persona_filters[category];
    const updated = current.includes(value)
      ? current.filter(v => v !== value)
      : [...current, value];
    setForm({
      ...form,
      persona_filters: { ...form.persona_filters, [category]: updated },
    });
  };

  const handleSubmit = async () => {
    setError('');
    setLoading(true);
    try {
      const payload = {
        ...form,
        config: {
          num_tables: form.num_tables,
          personas_per_table: form.personas_per_table,
          debate_rounds: form.debate_rounds,
        },
      };
      const result = await api.createSimulation(payload);
      navigate(`/simulation/${result.id}`);
    } catch (err) {
      setError(err.message);
      setLoading(false);
    }
  };

  return (
    <div className="max-w-3xl mx-auto">
      <button onClick={() => navigate('/')} className="flex items-center gap-1 text-gray-500 hover:text-gray-700 mb-6 text-sm">
        <ArrowLeft className="h-4 w-4" /> Back to Dashboard
      </button>

      <h1 className="text-2xl font-bold mb-2">New Pitch Simulation</h1>

      {/* Progress steps */}
      <div className="flex gap-2 mb-8">
        {[1, 2, 3].map(s => (
          <div key={s} className={`h-1.5 flex-1 rounded-full transition ${s <= step ? 'bg-primary-600' : 'bg-gray-200'}`} />
        ))}
      </div>

      {error && <div className="bg-red-50 text-red-600 p-3 rounded-lg mb-4 text-sm">{error}</div>}

      {/* Step 1: Pitch Content */}
      {step === 1 && (
        <div className="space-y-4">
          <h2 className="text-lg font-semibold">Your Pitch</h2>

          {/* Quick-Load Presets */}
          <div className="bg-gray-50 p-4 rounded-xl border border-gray-200">
            <p className="text-xs font-medium text-gray-500 mb-2 uppercase tracking-wide">Quick Load — Test Pitches</p>
            <div className="flex flex-wrap gap-2">
              {PRESETS.map(preset => (
                <button
                  key={preset.label}
                  onClick={() => loadPreset(preset)}
                  className={`px-3 py-1.5 rounded-lg text-sm font-medium border transition ${preset.color}`}
                >
                  {preset.label}
                </button>
              ))}
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Pitch Title</label>
            <input
              type="text"
              value={form.pitch_title}
              onChange={update('pitch_title')}
              placeholder="e.g., Q2 Enterprise Product Launch"
              className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent outline-none"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Pitch Content</label>
            <textarea
              value={form.pitch_content}
              onChange={update('pitch_content')}
              rows={12}
              placeholder="Paste your full sales pitch, call script, or deck outline here..."
              className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent outline-none resize-none"
            />
          </div>
          <div className="grid grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Your Company</label>
              <input type="text" value={form.company_name} onChange={update('company_name')} placeholder="Company name" className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent outline-none" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Industry</label>
              <select value={form.industry} onChange={update('industry')} className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent outline-none bg-white">
                <option value="">Select...</option>
                {INDUSTRIES.map(ind => <option key={ind} value={ind}>{ind}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Target Audience</label>
              <input type="text" value={form.target_audience} onChange={update('target_audience')} placeholder="e.g., CTOs at mid-market SaaS" className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent outline-none" />
            </div>
          </div>
          <div className="flex justify-end">
            <button onClick={() => setStep(2)} disabled={!form.pitch_title || !form.pitch_content} className="inline-flex items-center gap-2 bg-primary-600 text-white px-5 py-2.5 rounded-lg font-medium hover:bg-primary-700 transition disabled:opacity-50">
              Next <ArrowRight className="h-4 w-4" />
            </button>
          </div>
        </div>
      )}

      {/* Step 2: Persona Filters */}
      {step === 2 && (
        <div className="space-y-6">
          <h2 className="text-lg font-semibold">Buyer Persona Filters</h2>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Industries</label>
            <div className="flex flex-wrap gap-2">
              {INDUSTRIES.map(ind => (
                <button
                  key={ind}
                  onClick={() => toggleFilter('industries', ind)}
                  className={`px-3 py-1.5 rounded-lg text-sm font-medium transition border ${
                    form.persona_filters.industries.includes(ind)
                      ? 'bg-primary-600 text-white border-primary-600'
                      : 'bg-white text-gray-700 border-gray-300 hover:border-primary-300'
                  }`}
                >
                  {ind}
                </button>
              ))}
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Company Size</label>
            <div className="flex flex-wrap gap-2">
              {COMPANY_SIZES.map(size => (
                <button
                  key={size}
                  onClick={() => toggleFilter('company_sizes', size)}
                  className={`px-3 py-1.5 rounded-lg text-sm font-medium transition border ${
                    form.persona_filters.company_sizes.includes(size)
                      ? 'bg-primary-600 text-white border-primary-600'
                      : 'bg-white text-gray-700 border-gray-300 hover:border-primary-300'
                  }`}
                >
                  {size}
                </button>
              ))}
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Buying Style</label>
            <div className="flex flex-wrap gap-2">
              {BUYING_STYLES.map(style => (
                <button
                  key={style}
                  onClick={() => toggleFilter('buying_styles', style)}
                  className={`px-3 py-1.5 rounded-lg text-sm font-medium transition border ${
                    form.persona_filters.buying_styles.includes(style)
                      ? 'bg-primary-600 text-white border-primary-600'
                      : 'bg-white text-gray-700 border-gray-300 hover:border-primary-300'
                  }`}
                >
                  {style}
                </button>
              ))}
            </div>
          </div>

          <div className="flex justify-between">
            <button onClick={() => setStep(1)} className="text-gray-500 hover:text-gray-700 text-sm">Back</button>
            <button onClick={() => setStep(3)} className="inline-flex items-center gap-2 bg-primary-600 text-white px-5 py-2.5 rounded-lg font-medium hover:bg-primary-700 transition">
              Next <ArrowRight className="h-4 w-4" />
            </button>
          </div>
        </div>
      )}

      {/* Step 3: Review & Launch */}
      {step === 3 && (
        <div className="space-y-6">
          <h2 className="text-lg font-semibold">Review & Launch</h2>

          <div className="bg-white p-6 rounded-xl border border-gray-200 space-y-4">
            <div>
              <p className="text-sm text-gray-500">Pitch Title</p>
              <p className="font-medium">{form.pitch_title}</p>
            </div>
            <div>
              <p className="text-sm text-gray-500">Pitch Preview</p>
              <p className="text-sm text-gray-700 line-clamp-3">{form.pitch_content}</p>
            </div>
            <div className="grid grid-cols-3 gap-4">
              <div>
                <p className="text-sm text-gray-500">Company</p>
                <p className="font-medium">{form.company_name || 'Not specified'}</p>
              </div>
              <div>
                <p className="text-sm text-gray-500">Industry</p>
                <p className="font-medium">{form.industry || 'Not specified'}</p>
              </div>
              <div>
                <p className="text-sm text-gray-500">Target Audience</p>
                <p className="font-medium">{form.target_audience || 'All personas'}</p>
              </div>
            </div>
          </div>

          {/* Swarm Engine Configuration */}
          <div className="bg-white p-6 rounded-xl border border-gray-200 space-y-4">
            <div className="flex items-center gap-2 mb-2">
              <Users className="h-5 w-5 text-primary-600" />
              <h3 className="font-semibold">Swarm Engine Configuration</h3>
              <span className="text-xs bg-primary-50 text-primary-700 px-2 py-0.5 rounded-full font-medium">Multi-Agent Deliberation</span>
            </div>

            <div className="grid grid-cols-3 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Committee Tables ({form.num_tables})
                </label>
                <input
                  type="range"
                  min="1"
                  max="5"
                  value={form.num_tables}
                  onChange={(e) => setForm({ ...form, num_tables: parseInt(e.target.value) })}
                  className="w-full"
                />
                <div className="flex justify-between text-xs text-gray-400">
                  <span>1</span><span>5</span>
                </div>
                <p className="text-xs text-gray-500 mt-1">Different committee perspectives</p>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Personas per Table ({form.personas_per_table})
                </label>
                <input
                  type="range"
                  min="3"
                  max="7"
                  value={form.personas_per_table}
                  onChange={(e) => setForm({ ...form, personas_per_table: parseInt(e.target.value) })}
                  className="w-full"
                />
                <div className="flex justify-between text-xs text-gray-400">
                  <span>3</span><span>7</span>
                </div>
                <p className="text-xs text-gray-500 mt-1">Buyers on each committee</p>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Debate Rounds ({form.debate_rounds})
                </label>
                <input
                  type="range"
                  min="1"
                  max="4"
                  value={form.debate_rounds}
                  onChange={(e) => setForm({ ...form, debate_rounds: parseInt(e.target.value) })}
                  className="w-full"
                />
                <div className="flex justify-between text-xs text-gray-400">
                  <span>1</span><span>4</span>
                </div>
                <p className="text-xs text-gray-500 mt-1">More rounds = deeper deliberation</p>
              </div>
            </div>

            <div className="bg-gray-50 rounded-lg p-3 text-xs text-gray-600">
              <strong>Total LLM calls:</strong> ~{form.num_tables * form.personas_per_table * (1 + form.debate_rounds) + form.num_tables + 2} calls
              ({form.num_tables} tables × {form.personas_per_table} personas × {1 + form.debate_rounds} rounds + synthesis)
            </div>
          </div>

          <div className="flex justify-between">
            <button onClick={() => setStep(2)} className="text-gray-500 hover:text-gray-700 text-sm">Back</button>
            <button
              onClick={handleSubmit}
              disabled={loading}
              className="inline-flex items-center gap-2 bg-primary-600 text-white px-6 py-2.5 rounded-lg font-medium hover:bg-primary-700 transition disabled:opacity-50 shadow-sm"
            >
              <Zap className="h-4 w-4" />
              {loading ? 'Launching Swarm...' : 'Launch Swarm Simulation'}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
