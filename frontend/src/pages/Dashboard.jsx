import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api/client';
import { Plus, Clock, CheckCircle, AlertCircle, ArrowRight, Zap, Users, MessageSquare, BarChart3, Lightbulb, Target, ChevronRight } from 'lucide-react';

const statusConfig = {
  pending: { icon: Clock, color: 'text-yellow-600 bg-yellow-50', label: 'Pending' },
  running: { icon: Clock, color: 'text-blue-600 bg-blue-50', label: 'Running' },
  completed: { icon: CheckCircle, color: 'text-green-600 bg-green-50', label: 'Completed' },
  failed: { icon: AlertCircle, color: 'text-red-600 bg-red-50', label: 'Failed' },
};

export default function Dashboard() {
  const [simulations, setSimulations] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.listSimulations()
      .then(setSimulations)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  const runningSims = simulations.filter(s => s.status === 'running' || s.status === 'pending');
  const completedSims = simulations.filter(s => s.status === 'completed');
  const hasHistory = simulations.length > 0;

  return (
    <div>
      {/* Hero */}
      <div className="relative bg-gradient-to-br from-primary-600 via-primary-700 to-indigo-800 rounded-2xl p-8 mb-8 text-white overflow-hidden">
        <div className="absolute top-0 right-0 w-64 h-64 bg-white/5 rounded-full -translate-y-1/2 translate-x-1/3" />
        <div className="absolute bottom-0 left-0 w-48 h-48 bg-white/5 rounded-full translate-y-1/3 -translate-x-1/4" />
        <div className="relative z-10">
          <div className="flex items-center gap-2 mb-3">
            <Zap className="h-5 w-5 text-yellow-300" />
            <span className="text-xs font-semibold uppercase tracking-wider text-primary-200">AI-Powered Sales Intelligence</span>
          </div>
          <h1 className="text-3xl font-bold mb-3">PitchProof AI</h1>
          <p className="text-primary-100 text-lg max-w-2xl mb-6 leading-relaxed">
            Test your sales pitch against AI-generated buying committees before you walk into the room.
            Get real objections, real champions, and real deal predictions — so you can close with confidence.
          </p>
          <Link
            to="/new"
            className="inline-flex items-center gap-2 bg-white text-primary-700 px-6 py-3 rounded-lg font-semibold hover:bg-primary-50 transition shadow-lg"
          >
            <Plus className="h-4 w-4" />
            Run a Simulation
          </Link>
        </div>
      </div>

      {/* How It Works */}
      <div className="mb-10">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">How It Works</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-white p-5 rounded-xl border border-gray-200 relative">
            <div className="flex items-start gap-3">
              <div className="p-2 bg-blue-50 rounded-lg flex-shrink-0">
                <MessageSquare className="h-5 w-5 text-blue-600" />
              </div>
              <div>
                <div className="text-xs font-bold text-blue-600 mb-1">STEP 1</div>
                <h3 className="font-semibold text-sm mb-1">Submit Your Pitch</h3>
                <p className="text-sm text-gray-500 leading-snug">
                  Paste your sales pitch, call script, or deck talking points. Define the target industry and audience.
                </p>
              </div>
            </div>
            <ChevronRight className="hidden md:block absolute -right-3 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-300 z-10" />
          </div>

          <div className="bg-white p-5 rounded-xl border border-gray-200 relative">
            <div className="flex items-start gap-3">
              <div className="p-2 bg-violet-50 rounded-lg flex-shrink-0">
                <Users className="h-5 w-5 text-violet-600" />
              </div>
              <div>
                <div className="text-xs font-bold text-violet-600 mb-1">STEP 2</div>
                <h3 className="font-semibold text-sm mb-1">AI Committees Deliberate</h3>
                <p className="text-sm text-gray-500 leading-snug">
                  Multiple buying committees — CTOs, CFOs, security leads, end users — independently read your pitch, then debate it across rounds.
                </p>
              </div>
            </div>
            <ChevronRight className="hidden md:block absolute -right-3 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-300 z-10" />
          </div>

          <div className="bg-white p-5 rounded-xl border border-gray-200">
            <div className="flex items-start gap-3">
              <div className="p-2 bg-emerald-50 rounded-lg flex-shrink-0">
                <BarChart3 className="h-5 w-5 text-emerald-600" />
              </div>
              <div>
                <div className="text-xs font-bold text-emerald-600 mb-1">STEP 3</div>
                <h3 className="font-semibold text-sm mb-1">Actionable Intelligence</h3>
                <p className="text-sm text-gray-500 leading-snug">
                  Get deal predictions, ranked objections with counters, champion identification, and specific recommendations to sharpen your pitch.
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* What You Get */}
      <div className="mb-10">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">What You Get</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {[
            { icon: Target, label: 'Deal Probability', desc: 'Win/loss prediction with confidence score', color: 'text-red-600 bg-red-50' },
            { icon: Users, label: 'Committee Dynamics', desc: 'Champions, blockers, and influencers identified', color: 'text-blue-600 bg-blue-50' },
            { icon: AlertCircle, label: 'Top Objections', desc: 'Ranked by severity with suggested counters', color: 'text-amber-600 bg-amber-50' },
            { icon: Lightbulb, label: 'Pitch Improvements', desc: 'Prioritized actions to improve close rate', color: 'text-emerald-600 bg-emerald-50' },
          ].map(item => (
            <div key={item.label} className="bg-white p-4 rounded-xl border border-gray-200">
              <div className={`p-2 rounded-lg w-fit mb-2 ${item.color}`}>
                <item.icon className="h-4 w-4" />
              </div>
              <h3 className="font-semibold text-sm mb-0.5">{item.label}</h3>
              <p className="text-xs text-gray-500 leading-snug">{item.desc}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Active Simulations */}
      {runningSims.length > 0 && (
        <div className="mb-8">
          <h2 className="text-lg font-semibold text-gray-900 mb-3">In Progress</h2>
          <div className="space-y-3">
            {runningSims.map((sim) => (
              <Link key={sim.id} to={`/simulation/${sim.id}`} className="block bg-white p-4 rounded-xl border border-blue-200 hover:border-blue-300 transition">
                <div className="flex justify-between items-center">
                  <div>
                    <h3 className="font-medium">{sim.pitch_title}</h3>
                    <p className="text-sm text-gray-500 mt-0.5">{sim.num_personas} personas</p>
                  </div>
                  <div className="flex items-center gap-3">
                    <div className="w-32 bg-gray-200 rounded-full h-2">
                      <div className="bg-blue-600 h-2 rounded-full transition-all" style={{ width: `${sim.progress_pct}%` }}></div>
                    </div>
                    <span className="text-sm text-blue-600 font-medium">{sim.progress_pct}%</span>
                  </div>
                </div>
              </Link>
            ))}
          </div>
        </div>
      )}

      {/* Simulation History */}
      {hasHistory && (
        <div>
          <div className="flex justify-between items-center mb-3">
            <h2 className="text-lg font-semibold text-gray-900">Recent Simulations</h2>
            <Link to="/new" className="text-sm text-primary-600 hover:text-primary-700 font-medium flex items-center gap-1">
              New Simulation <ArrowRight className="h-3.5 w-3.5" />
            </Link>
          </div>
          {loading ? (
            <div className="text-center py-12 text-gray-400">Loading...</div>
          ) : (
            <div className="space-y-2">
              {simulations.slice(0, 10).map((sim) => {
                const config = statusConfig[sim.status] || statusConfig.pending;
                const Icon = config.icon;
                return (
                  <Link key={sim.id} to={`/simulation/${sim.id}`} className="block bg-white p-4 rounded-xl border border-gray-200 hover:border-gray-300 hover:shadow-sm transition group">
                    <div className="flex justify-between items-center">
                      <div className="flex items-center gap-3">
                        <div className={`p-1.5 rounded-lg ${config.color}`}>
                          <Icon className="h-4 w-4" />
                        </div>
                        <div>
                          <h3 className="font-medium group-hover:text-primary-600 transition">{sim.pitch_title}</h3>
                          <p className="text-sm text-gray-500">{sim.num_personas} personas · {new Date(sim.created_at).toLocaleDateString()}</p>
                        </div>
                      </div>
                      <ArrowRight className="h-4 w-4 text-gray-400 group-hover:text-primary-600 transition" />
                    </div>
                  </Link>
                );
              })}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
