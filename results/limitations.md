# Limitations

Read these before quoting any number from `results_table.md`.

## What the numbers are, and are not

1. **No real language model was used.** Every number comes from a rule-based scripted agent that obeys planted text with a probability we set (0.5 and 1.0). The results say how the *defences behave against an agent with that obedience*, and how far an attack spreads *if* agents obey at that rate. They say nothing yet about how often Groq or Gemini models obey planted text. No API key was available, so the calibration step in PLAN.md (measure real obedience, plug it into the scripted agent) is not done. Until it is, treat the headline numbers as a model, not a measurement.
2. **D1's result depends on an assumption.** D1 has two parts. Blocking writes with unverifiable provenance is deterministic and is what zeroes the `direct` poisoning attack. The fence ("treat this as untrusted data") is modelled by multiplying obedience by 0.2 for fenced text. That 0.2 is made up. `chart_d1_sensitivity.png` shows that at 1.0 (fence useless) D1 alone is no better than no defence against the worm or the forged poison. Real models are known to follow injected instructions even when told not to, so the true value may be much worse than 0.2.
3. **The `forged` poison is the more honest test, and it is not solved.** With all three defences it still succeeds in 2% of runs at obedience 0.5 and 9% at 1.0, and D2 and D3 do nothing against it. A stronger attacker (one that makes a compromised agent write the poison, or one that avoids the retrieval trigger) was not tested.
4. **D2 is tuned to this task.** It keeps only sentences that contain a number, because every fact in this task is numeric. It stripped all 126 built payloads, but a general system cannot allow-list "sentences with a number". Dropping every message without a number also removed content that agents would normally send; task success stayed at 100% only because agents also share facts through memory.
5. **D3 only helps against a minority.** With obedience 1.0 it does nothing: both normal writers are fooled and outvote the isolated third drafter. It cannot help against memory poisoning, because all three drafters read the same store.
6. **The baseline is deliberately weak.** The keyword blocklist catches 3 of 126 payloads. A better baseline (a trained prompt-injection classifier) was not tried, so "our defences beat the baseline" is a statement about a naive baseline.

## Design limits of the simulation

- **Six agents, three shapes.** Differences between chain, star and mesh come from one agent placement (patient zero is researcher-1, a leaf of the star). Other starting points, larger swarms, ring and small-world graphs were not run. The SIR fit is a coarse grid search, and gamma (recovery) is poorly identified because the observed curve is cumulative.
- **Infection means "emitted the canary".** The canary is harmless text. A real attack that makes an agent take an action (send data, call a tool) may spread differently, and a model could obey internally without emitting the marker.
- **Memory retrieval is simple.** Retrieval ranks by shared words with the task question, and the poison note is written to match. A poison that does not match retrieves less, and a vector store would behave differently.
- **Tasks are tiny and synthetic.** Reports are checked by finding numbers in the text, which was verified not to be passable by agents that never read the documents (empty, generic and other-task reports score 0%), but real research-and-write quality is far richer.

## Statistics

- Runs that share a payload are not independent, so intervals are bootstrapped over payloads (88 test payloads). Seeds change the scripted agent's random draws only; the largest standard deviation across 5 seeds is 4.0 percentage points. With a scripted agent, more seeds mostly re-sample the same rules.
- Attack wording comes from two public sets plus 12 self-written payloads, adapted to a canary goal. Per-source results were not reported because the self-written set is small.
- The dev split was used to build and debug the defences (Step 5) and the test split was run in full once for this evaluation. Short plumbing checks (a few payloads) also touched test payloads before that run, and no defence was changed after the full run.


## What would improve it

1. Add a Groq or Gemini key, measure real obedience on the 126 payloads (about 60 K tokens, under a day of free limit), and replace the assumed 0.5, 1.0 and 0.2 with measured values.
2. Run a smaller real-model confirmation of the defence comparison (PLAN.md budget: about 15 to 20 episodes a day).
3. Test a stronger poisoning attacker and a larger, more varied swarm.
4. Compare against a trained injection classifier as the baseline.
