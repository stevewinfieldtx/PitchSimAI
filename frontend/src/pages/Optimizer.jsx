import { useState, useEffect, useRef } from 'react';
import { useSearchParams, useNavigate, Link } from 'react-router-dom';
import { api } from '../api/client';
import { ArrowLeft, Zap, RefreshCw, ChevronDown, ChevronUp, Check, X, TrendingUp, Target, Copy } from 'lucide-react';

export default function Optimizer() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const simId = searchParams.get('simulation');

  const [loading, setLoading] = useState(false);
  const [jobId, setJobId] = useState(null);
  const [status, setStatus] = useState(null);
  const [error, setError] = useState('');
  const [expandedIter, setExpandedIter] = useState(null);
  const [copied, setCopied] = useState(false);
  const pollRef = useRef(null);

  // Form for standalone optimization
  const [form, setForm] = useState({
    pitch_content: '',
    pitch_title: '',
    company_name: '',
    industry: 'Cybersecurity',
    target_audience: '',
    max_iterations: 5,
    target_score: 85,
  });

  // If coming from a simulation, auto-start
  useEffect(() => {
    if (simId) {
      startFromSimulation(simId);
    }
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [simId]);

  const startFromSimulation = async (simulationId) => {
    setLoading(true);
    setError('');
    try {
      const result = await api.optimizeFromSimulation({
        simulation_id: simulationId,
        max_iterations: 5,
        target_score: 85,
      });
      setJobId(result.job_id);
      startPolling(result.job_id);
    } catch (err) {
      setError(err.message);
      setLoading(false);
    }
  };

  const startOptimization = async () => {
    if (!form.pitch_content) return;
    setLoading(true);
    setError('');
    try {
      const result = await api.startOptimization(form);
      setJobId(result.job_id);
      startPolling(result.job_id);
    } catch (err) {
      setError(err.message);
      setLoading(false);
    }
  };

  const startPolling = (id) => {
    pollRef.current = setInterval(async () => {
      try {
        const s = await api.getOptimizationStatus(id);
        setStatus(s);
        if (s.status === 'completed' || s.status === 'failed') {
          clearInterval(pollRef.current);
          setLoading(false);
          if (s.status === 'failed') setError(s.detail);
        }
      } catch {
        // Keep polling
      }
    }, 3000);
  };

  const copyPitch = (text) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const result = status?.result;

  // ── Running State ──
  if (loading && status) {
    return (
      <div className="max-w-3xl mx-auto">
        <h1 className="text-2xl font-bold mb-6">AutoOptimizer</h1>
        <div className="bg-white p-8 rounded-xl border border-gray-200 text-center">
          <RefreshCw className="h-10 w-10 text-primary-600 mx-auto mb-4 animate-spin" />
          <h2 className="text-lg font-semibold mb-2">{status.stage === 'optimizing' ? 'Optimizing...' : 'Starting...'}</h2>
          <p className="text-gray-600 mb-4">{status.detail}</p>
          <div className="w-full bg-gray-200 rounded-full h-3 mb-2">
            <div
              className="bg-primary-600 h-3 rounded-full transition-all duration-500"
              style={{ width: `${status.progress_pct}%` }}
            />
          </div>
          <p className="text-sm text-gray-500">{status.progress_pct}%</p>
        </div>
      </div>
    );
  }

  // ── Results State ──
  if (result) {
    const origScores = result.original_scores || {};
    const optScores = result.optimized_scores || {};
    const summary = result.summary || {};
    const progression = result.score_progression || [];

    return (
      <div className="max-w-4xl mx-auto">
        <button onClick={() => navigate(-1)} className="flex items-center gap-1 text-gray-500 hover:text-gray-700 mb-6 text-sm">
          <ArrowLeft className="h-4 w-4" /> Back
        </button>

        <div className="flex items-center gap-3 mb-6">
          <Zap className="h-6 w-6 text-primary-600" />
          <h1 className="text-2xl font-bold">AutoOptimizer Results</h1>
        </div>

        {/* Summary Card */}
        <div className="bg-gradient-to-r from-primary-50 to-emerald-50 p-6 rounded-xl border border-primary-200 mb-6">
          <h2 className="font-semibold text-lg mb-2">{summary.headline || 'Optimization Complete'}</h2>
          <p className="text-primary-700 font-medium mb-3">{summary.total_improvement}</p>
          <div className="grid grid-cols-4 gap-4 text-center">
            <div>
              <p className="text-xs text-gray-500">Iterations</p>
              <p className="text-xl font-bold">{result.total_iterations}</p>
            </div>
            <div>
              <p className="text-xs text-gray-500">Kept</p>
              <p className="text-xl font-bold text-emerald-600">{result.kept_count}</p>
            </div>
            <div>
              <p className="text-xs text-gray-500">Reverted</p>
              <p className="text-xl font-bold text-red-500">{result.reverted_count}</p>
            </div>
            <div>
              <p className="text-xs text-gray-500">Time</p>
              <p className="text-xl font-bold">{Math.round(result.elapsed_seconds)}s</p>
            </div>
          </div>
        </div>

        {/* Score Comparison */}
        <div className="grid grid-cols-2 gap-4 mb-6">
          <div className="bg-white p-5 rounded-xl border border-gray-200">
            <p className="text-xs font-medium text-gray-500 uppercase mb-3">Original Scores</p>
            {Object.entries(origScores).map(([key, val]) => (
              <div key={key} className="flex justify-between items-center py-1.5">
                <span className="text-sm text-gray-600">{key.replace(/_/g, ' ')}</span>
                <span className="font-mono text-sm">{typeof val === 'number' ? val : '-'}</span>
              </div>
            ))}
          </div>
          <div className="bg-white p-5 rounded-xl border border-emerald-200">
            <p className="text-xs font-medium text-emerald-600 uppercase mb-3">Optimized Scores</p>
            {Object.entries(optScores).map(([key, val]) => {
              const orig = origScores[key];
              const diff = typeof val === 'number' && typeof orig === 'number' ? val - orig : null;
              return (
                <div key={key} className="flex justify-between items-center py-1.5">
                  <span className="text-sm text-gray-600">{key.replace(/_/g, ' ')}</span>
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-sm font-medium">{typeof val === 'number' ? val : '-'}</span>
                    {diff !== null && diff !== 0 && (
                      <span className={`text-xs font-medium ${diff > 0 ? 'text-emerald-600' : 'text-red-500'}`}>
                        {diff > 0 ? '+' : ''}{diff}
                      </span>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Score Progression */}
        {progression.length > 1 && (
          <div className="bg-white p-5 rounded-xl border border-gray-200 mb-6">
            <h3 className="font-semibold text-sm mb-3">Score Progression</h3>
            <div className="flex items-end gap-1 h-24">
              {progression.map((p, idx) => {
                const engagement = p.engagement || 0;
                return (
                  <div key={idx} className="flex-1 flex flex-col items-center gap-1">
                    <div
                      className={`w-full rounded-t transition-all ${
                        p.kept !== false ? 'bg-primary-400' : 'bg-red-300'
                      }`}
                      style={{ height: `${Math.max(4, engagement)}%` }}
                      title={`Iter ${p.iteration}: ${engagement}`}
                    />
                    <span className="text-[10px] text-gray-400">{p.iteration}</span>
                  </div>
                );
              })}
            </div>
            <div className="flex justify-between text-[10px] text-gray-400 mt-1">
              <span>Baseline</span>
              <span>Final</span>
            </div>
          </div>
        )}

        {/* What Worked / What Didn't */}
        {summary.key_changes_that_worked && (
          <div className="grid grid-cols-2 gap-4 mb-6">
            <div className="bg-white p-5 rounded-xl border border-gray-200">
              <h3 className="font-semibold text-sm text-emerald-700 mb-2 flex items-center gap-1">
                <Check className="h-4 w-4" /> Changes That Worked
              </h3>
              <ul className="space-y-2">
                {summary.key_changes_that_worked.map((c, i) => (
                  <li key={i} className="text-sm text-gray-700">{c}</li>
                ))}
              </ul>
            </div>
            <div className="bg-white p-5 rounded-xl border border-gray-200">
              <h3 className="font-semibold text-sm text-red-600 mb-2 flex items-center gap-1">
                <X className="h-4 w-4" /> Changes That Backfired
              </h3>
              <ul className="space-y-2">
                {(summary.changes_that_backfired || []).length > 0
                  ? summary.changes_that_backfired.map((c, i) => (
                      <li key={i} className="text-sm text-gray-700">{c}</li>
                    ))
                  : <li className="text-sm text-gray-400">All changes improved the pitch!</li>
                }
              </ul>
            </div>
          </div>
        )}

        {/* Optimized Pitch */}
        <div className="bg-white p-6 rounded-xl border border-emerald-200 mb-6">
          <div className="flex justify-between items-center mb-3">
            <h3 className="font-semibold">Optimized Pitch</h3>
            <button
              onClick={() => copyPitch(result.optimized_pitch)}
              className="inline-flex items-center gap-1.5 text-sm text-primary-600 hover:text-primary-700"
            >
              <Copy className="h-3.5 w-3.5" />
              {copied ? 'Copied!' : 'Copy'}
            </button>
          </div>
          <div className="text-sm text-gray-700 whitespace-pre-wrap max-h-96 overflow-y-auto">
            {result.optimized_pitch}
          </div>
        </div>

        {/* Iteration Details (Collapsible) */}
        <div className="mb-6">
          <h3 className="font-semibold text-sm mb-3">Iteration Details</h3>
          <div className="space-y-2">
            {(result.iterations || []).map((iter, idx) => (
              <div key={idx} className="bg-white rounded-xl border border-gray-200 overflow-hidden">
                <button
                  onClick={() => setExpandedIter(expandedIter === idx ? null : idx)}
                  className="w-full px-4 py-3 flex justify-between items-center text-left hover:bg-gray-50"
                >
                  <div className="flex items-center gap-3">
                    <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                      iter.iteration === 0 ? 'bg-gray-100 text-gray-600' :
                      iter.kept ? 'bg-emerald-100 text-emerald-700' : 'bg-red-100 text-red-600'
                    }`}>
                      {iter.iteration === 0 ? 'BASELINE' : iter.kept ? 'KEPT' : 'REVERTED'}
                    </span>
                    <span className="text-sm font-medium">
                      Iteration {iter.iteration}
                    </span>
                    <span className="text-xs text-gray-500">
                      engagement: {iter.scores?.overall_engagement || '-'}
                    </span>
                  </div>
                  {expandedIter === idx ? <ChevronUp className="h-4 w-4 text-gray-400" /> : <ChevronDown className="h-4 w-4 text-gray-400" />}
                </button>
                {expandedIter === idx && (
                  <div className="px-4 pb-4 border-t border-gray-100">
                    <p className="text-sm text-gray-600 mt-3 mb-2">{iter.changes_made}</p>
                    {iter.objections?.length > 0 && (
                      <div className="mt-2">
                        <p className="text-xs font-medium text-gray-500 mb-1">Objections:</p>
                        <ul className="text-xs text-gray-600 space-y-1">
                          {iter.objections.slice(0, 3).map((o, oi) => <li key={oi}>- {o}</li>)}
                        </ul>
                      </div>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  // ── Input State (no simId) ──
  return (
    <div className="max-w-3xl mx-auto">
      <button onClick={() => navigate(-1)} className="flex items-center gap-1 text-gray-500 hover:text-gray-700 mb-6 text-sm">
        <ArrowLeft className="h-4 w-4" /> Back
      </button>

      <div className="flex items-center gap-3 mb-2">
        <Zap className="h-6 w-6 text-primary-600" />
        <h1 className="text-2xl font-bold">AutoOptimizer</h1>
      </div>
      <p className="text-gray-500 mb-6">
        Paste a pitch. The optimizer runs it through buying committees, rewrites it based on
        their feedback, re-evaluates, and keeps iterating — automatically.
      </p>

      {error && <div className="bg-red-50 text-red-600 p-3 rounded-lg mb-4 text-sm">{error}</div>}

      <div className="space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Pitch Title</label>
            <input type="text" value={form.pitch_title} onChange={e => setForm({...form, pitch_title: e.target.value})} placeholder="My Pitch" className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 outline-none" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Company</label>
            <input type="text" value={form.company_name} onChange={e => setForm({...form, company_name: e.target.value})} placeholder="Company name" className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 outline-none" />
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Pitch Content</label>
          <textarea value={form.pitch_content} onChange={e => setForm({...form, pitch_content: e.target.value})} rows={10} placeholder="Paste your pitch..." className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 outline-none resize-none" />
        </div>

        <div className="grid grid-cols-3 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Industry</label>
            <input type="text" value={form.industry} onChange={e => setForm({...form, industry: e.target.value})} className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 outline-none" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Target Audience</label>
            <input type="text" value={form.target_audience} onChange={e => setForm({...form, target_audience: e.target.value})} placeholder="e.g., CISOs at enterprise" className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 outline-none" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Iterations (max {form.max_iterations})</label>
            <input type="range" min="1" max="10" value={form.max_iterations} onChange={e => setForm({...form, max_iterations: parseInt(e.target.value)})} className="w-full mt-2" />
          </div>
        </div>

        <div className="flex justify-end">
          <button
            onClick={startOptimization}
            disabled={!form.pitch_content || loading}
            className="inline-flex items-center gap-2 bg-primary-600 text-white px-6 py-2.5 rounded-lg font-medium hover:bg-primary-700 transition disabled:opacity-50 shadow-sm"
          >
            <Zap className="h-4 w-4" />
            {loading ? 'Starting...' : `Optimize (${form.max_iterations} iterations)`}
          </button>
        </div>
      </div>
    </div>
  );
}
