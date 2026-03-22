import { useState, useEffect } from 'react';
import { api } from '../api/client';
import { Plus, Search, X, User, Briefcase } from 'lucide-react';

export default function PersonaLibrary() {
  const [personas, setPersonas] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [showCreate, setShowCreate] = useState(false);
  const [newPersona, setNewPersona] = useState({
    name: '', title: '', industry: 'SaaS', company_size: 'mid-market',
    buying_style: 'analytical', bio: '', pain_points: [], objection_patterns: [],
    personality_traits: { skepticism: 0.5, innovation_openness: 0.5, detail_orientation: 0.5 },
    is_public: true,
  });

  useEffect(() => {
    api.listPersonas().then(setPersonas).catch(console.error).finally(() => setLoading(false));
  }, []);

  const handleCreate = async () => {
    try {
      const created = await api.createPersona(newPersona);
      setPersonas([created, ...personas]);
      setShowCreate(false);
      setNewPersona({ name: '', title: '', industry: 'SaaS', company_size: 'mid-market', buying_style: 'analytical', bio: '', pain_points: [], objection_patterns: [], personality_traits: { skepticism: 0.5, innovation_openness: 0.5, detail_orientation: 0.5 }, is_public: true });
    } catch (err) {
      alert(err.message);
    }
  };

  const filtered = personas.filter(p =>
    p.name.toLowerCase().includes(search.toLowerCase()) ||
    p.industry.toLowerCase().includes(search.toLowerCase()) ||
    p.title.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">Persona Library</h1>
        <button onClick={() => setShowCreate(true)} className="inline-flex items-center gap-2 bg-primary-600 text-white px-4 py-2 rounded-lg font-medium hover:bg-primary-700 transition text-sm">
          <Plus className="h-4 w-4" /> Add Persona
        </button>
      </div>

      <div className="relative mb-6">
        <Search className="absolute left-3 top-2.5 h-4 w-4 text-gray-400" />
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search personas by name, title, or industry..."
          className="w-full pl-10 pr-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent outline-none"
        />
      </div>

      {loading ? (
        <div className="text-center py-12 text-gray-400">Loading personas...</div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filtered.map((p) => (
            <div key={p.id} className="bg-white p-5 rounded-xl border border-gray-200 hover:shadow-sm transition">
              <div className="flex items-start gap-3 mb-3">
                <div className="p-2 bg-primary-50 rounded-full">
                  <User className="h-5 w-5 text-primary-600" />
                </div>
                <div>
                  <h3 className="font-medium">{p.name}</h3>
                  <p className="text-sm text-gray-500">{p.title}</p>
                </div>
              </div>
              <div className="flex flex-wrap gap-1.5 mb-3">
                <span className="text-xs bg-blue-50 text-blue-700 px-2 py-0.5 rounded-full">{p.industry}</span>
                <span className="text-xs bg-purple-50 text-purple-700 px-2 py-0.5 rounded-full">{p.company_size}</span>
                <span className="text-xs bg-green-50 text-green-700 px-2 py-0.5 rounded-full">{p.buying_style}</span>
              </div>
              {p.bio && <p className="text-sm text-gray-600 line-clamp-2">{p.bio}</p>}
              {p.pain_points?.length > 0 && (
                <div className="mt-2 flex flex-wrap gap-1">
                  {p.pain_points.slice(0, 3).map((pp, i) => (
                    <span key={i} className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded">{pp}</span>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Create Modal */}
      {showCreate && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl p-6 w-full max-w-lg max-h-[90vh] overflow-y-auto">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-lg font-semibold">Create Persona</h2>
              <button onClick={() => setShowCreate(false)}><X className="h-5 w-5 text-gray-400" /></button>
            </div>
            <div className="space-y-3">
              <input type="text" placeholder="Name (e.g., Sarah Chen)" value={newPersona.name} onChange={(e) => setNewPersona({...newPersona, name: e.target.value})} className="w-full px-3 py-2 border rounded-lg text-sm" />
              <input type="text" placeholder="Title (e.g., VP of Engineering)" value={newPersona.title} onChange={(e) => setNewPersona({...newPersona, title: e.target.value})} className="w-full px-3 py-2 border rounded-lg text-sm" />
              <div className="grid grid-cols-2 gap-3">
                <select value={newPersona.industry} onChange={(e) => setNewPersona({...newPersona, industry: e.target.value})} className="px-3 py-2 border rounded-lg text-sm">
                  {['SaaS', 'Financial Services', 'Healthcare', 'Retail', 'Manufacturing'].map(i => <option key={i} value={i}>{i}</option>)}
                </select>
                <select value={newPersona.company_size} onChange={(e) => setNewPersona({...newPersona, company_size: e.target.value})} className="px-3 py-2 border rounded-lg text-sm">
                  {['early-stage', 'mid-market', 'enterprise'].map(s => <option key={s} value={s}>{s}</option>)}
                </select>
              </div>
              <select value={newPersona.buying_style} onChange={(e) => setNewPersona({...newPersona, buying_style: e.target.value})} className="w-full px-3 py-2 border rounded-lg text-sm">
                {['early-adopter', 'consensus-builder', 'risk-averse', 'analytical'].map(b => <option key={b} value={b}>{b}</option>)}
              </select>
              <textarea placeholder="Bio and background..." value={newPersona.bio} onChange={(e) => setNewPersona({...newPersona, bio: e.target.value})} rows={3} className="w-full px-3 py-2 border rounded-lg text-sm" />

              <div>
                <label className="text-xs font-medium text-gray-500">Skepticism: {newPersona.personality_traits.skepticism}</label>
                <input type="range" min="0" max="1" step="0.1" value={newPersona.personality_traits.skepticism} onChange={(e) => setNewPersona({...newPersona, personality_traits: {...newPersona.personality_traits, skepticism: parseFloat(e.target.value)}})} className="w-full" />
              </div>
              <div>
                <label className="text-xs font-medium text-gray-500">Innovation Openness: {newPersona.personality_traits.innovation_openness}</label>
                <input type="range" min="0" max="1" step="0.1" value={newPersona.personality_traits.innovation_openness} onChange={(e) => setNewPersona({...newPersona, personality_traits: {...newPersona.personality_traits, innovation_openness: parseFloat(e.target.value)}})} className="w-full" />
              </div>

              <button onClick={handleCreate} disabled={!newPersona.name || !newPersona.title} className="w-full bg-primary-600 text-white py-2 rounded-lg font-medium hover:bg-primary-700 transition disabled:opacity-50">
                Create Persona
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
