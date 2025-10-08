#!/usr/bin/env python3
"""Run the project's linters and tests locally."""
from __future__ import annotations

import argparse
import importlib
import os
import shlex
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
# Bandit: subprocess usage restricted to curated commands.
from subprocess import CalledProcessError, run  # nosec B404
from typing import Sequence


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_ENV = os.environ.copy()
DEFAULT_ENV.setdefault("EMBEDDING_INDEX_BACKEND", "memory")
SAFE_MODULES = {"ruff", "bandit", "compileall", "pytest"}


class MissingDependencyError(RuntimeError):
    """Raised when a required command dependency is unavailable."""


def _validate_command(command: Sequence[str]) -> None:
    if not command:
        raise ValueError("Command list must contain at least one entry.")
    binary = Path(command[0])
    if binary != Path(sys.executable):
        raise ValueError(f"Unsupported executable: {binary}")
    if len(command) < 3 or command[1] != "-m":
        raise ValueError("Commands must invoke a Python module via '-m'.")
    module_name = command[2]
    if module_name not in SAFE_MODULES:
        raise ValueError(f"Module '{module_name}' is not in the approved allowlist.")


def run_step(step_name: str, command: list[str], *, env: dict[str, str] | None = None) -> None:
    """Execute a command and stream its output."""
    _validate_command(command)
    display_cmd = shlex.join(command)
    print(f"\n==> {step_name}: {display_cmd}")
    try:
        # Bandit: command arguments are validated in _validate_command.
        run(command, cwd=PROJECT_ROOT, env=env or DEFAULT_ENV, check=True, shell=False)  # nosec B603
    except CalledProcessError as exc:
        raise SystemExit(exc.returncode) from exc


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

    with TemporaryDirectory(prefix="local_build_pycache_") as cache_dir:
        compile_env = DEFAULT_ENV.copy()
        compile_env["PYTHONPYCACHEPREFIX"] = cache_dir
        run_step(
            "python compileall",
            [sys.executable, "-m", "compileall", "app", "api", "scripts", "structlog"],
            env=compile_env,
        )


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
