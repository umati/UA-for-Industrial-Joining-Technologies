"""
Profile loader for the IJT OPC UA test framework.

Reads server_capabilities.yaml (or the path given by OPCUA_CAPABILITIES_FILE
env var), resolves the active profile and facets, applies cu_overrides, and
returns the final set of supported conformance unit keys.

The supported-CU set drives the pytest requires_cu marker: tests whose CU key
is absent from the set are skipped with an informative message — they are never
failed just because a feature is not implemented on a given server.

Usage in conftest.py::

    from helpers.profile_loader import get_skip_reason, load_supported_cus, is_cu_supported

    # at session start:
    _SUPPORTED = load_supported_cus()

    def pytest_runtest_setup(item):
        for marker in item.iter_markers("requires_cu"):
            for cu_key in marker.args:
                if not is_cu_supported(cu_key, _SUPPORTED):
                    pytest.skip(get_skip_reason(cu_key))
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import FrozenSet

import yaml

from helpers.skip_reasons import not_supported_reason

logger = logging.getLogger(__name__)

_DEFAULT_CAPABILITIES_FILENAME = "server_capabilities.yaml"
_PROFILES_DIR = Path(__file__).parent.parent / "profiles"
_PROJECT_ROOT = Path(__file__).parent.parent


def _load_yaml(path: Path) -> dict:
    """Load a YAML file and return its contents as a dict."""
    with path.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    return data


def _load_facets() -> dict[str, list[str]]:
    """
    Load profiles/facets.yaml and return a dict mapping each facet name
    to its list of conformance unit keys.
    """
    facets_path = _PROFILES_DIR / "facets.yaml"
    if not facets_path.exists():
        logger.warning("profiles/facets.yaml not found — no facet definitions available")
        return {}

    raw = _load_yaml(facets_path)
    result: dict[str, list[str]] = {}
    for facet_name, facet_data in raw.get("facets", {}).items():
        result[facet_name] = facet_data.get("conformance_units", [])
    return result


def _resolve_profile_facets(profile_name: str) -> list[str]:
    """
    Load a named profile file from profiles/ and return its list of facet names.
    Returns an empty list if the profile file does not exist.
    """
    profile_path = _PROFILES_DIR / f"{profile_name}.yaml"
    if not profile_path.exists():
        logger.warning("Profile file not found: %s", profile_path)
        return []

    raw = _load_yaml(profile_path)
    return raw.get("profile", {}).get("facets", [])


def load_supported_cus(
    capabilities_path: Path | None = None,
) -> FrozenSet[str]:
    """
    Read server_capabilities.yaml and return the frozenset of supported
    conformance unit keys for the current server under test.

    Resolution order:
      1. Load facets.yaml to get the facet→CU-key mapping.
      2. Load the active_profile's YAML to get its facet list.
      3. Union in any additional supported_facets listed in capabilities.
      4. Apply cu_overrides: "unsupported" removes a key, "supported" adds one.

    Parameters
    ----------
    capabilities_path:
        Explicit path to a capabilities YAML file. When None the loader
        checks the OPCUA_CAPABILITIES_FILE env var, then falls back to
        server_capabilities.yaml in the project root.
    """
    if capabilities_path is None:
        env_path = os.environ.get("OPCUA_CAPABILITIES_FILE")
        if env_path:
            capabilities_path = Path(env_path)
        else:
            capabilities_path = _PROJECT_ROOT / _DEFAULT_CAPABILITIES_FILENAME

    if not capabilities_path.exists():
        logger.warning(
            "server_capabilities.yaml not found at %s — "
            "treating all conformance units as supported (full conformance mode)",
            capabilities_path,
        )
        return _all_cus_from_facets()

    caps = _load_yaml(capabilities_path)
    all_facets = _load_facets()

    supported_cu_keys: set[str] = set()

    # Resolve active base profile
    active_profile = caps.get("active_profile", "full_conformance")
    profile_facet_names = _resolve_profile_facets(active_profile)
    for facet_name in profile_facet_names:
        keys = all_facets.get(facet_name, [])
        if not keys and facet_name not in all_facets:
            logger.warning("Unknown facet '%s' in profile '%s'", facet_name, active_profile)
        supported_cu_keys.update(keys)

    # Add any explicitly declared extra facets
    for facet_name in caps.get("supported_facets", []):
        keys = all_facets.get(facet_name, [])
        if not keys and facet_name not in all_facets:
            logger.warning("Unknown facet '%s' in supported_facets", facet_name)
        supported_cu_keys.update(keys)

    # Apply fine-grained overrides
    for cu_key, disposition in (caps.get("cu_overrides") or {}).items():
        if disposition == "unsupported":
            supported_cu_keys.discard(cu_key)
            logger.debug("cu_override: '%s' → unsupported (will skip)", cu_key)
        elif disposition == "supported":
            supported_cu_keys.add(cu_key)
            logger.debug("cu_override: '%s' → supported (will run)", cu_key)
        else:
            logger.warning(
                "Unknown cu_override disposition '%s' for key '%s' — ignored",
                disposition,
                cu_key,
            )

    logger.info(
        "Profile '%s': %d conformance units declared supported",
        active_profile,
        len(supported_cu_keys),
    )
    return frozenset(supported_cu_keys)


def is_cu_supported(cu_key: str, supported: FrozenSet[str]) -> bool:
    """Return True if the given conformance unit key is in the supported set."""
    return cu_key in supported


def _all_cus_from_facets() -> FrozenSet[str]:
    """Fallback: return every CU key found across all facets in facets.yaml."""
    all_facets = _load_facets()
    all_keys: set[str] = set()
    for keys in all_facets.values():
        all_keys.update(keys)
    return frozenset(all_keys)


def load_all_cus_from_facets() -> FrozenSet[str]:
    """Return every CU key known to profiles/facets.yaml."""
    return _all_cus_from_facets()


def get_skip_reason(cu_key: str, capabilities_path: Path | None = None) -> str:
    """
    Return a human-readable skip reason for a CU that is not supported.
    Includes the path to the capabilities file so users know where to
    edit to enable the test.
    """
    if capabilities_path is None:
        env_path = os.environ.get("OPCUA_CAPABILITIES_FILE")
        caps_file = Path(env_path) if env_path else _PROJECT_ROOT / _DEFAULT_CAPABILITIES_FILENAME
    else:
        caps_file = capabilities_path

    return not_supported_reason(
        cu_key,
        detail=(
            f"CU: {cu_key}. "
            f"To enable: add it under cu_overrides in {caps_file.name} "
            f"or switch to a profile that includes it. "
            f"Config file: {caps_file}"
        ),
        is_cu=True,
    )
