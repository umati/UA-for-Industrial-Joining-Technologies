"""Validate independent client locks using automatically prepared uv."""

import subprocess
import sys
from pathlib import Path

from tool_bootstrap import ensure_uv


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    uv = ensure_uv(root)
    failed = False
    for client in (
        "IJT_Console_Client",
        "IJT_Performance_Client",
        "IJT_Test_Client",
        "IJT_Web_Client",
    ):
        result = subprocess.run(  # noqa: S603 - fixed lock-check arguments
            [uv, "lock", "--check"],
            cwd=root / "OPC_UA_Clients" / "Release2" / client,
            check=False,
        )
        failed = failed or result.returncode != 0
    return int(failed)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1) from exc
