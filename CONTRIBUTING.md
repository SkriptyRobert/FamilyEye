# Contributing to FamilyEye

Thank you for considering contributing to FamilyEye! 🎉

## 📋 Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Making Changes](#making-changes)
- [Coding Standards](#coding-standards)
- [Commit Messages](#commit-messages)
- [Pull Requests](#pull-requests)
- [Frozen Code Areas](#frozen-code-areas)

## Code of Conduct

Please be respectful and constructive. We're building software to help families - let's keep our community family-friendly too.

## Getting Started

1. **Fork** the repository
2. **Clone** your fork locally
3. **Setup** your development environment (see below)
4. **Create** a feature branch
5. **Make** your changes
6. **Test** your changes
7. **Submit** a Pull Request

## Development Setup

### Backend (Python)

```bash
cd backend
python -m venv venv
.\venv\Scripts\activate  # Windows
pip install -r requirements.txt
python run_https.py
```

### Frontend (React)

```bash
cd frontend
npm install
npm run dev
```

### Android Agent

1. Open `clients/android` in Android Studio
2. Sync Gradle
3. Run on emulator or device

## Making Changes

### Branch Naming

- `feature/description` - New features
- `fix/description` - Bug fixes
- `docs/description` - Documentation only
- `refactor/description` - Code refactoring

### Where to Contribute

| Area | Path | Notes |
|------|------|-------|
| Backend API | `backend/app/api/` | New endpoints, bug fixes |
| Frontend UI | `frontend/src/` | Components, styling |
| Documentation | `docs/` | Always welcome! |
| Android Agent | `clients/android/` | Careful - see frozen areas |
| Windows Agent | `clients/windows/agent/` | ⚠️ **FROZEN** - see below |

## Coding Standards

### Python (Backend)

- Follow PEP 8
- Use type hints
- Document functions with docstrings
- Maximum line length: 100 characters

### JavaScript/React (Frontend)

- Use functional components with hooks
- Use CSS modules or component-scoped CSS
- No inline styles (except dynamic values)
- Use meaningful component names

### Kotlin (Android)

- Follow Kotlin coding conventions
- Use dependency injection (Hilt)
- Prefer immutable data structures

## Commit Messages

Use conventional commits:

```
type(scope): description

[optional body]

[optional footer]
```

**Types:**
- `feat` - New feature
- `fix` - Bug fix
- `docs` - Documentation
- `style` - Formatting, no code change
- `refactor` - Code restructuring
- `test` - Adding tests
- `chore` - Maintenance

**Examples:**
```
feat(dashboard): add weekly usage chart
fix(agent): correct timezone handling in reports
docs(readme): update installation instructions
```

## Pull Requests

1. **Title** should be clear and descriptive
2. **Description** should explain:
   - What changes were made
   - Why changes were made
   - How to test the changes
3. **Link** related issues with `Fixes #123` or `Closes #123`
4. **Wait** for review before merging

### PR Checklist

- [ ] Code follows project style guidelines
- [ ] Self-review completed
- [ ] Changes are tested
- [ ] Documentation updated (if needed)
- [ ] No hardcoded secrets or paths

## ⚠️ Frozen Code Areas

The following areas are considered **stable and frozen**. Do not modify without explicit maintainer approval:

### Windows Agent (`clients/windows/agent/`)

This code is production-stable with critical features:
- Offline mode
- Self-healing
- Ghost filtering

**Exception Procedure:**
1. Open an issue explaining the need
2. Wait for maintainer approval
3. Only then create a PR

---

## Questions?

Open an issue with the `question` label or reach out to maintainers.

Thank you for helping make FamilyEye better! 🛡️
