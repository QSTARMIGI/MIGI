# MIGI Project Registry

**Audit date:** 2026-10-13  
**Registry version:** 0.1.0-draft  
**Canonical repository:** [QSTARMIGI/MIGI](https://github.com/QSTARMIGI/MIGI)  
**Default branch:** `main`  
**Audit status:** Initial evidence-based snapshot; not yet a complete portfolio audit.

## Purpose

This registry separates verified repository facts from intended architecture, experiments, and unverified assumptions. A project name in a conversation or roadmap is not proof that working code exists. A repository under the account is not, by itself, proof that its contents are original MIGI work.

## Status vocabulary

- **Verified repository** — repository metadata or files were inspected directly.
- **Implementation evidence** — code, tests, commits, or a pull request were inspected; this does not imply production readiness.
- **Planned** — documented intent without verified implementation in the inspected source.
- **Needs audit** — ownership, provenance, status, dependencies, or integration has not yet been established.
- **Blocked / unknown** — evidence is missing or a check could not be completed.

## Canonical core

| Field | Current finding |
|---|---|
| Repository | `QSTARMIGI/MIGI` |
| Visibility | Public |
| Default branch | `main` |
| Account permission | Admin/push access confirmed by connected GitHub integration |
| Project phase | Architecture and MVP implementation |
| Python package metadata | `migi-core`, version `0.1.0`, Python `>=3.11` |
| README-described executable core | Genesis Node v0.1 |
| Product path in README | MIRROR SEED: trusted capture, local provenance, approved analysis, human approval, and replayable receipt trail |
| Rust workspace at repository root | Not found at `Cargo.toml` during this audit; do not assume a Rust workspace is present at root |
| `MIGI_CANON.md` / `CHANGELOG.md` at repository root | Not found during this audit; canonical positioning exists in project context, but these exact root files are not verified |
| Automated CI workflow | `.github/workflows/quality-gate.yml` exists; runs required-file checks, JSON schema parsing, unit tests, and CS-002/CS-004 benchmark scripts |
| Release tags and branch protection | Not yet audited |
| Dependency lockfile / reproducible install | `pyproject.toml` defines Python >=3.11 and optional API dependencies; no lockfile was confirmed in this pass. Local test reproduction is blocked because the audit runtime cannot resolve github.com; CI evidence is available for the two open PR heads below. |

## Known development branches

The GitHub branch search returned these branches at audit time:

- `main`
- `docs/version-control-audit-v1` (audit documentation branch; PR #16)
- `feat/genesis-cambus-replay`
- `feat/genesis-code-recall-api`
- `feat/migi-cs-001-verifiable-signal-loop`
- `feat/migi-cs-002-lufit-sfo-core`
- `feat/migi-cs-002-lufit-sfo-python`
- `feat/migi-cs-003-benchmark`
- `feat/migi-cs-004-real-validation`
- `feat/mirror-seed-capture-export`
- `feat/rag0shot-code-memory-v0.2`
- `genesis-node-v0.1`

A branch existing does not mean its changes are merged or current. Compare each branch with `main` before treating it as active work.

## Pull-request evidence

Current PR metadata was fetched directly from GitHub on 2026-10-13.

| PR | Scope | Verified state |
|---|---|---|
| [#7](https://github.com/QSTARMIGI/MIGI/pull/7) | MIGI-CS-001 verifiable core + RAG0SHOT | Closed, **not merged**; 2,019 additions across 18 files. Treat as superseded/archival candidate, but reconcile its unique changes before archiving. |
| [#8](https://github.com/QSTARMIGI/MIGI/pull/8) | Genesis Node v0.1 | Merged 2026-08-29 |
| [#9](https://github.com/QSTARMIGI/MIGI/pull/9) | Genesis CAMbus and deterministic replay | Merged 2026-08-30 |
| [#10](https://github.com/QSTARMIGI/MIGI/pull/10) | RAG0SHOT code memory v0.2 | Merged 2026-08-30 |
| [#11](https://github.com/QSTARMIGI/MIGI/pull/11) | Genesis code-recall API | Merged 2026-08-30 |
| [#12](https://github.com/QSTARMIGI/MIGI/pull/12) | LUFIT + SFO verifiable claim core | Merged 2026-09-07 |
| [#13](https://github.com/QSTARMIGI/MIGI/pull/13) | 1,000-case synthetic benchmark | Merged 2026-09-08 |
| [#14](https://github.com/QSTARMIGI/MIGI/pull/14) | Repository-grounded retrieval and noisy-evidence validation | Merged 2026-09-08 |
| [#15](https://github.com/QSTARMIGI/MIGI/pull/15) | MIRROR SEED MS-001 offline capture, authorized analysis, portable export | Open draft; 792 additions, 11 deletions, 9 files. Quality Gate reported success for head `f1140ae55aeef14062ea5c2b171a86162adb3487`; not merged or released. |
| [#16](https://github.com/QSTARMIGI/MIGI/pull/16) | Project registry and version-control policy | Open draft; 235 additions, 0 deletions, 2 files. Quality Gate reported success for head `e569c6c575acc13d79a8ce49bc661d0ddb855357`; not merged. |

### CI interpretation

The workflow at `.github/workflows/quality-gate.yml` checks required repository files, parses two JSON schemas, runs the Python unittest suite with ResourceWarnings treated as errors, and runs the CS-002 and CS-004 benchmark scripts. GitHub Actions reported the workflow conclusion as `success` for the exact head commits of PR #15 and PR #16 when checked on 2026-10-13. This is CI evidence, not a local rerun by this audit. The local audit environment could not reach github.com, so local reproduction remains outstanding.

PR descriptions and test claims are not substitutes for inspecting the code or acceptance boundaries. PR #15's own design documentation explicitly says the prototype's receipts are unsigned, scope strings are local consent choices rather than authentication, and native phone capture/UI/device-backed signing remain pending. Do not describe MS-001 as a shipped phone app or cryptographically authenticated capture.

## Account repository inventory snapshot

The connected GitHub account returned 50 repositories in the first inventory page and no second page. This is an account-level snapshot, not a claim that all 50 are MIGI products.

| Repository | Observed default branch | Preliminary handling |
|---|---|---|
| `QSTARMIGI/MIGI` | `main` | Canonical MIGI core |
| `QSTARMIGI/Assistant-migi` | `main` | Candidate assistant satellite; repository reported size 0; inspect before use |
| `QSTARMIGI/Xcode-project` | `main` | Private; reported size 0; inspect before use |
| `QSTARMIGI/maestro` | `main` | Provenance and purpose need audit |
| `QSTARMIGI/WirelessThings-Firmware-Uploader` | `master` | Provenance and purpose need audit |
| `QSTARMIGI/fw-mockingbird-telephone-exchange-master-controller` | `main` | Provenance and purpose need audit |
| `QSTARMIGI/xyzeva` | `main` | Reported size 2; purpose needs audit |
| `QSTARMIGI/Orbital` | `main` | Provenance and purpose need audit |
| `QSTARMIGI/jstack` | `main` | Provenance and purpose need audit |
| `QSTARMIGI/helix` | `master` | Provenance and purpose need audit |
| `QSTARMIGI/web-ai` | `main` | Provenance and purpose need audit |
| `QSTARMIGI/flame` | `main` | Provenance and purpose need audit |
| `QSTARMIGI/purple-ai` | `main` | Provenance and purpose need audit |
| `QSTARMIGI/HVM` | `main` | Provenance and purpose need audit |
| `QSTARMIGI/hydra` | `main` | Candidate Hydra-related repo; upstream/fork status must be checked |
| `QSTARMIGI/web-ui` | `main` | Provenance and purpose need audit |
| `QSTARMIGI/.github` | `main` | Account-level GitHub configuration; inspect separately |
| `QSTARMIGI/swarm` | `main` | Provenance and purpose need audit |
| `QSTARMIGI/tauri` | `dev` | Likely technology-name overlap; verify fork/upstream relationship before treating as original |
| `QSTARMIGI/valibot` | `main` | Provenance and purpose need audit |
| `QSTARMIGI/PurpleLlama` | `main` | Provenance and purpose need audit |
| `QSTARMIGI/pytorch-lightning` | `master` | Verify upstream/fork status and license |
| `QSTARMIGI/puter` | `main` | Verify upstream/fork status and license |
| `QSTARMIGI/shadcn-svelte` | `main` | Verify upstream/fork status and license |
| `QSTARMIGI/Bend` | `main` | Verify upstream/fork status and license |
| `QSTARMIGI/manim` | `master` | Verify upstream/fork status and license |
| `QSTARMIGI/tldraw` | `main` | Verify upstream/fork status and license |
| `QSTARMIGI/drei` | `master` | Verify upstream/fork status and license |
| `QSTARMIGI/three-stdlib` | `main` | Verify upstream/fork status and license |
| `QSTARMIGI/ipfs` | `master` | Verify upstream/fork status and license |
| `QSTARMIGI/router` | `main` | Candidate routing integration; purpose and provenance need audit |
| `QSTARMIGI/awesome-crawler` | `master` | Provenance and purpose need audit |
| Other repositories in the account snapshot | See GitHub account | Maintain as unclassified until README, remotes, license, recent commits, and intended use are checked |

The snapshot also included `CyberCodeOnline`, `DreamBerd`, `ladybird`, `standard-schema`, `fabric`, `e18e`, `pydantic-ai`, `ZeroSync`, `angular`, `posthog`, `cassandra`, `scylladb`, `elasticsearch`, `crawl4ai`, `uploadthing`, `lazygit`, `theia`, `react`, and other technology-name repositories. They remain **unclassified** until origin, licensing, modifications, and intended use are checked. Do not assume they are MIGI-authored implementations.

## Architecture-to-repository mapping

| Initiative | Current classification | Evidence required to promote status |
|---|---|---|
| MIGI / Genesis Node | Implementation evidence exists in canonical repo | Reproducible tests on current main; release artifact |
| MIRROR SEED MS-001 | Draft implementation proposed in PR #15 | Review, CI, explicit merge, tagged release |
| Android / Pixel capture client | Planned in roadmap | Actual app source, build workflow, on-device acceptance run |
| iOS / Xcode client | Unverified candidate | Non-empty project, reproducible build, permission and storage tests |
| HydraOS / HydraFS | Architectural initiative; candidate account repo needs provenance audit | Identify canonical source, ownership, scope, tests, and interface contract |
| Leviathan Kernel / SoC | Research/design unless separate implementation evidence is found | Repository and hardware/simulation artifacts with reproducible tests |
| Tre Logic / Emoji A++ | Concepts and/or modules must be mapped to concrete source paths | Identify maintained implementation, language targets, tests, and version |
| Alchemy IDE / XR / Strawberry / Q★ | Planned or experimental until repository evidence is linked | Explicit repository mapping, license/provenance, milestone acceptance tests |
| HBC / creator economy | Separate token/business specification; not assumed to be implemented in MIGI core | Contract repository, audit/tests, legal and economic review |
| Hex64³ / LUFIT spatial-compression research | Research hypothesis, not established scientific result | Reproducible experiment repository, baselines, metrics, and falsification results |

## Immediate audit backlog

- [x] Verify PR #7–#16 merge/open states; feature-branch content diffs against `main` still need a complete reconciliation.
- [x] Inspect the README, Python package metadata, quality-gate workflow, PR file lists, and selected implementation/spec files; full repository tree review remains open.
- [ ] Reproduce tests locally on a pinned commit; CI passed for PR #15 and #16 heads, but local reproduction was blocked by unavailable network access.
- [ ] Inspect release tags, version bump rules, branch protection, and required checks.
- [ ] Audit lockfiles and produce a reproducible install/test recipe.
- [ ] Classify all account repositories as original, fork, mirror, experiment, archive, or unrelated.
- [ ] Reconcile this registry with `docs/architecture/repository-roles.md`; remove stale repo names and unsupported claims.
- [ ] Add per-project ownership, status, upstream URL, license, last verified commit, and acceptance criteria.
- [ ] Add release notes and a lightweight dependency/security check.

## Update rule

Update this file in the same pull request that materially changes project boundaries, canonical ownership, release status, or integration status. Cite commit hashes, PRs, tests, or build artifacts for implementation claims. Use **planned**, **experimental**, and **verified** labels precisely.
