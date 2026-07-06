# ADR-0002: Source Classification Is Mandatory

- **Status:** accepted
- **Date:** 2026-07-05

## Context

MIGI handles raw captures, submitted work, model outputs, simulations, and proposed actions. Treating all content as equivalent would blur evidence, transformation history, and the limits of simulation.

## Decision

All material handled by MIGI must have one primary state classification:

```text
original    — directly captured or submitted source material
observed    — source material parsed, measured, or indexed
derived     — transformed, enhanced, summarized, or generated from source
simulated   — hypothetical model, reconstruction, forecast, or rendering
proposed    — a recommended action not yet authorized
authorized  — an action cleared by an authority path
executed    — an authorized action that has completed
```

A transition between classes should create a MUEF event and, where durable, a MIGIReceipt.

## Consequences

- User interfaces must label derived and simulated material visibly.
- Original content must not be overwritten by derivative content.
- Simulated output cannot be represented as verified physical reality.
- Sharing, licensing, retention, and auditing rules can vary by classification.

## Alternatives Considered

1. Use a generic `content_type` tag only. Rejected because it does not express provenance state.
2. Treat AI output as equivalent to source data. Rejected because it removes transformation boundaries.
3. Track only original and generated. Rejected because simulations and proposed actions need separate authority semantics.

## Review Notes

Review when introducing new media types, sensor sources, model classes, or external data providers.