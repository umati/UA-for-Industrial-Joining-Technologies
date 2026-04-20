#!/usr/bin/env python3
"""Normalize forbidden Python 3 multi-except syntax.

Rewrites the bare-comma form (Python 3 logic bug) into the parenthesised form::

    except (TypeError, ValueError):

Supports --check mode for CI/pre-commit enforcement.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

PATTERN = re.compile(
    r"(^[ \t]*except[ \t]+)([A-Za-z_][\w\.]*)([ \t]*,[ \t]*)([A-Za-z_][\w\.]*)([ \t]*:)",
    re.MULTILINE,
)


def _fix_text(text: str) -> tuple[str, int]:
    return PATTERN.subn(lambda m: f"{m.group(1)}({m.group(2)}, {m.group(4)}){m.group(5)}", text)


def _process_file(path: Path, write: bool) -> int:
    raw = path.read_text(encoding="utf-8")
    fixed, count = _fix_text(raw)
    if count and write:
        path.write_text(fixed, encoding="utf-8")
    return count


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--check", action="store_true", help="fail if any forbidden syntax is found"
    )
    parser.add_argument("--write", action="store_true", help="rewrite files in-place")
    parser.add_argument("files", nargs="*", help="python files to process")
    args = parser.parse_args()

    if args.check and args.write:
        parser.error("Use either --check or --write, not both.")
    if not args.check and not args.write:
        parser.error("Specify one mode: --check or --write.")

    write = args.write

    if args.files:
        paths = [Path(f) for f in args.files if f.endswith(".py")]
    else:
        proc = subprocess.run(
            ["git", "ls-files", "*.py"],  # noqa: S607
            check=False,
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            print(proc.stderr.strip(), file=sys.stderr)
            return proc.returncode or 1
        paths = [Path(line.strip()) for line in proc.stdout.splitlines() if line.strip()]
    total = 0
    touched = 0

    for path in paths:
        if not path.exists() or not path.is_file():
            continue
        count = _process_file(path, write)
        if count:
            total += count
            touched += 1
            print(f"{path}: {count}")

    if args.check and total:
        print(
            f"Found {total} forbidden multi-except occurrence(s) in {touched} file(s).",
            file=sys.stderr,
        )
        return 1

    if total:
        print(f"Fixed {total} occurrence(s) in {touched} file(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
