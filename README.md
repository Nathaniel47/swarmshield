# SwarmShield: Prompt-Infection and Memory Poisoning in Multi-Agent LLM Systems

A simulation testbed that measures how a malicious instruction or a poisoned memory spreads between cooperating LLM agents, modelled like an epidemic on a network (chain, star and mesh topologies), with three defences that stop the spread. Everything runs on a laptop with free LLM APIs and synthetic data; attacks only target the simulated system in this repo.

Status: setup done (Step 2). See [PLAN.md](PLAN.md) for the design and [BUILD_STEPS.md](BUILD_STEPS.md) for progress. Results, demo link and architecture diagram arrive in Step 8.

## Run locally

Requires Python 3.11.

Windows (PowerShell):

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
Copy-Item .env.example .env   # then fill in the keys you have
pytest
streamlit run dashboard/app.py
```

macOS and Linux:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env   # then fill in the keys you have
pytest
streamlit run dashboard/app.py
```

Then open http://localhost:8501. Keys are read only from `SWARMSHIELD_*` environment variables (or the git-ignored `.env`). With no keys, everything that needs a model uses the offline scripted agent.

Docker, locked down (read-only filesystem, no capabilities): `docker compose up --build`.

Lint and format: `ruff check .` and `ruff format .`. Optional commit hooks (gitleaks secret scan, ruff): `pre-commit install`.

## Data and licences

Filled in during Step 3 (InjecAgent, AgentDojo and the synthetic tasks).
