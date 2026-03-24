import { Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import NewSimulation from './pages/NewSimulation';
import SimulationResults from './pages/SimulationResults';
import PersonaLibrary from './pages/PersonaLibrary';
import AgentChat from './pages/AgentChat';
import CommitteeGenerator from './pages/CommitteeGenerator';
import Optimizer from './pages/Optimizer';

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Layout />}>
        <Route index element={<Dashboard />} />
        <Route path="new" element={<NewSimulation />} />
        <Route path="committee" element={<CommitteeGenerator />} />
        <Route path="simulation/:id" element={<SimulationResults />} />
        <Route path="simulation/:id/chat/:personaId" element={<AgentChat />} />
        <Route path="optimizer" element={<Optimizer />} />
        <Route path="personas" element={<PersonaLibrary />} />
      </Route>
    </Routes>
  );
}
