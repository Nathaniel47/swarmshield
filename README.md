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

Only the attacker's wording from public sets is reused, as cover text; every payload's checkable action is our own (write a canary string), and real-looking emails and URLs are replaced with `.test` addresses. Versions are pinned by commit and raw file hashes are in `data/manifest.json`. Rebuild everything with `python -m swarmshield.build_dataset` (downloads the raw files into the git-ignored `data/raw/`); the report is [results/data_report.md](results/data_report.md).

| Source | Licence | Pinned version | What is used |
|---|---|---|---|
| [InjecAgent](https://github.com/uiuc-kang-lab/InjecAgent) (attacker cases) | MIT | `f19c9f2c` | 30 of 62 attacker instructions, reworded into 60 payloads |
| [AgentDojo](https://github.com/ethz-spylab/agentdojo) (v1 injection task goals) | MIT | `089ed468` | 27 attacker goals, read as text only, reworded into 54 payloads |
| Self-written | this repo | n/a | 12 payloads and 60 synthetic research-and-write tasks |

The licences were checked on the two GitHub repositories (both report MIT).
