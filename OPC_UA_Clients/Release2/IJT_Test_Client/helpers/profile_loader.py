"""
CU claim resolution for the IJT OPC UA test framework.

Reads the authoritative Conformance Unit (CU) claims from the SUT manifest
selected for the run (``OPCUA_CAPABILITIES_FILE`` points at a ``*.sut.yaml``
file), resolves the active profile and facets, applies ``cu_overrides``, and
returns the final set of claimed conformance unit keys.

The claimed-CU set drives the pytest ``requires_cu`` marker: tests whose CU key
is absent from the set are skipped with an informative message - they are never
failed just because a feature is not claimed by a given server.

Claims are authoritative: discovery observations never silently mutate them.
An explicitly selected manifest that cannot be read is a configuration error -
:func:`resolve_session_supported_cus` raises :class:`ExplicitManifestError`
rather than falling back to "no gating".

Usage in conftest.py::

    from helpers.profile_loader import get_skip_reason, resolve_session_supported_cus

    # at session start:
    _SUPPORTED = resolve_session_supported_cus()

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
from typing import FrozenSet, Mapping

import yaml

from helpers.skip_reasons import not_supported_reason
from helpers.sut_manifest import CapabilityClaims, load_capability_claims

logger = logging.getLogger(__name__)

#: Environment variable naming the SUT manifest whose claims gate the run.
MANIFEST_ENV_VAR = "OPCUA_CAPABILITIES_FILE"

_PROFILES_DIR = Path(__file__).parent.parent / "profiles"

#: Dispositions in ``capability_claims.cu_overrides`` that claim a CU.
_CLAIMING_DISPOSITIONS = frozenset({"supported", "manual_required"})


class ExplicitManifestError(RuntimeError):
    """Raised when an explicitly selected SUT manifest cannot be used.

    Selecting a manifest is an explicit statement about which CUs are claimed.
    A missing, unreadable, or invalid selection is a configuration error: it
    must stop the run instead of silently disabling CU gating (which would let
    a run report evidence for a claim scope nobody configured).
    """


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
        logger.warning("profiles/facets.yaml not found - no facet definitions available")
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


def resolve_claimed_cus(claims: CapabilityClaims) -> FrozenSet[str]:
    """Resolve *claims* into the final set of claimed conformance unit keys.

    Resolution order:
      1. Load facets.yaml to get the facet -> CU-key mapping.
      2. Expand ``active_profile`` into its facet list.
      3. Union in any additional ``supported_facets``.
      4. Apply ``cu_overrides``: ``unsupported`` removes a key,
         ``supported``/``manual_required`` add one.
    """
    all_facets = _load_facets()
    claimed: set[str] = set()

    for facet_name in _resolve_profile_facets(claims.active_profile):
        keys = all_facets.get(facet_name, [])
        if not keys and facet_name not in all_facets:
            logger.warning("Unknown facet '%s' in profile '%s'", facet_name, claims.active_profile)
        claimed.update(keys)

    for facet_name in claims.supported_facets:
        keys = all_facets.get(facet_name, [])
        if not keys and facet_name not in all_facets:
            logger.warning("Unknown facet '%s' in capability_claims.supported_facets", facet_name)
        claimed.update(keys)

    for cu_key, disposition in claims.cu_overrides.items():
        if disposition == "unsupported":
            claimed.discard(cu_key)
            logger.debug("cu_override: '%s' -> unsupported (will skip)", cu_key)
        elif disposition in _CLAIMING_DISPOSITIONS:
            claimed.add(cu_key)
            logger.debug("cu_override: '%s' -> %s (claimed)", cu_key, disposition)

    logger.info(
        "SUT manifest claims %d conformance units (active profile '%s')",
        len(claimed),
        claims.active_profile,
    )
    return frozenset(claimed)


def load_supported_cus(manifest_path: Path | None = None) -> FrozenSet[str]:
    """
    Read the SUT manifest's claims and return the frozenset of claimed
    conformance unit keys for the current server under test.

    Parameters
    ----------
    manifest_path:
        Explicit path to a ``*.sut.yaml`` manifest. When None the loader checks
        the ``OPCUA_CAPABILITIES_FILE`` environment variable. When neither is
        set, every conformance unit is treated as claimed (full specification
        coverage mode), matching the historical no-declaration behaviour.

    Raises
    ------
    FileNotFoundError
        When an explicitly selected manifest does not exist.
    helpers.sut_manifest.SutManifestError
        When the selected file is not a valid SUT manifest (including a legacy
        ``*.profile.yaml`` / ``*.capabilities.yaml`` file).
    """
    if manifest_path is None:
        env_path = os.environ.get(MANIFEST_ENV_VAR)
        if not env_path:
            logger.info(
                "No SUT manifest selected (%s unset) - treating all Conformance Units as claimed "
                "(full specification coverage mode)",
                MANIFEST_ENV_VAR,
            )
            return _all_cus_from_facets()
        manifest_path = Path(env_path)

    if not manifest_path.exists():
        raise FileNotFoundError(f"SUT manifest not found: {manifest_path}")

    return resolve_claimed_cus(load_capability_claims(manifest_path))


def is_cu_supported(cu_key: str, supported: FrozenSet[str]) -> bool:
    """Return True if the given conformance unit key is claimed by the SUT."""
    return cu_key in supported


def selected_manifest_path(env: Mapping[str, str] | None = None) -> Path | None:
    """Return the explicitly selected SUT manifest path, or None when unset.

    Checks ``OPCUA_CAPABILITIES_FILE`` first, then falls back to
    ``OPCUA_TARGET_SERVER_PROFILE`` so that both env vars work interchangeably.
    """
    environ = os.environ if env is None else env
    raw = (environ.get(MANIFEST_ENV_VAR) or environ.get("OPCUA_TARGET_SERVER_PROFILE") or "").strip()
    return Path(raw) if raw else None


def resolve_session_supported_cus(
    manifest_path: Path | None = None,
    *,
    env: Mapping[str, str] | None = None,
) -> FrozenSet[str] | None:
    """Resolve the claimed-CU set for one pytest session.

    Returns
    -------
    frozenset[str]
        The claimed conformance unit keys. When no manifest is selected this is
        every CU known to ``profiles/facets.yaml`` (full specification coverage
        mode), which keeps the historical no-declaration behaviour.
    None
        Only when nothing was explicitly selected *and* the facet catalogue
        itself could not be read. CU gating is then disabled so an unrelated
        catalogue problem cannot silently mark everything unsupported.

    Raises
    ------
    ExplicitManifestError
        When a manifest was explicitly selected (argument or
        ``OPCUA_CAPABILITIES_FILE``) but is missing, unreadable, or invalid.
        The caller must turn this into a configuration/collection failure.
    """
    explicit_path = manifest_path if manifest_path is not None else selected_manifest_path(env)
    if explicit_path is not None:
        try:
            return load_supported_cus(explicit_path)
        except Exception as exc:
            raise ExplicitManifestError(
                f"The selected SUT manifest '{explicit_path}' could not be used: {exc}. "
                f"Fix the manifest, or unset {MANIFEST_ENV_VAR} to run without CU claim gating."
            ) from exc

    try:
        return load_supported_cus()
    except Exception as exc:  # noqa: BLE001 - catalogue problems must not gate a run
        logger.warning(
            "No SUT manifest is selected and the facet catalogue could not be read (%s) - "
            "all conformance units are treated as supported",
            exc,
        )
        return None


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


def get_skip_reason(cu_key: str, manifest_path: Path | None = None) -> str:
    """
    Return the canonical public skip reason for a CU that is not claimed.

    The run summary groups unclaimed server-profile CUs separately, so this
    reason intentionally omits config-file guidance and private path details.
    """
    _ = manifest_path
    return not_supported_reason(cu_key, is_cu=True)
