# ADR-0001: Authority and Provenance Precede Consequential Execution

- **Status:** accepted
- **Date:** 2026-07-05

## Context

MIGI connects user input, AI analysis, simulations, external services, and potentially physical systems. Without an explicit boundary, a helpful model response can be confused with an authorized decision or a completed action.

## Decision

Every durable or consequential transition must follow this order:

```text
Intent or observation
  ↓
Authority evaluation
  ↓
Approved execution path
  ↓
Receipt-linked event
```

The system uses:

- **LUFITGuard** for consent, scope, risk, budget, and tool policy;
- **Tre Logic** for explainable `+1`, `0`, or `-1` outcomes;
- **MIGIReceipt** and **ChainLog** for durable provenance.

Models may analyze, recommend, or propose. They do not independently authorize consequential action.

## Consequences

- Policy checks remain separate from inference.
- External actions need a clear human or policy authority path.
- Failed, held, and denied actions are recorded with reasons where appropriate.
- A user interface must show whether material is observed, derived, simulated, proposed, authorized, or executed.

## Alternatives Considered

1. Let the model decide and execute directly. Rejected because it obscures accountability and can create unsafe or unauthorized actions.
2. Record only final outputs. Rejected because it loses lineage and makes audit or replay difficult.
3. Require manual approval for every operation. Rejected because low-risk, explicitly scoped local operations can be safely automated.

## Review Notes

Review this decision before adding payment, production-machine, or high-impact external-action adapters.