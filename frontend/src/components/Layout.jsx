import { Outlet, Link, useLocation } from 'react-router-dom';
import { LayoutDashboard, Plus, Users, Zap, UserPlus, RefreshCw } from 'lucide-react';

export default function Layout() {
  const location = useLocation();

  const navItems = [
    { path: '/', label: 'Dashboard', icon: LayoutDashboard },
    { path: '/new', label: 'New Simulation', icon: Plus },
    { path: '/committee', label: 'Buying Committee', icon: UserPlus },
    { path: '/optimizer', label: 'AutoOptimizer', icon: RefreshCw },
    { path: '/personas', label: 'Persona Library', icon: Users },
  ];

  return (
    <div className="min-h-screen bg-gray-50">
      <nav className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16">
            <div className="flex">
              <Link to="/" className="flex items-center gap-2 text-xl font-bold text-primary-600">
                <Zap className="h-6 w-6" />
                PitchProof AI
              </Link>
              <div className="hidden sm:ml-8 sm:flex sm:space-x-4">
                {navItems.map((item) => {
                  const Icon = item.icon;
                  const active = location.pathname === item.path;
                  return (
                    <Link
                      key={item.path}
                      to={item.path}
                      className={`inline-flex items-center gap-1.5 px-3 py-2 text-sm font-medium rounded-md transition-colors ${
                        active
                          ? 'text-primary-600 bg-primary-50'
                          : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'
                      }`}
                    >
                      <Icon className="h-4 w-4" />
                      {item.label}
                    </Link>
                  );
                })}
              </div>
            </div>
          </div>
        </div>
      </nav>
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <Outlet />
      </main>
    </div>
  );
}
