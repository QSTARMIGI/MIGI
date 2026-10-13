# Mirrorfield v0.1 — Observation, State, Reflection

**Status:** Prototype specification  
**Scope:** Data contracts and deterministic utilities; no live camera/microphone capture, model inference, or physical-field claim.

## Purpose

Mirrorfield coordinates visual, audio, spatial, and event observations into a shared, traceable state. It keeps source observations separate from derived interpretations.

## Modules

- `migi/mirrorfield/schema.py`: versioned observation metadata and source classification.
- `migi/mirrorfield/sensors.py`: timestamp comparison with explicit clock-domain checks.
- `migi/mirrorfield/state.py`: deterministic ordering of observation references.
- `migi/mirrorfield/reflect.py`: observed-versus-predicted numeric feature residuals.
- `migi/mirrorfield/receipts.py`: deterministic SHA-256 integrity record.

## Invariants

1. **Observation is not interpretation.** Derived outputs refer back to their input observation IDs.
2. **Simulation is not reality.** Simulated records carry `source_class=simulated`.
3. **Prediction is not fact.** Residuals measure disagreement; they do not establish the cause.
4. **Time domains matter.** Timestamps from different clock IDs are not directly comparable.
5. **Hashes are not signatures.** A SHA-256 receipt hash detects changed content but does not authenticate a device or prove that an observation is true.
6. **Authority remains separate.** This package does not authorize actions. Integrate with MIGI's existing authority layer before any consequential action.

## Receipt format

Receipts include schema version, event ID, source class, input references, output reference, creation timestamp, previous hash, and record hash. The record hash is computed over deterministic JSON using the repository's existing `migi.canonical` helper. The current canonicalizer rejects floats and is explicitly not a full RFC 8785 implementation.

## Next experiment

Use synthetic scenes with known ground truth. Compare independent audio/video processing against a timestamp-aligned fusion baseline under controlled clock offsets, missing frames, noise, and moving sources. Report event accuracy, localization error, temporal alignment error, memory, latency, and resource cost. Preregister metrics and test on held-out scenarios.

## Run tests

```bash
python -m unittest tests.test_mirrorfield_v0 -v
```
