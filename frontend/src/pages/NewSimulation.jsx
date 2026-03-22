import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../api/client';
import { Zap, ArrowLeft, ArrowRight, Send, Fish, Settings2 } from 'lucide-react';

const INDUSTRIES = ['SaaS', 'Financial Services', 'Healthcare', 'Retail', 'Manufacturing'];
const COMPANY_SIZES = ['early-stage', 'mid-market', 'enterprise'];
const BUYING_STYLES = ['early-adopter', 'consensus-builder', 'risk-averse', 'analytical'];

export default function NewSimulation() {
  const navigate = useNavigate();
  const [step, setStep] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [mirofishAvailable, setMirofishAvailable] = useState(false);

  useEffect(() => {
    api.healthCheck()
      .then(h => setMirofishAvailable(h.mirofish_available))
      .catch(() => setMirofishAvailable(false));
  }, []);

  const [form, setForm] = useState({
    pitch_title: '',
    pitch_content: '',
    company_name: '',
    industry: '',
    target_audience: '',
    num_personas: 10,
    num_agents: 50,
    num_rounds: 20,
    use_mirofish: true,
    persona_filters: {
      industries: [],
      company_sizes: [],
      buying_styles: [],
    },
  });

  const update = (key) => (e) => setForm({ ...form, [key]: e.target.value });

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
          use_mirofish: form.use_mirofish,
          num_agents: form.num_agents,
          num_rounds: form.num_rounds,
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
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Your Company</label>
              <input type="text" value={form.company_name} onChange={update('company_name')} placeholder="Company name" className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent outline-none" />
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
          <h2 className="text-lg font-semibold">Select Buyer Personas</h2>

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

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Number of Personas ({form.num_personas})</label>
            <input
              type="range"
              min="1"
              max="50"
              value={form.num_personas}
              onChange={(e) => setForm({ ...form, num_personas: parseInt(e.target.value) })}
              className="w-full"
            />
            <div className="flex justify-between text-xs text-gray-400">
              <span>1</span><span>50</span>
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
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-sm text-gray-500">Company</p>
                <p className="font-medium">{form.company_name || 'Not specified'}</p>
              </div>
              <div>
                <p className="text-sm text-gray-500">Target Audience</p>
                <p className="font-medium">{form.target_audience || 'All personas'}</p>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-sm text-gray-500">Personas</p>
                <p className="font-medium">{form.num_personas}</p>
              </div>
              <div>
                <p className="text-sm text-gray-500">Filters</p>
                <p className="font-medium text-sm">
                  {[...form.persona_filters.industries, ...form.persona_filters.company_sizes, ...form.persona_filters.buying_styles].join(', ') || 'None (all personas)'}
                </p>
              </div>
            </div>
          </div>

          {/* MiroFish Swarm Configuration */}
          <div className="bg-white p-6 rounded-xl border border-gray-200 space-y-4">
            <div className="flex items-center gap-2 mb-2">
              <Fish className="h-5 w-5 text-primary-600" />
              <h3 className="font-semibold">Simulation Engine</h3>
            </div>

            <div className="flex items-center gap-3">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={form.use_mirofish}
                  onChange={(e) => setForm({ ...form, use_mirofish: e.target.checked })}
                  className="rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                />
                <span className="text-sm font-medium">
                  Use MiroFish Swarm Intelligence
                  {mirofishAvailable
                    ? <span className="ml-2 text-xs text-emerald-600">(Connected)</span>
                    : <span className="ml-2 text-xs text-amber-600">(Will use fallback if unavailable)</span>
                  }
                </span>
              </label>
            </div>

            {form.use_mirofish && (
              <div className="grid grid-cols-2 gap-4 pt-2">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    AI Agents ({form.num_agents})
                  </label>
                  <input
                    type="range"
                    min="10"
                    max="200"
                    step="10"
                    value={form.num_agents}
                    onChange={(e) => setForm({ ...form, num_agents: parseInt(e.target.value) })}
                    className="w-full"
                  />
                  <div className="flex justify-between text-xs text-gray-400">
                    <span>10</span><span>200</span>
                  </div>
                  <p className="text-xs text-gray-500 mt-1">Autonomous buyer agents in the swarm</p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Simulation Rounds ({form.num_rounds})
                  </label>
                  <input
                    type="range"
                    min="5"
                    max="50"
                    step="5"
                    value={form.num_rounds}
                    onChange={(e) => setForm({ ...form, num_rounds: parseInt(e.target.value) })}
                    className="w-full"
                  />
                  <div className="flex justify-between text-xs text-gray-400">
                    <span>5</span><span>50</span>
                  </div>
                  <p className="text-xs text-gray-500 mt-1">Interaction rounds (more = deeper dynamics)</p>
                </div>
              </div>
            )}
          </div>

          <div className="flex justify-between">
            <button onClick={() => setStep(2)} className="text-gray-500 hover:text-gray-700 text-sm">Back</button>
            <button
              onClick={handleSubmit}
              disabled={loading}
              className="inline-flex items-center gap-2 bg-primary-600 text-white px-6 py-2.5 rounded-lg font-medium hover:bg-primary-700 transition disabled:opacity-50 shadow-sm"
            >
              {form.use_mirofish ? <Fish className="h-4 w-4" /> : <Send className="h-4 w-4" />}
              {loading ? 'Launching...' : form.use_mirofish ? 'Launch Swarm Simulation' : 'Launch Simulation'}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
