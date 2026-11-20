# PLAN.md: SwarmShield

A small simulated multi-agent LLM system (planner, researcher, writer plus replicas) with shared memory, two attacks (self-copying prompt infection and shared-memory poisoning), an epidemic analysis of how they spread over chain, star and mesh topologies, three defences, and a live graph dashboard.
Budget: 7 weeks of evenings and weekends, free compute, free hosting, laptop only.

## Scope

| Area | Decision |
|---|---|
| Agent framework | **Plain Python.** An agent is a function over a message list plus a role prompt; a `Swarm` object routes messages along a graph and holds the shared memory. No LangGraph, LangChain or LlamaIndex: every message hop and memory write must be visible, logged and hookable by a defence. |
| Agents | Core system: **planner** (splits the task), **researcher** (reads synthetic documents and writes findings to memory), **writer** (reads findings and drafts the report). Topology experiments use a **6-agent swarm** made of replicas of those roles (1 planner, 3 researchers, 2 writers), because a 3-node graph cannot tell a chain from a mesh. |
| Main LLM | **Groq free API** (`SWARMSHIELD_GROQ_API_KEY`). The binding limit is tokens per day, not requests. Model ID and current limits are verified in week 1 and recorded in `results/run_meta.json`. |
| Second LLM | **Gemini free API** (`SWARMSHIELD_GEMINI_API_KEY`), for a confirmation run on a subset only. |
| Offline agent | A deterministic **scripted agent** with a tunable `susceptibility` (the probability that it obeys and re-emits an injected instruction), seeded. It makes tests, CI and the thousands of epidemic runs free and repeatable. Its probabilities are **calibrated from real-LLM runs**, and that calibration is reported as a limitation, since a scripted agent is a model of an LLM, not an LLM. |
| Attacks | **A1 prompt infection**: a payload hidden in a document that instructs the agent to carry out an action and copy the payload into every message it sends on. **A2 memory poisoning**: a payload written once into the shared store that changes what every later reader does. Both are benign by construction: the "harm" is only a **canary** marker (see Scoring), never a real action. |
| Topologies | Chain, star, mesh (full graph), built with NetworkX. Optional extras if time allows: ring and small-world. |
| Epidemic model | Per-agent state S, I, R (infected, then cleaned by a defence or by finishing the task). Measured per run: infection rate (share of agents ever infected), time to peak, spread speed (new infections per round). A **SIR-style fit** (transmission and recovery rates per topology and defence) is fitted to the measured curves with NetworkX/NumPy and compared with the observed data. |
| Defences | **D1 provenance tags** (every memory entry and message carries who wrote it and whether it derived from untrusted content; untrusted entries are quoted as data and cannot trigger actions). **D2 message sanitiser** (agent-to-agent messages are stripped of instruction-like text and re-templated). **D3 majority check** (the critical step is done by 3 independent agents and the majority output is used; costs 3x calls). Each defence is a switchable hook and is scored on security **and** task success. |
| Scoring | **Automatic, no LLM judge.** *Infected*: the run's canary token appears in an agent's outgoing message, memory write or tool-call arguments (exact match on a unique per-run string). *Task success*: the final report contains the required facts from the synthetic documents (set-membership check) and no canary. Infection and task success are reported together so a defence that blocks everything cannot look perfect. |
| Data | **Synthetic research-and-write tasks** (about 60: a question plus 3-5 synthetic documents with known facts, fixed seed). Attack wording drawn from **InjecAgent** and **AgentDojo** (public task suites; licences confirmed in Step 3). Only the attacker's phrasing is reused, adapted to this system's agents and canaries. Split 30% dev / 70% test. |
| Dashboard | **Streamlit + Plotly + NetworkX layout**: an animated graph with infected agents coloured per round, an S/I/R curve, and a defence selector with a replay of stored runs (live LLM runs are optional and capped). |
| API | **FastAPI is dropped by default** (see Simplifications): Streamlit reads run records from SQLite and `results/` directly. Revisit only if a separate public API turns out to be needed in Step 7. |
| Secrets | Only from `SWARMSHIELD_*` environment variables. Git-ignored `.env`; `.env.example` has names with empty values. Pre-commit gitleaks scan. |
| Out of scope | LangChain/LlamaIndex/LangGraph, fine-tuning, real tools or accounts, real personal data, and attacking anything except this simulated system. |

## 1. Architecture

```mermaid
flowchart LR
  T[Task generator<br/>synthetic docs + facts] --> SW
  subgraph SW[Swarm runtime]
    P[Planner] --> R1[Researchers x3] --> W[Writers x2]
    ROUTER[Message router<br/>topology graph] --- P
    ROUTER --- R1
    ROUTER --- W
  end
  ATK[Attack injector<br/>A1 infection, A2 poisoning] --> SW
  SW <--> MEM[(Shared memory<br/>SQLite, provenance tags)]
  D1{D1 provenance} -.-> MEM
  D2{D2 sanitiser} -.-> ROUTER
  D3{D3 majority} -.-> W
  SW --> LLM[Cached LLM client<br/>Groq / Gemini / scripted]
  SW -. events .-> LOG[(Run log<br/>SQLite)]
  LOG --> SC[Scorer: canary + facts]
  SC --> EP[Epidemic analysis<br/>NetworkX, SIR fit]
  EP --> RES[results/ tables, charts]
  LOG --> DASH[Streamlit dashboard<br/>live graph]
```

- **Agents** (`swarmshield/agents/`): `base.py` (agent = role prompt + message list + LLM call), `roles.py` (planner, researcher, writer), `scripted.py` (offline, seeded, tunable susceptibility).
- **Swarm** (`swarmshield/swarm/`): `topology.py` (chain, star, mesh via NetworkX), `router.py` (delivers messages along edges, calls defence hooks, logs every hop), `runtime.py` (round-based loop with a round cap).
- **Memory** (`swarmshield/memory/`): shared SQLite store with `write(entry, author, provenance)` and `read(query)`. Each entry keeps its author, the chain of sources it derived from and a trust flag.
- **Attacks** (`swarmshield/attacks/`): payload builders (A1, A2), canary generation, injection points (a document, a message, a memory entry).
- **Defences** (`swarmshield/defences/`): `provenance.py`, `sanitiser.py`, `majority.py`, each exposing `check(event) -> Decision(allow | block | rewrite, reason)`.
- **Tasks and data** (`swarmshield/tasks/`, `data/`): synthetic task generator, public attack-wording loader with licence notes.
- **LLM client** (`swarmshield/llm/`): cache, token budget (stops at 95% of the daily limit and resumes after 00:00 UTC), Groq, Gemini, `meta.py` for `run_meta.json`.
- **Epidemic analysis** (`swarmshield/epidemic/`): per-round S/I/R extraction from logs, summary metrics, SIR fit, topology comparison.
- **Dashboard** (`dashboard/`): Streamlit app, Plotly graph animation.

**Metrics**
- **Infection rate** (share of agents infected by the end) and **time to peak**, per topology, attack and defence, with 95% confidence intervals over many seeds.
- **Spread speed**: new infections per round, plus fitted SIR transmission and recovery rates.
- **Task success** under each configuration, and **false-block rate** (clean runs a defence breaks).
- **Cost**: extra LLM calls and tokens per defence (D3 is the expensive one).
- **Variance**: mean and spread over repeated seeds.

## 2. Call budget

Estimates, to be replaced by measurements in Step 4. An episode is one full run of the swarm on one task (6 agents, about 2 rounds, so about 12 LLM calls at about 600 tokens, roughly 7K tokens). With a free limit of about 200K tokens/day that is about **25-30 real-LLM episodes per day**.

| Run | Episodes | Notes |
|---|---|---|
| Scripted-agent grid (free) | tens of thousands: 3 topologies x 2 attacks x 4 defence settings x 50+ seeds x 2 susceptibility levels | No API calls; runs in minutes, in CI. This is where the epidemic curves and fits come from. |
| Real LLM calibration | 60 single-hop episodes (one infected message, measure obedience rate), about 1K tokens each | About 60K tokens, under one day. Sets the scripted agent's susceptibility. |
| Real LLM, no defence vs all defences | 3 topologies x 2 attacks x 10 episodes x 2 settings = 120 | About 840K tokens, roughly 4-5 days. |
| Real LLM, one defence at a time | 30-episode subset x 3 defences | About 630K tokens, roughly 3-4 days. D3 triples the calls, so it runs on the smallest subset. |
| Gemini confirmation | 30 episodes | Cut first if time runs short. |

Everything answered is cached, and runs are resumable across days. Total real-LLM time is roughly 2 weeks of waiting, scheduled in parallel with the build from week 4.

## 3. Repo structure

```
swarmshield/
├── swarmshield/
│   ├── llm/          # client.py, cache.py, budget.py, groq.py, gemini.py, meta.py
│   ├── agents/       # base.py, roles.py, scripted.py
│   ├── swarm/        # topology.py, router.py, runtime.py
│   ├── memory/       # store.py (shared memory with provenance)
│   ├── attacks/      # infection.py, poisoning.py, canary.py, load_public.py
│   ├── defences/     # provenance.py, sanitiser.py, majority.py
│   ├── tasks/        # generator.py (synthetic research-and-write tasks)
│   ├── epidemic/     # states.py, metrics.py, sir_fit.py
│   ├── scoring.py
│   └── config.py
├── dashboard/        # Streamlit app + Plotly graph
├── data/             # synthetic tasks, public attack wording, licence notes
├── results/          # tables, charts, run_meta.json, sample runs
├── docs/             # write-up
├── tests/
├── Dockerfile, docker-compose.yml, pyproject.toml, requirements*.txt
├── .pre-commit-config.yaml, .github/workflows/tests.yml
├── .env.example      # SWARMSHIELD_GROQ_API_KEY=  SWARMSHIELD_GEMINI_API_KEY=
└── README.md, PLAN.md, CLAUDE.md, BUILD_STEPS.md, LEARNING.md, PORTFOLIO.md
```

## 4. Week-by-week

| Week | Goal | Done when |
|---|---|---|
| 1 | Setup and plan checks (Steps 2-3 start) | Repo, CI, gitleaks, `.env.example`. Groq and Gemini models and limits verified and recorded. InjecAgent and AgentDojo licences checked. Agent count and topology list frozen. |
| 2 | Data (Step 3) | Synthetic task generator, attack wording loaded and adapted, data report, dev/test split. |
| 3 | Core feature (Step 4) | Planner, researcher, writer on a chain, shared memory, message router, run log, scripted agent. Token use per episode measured. |
| 4 | Attacks and epidemic analysis (Step 5, parts 1-2) | A1 and A2 working on all three topologies, canary scoring, S/I/R extraction and SIR fit. Real-LLM calibration started. |
| 5 | Defences (Step 5, part 3) | D1-D3 as hooks with tests, each scored on security and task success. Full scripted grid runs. |
| 6 | Dashboard and evaluation (Step 5 part 4, Step 6) | Live graph dashboard, results table, 2-3 charts, variance, limitations. Real-LLM runs finish. |
| 7 | Ship (Steps 7-8) | Public demo, README, write-up, portfolio card. No new features. |

## 5. Risks and first checks

1. **Free-tier limits and model behaviour.** Daily tokens cap real-LLM episodes at about 25-30 per day, and a small model may ignore the injection every time (nothing to measure) or obey every time (nothing to defend). *Check first:* current Groq model list and limits, then a 20-call smoke test of single-hop obedience. Fallback: the scripted agent with calibrated susceptibility carries the full grid, and the real LLM runs on subsets.
2. **Licences and safety of attack text.** InjecAgent and AgentDojo have their own terms, and attack text is adapted, not copied wholesale. *Check first:* both licences, and keep only phrasing reworked for this system. All "harm" is a canary string, all documents are synthetic, and nothing leaves the process, so no real service or person is ever touched.
3. **Scope and a scripted-vs-real gap.** Two attacks, three topologies, three defences, an epidemic fit and a dashboard in 7 weeks is tight, and results from the scripted agent only mean something if calibrated. *Mitigation:* freeze the lists at end of week 1, keep scoring marker-based, keep the dashboard to replaying stored runs, state the calibration gap in the limitations, and cut ring/small-world topologies and the Gemini run before any defence.

## 6. Simplifications

- Plain Python agents and router instead of an agent framework.
- Scripted agent with calibrated susceptibility so most experiments cost nothing.
- SQLite only; the dashboard reads stored runs instead of needing a separate API (FastAPI dropped).
- Three roles replicated to six agents, rather than many role types.
- Marker-based scoring instead of any LLM judge.

## Concepts (plain language + one reading each)

- **Prompt infection (self-replicating injection).** Reading: Lee and Tiwari, "Prompt Infection: LLM-to-LLM Prompt Injection within Multi-Agent Systems" (2024).
- **Memory poisoning.** Reading: Chen et al., "AgentPoison" (2024).
- **Indirect prompt injection and agent benchmarks.** Reading: Zhan et al., InjecAgent (2024); Debenedetti et al., AgentDojo (2024).
- **SIR epidemic models on networks.** Reading: Newman, "Networks", the chapter on epidemics; or the Wikipedia article on compartmental models in epidemiology for the basics.
- **Provenance and taint tracking.** Reading: OWASP Top 10 for LLM Applications, "Prompt Injection" and "Excessive Agency".
- **Redundancy and majority voting for robustness.** Reading: Wang et al., "Self-Consistency Improves Chain of Thought Reasoning" (2022), for the voting idea.
