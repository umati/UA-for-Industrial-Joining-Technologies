import inspect
import os
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

import conftest
from helpers.sut_manifest import manifest_file_sha256, render_manifest_yaml


@pytest.mark.parametrize(
    "fixture_name,target",
    [
        ("session_client", False),
        ("opcua_client", False),
        ("_module_subscription_client", False),
        ("subscription_client", True),
    ],
)
async def test_fixture_clients_use_bounded_health_probe(monkeypatch, fixture_name, target):
    client = object()
    factory = MagicMock(return_value=client)
    monkeypatch.setattr(conftest, "Client", factory)
    monkeypatch.setattr(conftest, "_connect_test_client", AsyncMock())
    monkeypatch.setattr(conftest, "_disconnect_test_client", AsyncMock())
    monkeypatch.setattr(conftest, "_target_server_profile_path", lambda: "target.yaml" if target else "")
    fixture = getattr(conftest, fixture_name).__wrapped__
    args = (object(), None) if fixture_name == "subscription_client" else (object(),)
    generator = fixture(*args)
    assert await anext(generator) is client
    factory.assert_called_once_with(conftest.SERVER_URL, timeout=120, watchdog_intervall=30)
    await generator.aclose()


@pytest.fixture
def reviewed_config(monkeypatch, tmp_path):
    for name in ("OPCUA_CAPABILITIES_FILE", "OPCUA_TARGET_SERVER_PROFILE", "OPCUA_TARGET_MANIFEST_SHA256"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(conftest, "_SUPPORTED_CUS", None)
    monkeypatch.setattr(conftest, "_UNREVIEWED_CUS", frozenset())
    monkeypatch.setattr(conftest, "_WORKFLOW_EXCLUDED_CUS", frozenset())
    path = tmp_path / "controller.yaml"
    path.write_text(render_manifest_yaml("remote_start_multi_operation"), encoding="utf-8")
    monkeypatch.setenv("OPCUA_TARGET_SERVER_PROFILE", str(path))
    config = MagicMock()
    config.option.basetemp = str(tmp_path)
    config.stash = {}
    yield config, path
    conftest.pytest_unconfigure(config)


def test_direct_pytest_reviews_manifest_and_blocks_later_edits(reviewed_config):
    config, path = reviewed_config
    conftest.pytest_configure(config)
    item = SimpleNamespace(config=config, user_properties=[], iter_markers=lambda _: [])
    conftest.pytest_runtest_setup(item)
    path.write_text(path.read_text().replace("max_candidates: 3", "max_candidates: 2"))
    with pytest.raises(pytest.skip.Exception, match="BLOCKED"):
        conftest.pytest_runtest_setup(item)
    assert ("ijt_outcome", "blocked") in item.user_properties
    assert ("ijt_reason_code", "manifest_changed") in item.user_properties


@pytest.mark.parametrize("marker_name", ["requires_cu", "requires_dependency_cu"])
def test_unreviewed_cu_never_starts_a_test_or_becomes_unsupported(monkeypatch, marker_name):
    monkeypatch.setattr(conftest, "_SUPPORTED_CUS", frozenset({"basic_result"}))
    monkeypatch.setattr(conftest, "_UNREVIEWED_CUS", frozenset({"future_cu"}))
    config = SimpleNamespace(stash={})
    item = SimpleNamespace(
        config=config,
        user_properties=[],
        iter_markers=lambda name: [SimpleNamespace(args=("future_cu",))] if name == marker_name else [],
    )
    with pytest.raises(pytest.skip.Exception, match="unreviewed"):
        conftest.pytest_runtest_setup(item)
    assert ("ijt_outcome", "untested") in item.user_properties
    assert ("ijt_reason_code", "cu_unreviewed") in item.user_properties


def test_direct_pytest_does_not_replace_a_supplied_review_hash(reviewed_config, monkeypatch):
    config, path = reviewed_config
    monkeypatch.setenv("OPCUA_TARGET_MANIFEST_SHA256", manifest_file_sha256(path))
    path.write_text(path.read_text() + "# Owner changed the manifest after runner review.\n")
    with pytest.raises(pytest.UsageError, match="changed"):
        conftest.pytest_configure(config)


def test_manifest_path_changes_are_blocked(reviewed_config, monkeypatch):
    config, path = reviewed_config
    conftest.pytest_configure(config)
    monkeypatch.setenv("OPCUA_TARGET_SERVER_PROFILE", str(path.parent / "another.yaml"))
    issue = conftest._manifest_review_issue(config)
    assert issue is not None
    assert "Selected SUT manifest changed" in issue


def test_direct_pytest_releases_only_its_own_review_hash(reviewed_config, monkeypatch):
    config, _ = reviewed_config
    monkeypatch.setenv("OPCUA_TARGET_MANIFEST_SHA256", "")
    conftest.pytest_configure(config)
    assert os.environ.get("OPCUA_TARGET_MANIFEST_SHA256")
    conftest.pytest_unconfigure(config)
    assert "OPCUA_TARGET_MANIFEST_SHA256" not in os.environ
    conftest.pytest_configure(config)
    monkeypatch.setenv("OPCUA_TARGET_MANIFEST_SHA256", "another-session")
    conftest.pytest_unconfigure(config)
    assert os.environ["OPCUA_TARGET_MANIFEST_SHA256"] == "another-session"


async def test_direct_node_call_blocks_an_edit_inside_a_running_test(reviewed_config, monkeypatch):
    from helpers.cu_coverage_report import WorkflowEvidenceUnavailable

    config, path = reviewed_config
    conftest.pytest_configure(config)
    rpc = AsyncMock(return_value="read result")
    monkeypatch.setattr(conftest.UANode, "call_method", rpc)
    monkeypatch.setattr("helpers.method_caller.is_target_method_call_authorized", lambda: True)
    guard = inspect.unwrap(conftest._guard_direct_target_method_calls)(monkeypatch, SimpleNamespace(config=config))
    next(guard)
    assert await conftest.UANode.call_method(object(), "method") == "read result"
    path.write_text(path.read_text() + "# Edited inside the running test.\n")
    with pytest.raises(WorkflowEvidenceUnavailable) as result:
        await conftest.UANode.call_method(object(), "method")
    assert result.value.ijt_properties["ijt_outcome"] == "blocked"
    assert result.value.ijt_properties["ijt_reason_code"] == "manifest_changed"
    rpc.assert_awaited_once()
    guard.close()


@pytest.mark.parametrize("primary_excluded", [False, True])
def test_dependency_exclusion_does_not_mark_primary_cu_scope_excluded(monkeypatch, primary_excluded):
    monkeypatch.setattr(conftest, "_SUPPORTED_CUS", frozenset({"primary", "dependency"}))
    monkeypatch.setattr(
        conftest,
        "_WORKFLOW_EXCLUDED_CUS",
        frozenset({"primary"} if primary_excluded else {"dependency"}),
    )
    markers = {
        "requires_cu": [SimpleNamespace(args=("primary",))],
        "requires_dependency_cu": [SimpleNamespace(args=("dependency",))],
    }
    item = SimpleNamespace(
        config=SimpleNamespace(stash={}), user_properties=[], iter_markers=lambda name: markers[name]
    )
    with pytest.raises(pytest.skip.Exception):
        conftest.pytest_runtest_setup(item)
    assert (("ijt_scope_excluded", "true") in item.user_properties) is primary_excluded
