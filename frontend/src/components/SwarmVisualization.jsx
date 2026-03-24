import { useRef, useEffect, useState, useCallback } from 'react';

/**
 * SwarmVisualization — Animated particle system showing the multi-agent
 * deliberation process. Dots form committee clusters, break out to debate,
 * exchange ideas, then converge into a consensus formation.
 *
 * Phases:
 *   0 - GATHER:    Dots drift in from edges and cluster into committee tables
 *   1 - REACT:     Dots pulse within their clusters (initial reactions)
 *   2 - DEBATE:    Dots break out, zip between clusters, exchange sparks
 *   3 - SYNTHESIZE: Dots orbit in wider arcs, cross-table connections form
 *   4 - CONSENSUS: All dots converge toward center, form unified ring
 *
 * The phase auto-advances on a timer, but can also be driven by
 * progressPct from the parent.
 */

const TABLE_COLORS = [
  '#6366f1', // indigo  - conservative
  '#8b5cf6', // violet  - innovation-forward
  '#f59e0b', // amber   - cost-conscious
  '#3b82f6', // blue    - enterprise-cautious
  '#10b981', // emerald - growth-stage
];

const PHASE_LABELS = [
  'Forming Committees',
  'Initial Reactions',
  'Committee Debate',
  'Cross-Table Synthesis',
  'Building Consensus',
];

const ROLE_SIZES = {
  decision_maker: 6,
  champion: 5,
  blocker: 5,
  skeptic: 4.5,
  influencer: 4,
  default: 3.5,
};

export default function SwarmVisualization({
  numTables = 3,
  personasPerTable = 5,
  progressPct = 0,
  width = 600,
  height = 400,
}) {
  const canvasRef = useRef(null);
  const animRef = useRef(null);
  const stateRef = useRef(null);
  const [currentPhase, setCurrentPhase] = useState(0);

  // Map progress percentage to phase
  const getPhaseFromProgress = useCallback((pct) => {
    if (pct < 15) return 0;
    if (pct < 35) return 1;
    if (pct < 65) return 2;
    if (pct < 85) return 3;
    return 4;
  }, []);

  // Initialize particles and cluster centers
  const initState = useCallback(() => {
    const cx = width / 2;
    const cy = height / 2;
    const clusterRadius = Math.min(width, height) * 0.3;
    const tables = numTables;

    // Compute cluster center positions in a circle
    const clusters = [];
    for (let t = 0; t < tables; t++) {
      const angle = (t / tables) * Math.PI * 2 - Math.PI / 2;
      clusters.push({
        x: cx + Math.cos(angle) * clusterRadius,
        y: cy + Math.sin(angle) * clusterRadius,
        color: TABLE_COLORS[t % TABLE_COLORS.length],
        angle,
      });
    }

    // Create particles
    const particles = [];
    const roles = ['decision_maker', 'champion', 'skeptic', 'blocker', 'influencer'];
    for (let t = 0; t < tables; t++) {
      for (let p = 0; p < personasPerTable; p++) {
        const role = roles[p % roles.length];
        const startAngle = Math.random() * Math.PI * 2;
        const startDist = Math.max(width, height) * 0.6;
        particles.push({
          // Current position
          x: cx + Math.cos(startAngle) * startDist,
          y: cy + Math.sin(startAngle) * startDist,
          // Velocity
          vx: 0,
          vy: 0,
          // Home cluster
          table: t,
          role,
          radius: ROLE_SIZES[role] || ROLE_SIZES.default,
          color: clusters[t].color,
          // Animation state
          phase: 0,
          pulseOffset: Math.random() * Math.PI * 2,
          orbitAngle: (p / personasPerTable) * Math.PI * 2,
          orbitSpeed: 0.005 + Math.random() * 0.01,
          debateTarget: null, // index of particle to debate with
          sparkTimer: 0,
          alpha: 0.3,
        });
      }
    }

    // Connection lines (for debate/synthesis phases)
    const connections = [];

    return {
      particles,
      clusters,
      connections,
      phase: 0,
      phaseTimer: 0,
      time: 0,
      sparks: [], // little burst particles
    };
  }, [width, height, numTables, personasPerTable]);

  // Animation loop
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');

    // Handle high-DPI
    const dpr = window.devicePixelRatio || 1;
    canvas.width = width * dpr;
    canvas.height = height * dpr;
    ctx.scale(dpr, dpr);

    stateRef.current = initState();
    let phase = getPhaseFromProgress(progressPct);

    const lerp = (a, b, t) => a + (b - a) * t;
    const dist = (a, b) => Math.sqrt((a.x - b.x) ** 2 + (a.y - b.y) ** 2);

    const update = (state, dt) => {
      state.time += dt;
      state.phaseTimer += dt;

      // Determine target phase from progress
      const targetPhase = getPhaseFromProgress(progressPct);
      if (targetPhase !== state.phase) {
        state.phase = targetPhase;
        state.phaseTimer = 0;
        // Reset debate targets on phase change
        state.particles.forEach(p => { p.debateTarget = null; });
        state.connections = [];
      }
      setCurrentPhase(state.phase);

      const cx = width / 2;
      const cy = height / 2;
      const clusterSpread = 25 + Math.sin(state.time * 0.5) * 5;

      state.particles.forEach((p, idx) => {
        const cluster = state.clusters[p.table];
        let targetX, targetY;

        switch (state.phase) {
          case 0: {
            // GATHER — move toward cluster center with slight orbit
            const orbitR = clusterSpread * 0.8;
            p.orbitAngle += p.orbitSpeed;
            targetX = cluster.x + Math.cos(p.orbitAngle) * orbitR;
            targetY = cluster.y + Math.sin(p.orbitAngle) * orbitR;
            p.x = lerp(p.x, targetX, 0.03);
            p.y = lerp(p.y, targetY, 0.03);
            p.alpha = lerp(p.alpha, 0.9, 0.02);
            break;
          }
          case 1: {
            // REACT — tight cluster with pulsing
            const pulse = 1 + Math.sin(state.time * 3 + p.pulseOffset) * 0.3;
            const orbitR = clusterSpread * 0.6 * pulse;
            p.orbitAngle += p.orbitSpeed * 2;
            targetX = cluster.x + Math.cos(p.orbitAngle) * orbitR;
            targetY = cluster.y + Math.sin(p.orbitAngle) * orbitR;
            p.x = lerp(p.x, targetX, 0.06);
            p.y = lerp(p.y, targetY, 0.06);
            p.alpha = 1;
            break;
          }
          case 2: {
            // DEBATE — some particles zip to other clusters
            if (!p.debateTarget && Math.random() < 0.005) {
              // Pick a random particle from another table
              const candidates = state.particles.filter((q, qi) => q.table !== p.table && qi !== idx);
              if (candidates.length > 0) {
                p.debateTarget = state.particles.indexOf(candidates[Math.floor(Math.random() * candidates.length)]);
                p.sparkTimer = 30;
              }
            }

            if (p.debateTarget !== null && p.sparkTimer > 0) {
              const target = state.particles[p.debateTarget];
              const midX = (cluster.x + state.clusters[target.table].x) / 2 + (Math.random() - 0.5) * 40;
              const midY = (cluster.y + state.clusters[target.table].y) / 2 + (Math.random() - 0.5) * 40;
              p.x = lerp(p.x, midX, 0.08);
              p.y = lerp(p.y, midY, 0.08);
              p.sparkTimer--;

              // Spawn sparks at meeting point
              if (p.sparkTimer === 15 && dist(p, state.particles[p.debateTarget]) < 60) {
                for (let s = 0; s < 3; s++) {
                  state.sparks.push({
                    x: p.x, y: p.y,
                    vx: (Math.random() - 0.5) * 3,
                    vy: (Math.random() - 0.5) * 3,
                    life: 20 + Math.random() * 15,
                    maxLife: 35,
                    color: p.color,
                  });
                }
              }

              if (p.sparkTimer <= 0) p.debateTarget = null;
            } else {
              // Return to home cluster with wider orbit
              const orbitR = clusterSpread * 1.2;
              p.orbitAngle += p.orbitSpeed * 1.5;
              targetX = cluster.x + Math.cos(p.orbitAngle) * orbitR;
              targetY = cluster.y + Math.sin(p.orbitAngle) * orbitR;
              p.x = lerp(p.x, targetX, 0.04);
              p.y = lerp(p.y, targetY, 0.04);
            }
            p.alpha = 1;
            break;
          }
          case 3: {
            // SYNTHESIZE — wider orbits, arcs between clusters
            const bigOrbitR = clusterSpread * 1.8;
            p.orbitAngle += p.orbitSpeed * 0.8;
            const wobble = Math.sin(state.time * 2 + idx) * 15;
            targetX = cluster.x + Math.cos(p.orbitAngle) * bigOrbitR + wobble;
            targetY = cluster.y + Math.sin(p.orbitAngle) * bigOrbitR;
            p.x = lerp(p.x, targetX, 0.04);
            p.y = lerp(p.y, targetY, 0.04);

            // Cross-table connection lines
            if (state.phaseTimer < 2 && state.connections.length < numTables * 2) {
              if (Math.random() < 0.02) {
                const otherTable = (p.table + 1 + Math.floor(Math.random() * (numTables - 1))) % numTables;
                state.connections.push({
                  from: p.table,
                  to: otherTable,
                  alpha: 0.5,
                  decay: 0.003,
                });
              }
            }
            p.alpha = 1;
            break;
          }
          case 4: {
            // CONSENSUS — all converge toward center, form a ring
            const convergePct = Math.min(1, state.phaseTimer / 3);
            const ringR = 30 + (1 - convergePct) * clusterSpread * 2;
            const globalAngle = (idx / state.particles.length) * Math.PI * 2 + state.time * 0.3;
            targetX = lerp(cluster.x, cx, convergePct) + Math.cos(globalAngle) * ringR;
            targetY = lerp(cluster.y, cy, convergePct) + Math.sin(globalAngle) * ringR;
            p.x = lerp(p.x, targetX, 0.04);
            p.y = lerp(p.y, targetY, 0.04);
            p.alpha = 1;
            break;
          }
        }
      });

      // Update sparks
      state.sparks = state.sparks.filter(s => {
        s.x += s.vx;
        s.y += s.vy;
        s.vx *= 0.95;
        s.vy *= 0.95;
        s.life--;
        return s.life > 0;
      });

      // Decay connections
      state.connections = state.connections.filter(c => {
        c.alpha -= c.decay;
        return c.alpha > 0;
      });
    };

    const draw = (state) => {
      ctx.clearRect(0, 0, width, height);

      // Background subtle gradient
      const grad = ctx.createRadialGradient(width / 2, height / 2, 0, width / 2, height / 2, width * 0.6);
      grad.addColorStop(0, 'rgba(99, 102, 241, 0.03)');
      grad.addColorStop(1, 'rgba(0, 0, 0, 0)');
      ctx.fillStyle = grad;
      ctx.fillRect(0, 0, width, height);

      // Draw cluster zones (subtle)
      if (state.phase < 4) {
        state.clusters.forEach((cl, i) => {
          ctx.beginPath();
          ctx.arc(cl.x, cl.y, 45, 0, Math.PI * 2);
          ctx.fillStyle = cl.color + '10';
          ctx.fill();
          ctx.strokeStyle = cl.color + '25';
          ctx.lineWidth = 1;
          ctx.stroke();
        });
      }

      // Draw cross-table connections
      state.connections.forEach(c => {
        const from = state.clusters[c.from];
        const to = state.clusters[c.to];
        ctx.beginPath();
        ctx.moveTo(from.x, from.y);
        // Curved line through center-ish
        const midX = (from.x + to.x) / 2 + (Math.random() - 0.5) * 2;
        const midY = (from.y + to.y) / 2 - 20;
        ctx.quadraticCurveTo(midX, midY, to.x, to.y);
        ctx.strokeStyle = `rgba(99, 102, 241, ${c.alpha * 0.4})`;
        ctx.lineWidth = 1.5;
        ctx.setLineDash([4, 4]);
        ctx.stroke();
        ctx.setLineDash([]);
      });

      // Draw debate lines (phase 2)
      if (state.phase === 2) {
        state.particles.forEach(p => {
          if (p.debateTarget !== null && p.sparkTimer > 0) {
            const target = state.particles[p.debateTarget];
            ctx.beginPath();
            ctx.moveTo(p.x, p.y);
            ctx.lineTo(target.x, target.y);
            ctx.strokeStyle = p.color + '30';
            ctx.lineWidth = 1;
            ctx.stroke();
          }
        });
      }

      // Draw consensus ring (phase 4)
      if (state.phase === 4) {
        const convergePct = Math.min(1, state.phaseTimer / 3);
        if (convergePct > 0.5) {
          ctx.beginPath();
          ctx.arc(width / 2, height / 2, 35, 0, Math.PI * 2);
          const ringAlpha = (convergePct - 0.5) * 2 * 0.15;
          ctx.strokeStyle = `rgba(99, 102, 241, ${ringAlpha})`;
          ctx.lineWidth = 2;
          ctx.stroke();
        }
      }

      // Draw sparks
      state.sparks.forEach(s => {
        const sparkAlpha = s.life / s.maxLife;
        ctx.beginPath();
        ctx.arc(s.x, s.y, 2 * sparkAlpha, 0, Math.PI * 2);
        ctx.fillStyle = s.color + Math.round(sparkAlpha * 200).toString(16).padStart(2, '0');
        ctx.fill();
      });

      // Draw particles
      state.particles.forEach(p => {
        const pulse = state.phase === 1 ? 1 + Math.sin(state.time * 4 + p.pulseOffset) * 0.25 : 1;
        const r = p.radius * pulse;

        // Glow
        ctx.beginPath();
        ctx.arc(p.x, p.y, r * 2.5, 0, Math.PI * 2);
        ctx.fillStyle = p.color + '15';
        ctx.fill();

        // Main dot
        ctx.beginPath();
        ctx.arc(p.x, p.y, r, 0, Math.PI * 2);
        const alphaHex = Math.round(p.alpha * 255).toString(16).padStart(2, '0');
        ctx.fillStyle = p.color + alphaHex;
        ctx.fill();

        // Decision makers get a highlight ring
        if (p.role === 'decision_maker') {
          ctx.beginPath();
          ctx.arc(p.x, p.y, r + 2, 0, Math.PI * 2);
          ctx.strokeStyle = p.color + '60';
          ctx.lineWidth = 1;
          ctx.stroke();
        }
      });
    };

    let lastTime = performance.now();
    const animate = (now) => {
      const dt = Math.min((now - lastTime) / 1000, 0.05);
      lastTime = now;

      if (stateRef.current) {
        update(stateRef.current, dt);
        draw(stateRef.current);
      }

      animRef.current = requestAnimationFrame(animate);
    };

    animRef.current = requestAnimationFrame(animate);

    return () => {
      if (animRef.current) cancelAnimationFrame(animRef.current);
    };
  }, [width, height, numTables, personasPerTable, progressPct, initState, getPhaseFromProgress]);

  return (
    <div className="flex flex-col items-center">
      <canvas
        ref={canvasRef}
        style={{ width: `${width}px`, height: `${height}px` }}
        className="rounded-xl"
      />
      <div className="flex items-center gap-3 mt-3">
        {PHASE_LABELS.map((label, i) => (
          <div key={i} className="flex items-center gap-1.5">
            <div className={`w-2 h-2 rounded-full transition-all duration-500 ${
              i === currentPhase ? 'bg-indigo-500 scale-125' :
              i < currentPhase ? 'bg-indigo-300' : 'bg-gray-200'
            }`} />
            <span className={`text-xs transition-colors duration-300 ${
              i === currentPhase ? 'text-indigo-600 font-semibold' : 'text-gray-400'
            }`}>{label}</span>
          </div>
        ))}
      </div>
      {/* Legend */}
      <div className="flex gap-4 mt-2">
        {TABLE_COLORS.slice(0, numTables).map((color, i) => (
          <div key={i} className="flex items-center gap-1">
            <div className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: color }} />
            <span className="text-xs text-gray-400">Table {i + 1}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
