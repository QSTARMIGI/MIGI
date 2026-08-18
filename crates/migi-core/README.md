# MIGI Core — MIGI-CS-001

First executable foundation for the Verifiable Signal Loop.

## Current primitives

- `MuefEvent` — typed MIGI Unified Event Framework event.
- `Authority` / `TreLogic` — `+1`, `0`, `-1` decision model.
- `MigiReceipt` — provenance record linking an event, input hash, output hash, authority decision, and previous receipt.
- `validate_event` — minimal v0 MUEF validation.
- `sha256_json` — deterministic JSON hashing helper.

## Lifecycle

```text
MUEF event → authority → execution → observation → MIGIReceipt
```

MIGI-CS-001 intentionally keeps transport and persistence out of this crate. Those will be added as separate layers so CAMbus/BEAM/ChainLog remain independently testable.

## Status

Experimental v0.1. The implementation follows the existing repository schemas; it is not yet a complete security boundary or distributed runtime.
