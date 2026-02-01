# Contributing to FamilyEye

Thank you for wanting to help improve FamilyEye. Every bug fix or idea counts.

## How to Contribute

1. **Fork** – Make a copy of the project under your account.
2. **Branch** – Create a branch (e.g. `feature/your-feature`) and make your changes.
3. **Pull Request** – When done, open a PR against the target branch.

### Technical minimum

- **Backend:** Python 3.11, run with `python run_https.py` from `backend/` (inside a virtual environment).
- **Frontend:** Node.js 18+, run with `npm run dev` from `frontend/`.
- **Agent:** See `clients/windows/` and `clients/android/` for build/setup (optional, for agent changes only).
- Keep code clean and tested so others can review and maintain it.

---

## Legal / Contributor agreement

By submitting a contribution (e.g. Pull Request), you confirm that:

1. **Authorship & rights** – You are the author of the contributed code, or you have the right to submit it under the project’s license (GPL-3.0).
2. **No conflicting rights** – Your contribution does not violate any third‑party rights (including copyright, patent, trademark, or other intellectual property). You will not submit code that is under a license or patent that conflicts with the project license.
3. **Responsibility** – You are responsible for what you push; you have reviewed your changes and accept that they may be used under the project’s terms.
4. **Grant to the project** – You grant the project maintainer (Róbert Pešout / BertSoftware – robert.pesout@gmail.com) the unlimited, perpetual right to use, modify, and incorporate your contribution into the project, including under other (including commercial) licenses in the future.

*Why?* So the project can evolve without chasing individual contributors for permission. You remain credited as the author; the project keeps the right to use and relicense the code.

---

## Code of conduct

Be respectful. We are here to build a useful tool for families.

---

## Tests, builds, and CI

### What runs automatically (GitHub Actions)

| Workflow | Trigger | What it does |
|----------|---------|--------------|
| **Backend tests** | Push/PR (any branch) touching `backend/**` | `pytest` in `backend/tests/` |
| **Frontend tests** | Push/PR (any branch) touching `frontend/**` | `npm test` in `frontend/` |
| **Android tests** | Push/PR (any branch) touching `clients/android/**` | `./gradlew test`; on success builds APK (artifact) |
| **Build Server (Docker)** | Push/PR to main touching `backend/**`, `frontend/**`, `docker/**` | Builds frontend, builds Docker image, pushes to GHCR (`familyeye-server`) |
| **Build Windows Agent** | Push/PR to main touching `installer/agent/**`, `clients/windows/**` | Builds Windows agent installer (artifact) |
| **Build Windows Server** | Push/PR to main touching `installer/server/**`, `backend/**`, `frontend/**` | Builds Windows server installer (artifact) |
| **Create Release** | Push of tag `v*` (e.g. `v2.4.0`) | Runs unit tests; builds APK, Windows agent and Windows server installers; creates GitHub Release and attaches all artifacts |

Release is created **only after all unit tests pass**. No manual approval step by default (optional: use a GitHub Environment with required reviewers if you want gating).

### What you should run locally before opening a PR

- **Backend:** From `backend/`: `pip install -r requirements.txt pytest pytest-cov pytest-asyncio` then `python -m pytest tests/ -x --tb=short` (use `DATABASE_URL=sqlite:///:memory:` and `BACKEND_URL=http://localhost:8000` if needed).
- **Frontend:** From `frontend/`: `npm ci && npm test -- --run`.
- **Android:** From `clients/android/`: `./gradlew test` (or run tests from Android Studio).

See `docs/reference/testing.md` for detailed test descriptions and critical tests before release.

### Conventional Commits (recommended for changelog)

Use [Conventional Commits](https://www.conventionalcommits.org/) so changelogs can be generated from commit history:

- `feat: add X` – new feature (minor bump)
- `fix: Y` – bug fix (patch bump)
- `chore: Z` – maintenance (no user-facing change)
- `docs: ...` – documentation only
- `BREAKING CHANGE: ...` in footer – major bump

Example: `git commit -m "feat: add Device Owner setup wizard"`. From the repo root you can run `npm run release:changelog` (after `npm install`) to append new entries to `CHANGELOG.md` from commits since the last tag.

### Releasing a new version

Version is defined in the root file `VERSION`. All components (backend, frontend, Android, installers, website) read or are updated from it.

**One command (recommended):** From repo root, on branch `main`:

```bash
npm run release -- patch
```

Use `patch` (2.4.0 → 2.4.1), `minor` (2.4.0 → 2.5.0), or `major` (2.4.0 → 3.0.0). This will: bump version everywhere, update CHANGELOG from commits (if `npm install` was run in root), commit, create tag, and push `main` + tag. GitHub Actions will then create the [Release](https://github.com/SkriptyRobert/FamilyEye/releases) with APK and Windows installer. Optional: `--no-changelog` to skip changelog, `--dry-run` to only print commands.

**Manual steps** (if you prefer or need a specific version):

1. **Bump version:** `python scripts/bump_version.py 2.5.0` or `patch` / `minor` / `major`.
2. **Update CHANGELOG:** Edit `CHANGELOG.md` or run `npm run release:changelog`.
3. **Commit and push:** `git add -A && git commit -m "chore: release 2.5.0" && git push origin main`.
4. **Tag and push tag:** `git tag v2.5.0`, then `git push origin v2.5.0`.
5. **GitHub Release:** The workflow runs on push of tag `v*` and creates the release with artifacts.

Always bump and commit the new version **before** creating the tag so the tagged commit contains the updated version everywhere.

### Docker image and deployment

- Pre-built server image: `ghcr.io/skriptyrobert/familyeye/familyeye-server:latest` (and per-commit SHA tags). Use with `docker/server/docker-compose.yml`; set `BACKEND_URL` in `.env` for the public URL. See `docker/server/README.md`.
