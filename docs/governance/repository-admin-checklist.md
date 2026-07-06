# Repository Administration Checklist

This checklist records GitHub settings that cannot be enforced solely by repository files.

## Main Branch Protection

Apply to `main` in `QSTARMIGI/MIGI` when the first implementation work begins:

- [ ] Require pull requests before merging.
- [ ] Require at least one approving review, including the repository owner while solo-maintained.
- [ ] Require the `MIGI Quality Gate` status check.
- [ ] Require branches to be up to date before merging when collaboration increases.
- [ ] Block force pushes.
- [ ] Block branch deletion.
- [ ] Restrict bypass permissions to the owner or designated maintainers.

## Repository Security Settings

- [ ] Enable secret scanning and push protection where available.
- [ ] Enable Dependabot alerts and security updates where available.
- [ ] Enable private vulnerability reporting if the repository’s public collaboration model needs it.
- [ ] Review Actions permissions; keep default workflow token permissions read-only unless a workflow needs a narrow write scope.
- [ ] Review deploy keys, OAuth applications, GitHub Apps, and personal access tokens quarterly.

## Release and Provenance

- [ ] Use signed or otherwise verifiable release tags once code is shipped.
- [ ] Attach a changelog and compatibility notes to releases.
- [ ] Record upstream dependency versions in `provenance/dependencies.yaml`.
- [ ] Keep generated assets, model artifacts, and sensitive capture data out of the repository unless distribution rights and retention rules are explicit.

## Issue and Project Management

- [ ] Create labels: `core`, `mobile`, `authority`, `receipt`, `chainlog`, `muef`, `lufitguard`, `tre-logic`, `mirror-seed`, `security`, `documentation`, `research`, `upstream-mirror`, `blocked`.
- [ ] Create a MIRROR SEED project board with columns: `Backlog`, `Ready`, `In progress`, `Validation`, `Done`.
- [ ] Tie each implementation issue to a milestone and acceptance criteria.
- [ ] Use the organization pull-request template for all core changes.

## Cadence

- Weekly: review open issues, dependency changes, and blocked work.
- Monthly: review secrets, integrations, permissions, and the provenance registry.
- Before a public release: run full tests, documentation checks, license review, and a receipt/provenance audit.
