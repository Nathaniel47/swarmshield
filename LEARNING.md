# LEARNING.md

Plain-English notes on what was built and why it matters.

## Step 1: Kickoff & plan

- **Why an epidemic model?** A malicious instruction that one agent copies into its message to the next behaves like a germ: it needs a host that is susceptible, a contact between hosts, and a chance of passing on. SIR (Susceptible, Infected, Recovered) is the classic way to describe that. Treating agent networks this way lets us ask the same questions epidemiologists ask: how fast does it spread, how many get infected, and which network shape (chain, star, mesh) is safest? Reading: Lee et al., "Prompt Infection: LLM-to-LLM Prompt Injection within Multi-Agent Systems" (2024).
- **Why memory poisoning is different from prompt infection.** Infection travels in messages and dies when the conversation ends. A poisoned memory entry stays in the shared store and infects every agent that reads it later. Reading: Chen et al., "AgentPoison" (2024).
- **Why a scripted agent as well as a real LLM.** Free API limits are tokens per day, so thousands of epidemic runs on a real model are impossible. A deterministic agent that obeys an injected instruction with a set probability lets us run the full grid for free; the real LLM is used to measure that probability and to confirm the headline results.

## Step 2: Repo setup

- **Package layout** (`swarmshield/`, `dashboard/`, `tests/`): mirrors PLAN.md so each part (agents, swarm, memory, attacks, defences, tasks, epidemic analysis) has one obvious home. The empty packages are placeholders for later steps.
- **`config.py`**: one place for the topology list, the attack list, the three defence switches and the 6-agent role mix. `CONFIGS` lists the 5 defence settings that will be compared (none, each alone, all three), so every experiment is just a named setting and is reproducible.
- **Cached LLM client** (`llm/`): every model call goes through one function that checks an on-disk cache first, then a daily token budget. Why it matters: free APIs limit tokens per day, so a rerun must never pay twice for an answer, and a cache makes results repeatable. The Groq and Gemini backends arrive in Step 4. The rate limits in `config.py` are placeholders copied from an earlier project and are rechecked in Step 4.
- **`run_meta.json` helper**: records model IDs, settings and the git commit next to the results, so any number traces back to the code that made it.
- **Secrets**: keys come only from `SWARMSHIELD_*` variables. `.env` is git-ignored and `.env.example` holds names only; the optional gitleaks pre-commit hook blocks key-like strings. Free-tier keys pushed to a public repo get scraped within minutes.
- **Docker and CI**: the container runs as a non-root user with a read-only filesystem and no Linux capabilities; GitHub Actions runs ruff and pytest, then builds the image and checks the dashboard's health endpoint. The workflow will only run once a GitHub remote exists.

How to check: `pytest` and `ruff check .` both pass (10 tests). The Docker build and the CI workflow were not run locally.

## Step 3: Data pipeline

- **Synthetic tasks** (`tasks/generator.py`): 60 research-and-write tasks. Each is a question plus 3-5 short documents about an invented place, with one fact (a number) per document. A correct report must contain all the numbers, so task success is a simple automatic check. A fixed seed makes the same 60 tasks every time, and a check confirms each number appears exactly once in the documents, so a stray match cannot count as success. Everything is made up, so no real person, organisation or place can appear.
- **Payloads** (`attacks/payloads.py`): a payload is the malicious text an attacker plants. Prompt infection (A1) goes into a document and asks the agent to repeat the notice in every message it sends on, which is what lets it spread. Memory poisoning (A2) goes into shared memory as a standing note. Both only ask the agent to write a **canary**: a unique per-run code. Finding the canary somewhere it should not be is the whole definition of "infected", so scoring needs no judge model.
- **Public data, adapted** (`attacks/load_public.py`): InjecAgent and AgentDojo (both MIT, pinned by commit, file hashes recorded) supply attacker wording only. Their original goals (unlock a smart lock, send a payment) do not exist in this system, so their wording is cover text and the canary is the checkable action. Emails and URLs are swapped for `.test` addresses, so no payload names a real person. AgentDojo's Python files are read as text with `ast` and never run. Reading: the AgentDojo paper (Debenedetti et al., 2024) for how injection tasks are defined.
- **Paired design**: each public wording is used for one A1 and one A2 payload, so differences between the attacks are not caused by different wording. A pair always stays in the same split.
- **Dev/test split**: a seeded 30/70 split per source. Tune defences on dev only, then report on test, otherwise the results would flatter the defences. Reading: the scikit-learn user guide on cross-validation, section on held-out test sets.
- **Limits**: the self-written payload set is small (12), and substring fact scoring can be passed by luck; both are listed in `results/data_report.md` and get checked in the evaluation.

How to check: `python -m swarmshield.build_dataset` rebuilds everything and stops with an error on duplicate ids, a payload with the wrong number of canary placeholders, a real-looking email or URL, or a fact that does not appear exactly once. Then read `results/data_report.md` and run `pytest` (18 tests).

## Step 4: Core feature, the multi-agent system

- **What an agent is here** (`agents/base.py`): a role prompt plus one LLM call per round. It sees its documents, the most recent shared-memory entries and its inbox, and replies in a small labelled format: `NOTE` (saved to shared memory), `MESSAGE` (sent to neighbours) and, for a writer, `REPORT`. There is no framework: the whole agent is about 40 lines, so every input and output can be logged and later intercepted by a defence. If a free model ignores the format, the reply is used whole rather than crashing the run.
- **Roles**: the planner sets the plan, researchers read documents and record facts, writers turn facts into the report. The swarm has 6 agents (1 planner, 3 researchers, 2 writers) so topology differences are visible.
- **Two communication channels, on purpose** (`memory/store.py`, `swarm/router.py`). *Messages* only go to graph neighbours and take one round per hop, so the shape of the network (chain, star, mesh) controls how fast a message-borne infection can travel. *Shared memory* is global and instant, so anything poisoned there reaches everyone regardless of topology. Comparing the two is the core of the epidemic analysis. Reading: Newman, "Networks", the introduction to epidemics on networks.
- **Provenance is recorded from day one**: each memory entry and message keeps its author, the sources it was derived from (documents, earlier memory entries, messages) and a trusted flag. Nothing uses it yet; defence D1 will (Step 5). Recording it now means defences cannot be accused of seeing information the attackers could not.
- **Hooks**: memory has write filters and the router has message filters. Each can pass, rewrite or block. Defences D1 and D2 will be exactly these, so switching a defence on or off changes no agent code.
- **Run log** (`swarm/runtime.py`): every LLM call, memory write, message, dropped message and report is an event with a round and agent id, saved to SQLite on request. The epidemic analysis and the dashboard will read this log, not the agents.
- **Scripted agent** (`agents/scripted.py`): a deterministic stand-in for the LLM that keeps the sentences containing numbers. If it sees a canary token, it obeys with a set probability (its *susceptibility*), decided by a seeded hash so reruns are identical, and copies a self-replicating notice onward. At susceptibility 1.0 it is the worst case; real values will be measured from real LLM runs and plugged in. Its main purpose is to let thousands of epidemic runs cost nothing.
- **Scoring** (`scoring.py`): task success means every required number appears in the report and no canary does; an agent is infected from the first round it emits the canary in a note, message or report. No judge model.
- **LLM clients**: Groq and Gemini backends go through the same cache and daily token budget as the scripted one. They have not been run, because no API key is set in this project yet; the tests check only that they refuse to run without a key.

How to run and check:
- `python -m swarmshield.run_episode --task t000 --topology chain` runs one episode offline and prints success, call count, estimated tokens and the report. Add `--backend groq` once `SWARMSHIELD_GROQ_API_KEY` is in `.env`.
- `python -m swarmshield.run_episode --measure` runs all 60 tasks on all 3 topologies (180 episodes) offline and writes `results/episode_cost.json`.
- `pytest` (32 tests) includes the spread checks: with an infected document, an infection reaches the planner and researcher-2 in round 2 and the far end of a chain in round 5, and mesh beats star beats chain.

## Step 5.1: Attacks

- **A1, prompt infection** (`attacks/infection.py`): the attacker plants a notice in one document. Whichever researcher reads it is "patient zero". The notice tells the agent to emit a canary and to copy the whole notice into every message it sends on, so each infected agent infects its neighbours. This is a worm: it needs no attacker action after the first plant. Reading: Lee and Tiwari, "Prompt Infection" (2024).
- **A2, memory poisoning** (`attacks/poisoning.py`): the attacker writes one standing note into the shared memory before the run. Every agent that retrieves it can be affected, whatever the network shape. Two strengths: `direct` (an unknown author with no provenance) and `forged` (written as researcher-1, citing that researcher's real document, and claiming to be trusted). The forged one matters because the first defence checks provenance, and an attacker who knows the task can fake plausible provenance. Reading: Chen et al., "AgentPoison" (2024).
- **Why canaries**: the planted text only asks the agent to write a unique code. That is harmless by construction, easy to detect exactly, and still shows whether an agent obeyed text it should have treated as data.
- **Observed with the worst-case scripted agent**: infection starts at researcher-1 in round 1 and reaches every agent on all three topologies if given enough rounds; poisoned memory reaches all six agents in rounds 1-2 on a chain, because it does not travel along edges. With susceptibility 0 nothing spreads and the task succeeds.
- **Limits**: a poisoned entry stays visible only while it is among the 12 most recent memory entries, which is about two rounds. A real retrieval system would keep returning it when relevant, so memory poisoning is probably understated here.

How to check: `pytest tests/test_attacks.py` (checks all 126 built payloads infect the worst-case agent, the forged style, and that the seed write is logged but not counted as an infection).
