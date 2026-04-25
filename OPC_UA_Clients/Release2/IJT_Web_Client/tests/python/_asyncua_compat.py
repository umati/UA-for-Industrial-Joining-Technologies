"""asyncua compatibility shims — version-gated monkey-patches.

Central location for all workarounds targeting known asyncua bugs.  Each patch
is guarded by a version check:

  * While asyncua < 1.2.0 stable  → patch is applied silently.
  * Once asyncua >= 1.2.0 stable  → patch is skipped and a DeprecationWarning
    is emitted so the call site is easy to locate and remove.

Usage (from any tests/python/{live,integration} file)::

    from .._asyncua_compat import apply_send_request_timeout_patch
    apply_send_request_timeout_patch()

Remove the call (and this module) once asyncua 1.2.0 stable ships and the
upstream fix is confirmed.
"""

from __future__ import annotations

import importlib.metadata
import warnings

from packaging.version import Version


def _asyncua_version() -> Version:
    try:
        return Version(importlib.metadata.version("asyncua"))
    except Exception:
        return Version("0.0.0")


ASYNCUA_VERSION: Version = _asyncua_version()


# ---------------------------------------------------------------------------
# Patch 1 — _send_request timeout
#
# Bug       : UaClient.call() passes timeout=None to _send_request(), which
#             asyncua falls back to a hard-coded 1-second default instead of
#             using the configured client timeout.  Heavy server calls that
#             take >1 s (e.g. SimulateJobResult with refs=True, or
#             load_type_definitions) raise spurious timeout errors.
# Affected  : asyncua 1.2b2 and all earlier releases (confirmed on 1.1.5).
# Fixed in  : not yet merged upstream as of asyncua 1.2b2.
# Remove    : when asyncua >= 1.2.0 stable — verify upstream fix, then delete
#             every call to apply_send_request_timeout_patch().
# ---------------------------------------------------------------------------
def apply_send_request_timeout_patch() -> None:
    """Wrap UaClient._send_request so timeout=None inherits self._timeout.

    Safe to call multiple times — re-patching is a no-op after the first call.
    Emits DeprecationWarning when asyncua >= 1.2.0 so the call site is found
    automatically once the upstream fix ships.
    """
    if ASYNCUA_VERSION >= Version("1.2.0"):
        warnings.warn(
            f"asyncua {ASYNCUA_VERSION} >= 1.2.0 stable: the _send_request "
            "timeout workaround in tests/python/_asyncua_compat.py is likely "
            "obsolete.  Verify that the upstream fix is in place, then remove "
            "every call to apply_send_request_timeout_patch() and delete "
            "_asyncua_compat.py.",
            DeprecationWarning,
            stacklevel=2,
        )
        return

    try:
        import asyncua.client.ua_client as _uc
        from asyncua import ua
    except ImportError:
        return  # asyncua not installed — nothing to patch

    if not hasattr(_uc.UaClient, "_send_request"):
        # Upstream renamed or removed _send_request — patch no longer needed.
        return

    # Guard against double-patching (e.g. conftest + individual test module).
    if getattr(_uc.UaClient._send_request, "_ijt_patched", False):
        return

    _orig = _uc.UaClient._send_request

    async def _fixed(self, request, timeout=None, message_type=ua.MessageType.SecureMessage):
        if timeout is None:
            timeout = self._timeout  # use the configured timeout (e.g. 60 s)
        return await _orig(self, request, timeout, message_type)  # type: ignore[arg-type]

    _fixed._ijt_patched = True  # type: ignore[attr-defined]
    _uc.UaClient._send_request = _fixed  # type: ignore[method-assign]
