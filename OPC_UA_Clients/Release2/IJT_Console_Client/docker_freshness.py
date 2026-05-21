"""Docker image freshness helpers for the OPC UA simulator.

Pure stdlib so this module is safe to import from regression tests that
must run in lightweight environments (no cryptography, no asyncua, no
pytest plugins beyond the core).

Behavior parity with the C# fixture's ShouldBuildDockerImage path lives in
OPC_UA_Clients/Release2/IJT_CSharp_Client/Tests/IJT_CSharp_Client.Tests/
OpcUaServerFixture.cs (see DockerImageCreatedUtc / ShouldBuildDockerImage).
Keep the two implementations behavior-equivalent.
"""

from __future__ import annotations

import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

_DOCKER_INSPECT_TIMEOUT_SECONDS = 10


def parse_docker_created_timestamp(value: str) -> float | None:
    """Parse a `docker image inspect --format {{.Created}}` value.

    Docker emits RFC3339 with nanosecond precision (e.g. trailing
    `.204798168Z`). Python's ``datetime.fromisoformat`` only accepts up to
    microsecond precision, so we truncate the fractional component to 6
    digits before parsing.

    Returns the POSIX timestamp on success, or ``None`` when the value is
    empty or unparseable.
    """
    text = value.strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    if "." in text:
        head, tail = text.split(".", 1)
        zone_pos = min(
            [idx for idx in (tail.find("+"), tail.find("-")) if idx >= 0],
            default=-1,
        )
        if zone_pos >= 0:
            fraction = tail[:zone_pos]
            zone = tail[zone_pos:]
        else:
            fraction = tail
            zone = ""
        text = f"{head}.{fraction[:6].ljust(6, '0')}{zone}"

    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.timestamp()


def docker_image_created_timestamp(
    docker_exe: str,
    image: str,
    *,
    cwd: str | os.PathLike[str] | None = None,
) -> float | None:
    """Return the POSIX-time when ``image`` was created, or ``None`` when
    the image is missing or ``docker image inspect`` otherwise fails."""
    try:
        result = subprocess.run(
            [docker_exe, "image", "inspect", image, "--format", "{{.Created}}"],
            cwd=str(cwd) if cwd is not None else None,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            check=False,
            timeout=_DOCKER_INSPECT_TIMEOUT_SECONDS,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return None
    if result.returncode != 0:
        return None
    return parse_docker_created_timestamp(result.stdout)


def is_image_stale(
    docker_exe: str,
    image: str,
    reference_path: Path,
    *,
    cwd: str | os.PathLike[str] | None = None,
) -> bool:
    """Return True when ``image`` is missing or older than ``reference_path``.

    Used by test fixtures to decide whether to pass ``--build`` to
    ``docker compose up``. When the reference file is missing, returns
    False (we cannot prove the image is stale, so do not force a rebuild).
    """
    if not reference_path.exists():
        return False
    image_created = docker_image_created_timestamp(docker_exe, image, cwd=cwd)
    if image_created is None:
        return True
    return reference_path.stat().st_mtime > image_created
