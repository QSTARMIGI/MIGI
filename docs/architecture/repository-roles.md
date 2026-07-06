# MIGI Repository Roles and Source Provenance

This document distinguishes canonical MIGI work from experimental projects and upstream technology sources. The distinction protects attribution, licensing, and contributor clarity.

## Role Classes

| Class | Meaning | Contribution Rule |
|---|---|---|
| **Canonical** | Primary home for MIGI-owned architecture, schemas, documentation, and implementation. | New core work belongs here unless a module earns its own repository. |
| **Satellite** | MIGI-specific project with a focused purpose, such as an IDE, client, or experimental runtime. | Clearly document scope and relationship to MIGI Core. |
| **Experimental** | Prototype or research workspace. | Label it experimental; do not make production or compatibility claims without validation. |
| **Integration / Overlay** | A repo based on or used with upstream software. | Preserve upstream attribution and document only MIGI-owned integration material. |
| **Reference Mirror** | Local copy of an upstream project for study, evaluation, or future integration. | Do not relabel upstream code as MIGI-authored or edit it without preserving license and provenance. |

## Current Portfolio Map

### Canonical

| Repository | Role |
|---|---|
| [`QSTARMIGI/MIGI`](../../) | Canonical MIGI architecture, core documentation, future schemas, authority primitives, and implementation. |

### MIGI Satellites and Experiments

| Repository | Intended Role | Current Documentation Direction |
|---|---|---|
| `QSTARMIGI/Alchemy-IDE` | Workflow authoring, symbolic orchestration, and developer experience. | Document as an experimental MIGI satellite; keep implementation claims evidence-based. |
| `QSTARMIGI/Assistant-migi` | Future assistant client or agent interface. | Empty repository; seed only with a scoped README and backlog until code begins. |
| `QSTARMIGI/MIGI3` | Experimental workspace. | Use an explicit README to establish scope, provenance, and migration rules. |
| `QSTARMIGI/migi-project` | Local-inference integration workspace. | Treat upstream source as third-party; keep MIGI overlays separate and attributed. |
| `QSTARMIGI/desktop` | Candidate desktop interface or shell research. | Treat as a focused UI/runtime integration, not the canonical authority core. |
| `QSTARMIGI/router` | Candidate routing research. | Evaluate as a dependency or adapter; the canonical task-routing policy belongs in MIGI Core. |

### Technology Reference Mirrors

The GitHub portfolio also includes repositories named after major upstream projects and technologies, including examples such as `chromium`, `node`, `react`, `expo`, `jax`, `opencv`, `pydantic-ai`, `surrealdb`, `tauri`, `rollup`, `rolldown`, `elasticsearch`, `cassandra`, `scylladb`, `open-webui`, and others.

These repositories may be useful for study, pinning, experimentation, or downstream integration. They are **not automatically MIGI-authored code**. Their original authorship, licenses, trademarks, release processes, security advisories, and compatibility requirements remain upstream concerns.

## Provenance Requirements

For every repository and deliverable, record one of the following categories:

```text
original_migi
migi_derivative
upstream_mirror
upstream_dependency
external_asset_with_license
simulation_or_generated_output
```

For code, documentation, media, models, and datasets, preserve:

- origin URL or source reference when known;
- applicable license and attribution notices;
- the commit, tag, or version used;
- MIGI-owned modifications;
- distribution restrictions;
- whether the material is original, derivative, or generated.

## Recommended Working Rule

```text
Build new MIGI capability in QSTARMIGI/MIGI.
Use satellite repositories for independently deployable modules.
Use upstream mirrors only as tracked sources or integration targets.
Do not merge unreviewed upstream changes into canonical MIGI code.
```

## Migration Path

A satellite can graduate into a stronger project only after it has:

1. a clear purpose and scope;
2. a license compatible with its contents;
3. a README that distinguishes implemented from planned work;
4. a basic security and contribution policy;
5. a dependency and provenance record;
6. automated validation appropriate to its language and runtime.
