# SignalZero Local Node – Agent Guide

## Repository overview
- **Runtime** code lives in `app/` and `api/`, while shared logging and helpers sit under `structlog/`.
- **Scripts** for local tooling (including lint/test automation) are in `scripts/`.
- **Tests** live inside `tests/` and should be kept in sync with feature changes.
- Avoid committing secrets; configuration relies on environment variables or a local `.env` file (see `README.md`).

## Coding conventions
- Follow the existing FastAPI and Python module structure when extending endpoints or services.
- Prefer dependency injection for external services to keep modules testable.
- Do not wrap imports in `try/except` blocks; missing dependencies should surface during `local_build.py` runs.
- Keep data files inside `data/` immutable unless specifically working on datasets.

## Required validation before submitting changes
- Always run the consolidated build script: `python scripts/local_build.py`.
  - This script executes Ruff, Bandit, `compileall`, and `pytest`. Use flags such as `--skip-tests` only when justified by the task instructions.
- Include any additional, task-specific checks requested by higher-level instructions (e.g., custom scripts or integration tests).

## Communication tips
- Summarize meaningful behavioral changes in commit messages and pull request descriptions.
- Call out new dependencies or configuration changes explicitly so reviewers can update their environments.
