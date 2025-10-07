"""Simple test runner for the SignalZero Local Node codebase."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest


def main(argv: list[str] | None = None) -> int:
    """Execute the project's unit tests via pytest."""

    os.environ.setdefault("EMBEDDING_INDEX_BACKEND", "memory")

    argv = list(argv or sys.argv[1:])

    project_root = Path(__file__).resolve().parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    return pytest.main(argv)


if __name__ == "__main__":  # pragma: no cover - manual invocation
    raise SystemExit(main())
