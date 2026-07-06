# ADR-0003: Canonical Core and Satellite Repository Boundaries

- **Status:** accepted
- **Date:** 2026-07-05

## Context

The QSTARMIGI portfolio includes canonical MIGI work, experiments, client concepts, integrations, and upstream reference mirrors. Without boundaries, changes can fragment the architecture, duplicate authority logic, or misrepresent third-party source as MIGI-owned code.

## Decision

- `QSTARMIGI/MIGI` is the canonical home for shared architecture, MUEF schemas, authority primitives, receipt contracts, contribution rules, and MVP backlog.
- Satellite repositories contain independently scoped clients, tools, prototypes, or deployable modules.
- Integration overlays isolate MIGI-specific changes around external software.
- Reference mirrors preserve upstream provenance and are not treated as canonical MIGI implementation.

## Consequences

- Shared policy, receipt, and event behavior is defined in one place.
- Experiments must document their migration criteria before entering MIGI Core.
- Upstream licensing and attribution remain visible.
- Contributors can determine where a feature belongs before opening a pull request.

## Alternatives Considered

1. Put all projects in one repository. Rejected because large upstream codebases and independently deployable tools would overwhelm the core.
2. Treat every repository as an equal product. Rejected because it makes ownership, readiness, and architecture unclear.
3. Fork and relabel upstream software as MIGI. Rejected because it damages provenance and license clarity.

## Review Notes

Review this ADR when extracting a stable new module from MIGI Core or retiring an experimental repository.