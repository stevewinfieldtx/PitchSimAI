import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { api } from '../api/client';
import { ArrowLeft, MessageSquare, RefreshCw, TrendingUp, TrendingDown, AlertTriangle, Lightbulb, Zap } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';

const SENTIMENT_COLORS = {
  very_positive: '#22c55e',
  positive: '#86efac',
  neutral: '#fbbf24',
  negative: '#fb923c',
  very_negative: '#ef4444',
};

export default function SimulationResults() {
  const { id } = useParams();
  const [sim, setSim] = useState(null);
  const [responses, setResponses] = useState([]);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState('overview');

  const fetchData = async () => {
    try {
      const simData = await api.getSimulation(id);
      setSim(simData);
      if (simData.status === 'completed') {
        const resp = await api.getSimulationResponses(id);
        setResponses(resp);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    // Poll if running
    const interval = setInterval(() => {
      if (sim?.status === 'running' || sim?.status === 'pending') {
        fetchData();
      }
    }, 3000);
    return () => clearInterval(interval);
  }, [id, sim?.status]);

  if (loading) return <div className="text-center py-12 text-gray-400">Loading simulation...</div>;
  if (!sim) return <div className="text-center py-12 text-red-500">Simulation not found</div>;

  const isRunning = sim.status === 'running' || sim.status === 'pending';
  const results = sim.results;

  // Chart data
  const sentimentData = results?.sentiment_breakdown
    ? Object.entries(results.sentiment_breakdown).map(([key, value]) => ({ name: key.replace('_', ' '), value, fill: SENTIMENT_COLORS[key] }))
    : [];

  const industryData = results?.engagement_by_industry
    ? Object.entries(results.engagement_by_industry).map(([name, score]) => ({ name, score }))
    : [];

  const objectionData = results?.objection_frequency
    ? Object.entries(results.objection_frequency).map(([name, count]) => ({ name, count })).sort((a, b) => b.count - a.count)
    : [];

  return (
    <div>
      <Link to="/" className="flex items-center gap-1 text-gray-500 hover:text-gray-700 mb-6 text-sm">
        <ArrowLeft className="h-4 w-4" /> Back to Dashboard
      </Link>

      <div className="flex justify-between items-start mb-6">
        <div>
          <h1 className="text-2xl font-bold">{sim.pitch_title}</h1>
          <p className="text-gray-500 mt-1">
            {sim.num_personas} personas · {new Date(sim.created_at).toLocaleString()}
          </p>
        </div>
        <div className="flex items-center gap-2">
          {isRunning && (
            <div className="flex items-center gap-2 text-blue-600 bg-blue-50 px-4 py-2 rounded-lg">
              <RefreshCw className="h-4 w-4 animate-spin" />
              <span className="font-medium">{sim.progress_pct}% complete</span>
            </div>
          )}
          {sim.status === 'completed' && (
            <Link
              to={`/optimizer?simulation=${id}`}
              className="inline-flex items-center gap-2 bg-primary-600 text-white px-4 py-2 rounded-lg font-medium hover:bg-primary-700 transition text-sm shadow-sm"
            >
              <Zap className="h-4 w-4" />
              AutoOptimize This Pitch
            </Link>
          )}
        </div>
      </div>

      {isRunning && (
        <div className="bg-white p-8 rounded-xl border border-gray-200 text-center">
          <RefreshCw className="h-12 w-12 text-primary-400 mx-auto mb-4 animate-spin" />
          <h2 className="text-lg font-semibold mb-2">Simulation Running</h2>
          <p className="text-gray-500 mb-4">Your personas are evaluating the pitch...</p>
          <div className="w-full max-w-md mx-auto bg-gray-200 rounded-full h-3">
            <div className="bg-primary-600 h-3 rounded-full transition-all duration-500" style={{ width: `${sim.progress_pct}%` }}></div>
          </div>
        </div>
      )}

      {sim.status === 'completed' && results && (
        <>
          {/* Score Cards */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
            <div className="bg-white p-5 rounded-xl border border-gray-200">
              <div className="flex items-center gap-2 mb-2">
                <TrendingUp className="h-5 w-5 text-green-600" />
                <span className="text-sm text-gray-500">Engagement Score</span>
              </div>
              <p className="text-3xl font-bold">{results.overall_engagement_score?.toFixed(1)}</p>
              <p className="text-xs text-gray-400 mt-1">out of 100</p>
            </div>
            <div className="bg-white p-5 rounded-xl border border-gray-200">
              <div className="flex items-center gap-2 mb-2">
                {results.overall_sentiment_score >= 0 ? <TrendingUp className="h-5 w-5 text-green-600" /> : <TrendingDown className="h-5 w-5 text-red-600" />}
                <span className="text-sm text-gray-500">Sentiment Score</span>
              </div>
              <p className="text-3xl font-bold">{results.overall_sentiment_score?.toFixed(1)}</p>
              <p className="text-xs text-gray-400 mt-1">-100 to +100</p>
            </div>
            <div className="bg-white p-5 rounded-xl border border-gray-200">
              <div className="flex items-center gap-2 mb-2">
                <AlertTriangle className="h-5 w-5 text-yellow-600" />
                <span className="text-sm text-gray-500">Top Objections</span>
              </div>
              <p className="text-3xl font-bold">{results.key_objections?.length || 0}</p>
              <p className="text-xs text-gray-400 mt-1">unique objections</p>
            </div>
          </div>

          {/* Tabs */}
          <div className="flex gap-1 mb-6 bg-gray-100 p-1 rounded-lg w-fit">
            {['overview', 'personas', 'recommendations'].map(t => (
              <button key={t} onClick={() => setTab(t)} className={`px-4 py-1.5 rounded-md text-sm font-medium transition ${tab === t ? 'bg-white shadow-sm text-gray-900' : 'text-gray-500 hover:text-gray-700'}`}>
                {t.charAt(0).toUpperCase() + t.slice(1)}
              </button>
            ))}
          </div>

          {/* Overview Tab */}
          {tab === 'overview' && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="bg-white p-5 rounded-xl border border-gray-200">
                <h3 className="font-semibold mb-4">Sentiment Breakdown</h3>
                <ResponsiveContainer width="100%" height={250}>
                  <PieChart>
                    <Pie data={sentimentData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={90} label={({ name, value }) => `${name}: ${value}`}>
                      {sentimentData.map((entry, i) => <Cell key={i} fill={entry.fill} />)}
                    </Pie>
                    <Tooltip />
                  </PieChart>
                </ResponsiveContainer>
              </div>
              <div className="bg-white p-5 rounded-xl border border-gray-200">
                <h3 className="font-semibold mb-4">Engagement by Industry</h3>
                <ResponsiveContainer width="100%" height={250}>
                  <BarChart data={industryData}>
                    <XAxis dataKey="name" fontSize={12} />
                    <YAxis domain={[0, 100]} fontSize={12} />
                    <Tooltip />
                    <Bar dataKey="score" fill="#6366f1" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
              <div className="bg-white p-5 rounded-xl border border-gray-200 md:col-span-2">
                <h3 className="font-semibold mb-4">Objection Frequency</h3>
                <ResponsiveContainer width="100%" height={200}>
                  <BarChart data={objectionData} layout="vertical">
                    <XAxis type="number" fontSize={12} />
                    <YAxis type="category" dataKey="name" width={120} fontSize={12} />
                    <Tooltip />
                    <Bar dataKey="count" fill="#f59e0b" radius={[0, 4, 4, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          )}

          {/* Personas Tab */}
          {tab === 'personas' && (
            <div className="space-y-3">
              {responses.map((r) => (
                <div key={r.id} className="bg-white p-5 rounded-xl border border-gray-200">
                  <div className="flex justify-between items-start mb-3">
                    <div>
                      <h3 className="font-medium">{r.persona_name}</h3>
                      <p className="text-sm text-gray-500">{r.persona_title} · {r.industry} · {r.company_size}</p>
                    </div>
                    <div className="flex items-center gap-3">
                      <span className={`text-sm font-medium px-2 py-0.5 rounded-full ${
                        r.sentiment?.includes('positive') ? 'bg-green-50 text-green-700' :
                        r.sentiment === 'neutral' ? 'bg-yellow-50 text-yellow-700' :
                        'bg-red-50 text-red-700'
                      }`}>{r.sentiment}</span>
                      <span className="text-sm font-bold">{r.engagement_score?.toFixed(0)}/100</span>
                      <Link to={`/simulation/${id}/chat/${r.persona_id}`} className="inline-flex items-center gap-1 text-sm text-primary-600 hover:text-primary-700 font-medium">
                        <MessageSquare className="h-4 w-4" /> Chat
                      </Link>
                    </div>
                  </div>
                  <p className="text-sm text-gray-700 mb-3">{r.initial_reaction}</p>
                  {r.objections?.length > 0 && (
                    <div className="flex flex-wrap gap-1.5">
                      {r.objections.map((obj, i) => (
                        <span key={i} className="text-xs bg-gray-100 text-gray-600 px-2 py-1 rounded">{obj}</span>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}

          {/* Recommendations Tab */}
          {tab === 'recommendations' && (
            <div className="bg-white p-6 rounded-xl border border-gray-200">
              <div className="flex items-center gap-2 mb-4">
                <Lightbulb className="h-5 w-5 text-yellow-500" />
                <h3 className="font-semibold">Recommendations</h3>
              </div>
              <div className="space-y-3">
                {results.key_recommendations?.map((rec, i) => (
                  <div key={i} className="flex gap-3 p-3 bg-yellow-50 rounded-lg">
                    <span className="text-yellow-600 font-bold text-sm">{i + 1}</span>
                    <p className="text-sm text-gray-700">{rec}</p>
                  </div>
                ))}
              </div>
              {results.key_objections?.length > 0 && (
                <div className="mt-6">
                  <h4 className="font-medium mb-3">Top Objections to Address</h4>
                  <div className="space-y-2">
                    {results.key_objections.map((obj, i) => (
                      <div key={i} className="flex items-start gap-2 text-sm">
                        <AlertTriangle className="h-4 w-4 text-orange-500 mt-0.5 shrink-0" />
                        <span>{obj}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </>
      )}

      {sim.status === 'failed' && (
        <div className="bg-red-50 p-8 rounded-xl text-center">
          <AlertTriangle className="h-12 w-12 text-red-400 mx-auto mb-4" />
          <h2 className="text-lg font-semibold text-red-800 mb-2">Simulation Failed</h2>
          <p className="text-red-600">Something went wrong. Please try again.</p>
        </div>
      )}
    </div>
  );
}
