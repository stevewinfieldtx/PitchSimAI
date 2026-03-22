import { Routes, Route, Navigate } from 'react-router-dom';
import { useAuth } from './contexts/AuthContext';
import Layout from './components/Layout';
import Login from './pages/Login';
import Register from './pages/Register';
import Dashboard from './pages/Dashboard';
import NewSimulation from './pages/NewSimulation';
import SimulationResults from './pages/SimulationResults';
import PersonaLibrary from './pages/PersonaLibrary';
import AgentChat from './pages/AgentChat';
import CommitteeGenerator from './pages/CommitteeGenerator';

function ProtectedRoute({ children }) {
  const { user, loading } = useAuth();
  if (loading) return <div className="flex items-center justify-center h-screen"><div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div></div>;
  if (!user) return <Navigate to="/login" />;
  return children;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route path="/" element={<ProtectedRoute><Layout /></ProtectedRoute>}>
        <Route index element={<Dashboard />} />
        <Route path="new" element={<NewSimulation />} />
        <Route path="committee" element={<CommitteeGenerator />} />
        <Route path="simulation/:id" element={<SimulationResults />} />
        <Route path="simulation/:id/chat/:personaId" element={<AgentChat />} />
        <Route path="personas" element={<PersonaLibrary />} />
      </Route>
    </Routes>
  );
}
