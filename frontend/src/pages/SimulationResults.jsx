import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { api } from '../api/client';
import {
  ArrowLeft, RefreshCw, Zap, TrendingUp, TrendingDown, AlertTriangle,
  Lightbulb, Shield, Target, Brain, Users, ChevronDown, ChevronRight,
  Clock, CheckCircle2, XCircle, AlertCircle, Crosshair, BarChart3,
  Sparkles, Eye, ThumbsUp, ThumbsDown, Scale, Copy, Check, X, HelpCircle
} from 'lucide-react';
import SwarmVisualization from '../components/SwarmVisualization';

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

const TOOLTIP_DEFINITIONS = {
  'Engagement Score': 'Measures how compelling and attention-grabbing the pitch is to the buying committee. Higher scores indicate the pitch resonates and holds attention.',
  'Sentiment Score': 'Overall emotional response to the pitch across all committee members. Ranges from strongly negative to strongly positive.',
  'Deal Probability': 'AI-estimated likelihood of advancing to the next stage based on committee reactions, objections, and buying signals.',
  'Pitch Clarity': 'How clearly the value proposition, differentiators, and call-to-action come through in the pitch.',
  'Value Proposition Strength': 'How compelling and differentiated the pitch\'s value proposition is perceived by the buying committee.',
  'Objection Risk': 'Vulnerability to objections. Lower scores mean fewer and less severe objections were raised. This is inverted — lower is better.',
  'Committee Table': 'A simulated buying committee with a distinct evaluation bias. Each variant (conservative, innovation-forward, etc.) approaches the pitch differently.',
  'Cross-Table Synthesis': 'Analysis of patterns that emerged when comparing results across all committee tables.',
  'Deal Prediction': 'The SwarmEngine\'s consensus forecast on deal outcome, based on aggregated committee verdicts, objection severity, and buying signals.',
};

// ─── Tooltip Component ───
function Tooltip({ term, children }) {
  const [showTooltip, setShowTooltip] = useState(false);
  const definition = TOOLTIP_DEFINITIONS[term];

  if (!definition) return children;

  return (
    <div className="relative inline-block">
      <div
        className="flex items-center gap-1 cursor-help"
        onMouseEnter={() => setShowTooltip(true)}
        onMouseLeave={() => setShowTooltip(false)}
      >
        {children}
        <HelpCircle className="h-3.5 w-3.5 text-gray-300 hover:text-gray-400 transition" />
      </div>
      {showTooltip && (
        <div className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 z-40 pointer-events-none">
          <div className="bg-gray-900 text-white text-xs rounded-lg px-3 py-2 max-w-xs whitespace-normal shadow-lg">
            {definition}
            <div className="absolute top-full left-1/2 transform -translate-x-1/2 w-2 h-2 bg-gray-900"></div>
          </div>
        </div>
      )}
    </div>
  );
}

// ─── Insight Modal Component ───
function InsightModal({ isOpen, onClose, title, children }) {
  useEffect(() => {
    const handleEscape = (e) => {
      if (e.key === 'Escape') onClose();
    };
    if (isOpen) {
      document.addEventListener('keydown', handleEscape);
      return () => document.removeEventListener('keydown', handleEscape);
    }
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/40 backdrop-blur-sm animate-fadeIn"
        onClick={onClose}
      />

      {/* Modal Card */}
      <div className="relative bg-white rounded-2xl shadow-2xl max-w-2xl w-full max-h-[90vh] overflow-y-auto animate-slideUp">
        {/* Header */}
        <div className="sticky top-0 bg-gradient-to-r from-indigo-600 to-violet-600 text-white px-6 py-5 flex items-center justify-between border-b border-indigo-700">
          <h2 className="text-xl font-bold">PitchSim Insights: {title}</h2>
          <button
            onClick={onClose}
            className="p-1 hover:bg-white/20 rounded-lg transition"
            aria-label="Close modal"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6">
          {children}
        </div>
      </div>

      <style jsx>{`
        @keyframes fadeIn {
          from { opacity: 0; }
          to { opacity: 1; }
        }
        @keyframes slideUp {
          from {
            transform: translateY(20px);
            opacity: 0;
          }
          to {
            transform: translateY(0);
            opacity: 1;
          }
        }
        .animate-fadeIn {
          animation: fadeIn 0.2s ease-out;
        }
        .animate-slideUp {
          animation: slideUp 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        }
      `}</style>
    </div>
  );
}

// ─── Score bar component ───
function ScoreBar({ label, value, max = 100, inverted = false, icon: Icon, onDoubleClick }) {
  const pct = Math.min(100, Math.max(0, (value / max) * 100));
  const displayVal = inverted ? max - value : value;
  const barColor = inverted
    ? (value > 60 ? 'bg-red-500' : value > 35 ? 'bg-amber-500' : 'bg-emerald-500')
    : (value > 70 ? 'bg-emerald-500' : value > 45 ? 'bg-amber-500' : 'bg-red-500');

  return (
    <div
      className="bg-white rounded-xl border border-gray-200 p-4 cursor-pointer transition-all hover:shadow-md hover:border-gray-300 relative overflow-hidden group"
      onDoubleClick={onDoubleClick}
      title="Double-click for details"
    >
      {/* Accent line */}
      <div className="absolute left-0 top-0 bottom-0 w-1 bg-gradient-to-b from-indigo-400 to-violet-400 opacity-0 group-hover:opacity-100 transition-opacity" />

      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          {Icon && <Icon className="h-4 w-4 text-gray-400" />}
          <Tooltip term={label}>
            <span className="text-sm text-gray-500 font-medium">{label}</span>
          </Tooltip>
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
function CommitteeAccordion({ table, index, onDoubleClick }) {
  const [open, setOpen] = useState(false);
  const variant = VARIANT_LABELS[table.variant] || { label: table.variant, color: 'bg-gray-100 text-gray-700' };
  const scores = table.scores || {};
  const verdict = scores.verdict;
  const verdictColor = verdict === 'advance' ? 'text-emerald-600' : verdict === 'decline' ? 'text-red-600' : 'text-amber-600';

  return (
    <div
      className="bg-white rounded-xl border border-gray-200 overflow-hidden cursor-pointer transition-all hover:shadow-md hover:border-gray-300 relative group"
      onDoubleClick={() => onDoubleClick?.(table, index)}
      title="Double-click for full details"
    >
      {/* Accent line */}
      <div className="absolute left-0 top-0 bottom-0 w-1 bg-gradient-to-b from-indigo-400 to-violet-400 opacity-0 group-hover:opacity-100 transition-opacity" />

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

// ─── By Role Tab Component ───
function ByRoleTab({ debateTranscript }) {
  const [expandedRole, setExpandedRole] = useState(null);

  // Group all responses by title across all tables
  const roleGroups = {};

  debateTranscript.forEach((table, tableIdx) => {
    const tableVariant = VARIANT_LABELS[table.variant]?.label || table.variant;

    (table.rounds || []).forEach((round) => {
      if (round.round === 'initial_reaction') {
        (round.responses || []).forEach((response) => {
          const title = response.title || 'Unknown';
          if (!roleGroups[title]) {
            roleGroups[title] = {
              title,
              personas: [],
              quotes: [],
              tables: new Set(),
            };
          }

          const persona = table.personas?.find(p => p.name === response.persona);
          if (persona && !roleGroups[title].personas.find(p => p.name === response.persona)) {
            roleGroups[title].personas.push(persona);
          }

          roleGroups[title].quotes.push({
            persona: response.persona,
            response: response.response,
            table: tableVariant,
          });
          roleGroups[title].tables.add(tableVariant);
        });
      }
    });
  });

  const sortedRoles = Object.values(roleGroups).sort((a, b) => b.personas.length - a.personas.length);

  return (
    <div className="space-y-4">
      {sortedRoles.length === 0 ? (
        <div className="text-center py-12 text-gray-400">No role data available</div>
      ) : (
        sortedRoles.map((role, idx) => (
          <div key={idx} className="bg-white rounded-xl border border-gray-200 overflow-hidden">
            <button
              onClick={() => setExpandedRole(expandedRole === role.title ? null : role.title)}
              className="w-full flex items-center justify-between p-5 hover:bg-gray-50 transition group"
            >
              <div className="flex items-center gap-3">
                {expandedRole === role.title ? (
                  <ChevronDown className="h-5 w-5 text-gray-400" />
                ) : (
                  <ChevronRight className="h-5 w-5 text-gray-400" />
                )}
                <div className="text-left">
                  <h3 className="font-semibold text-gray-900">{role.title}</h3>
                  <p className="text-xs text-gray-500">{role.personas.length} persona{role.personas.length !== 1 ? 's' : ''} · {role.tables.size} table{role.tables.size !== 1 ? 's' : ''}</p>
                </div>
              </div>
            </button>

            {expandedRole === role.title && (
              <div className="border-t border-gray-100 px-5 py-4 bg-gray-50">
                {/* Synthesis summary */}
                <div className="mb-5 pb-5 border-b border-gray-200">
                  <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">Key Positions</p>
                  <div className="space-y-2">
                    {role.quotes.slice(0, 2).map((quote, qi) => (
                      <p key={qi} className="text-sm text-gray-700 italic border-l-2 border-indigo-300 pl-3">
                        "{quote.response.substring(0, 120)}{quote.response.length > 120 ? '...' : ''}"
                      </p>
                    ))}
                  </div>
                </div>

                {/* Individual quotes */}
                <div>
                  <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">Individual Responses</p>
                  <div className="space-y-3">
                    {role.quotes.map((quote, qi) => (
                      <div key={qi} className="bg-white rounded-lg p-3 border border-gray-200">
                        <div className="flex items-start justify-between mb-1">
                          <div>
                            <p className="text-sm font-medium text-gray-900">{quote.persona}</p>
                            <p className="text-xs text-gray-400">{quote.table}</p>
                          </div>
                        </div>
                        <p className="text-sm text-gray-700">{quote.response}</p>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}
          </div>
        ))
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
  const [modalState, setModalState] = useState({ isOpen: false, type: null, data: null });

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
    ? ['insights', 'by_role', 'debates', 'objections', 'action_plan']
    : ['overview', 'personas', 'recommendations'];

  const TAB_LABELS = {
    insights: 'Insights',
    by_role: 'By Role',
    debates: 'Committee Debates',
    objections: 'Objections & Strengths',
    action_plan: 'Action Plan',
    overview: 'Overview',
    personas: 'Personas',
    recommendations: 'Recommendations',
  };

  const openModal = (type, data) => {
    setModalState({ isOpen: true, type, data });
  };

  const closeModal = () => {
    setModalState({ isOpen: false, type: null, data: null });
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 via-white to-gray-50">
      <div className="max-w-6xl mx-auto px-4 py-8">
        {/* Header */}
        <Link to="/" className="flex items-center gap-1 text-gray-500 hover:text-gray-700 mb-4 text-sm">
          <ArrowLeft className="h-4 w-4" /> Back to Dashboard
        </Link>

        <div className="flex justify-between items-start mb-6">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">{sim.pitch_title}</h1>
            <p className="text-gray-500 mt-2">
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

        {/* Running State — Animated Swarm Visualization */}
        {isRunning && (
          <div className="bg-white p-6 rounded-xl border border-gray-200 mb-6">
            <div className="text-center mb-4">
              <h2 className="text-lg font-semibold mb-1">Swarm Deliberation in Progress</h2>
              <p className="text-gray-500 text-sm">{sim.progress_detail || 'Committees are evaluating your pitch...'}</p>
              {sim.progress_stage && <p className="text-gray-400 text-xs mt-0.5">{sim.progress_stage}</p>}
            </div>

            {/* The animated particle visualization */}
            <div className="flex justify-center mb-5">
              <SwarmVisualization
                numTables={sim.config?.num_tables || 3}
                personasPerTable={sim.config?.personas_per_table || 5}
                progressPct={sim.progress_pct || 0}
                width={560}
                height={340}
              />
            </div>

            {/* Progress bar */}
            <div className="max-w-md mx-auto">
              <div className="flex justify-between text-xs text-gray-400 mb-1">
                <span>Progress</span>
                <span>{sim.progress_pct}%</span>
              </div>
              <div className="w-full bg-gray-100 rounded-full h-2.5">
                <div className="bg-gradient-to-r from-indigo-500 to-violet-500 h-2.5 rounded-full transition-all duration-500" style={{ width: `${sim.progress_pct}%` }} />
              </div>
            </div>
          </div>
        )}

        {/* ─── COMPLETED RESULTS ─── */}
        {sim.status === 'completed' && results && (
          <>
            {/* Deal Prediction Hero */}
            {isSwarm && dealPrediction.outcome && (
              <div
                className={`${outcomeStyle.bg} ${outcomeStyle.border} border rounded-xl p-6 mb-6 cursor-pointer transition-all hover:shadow-lg hover:border-gray-300`}
                onDoubleClick={() => openModal('dealPrediction', dealPrediction)}
                title="Double-click for full analysis"
              >
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
              <div className="bg-white rounded-xl border border-gray-200 p-5 mb-6 shadow-sm hover:shadow-md transition">
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
                <ScoreBar
                  label="Engagement Score"
                  value={scoreEngagement}
                  icon={TrendingUp}
                  onDoubleClick={() => openModal('scoreCard', { name: 'Engagement Score', value: scoreEngagement, definition: TOOLTIP_DEFINITIONS['Engagement Score'] })}
                />
                <ScoreBar
                  label="Sentiment Score"
                  value={scoreSentiment}
                  icon={ThumbsUp}
                  onDoubleClick={() => openModal('scoreCard', { name: 'Sentiment Score', value: scoreSentiment, definition: TOOLTIP_DEFINITIONS['Sentiment Score'] })}
                />
                <ScoreBar
                  label="Deal Probability"
                  value={scoreDealProb}
                  icon={Target}
                  onDoubleClick={() => openModal('scoreCard', { name: 'Deal Probability', value: scoreDealProb, definition: TOOLTIP_DEFINITIONS['Deal Probability'] })}
                />
                <ScoreBar
                  label="Pitch Clarity"
                  value={scoreClarity}
                  icon={Eye}
                  onDoubleClick={() => openModal('scoreCard', { name: 'Pitch Clarity', value: scoreClarity, definition: TOOLTIP_DEFINITIONS['Pitch Clarity'] })}
                />
                <ScoreBar
                  label="Value Proposition Strength"
                  value={scoreValueProp}
                  icon={Sparkles}
                  onDoubleClick={() => openModal('scoreCard', { name: 'Value Proposition Strength', value: scoreValueProp, definition: TOOLTIP_DEFINITIONS['Value Proposition Strength'] })}
                />
                <ScoreBar
                  label="Objection Risk"
                  value={scoreObjVuln}
                  inverted
                  icon={Shield}
                  onDoubleClick={() => openModal('scoreCard', { name: 'Objection Risk', value: scoreObjVuln, definition: TOOLTIP_DEFINITIONS['Objection Risk'] })}
                />
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
                    <div
                      key={i}
                      className="bg-white rounded-xl border border-gray-200 p-4 cursor-pointer transition-all hover:shadow-md hover:border-gray-300 relative group overflow-hidden"
                      onDoubleClick={() => openModal('committeeBreakdown', { table, index: i })}
                      title="Double-click for details"
                    >
                      {/* Accent line */}
                      <div className="absolute left-0 top-0 bottom-0 w-1 bg-gradient-to-b from-indigo-400 to-violet-400 opacity-0 group-hover:opacity-100 transition-opacity" />

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
            <div className="flex gap-1 mb-6 border-b border-gray-200">
              {TABS.map(t => (
                <button
                  key={t}
                  onClick={() => setTab(t)}
                  className={`px-4 py-3 text-sm font-medium transition-all relative ${
                    tab === t
                      ? 'text-gray-900 after:absolute after:bottom-0 after:left-0 after:right-0 after:h-0.5 after:bg-gradient-to-r after:from-indigo-500 after:to-violet-500'
                      : 'text-gray-500 hover:text-gray-700'
                  }`}
                >
                  {TAB_LABELS[t]}
                </button>
              ))}
            </div>

            {/* ─── INSIGHTS TAB ─── */}
            {tab === 'insights' && (
              <div className="space-y-6">
                {/* Best Pitch Approach */}
                {bestApproach && (
                  <div className="bg-gradient-to-r from-indigo-50 to-violet-50 rounded-xl border border-indigo-200 p-5 shadow-sm hover:shadow-md transition">
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
                    <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm hover:shadow-md transition relative overflow-hidden group">
                      <div className="absolute left-0 top-0 bottom-0 w-1 bg-emerald-400 opacity-0 group-hover:opacity-100 transition-opacity" />
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
                    <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm hover:shadow-md transition relative overflow-hidden group">
                      <div className="absolute left-0 top-0 bottom-0 w-1 bg-red-400 opacity-0 group-hover:opacity-100 transition-opacity" />
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
                    <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm hover:shadow-md transition relative overflow-hidden group">
                      <div className="absolute left-0 top-0 bottom-0 w-1 bg-amber-400 opacity-0 group-hover:opacity-100 transition-opacity" />
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
                    <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm hover:shadow-md transition relative overflow-hidden group">
                      <div className="absolute left-0 top-0 bottom-0 w-1 bg-violet-400 opacity-0 group-hover:opacity-100 transition-opacity" />
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
                    <div className="bg-red-50 rounded-xl border border-red-200 p-5 shadow-sm hover:shadow-md transition relative overflow-hidden group">
                      <div className="absolute left-0 top-0 bottom-0 w-1 bg-red-400 opacity-0 group-hover:opacity-100 transition-opacity" />
                      <div className="flex items-center gap-2 mb-2">
                        <AlertTriangle className="h-4 w-4 text-red-600" />
                        <h3 className="font-semibold text-sm text-red-800">Biggest Deal Risk</h3>
                      </div>
                      <p className="text-sm text-red-700">{crossInsights.biggest_risk}</p>
                    </div>
                  )}
                  {crossInsights.audience_sensitivity && (
                    <div className="bg-blue-50 rounded-xl border border-blue-200 p-5 shadow-sm hover:shadow-md transition relative overflow-hidden group">
                      <div className="absolute left-0 top-0 bottom-0 w-1 bg-blue-400 opacity-0 group-hover:opacity-100 transition-opacity" />
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

            {/* ─── BY ROLE TAB ─── */}
            {tab === 'by_role' && <ByRoleTab debateTranscript={debateTranscript} />}

            {/* ─── COMMITTEE DEBATES TAB ─── */}
            {tab === 'debates' && (
              <div className="space-y-4">
                {debateTranscript.length > 0 ? (
                  debateTranscript.map((table, i) => (
                    <CommitteeAccordion
                      key={i}
                      table={table}
                      index={i}
                      onDoubleClick={(table, index) => openModal('committeeBreakdown', { table, index })}
                    />
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
                        <div key={i} className="bg-white rounded-xl border border-gray-200 p-4 shadow-sm hover:shadow-md transition">
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
                        <div key={i} className="bg-white rounded-xl border border-gray-200 p-4 shadow-sm hover:shadow-md transition">
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
                    <div key={i} className="bg-white rounded-xl border border-gray-200 p-5 flex gap-4 shadow-sm hover:shadow-md transition relative overflow-hidden group">
                      <div className="absolute left-0 top-0 bottom-0 w-1 bg-indigo-400 opacity-0 group-hover:opacity-100 transition-opacity" />
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
                <div className="bg-gradient-to-r from-violet-50 to-indigo-50 rounded-xl border border-indigo-200 p-6 text-center shadow-sm hover:shadow-md transition">
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
              <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
                <p className="text-gray-500 text-sm">Legacy simulation results overview.</p>
              </div>
            )}

            {tab === 'personas' && !isSwarm && (
              <div className="space-y-3">
                {(responses?.responses || []).map((r) => (
                  <div key={r.id} className="bg-white p-5 rounded-xl border border-gray-200 shadow-sm hover:shadow-md transition">
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
              <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm">
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
          <div className="bg-red-50 p-8 rounded-xl text-center border border-red-200 shadow-sm">
            <XCircle className="h-12 w-12 text-red-400 mx-auto mb-4" />
            <h2 className="text-lg font-semibold text-red-800 mb-2">Simulation Failed</h2>
            <p className="text-red-600 text-sm">{sim.config?.error || 'Something went wrong. Please try again.'}</p>
          </div>
        )}
      </div>

      {/* Score Card Modal */}
      {modalState.type === 'scoreCard' && (
        <InsightModal
          isOpen={modalState.isOpen}
          onClose={closeModal}
          title={modalState.data?.name}
        >
          <div className="space-y-4">
            <div className="text-center py-4">
              <div className="text-5xl font-bold text-indigo-600">{modalState.data?.value?.toFixed(0) ?? modalState.data?.value}</div>
              <p className="text-sm text-gray-500 mt-1">Score out of 100</p>
            </div>
            <div className="bg-gray-50 rounded-lg p-4">
              <h3 className="font-semibold text-sm text-gray-900 mb-2">About this score</h3>
              <p className="text-sm text-gray-700">{modalState.data?.definition}</p>
            </div>
            {debateTranscript.length > 0 && (
              <div className="bg-gray-50 rounded-lg p-4">
                <h3 className="font-semibold text-sm text-gray-900 mb-3">Score by Committee Table</h3>
                <div className="space-y-2">
                  {debateTranscript.map((table, i) => {
                    const scoreKey = modalState.data?.name?.toLowerCase().replace(/ /g, '_');
                    const tableScore = table.scores?.[scoreKey] ?? '—';
                    const variant = VARIANT_LABELS[table.variant] || { label: table.variant };
                    return (
                      <div key={i} className="flex items-center justify-between text-sm">
                        <span className="text-gray-600">{variant.label}</span>
                        <span className="font-semibold">{tableScore}</span>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </div>
        </InsightModal>
      )}

      {/* Committee Breakdown Modal */}
      {modalState.type === 'committeeBreakdown' && modalState.data?.table && (
        <InsightModal
          isOpen={modalState.isOpen}
          onClose={closeModal}
          title={`${VARIANT_LABELS[modalState.data.table.variant]?.label || modalState.data.table.variant} Committee`}
        >
          <div className="space-y-5">
            {/* Committee Members */}
            <div>
              <h3 className="font-semibold text-sm text-gray-900 mb-3">Committee Members</h3>
              <div className="space-y-2">
                {(modalState.data.table.personas || []).map((p, i) => (
                  <div key={i} className="flex items-center gap-2 text-sm p-2 bg-gray-50 rounded-lg">
                    <span className="text-lg">{ROLE_ICONS[p.role_in_committee] || '⚪'}</span>
                    <div>
                      <p className="font-medium text-gray-900">{p.name}</p>
                      <p className="text-xs text-gray-500">{p.title}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Scores */}
            <div className="grid grid-cols-3 gap-2 py-3 border-t border-b border-gray-200">
              <div className="text-center">
                <p className="text-xs text-gray-500 mb-1">Engagement</p>
                <p className="text-lg font-bold text-gray-900">{modalState.data.table.scores?.engagement ?? '—'}</p>
              </div>
              <div className="text-center">
                <p className="text-xs text-gray-500 mb-1">Sentiment</p>
                <p className="text-lg font-bold text-gray-900">{modalState.data.table.scores?.sentiment ?? '—'}</p>
              </div>
              <div className="text-center">
                <p className="text-xs text-gray-500 mb-1">Deal Prob</p>
                <p className="text-lg font-bold text-gray-900">{modalState.data.table.scores?.deal_probability ?? '—'}%</p>
              </div>
            </div>

            {/* Verdict */}
            {modalState.data.table.scores?.verdict && (
              <div className="text-center py-3">
                <p className="text-xs text-gray-500 mb-1">Committee Verdict</p>
                <p className={`text-lg font-bold capitalize ${
                  modalState.data.table.scores.verdict === 'advance' ? 'text-emerald-600' :
                  modalState.data.table.scores.verdict === 'decline' ? 'text-red-600' : 'text-amber-600'
                }`}>
                  {modalState.data.table.scores.verdict.replace('_', ' ')}
                </p>
              </div>
            )}

            {/* Summary */}
            {modalState.data.table.summary && (
              <div className="bg-gray-50 rounded-lg p-4">
                <h3 className="font-semibold text-sm text-gray-900 mb-2">Committee Summary</h3>
                <p className="text-sm text-gray-700">{modalState.data.table.summary}</p>
              </div>
            )}

            {/* Key Quotes */}
            {modalState.data.table.rounds && (
              <div>
                <h3 className="font-semibold text-sm text-gray-900 mb-3">Key Positions</h3>
                <div className="space-y-2">
                  {modalState.data.table.rounds
                    .filter(r => r.round === 'initial_reaction')
                    .flatMap(r => r.responses || [])
                    .slice(0, 3)
                    .map((resp, i) => (
                      <div key={i} className="bg-gray-50 rounded-lg p-3 border-l-2 border-indigo-400">
                        <p className="text-xs font-medium text-gray-900 mb-1">{resp.persona}</p>
                        <p className="text-sm text-gray-700">{resp.response.substring(0, 150)}{resp.response.length > 150 ? '...' : ''}</p>
                      </div>
                    ))}
                </div>
              </div>
            )}
          </div>
        </InsightModal>
      )}

      {/* Deal Prediction Modal */}
      {modalState.type === 'dealPrediction' && modalState.data && (
        <InsightModal
          isOpen={modalState.isOpen}
          onClose={closeModal}
          title="Deal Prediction Analysis"
        >
          <div className="space-y-5">
            {/* Prediction */}
            <div className="text-center py-4 bg-gradient-to-r from-indigo-50 to-violet-50 rounded-lg">
              <p className={`text-sm font-semibold mb-2 ${outcomeStyle.text}`}>
                {dealPrediction.outcome?.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
              </p>
              <div className="flex items-center justify-center gap-2 mb-2">
                <span className="text-4xl font-bold text-indigo-600">{dealPrediction.confidence}%</span>
                <span className="text-sm text-gray-600">Confidence</span>
              </div>
              {dealPrediction.timeline_estimate && (
                <p className="text-xs text-gray-500">Timeline: {dealPrediction.timeline_estimate}</p>
              )}
            </div>

            {/* Key Factor */}
            {dealPrediction.key_factor && (
              <div className="bg-gray-50 rounded-lg p-4">
                <h3 className="font-semibold text-sm text-gray-900 mb-2">Key Factor</h3>
                <p className="text-sm text-gray-700">{dealPrediction.key_factor}</p>
              </div>
            )}

            {/* Cross-Table Agreement */}
            {debateTranscript.length > 1 && (
              <div className="bg-gray-50 rounded-lg p-4">
                <h3 className="font-semibold text-sm text-gray-900 mb-3">Cross-Table Verdicts</h3>
                <div className="space-y-2">
                  {debateTranscript.map((table, i) => {
                    const verdict = table.scores?.verdict;
                    const variant = VARIANT_LABELS[table.variant] || { label: table.variant };
                    const verdictColor = verdict === 'advance' ? 'text-emerald-600' :
                                         verdict === 'decline' ? 'text-red-600' : 'text-amber-600';
                    return (
                      <div key={i} className="flex items-center justify-between text-sm p-2 bg-white rounded border border-gray-200">
                        <span className="font-medium text-gray-700">{variant.label}</span>
                        {verdict && <span className={`font-semibold capitalize ${verdictColor}`}>{verdict.replace('_', ' ')}</span>}
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </div>
        </InsightModal>
      )}
    </div>
  );
}
