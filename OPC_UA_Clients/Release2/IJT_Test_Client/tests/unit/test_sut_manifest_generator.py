"""
Unit tests for scripts/generate_sut_manifest_docs.py

The committed template, example manifests, and Markdown field reference are
generated from the schema metadata. These tests guard freshness (``--check``
drift mode) so a schema change cannot land without regenerating the artifacts.
No OPC UA server required.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
import yaml

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_SCRIPTS_DIR = _PROJECT_ROOT / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

import generate_sut_manifest_docs as generator  # noqa: E402

from helpers.sut_manifest import (  # noqa: E402
    MANIFEST_SUFFIX,
    annotate_local_manifest,
    preset_names,
    render_manifest_yaml,
)


@pytest.mark.parametrize("flow", [False, True])
def test_complete_local_cu_table_preserves_scope_settings_and_owner_notes(flow):
    from helpers.profile_loader import load_all_cus_from_facets, resolve_claimed_cus
    from helpers.sut_manifest import parse_sut_manifest

    source = render_manifest_yaml("remote_start_multi_operation")
    data = yaml.safe_load(source)
    data["capability_claims"].pop("cu_scope_policy")
    data["capability_claims"]["cu_overrides"] = {} if flow else {"get_result_by_id": "manual_required"}
    source = yaml.safe_dump(data, sort_keys=False)
    source = source.replace("cu_overrides:", "# Owner note: approved scope.\n  cu_overrides:")
    before = parse_sut_manifest(yaml.safe_load(source))
    result = generator.complete_local_cu_table(source)
    after = parse_sut_manifest(yaml.safe_load(result))
    assert set(after.capability_claims.cu_overrides) == load_all_cus_from_facets()
    assert list(after.capability_claims.cu_overrides) == sorted(after.capability_claims.cu_overrides)
    assert resolve_claimed_cus(before.capability_claims) == resolve_claimed_cus(after.capability_claims)
    assert before.to_execution_profile() == after.to_execution_profile()
    assert "# Owner note: approved scope." in result
    assert generator.complete_local_cu_table(result) == result
    if not flow:
        assert after.capability_claims.cu_overrides["get_result_by_id"] == "manual_required"


def test_complete_local_cu_table_refuses_nonempty_flow_or_missing_mapping():
    head = (
        "schema_version: 1\nname: owner\nlifecycle:\n  mode: external\n"
        "connection:\n  endpoint: opc.tcp://localhost:40451\n"
        "authentication:\n  source: anonymous\n"
    )
    source = head + "capability_claims:\n  cu_overrides: {basic_result: supported}\n"
    with pytest.raises(ValueError, match="non-empty CU flow"):
        generator.complete_local_cu_table(source)
    with pytest.raises(ValueError, match="explicit capability_claims"):
        generator.complete_local_cu_table(head)


def test_complete_local_cli_saves_a_scope_preserving_table_and_is_idempotent(tmp_path):
    from helpers.profile_loader import resolve_claimed_cus
    from helpers.sut_manifest import parse_sut_manifest

    path = tmp_path / "controller.local.yaml"
    data = yaml.safe_load(render_manifest_yaml("remote_start_multi_operation"))
    data["capability_claims"].pop("cu_scope_policy")
    data["capability_claims"]["cu_overrides"] = {"get_result_by_id": "manual_required"}
    original = yaml.safe_dump(data, sort_keys=False)
    path.write_text(original, encoding="utf-8")
    before = parse_sut_manifest(data)
    assert generator.main(["--complete-local-cus", str(path)]) == 0
    saved = path.read_bytes()
    after = parse_sut_manifest(yaml.safe_load(saved))
    assert resolve_claimed_cus(before.capability_claims) == resolve_claimed_cus(after.capability_claims)
    assert before.to_execution_profile() == after.to_execution_profile()
    assert after.capability_claims.cu_overrides["get_result_by_id"] == "manual_required"
    assert generator.main(["--complete-local-cus", str(path)]) == 0
    assert path.read_bytes() == saved


def test_rendering_keeps_omitted_optional_counter_restrictions_compatible(monkeypatch):
    from helpers import sut_manifest

    data = sut_manifest.preset_data("remote_start_multi_operation")
    effect = data["execution_policy"]["counter_effects"][0]
    for key in ("match_by", "joining_process_id", "joining_process_origin_id", "selection_name"):
        del effect[key]
    before = sut_manifest.parse_sut_manifest(data).to_execution_profile()
    monkeypatch.setattr(sut_manifest, "preset_data", lambda name: data)
    rendered = sut_manifest.render_manifest_yaml("remote_start_multi_operation")
    after = sut_manifest.parse_sut_manifest(yaml.safe_load(rendered)).to_execution_profile()
    assert after == before
    assert yaml.safe_load(rendered)["execution_policy"]["counter_effects"][0] == effect


def test_local_guidance_check_accepts_labelled_notes_and_refuses_duplicates(tmp_path):
    source = render_manifest_yaml("remote_start_multi_operation")
    assert not generator.local_guidance_errors(source)
    source = source.replace("\nname:", "\n# Local note: installation label.\nname:", 1)
    assert not generator.local_guidance_errors(source)
    bad = source.replace(
        "# Human-readable SUT name used in reports.",
        "# Human-readable SUT name used in reports.\n# Duplicate explanation.",
    )
    path = tmp_path / "controller.local.yaml"
    path.write_text(bad, encoding="utf-8")
    saved = path.read_bytes()
    assert generator.main(["--check-local", str(path)]) == 1
    assert path.read_bytes() == saved
    path.write_text(source, encoding="utf-8")
    assert generator.main(["--check-local", str(path)]) == 0
    assert generator.local_guidance_errors(source.replace("installation label.", "installation label;"))


@pytest.mark.parametrize("newline", ["\n", "\r\n"])
def test_local_layout_matches_generated_spacing_and_counter_list_style(newline):
    source = render_manifest_yaml("remote_start_multi_operation")
    altered = source.replace("\n\n", "\n").replace("    -\n", "")
    altered = altered.replace(
        "      method: IncrementJoiningProcessCounter",
        "    - method: IncrementJoiningProcessCounter",
        1,
    )
    source = source.replace("\n", newline)
    altered = altered.replace("\n", newline)
    assert yaml.safe_load(altered) == yaml.safe_load(source)
    assert generator.format_local_manifest(altered) == source
    assert generator.format_local_manifest(source) == source
    assert generator.local_guidance_errors(altered)


@pytest.mark.parametrize("style", ["|", ">"])
def test_local_layout_preserves_multiline_values_and_labelled_notes(style):
    source = render_manifest_yaml("remote_start_multi_operation")
    root = yaml.compose(source)
    assert isinstance(root, yaml.MappingNode)
    key, value = next((key, value) for key, value in root.value if key.value == "description")
    lines = source.splitlines(keepends=True)
    lines[key.start_mark.line : value.end_mark.line + bool(value.end_mark.column)] = [
        f"# Local note: retain the owner description.\ndescription: {style}\n"
        "  first line\n\n  # This is string content, not field guidance.\n\n  last line\n",
    ]
    source = "".join(lines)
    before = yaml.safe_load(source)
    formatted = generator.format_local_manifest(source)
    assert yaml.safe_load(formatted) == before
    assert "# Local note: retain the owner description." in formatted
    assert generator.format_local_manifest(formatted) == formatted


def test_completing_explicit_scope_never_decides_unreviewed_cus(monkeypatch):
    from helpers import profile_loader

    source = render_manifest_yaml("remote_start_multi_operation")
    catalogue = profile_loader.load_all_cus_from_facets() | {"future_cu"}
    monkeypatch.setattr(profile_loader, "load_all_cus_from_facets", lambda: catalogue)
    result = generator.complete_local_cu_table(source)
    assert "future_cu:" not in result


def test_guidance_refresh_consolidates_known_legacy_cu_text_without_repeated_policy():
    source = render_manifest_yaml("remote_start_multi_operation")
    old = (
        "    # Support declaration for abort_joining_process. Values: supported, unsupported, manual_required.\n"
        "    # When omitted: use the parent profile/map policy."
    )
    old_source = source.replace("    # Support for abort joining process.", old)
    refreshed = generator.format_local_manifest(old_source)
    assert yaml.safe_load(refreshed) == yaml.safe_load(source)
    assert not generator.local_guidance_errors(refreshed)
    assert "When omitted: use the parent profile/map policy." not in refreshed


def test_guidance_check_handles_marked_comments_and_detects_missing_fields():
    source = render_manifest_yaml("remote_start_multi_operation")
    assert not generator.local_guidance_errors(annotate_local_manifest(source))
    missing = (
        "\n".join(line for line in source.splitlines() if not line.startswith("  startup_timeout_seconds:")) + "\n"
    )
    assert any("lifecycle.startup_timeout_seconds" in error for error in generator.local_guidance_errors(missing))


class TestGeneratedArtifactSet:
    def test_every_preset_has_a_committed_manifest(self):
        assert set(generator.GENERATED_MANIFESTS) == set(preset_names())

    def test_artifacts_include_the_field_reference(self):
        artifacts = generator.build_artifacts()
        assert generator.FIELD_REFERENCE_PATH in artifacts
        assert len(artifacts) == len(preset_names()) + 1

    def test_committed_artifacts_exist(self):
        for path in generator.build_artifacts():
            assert path.exists(), f"{path.name} has not been generated"

    def test_manifest_paths_use_the_manifest_suffix(self):
        for path in generator.GENERATED_MANIFESTS.values():
            assert path.name.endswith(MANIFEST_SUFFIX)


class TestDriftDetection:
    def test_committed_artifacts_are_up_to_date(self):
        stale = generator.check_artifacts()
        assert not stale, (
            "Generated SUT manifest artifacts are stale: "
            f"{[path.name for path in stale]}. "
            "Run: python scripts/generate_sut_manifest_docs.py"
        )

    def test_check_mode_passes_for_fresh_artifacts(self, capsys):
        assert generator.main(["--check"]) == 0
        assert "up to date" in capsys.readouterr().out

    def test_check_mode_reports_a_stale_artifact(self, monkeypatch, tmp_path, capsys):
        missing = tmp_path / f"missing{MANIFEST_SUFFIX}"
        monkeypatch.setattr(generator, "build_artifacts", lambda: {missing: "content\n"})
        assert generator.main(["--check"]) == 1
        assert "out of date" in capsys.readouterr().out

    def test_check_mode_detects_modified_content(self, monkeypatch, tmp_path):
        drifted = tmp_path / f"drifted{MANIFEST_SUFFIX}"
        drifted.write_text("old\n", encoding="utf-8")
        monkeypatch.setattr(generator, "build_artifacts", lambda: {drifted: "new\n"})
        assert generator.check_artifacts() == [drifted]


class TestWriteMode:
    def test_write_creates_missing_artifacts(self, monkeypatch, tmp_path, capsys):
        target = tmp_path / "generated" / f"new{MANIFEST_SUFFIX}"
        monkeypatch.setattr(generator, "build_artifacts", lambda: {target: "generated\n"})
        assert generator.main([]) == 0
        assert target.read_text(encoding="utf-8") == "generated\n"
        assert "Updated 1 generated artifact" in capsys.readouterr().out

    def test_write_is_idempotent(self, monkeypatch, tmp_path, capsys):
        target = tmp_path / f"stable{MANIFEST_SUFFIX}"
        monkeypatch.setattr(generator, "build_artifacts", lambda: {target: "stable\n"})
        generator.main([])
        capsys.readouterr()
        assert generator.main([]) == 0
        assert "already up to date" in capsys.readouterr().out

    def test_write_artifacts_returns_changed_paths(self, monkeypatch, tmp_path):
        target = tmp_path / f"changed{MANIFEST_SUFFIX}"
        monkeypatch.setattr(generator, "build_artifacts", lambda: {target: "v1\n"})
        assert generator.write_artifacts() == [target]
        assert generator.write_artifacts() == []


class TestGeneratedContent:
    @pytest.mark.parametrize("preset", sorted(preset_names()))
    def test_generated_manifest_is_marked_generated(self, preset):
        text = generator.GENERATED_MANIFESTS[preset].read_text(encoding="utf-8")
        assert "GENERATED FILE" in text
        assert "generate_sut_manifest_docs.py" in text

    def test_field_reference_is_marked_generated(self):
        text = generator.FIELD_REFERENCE_PATH.read_text(encoding="utf-8")
        assert "GENERATED FILE" in text
        assert "| Field | Type | Required | Default | Allowed values | Description |" in text

    def test_every_yaml_field_has_consistent_guidance_within_its_schema(self):
        guidance: dict[tuple[str, ...], list[str]] = {}
        paths = [*generator.GENERATED_MANIFESTS.values(), *(_PROJECT_ROOT / "profiles").glob("*.yaml")]
        for path in paths:
            source = path.read_text(encoding="utf-8")
            lines = source.splitlines()

            def visit(node, parts=()):
                if isinstance(node, yaml.MappingNode):
                    for key, value in node.value:
                        comments: list[str] = []
                        index = key.start_mark.line - 1
                        while index >= 0 and lines[index].lstrip().startswith("#"):
                            comments.insert(0, lines[index].strip())
                            index -= 1
                        assert comments, f"{path.name}: {'.'.join((*parts, key.value))} has no field guidance"
                        context = ("facets", "[]") if len(parts) == 2 and parts[0] == "facets" else parts
                        identity = (path.parent.name, *context, key.value)
                        assert guidance.setdefault(identity, comments) == comments, (
                            f"{path.name}: inconsistent guidance for {'.'.join((*context, key.value))}"
                        )
                        visit(value, (*parts, key.value))
                elif isinstance(node, yaml.SequenceNode):
                    for value in node.value:
                        visit(value, (*parts, "[]"))

            visit(yaml.compose(source))


def test_local_formatting_orders_fields_and_preserves_values_and_owner_notes():
    source = render_manifest_yaml("remote_start_multi_operation")
    name = yaml.safe_load(source)["name"]
    source = source.replace(
        "schema_version: 1\n",
        'schema_version: 1\n# Owner note about the installation label.\nname: "Chosen local label"\n',
    ).replace(f"\nname: {name}", "", 1)
    start = source.index("\n  counter_effects:")
    block_start = source.rfind("\n\n", 0, start)
    end = source.index("\n  state_changing_methods:", start)
    block_end = source.rfind("\n\n", start, end)
    counter = source[block_start:block_end]
    source = source[:block_start] + source[block_end:]
    insertion = source.index("\n  request_results:")
    insertion = source.rfind("\n\n", 0, insertion)
    source = source[:insertion] + counter + source[insertion:]
    source = source.replace("\n", "\r\n")
    formatted = generator.format_local_manifest(annotate_local_manifest(source))
    assert yaml.safe_load(formatted) == yaml.safe_load(source)
    assert '"Chosen local label"\r\n' in formatted
    assert "# Owner note about the installation label.\r\n" in formatted
    assert formatted.index("counter_effects:") < formatted.index("state_changing_methods:")
    assert "\n" not in formatted.replace("\r\n", "")
    assert generator.format_local_manifest(formatted) == formatted


def test_format_local_cli_saves_only_comment_and_order_changes(tmp_path):
    path = tmp_path / "controller.local.yaml"
    original = render_manifest_yaml("remote_start_multi_operation")
    path.write_text(original, encoding="utf-8")
    assert generator.main(["--format-local", str(path)]) == 0
    assert yaml.safe_load(path.read_text()) == yaml.safe_load(original)


def test_format_local_refuses_edited_schema_blocks_before_saving(tmp_path):
    path = tmp_path / "controller.local.yaml"
    original = annotate_local_manifest(render_manifest_yaml("remote_start_multi_operation"))
    original = original.replace("# END SUT FIELD", "# END SUT FIELD owner note", 1)
    path.write_text(original, encoding="utf-8")
    with pytest.raises(ValueError, match="was edited"):
        generator.main(["--format-local", str(path)])
    assert path.read_text(encoding="utf-8") == original


def test_local_formatting_preserves_comment_like_block_scalar_content():
    source = (
        "schema_version: 1\n"
        "lifecycle:\n  mode: external\n"
        "connection:\n  endpoint: opc.tcp://localhost:40451\n"
        "authentication:\n  source: anonymous\n"
        "name: Local test controller\n"
        "description: |+\n  # This is description content, not a YAML comment.\n\n"
    )
    formatted = generator.format_local_manifest(source)
    assert yaml.safe_load(formatted) == yaml.safe_load(source)
    assert "description: |+\n  # This is description content, not a YAML comment.\n\n" in formatted
    assert formatted.index("description:") < formatted.index("lifecycle:")
    assert generator.format_local_manifest(formatted) == formatted
