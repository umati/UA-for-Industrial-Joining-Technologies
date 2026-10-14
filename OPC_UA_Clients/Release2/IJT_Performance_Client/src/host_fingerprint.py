"""Host fingerprint for benchmark reports (stdlib-only; privacy-aware)."""

from __future__ import annotations

import hashlib
import os
import platform
import socket
import sys
import uuid
from typing import Any


def generate_host_id() -> str:
    """Stable-enough local host id for Topology evidence (not a security proof)."""
    raw = f"{platform.node()}|{platform.system()}|{platform.machine()}|{uuid.getnode()}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def collect_host_fingerprint(*, include_network: bool = False, redact: bool = True) -> dict[str, Any]:
    """Return OS/CPU/RAM fingerprint. Never includes username.

    When ``redact`` is True (default), hostname and IP are omitted or hashed.
    Pass ``include_network=True`` and ``redact=False`` only when the operator opts in.
    """
    cpu_count = os.cpu_count()
    fingerprint: dict[str, Any] = {
        "host_id": generate_host_id(),
        "os": platform.system(),
        "os_release": platform.release(),
        "architecture": platform.machine(),
        "python": platform.python_version(),
        "cpu_count_logical": cpu_count,
        "processor": platform.processor() or "unknown",
        "redacted": bool(redact),
    }

    # Best-effort RAM via stdlib-only paths (Windows / POSIX). None if unavailable.
    total_ram = _total_ram_bytes()
    if total_ram is not None:
        fingerprint["ram_bytes"] = total_ram
        fingerprint["ram_gib"] = round(total_ram / (1024**3), 2)

    if include_network and not redact:
        fingerprint["hostname"] = platform.node()
        fingerprint["ip_addresses"] = _local_ips()
    elif include_network and redact:
        fingerprint["hostname_hash"] = hashlib.sha256(platform.node().encode("utf-8")).hexdigest()[:12]
        fingerprint["ip_count"] = len(_local_ips())

    return fingerprint


def _total_ram_bytes() -> int | None:
    try:
        # sys.platform narrows for mypy (platform.system() does not expose windll).
        if sys.platform == "win32":
            import ctypes

            class MEMORYSTATUSEX(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]

            stat = MEMORYSTATUSEX()
            stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat)):
                return int(stat.ullTotalPhys)
            return None

        # POSIX: sysconf when available
        try:
            sysconf = getattr(os, "sysconf", None)
            if sysconf is not None:
                pages = sysconf("SC_PHYS_PAGES")
                page_size = sysconf("SC_PAGE_SIZE")
                if isinstance(pages, int) and isinstance(page_size, int) and pages > 0:
                    return pages * page_size
        except (ValueError, OSError, AttributeError):
            pass
    except Exception:
        return None
    return None


def _local_ips() -> list[str]:
    ips: list[str] = []
    try:
        hostname = socket.gethostname()
        for info in socket.getaddrinfo(hostname, None):
            raw_addr = info[4][0]
            if not isinstance(raw_addr, str):
                continue
            if raw_addr and raw_addr not in ips and not raw_addr.startswith("127."):
                ips.append(raw_addr)
    except OSError:
        pass
    return ips
