"""asyncua compatibility shims — capability-gated monkey-patches.

Central location for all workarounds targeting known asyncua bugs.  Each patch
is guarded by the upstream behavior it corrects, not by version alone:

  * If ``UaClient._send_request`` still defaults ``timeout`` to a hard-coded
    numeric value, the patch is applied.
  * If upstream changes the default to ``None`` or removes the method, the patch
    is skipped and a DeprecationWarning marks the shim for removal.

Usage (from any tests/python/{live,integration} file)::

    from .._asyncua_compat import apply_send_request_timeout_patch
    apply_send_request_timeout_patch()

Do not use asyncua's reported version as the only gate.  The repo-pinned master
SHA can self-report as a pre-release while still retaining the affected
``_send_request(..., timeout=1, ...)`` signature.
"""

from __future__ import annotations

import importlib.metadata
import inspect
import warnings

from packaging.version import Version


def _asyncua_version() -> Version:
    try:
        return Version(importlib.metadata.version("asyncua"))
    except Exception:
        return Version("0.0.0")


ASYNCUA_VERSION: Version = _asyncua_version()


def _send_request_needs_timeout_patch(send_request) -> bool:
    try:
        timeout_param = inspect.signature(send_request).parameters.get("timeout")
    except (TypeError, ValueError):
        return False
    if timeout_param is None:
        return False
    return timeout_param.default not in {None, inspect.Parameter.empty}


# ---------------------------------------------------------------------------
# Patch 1 — _send_request timeout
#
# Bug       : UaClient.call() passes timeout=None to _send_request(), which
#             asyncua falls back to a hard-coded 1-second default instead of
#             using the configured client timeout.  Heavy server calls that
#             take >1 s (e.g. SimulateJobResult with refs=True, or
#             load_data_type_definitions) raise spurious timeout errors.
# Affected  : asyncua releases/SHA builds where UaClient._send_request has a
#             hard-coded numeric timeout default (currently 1 second).
# Fixed in  : unknown.  The repo-pinned SHA still has timeout=1 even when it
#             self-reports as 2.0a0, so this shim is capability-gated.
# Remove    : when _send_request no longer needs this patch in the pinned
#             asyncua build; then delete every call to
#             apply_send_request_timeout_patch() and this module.
# ---------------------------------------------------------------------------
def apply_send_request_timeout_patch() -> None:
    """Wrap UaClient._send_request so timeout=None inherits self._timeout.

    Safe to call multiple times — re-patching is a no-op after the first call.
    Emits DeprecationWarning when the installed asyncua no longer exposes the
    affected signature so the call site is easy to find and remove.
    """
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
    if not _send_request_needs_timeout_patch(_orig):
        warnings.warn(
            f"asyncua {ASYNCUA_VERSION}: _send_request no longer has the "
            "hard-coded timeout default this shim patches. Re-verify live "
            "tests, remove every call to apply_send_request_timeout_patch(), "
            "and delete tests/python/_asyncua_compat.py.",
            DeprecationWarning,
            stacklevel=2,
        )
        return

    async def _fixed(self, request, timeout=None, message_type=ua.MessageType.SecureMessage):
        if timeout is None:
            timeout = getattr(self, "_timeout", getattr(self, "timeout", timeout))
        return await _orig(self, request, timeout, message_type)  # type: ignore[arg-type]

    _fixed._ijt_patched = True  # type: ignore[attr-defined]
    _uc.UaClient._send_request = _fixed  # type: ignore[method-assign]
