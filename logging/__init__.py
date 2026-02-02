"""
Compatibility package.

This repo needs a `logging/stream.py` module, but Python's standard library also
provides a `logging` package that is used by FastAPI/Uvicorn and most deps.

If a project-level `logging` package shadows stdlib, imports like `import logging`
would break the world. This module deliberately loads the stdlib logging package
code into this package namespace, then keeps our extra `stream` module alongside it.
"""

from __future__ import annotations

import sysconfig
from pathlib import Path


def _bootstrap_stdlib_logging() -> None:
    stdlib = Path(sysconfig.get_paths()["stdlib"])
    std_logging_dir = stdlib / "logging"
    std_init = std_logging_dir / "__init__.py"
    if not std_init.exists():
        raise RuntimeError(f"Could not locate stdlib logging at {std_init}")

    # Ensure `from . import handlers` etc resolves to stdlib modules.
    if str(std_logging_dir) not in __path__:  # type: ignore[name-defined]
        __path__.append(str(std_logging_dir))  # type: ignore[name-defined]

    code = std_init.read_text(encoding="utf-8")
    exec(compile(code, str(std_init), "exec"), globals(), globals())


_bootstrap_stdlib_logging()

