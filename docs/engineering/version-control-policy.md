# Version Control and Release Policy

**Status:** Proposed policy  
**Applies to:** MIGI core and any satellite repository explicitly adopted into the MIGI project portfolio.

## 1. Source of truth

- `main` is the canonical integration branch for the MIGI core repository.
- Work happens on short-lived feature or fix branches and enters `main` through a pull request.
- Never infer merge/release status from a branch name, a conversation summary, or a passing test mentioned in a PR body.
- A satellite repository is not canonical until the project registry names it and defines its owner, scope, provenance, and interface.

## 2. Version semantics

Use Semantic Versioning (`MAJOR.MINOR.PATCH`) for published software releases:

- **MAJOR** — incompatible public API/schema or persisted-data changes.
- **MINOR** — backward-compatible capability additions.
- **PATCH** — backward-compatible fixes and documentation corrections.

Before the first stable 1.0 release, use explicit `0.y.z` versions and document that public interfaces may change. Keep package version, release tag, and release notes synchronized. Do not call an untagged commit a release.

## 3. Commit and branch conventions

Suggested branch names:

- `feat/<short-scope>`
- `fix/<short-scope>`
- `docs/<short-scope>`
- `test/<short-scope>`
- `chore/<short-scope>`

Commit messages should state the change and scope, for example:

- `feat(receipts): validate parent lineage`
- `fix(chainlog): reject stale chain heads`
- `docs(registry): reconcile project status`

Keep commits reviewable. Do not include credentials, private user data, device captures, signing keys, generated secrets, or unrelated vendor trees.

## 4. Pull-request acceptance checklist

Before merge, a reviewer should confirm:

- [ ] The change has a single clear purpose and links to an issue or milestone where useful.
- [ ] Tests cover changed behavior and relevant failure cases.
- [ ] Tests are run on the exact candidate commit; results are not inferred from another branch.
- [ ] Formatting, static checks, and `git diff --check` pass where configured.
- [ ] Schemas, APIs, dependencies, documentation, and migration notes are updated as needed.
- [ ] No secrets, personal data, unauthorized media, or unlicensed copied content are included.
- [ ] Security, privacy, consent, and data-retention implications are considered.
- [ ] Breaking changes and rollback steps are stated.
- [ ] A reviewer explicitly approves the PR; automation does not replace review.

For the early solo-maintainer phase, the maintainer may self-review, but must still record the checklist and test evidence. Do not merge solely because a PR exists.

## 5. Reproducibility and dependency control

- Pin runtime/toolchain versions for release builds.
- Commit the package-manager lockfile for each supported package manager.
- Document one clean install and one test command.
- Prefer bounded direct dependencies and update them deliberately.
- Record OS, language/runtime versions, commit SHA, test command, and outcome for release validation.
- Do not claim deterministic or reproducible builds until repeated clean runs verify the claim.

## 6. Release checklist

- [ ] Candidate commit is on `main` and its CI checks pass.
- [ ] Tests were rerun or verified against that exact commit.
- [ ] Version and changelog are updated.
- [ ] Security and dependency checks have no untriaged release-blocking finding.
- [ ] Public interfaces and known limitations are documented.
- [ ] Tag is created only after acceptance; release notes link to the tag and commit.
- [ ] A rollback/recovery path is recorded for changes that affect stored data.
- [ ] Project registry is updated if milestone or integration status changed.

## 7. Integrity and provenance claims

MIGI's product principle is that originals, derivatives, simulations, and proposals must remain distinguishable. Apply the same discipline to software:

- A hash proves byte equality relative to the bytes hashed; it does not prove authorship or truth.
- A signed commit/release can establish a key-associated signature, not that the code is safe or scientifically correct.
- Test success establishes only the tested behavior, environment, and revision.
- A PR description is a claim until independently verified.
- Never describe a prototype as production-ready without a defined deployment and acceptance test.

## 8. Security and recovery

- Keep secrets out of Git history; rotate exposed credentials and follow repository-specific remediation.
- Use least-privilege tokens and require protected-branch checks when available.
- Maintain a second recovery copy for important canonical work; a remote repository alone is not a complete backup strategy.
- Treat deletion, history rewriting, force-push, release replacement, and changes to signing policy as high-risk operations requiring explicit review.
