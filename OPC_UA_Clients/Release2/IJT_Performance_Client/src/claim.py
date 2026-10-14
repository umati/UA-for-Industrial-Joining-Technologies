"""Claim profile intended vs achieved (capacity vs split-host observed path)."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Literal
from urllib.parse import urlparse

from .config import is_loopback_endpoint
from .host_fingerprint import generate_host_id

ClaimName = Literal["capacity", "split_path", "auto"]
AchievedClaim = Literal["A", "B", "UNPROVEN", "NONE"]


@dataclass
class ClaimResult:
    intended: str  # auto | capacity | split_path
    achieved: AchievedClaim
    profile_label: str  # A | B | UNPROVEN | …
    reason: str
    producer_host_id: str | None = None
    client_host_id: str | None = None
    all_endpoints_local: bool = False
    topology_verified: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def resolve_claim(
    *,
    intended: str = "auto",
    endpoints: list[str],
    producer_host_id: str | None = None,
    client_host_id: str | None = None,
    topology_verified: bool = False,
    clock_quality_ok: bool = True,
    clock_probe_ran: bool = False,
    wire_timing_coverage: float | None = None,
) -> ClaimResult:
    """Compute achieved claim from evidence. Never auto-promotes to B from URL text alone.

    Profile B needs: distinct host IDs (typically from client-only inventory consumption),
    clock_probe_ran=True (caller must require measured clock_rtt_ms, not skew 0.0 alone),
    clock_quality_ok, and wire_timing_coverage >= 0.95. Intended split_path + UNPROVEN → exit 1 in CLI.
    """
    intended_norm = (intended or "auto").strip().lower()
    if intended_norm not in {"auto", "capacity", "split_path"}:
        intended_norm = "auto"

    client_id = client_host_id or generate_host_id()
    all_local = bool(endpoints) and all(is_loopback_endpoint(url) for url in endpoints)

    # Capacity (A) is always available for colocated / intended capacity.
    if intended_norm == "capacity":
        return ClaimResult(
            intended=intended_norm,
            achieved="A",
            profile_label="A",
            reason="Intended capacity (Profile A). Does not prove network or plant OPC path.",
            producer_host_id=producer_host_id,
            client_host_id=client_id,
            all_endpoints_local=all_local,
            topology_verified=False,
        )

    hosts_differ = (
        topology_verified
        and producer_host_id is not None
        and client_id is not None
        and producer_host_id != client_id
        and not all_local
    )

    def _unproven(reason: str) -> ClaimResult:
        return ClaimResult(
            intended=intended_norm,
            achieved="UNPROVEN",
            profile_label="UNPROVEN",
            reason=reason,
            producer_host_id=producer_host_id,
            client_host_id=client_id,
            all_endpoints_local=all_local,
            topology_verified=bool(topology_verified and hosts_differ),
        )

    def _profile_b_ready() -> str | None:
        """Return None if ready for B, else UNPROVEN reason."""
        if not hosts_differ:
            return (
                "distinct producer/client host IDs were not established via consumed inventory "
                "(URL/hostname alone is not enough; colocated self-written inventory is not evidence)."
            )
        if not clock_probe_ran:
            return "clock probe did not run (skipped or unavailable); Profile B requires a successful probe."
        if not clock_quality_ok:
            return "clock quality is insufficient for a formal path claim."
        if wire_timing_coverage is None:
            return "receive-timing coverage is unknown (no valid timed samples)."
        if wire_timing_coverage < 0.95:
            return f"receive-timing coverage is only {wire_timing_coverage:.1%} (need >= 95%)."
        return None

    if intended_norm == "split_path":
        blocked = _profile_b_ready()
        if blocked:
            return _unproven(f"split_path intended but {blocked}")
        return ClaimResult(
            intended=intended_norm,
            achieved="B",
            profile_label="B",
            reason=(
                "Profile B: bounded observed server-event-to-client-receive path under stated evidence. "
                "Not a global OPC UA acquittal; receive time is a protocol callback, not NIC wire time."
            ),
            producer_host_id=producer_host_id,
            client_host_id=client_id,
            all_endpoints_local=False,
            topology_verified=True,
        )

    # auto: A when colocated / unverified split; B only when split evidence is complete
    blocked_auto = _profile_b_ready()
    if blocked_auto is None:
        return ClaimResult(
            intended=intended_norm,
            achieved="B",
            profile_label="B",
            reason="auto → Profile B (verified distinct hosts + clock probe + receive-timing coverage).",
            producer_host_id=producer_host_id,
            client_host_id=client_id,
            all_endpoints_local=False,
            topology_verified=True,
        )

    return ClaimResult(
        intended=intended_norm,
        achieved="A",
        profile_label="A",
        reason=(
            "auto → Profile A (capacity). Split-host path claim not achieved: "
            f"all_local={all_local}, topology_verified={topology_verified}."
        ),
        producer_host_id=producer_host_id,
        client_host_id=client_id,
        all_endpoints_local=all_local,
        topology_verified=topology_verified,
    )


def endpoint_hosts(endpoints: list[str]) -> set[str]:
    hosts: set[str] = set()
    for url in endpoints:
        host = (urlparse(url).hostname or "").lower()
        if host:
            hosts.add(host)
    return hosts
