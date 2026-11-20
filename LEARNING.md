# LEARNING.md

Plain-English notes on what was built and why it matters.

## Step 1: Kickoff & plan

- **Why an epidemic model?** A malicious instruction that one agent copies into its message to the next behaves like a germ: it needs a host that is susceptible, a contact between hosts, and a chance of passing on. SIR (Susceptible, Infected, Recovered) is the classic way to describe that. Treating agent networks this way lets us ask the same questions epidemiologists ask: how fast does it spread, how many get infected, and which network shape (chain, star, mesh) is safest? Reading: Lee et al., "Prompt Infection: LLM-to-LLM Prompt Injection within Multi-Agent Systems" (2024).
- **Why memory poisoning is different from prompt infection.** Infection travels in messages and dies when the conversation ends. A poisoned memory entry stays in the shared store and infects every agent that reads it later. Reading: Chen et al., "AgentPoison" (2024).
- **Why a scripted agent as well as a real LLM.** Free API limits are tokens per day, so thousands of epidemic runs on a real model are impossible. A deterministic agent that obeys an injected instruction with a set probability lets us run the full grid for free; the real LLM is used to measure that probability and to confirm the headline results.
