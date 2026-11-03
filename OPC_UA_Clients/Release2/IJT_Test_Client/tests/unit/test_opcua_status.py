"""Unit tests for helpers/opcua_status.py."""

import pytest
from asyncua import ua

from helpers.opcua_status import is_transport_failure, require_server_rejection


@pytest.mark.parametrize(
    "code",
    (
        ua.StatusCodes.BadConnectionClosed,
        ua.StatusCodes.BadSessionClosed,
        ua.StatusCodes.BadSecureChannelClosed,
        ua.StatusCodes.BadCommunicationError,
    ),
)
def test_transport_failure_fails_the_test(code):
    exc = ua.UaStatusCodeError(code)
    assert is_transport_failure(exc)
    with pytest.raises(pytest.fail.Exception, match="call failed in transport"):
        require_server_rejection(exc, "Method")


@pytest.mark.parametrize(
    "code",
    (
        ua.StatusCodes.BadNotImplemented,
        ua.StatusCodes.BadNotWritable,
        ua.StatusCodes.BadInvalidArgument,
        ua.StatusCodes.BadNodeIdUnknown,
        ua.StatusCodes.BadTimeout,
    ),
)
def test_server_rejection_is_accepted(code):
    exc = ua.UaStatusCodeError(code)
    assert not is_transport_failure(exc)
    require_server_rejection(exc, "Method")


def test_non_status_ua_error_is_accepted():
    require_server_rejection(ua.UaError("decode failure"), "Method")
