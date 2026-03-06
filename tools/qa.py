#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import sys


def run(*cmd: str) -> None:
    print(f"\n$ {' '.join(cmd)}")
    result = subprocess.run(cmd)
    if result.returncode != 0:
        raise SystemExit(result.returncode)


def main() -> int:
    run(sys.executable, "-m", "compileall", "app", "tests")
    run(sys.executable, "-m", "pytest", "-q")
    print("\nQA OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())