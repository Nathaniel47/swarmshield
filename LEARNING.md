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
