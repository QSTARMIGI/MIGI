<!-- MIGI Pull Request Template -->

## 🚀 Summary
- **What** does this PR change?
- **Why** is this important? Closes #Issue

## 🎯 Type of Change
- [ ] Feature (`feature/...`)
- [ ] Bugfix (`bugfix/...`)
- [ ] Docs (`docs/...`)
- [ ] Refactor (`refactor/...`)

## ✅ Checklist
- [ ] Self-reviewed
- [ ] Tests pass locally
- [ ] CI is passing
- [ ] Documentation updated

## 🔍 Testing Instructions
Explain how to test, e.g.:
```bash
docker-compose up
pytest
yarn test
---

## 🧩 Step 3: Branching Strategy Documentation

Add `CONTRIBUTING.md`:
```md
# MIGI Branching Strategy

## Core Branches
- `main` – production
- `develop` – feature integration

## Supporting Branches
| Type     | Format              | Base     | Merge Into           |
|---------|---------------------|-----------|----------------------|
| Feature | feature/<id>-desc   | develop   | develop              |
| Bugfix  | bugfix/<id>-desc    | develop   | develop              |
| Hotfix  | hotfix/<id>-desc    | main      | main & develop       |
| Release | release/vX.Y        | develop   | main & develop       |
| Docs    | docs/<desc>         | develop   | develop              |

## Workflow
- PRs to `develop`, reviewed via template
- Create `release/` from `develop`, finalize, merge into `main`
- Tag `main` after merge
- Hotfix via `main`, merge back into `develop`