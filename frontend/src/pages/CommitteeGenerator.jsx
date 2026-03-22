import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../api/client';
import {
  Users, Smile, Meh, Frown, Building2, Linkedin, UserPlus,
  Sparkles, ArrowRight, ChevronDown, ChevronUp, Briefcase,
  Shield, Zap, Target, AlertTriangle, Globe
} from 'lucide-react';

const INDUSTRIES = [
  { value: 'SaaS', icon: Globe, color: 'blue' },
  { value: 'Financial Services', icon: Shield, color: 'emerald' },
  { value: 'Healthcare', icon: Target, color: 'rose' },
  { value: 'Retail', icon: Briefcase, color: 'purple' },
  { value: 'Manufacturing', icon: Building2, color: 'orange' },
  { value: 'Education', icon: Sparkles, color: 'cyan' },
  { value: 'Real Estate', icon: Building2, color: 'amber' },
];

const COMPANY_SIZES = [
  { value: 'small', label: 'Startup / Small', desc: '1-100 employees', members: '3 committee members' },
  { value: 'mid-market', label: 'Mid-Market', desc: '100-1,000 employees', members: '5 committee members' },
  { value: 'enterprise', label: 'Enterprise', desc: '1,000+ employees', members: '7 committee members' },
];

const WARMTH_OPTIONS = [
  {
    value: 'friendly',
    label: 'Friendly',
    icon: Smile,
    color: 'green',
    desc: 'Actively looking for solutions, open to new vendors, positive buying signals',
    bg: 'bg-green-50 border-green-200 hover:border-green-400',
    selected: 'bg-green-100 border-green-500 ring-2 ring-green-200',
    iconColor: 'text-green-600',
  },
  {
    value: 'mixed',
    label: 'Mixed',
    icon: Meh,
    color: 'yellow',
    desc: 'Standard evaluation process — some champions, some skeptics',
    bg: 'bg-yellow-50 border-yellow-200 hover:border-yellow-400',
    selected: 'bg-yellow-100 border-yellow-500 ring-2 ring-yellow-200',
    iconColor: 'text-yellow-600',
  },
  {
    value: 'hostile',
    label: 'Hostile',
    icon: Frown,
    color: 'red',
    desc: 'Resistant to change, incumbent loyalty, budget-constrained, political dynamics',
    bg: 'bg-red-50 border-red-200 hover:border-red-400',
    selected: 'bg-red-100 border-red-500 ring-2 ring-red-200',
    iconColor: 'text-red-600',
  },
];

export default function CommitteeGenerator() {
  const navigate = useNavigate();
  const [step, setStep] = useState('configure'); // configure | results | linkedin
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // Committee config
  const [industry, setIndustry] = useState('');
  const [companySize, setCompanySize] = useState('');
  const [warmth, setWarmth] = useState('');
  const [companyName, setCompanyName] = useState('');
  const [productContext, setProductContext] = useState('');

  // Results
  const [committee, setCommittee] = useState(null);

  // LinkedIn import
  const [linkedinMode, setLinkedinMode] = useState('text'); // text | name
  const [linkedinText, setLinkedinText] = useState('');
  const [linkedinName, setLinkedinName] = useState('');
  const [linkedinCompany, setLinkedinCompany] = useState('');
  const [linkedinTitle, setLinkedinTitle] = useState('');
  const [linkedinWarmth, setLinkedinWarmth] = useState('mixed');
  const [enrichedPersona, setEnrichedPersona] = useState(null);
  const [enrichLoading, setEnrichLoading] = useState(false);

  const canGenerate = industry && companySize && warmth;

  const handleGenerate = async () => {
    setError('');
    setLoading(true);
    try {
      const result = await api.generateCommittee({
        industry,
        company_size: companySize,
        warmth,
        company_name: companyName || undefined,
        product_context: productContext || undefined,
      });
      setCommittee(result);
      setStep('results');
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleLinkedInEnrich = async () => {
    setError('');
    setEnrichLoading(true);
    try {
      let result;
      if (linkedinMode === 'text') {
        result = await api.enrichFromLinkedIn({
          profile_text: linkedinText,
          warmth: linkedinWarmth,
        });
      } else {
        result = await api.enrichFromName({
          name: linkedinName,
          company: linkedinCompany,
          title: linkedinTitle || undefined,
          warmth: linkedinWarmth,
        });
      }
      setEnrichedPersona(result);
    } catch (err) {
      setError(err.message);
    } finally {
      setEnrichLoading(false);
    }
  };

  const handleUseCommittee = () => {
    const personaIds = committee.members.map(m => m.id).filter(Boolean);
    navigate('/new', { state: { personaIds, committeeInfo: { industry, companySize, warmth, companyName } } });
  };

  const traitBar = (label, value) => (
    <div className="flex items-center gap-2">
      <span className="text-xs text-gray-500 w-28 shrink-0">{label}</span>
      <div className="flex-1 bg-gray-200 rounded-full h-1.5">
        <div
          className={`h-1.5 rounded-full ${value > 0.7 ? 'bg-red-400' : value > 0.4 ? 'bg-yellow-400' : 'bg-green-400'}`}
          style={{ width: `${(value || 0) * 100}%` }}
        ></div>
      </div>
      <span className="text-xs text-gray-400 w-8 text-right">{((value || 0) * 100).toFixed(0)}%</span>
    </div>
  );

  const PersonaCard = ({ persona }) => (
    <div className="bg-white p-5 rounded-xl border border-gray-200 hover:shadow-md transition">
      <div className="flex justify-between items-start mb-3">
        <div>
          <h3 className="font-semibold text-gray-900">{persona.name}</h3>
          <p className="text-sm text-gray-500">{persona.title}</p>
        </div>
        <div className="flex gap-1.5">
          <span className="text-xs bg-blue-50 text-blue-700 px-2 py-0.5 rounded-full">{persona.buying_style}</span>
          <span className="text-xs bg-purple-50 text-purple-700 px-2 py-0.5 rounded-full">{persona.budget_authority}</span>
        </div>
      </div>

      {persona.bio && <p className="text-sm text-gray-600 mb-3">{persona.bio}</p>}

      {persona.personality_traits && (
        <div className="space-y-1 mb-3">
          {traitBar('Skepticism', persona.personality_traits.skepticism)}
          {traitBar('Openness', persona.personality_traits.innovation_openness)}
          {traitBar('Detail Focus', persona.personality_traits.detail_orientation)}
        </div>
      )}

      {persona.pain_points?.length > 0 && (
        <div className="mb-2">
          <p className="text-xs font-medium text-gray-400 mb-1">PAIN POINTS</p>
          <div className="flex flex-wrap gap-1">
            {persona.pain_points.map((pp, i) => (
              <span key={i} className="text-xs bg-orange-50 text-orange-700 px-2 py-0.5 rounded">{pp}</span>
            ))}
          </div>
        </div>
      )}

      {persona.objection_patterns?.length > 0 && (
        <div>
          <p className="text-xs font-medium text-gray-400 mb-1">LIKELY OBJECTIONS</p>
          {persona.objection_patterns.map((obj, i) => (
            <p key={i} className="text-xs text-gray-600 italic mb-1">"{obj}"</p>
          ))}
        </div>
      )}

      {persona.linkedin_insights && (
        <div className="mt-2 p-2 bg-blue-50 rounded-lg">
          <p className="text-xs text-blue-700"><Linkedin className="h-3 w-3 inline mr-1" />{persona.linkedin_insights}</p>
        </div>
      )}
      {persona.company_insights && (
        <div className="mt-2 p-2 bg-indigo-50 rounded-lg">
          <p className="text-xs text-indigo-700"><Building2 className="h-3 w-3 inline mr-1" />{persona.company_insights}</p>
        </div>
      )}
    </div>
  );

  return (
    <div className="max-w-5xl mx-auto">
      {/* Header with tabs */}
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Buying Committee Generator</h1>
          <p className="text-gray-500 mt-1">Create realistic buyer groups with zero manual entry</p>
        </div>
      </div>

      {/* Mode tabs */}
      <div className="flex gap-1 mb-8 bg-gray-100 p-1 rounded-lg w-fit">
        <button
          onClick={() => setStep(step === 'linkedin' ? 'configure' : step)}
          className={`flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition ${
            step !== 'linkedin' ? 'bg-white shadow-sm text-gray-900' : 'text-gray-500 hover:text-gray-700'
          }`}
        >
          <Users className="h-4 w-4" /> Generate Committee
        </button>
        <button
          onClick={() => setStep('linkedin')}
          className={`flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition ${
            step === 'linkedin' ? 'bg-white shadow-sm text-gray-900' : 'text-gray-500 hover:text-gray-700'
          }`}
        >
          <Linkedin className="h-4 w-4" /> Import from LinkedIn
        </button>
      </div>

      {error && <div className="bg-red-50 text-red-600 p-3 rounded-lg mb-6 text-sm">{error}</div>}

      {/* ===== COMMITTEE GENERATOR ===== */}
      {step === 'configure' && (
        <div className="space-y-8">
          {/* Industry */}
          <div>
            <h2 className="text-lg font-semibold mb-3">Industry</h2>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              {INDUSTRIES.map((ind) => {
                const Icon = ind.icon;
                const selected = industry === ind.value;
                return (
                  <button
                    key={ind.value}
                    onClick={() => setIndustry(ind.value)}
                    className={`p-4 rounded-xl border text-left transition ${
                      selected
                        ? 'border-primary-500 bg-primary-50 ring-2 ring-primary-200'
                        : 'border-gray-200 bg-white hover:border-gray-300'
                    }`}
                  >
                    <Icon className={`h-5 w-5 mb-2 ${selected ? 'text-primary-600' : 'text-gray-400'}`} />
                    <span className={`text-sm font-medium ${selected ? 'text-primary-700' : 'text-gray-700'}`}>
                      {ind.value}
                    </span>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Company Size */}
          <div>
            <h2 className="text-lg font-semibold mb-3">Company Size</h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              {COMPANY_SIZES.map((size) => {
                const selected = companySize === size.value;
                return (
                  <button
                    key={size.value}
                    onClick={() => setCompanySize(size.value)}
                    className={`p-5 rounded-xl border text-left transition ${
                      selected
                        ? 'border-primary-500 bg-primary-50 ring-2 ring-primary-200'
                        : 'border-gray-200 bg-white hover:border-gray-300'
                    }`}
                  >
                    <p className={`font-medium ${selected ? 'text-primary-700' : 'text-gray-900'}`}>{size.label}</p>
                    <p className="text-sm text-gray-500 mt-0.5">{size.desc}</p>
                    <p className="text-xs text-gray-400 mt-1">{size.members}</p>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Warmth */}
          <div>
            <h2 className="text-lg font-semibold mb-3">Committee Warmth</h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              {WARMTH_OPTIONS.map((opt) => {
                const Icon = opt.icon;
                const selected = warmth === opt.value;
                return (
                  <button
                    key={opt.value}
                    onClick={() => setWarmth(opt.value)}
                    className={`p-5 rounded-xl border text-left transition ${
                      selected ? opt.selected : opt.bg
                    }`}
                  >
                    <Icon className={`h-8 w-8 mb-2 ${opt.iconColor}`} />
                    <p className="font-medium text-gray-900">{opt.label}</p>
                    <p className="text-sm text-gray-500 mt-1">{opt.desc}</p>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Optional Details */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Company Name (optional)</label>
              <input
                type="text"
                value={companyName}
                onChange={(e) => setCompanyName(e.target.value)}
                placeholder="e.g., Acme Corp"
                className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent outline-none"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">What are you selling? (optional)</label>
              <input
                type="text"
                value={productContext}
                onChange={(e) => setProductContext(e.target.value)}
                placeholder="e.g., AI-powered sales enablement platform"
                className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent outline-none"
              />
            </div>
          </div>

          {/* Generate Button */}
          <div className="flex justify-end">
            <button
              onClick={handleGenerate}
              disabled={!canGenerate || loading}
              className="inline-flex items-center gap-2 bg-primary-600 text-white px-6 py-3 rounded-lg font-medium hover:bg-primary-700 transition disabled:opacity-50 shadow-sm"
            >
              <Sparkles className="h-5 w-5" />
              {loading ? 'Generating Committee...' : 'Generate Buying Committee'}
            </button>
          </div>
        </div>
      )}

      {/* ===== RESULTS ===== */}
      {step === 'results' && committee && (
        <div>
          <div className="flex justify-between items-center mb-6">
            <div>
              <h2 className="text-lg font-semibold">
                {committee.warmth.charAt(0).toUpperCase() + committee.warmth.slice(1)} Committee — {committee.industry}
              </h2>
              <p className="text-sm text-gray-500">
                {committee.committee_size} members · {committee.company_size}
                {companyName ? ` · ${companyName}` : ''}
              </p>
            </div>
            <div className="flex gap-3">
              <button
                onClick={() => { setStep('configure'); setCommittee(null); }}
                className="px-4 py-2 border border-gray-300 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50 transition"
              >
                Generate Another
              </button>
              <button
                onClick={handleUseCommittee}
                className="inline-flex items-center gap-2 bg-primary-600 text-white px-5 py-2 rounded-lg text-sm font-medium hover:bg-primary-700 transition shadow-sm"
              >
                Use in Simulation <ArrowRight className="h-4 w-4" />
              </button>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {committee.members.map((member, i) => (
              <PersonaCard key={member.id || i} persona={member} />
            ))}
          </div>
        </div>
      )}

      {/* ===== LINKEDIN IMPORT ===== */}
      {step === 'linkedin' && (
        <div className="max-w-2xl">
          <div className="flex gap-1 mb-6 bg-gray-100 p-1 rounded-lg w-fit">
            <button
              onClick={() => setLinkedinMode('text')}
              className={`px-4 py-1.5 rounded-md text-sm font-medium transition ${
                linkedinMode === 'text' ? 'bg-white shadow-sm text-gray-900' : 'text-gray-500'
              }`}
            >
              Paste Profile Text
            </button>
            <button
              onClick={() => setLinkedinMode('name')}
              className={`px-4 py-1.5 rounded-md text-sm font-medium transition ${
                linkedinMode === 'name' ? 'bg-white shadow-sm text-gray-900' : 'text-gray-500'
              }`}
            >
              Name + Company
            </button>
          </div>

          {linkedinMode === 'text' ? (
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">LinkedIn Profile Text</label>
                <p className="text-xs text-gray-400 mb-2">Go to their LinkedIn profile, select all text (Ctrl+A), copy and paste it here</p>
                <textarea
                  value={linkedinText}
                  onChange={(e) => setLinkedinText(e.target.value)}
                  rows={10}
                  placeholder="Paste the full text from a LinkedIn profile here..."
                  className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent outline-none resize-none text-sm"
                />
              </div>
            </div>
          ) : (
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Full Name</label>
                <input
                  type="text"
                  value={linkedinName}
                  onChange={(e) => setLinkedinName(e.target.value)}
                  placeholder="e.g., Sarah Chen"
                  className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent outline-none"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Company</label>
                <input
                  type="text"
                  value={linkedinCompany}
                  onChange={(e) => setLinkedinCompany(e.target.value)}
                  placeholder="e.g., Stripe, Goldman Sachs, Mayo Clinic"
                  className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent outline-none"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Title (optional)</label>
                <input
                  type="text"
                  value={linkedinTitle}
                  onChange={(e) => setLinkedinTitle(e.target.value)}
                  placeholder="e.g., VP of Engineering"
                  className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent outline-none"
                />
              </div>
            </div>
          )}

          {/* Warmth for LinkedIn */}
          <div className="mt-6">
            <label className="block text-sm font-medium text-gray-700 mb-2">Assumed Disposition</label>
            <div className="flex gap-2">
              {WARMTH_OPTIONS.map((opt) => {
                const Icon = opt.icon;
                return (
                  <button
                    key={opt.value}
                    onClick={() => setLinkedinWarmth(opt.value)}
                    className={`flex items-center gap-2 px-4 py-2 rounded-lg border text-sm font-medium transition ${
                      linkedinWarmth === opt.value
                        ? opt.selected
                        : 'border-gray-200 bg-white hover:border-gray-300'
                    }`}
                  >
                    <Icon className={`h-4 w-4 ${opt.iconColor}`} />
                    {opt.label}
                  </button>
                );
              })}
            </div>
          </div>

          <button
            onClick={handleLinkedInEnrich}
            disabled={enrichLoading || (linkedinMode === 'text' ? !linkedinText : !linkedinName || !linkedinCompany)}
            className="mt-6 inline-flex items-center gap-2 bg-primary-600 text-white px-6 py-2.5 rounded-lg font-medium hover:bg-primary-700 transition disabled:opacity-50"
          >
            <UserPlus className="h-4 w-4" />
            {enrichLoading ? 'Analyzing...' : 'Generate Persona'}
          </button>

          {enrichedPersona && (
            <div className="mt-6">
              <h3 className="font-semibold mb-3">Generated Persona</h3>
              <PersonaCard persona={enrichedPersona} />
            </div>
          )}
        </div>
      )}
    </div>
  );
}
