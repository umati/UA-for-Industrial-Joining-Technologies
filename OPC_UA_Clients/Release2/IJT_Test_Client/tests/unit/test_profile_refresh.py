"""Offline contracts for reviewed process refresh; no controller is contacted."""

from __future__ import annotations

import importlib
import stat
import sys
from pathlib import Path
from unittest.mock import AsyncMock, Mock

import pytest
import yaml

from helpers.profile_refresh import guide_process_refresh, parse_refresh_manifest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
_RUNNER = importlib.import_module("run_all_tests")
_SOURCE = """# Owner comments and unrelated settings must survive.
schema_version: 1
name: Refresh test
lifecycle:
  mode: external
connection:
  endpoint: opc.tcp://controller:40451
authentication:
  source: anonymous
capability_claims:
  cu_overrides: {Asset_Identification: unsupported}
workflows:
  approved: [counter_intervention]
  process_selector:
    policy: first_compatible
  process_selectors_by_classification:
    job:
      policy: exact_match
      match_by: joining_process_id
      joining_process_id: old-job # Keep this comment.
      joining_process_origin_id: old-origin
      selection_name: old-selection
      identifier_strategy: id_only
execution_policy:
  state_changing_methods:
    allowed_methods: [IncrementJoiningProcessCounter]
  counter_effects:
    - method: IncrementJoiningProcessCounter
      count: 1
      process_policy: exact_match
      joining_process_id: old-job
      expected_result_classification: batch
  intervention:
    method: IncrementJoiningProcessCounter
    parent_process:
      match_by: joining_process_origin_id
      joining_process_origin_id: old-origin
"""
_PROCESS = {
    "id": "new-job",
    "origin_id": "new-origin",
    "selection_name": "new-selection",
    "name": "Sequence",
    "classification": 5,
}


@pytest.fixture
def profile(tmp_path):
    path = tmp_path / "controller.sut.yaml"
    path.write_bytes(_SOURCE.encode())
    return path


def _guide(path, answers, *, processes=None, prompt=None, emit=None):
    choices = iter(answers)
    return guide_process_refresh(
        path,
        path.read_bytes(),
        [_PROCESS] if processes is None else processes,
        prompt=prompt or (lambda _: next(choices)),
        emit=emit or (lambda _: None),
    )


@pytest.mark.parametrize("newline", ["\n", "\r\n"])
def test_job_counter_and_parent_are_reviewed_once_and_saved_together(profile, newline):
    original = _SOURCE.replace("\n", newline).encode()
    profile.write_bytes(original)
    output: list[str] = []
    assert _guide(profile, ["1", f"REFRESH {profile.name}"], emit=output.append) == 0
    updated = profile.read_bytes().decode()
    assert "# Keep this comment." in updated
    assert "# Owner comments and unrelated settings must survive." in updated
    assert updated.count("new-job") == 3
    assert updated.count("new-origin") == 2
    assert newline in updated
    if newline == "\r\n":
        assert b"\n" not in profile.read_bytes().replace(b"\r\n", b"")
    before = yaml.safe_load(original)
    after = yaml.safe_load(updated)
    before["workflows"]["process_selectors_by_classification"]["job"].update(
        joining_process_id="new-job", joining_process_origin_id="new-origin", selection_name="new-selection"
    )
    before["execution_policy"]["counter_effects"][0]["joining_process_id"] = "new-job"
    before["execution_policy"]["intervention"]["parent_process"].update(
        joining_process_id="new-job", joining_process_origin_id="new-origin"
    )
    assert before == after
    assert sum(line == "\nReferences updated together:" for line in output) == 1
    assert any(line.startswith("\n--- ") for line in output)
    parse_refresh_manifest(updated, profile)


@pytest.mark.parametrize("answers", [["q"], [""], ["1", "no"], ["1", "refresh controller.sut.yaml"]])
def test_cancellation_never_writes_or_creates_temporary_files(profile, answers):
    original = profile.read_bytes()
    assert _guide(profile, answers) == 1
    assert profile.read_bytes() == original
    assert list(profile.parent.iterdir()) == [profile]


def test_invalid_or_unavailable_keep_does_not_choose_first_process(profile):
    output: list[str] = []
    assert _guide(profile, ["k", "0", "999", "not-a-number", "q"], emit=output.append) == 1
    assert sum("Choose a listed process" in line for line in output) == 4
    assert profile.read_text() == _SOURCE


def test_current_catalog_can_be_kept_without_a_write(profile):
    source = _SOURCE.replace(
        "      match_by: joining_process_origin_id\n",
        "      match_by: joining_process_origin_id\n      joining_process_id: old-job\n",
    )
    profile.write_text(source)
    current = dict(_PROCESS, id="old-job", origin_id="old-origin", selection_name="old-selection")
    assert _guide(profile, ["k"], processes=[current]) == 0
    assert profile.read_text() == source


def test_same_process_id_groups_references_even_if_secondary_origin_is_stale(profile):
    source = _SOURCE.replace(
        "      joining_process_id: old-job\n      expected_result_classification",
        "      joining_process_id: old-job\n      joining_process_origin_id: stale-secondary\n"
        "      expected_result_classification",
    )
    profile.write_text(source)
    assert _guide(profile, ["1", f"REFRESH {profile.name}"]) == 0
    after = yaml.safe_load(profile.read_text())
    assert after["execution_policy"]["counter_effects"][0]["joining_process_origin_id"] == "new-origin"


def test_keep_cannot_preserve_conflicting_live_processes_in_one_group(profile):
    first = dict(_PROCESS, id="old-job", origin_id="different-origin", selection_name="old-selection")
    second = dict(_PROCESS, id="another-job", origin_id="old-origin", selection_name="another-selection")
    output: list[str] = []
    assert _guide(profile, ["k", "q"], processes=[first, second], emit=output.append) == 1
    assert any("Choose a listed process" in line for line in output)
    assert profile.read_text() == _SOURCE


def test_discovery_order_never_implicitly_selects_a_program(profile):
    program = dict(_PROCESS, id="program", origin_id="program-origin", name="Program", classification=2)
    assert _guide(profile, ["2", f"REFRESH {profile.name}"], processes=[program, _PROCESS]) == 0
    assert "program" not in profile.read_text()
    assert "new-job" in profile.read_text()


@pytest.mark.parametrize("processes", [[], [_PROCESS, dict(_PROCESS)]])
def test_empty_or_ambiguous_catalog_does_not_write(profile, processes):
    with pytest.raises(ValueError, match="no processes|ambiguous"):
        _guide(profile, ["1"], processes=processes)
    assert profile.read_text() == _SOURCE


def test_duplicate_selection_names_cannot_bypass_exact_matching(profile):
    source = _SOURCE.replace("match_by: joining_process_id", "match_by: selection_name")
    profile.write_text(source)
    other = dict(_PROCESS, id="different-job", selection_name="new-selection")
    with pytest.raises(ValueError, match="ambiguous"):
        _guide(profile, ["1"], processes=[_PROCESS, other])
    assert profile.read_text() == source


def test_missing_origin_cannot_relax_identifier_strategy(profile):
    source = _SOURCE.replace("identifier_strategy: id_only", "identifier_strategy: id_with_origin")
    profile.write_text(source)
    with pytest.raises(ValueError, match="lacks an identifier"):
        _guide(profile, ["1"], processes=[dict(_PROCESS, origin_id="")])
    assert profile.read_text() == source


def test_concurrent_profile_edit_is_preserved(profile):
    def answer(question):
        if question.startswith("Type REFRESH"):
            profile.write_text(_SOURCE + "# External edit.\n")
            return f"REFRESH {profile.name}"
        return "1"

    with pytest.raises(ValueError, match="Profile changed during review"):
        _guide(profile, [], prompt=answer)
    assert profile.read_text().endswith("# External edit.\n")
    assert list(profile.parent.iterdir()) == [profile]


def test_failed_atomic_replace_preserves_profile_and_cleans_only_its_temporary_file(profile, monkeypatch):
    from helpers import profile_refresh

    def fail_replace(*_):
        raise PermissionError("File is in use")

    monkeypatch.setattr(profile_refresh.os, "replace", fail_replace)
    with pytest.raises(PermissionError, match="File is in use"):
        _guide(profile, ["1", f"REFRESH {profile.name}"])
    assert profile.read_text() == _SOURCE
    assert list(profile.parent.iterdir()) == [profile]


def test_read_only_profile_is_not_replaced_or_left_with_temporary_files(profile):
    profile.chmod(stat.S_IREAD)
    try:
        with pytest.raises(PermissionError, match="read-only"):
            _guide(profile, ["1", f"REFRESH {profile.name}"])
    finally:
        profile.chmod(stat.S_IREAD | stat.S_IWRITE)
    assert profile.read_text() == _SOURCE
    assert list(profile.parent.iterdir()) == [profile]


def test_unrelated_current_process_reference_is_not_rewritten(profile):
    source = _SOURCE.replace(
        "    policy: first_compatible",
        "    policy: exact_match\n    joining_process_id: other-job",
    )
    profile.write_text(source)
    other = dict(_PROCESS, id="other-job", origin_id="other-origin", selection_name="other-selection")
    assert _guide(profile, ["k", "2", f"REFRESH {profile.name}"], processes=[other, _PROCESS]) == 0
    after = yaml.safe_load(profile.read_text())
    assert after["workflows"]["process_selector"]["joining_process_id"] == "other-job"
    assert after["workflows"]["process_selectors_by_classification"]["job"]["joining_process_id"] == "new-job"


def test_cancel_after_earlier_group_review_never_saves_a_partial_refresh(profile):
    source = _SOURCE.replace(
        "    policy: first_compatible",
        "    policy: exact_match\n    joining_process_id: other-job",
    )
    profile.write_text(source)
    assert _guide(profile, ["1", "q"]) == 1
    assert profile.read_text() == source


def test_shared_name_cannot_merge_distinct_process_identities(profile):
    source = _SOURCE.replace(
        "    policy: first_compatible",
        "    policy: exact_match\n    joining_process_id: other-job\n    selection_name: old-selection",
    ).replace(
        "      joining_process_id: old-job\n      expected_result_classification",
        "      match_by: selection_name\n      selection_name: old-selection\n      expected_result_classification",
    )
    profile.write_text(source)
    with pytest.raises(ValueError, match="Ambiguous related references"):
        _guide(profile, [])
    assert profile.read_text() == source


def test_shared_origin_does_not_group_distinct_selection_names():
    from helpers.profile_refresh import _reference_groups

    selectors = {
        role: {
            "policy": "exact_match",
            "match_by": "selection_name",
            "joining_process_origin_id": "shared-origin",
            "selection_name": name,
        }
        for role, name in (("single", "Program"), ("job", "Sequence"))
    }
    groups = _reference_groups({"workflows": {"process_selectors_by_classification": selectors}})
    assert [len(group) for group in groups] == [1, 1]


@pytest.mark.parametrize("order", [(0, 1, 2), (1, 0, 2), (2, 0, 1)])
@pytest.mark.parametrize("bridge_key", ["joining_process_origin_id", "selection_name"])
def test_secondary_only_transitive_bridge_stays_in_separate_review_groups(order, bridge_key):
    from helpers.profile_refresh import _reference_groups

    selectors = [
        {"match_by": "joining_process_origin_id", "joining_process_origin_id": "origin"},
        {"match_by": bridge_key, "joining_process_origin_id": "origin", "selection_name": "name"},
        {"match_by": "selection_name", "selection_name": "name"},
    ]
    raw = {"execution_policy": {"counter_effects": [selectors[index] for index in order]}}
    groups = _reference_groups(raw)
    assert sorted(len(group) for group in groups) == [1, 2]
    assert all(len({item.selector["match_by"] for item in group}) == 1 for group in groups)


@pytest.mark.parametrize("reverse", [False, True])
def test_origin_only_reference_cannot_absorb_a_selection_name_match(reverse):
    from helpers.profile_refresh import _reference_groups

    selectors = [
        {"match_by": "joining_process_origin_id", "joining_process_origin_id": "shared"},
        {"match_by": "selection_name", "joining_process_origin_id": "shared", "selection_name": "Job_2"},
    ]
    if reverse:
        selectors.reverse()
    groups = _reference_groups({"execution_policy": {"counter_effects": selectors}})
    assert [len(group) for group in groups] == [1, 1]


def test_secondary_references_can_group_when_both_active_matching_keys_are_shared():
    from helpers.profile_refresh import _reference_groups

    identity = {"joining_process_origin_id": "shared", "selection_name": "Job_2"}
    selectors = [
        {"match_by": "joining_process_origin_id", **identity},
        {"match_by": "selection_name", **identity},
    ]
    groups = _reference_groups({"execution_policy": {"counter_effects": selectors}})
    assert [len(group) for group in groups] == [2]


@pytest.mark.parametrize(
    "strategy,process",
    [
        ("selection_name_only", dict(_PROCESS, selection_name="")),
        ("all_available", dict(_PROCESS, origin_id="")),
        ("all_available", dict(_PROCESS, selection_name="")),
    ],
)
def test_refresh_requires_all_wire_strategy_identifiers(profile, strategy, process):
    source = _SOURCE.replace("identifier_strategy: id_only", f"identifier_strategy: {strategy}")
    profile.write_text(source)
    with pytest.raises(ValueError, match="lacks an identifier"):
        _guide(profile, ["1"], processes=[process])
    assert profile.read_text() == source


def test_selection_name_only_rejects_duplicate_wire_identity_even_when_id_matches(profile):
    source = _SOURCE.replace("identifier_strategy: id_only", "identifier_strategy: selection_name_only")
    profile.write_text(source)
    with pytest.raises(ValueError, match="ambiguous"):
        _guide(profile, ["1"], processes=[_PROCESS, dict(_PROCESS, id="other")])
    assert profile.read_text() == source


def test_selection_name_only_checks_all_associated_names_not_just_the_displayed_name(profile):
    source = _SOURCE.replace("identifier_strategy: id_only", "identifier_strategy: selection_name_only")
    profile.write_text(source)
    other = dict(
        _PROCESS,
        id="other",
        selection_name="displayed-other-name",
        AssociatedEntities=[{"Name": "SelectionName", "EntityId": _PROCESS["selection_name"]}],
    )
    with pytest.raises(ValueError, match="ambiguous"):
        _guide(profile, ["1"], processes=[_PROCESS, other])
    assert profile.read_text() == source


@pytest.mark.parametrize("configured_name", ["old-selection", "stale-name"])
@pytest.mark.parametrize(
    "strategy", ["id_only", "id_with_origin", "selection_name_only", "id_with_selection_name", "all_available"]
)
def test_multiple_advertised_names_require_an_explicit_current_wire_name(configured_name, strategy):
    from helpers.profile_refresh import ProcessReference, _updated_identifiers

    reference = ProcessReference(
        ("selector",),
        {"identifier_strategy": strategy, "selection_name": configured_name},
    )
    process = dict(
        _PROCESS,
        AssociatedEntities=[{"Name": "SelectionName", "EntityId": "old-selection"}],
    )
    if configured_name == "old-selection":
        assert _updated_identifiers(reference, process, [process])["selection_name"] == "old-selection"
    else:
        with pytest.raises(ValueError, match="one advertised name or an explicit advertised name"):
            _updated_identifiers(reference, process, [process])


@pytest.mark.parametrize("strategy", ["selection_name_only", "id_with_selection_name", "all_available"])
def test_unique_associated_name_refreshes_a_stale_alias_without_a_scalar_name(strategy):
    from helpers.profile_refresh import ProcessReference, _updated_identifiers

    reference = ProcessReference(("selector",), {"identifier_strategy": strategy, "selection_name": "stale"})
    process = dict(
        _PROCESS,
        selection_name="",
        AssociatedEntities=[{"Name": "SelectionName", "EntityId": "OnlyAlias"}],
    )
    assert _updated_identifiers(reference, process, [process])["selection_name"] == "OnlyAlias"


def test_selection_name_match_cannot_guess_an_alias_even_when_no_name_was_saved():
    from helpers.profile_refresh import ProcessReference, _updated_identifiers

    reference = ProcessReference(("selector",), {"match_by": "selection_name"})
    process = dict(
        _PROCESS,
        AssociatedEntities=[{"Name": "SelectionName", "EntityId": "other-alias"}],
    )
    with pytest.raises(ValueError, match="advertised names:"):
        _updated_identifiers(reference, process, [process])


@pytest.mark.parametrize("strategy", ["id_only", "id_with_origin"])
def test_unused_aliases_do_not_block_identifier_only_refresh(strategy):
    from helpers.profile_refresh import ProcessReference, _updated_identifiers

    reference = ProcessReference(("selector",), {"identifier_strategy": strategy})
    process = dict(
        _PROCESS,
        AssociatedEntities=[{"Name": "SelectionName", "EntityId": "other-alias"}],
    )
    updated = _updated_identifiers(reference, process, [process])
    assert updated["joining_process_id"] == _PROCESS["id"]
    assert "selection_name" not in updated


def test_catalog_displays_all_aliases_before_operator_selection(profile):
    process = dict(
        _PROCESS,
        AssociatedEntities=[{"Name": "SelectionName", "EntityId": "hidden-alias"}],
    )
    output: list[str] = []
    assert _guide(profile, ["q"], processes=[process], emit=output.append) == 1
    assert any('SelectionNames=["hidden-alias", "new-selection"]' in line for line in output)
    assert profile.read_text() == _SOURCE


def test_all_available_adds_missing_secondary_fields_without_changing_strategy(profile):
    source = _SOURCE.replace("identifier_strategy: id_only", "identifier_strategy: all_available").replace(
        "      joining_process_origin_id: old-origin\n      selection_name: old-selection\n", ""
    )
    profile.write_text(source)
    assert _guide(profile, ["1", "1", f"REFRESH {profile.name}"]) == 0
    selector = yaml.safe_load(profile.read_text())["workflows"]["process_selectors_by_classification"]["job"]
    assert selector["joining_process_origin_id"] == "new-origin"
    assert selector["selection_name"] == "new-selection"
    assert selector["identifier_strategy"] == "all_available"


@pytest.mark.parametrize(
    "strategy", ["id_with_origin", "id_with_selection_name", "selection_name_only", "all_available"]
)
def test_keep_cannot_preserve_stale_secondary_identifiers(profile, strategy):
    source = (
        "schema_version: 1\nname: Test\nlifecycle: {mode: external}\n"
        "connection: {endpoint: 'opc.tcp://controller:40451'}\nauthentication: {source: anonymous}\n"
        "workflows:\n  process_selector:\n    policy: exact_match\n    joining_process_id: new-job\n"
        f"    identifier_strategy: {strategy}\n"
        "    joining_process_origin_id: stale-origin\n    selection_name: stale-selection\n"
    )
    profile.write_text(source)
    output: list[str] = []
    assert _guide(profile, ["k", "q"], emit=output.append) == 1
    assert any("Choose a listed process" in line for line in output)
    assert profile.read_text() == source


@pytest.mark.parametrize(
    "source",
    [
        _SOURCE + "name: duplicate\n",
        _SOURCE.replace("job:\n", "job: &job_selector\n"),
        _SOURCE.replace("job:\n", "job: &job_selector\n") + "other: *job_selector\n",
    ],
)
def test_ambiguous_yaml_or_aliases_are_not_edited(profile, source):
    profile.write_text(source)
    with pytest.raises(ValueError, match="unique scalar|anchors/aliases"):
        _guide(profile, [])
    assert profile.read_text() == source


def test_missing_id_is_added_to_flow_selector_without_reformatting(profile):
    source = (
        "schema_version: 1\nname: Test\nlifecycle: {mode: external}\n"
        "connection: {endpoint: 'opc.tcp://controller:40451'}\nauthentication: {source: anonymous}\n"
        "workflows:\n"
        "  process_selector: {policy: exact_match, match_by: selection_name, selection_name: old-selection}\n"
    )
    profile.write_text(source)
    assert _guide(profile, ["1", f"REFRESH {profile.name}"]) == 0
    assert "lifecycle: {mode: external}" in profile.read_text()
    selector = yaml.safe_load(profile.read_text())["workflows"]["process_selector"]
    assert selector["joining_process_id"] == "new-job"
    assert selector["match_by"] == "selection_name"


def test_catalog_strings_are_quoted_not_interpreted_as_yaml(profile):
    process = dict(_PROCESS, id="true", origin_id="123", selection_name="x\nexecution_policy: {}")
    assert _guide(profile, ["1", f"REFRESH {profile.name}"], processes=[process]) == 0
    after = yaml.safe_load(profile.read_text())
    selector = after["workflows"]["process_selectors_by_classification"]["job"]
    assert selector["joining_process_id"] == "true"
    assert selector["joining_process_origin_id"] == "123"
    assert selector["selection_name"] == "x\nexecution_policy: {}"
    assert after["execution_policy"]["counter_effects"][0]["count"] == 1


def test_no_exact_selectors_need_no_prompt_or_file_write(profile):
    source = (
        "schema_version: 1\nname: Test\nlifecycle: {mode: external}\n"
        "connection: {endpoint: 'opc.tcp://controller:40451'}\nauthentication: {source: anonymous}\n"
        "workflows: null\n"
    )
    profile.write_text(source)
    assert _guide(profile, [], processes=[]) == 0
    assert profile.read_text() == source


def test_block_scalar_identifiers_stop_instead_of_damaging_neighboring_fields(profile):
    source = _SOURCE.replace(
        "joining_process_id: old-job # Keep this comment.", "joining_process_id: |-\n        old-job"
    )
    profile.write_text(source)
    with pytest.raises(ValueError, match="block scalar"):
        _guide(profile, ["1"])
    assert profile.read_text() == source


@pytest.fixture
def refresh_cli(profile, monkeypatch):
    from helpers import profile_refresh, target_server_execution

    monkeypatch.setattr(_RUNNER.sys.stdin, "isatty", lambda: True)
    relaunch = Mock()
    monkeypatch.setattr(_RUNNER, "_relaunch_if_needed", relaunch)
    install = Mock(side_effect=AssertionError("Refresh must not sync or clean environments"))
    monkeypatch.setattr(_RUNNER, "ensure_venv", install)
    monkeypatch.setattr(_RUNNER, "install_requirements", install)
    discovery = AsyncMock(return_value={"processes": [_PROCESS], "tools": [{"product_instance_uri": "tool"}]})
    monkeypatch.setattr(target_server_execution, "async_discover_target_server", discovery)
    guide = Mock(return_value=0)
    monkeypatch.setattr(profile_refresh, "guide_process_refresh", guide)
    return discovery, guide, relaunch


def test_refresh_subcommand_uses_manifest_security_and_only_discovery(profile, refresh_cli):
    discovery, guide, relaunch = refresh_cli
    source = _SOURCE.replace("source: anonymous", "source: environment\n  password_env_var: IJT_TEST_PASSWORD")
    profile.write_bytes(source.encode())
    assert _RUNNER._handle_subcommands(["refresh-profile", "--profile", str(profile)]) == 0
    discovery.assert_awaited_once()
    assert discovery.call_args.args == ("opc.tcp://controller:40451",)
    assert discovery.call_args.kwargs["security"].auth_source == "environment"
    assert discovery.call_args.kwargs["security"].password_env_var == "IJT_TEST_PASSWORD"
    assert discovery.call_args.kwargs["expected_tool_uri"] == ""
    assert guide.call_args.args[:2] == (profile.resolve(), source.encode())
    relaunch.assert_called_once()


def test_refresh_requests_configured_nonfirst_tool(profile, refresh_cli):
    discovery, guide, _ = refresh_cli
    profile.write_text(
        _SOURCE.replace("workflows:\n", "workflows:\n  tool_selector: {product_instance_uri: second-tool}\n")
    )
    discovery.return_value = {"processes": [_PROCESS], "tools": [{"product_instance_uri": "second-tool"}]}
    assert _RUNNER._subcommand_refresh_profile(str(profile)) == 0
    assert discovery.call_args.kwargs["expected_tool_uri"] == "second-tool"
    guide.assert_called_once()


def test_refresh_noninteractive_fails_before_discovery(profile, refresh_cli, monkeypatch):
    discovery, guide, relaunch = refresh_cli
    monkeypatch.setattr(_RUNNER.sys.stdin, "isatty", lambda: False)
    assert _RUNNER._subcommand_refresh_profile(str(profile)) == 2
    discovery.assert_not_called()
    guide.assert_not_called()
    relaunch.assert_not_called()


def test_main_routes_refresh_without_environment_cleanup_or_test_workloads(profile, refresh_cli, monkeypatch):
    discovery, guide, _ = refresh_cli
    monkeypatch.setattr(_RUNNER.sys, "argv", ["run_all_tests.py", "refresh-profile", "--profile", str(profile)])
    monkeypatch.setattr(_RUNNER, "_cleanup_caches", Mock(side_effect=AssertionError("Must not clean evidence")))
    monkeypatch.setattr(_RUNNER, "_step_target_run", Mock(side_effect=AssertionError("Must not run tests")))
    assert _RUNNER.main() == 0
    discovery.assert_awaited_once()
    guide.assert_called_once()


@pytest.mark.parametrize(
    "source",
    [
        _SOURCE.replace("mode: external", "mode: auto_simulator"),
        _SOURCE.replace("opc.tcp://controller:40451", "opc.tcp://<controller>:40451"),
    ],
)
def test_refresh_requires_actual_external_profile_before_discovery(profile, refresh_cli, source):
    discovery, guide, _ = refresh_cli
    profile.write_text(source)
    assert _RUNNER._subcommand_refresh_profile(str(profile)) == 2
    discovery.assert_not_called()
    guide.assert_not_called()
    assert profile.read_text() == source


@pytest.mark.parametrize("failure", ["error", "exception", "wrong-tool", "no-tool"])
def test_failed_discovery_cannot_reach_the_save_guide(profile, refresh_cli, failure):
    discovery, guide, _ = refresh_cli
    if failure == "error":
        discovery.return_value = {"error": "GetJoiningProcessList unavailable"}
    elif failure == "exception":
        discovery.side_effect = TimeoutError("Discovery timed out")
    elif failure == "no-tool":
        discovery.return_value = {"processes": [_PROCESS], "tools": []}
    else:
        profile.write_text(
            _SOURCE.replace("workflows:\n", "workflows:\n  tool_selector: {product_instance_uri: expected}\n")
        )
        discovery.return_value = {"processes": [_PROCESS], "tools": [{"product_instance_uri": "other"}]}
    before = profile.read_bytes()
    assert _RUNNER._subcommand_refresh_profile(str(profile)) == 2
    guide.assert_not_called()
    assert profile.read_bytes() == before


def test_cli_cancellation_does_not_start_a_test_run(profile, refresh_cli):
    _, guide, _ = refresh_cli
    guide.side_effect = EOFError
    assert _RUNNER._subcommand_refresh_profile(str(profile)) == 1
    assert profile.read_text() == _SOURCE
