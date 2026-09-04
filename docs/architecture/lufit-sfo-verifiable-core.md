# MIGI-CS-002 — LUFIT + SFO Verifiable Claim Core

This milestone turns the current MIGI epistemic architecture into executable Rust rules.

## Scope

MIGI-CS-002 adds a small vertical slice around five invariants:

1. **SFO contract** — state transitions expose an explicit observation record.
2. **Evidence is not truth** — evidence is weighted by confidence, reliability, provenance quality, and direction.
3. **LUFIT profile boundary** — a claim is qualified only when declared resolution, budget, observables, methods, and cutoff are sufficient.
4. **Simulation is not observation** — a `simulated` source can produce a simulation result but cannot silently become a factual observation.
5. **Inference is not authority** — an executed MIGIReceipt may only be issued with Tre Logic `+1` / `Proceed` authority.

## Tre evidence assessment

Evidence direction is normalized to `[-1, 1]`:

- `-1` contradicts
- `0` is neutral / unresolved
- `+1` supports

Each evidence item receives weight:

```text
w = confidence × reliability × provenance_quality
```

The evaluator converts the weighted evidence into probability mass:

```text
[contradicted, unresolved, supported]
```

The net support score is:

```text
supported_probability - contradicted_probability
```

and the configured threshold maps that score to `+1 / 0 / -1` evidence state.

Uncertainty is normalized Shannon entropy over the three-way distribution.

## LUFIT profile

The v0 executable profile is:

```text
π = (resolution_level, budget_units, observables, methods, cutoff)
```

A claim requirement is `OUT_OF_PROFILE` when any required resolution, budget, observable, method, or regime value exceeds the declared profile.

## RAG0SHOT evidence-aware score

MIGI-CS-002 introduces the first explicit weighted score:

```text
score =
    0.40 × semantic
  + 0.20 × provenance
  + 0.15 × reliability
  + 0.15 × graph
  + 0.10 × temporal
```

All inputs are normalized to `[0, 1]`. This is a benchmarkable baseline, not a claim that these weights are optimal.

## Vertical slice

The integration test exercises:

```text
Observation
  → SFO record
  → evidence assessment
  → LUFIT profile validation
  → qualified claim
  → authorized MIGIReceipt
  → ChainLog append
  → ChainLog verification
```

It also tests the two prohibited transitions:

```text
Simulation → factual observation      (blocked)
Hold/Deny → executed receipt           (blocked)
```

## Next benchmark

After this core passes CI, generate a fixed synthetic evidence corpus and compare:

- semantic-only retrieval
- provenance-aware RAG0SHOT scoring
- calibrated claim accuracy
- Brier/calibration error
- bad-source retrieval rate
- out-of-profile refusal rate

MCFP / FieldWord64 and Hex64³ should be added after the epistemic core is stable, so compression work does not obscure correctness failures in claim qualification.
