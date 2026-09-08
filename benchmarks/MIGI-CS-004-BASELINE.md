# MIGI-CS-004 Repository-Grounded Baseline

**Recorded:** 2026-09-08  
**CI run:** `34262846187`  
**Corpus SHA-256:** `e001f9211fcc507fdb8a1c8379e23fa29817bfb81f7ac0cc2bf188ba3498fa68`

## Scope

MIGI-CS-004 evaluates the already-fixed RAG0SHOT weighting and Tre evidence aggregation on the current MIGI repository rather than on a corpus designed around the formula.

The corpus contains:

- 25 current source/document artifacts read directly from the checkout;
- 21 manually labeled retrieval queries;
- 20 file-content predicates for evidence tests;
- the existing RAG0SHOT weights, unchanged from before this corpus;
- graph relevance derived from actual Python imports;
- a neutral temporal signal because the shallow CI checkout does not provide a stable per-file timestamp source.

This is an **internal repository-grounded benchmark**, not external real-world validation.

## Retrieval results

| Variant | Precision@1 | Recall@3 | MRR |
|---|---:|---:|---:|
| Semantic only | 0.7619 | **1.0000** | 0.8810 |
| Full RAG0SHOT | **0.8095** | 0.9524 | **0.8929** |
| Without provenance | 0.8095 | 0.9524 | 0.8929 |
| Without reliability | 0.8095 | 0.9524 | 0.8929 |
| Without graph | 0.7619 | **1.0000** | 0.8810 |
| Without temporal | 0.8095 | 0.9524 | 0.8929 |

### What this says

On this corpus, the full score improved top-1 accuracy by about **4.76 percentage points** and MRR by about **0.0119** relative to semantic-only retrieval. It also reduced Recall@3 by about **4.76 percentage points**, meaning one relevant target was pushed below rank 3.

The ablation is more important than the headline score:

- **Graph relevance produced the observed ranking change.** Removing graph returns the metrics exactly to the semantic-only baseline.
- **Provenance produced no measurable ranking change on this corpus.** This does not show provenance is useless; it shows the current candidate set does not discriminate enough on that signal.
- **Reliability produced no measurable ranking change on this corpus.** The same caution applies.
- **Temporal produced no measurable ranking change by construction** because temporal relevance is neutral in this CI environment.

Therefore the current evidence supports keeping the graph term under further study, while provenance/reliability need a corpus containing meaningful source-quality variation before their retrieval weights can be justified empirically.

## Noisy evidence results

The direct observation is derived from an actual repository predicate. Contradictory noise has lower confidence, reliability, and provenance quality.

| Contradictory noise items | Correct polarity | Unresolved | Wrong polarity | Mean uncertainty |
|---:|---:|---:|---:|---:|
| 0 | 1.000 | 0.000 | 0.000 | 0.0726 |
| 2 | 1.000 | 0.000 | 0.000 | 0.2581 |
| 4 | 1.000 | 0.000 | 0.000 | 0.3871 |
| 8 | 0.000 | 1.000 | 0.000 | 0.5246 |

Equal-strength direct contradictions became `unresolved` at a rate of **1.000**.

This is the desired safety shape for Tre evidence aggregation in this controlled test:

1. uncertainty rises as contradictory evidence accumulates;
2. the correct polarity is retained under moderate low-quality noise;
3. sufficiently heavy contradiction causes `0 / unresolved` before the system flips to the wrong polarity;
4. wrong-polarity rate remained zero in these cases.

## Test status

The quality gate ran **30 tests** and passed.

## Next experiment

MIGI-CS-005 should focus specifically on the terms that did not earn measurable value here:

1. build source-quality cases using version drift, stale documentation, contradictory logs, and current executable code;
2. evaluate provenance and reliability independently rather than assigning both mostly by path class;
3. add a real time/revision signal from Git history instead of a neutral temporal constant;
4. inspect the one query where graph propagation hurt Recall@3;
5. compare fixed weights against a development-set-tuned model while keeping a separate test split untouched.

The goal is not to make every RAG0SHOT term look useful. The goal is to remove or redesign terms that do not demonstrate value.
