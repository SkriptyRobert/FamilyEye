# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [2.4.1] - 2026-02-02

### Fixed

- Android: Improved agent process immortality and recovery mechanisms (accessibility service stability, usage tracking reliability).
- Security: Synchronized English and Czech security policies; added `certs/` to `.gitignore`.
- Security: Implemented probe path protection and automated SSL certificate management improvements.

## [2.4.0] - 2025-01-29

### Added

- Root `VERSION` file as single source of truth; backend, frontend, Android, installers and website read or are updated from it.
- `scripts/bump_version.py` for bumping version across all components (patch/minor/major or explicit version).
- Root `package.json` with `release:changelog` (conventional-changelog) and `release:bump` scripts.
- Conventional Commits section in CONTRIBUTING; "Stáhnout" on website points to `releases/latest`.

### Changed

- Release workflow: GitHub Actions use `setup_agent.iss` and version from `VERSION`; tests run on all branches (not only main).
- MkDocs docs: home page uses `index.md` so GitHub Pages serves `/docs/` correctly; removed `extra.version` (mike); added pymdown-extensions and build verification in deploy workflow.
- Website deploy: workflow uses `GITHUB_WORKSPACE` and verifies `site/index.html` after MkDocs build; duplicate `docs/mkdocs.yml` removed.
- Windows installer: Inno Setup `[Code]` section uses `//` for comments (fixes "Unknown identifier" compile errors).
- Frontend tests: `window.matchMedia` mocked in JSDOM setup so DeviceOwnerSetup tests pass in CI.
- Backend test: `test_calculate_day_usage_minutes` uses `timedelta(minutes=1)` instead of `replace(minute=...)` to avoid minute overflow.
- Workflows: removed `master` from branch triggers; only `main` (and `android-fix-process` where applicable).

### Fixed

- 404 on GitHub Pages docs (`/FamilyEye/docs/`).
- Windows agent installer build (Pascal comment syntax in Inno Setup).
- Frontend CI (matchMedia not defined in JSDOM).
- Backend CI (minute must be in 0..59 in stats service test).
