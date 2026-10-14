"""Effective configuration echo with {value, source} provenance."""

from __future__ import annotations

from dataclasses import dataclass, fields
from typing import Any, Literal

from .config import OpcUaPoolConfig

Source = Literal["default", "profile", "env", "cli", "inventory"]


@dataclass
class TrackedValue:
    value: Any
    source: Source

    def to_dict(self) -> dict[str, Any]:
        return {"value": self.value, "source": self.source}


class EffectiveConfigTracker:
    """Track where each OpcUaPoolConfig field came from (CLI > env > profile > default)."""

    def __init__(self) -> None:
        self._sources: dict[str, Source] = {}

    def mark(self, field_name: str, source: Source) -> None:
        self._sources[field_name] = source

    def mark_many(self, names: list[str], source: Source) -> None:
        for name in names:
            self._sources[name] = source

    _SECRET_FIELDS = frozenset({"inventory_http_token"})

    def snapshot(
        self,
        cfg: OpcUaPoolConfig,
        *,
        extra: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for f in fields(cfg):
            if f.name.startswith("_") or f.name == "explicit_profile_fields":
                continue
            val = getattr(cfg, f.name)
            if f.name in self._SECRET_FIELDS:
                val = "***" if val else None
            src = self._sources.get(f.name, "default")
            out[f.name] = {"value": val, "source": src}
        if extra:
            for key, tracked in extra.items():
                if key in self._SECRET_FIELDS:
                    continue
                if isinstance(tracked, TrackedValue):
                    out[key] = tracked.to_dict()
                elif isinstance(tracked, dict) and "value" in tracked and "source" in tracked:
                    out[key] = tracked
                else:
                    out[key] = {"value": tracked, "source": "default"}
        return out


def parse_env_int(name: str, raw: str) -> int:
    """Parse env int or raise ValueError (invalid env must fail, not silently fall back)."""
    try:
        return int(raw)
    except ValueError as exc:
        raise ValueError(f"Invalid integer for environment variable {name}={raw!r}") from exc


def parse_env_float(name: str, raw: str) -> float:
    try:
        return float(raw)
    except ValueError as exc:
        raise ValueError(f"Invalid float for environment variable {name}={raw!r}") from exc
