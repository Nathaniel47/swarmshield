# Epidemic analysis (dev split, scripted agent)

Susceptibility 0.5, 10 seeds, 6 rounds, 1140 episodes, no defences. Dev split only; test is reserved for Step 6.

| attack / topology | infection rate | time to peak | peak infected | spread speed | task success |
|---|---|---|---|---|---|
| prompt_infection/chain | 0.50 | 3.50 | 2.06 | 0.76 | 0.91 |
| prompt_infection/star | 0.55 | 3.69 | 2.33 | 0.82 | 0.85 |
| prompt_infection/mesh | 0.88 | 3.98 | 3.88 | 1.24 | 0.61 |
| memory_poisoning/chain | 0.86 | 1.57 | 3.68 | 2.11 | 0.85 |
| memory_poisoning/star | 0.89 | 1.86 | 3.92 | 2.11 | 0.86 |
| memory_poisoning/mesh | 0.96 | 2.71 | 4.38 | 1.94 | 0.56 |

## SIR fit

Per-cell grid-search fit to the share of agents ever infected by each round (beta: per-contact infection chance, gamma: recovery chance, epsilon: round-1 exposure from the shared store, used for memory poisoning only), with its mean squared error. The last column predicts each topology from the parameters fitted on the chain alone.

| attack / topology | beta | gamma | epsilon | fit MSE | MSE predicting from chain fit |
|---|---|---|---|---|---|
| prompt_infection/chain | 0.20 | 0.00 | 0.00 | 0.0019 | 0.0019 |
| prompt_infection/star | 0.30 | 0.00 | 0.00 | 0.0018 | 0.0065 |
| prompt_infection/mesh | 0.20 | 0.20 | 0.00 | 0.0020 | 0.0026 |
| memory_poisoning/chain | 0.30 | 0.20 | 0.60 | 0.0018 | 0.0018 |
| memory_poisoning/star | 0.50 | 0.40 | 0.60 | 0.0015 | 0.0032 |
| memory_poisoning/mesh | 0.20 | 0.40 | 0.60 | 0.0015 | 0.0052 |
