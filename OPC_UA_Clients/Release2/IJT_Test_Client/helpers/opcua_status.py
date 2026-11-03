"""Tell a real server rejection apart from a transport or session failure.

Negative tests expect the server to reject a call. A dropped connection or closed
session also raises ``ua.UaError`` but proves nothing about server behaviour, so
it must fail the test instead of counting as the expected rejection.

``BadTimeout`` is deliberately excluded: client-side wall-clock timeouts surface
as ``asyncio.TimeoutError`` and are handled by callers, while a method may
legitimately return ``BadTimeout`` as its own result.
"""

from asyncua import ua

TRANSPORT_STATUS_CODES = frozenset(
    {
        ua.StatusCodes.BadCommunicationError,
        ua.StatusCodes.BadConnectionClosed,
        ua.StatusCodes.BadNoCommunication,
        ua.StatusCodes.BadNotConnected,
        ua.StatusCodes.BadSecureChannelClosed,
        ua.StatusCodes.BadSecureChannelIdInvalid,
        ua.StatusCodes.BadServerNotConnected,
        ua.StatusCodes.BadSessionClosed,
        ua.StatusCodes.BadSessionIdInvalid,
        ua.StatusCodes.BadShutdown,
    }
)


def is_transport_failure(exc: BaseException) -> bool:
    """Return True when the error means the call never got a server decision."""
    return isinstance(exc, ua.UaStatusCodeError) and exc.code in TRANSPORT_STATUS_CODES


def require_server_rejection(exc: BaseException, context: str) -> None:
    """Fail the current test unless ``exc`` is a genuine server-side rejection."""
    import pytest

    if is_transport_failure(exc):
        pytest.fail(f"{context}: call failed in transport, not rejected by the server: {exc}")
