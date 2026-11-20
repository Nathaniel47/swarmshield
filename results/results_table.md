# Results (held-out test split, scripted agent)

88 test payloads x 42 test tasks, 3 topologies, 5 seeds, 6 rounds. Cells show mean [95% cluster-bootstrap interval over payloads]. ASR = share of attacked runs whose final report has the canary (lower is better). Defence strength D1 'fence effect' fixed at 0.2 (an assumption; see the sensitivity chart). No real LLM was used: see limitations.md.

## ASR with agent susceptibility 0.5

| defence | prompt infection | memory poisoning (forged) | memory poisoning (direct) | benign success | calls/episode |
|---|---|---|---|---|---|
| none | 23% [21%-26%] | 50% [46%-54%] | 50% [46%-54%] | 100% | 36.0 |
| keyword blocklist | 22% [20%-25%] | 50% [46%-54%] | 50% [46%-54%] | 100% | 36.0 |
| D1 provenance | 0% [0%-1%] | 10% [8%-12%] | 0% [0%-0%] | 100% | 36.0 |
| D2 sanitiser | 4% [3%-6%] | 50% [46%-54%] | 50% [46%-54%] | 100% | 36.0 |
| D3 majority | 8% [7%-10%] | 47% [43%-52%] | 47% [43%-52%] | 100% | 37.0 |
| all three | 0% [0%-0%] | 2% [1%-3%] | 0% [0%-0%] | 100% | 37.0 |

Clean-and-correct reports and infection rate at susceptibility 0.5:

| defence | prompt infection: clean / infected | memory poisoning (forged): clean / infected | memory poisoning (direct): clean / infected |
|---|---|---|---|
| none | 77% / 67% | 50% / 99% | 50% / 99% |
| keyword blocklist | 78% / 66% | 50% / 99% | 50% / 99% |
| D1 provenance | 100% / 12% | 90% / 47% | 100% / 0% |
| D2 sanitiser | 96% / 8% | 50% / 8% | 50% / 8% |
| D3 majority | 92% / 67% | 53% / 99% | 53% / 99% |
| all three | 100% / 4% | 98% / 2% | 100% / 0% |

## ASR with agent susceptibility 1.0

| defence | prompt infection | memory poisoning (forged) | memory poisoning (direct) | benign success | calls/episode |
|---|---|---|---|---|---|
| none | 100% [100%-100%] | 100% [100%-100%] | 100% [100%-100%] | 100% | 36.0 |
| keyword blocklist | 98% [93%-100%] | 100% [100%-100%] | 100% [100%-100%] | 100% | 36.0 |
| D1 provenance | 3% [2%-5%] | 21% [17%-25%] | 0% [0%-0%] | 100% | 36.0 |
| D2 sanitiser | 14% [10%-19%] | 100% [100%-100%] | 100% [100%-100%] | 100% | 36.0 |
| D3 majority | 100% [100%-100%] | 100% [100%-100%] | 100% [100%-100%] | 100% | 37.0 |
| all three | 0% [0%-0%] | 9% [7%-11%] | 0% [0%-0%] | 100% | 37.0 |

Clean-and-correct reports and infection rate at susceptibility 1.0:

| defence | prompt infection: clean / infected | memory poisoning (forged): clean / infected | memory poisoning (direct): clean / infected |
|---|---|---|---|
| none | 0% / 100% | 0% / 100% | 0% / 100% |
| keyword blocklist | 2% / 98% | 0% / 100% | 0% / 100% |
| D1 provenance | 97% / 25% | 79% / 75% | 100% / 0% |
| D2 sanitiser | 86% / 10% | 0% / 17% | 0% / 17% |
| D3 majority | 0% / 100% | 0% / 100% | 0% / 100% |
| all three | 100% / 6% | 91% / 4% | 100% / 0% |

## Spread by topology (no defence, first susceptibility)

| attack / topology | agents infected | time to peak | speed | SIR b/g/e | MSE chain |
|---|---|---|---|---|---|
| prompt infection/chain | 54% [51%-56%] | 3.6 | 0.77 | 0.3 / 0.0 / 0.0 | 0.0019 |
| prompt infection/star | 57% [53%-61%] | 3.8 | 0.85 | 0.3 / 0.0 / 0.0 | 0.0014 |
| prompt infection/mesh | 91% [88%-93%] | 4.1 | 1.24 | 0.2 / 0.0 / 0.0 | 0.0184 |
| memory poisoning (forged)/chain | 99% [98%-99%] | 2.8 | 1.86 | 0.5 / 0.0 / 0.6 | 0.0015 |
| memory poisoning (forged)/star | 98% [97%-99%] | 3.0 | 1.89 | 0.5 / 0.0 / 0.6 | 0.0010 |
| memory poisoning (forged)/mesh | 99% [98%-100%] | 2.9 | 1.74 | 0.2 / 0.2 / 0.6 | 0.0112 |

Variance: the largest standard deviation across the 5 seeds of any rate in the tables above is 4.0 percentage points (per-cell values are in eval_test.json).

## Checks

- D2 strips the canary from 126 of 126 built payloads; the keyword blocklist would catch 3.
- Fact scoring cannot be passed without reading the documents: empty report scores 0%, generic report scores 0%, facts of another task scores 0%.
