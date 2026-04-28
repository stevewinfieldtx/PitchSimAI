"""
PitchSimAI x MiroThinker Research Engine - Master Installer

Usage:
    cd C:\\Users\\SteveWinfiel_12vs805\\Documents\\PitchSimAI
    py install_research_engine.py
"""

import os
import shutil
import sys
from pathlib import Path

PITCHSIM_ROOT = Path(r"C:\Users\SteveWinfiel_12vs805\Documents\PitchSimAI")
BACKEND = PITCHSIM_ROOT / "backend"
SERVICES = BACKEND / "services"
SCRIPT_DIR = Path(__file__).parent


def check_prerequisites():
    if not PITCHSIM_ROOT.exists():
        print(f"[ERROR] PitchSimAI not found at {PITCHSIM_ROOT}")
        sys.exit(1)
    for f in [SERVICES / "swarm_engine.py", SERVICES / "simulation.py", BACKEND / "config.py"]:
        if not f.exists():
            print(f"[ERROR] Required file not found: {f}")
            sys.exit(1)
    print("[OK] Prerequisites passed")


def backup_files():
    backup_dir = BACKEND / "_backup_pre_research"
    backup_dir.mkdir(exist_ok=True)
    for f in [BACKEND / "config.py", SERVICES / "swarm_engine.py", SERVICES / "simulation.py"]:
        dest = backup_dir / f.name
        if not dest.exists():
            shutil.copy2(f, dest)
            print(f"  Backed up {f.name}")
    print(f"[OK] Backups in {backup_dir}")


def install_research_engine():
    source = SCRIPT_DIR / "research_engine.py"
    dest = SERVICES / "research_engine.py"
    if not source.exists():
        print(f"[ERROR] research_engine.py not found next to this script")
        sys.exit(1)
    shutil.copy2(source, dest)
    print(f"[OK] Installed research_engine.py")


def patch_config():
    config_file = BACKEND / "config.py"
    code = config_file.read_text(encoding="utf-8")
    if "serper_api_key" in code:
        print("  [SKIP] config.py already patched")
        return
    code = code.replace(
        '    openrouter_concurrency_per_model: int = 10',
        '    openrouter_concurrency_per_model: int = 10\n'
        '\n'
        '    # Research Engine (MiroThinker tool stack)\n'
        '    serper_api_key: str = ""\n'
        '    serper_base_url: str = "https://google.serper.dev"\n'
        '    jina_api_key: str = ""\n'
        '    jina_base_url: str = "https://r.jina.ai"'
    )
    config_file.write_text(code, encoding="utf-8")
    print("[OK] Patched config.py")


def patch_swarm_engine():
    swarm_file = SERVICES / "swarm_engine.py"
    code = swarm_file.read_text(encoding="utf-8")
    if "research_context" in code:
        print("  [SKIP] swarm_engine.py already patched")
        return

    # AgentPersona.__init__ - add research_context
    code = code.replace(
        '        bio: str = "",\n    ):\n        self.name = name',
        '        bio: str = "",\n        research_context: str = "",\n    ):\n        self.name = name'
    )
    code = code.replace(
        '        self.bio = bio\n        self.messages',
        '        self.bio = bio\n        self.research_context = research_context\n        self.messages'
    )

    # system_prompt - capture as variable and append research
    code = code.replace(
        '        return f"""You are {self.name}, {self.title}',
        '        prompt = f"""You are {self.name}, {self.title}'
    )
    code = code.replace(
        'concrete reasoning. You have real opinions shaped by your experience."""',
        'concrete reasoning. You have real opinions shaped by your experience."""\n'
        '\n'
        '        if self.research_context:\n'
        '            prompt += "\\n\\nCOMPANY & MARKET INTELLIGENCE (from pre-simulation research):\\n"\n'
        '            prompt += self.research_context + "\\n"\n'
        '            prompt += "Use this real-world intelligence. Reference specific facts.\\n"\n'
        '            prompt += "Your concerns should reflect the ACTUAL situation, not generic objections."\n'
        '\n'
        '        return prompt'
    )

    # generate_committee_tables - accept research_context
    code = code.replace(
        '    existing_personas: Optional[List[Dict[str, Any]]] = None,\n'
        '    seed: Optional[int] = None,\n'
        ') -> List[CommitteeTable]:',
        '    existing_personas: Optional[List[Dict[str, Any]]] = None,\n'
        '    seed: Optional[int] = None,\n'
        '    research_context: str = "",\n'
        ') -> List[CommitteeTable]:'
    )
    code = code.replace(
        '                budget_authority=role_config["budget_authority"],\n'
        '                bio=f"15+ years in {display_industry}.',
        '                budget_authority=role_config["budget_authority"],\n'
        '                research_context=research_context,\n'
        '                bio=f"15+ years in {display_industry}.'
    )

    # SwarmEngine.run - accept research_context
    code = code.replace(
        '        progress_callback: Optional[Callable] = None,\n'
        '        seed: Optional[int] = None,\n'
        '    ) -> Dict[str, Any]:',
        '        progress_callback: Optional[Callable] = None,\n'
        '        seed: Optional[int] = None,\n'
        '        research_context: str = "",\n'
        '    ) -> Dict[str, Any]:'
    )
    code = code.replace(
        '            existing_personas=existing_personas,\n'
        '            seed=seed,\n'
        '        )',
        '            existing_personas=existing_personas,\n'
        '            seed=seed,\n'
        '            research_context=research_context,\n'
        '        )'
    )

    swarm_file.write_text(code, encoding="utf-8")
    print("[OK] Patched swarm_engine.py")


def patch_simulation():
    sim_file = SERVICES / "simulation.py"
    code = sim_file.read_text(encoding="utf-8")
    if "research_engine" in code:
        print("  [SKIP] simulation.py already patched")
        return

    # Add import
    code = code.replace(
        "from services.swarm_engine import get_swarm_engine",
        "from services.swarm_engine import get_swarm_engine\n"
        "from services.research_engine import get_research_engine"
    )

    # Add research step before progress callback
    research_block = (
        '            # -- Pre-Simulation Research (MiroThinker-inspired) --\n'
        '            research_context = ""\n'
        '            research_data = {}\n'
        '            enable_research = (sim.config or {}).get("enable_research", True)\n'
        '\n'
        '            if enable_research:\n'
        '                try:\n'
        '                    sim.config = {**(sim.config or {}), "swarm_stage": "researching", "swarm_detail": "Researching target company & industry..."}\n'
        '                    sim.progress_pct = 8\n'
        '                    await db.commit()\n'
        '\n'
        '                    research_engine_inst = get_research_engine()\n'
        '                    research_result = await research_engine_inst.research_target(\n'
        '                        company_name=company_name,\n'
        '                        industry=industry,\n'
        '                        target_audience=target_audience,\n'
        '                        pitch_content=pitch_content,\n'
        '                    )\n'
        '                    research_context = research_result.context_block\n'
        '                    research_data = research_result.to_dict()\n'
        '                    logger.info(\n'
        '                        f"Pre-sim research: quality={research_result.research_quality}, "\n'
        '                        f"sources={research_result.sources_used}, "\n'
        '                        f"time={research_result.research_elapsed_seconds}s"\n'
        '                    )\n'
        '                except Exception as e:\n'
        '                    logger.warning(f"Pre-sim research failed (non-fatal): {e}")\n'
        '                    research_context = ""\n'
        '                    research_data = {"error": str(e)}\n'
        '\n'
    )
    code = code.replace(
        '            # Progress callback to update DB\n'
        '            async def update_progress(stage: str, detail: str = "", pct: int = 0):',
        research_block +
        '            # Progress callback to update DB\n'
        '            async def update_progress(stage: str, detail: str = "", pct: int = 0):'
    )

    # Pass research_context to engine.run()
    code = code.replace(
        '                existing_personas=personas,\n'
        '                progress_callback=update_progress,\n'
        '            )',
        '                existing_personas=personas,\n'
        '                progress_callback=update_progress,\n'
        '                research_context=research_context,\n'
        '            )'
    )

    # Store research data
    code = code.replace(
        '                # Store full debate for the UI to render\n'
        '                "debate_transcript": swarm_result.get("tables", []),',
        '                # Store full debate for the UI to render\n'
        '                "debate_transcript": swarm_result.get("tables", []),\n'
        '                # Research intel from pre-simulation research\n'
        '                "research_intel": research_data,'
    )

    sim_file.write_text(code, encoding="utf-8")
    print("[OK] Patched simulation.py")


def main():
    print("=" * 60)
    print("  PitchSimAI x MiroThinker Research Engine - Installer")
    print("=" * 60)
    print()
    check_prerequisites()
    print()
    print("Creating backups...")
    backup_files()
    print()
    print("Installing research_engine.py...")
    install_research_engine()
    print()
    print("Patching config.py...")
    patch_config()
    print()
    print("Patching swarm_engine.py...")
    patch_swarm_engine()
    print()
    print("Patching simulation.py...")
    patch_simulation()
    print()
    print("=" * 60)
    print("  DONE! Next steps:")
    print("=" * 60)
    print()
    print("  1. Add to .env:")
    print("     SERPER_API_KEY=your_key")
    print("     SERPER_BASE_URL=https://google.serper.dev")
    print("     JINA_API_KEY=your_key")
    print("     JINA_BASE_URL=https://r.jina.ai")
    print()
    print("  2. pip install httpx --break-system-packages")
    print("  3. Add keys to Railway env vars")
    print("  4. Test locally, push to Railway")
    print()
    print("  Serper keys: https://serper.dev (2,500 free)")
    print("  Jina keys:   https://jina.ai (free tier)")
    print("  Cost/sim:    ~$0.01-0.03")
    print()
    print("  Disable per-sim: config={\"enable_research\": false}")


if __name__ == "__main__":
    main()
