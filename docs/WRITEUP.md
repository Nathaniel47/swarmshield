# SwarmShield: spread and containment of prompt infection and memory poisoning in a simulated multi-agent LLM system

## 1. Problem

Teams of cooperating LLM agents read documents, keep shared notes and message each other. That makes a new kind of attack possible. A single malicious instruction planted in a document one agent reads can tell that agent to copy the instruction into its messages, so the next agent reads it too and the instruction spreads, like a worm (called *prompt infection*, Lee and Tiwari 2024). A single poisoned entry in a shared memory store can be retrieved by every agent that later queries it (*memory poisoning*, e.g. Chen et al., AgentPoison, 2024). Most agent-security work scores attacks against one agent. This project asks three questions about a team:

1. How far and how fast does an attack spread, and does the shape of the agent network matter?
2. Does the spread behave like an epidemic, so that a simple SIR-style model explains it?
3. Which defences stop it, and what do they cost in task quality?

Everything is simulated: a small swarm with synthetic documents, attacks that only ask an agent to write a harmless code string, and no real service or person involved.

## 2. Method

**System.** Six agents (one planner, three researchers, two writers) written in plain Python without an agent framework. Each round every agent makes one LLM call over a view of its documents, the twelve most task-relevant shared-memory entries and its inbox, and replies with a note for memory, a message for its neighbours and (writers) a report. Messages travel one hop per round along a graph that is a chain, a star or a mesh; memory is global and instant. Memory entries and messages carry provenance: author, the sources they were derived from, and a trusted flag. All LLM calls go through one cached client with a daily token budget, so a rerun never pays twice.

**Task and data.** 60 synthetic research-and-write tasks: a question plus three to five short documents about an invented place, each holding one numeric fact. A report is correct if it contains every required number. A check confirms this cannot be passed without reading (empty, generic and other-task reports all score 0%). Attack wording comes from two public suites, InjecAgent (MIT) and AgentDojo (MIT), pinned by commit; only the attacker's phrasing is reused, as cover text, with emails and URLs replaced by `.test` addresses. There are 126 payloads (60 from InjecAgent, 54 from AgentDojo, 12 self-written), split 30/70 into development and test sets by paired group. Defences were built on the development set; the test set was run once.

**Attacks.** *A1 prompt infection*: a notice in one document tells the agent to write a canary code (a unique per-run string) and to copy the notice into every message it sends. *A2 memory poisoning*: one standing note planted in memory before the run, opening with the task question so retrieval ranks it as relevant. A2 comes in two strengths: written by an unknown author with no provenance (*direct*), or written as a real agent citing that agent's real document (*forged*).

**Scoring.** No LLM judge. An agent is *infected* in the first round it emits the canary in a note, message or report. The *attack success rate* (ASR) is the share of attacked runs whose final report contains the canary. A report is *clean* if it also has every fact. *Benign success* is the same fact check on un-attacked runs, so a defence that wrecks the answer is caught.

**Epidemic analysis.** From the run log, each round each agent is Susceptible, Infected (emitted the canary this round) or Recovered (earlier, quiet now). A discrete-time SIR model on the agent graph (infection probability 1 - (1 - beta)^k with k infected neighbours, recovery probability gamma; for poisoning, round-one exposure probability epsilon in place of a patient zero) is fitted to the share of agents ever infected by grid search.

**Defences.** *D1 provenance tags*: block memory writes whose author is not a swarm agent or whose cited sources are not real for that author, ignore claimed trust, and label untrusted content as data in prompts. *D2 message sanitiser*: keep only sentences that state a fact (contain a number) and contain no instruction-like wording. *D3 majority check*: a third writer that reads only shared memory drafts the report next to the two normal writers, and the final report keeps only what at least two drafts agree on. The baseline is a naive keyword blocklist.

**The model of an LLM.** Free-tier APIs allow roughly 15 to 20 real-model episodes a day, far too few for a grid, so the experiments use a deterministic scripted agent that obeys planted text with a set probability (0.5 or 1.0), decided by a seeded hash. D1's fencing is modelled as multiplying that probability by 0.2. Both are assumptions; see limitations.

## 3. Results

Test split, 88 payloads, 42 tasks, 3 topologies, 5 seeds. Intervals are 95% bootstraps over payloads; the largest standard deviation across seeds of any rate is 4.0 percentage points. At obedience 0.5, ASR (lower is better):

| Defence | Prompt infection | Memory poisoning (forged) | Memory poisoning (direct) | Benign success |
|---|---|---|---|---|
| None | 23% | 50% | 50% | 100% |
| Keyword blocklist | 22% | 50% | 50% | 100% |
| D1 provenance | 0% | 10% | 0% | 100% |
| D2 sanitiser | 4% | 50% | 50% | 100% |
| D3 majority | 8% | 47% | 47% | 100% |
| All three | 0% | 2% | 0% | 100% |

At obedience 1.0 the undefended attacks always succeed (100%); D1 gives 3% / 21% / 0%, D2 14% / 100% / 100%, D3 100% across the board, all three 0% / 9% / 0%.

**Network shape matters for the worm, not for the poison.** Without defences the worm infects 54% of agents on a chain, 57% on a star (patient zero is a leaf, so the hub adds little by round six) and 91% on a mesh. Poisoned memory reaches about 99% of agents on all three shapes, because it does not travel along edges. Parameters fitted on the chain alone predict the star curve (mean squared error 0.0014) and, less well, the mesh curve (0.018), so network structure explains most of the topology difference for the worm.

**Defences cover different routes.** D2 sits on messages, so it stops the worm (23% to 4%) but not a store the agents read directly. D3 helps only when fewer than half the drafters are fooled: it helps at obedience 0.5, does nothing at 1.0 and cannot help against poisoning, because all three drafters read the same store. D1 is the only one that touches memory: it removes the unknown-author poison completely and cuts the forged poison to 10%, but the forged result depends on the assumed fence effect. A sensitivity chart shows that if fencing has no effect (1.0), D1 alone is no better than no defence for either attack. The three together reach 0% and 2%, with benign success unchanged and D3 adding one LLM call per episode.

**The naive baseline fails.** The keyword blocklist catches 3 of the 126 payloads and changes ASR by one point. The sanitiser's allow-list strips the canary from all 126, which is why wording-blind allow-listing beats phrase blocking.

## 4. Limitations

Every rate in the results is a property of the scripted agent and its assumed obedience. A later check on Groq `openai/gpt-oss-20b` (76 single-agent calls, all 19 development payloads per attack, with and without D1's label) found the planted code in 15 of 19 unlabelled infection replies (95% interval 57-92%) and 18 of 19 memory-poisoning replies (75-99%). With the label it was 1 of 19 for infection but still 18 of 19 for memory poisoning. **For this model the fence did nothing against poisoned memory, so the assumed 0.2 is wrong there, and the forged-poison results for D1 (10%) and for all three defences (2%) should not be expected to hold.** D1's write filter, which blocks the unknown-author poison, does not depend on the model. Also, in 13 of the 15 obeying infection replies the code appeared only before the labelled fields, which the reply parser discards; it reached the `MESSAGE` field in 2 of 19. The scripted worm relays far more often than that, so the spread and topology results may not carry over. These are single-agent turns; no multi-agent episode has been run on a real model. D2's number allow-list suits a numeric task and would not carry over to general text; all of its messages without numbers (such as the planner's) are removed, and benign success stays at 100% only because agents also share facts through memory. The forged poison is not solved (2 to 9% with all defences even in the simulation), and a stronger attacker was not tested. The swarm has six agents on three graph shapes with one patient-zero placement, and the SIR fit is a coarse grid search where recovery is poorly identified. "Infected" means emitting a harmless marker; real attacks that trigger actions may spread differently. The keyword baseline is deliberately naive and a trained classifier was not compared. Full list: `results/limitations.md`.

## 5. Lessons learned

- **Model the channels separately.** Giving the swarm both a hop-limited message channel and a global memory channel was what made the results interesting: the same attack behaves like an epidemic on one and like a broadcast on the other, and different defences cover each.
- **A first memory design hid the poison.** An early recency window let the poisoned note scroll out of view after two rounds, which made the sanitiser look far better against poisoning than it should have. Retrieval by relevance, with a note crafted to match the task, fixed it. Memory-poisoning results depend heavily on how memory is retrieved.
- **A silent bug can look like a result.** For a while D1's fence did nothing because an edit had not applied; two rows of the comparison table were identical to the baseline, which is what gave it away. Comparing every defence row with the baseline row is a cheap check.
- **Report the assumption next to the number.** Several headline effects depend on a value that was assumed, not measured. Charting the sensitivity to it (and listing it first in the limitations) is more honest than a single table.
- **Build the offline stand-in first.** A deterministic agent made tests, CI, thousands of runs and the dashboard free and repeatable. Its price is that it must eventually be calibrated against a real model, which is the first item of future work.

## References

Lee, D. and Tiwari, M. (2024). Prompt Infection: LLM-to-LLM Prompt Injection within Multi-Agent Systems. Chen, Z. et al. (2024). AgentPoison: Red-teaming LLM Agents via Poisoning Memory or Knowledge Bases. Zhan, Q. et al. (2024). InjecAgent: Benchmarking Indirect Prompt Injections in Tool-Integrated LLM Agents. Debenedetti, E. et al. (2024). AgentDojo: A Dynamic Environment to Evaluate Prompt Injection Attacks and Defenses for LLM Agents. Greshake, K. et al. (2023). Not What You've Signed Up For: Compromising Real-World LLM-Integrated Applications with Indirect Prompt Injection. Wang, X. et al. (2022). Self-Consistency Improves Chain of Thought Reasoning in Language Models.
