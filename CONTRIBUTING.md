# Contributing to MIGI

Thank you for contributing to MIGI.

## Project Principles

Contributions should preserve the architecture’s core boundaries:

1. **Original is truth.** Preserve source data and provenance.
2. **Enhancement is derivative.** Clearly label transformed or generated outputs.
3. **Simulation is not reality.** Do not present predictions as verified observations.
4. **Action requires permission.** Consequential actions need an explicit authority path.
5. **Human review remains available.** Automation must provide an understandable escalation path.

## Before You Start

- Search existing issues and documentation before beginning a large change.
- Keep changes scoped to one concern: schema, policy, receipt, adapter, interface, or documentation.
- Do not add credentials, private keys, personal data, model weights without distribution rights, or proprietary third-party material.
- Preserve required third-party attribution and license notices.

## Preferred Contribution Flow

```text
Issue or documented problem
  ↓
Small branch
  ↓
Focused implementation or documentation change
  ↓
Tests / validation where applicable
  ↓
Pull request with provenance and risk notes
```

## Pull Request Expectations

A pull request should state:

- the user or system problem it solves;
- affected module(s);
- whether input is original, derived, or simulated;
- authority and permission implications;
- data-handling implications;
- test or manual verification performed;
- rollback or recovery considerations for consequential changes.

## Code and Schema Guidance

- Prefer typed, versioned event schemas.
- Add receipts at durable state transitions.
- Treat `+1`, `0`, and `-1` authority states as explainable outcomes, not opaque scores.
- Keep policy evaluation separate from model inference.
- Keep hardware or irreversible actions behind deterministic safeguards and human authorization.
- Use clear names and small, composable modules.

## Documentation Guidance

Use documentation to distinguish:

```text
implemented
prototype
planned
research
third-party dependency or mirror
```

Do not claim production readiness, security certification, regulatory approval, ownership, or performance results unless the repository contains evidence for that claim.

## License

By contributing, you agree that your contribution is licensed under the repository’s Apache License 2.0 terms unless a separate written agreement states otherwise.
