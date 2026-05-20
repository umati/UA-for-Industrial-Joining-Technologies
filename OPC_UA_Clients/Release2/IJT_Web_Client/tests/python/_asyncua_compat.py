"""asyncua compatibility shims — version-gated monkey-patches.

Central location for all workarounds targeting known asyncua bugs.  Each patch
is guarded by a version check:

  * While asyncua < 1.3.0           → patch is applied silently.
  * Once asyncua >= 1.3.0           → patch is skipped and a DeprecationWarning
    is emitted so the call site is easy to locate and re-verify.

Usage (from any tests/python/{live,integration} file)::

    from .._asyncua_compat import apply_send_request_timeout_patch
    apply_send_request_timeout_patch()

The 1.3.0 threshold was chosen because the upstream timeout bug is NOT yet
fixed at master SHA 35a77c6b (2026-05-11 — the SHA pinned in our
repo-root constraints.txt).  When asyncua publishes a release that includes the
fix, bump the gate, re-verify, and remove this module + every call to
apply_send_request_timeout_patch().
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
#             load_data_type_definitions) raise spurious timeout errors.
# Affected  : asyncua 1.2b2 and all earlier releases (confirmed on 1.1.5).
# Fixed in  : NOT YET FIXED upstream.  Verified absent at master SHA
#             35a77c6b128a4f1226a685cde3b46abd59975258 (2026-05-11) — the
#             commit currently pinned by repo-root constraints.txt.
# Remove    : when asyncua >= 1.3.0 stable ships — verify upstream fix is
#             actually present, then delete every call to
#             apply_send_request_timeout_patch() and this module.
# ---------------------------------------------------------------------------
def apply_send_request_timeout_patch() -> None:
    """Wrap UaClient._send_request so timeout=None inherits self._timeout.

    Safe to call multiple times — re-patching is a no-op after the first call.
    Emits DeprecationWarning when asyncua >= 1.3.0 so the call site is found
    automatically once the upstream fix has potentially shipped.
    """
    if ASYNCUA_VERSION >= Version("1.3.0"):
        warnings.warn(
            f"asyncua {ASYNCUA_VERSION} >= 1.3.0: re-verify that the "
            "_send_request timeout fix has actually landed upstream "
            "(absent at master SHA 35a77c6b on 2026-05-11).  If present, "
            "remove every call to apply_send_request_timeout_patch() and "
            "delete tests/python/_asyncua_compat.py.",
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
