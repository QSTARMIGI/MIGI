# MIGI-CS-002 — LUFIT + SFO Verifiable Claim Core

MIGI-CS-002 turns the LUFIT/SFO theory into executable computer-science rules on top of the current Python Genesis Node.

## Core contract

```text
State → Flow → Observation
                  ↓
              Evidence
                  ↓
         Tre evidence state
                  ↓
          LUFIT profile check
                  ↓
          Qualified claim
                  ↓
        Derived MIGIReceipt
                  ↓
              Memory
                  ↓
               Recall
```

The runtime composes with the existing `GenesisStore` and `LUFITGuard`; it does not create a second database or authority system.

## SFO

An SFO record contains:

- `state_before`
- `state_after`
- an explicit observation

The observation preserves its source class (`observed`, `derived`, `simulated`, etc.), confidence, source identifier, and optional provenance reference.

## Evidence / Tre state

Each evidence item uses:

```text
direction ∈ [-1, 1]
confidence ∈ [0, 1]
reliability ∈ [0, 1]
provenance_quality ∈ [0, 1]
```

Weight:

```text
w = confidence × reliability × provenance_quality
```

Weighted mass is normalized into:

```text
[contradicted, unresolved, supported]
```

Net support:

```text
support_score = P(supported) - P(contradicted)
```

The default threshold is `0.60`, mapped to the three-value evidence state:

```text
+1 supported
 0 unresolved
-1 contradicted
```

Uncertainty is normalized Shannon entropy over the three-way distribution.

## LUFIT executable profile

The v0 profile is:

```text
π = (resolution_level, budget_units, observables, methods, cutoff)
```

A claim becomes `out_of_profile` when its requirements exceed any declared bound.

This makes `OUT_OF_PROFILE` a first-class result rather than forcing the system to invent an answer.

## Simulation boundary

A source classified as `simulated` can never silently become a factual `supported` observation through this runtime.

Even if the simulated result has strong evidence weights, its factual qualification is:

```text
simulation_only
```

A later real observation can be compared against that prediction in a separate SFO cycle.

## Authority boundary

Claim qualification uses a distinct action and consent scope:

```text
action: claim.qualify
scope:  local.reason | private.local.reason
```

No reasoning execution occurs when the scope is absent. A blocked attempt receives a `proposed` receipt and no execution record.

This preserves the architecture rule:

```text
Inference != Authority
```

## RAG0SHOT scoring baseline

MIGI-CS-002 defines an evidence-aware retrieval score:

```text
score =
    0.40 × semantic
  + 0.20 × provenance
  + 0.15 × reliability
  + 0.15 × graph
  + 0.10 × temporal
```

The weights are a benchmarkable starting point, not an assertion that they are optimal.

## Current tests

The automated suite proves:

1. no evidence returns unresolved;
2. a supported observed claim produces a derived receipt and can be recalled;
3. simulation remains `simulation_only`;
4. an out-of-profile claim is explicitly labeled;
5. missing reasoning authority produces Hold (`0`) and no execution;
6. provenance-aware RAG0SHOT ranking can prefer a trustworthy result over a superficially more similar result.

## Next benchmark

The next milestone should generate a fixed synthetic corpus (target: 1,000 claims) and compare:

- semantic-only retrieval vs evidence-aware RAG0SHOT;
- precision / recall / MRR;
- Brier score and calibration error;
- bad-source retrieval rate;
- out-of-profile refusal accuracy;
- latency and receipt overhead.

MCFP / FieldWord64 and Hex64³ should follow after this epistemic core is benchmarked, so compression gains do not mask correctness problems.
