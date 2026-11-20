# CLAUDE.md: SwarmShield coding rules

- Follow PLAN.md; if anything conflicts, PLAN.md wins. Work one BUILD_STEPS.md step at a time.
- Python 3.11, no LangChain/LlamaIndex/LangGraph. Keep each agent a plain function over a message list and each defence a separate hook.
- Secrets only from environment variables named `SWARMSHIELD_*`. Never commit `.env`; `.env.example` has names with empty values.
- All attacks target this simulated multi-agent system only. Memory and messages are in-process or local SQLite, tasks and documents are synthetic. Never use real services or real personal data.
- Scoring is automatic (canary markers and state checks). No LLM judge.
- Every LLM call goes through the cached client in `swarmshield/llm/`. Fixed seeds; record model IDs, temperature, seed and git commit in `results/run_meta.json`.
- Format and lint with ruff (line length 100). Write tests in `tests/` for every feature; run `pytest` before each commit.
- Code comments only for non-obvious reasons. Plain-English explanations go in LEARNING.md, not chat.
- Commit with the step name in the message. Push only once a GitHub remote exists and the user has approved it. Never add attribution to commits or PRs: no `Co-Authored-By` lines and no "Generated with" text.
