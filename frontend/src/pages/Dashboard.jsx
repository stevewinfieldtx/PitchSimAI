import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api/client';
import { Plus, Clock, CheckCircle, AlertCircle, ArrowRight, Zap, Target, TrendingUp, Users, CheckCheck } from 'lucide-react';

const statusConfig = {
  pending: { icon: Clock, color: 'text-yellow-600 bg-yellow-50', label: 'Pending' },
  running: { icon: Clock, color: 'text-blue-600 bg-blue-50', label: 'Running' },
  completed: { icon: CheckCircle, color: 'text-green-600 bg-green-50', label: 'Completed' },
  failed: { icon: AlertCircle, color: 'text-red-600 bg-red-50', label: 'Failed' },
};

export default function Dashboard() {
  const [simulations, setSimulations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [health, setHealth] = useState(null);

  useEffect(() => {
    api.listSimulations()
      .then(setSimulations)
      .catch(console.error)
      .finally(() => setLoading(false));

    // Check engine status
    api.healthCheck()
      .then(setHealth)
      .catch(() => setHealth(null));
  }, []);

  const completedSims = simulations.filter(s => s.status === 'completed');
  const runningSims = simulations.filter(s => s.status === 'running' || s.status === 'pending');

  return (
    <div>
      <div className="flex justify-between items-center mb-8">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Welcome back</h1>
          <p className="text-gray-500 mt-1">Test your pitches against AI buyer personas</p>
        </div>
        <Link
          to="/new"
          className="inline-flex items-center gap-2 bg-primary-600 text-white px-5 py-2.5 rounded-lg font-medium hover:bg-primary-700 transition shadow-sm"
        >
          <Plus className="h-4 w-4" />
          New Simulation
        </Link>
      </div>

      {/* Swarm Engine Status */}
      {health && (
        <div className="mb-6 p-4 rounded-xl border bg-emerald-50 border-emerald-200">
          <div className="flex items-center gap-3">
            <Users className="h-5 w-5 text-emerald-600" />
            <div className="flex-1">
              <div className="flex items-center gap-2">
                <span className="font-medium text-sm">Swarm Engine Active</span>
                <CheckCheck className="h-3.5 w-3.5 text-emerald-600" />
              </div>
              <p className="text-xs text-gray-600 mt-0.5">
                Multi-agent buying committee deliberation — {health.models_configured || 1} LLM model{health.models_configured !== 1 ? 's' : ''} configured
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
        <div className="bg-white p-5 rounded-xl border border-gray-200">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-primary-50 rounded-lg">
              <Zap className="h-5 w-5 text-primary-600" />
            </div>
            <div>
              <p className="text-sm text-gray-500">Total Simulations</p>
              <p className="text-2xl font-bold">{simulations.length}</p>
            </div>
          </div>
        </div>
        <div className="bg-white p-5 rounded-xl border border-gray-200">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-green-50 rounded-lg">
              <Target className="h-5 w-5 text-green-600" />
            </div>
            <div>
              <p className="text-sm text-gray-500">Completed</p>
              <p className="text-2xl font-bold">{completedSims.length}</p>
            </div>
          </div>
        </div>
        <div className="bg-white p-5 rounded-xl border border-gray-200">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-blue-50 rounded-lg">
              <TrendingUp className="h-5 w-5 text-blue-600" />
            </div>
            <div>
              <p className="text-sm text-gray-500">Sims Remaining</p>
              <p className="text-2xl font-bold">∞</p>
            </div>
          </div>
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
      <h2 className="text-lg font-semibold text-gray-900 mb-3">Simulation History</h2>
      {loading ? (
        <div className="text-center py-12 text-gray-400">Loading...</div>
      ) : simulations.length === 0 ? (
        <div className="text-center py-16 bg-white rounded-xl border border-gray-200">
          <Zap className="h-12 w-12 text-gray-300 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">No simulations yet</h3>
          <p className="text-gray-500 mb-6">Run your first pitch simulation to get started</p>
          <Link to="/new" className="inline-flex items-center gap-2 bg-primary-600 text-white px-5 py-2.5 rounded-lg font-medium hover:bg-primary-700 transition">
            <Plus className="h-4 w-4" /> New Simulation
          </Link>
        </div>
      ) : (
        <div className="space-y-3">
          {simulations.map((sim) => {
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
  );
}
