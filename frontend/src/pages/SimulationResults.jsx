import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { api } from '../api/client';
import {
  ArrowLeft, RefreshCw, Zap, TrendingUp, TrendingDown, AlertTriangle,
  Lightbulb, Shield, Target, Brain, Users, ChevronDown, ChevronRight,
  Clock, CheckCircle2, XCircle, AlertCircle, Crosshair, BarChart3,
  Sparkles, Eye, ThumbsUp, ThumbsDown, Scale, Copy, Check
} from 'lucide-react';

// ─── Outcome color schemes ───
const OUTCOME_STYLES = {
  likely_win: { bg: 'bg-emerald-50', border: 'border-emerald-200', text: 'text-emerald-800', badge: 'bg-emerald-600', icon: CheckCircle2 },
  possible_win: { bg: 'bg-blue-50', border: 'border-blue-200', text: 'text-blue-800', badge: 'bg-blue-600', icon: TrendingUp },
  needs_work: { bg: 'bg-amber-50', border: 'border-amber-200', text: 'text-amber-800', badge: 'bg-amber-600', icon: AlertCircle },
  likely_loss: { bg: 'bg-red-50', border: 'border-red-200', text: 'text-red-800', badge: 'bg-red-600', icon: XCircle },
};

const VARIANT_LABELS = {
  conservative: { label: 'Conservative', color: 'bg-slate-100 text-slate-700' },
  'innovation-forward': { label: 'Innovation Forward', color: 'bg-violet-100 text-violet-700' },
  'cost-conscious': { label: 'Cost Conscious', color: 'bg-amber-100 text-amber-700' },
  'enterprise-cautious': { label: 'Enterprise Cautious', color: 'bg-blue-100 text-blue-700' },
  'growth-stage': { label: 'Growth Stage', color: 'bg-emerald-100 text-emerald-700' },
};

const SEVERITY_COLORS = {
  high: 'bg-red-100 text-red-700 border-red-200',
  medium: 'bg-amber-100 text-amber-700 border-amber-200',
  low: 'bg-slate-100 text-slate-600 border-slate-200',
};

const ROLE_ICONS = {
  champion: '🟢',
  skeptic: '🟡',
  blocker: '🔴',
  decision_maker: '👑',
  influencer: '🔵',
};

// ─── Score bar component ───
function ScoreBar({ label, value, max = 100, inverted = false, icon: Icon }) {
  const pct = Math.min(100, Math.max(0, (value / max) * 100));
  const displayVal = inverted ? max - value : value;
  const barColor = inverted
    ? (value > 60 ? 'bg-red-500' : value > 35 ? 'bg-amber-500' : 'bg-emerald-500')
    : (value > 70 ? 'bg-emerald-500' : value > 45 ? 'bg-amber-500' : 'bg-red-500');

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-4">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          {Icon && <Icon className="h-4 w-4 text-gray-400" />}
          <span className="text-sm text-gray-500 font-medium">{label}</span>
        </div>
        <span className="text-lg font-bold">{value?.toFixed?.(0) ?? value}</span>
      </div>
      <div className="w-full bg-gray-100 rounded-full h-2">
        <div className={`${barColor} h-2 rounded-full transition-all duration-700`} style={{ width: `${pct}%` }} />
      </div>
      {inverted && <p className="text-xs text-gray-400 mt-1">Lower is better</p>}
    </div>
  );
}

// ─── Committee Table Accordion ───
function CommitteeAccordion({ table, index }) {
  const [open, setOpen] = useState(false);
  const variant = VARIANT_LABELS[table.variant] || { label: table.variant, color: 'bg-gray-100 text-gray-700' };
  const scores = table.scores || {};
  const verdict = scores.verdict;
  const verdictColor = verdict === 'advance' ? 'text-emerald-600' : verdict === 'decline' ? 'text-red-600' : 'text-amber-600';

  return (
    <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
      <button onClick={() => setOpen(!open)} className="w-full flex items-center justify-between p-4 hover:bg-gray-50 transition">
        <div className="flex items-center gap-3">
          {open ? <ChevronDown className="h-5 w-5 text-gray-400" /> : <ChevronRight className="h-5 w-5 text-gray-400" />}
          <span className="font-semibold">Table {index + 1}</span>
          <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${variant.color}`}>{variant.label}</span>
        </div>
        <div className="flex items-center gap-4 text-sm">
          <span>Engagement <strong>{scores.engagement ?? '—'}</strong></span>
          <span>Sentiment <strong>{scores.sentiment ?? '—'}</strong></span>
          <span>Deal <strong>{scores.deal_probability ?? '—'}%</strong></span>
          {verdict && <span className={`font-semibold capitalize ${verdictColor}`}>{verdict.replace('_', ' ')}</span>}
        </div>
      </button>

      {open && (
        <div className="border-t border-gray-100">
          {/* Personas list */}
          <div className="px-4 py-3 bg-gray-50 border-b border-gray-100">
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Committee Members</p>
            <div className="flex flex-wrap gap-2">
              {(table.personas || []).map((p, i) => (
                <span key={i} className="inline-flex items-center gap-1 text-xs bg-white border border-gray-200 rounded-full px-2.5 py-1">
                  <span>{ROLE_ICONS[p.role_in_committee] || '⚪'}</span>
                  <span className="font-medium">{p.name}</span>
                  <span className="text-gray-400">· {p.title}</span>
                </span>
              ))}
            </div>
          </div>

          {/* Debate rounds */}
          <div className="divide-y divide-gray-100">
            {(table.rounds || []).map((round, ri) => (
              <div key={ri} className="px-4 py-3">
                <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">
                  {round.round === 'initial_reaction' ? '💭 Initial Reactions' : `🗣️ ${round.round.replace('_', ' ').replace('debate', 'Debate Round')}`}
                </p>
                <div className="space-y-3">
                  {(round.responses || []).map((resp, rri) => (
                    <div key={rri} className="flex gap-3">
                      <div className="shrink-0 w-8 h-8 rounded-full bg-gray-100 flex items-center justify-center text-xs">
                        {ROLE_ICONS[resp.role] || '⚪'}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-0.5">
                          <span className="text-sm font-semibold">{resp.persona}</span>
                          <span className="text-xs text-gray-400">{resp.title}</span>
                        </div>
                        <p className="text-sm text-gray-700 whitespace-pre-wrap">{resp.response}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>

          {/* Table summary */}
          {table.summary && (
            <div className="px-4 py-3 bg-gray-50 border-t border-gray-100">
              <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Committee Summary</p>
              <p className="text-sm text-gray-700">{table.summary}</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ─── Main Component ───
export default function SimulationResults() {
  const { id } = useParams();
  const [sim, setSim] = useState(null);
  const [responses, setResponses] = useState(null);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState('insights');
  const [copiedPitch, setCopiedPitch] = useState(false);

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
    const interval = setInterval(() => {
      if (sim?.status === 'running' || sim?.status === 'pending') fetchData();
    }, 3000);
    return () => clearInterval(interval);
  }, [id, sim?.status]);

  if (loading) return (
    <div className="flex items-center justify-center py-20">
      <RefreshCw className="h-6 w-6 text-gray-400 animate-spin mr-3" />
      <span className="text-gray-400">Loading simulation...</span>
    </div>
  );
  if (!sim) return <div className="text-center py-12 text-red-500">Simulation not found</div>;

  const isRunning = sim.status === 'running' || sim.status === 'pending';
  const isSwarm = sim.engine === 'pitchsim_swarm';
  const results = sim.results || {};
  const consensus = sim.consensus || {};
  const swarmScores = sim.swarm_scores || consensus.scores || {};
  const dealPrediction = sim.deal_prediction || {};
  const crossInsights = sim.cross_table_insights || {};
  const bestApproach = sim.best_pitch_approach || '';
  const debateTranscript = sim.debate_transcript || [];
  const metadata = sim.metadata || {};

  // Structured data from consensus
  const topObjections = consensus.top_objections || [];
  const topStrengths = consensus.top_strengths || [];
  const recommendations = consensus.recommendations || [];
  const execSummary = consensus.executive_summary || results.next_steps_suggested || '';

  // Fallback: if consensus doesn't have structured data, use flat strings from results
  const objectionsList = topObjections.length > 0 ? topObjections :
    (results.key_objections || []).map(o => ({ objection: o, severity: 'medium', raised_by: '', suggested_counter: '' }));
  const strengthsList = topStrengths.length > 0 ? topStrengths :
    (results.strongest_segments || []).map(s => ({ strength: s, impact: '' }));
  const recommendationsList = recommendations.length > 0 ? recommendations :
    (results.key_recommendations || []).map((r, i) => ({ priority: i + 1, action: r, rationale: '', expected_impact: '' }));

  // Score values with fallbacks
  const scoreEngagement = swarmScores.overall_engagement ?? results.overall_engagement_score ?? 0;
  const scoreSentiment = swarmScores.overall_sentiment ?? results.overall_sentiment_score ?? 0;
  const scoreDealProb = swarmScores.deal_probability ?? 0;
  const scoreClarity = swarmScores.pitch_clarity ?? 0;
  const scoreValueProp = swarmScores.value_proposition_strength ?? 0;
  const scoreObjVuln = swarmScores.objection_vulnerability ?? 0;

  const outcomeStyle = OUTCOME_STYLES[dealPrediction.outcome] || OUTCOME_STYLES.needs_work;
  const OutcomeIcon = outcomeStyle.icon;

  const copyPitch = () => {
    navigator.clipboard.writeText(bestApproach);
    setCopiedPitch(true);
    setTimeout(() => setCopiedPitch(false), 2000);
  };

  const TABS = isSwarm
    ? ['insights', 'debates', 'objections', 'action_plan']
    : ['overview', 'personas', 'recommendations'];

  const TAB_LABELS = {
    insights: 'Insights',
    debates: 'Committee Debates',
    objections: 'Objections & Strengths',
    action_plan: 'Action Plan',
    overview: 'Overview',
    personas: 'Personas',
    recommendations: 'Recommendations',
  };

  return (
    <div className="max-w-6xl mx-auto">
      {/* Header */}
      <Link to="/" className="flex items-center gap-1 text-gray-500 hover:text-gray-700 mb-4 text-sm">
        <ArrowLeft className="h-4 w-4" /> Back to Dashboard
      </Link>

      <div className="flex justify-between items-start mb-6">
        <div>
          <h1 className="text-2xl font-bold">{sim.pitch_title}</h1>
          <p className="text-gray-500 mt-1">
            {sim.company_name && <span className="font-medium text-gray-700">{sim.company_name}</span>}
            {sim.company_name && ' · '}
            {sim.industry && <span>{sim.industry}</span>}
            {sim.industry && ' · '}
            {metadata.total_agents || sim.num_personas} agents across {metadata.num_tables || debateTranscript.length || '?'} committees
            {' · '}
            {new Date(sim.created_at).toLocaleString()}
          </p>
        </div>
        <div className="flex items-center gap-2">
          {isRunning && (
            <div className="flex items-center gap-2 text-blue-600 bg-blue-50 px-4 py-2 rounded-lg">
              <RefreshCw className="h-4 w-4 animate-spin" />
              <span className="font-medium">{sim.progress_pct}%</span>
            </div>
          )}
          {sim.status === 'completed' && (
            <Link
              to={`/optimizer?simulation=${id}`}
              className="inline-flex items-center gap-2 bg-gradient-to-r from-violet-600 to-indigo-600 text-white px-4 py-2 rounded-lg font-medium hover:from-violet-700 hover:to-indigo-700 transition text-sm shadow-sm"
            >
              <Zap className="h-4 w-4" />
              AutoOptimize This Pitch
            </Link>
          )}
        </div>
      </div>

      {/* Running State */}
      {isRunning && (
        <div className="bg-white p-8 rounded-xl border border-gray-200 text-center">
          <div className="relative mx-auto w-20 h-20 mb-4">
            <RefreshCw className="h-12 w-12 text-indigo-400 mx-auto animate-spin absolute inset-0 m-auto" />
          </div>
          <h2 className="text-lg font-semibold mb-1">Swarm Deliberation in Progress</h2>
          <p className="text-gray-500 mb-1 text-sm">{sim.progress_detail || 'Committees are evaluating your pitch...'}</p>
          <p className="text-gray-400 mb-4 text-xs">{sim.progress_stage || ''}</p>
          <div className="w-full max-w-md mx-auto bg-gray-100 rounded-full h-3">
            <div className="bg-gradient-to-r from-indigo-500 to-violet-500 h-3 rounded-full transition-all duration-500" style={{ width: `${sim.progress_pct}%` }} />
          </div>
        </div>
      )}

      {/* ─── COMPLETED RESULTS ─── */}
      {sim.status === 'completed' && results && (
        <>
          {/* Deal Prediction Hero */}
          {isSwarm && dealPrediction.outcome && (
            <div className={`${outcomeStyle.bg} ${outcomeStyle.border} border rounded-xl p-6 mb-6`}>
              <div className="flex items-start justify-between">
                <div className="flex items-start gap-4">
                  <div className={`${outcomeStyle.badge} rounded-full p-3`}>
                    <OutcomeIcon className="h-6 w-6 text-white" />
                  </div>
                  <div>
                    <div className="flex items-center gap-3 mb-1">
                      <h2 className={`text-xl font-bold ${outcomeStyle.text}`}>
                        {dealPrediction.outcome?.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                      </h2>
                      <span className={`text-sm font-medium ${outcomeStyle.text} opacity-75`}>
                        {dealPrediction.confidence}% confidence
                      </span>
                    </div>
                    <p className="text-sm text-gray-600 max-w-2xl">{dealPrediction.key_factor}</p>
                    {dealPrediction.timeline_estimate && (
                      <div className="flex items-center gap-1.5 mt-2 text-xs text-gray-500">
                        <Clock className="h-3.5 w-3.5" />
                        <span>Estimated timeline: {dealPrediction.timeline_estimate}</span>
                      </div>
                    )}
                  </div>
                </div>
                {/* Confidence ring */}
                <div className="text-center shrink-0">
                  <div className="relative w-16 h-16">
                    <svg className="w-16 h-16 -rotate-90" viewBox="0 0 36 36">
                      <path d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                        fill="none" stroke="#e5e7eb" strokeWidth="3" />
                      <path d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                        fill="none" stroke="currentColor" strokeWidth="3" strokeDasharray={`${dealPrediction.confidence}, 100`}
                        className={outcomeStyle.text} />
                    </svg>
                    <span className={`absolute inset-0 flex items-center justify-center text-sm font-bold ${outcomeStyle.text}`}>
                      {dealPrediction.confidence}%
                    </span>
                  </div>
                  <p className="text-xs text-gray-400 mt-1">Confidence</p>
                </div>
              </div>
            </div>
          )}

          {/* Executive Summary */}
          {execSummary && (
            <div className="bg-white rounded-xl border border-gray-200 p-5 mb-6">
              <div className="flex items-center gap-2 mb-2">
                <Brain className="h-4 w-4 text-indigo-500" />
                <h3 className="font-semibold text-sm text-gray-500 uppercase tracking-wide">Executive Summary</h3>
              </div>
              <p className="text-gray-700 leading-relaxed">{execSummary}</p>
            </div>
          )}

          {/* Score Grid */}
          {isSwarm ? (
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3 mb-6">
              <ScoreBar label="Engagement" value={scoreEngagement} icon={TrendingUp} />
              <ScoreBar label="Sentiment" value={scoreSentiment} icon={ThumbsUp} />
              <ScoreBar label="Deal Probability" value={scoreDealProb} icon={Target} />
              <ScoreBar label="Pitch Clarity" value={scoreClarity} icon={Eye} />
              <ScoreBar label="Value Prop" value={scoreValueProp} icon={Sparkles} />
              <ScoreBar label="Objection Risk" value={scoreObjVuln} inverted icon={Shield} />
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
              <ScoreBar label="Engagement Score" value={results.overall_engagement_score} icon={TrendingUp} />
              <ScoreBar label="Sentiment Score" value={results.overall_sentiment_score} icon={ThumbsUp} />
              <div className="bg-white p-4 rounded-xl border border-gray-200">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <AlertTriangle className="h-4 w-4 text-gray-400" />
                    <span className="text-sm text-gray-500 font-medium">Objections</span>
                  </div>
                  <span className="text-lg font-bold">{results.key_objections?.length || 0}</span>
                </div>
              </div>
            </div>
          )}

          {/* Committee Breakdown (swarm only) */}
          {isSwarm && debateTranscript.length > 0 && (
            <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5 gap-3 mb-6">
              {debateTranscript.map((table, i) => {
                const v = VARIANT_LABELS[table.variant] || { label: table.variant, color: 'bg-gray-100 text-gray-700' };
                const ts = table.scores || {};
                const verdictColor = ts.verdict === 'advance' ? 'text-emerald-600 bg-emerald-50' : ts.verdict === 'decline' ? 'text-red-600 bg-red-50' : 'text-amber-600 bg-amber-50';
                return (
                  <div key={i} className="bg-white rounded-xl border border-gray-200 p-4">
                    <div className="flex items-center gap-2 mb-3">
                      <Users className="h-4 w-4 text-gray-400" />
                      <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${v.color}`}>{v.label}</span>
                    </div>
                    <div className="space-y-1.5 text-sm">
                      <div className="flex justify-between"><span className="text-gray-500">Engagement</span><span className="font-semibold">{ts.engagement ?? '—'}</span></div>
                      <div className="flex justify-between"><span className="text-gray-500">Sentiment</span><span className="font-semibold">{ts.sentiment ?? '—'}</span></div>
                      <div className="flex justify-between"><span className="text-gray-500">Deal Prob</span><span className="font-semibold">{ts.deal_probability ?? '—'}%</span></div>
                    </div>
                    {ts.verdict && (
                      <div className={`mt-3 text-center text-xs font-bold uppercase tracking-wide py-1 rounded ${verdictColor}`}>
                        {ts.verdict.replace('_', ' ')}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}

          {/* Tabs */}
          <div className="flex gap-1 mb-6 bg-gray-100 p-1 rounded-lg w-fit">
            {TABS.map(t => (
              <button key={t} onClick={() => setTab(t)}
                className={`px-4 py-1.5 rounded-md text-sm font-medium transition ${tab === t ? 'bg-white shadow-sm text-gray-900' : 'text-gray-500 hover:text-gray-700'}`}>
                {TAB_LABELS[t]}
              </button>
            ))}
          </div>

          {/* ─── INSIGHTS TAB ─── */}
          {tab === 'insights' && (
            <div className="space-y-6">
              {/* Best Pitch Approach */}
              {bestApproach && (
                <div className="bg-gradient-to-r from-indigo-50 to-violet-50 rounded-xl border border-indigo-200 p-5">
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <Crosshair className="h-4 w-4 text-indigo-600" />
                      <h3 className="font-semibold text-indigo-900">Recommended Pitch Approach</h3>
                    </div>
                    <button onClick={copyPitch} className="text-xs text-indigo-600 hover:text-indigo-800 flex items-center gap-1">
                      {copiedPitch ? <Check className="h-3.5 w-3.5" /> : <Copy className="h-3.5 w-3.5" />}
                      {copiedPitch ? 'Copied' : 'Copy'}
                    </button>
                  </div>
                  <p className="text-indigo-800 leading-relaxed">{bestApproach}</p>
                </div>
              )}

              {/* Cross-Table Insights Grid */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {crossInsights.universal_strengths?.length > 0 && (
                  <div className="bg-white rounded-xl border border-gray-200 p-5">
                    <div className="flex items-center gap-2 mb-3">
                      <ThumbsUp className="h-4 w-4 text-emerald-500" />
                      <h3 className="font-semibold text-sm">Unanimous Strengths</h3>
                      <span className="text-xs bg-emerald-100 text-emerald-700 px-1.5 py-0.5 rounded-full">All committees agreed</span>
                    </div>
                    <ul className="space-y-2">
                      {crossInsights.universal_strengths.map((s, i) => (
                        <li key={i} className="flex items-start gap-2 text-sm">
                          <CheckCircle2 className="h-4 w-4 text-emerald-500 mt-0.5 shrink-0" />
                          <span className="text-gray-700">{s}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {crossInsights.universal_objections?.length > 0 && (
                  <div className="bg-white rounded-xl border border-gray-200 p-5">
                    <div className="flex items-center gap-2 mb-3">
                      <AlertTriangle className="h-4 w-4 text-red-500" />
                      <h3 className="font-semibold text-sm">Universal Objections</h3>
                      <span className="text-xs bg-red-100 text-red-700 px-1.5 py-0.5 rounded-full">Cross-committee</span>
                    </div>
                    <ul className="space-y-2">
                      {crossInsights.universal_objections.map((o, i) => (
                        <li key={i} className="flex items-start gap-2 text-sm">
                          <XCircle className="h-4 w-4 text-red-500 mt-0.5 shrink-0" />
                          <span className="text-gray-700">{o}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {crossInsights.unique_insights?.length > 0 && (
                  <div className="bg-white rounded-xl border border-gray-200 p-5">
                    <div className="flex items-center gap-2 mb-3">
                      <Lightbulb className="h-4 w-4 text-amber-500" />
                      <h3 className="font-semibold text-sm">Unique Insights</h3>
                      <span className="text-xs bg-amber-100 text-amber-700 px-1.5 py-0.5 rounded-full">Single committee</span>
                    </div>
                    <ul className="space-y-2">
                      {crossInsights.unique_insights.map((u, i) => (
                        <li key={i} className="flex items-start gap-2 text-sm">
                          <Sparkles className="h-4 w-4 text-amber-500 mt-0.5 shrink-0" />
                          <span className="text-gray-700">{u}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {crossInsights.disagreements?.length > 0 && (
                  <div className="bg-white rounded-xl border border-gray-200 p-5">
                    <div className="flex items-center gap-2 mb-3">
                      <Scale className="h-4 w-4 text-violet-500" />
                      <h3 className="font-semibold text-sm">Committee Disagreements</h3>
                    </div>
                    <ul className="space-y-2">
                      {crossInsights.disagreements.map((d, i) => (
                        <li key={i} className="flex items-start gap-2 text-sm">
                          <AlertCircle className="h-4 w-4 text-violet-500 mt-0.5 shrink-0" />
                          <span className="text-gray-700">{d}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>

              {/* Biggest Risk + Audience Sensitivity */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {crossInsights.biggest_risk && (
                  <div className="bg-red-50 rounded-xl border border-red-200 p-5">
                    <div className="flex items-center gap-2 mb-2">
                      <AlertTriangle className="h-4 w-4 text-red-600" />
                      <h3 className="font-semibold text-sm text-red-800">Biggest Deal Risk</h3>
                    </div>
                    <p className="text-sm text-red-700">{crossInsights.biggest_risk}</p>
                  </div>
                )}
                {crossInsights.audience_sensitivity && (
                  <div className="bg-blue-50 rounded-xl border border-blue-200 p-5">
                    <div className="flex items-center gap-2 mb-2">
                      <Target className="h-4 w-4 text-blue-600" />
                      <h3 className="font-semibold text-sm text-blue-800">Audience Sensitivity</h3>
                    </div>
                    <p className="text-sm text-blue-700">{crossInsights.audience_sensitivity}</p>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* ─── COMMITTEE DEBATES TAB ─── */}
          {tab === 'debates' && (
            <div className="space-y-4">
              {debateTranscript.length > 0 ? (
                debateTranscript.map((table, i) => (
                  <CommitteeAccordion key={i} table={table} index={i} />
                ))
              ) : (
                <div className="text-center py-12 text-gray-400">No debate transcript available</div>
              )}
            </div>
          )}

          {/* ─── OBJECTIONS & STRENGTHS TAB ─── */}
          {tab === 'objections' && (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Objections */}
              <div>
                <div className="flex items-center gap-2 mb-4">
                  <AlertTriangle className="h-5 w-5 text-red-500" />
                  <h3 className="font-semibold">Top Objections</h3>
                  <span className="text-xs text-gray-400">({objectionsList.length})</span>
                </div>
                <div className="space-y-3">
                  {objectionsList.map((obj, i) => {
                    const o = typeof obj === 'string' ? { objection: obj, severity: 'medium' } : obj;
                    return (
                      <div key={i} className="bg-white rounded-xl border border-gray-200 p-4">
                        <div className="flex items-start justify-between mb-2">
                          <p className="text-sm font-medium text-gray-800 flex-1">{o.objection}</p>
                          {o.severity && (
                            <span className={`text-xs font-medium px-2 py-0.5 rounded-full border ml-2 shrink-0 ${SEVERITY_COLORS[o.severity] || SEVERITY_COLORS.medium}`}>
                              {o.severity}
                            </span>
                          )}
                        </div>
                        {o.raised_by && (
                          <p className="text-xs text-gray-400 mb-2">Raised by: {o.raised_by}</p>
                        )}
                        {o.suggested_counter && (
                          <div className="bg-emerald-50 rounded-lg p-3 mt-2">
                            <p className="text-xs font-semibold text-emerald-700 mb-0.5">💡 Suggested Counter</p>
                            <p className="text-sm text-emerald-800">{o.suggested_counter}</p>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Strengths */}
              <div>
                <div className="flex items-center gap-2 mb-4">
                  <ThumbsUp className="h-5 w-5 text-emerald-500" />
                  <h3 className="font-semibold">Top Strengths</h3>
                  <span className="text-xs text-gray-400">({strengthsList.length})</span>
                </div>
                <div className="space-y-3">
                  {strengthsList.map((str, i) => {
                    const s = typeof str === 'string' ? { strength: str } : str;
                    return (
                      <div key={i} className="bg-white rounded-xl border border-gray-200 p-4">
                        <p className="text-sm font-medium text-gray-800">{s.strength}</p>
                        {s.impact && (
                          <p className="text-xs text-gray-500 mt-1.5">
                            <span className="font-medium text-emerald-600">Impact:</span> {s.impact}
                          </p>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          )}

          {/* ─── ACTION PLAN TAB ─── */}
          {tab === 'action_plan' && (
            <div className="space-y-4">
              {recommendationsList.map((rec, i) => {
                const r = typeof rec === 'string' ? { priority: i + 1, action: rec } : rec;
                return (
                  <div key={i} className="bg-white rounded-xl border border-gray-200 p-5 flex gap-4">
                    <div className="shrink-0 w-8 h-8 rounded-full bg-indigo-100 text-indigo-700 flex items-center justify-center font-bold text-sm">
                      {r.priority || i + 1}
                    </div>
                    <div className="flex-1">
                      <p className="font-medium text-gray-800">{r.action}</p>
                      {r.rationale && (
                        <p className="text-sm text-gray-500 mt-1">
                          <span className="font-medium">Why:</span> {r.rationale}
                        </p>
                      )}
                      {r.expected_impact && (
                        <p className="text-sm text-emerald-600 mt-1">
                          <span className="font-medium">Expected Impact:</span> {r.expected_impact}
                        </p>
                      )}
                    </div>
                  </div>
                );
              })}

              {/* AutoOptimize CTA at bottom of action plan */}
              <div className="bg-gradient-to-r from-violet-50 to-indigo-50 rounded-xl border border-indigo-200 p-6 text-center">
                <Zap className="h-8 w-8 text-indigo-500 mx-auto mb-2" />
                <h3 className="font-semibold text-lg mb-1">Want to see these improvements applied automatically?</h3>
                <p className="text-sm text-gray-500 mb-4">AutoOptimizer will iteratively rewrite and re-evaluate your pitch using the Swarm Engine.</p>
                <Link
                  to={`/optimizer?simulation=${id}`}
                  className="inline-flex items-center gap-2 bg-gradient-to-r from-violet-600 to-indigo-600 text-white px-6 py-2.5 rounded-lg font-medium hover:from-violet-700 hover:to-indigo-700 transition shadow-sm"
                >
                  <Zap className="h-4 w-4" />
                  Launch AutoOptimizer
                </Link>
              </div>
            </div>
          )}

          {/* ─── LEGACY TABS (non-swarm fallback) ─── */}
          {tab === 'overview' && !isSwarm && (
            <div className="bg-white rounded-xl border border-gray-200 p-5">
              <p className="text-gray-500 text-sm">Legacy simulation results overview.</p>
            </div>
          )}

          {tab === 'personas' && !isSwarm && (
            <div className="space-y-3">
              {(responses?.responses || []).map((r) => (
                <div key={r.id} className="bg-white p-5 rounded-xl border border-gray-200">
                  <div className="flex justify-between items-start mb-3">
                    <div>
                      <h3 className="font-medium">{r.persona_name}</h3>
                      <p className="text-sm text-gray-500">{r.persona_title} · {r.industry} · {r.company_size}</p>
                    </div>
                    <div className="flex items-center gap-3">
                      <span className={`text-sm font-medium px-2 py-0.5 rounded-full ${
                        r.sentiment?.includes('positive') ? 'bg-green-50 text-green-700' :
                        r.sentiment === 'neutral' ? 'bg-yellow-50 text-yellow-700' : 'bg-red-50 text-red-700'
                      }`}>{r.sentiment}</span>
                      <span className="text-sm font-bold">{r.engagement_score?.toFixed(0)}/100</span>
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

          {tab === 'recommendations' && !isSwarm && (
            <div className="bg-white p-6 rounded-xl border border-gray-200">
              <div className="space-y-3">
                {results.key_recommendations?.map((rec, i) => (
                  <div key={i} className="flex gap-3 p-3 bg-yellow-50 rounded-lg">
                    <span className="text-yellow-600 font-bold text-sm">{i + 1}</span>
                    <p className="text-sm text-gray-700">{rec}</p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      )}

      {/* Failed State */}
      {sim.status === 'failed' && (
        <div className="bg-red-50 p-8 rounded-xl text-center border border-red-200">
          <XCircle className="h-12 w-12 text-red-400 mx-auto mb-4" />
          <h2 className="text-lg font-semibold text-red-800 mb-2">Simulation Failed</h2>
          <p className="text-red-600 text-sm">{sim.config?.error || 'Something went wrong. Please try again.'}</p>
        </div>
      )}
    </div>
  );
}
