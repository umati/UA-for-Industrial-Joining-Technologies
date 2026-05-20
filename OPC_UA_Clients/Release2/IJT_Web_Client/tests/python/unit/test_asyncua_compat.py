"""Unit tests for asyncua compatibility shims."""

from __future__ import annotations

import inspect

import pytest

pytest.importorskip("asyncua", reason="asyncua not installed")

import asyncua.client.ua_client as ua_client  # noqa: E402

from tests.python import _asyncua_compat  # noqa: E402


async def _broken_send_request(self, request, timeout=1, message_type=None):
    return request, timeout, message_type


async def _fixed_send_request(self, request, timeout=None, message_type=None):
    return request, timeout, message_type


def test_send_request_timeout_patch_is_capability_gated() -> None:
    assert _asyncua_compat._send_request_needs_timeout_patch(_broken_send_request) is True
    assert _asyncua_compat._send_request_needs_timeout_patch(_fixed_send_request) is False


def test_current_asyncua_still_needs_send_request_timeout_patch() -> None:
    assert _asyncua_compat._send_request_needs_timeout_patch(ua_client.UaClient._send_request)


def test_apply_send_request_timeout_patch_handles_prerelease_version(monkeypatch) -> None:
    original = ua_client.UaClient._send_request
    monkeypatch.setattr(ua_client.UaClient, "_send_request", original)

    _asyncua_compat.apply_send_request_timeout_patch()
    patched = ua_client.UaClient._send_request

    assert getattr(patched, "_ijt_patched", False) is True
    assert inspect.signature(patched).parameters["timeout"].default is None
