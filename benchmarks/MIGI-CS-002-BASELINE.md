# MIGI-CS-002 Synthetic Benchmark Baseline

Recorded from GitHub Actions run `34171847370` on 2026-09-07.

Environment: Ubuntu 24.04, CPython 3.11.16.

## Scope

This is a deterministic **synthetic contract benchmark**, not a real-world accuracy claim. It tests whether the LUFIT/SFO/RAG0SHOT mechanisms behave as designed under controlled failure modes.

Corpus size: **1,000 cases**

- supported: 200
- contradicted: 200
- unresolved: 200
- out-of-profile: 200
- simulation-only: 200

Every case also contains a five-candidate retrieval problem with one trusted relevant candidate and adversarial distractors.

## Retrieval baseline

| Metric | Semantic-only | RAG0SHOT |
|---|---:|---:|
| Precision@1 | 0.25 | 1.00 |
| Recall@3 | 1.00 | 1.00 |
| MRR | 0.625 | 1.00 |
| Bad-source top-1 rate | 0.75 | 0.00 |

Delta from semantic-only to RAG0SHOT:

- Precision@1: **+0.75**
- MRR: **+0.375**
- bad-source top-1 rate: **-0.75**

The corpus intentionally creates a high-semantic / low-provenance distractor in 75% of retrieval cases. These numbers therefore verify the weighting mechanism; they do not establish performance on natural data.

## Claim qualification baseline

| Metric | Result |
|---|---:|
| Qualification accuracy | 1.00 |
| Tre evidence-state accuracy | 1.00 |
| Multiclass Brier score | 0.0075246251 |
| Top-class calibration error | 0.0708266667 |
| Out-of-profile refusal accuracy | 1.00 |
| Simulation-boundary accuracy | 1.00 |

Pure qualification latency on the CI runner:

- mean: **0.00859 ms**
- p50: **0.00828 ms**
- p95: **0.01022 ms**

These latency values are machine-dependent and are recorded only as a reference point, not as a gating threshold.

## Receipt overhead sample

Sample size: **20 real VerifiableClaimRuntime receipts**

- mean receipt size: **716.6 bytes**
- p95 receipt size: **725 bytes**
- mean end-to-end qualification + persistence: **9.828 ms**
- p95 end-to-end: **10.422 ms**
- receipt chain checked: **20**
- receipt chain valid: **true**

## Test status

The same CI run completed **24 unit tests successfully** before running the benchmark.

## Next benchmark stage

The next stage must make the benchmark harder and less self-defined:

1. replace part of the synthetic retrieval set with held-out repository/chat artifacts;
2. add noisy and contradictory multi-source observations;
3. separate development and test splits before tuning RAG0SHOT weights;
4. add ablations for provenance, reliability, graph, and temporal terms;
5. compare against BM25/lexical and embedding baselines when those adapters are available;
6. keep this synthetic suite as a regression/contract test rather than presenting it as external validation.
