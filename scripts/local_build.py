#!/usr/bin/env python3
"""Run the project's linters and tests locally."""
from __future__ import annotations

import argparse
import importlib
import os
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_ENV = os.environ.copy()
DEFAULT_ENV.setdefault("EMBEDDING_INDEX_BACKEND", "memory")


class MissingDependencyError(RuntimeError):
    """Raised when a required command dependency is unavailable."""


def run_step(step_name: str, command: list[str], *, env: dict[str, str] | None = None) -> None:
    """Execute a command and stream its output."""
    display_cmd = " ".join(command)
    print(f"\n==> {step_name}: {display_cmd}")
    completed = subprocess.run(command, cwd=PROJECT_ROOT, env=env or DEFAULT_ENV, check=False)
    if completed.returncode != 0:
        raise SystemExit(completed.returncode)


def ensure_module(module_name: str, *, install_hint: str) -> None:
    """Ensure a Python module can be imported before invoking it as a CLI."""
    try:
        importlib.import_module(module_name)
    except ModuleNotFoundError as exc:  # pragma: no cover - defensive runtime guard
        raise MissingDependencyError(
            f"Required module '{module_name}' is not installed. "
            f"Install it with `{install_hint}`."
        ) from exc


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command line arguments for the build script."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--skip-tests",
        action="store_true",
        help="Skip running pytest.",
    )
    parser.add_argument(
        "--skip-lint",
        action="store_true",
        help="Skip running linting steps.",
    )
    parser.add_argument(
        "--pytest-args",
        nargs=argparse.REMAINDER,
        help="Extra arguments to forward to pytest.",
    )
    return parser.parse_args(argv)


def lint() -> None:
    """Run static analysis tools."""
    ensure_module("ruff", install_hint="pip install ruff")
    run_step("ruff", [sys.executable, "-m", "ruff", "check", "--ignore", "E402", "."])

    ensure_module("bandit", install_hint="pip install bandit")
    run_step(
        "bandit",
        [
            sys.executable,
            "-m",
            "bandit",
            "-r",
            "app",
            "api",
            "structlog",
            "scripts",
            "-x",
            "tests,data",
        ],
    )

    run_step("python compileall", [sys.executable, "-m", "compileall", "."])


def test(pytest_args: list[str] | None) -> None:
    """Run the project's test suite."""
    command = [sys.executable, "-m", "pytest"]
    if pytest_args:
        command.extend(pytest_args)
    run_step("pytest", command)



def main(argv: list[str] | None = None) -> int:
    """Entry point for the local build script."""
    args = parse_args(argv)

    if not args.skip_lint:
        lint()

    if not args.skip_tests:
        test(args.pytest_args)

    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(main())
