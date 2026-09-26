"""Check that Python files parse without executing them."""

from __future__ import annotations

import ast
import sys
from pathlib import Path


def main(filenames: list[str]) -> int:
    failed = False
    for filename in filenames:
        try:
            ast.parse(Path(filename).read_bytes(), filename=filename)
        except SyntaxError as error:
            print(f"{filename}: invalid Python syntax: {error}", file=sys.stderr)
            failed = True
    return int(failed)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
