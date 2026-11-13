"""
Generate the SUT manifest template, example manifests, and field reference.

Everything here is derived from the single authoritative schema metadata in
``helpers/sut_manifest.py`` (``MANIFEST_SCHEMA`` plus the built-in presets), so
the committed artifacts cannot drift away from the code that validates them.

Usage (from OPC_UA_Clients/Release2/IJT_Test_Client)::

    python scripts/generate_sut_manifest_docs.py            # write artifacts
    python scripts/generate_sut_manifest_docs.py --check    # fail on drift (CI/tests)
    python scripts/generate_sut_manifest_docs.py --format-local controller.local.yaml
    python scripts/generate_sut_manifest_docs.py --complete-local-cus controller.local.yaml
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from yaml.nodes import MappingNode, Node, ScalarNode, SequenceNode

TEST_CLIENT_ROOT = Path(__file__).resolve().parents[1]
if str(TEST_CLIENT_ROOT) not in sys.path:
    sys.path.insert(0, str(TEST_CLIENT_ROOT))

from helpers.sut_manifest import (
    MANIFEST_SCHEMA,
    MANIFEST_SUFFIX,
    SectionSpec,
    _comment_lines,
    _counter_field_specs,
    annotate_local_manifest,
    manifest_field_spec,
    manifest_field_specs,
    parse_sut_manifest,
    render_field_reference,
    render_manifest_yaml,
)

MANIFEST_DIR = TEST_CLIENT_ROOT / "target_server_cu_profiles"
DOCS_DIR = TEST_CLIENT_ROOT / "docs"

FIELD_REFERENCE_PATH = DOCS_DIR / "SUT_MANIFEST_REFERENCE.md"

#: preset name -> committed artifact path
GENERATED_MANIFESTS: dict[str, Path] = {
    "template": MANIFEST_DIR / f"template{MANIFEST_SUFFIX}",
    "simulator": MANIFEST_DIR / f"simulator{MANIFEST_SUFFIX}",
    "remote_start_multi_operation": MANIFEST_DIR / f"controller_remote_start{MANIFEST_SUFFIX}",
    "manual_trigger": MANIFEST_DIR / f"controller_manual_trigger{MANIFEST_SUFFIX}",
}


def build_artifacts() -> dict[Path, str]:
    """Return the full generated content for every artifact, keyed by target path."""
    artifacts: dict[Path, str] = {path: render_manifest_yaml(preset) for preset, path in GENERATED_MANIFESTS.items()}
    artifacts[FIELD_REFERENCE_PATH] = render_field_reference()
    return artifacts


def check_artifacts() -> list[Path]:
    """Return the artifact paths that are missing or out of date."""
    stale: list[Path] = []
    for path, expected in build_artifacts().items():
        if not path.exists() or path.read_text(encoding="utf-8") != expected:
            stale.append(path)
    return stale


def write_artifacts() -> list[Path]:
    """Write every artifact and return the paths that changed."""
    changed: list[Path] = []
    for path, expected in build_artifacts().items():
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists() or path.read_text(encoding="utf-8") != expected:
            path.write_text(expected, encoding="utf-8", newline="\n")
            changed.append(path)
    return changed


def _align_local_layout(source: str) -> str:
    """Use generated field spacing and mapping-list layout without rewriting scalar text."""
    from helpers.profile_refresh import _document

    newline = "\r\n" if "\r\n" in source else "\n"
    _, nodes = _document(source)
    lines = source.splitlines(keepends=True)
    edits: list[tuple[int, int, list[str]]] = []
    for node in nodes.values():
        if not isinstance(node, MappingNode) or node.flow_style or not node.value:
            continue
        key = node.value[0][0]
        index = key.start_mark.line
        prefix = lines[index][: key.start_mark.column]
        if prefix.strip() != "-":
            continue
        start = index
        indent = " " * key.start_mark.column
        while start and lines[start - 1].startswith(indent + "#"):
            start -= 1
        edits.append((index, index + 1, [indent + lines[index][key.start_mark.column :]]))
        edits.append((start, start, [prefix[: prefix.index("-")] + "-" + newline]))
    for start, stop, replacement in sorted(edits, key=lambda edit: (edit[0], edit[1]), reverse=True):
        lines[start:stop] = replacement
    source = "".join(lines)
    _, nodes = _document(source)
    protected: set[int] = set()
    block_ends: set[int] = set()
    for node in nodes.values():
        if isinstance(node, ScalarNode) and node.style in ("|", ">", '"', "'"):
            protected.update(range(node.start_mark.line + 1, node.end_mark.line + bool(node.end_mark.column)))
            if node.style in ("|", ">"):
                block_ends.add(node.end_mark.line + bool(node.end_mark.column) - 1)
    lines = source.splitlines(keepends=True)
    fixed = manifest_field_specs()
    edits = []
    for path, node in nodes.items():
        if not isinstance(node, MappingNode) or node.flow_style:
            continue
        for key, _ in node.value:
            field_path = tuple(str(part) for part in (*path, key.value))
            spec = manifest_field_spec(field_path)
            if spec is None:
                continue
            expected = _comment_lines(spec, " " * key.start_mark.column)
            if spec.default_value() == "section guidance" and len(field_path) == 1:
                border = "# " + "-" * 74
                expected = [border, *expected, border]
            start = key.start_mark.line
            actual: list[str] = []
            while start and len(actual) < len(expected):
                start -= 1
                if not lines[start].lstrip().startswith("# Local note:"):
                    actual.insert(0, lines[start].rstrip("\r\n"))
            if actual != expected:
                raise ValueError(f"Cannot locate shared comments for {'.'.join(field_path)}. Nothing saved.")
            while start and lines[start - 1].lstrip().startswith("# Local note:"):
                start -= 1
            blank = start
            while blank and blank - 1 not in protected and not lines[blank - 1].strip():
                blank -= 1
            separate = (
                ".".join(field_path) in fixed
                or spec.default_value() == "section guidance"
                or len(field_path) == 4
                and field_path[:2] == ("workflows", "process_selectors_by_classification")
            )
            preserve_scalar_end = blank == start and start - 1 in block_ends
            edits.append((blank, start, [newline] if separate and blank and not preserve_scalar_end else []))
    for start, stop, replacement in sorted(edits, key=lambda edit: (edit[0], edit[1]), reverse=True):
        lines[start:stop] = replacement
    return "".join(lines)


def format_local_manifest(source: str) -> str:
    """Consolidate verified schema prose and order fields without reserializing values."""
    from helpers.profile_refresh import _document

    original, _ = _document(source)
    result = annotate_local_manifest(source, compact=True)
    orders: dict[tuple[str | int, ...], list[str]] = {
        (): [spec.name for section in MANIFEST_SCHEMA if not section.name for spec in section.fields]
        + [section.name for section in MANIFEST_SCHEMA if section.name]
    }

    def section_order(section: SectionSpec, path: tuple[str | int, ...]) -> None:
        orders[path] = [spec.name for spec in section.fields] + [sub.name for sub in section.subsections]
        for sub in section.subsections:
            section_order(sub, (*path, sub.name))

    for section in MANIFEST_SCHEMA:
        if section.name:
            section_order(section, (section.name,))

    def content_end(node: Node) -> int:
        if isinstance(node, MappingNode) and node.value:
            return max(content_end(value) for _, value in node.value)
        if isinstance(node, SequenceNode) and node.value:
            return max(content_end(value) for value in node.value)
        return node.end_mark.line + bool(node.end_mark.column)

    while True:
        _, nodes = _document(result)
        lines = result.splitlines(keepends=True)
        for path, node in sorted(nodes.items(), key=lambda item: len(item[0]), reverse=True):
            if not isinstance(node, MappingNode) or node.flow_style:
                continue
            order = orders.get(path, [])
            if len(path) == 3 and path[:2] == ("workflows", "process_selectors_by_classification"):
                order = orders[("workflows", "process_selector")]
            if len(path) == 3 and path[:2] == ("execution_policy", "counter_effects"):
                order = [spec.name for spec in _counter_field_specs()]
            keys = [key.value for key, _ in node.value]
            if path == ("capability_claims", "cu_overrides"):
                order = sorted(keys)
            ordered = sorted(
                range(len(keys)), key=lambda index: order.index(keys[index]) if keys[index] in order else len(order)
            )
            if ordered == list(range(len(keys))):
                continue
            starts = []
            for key, _ in node.value:
                start = key.start_mark.line
                indent = " " * key.start_mark.column
                while start and (not lines[start - 1].strip() or lines[start - 1].startswith(indent + "#")):
                    start -= 1
                starts.append(start)
            end = node.end_mark.line
            minimum_end = content_end(node.value[-1][1])
            while end > minimum_end and (not lines[end - 1].strip() or lines[end - 1].lstrip().startswith("#")):
                end -= 1
            stops = [*starts[1:], end]
            chunks = ["".join(lines[start:stop]) for start, stop in zip(starts, stops)]
            lines[starts[0] : end] = ["".join(chunks[index] for index in ordered)]
            result = "".join(lines)
            if _document(result)[0] != original:
                raise ValueError("Field ordering changed YAML values. Nothing saved.")
            break
        else:
            result = _align_local_layout(result)
            if _document(result)[0] != original:
                raise ValueError("Layout alignment changed YAML values. Nothing saved.")
            return result


def complete_local_cu_table(source: str) -> str:
    """Add missing CU rows without changing scope, approvals or existing scalar text."""
    from helpers.profile_loader import complete_cu_overrides, resolve_claimed_cus
    from helpers.profile_refresh import _document

    original, nodes = _document(source)
    manifest = parse_sut_manifest(original)
    claims = manifest.capability_claims
    complete = complete_cu_overrides(claims)
    missing = complete.keys() - claims.cu_overrides.keys()
    if claims.cu_scope_policy == "explicit":
        return format_local_manifest(source)
    node = nodes.get(("capability_claims", "cu_overrides"))
    parent = nodes.get(("capability_claims",))
    if not isinstance(node, MappingNode) or not isinstance(parent, MappingNode):
        raise ValueError("Add an explicit capability_claims.cu_overrides mapping before completing its table.")
    if node.flow_style and node.value:
        raise ValueError("Expand the non-empty CU flow mapping before completing its table. Nothing saved.")
    key = next(key for key, _ in parent.value if key.value == "cu_overrides")
    newline = "\r\n" if "\r\n" in source else "\n"
    lines = source.splitlines(keepends=True)
    if node.flow_style:
        index = node.start_mark.line
        lines[index] = lines[index][: node.start_mark.column] + lines[index][node.end_mark.column :]
        insert_at = index + 1
    else:
        last = node.value[-1][1]
        insert_at = last.end_mark.line + bool(last.end_mark.column)
    indent = " " * (key.start_mark.column + 2)
    lines[insert_at:insert_at] = [f"{indent}{cu}: {complete[cu]}{newline}" for cu in sorted(missing)]
    result = "".join(lines)
    _, updated_nodes = _document(result)
    mode = updated_nodes.get(("capability_claims", "cu_scope_policy"))
    if mode is None:
        lines[insert_at + len(missing) : insert_at + len(missing)] = [
            f"{' ' * key.start_mark.column}cu_scope_policy: explicit{newline}"
        ]
    else:
        index = mode.start_mark.line
        lines[index] = lines[index][: mode.start_mark.column] + "explicit" + lines[index][mode.end_mark.column :]
    result = format_local_manifest("".join(lines))
    updated = parse_sut_manifest(_document(result)[0])
    if (
        resolve_claimed_cus(updated.capability_claims) != resolve_claimed_cus(claims)
        or updated.to_execution_profile() != manifest.to_execution_profile()
    ):
        raise ValueError("CU completion changed scope or execution settings. Nothing saved.")
    return result


def local_guidance_errors(source: str) -> list[str]:
    """Check shared field guidance without changing values or labelled local notes."""
    from helpers.profile_refresh import _document

    _, nodes = _document(source)
    # This verifies existing hashed blocks and protects owner edits.
    annotate_local_manifest(source)
    lines = source.splitlines()
    protected: set[int] = set()
    for node in nodes.values():
        if isinstance(node, ScalarNode) and node.style in ("|", ">", '"', "'"):
            protected.update(range(node.start_mark.line + 1, node.end_mark.line + bool(node.end_mark.column)))
    errors = []
    for field in manifest_field_specs():
        if tuple(field.split(".")) not in nodes:
            errors.append(f"{field}: shared field is missing, use the current template to review its default")
    for path, node in nodes.items():
        spec = manifest_field_spec(tuple(str(part) for part in path))
        if spec is None:
            continue
        index = node.start_mark.line
        # _document indexes values. Find their mapping key before examining its comments.
        parent = nodes.get(path[:-1])
        if not isinstance(parent, MappingNode):
            continue
        key = next(key for key, _ in parent.value if key.value == str(path[-1]))
        index = key.start_mark.line - 1
        comments: list[str] = []
        while index >= 0 and index not in protected and lines[index].lstrip().startswith("#"):
            line = lines[index].lstrip()
            if not line.startswith(("# Local note:", "# BEGIN SUT FIELD ", "# END SUT FIELD", "# ---")):
                comments.insert(0, line)
            index -= 1
        expected = [line.lstrip() for line in _comment_lines(spec, " " * key.start_mark.column)]
        if comments != expected:
            errors.append(f"{'.'.join(str(part) for part in path)}: shared guidance is missing, stale or duplicated")
    for index, line in enumerate(lines):
        if index not in protected and line.lstrip().startswith("#") and ";" in line:
            errors.append(f"line {index + 1}: use a comma or full stop in comments")
    marked = any(
        index not in protected and line.lstrip().startswith("# BEGIN SUT FIELD ") for index, line in enumerate(lines)
    )
    if not errors and not marked and _align_local_layout(source) != source:
        errors.append("Shared spacing or mapping-list layout differs. Use --format-local to align it.")
    return errors


def main(argv: list[str] | None = None) -> int:
    """CLI entry point. Returns a process exit code."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check-local",
        type=Path,
        help="Read-only check of shared field comments in one local manifest. Label owner notes with '# Local note:'.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Do not write anything. Exit non-zero when a committed artifact is stale.",
    )
    parser.add_argument(
        "--annotate-local",
        type=Path,
        help="Refresh schema comments in one local manifest without changing values or owner notes.",
    )
    parser.add_argument(
        "--format-local",
        type=Path,
        help="Consolidate schema comments and align local field order without changing values or owner notes.",
    )
    parser.add_argument(
        "--complete-local-cus",
        type=Path,
        help="List all CUs in one local manifest, preserving current scope, approvals and existing scalar text.",
    )
    args = parser.parse_args(argv)
    local_modes = (args.annotate_local, args.format_local, args.complete_local_cus, args.check_local)
    if any(path is not None for path in local_modes):
        if args.check or sum(path is not None for path in local_modes) != 1:
            parser.error("--check, --annotate-local, --format-local and --complete-local-cus are mutually exclusive")
        from helpers.profile_refresh import _save_profile

        path = next(path for path in local_modes if path is not None)
        assert path is not None
        original = path.read_bytes()
        import yaml

        from helpers.profile_loader import unreviewed_cus

        pending = sorted(unreviewed_cus(parse_sut_manifest(yaml.safe_load(original)).capability_claims))
        if pending:
            print("Unreviewed catalogue CUs remain disabled: " + ", ".join(pending))
            print(
                "Approved tests can continue. Newer catalogue coverage is INCOMPLETE until these entries are reviewed."
            )
        if args.check_local is not None:
            errors = local_guidance_errors(original.decode("utf-8"))
            if errors:
                print(f"{path.name}: local guidance needs review. Nothing changed.")
                for error in errors:
                    print(f"  - {error}")
                return 1
            print(f"{path.name}: shared guidance is current. Local values and notes were not changed.")
            return 0
        renderer = (
            complete_local_cu_table
            if args.complete_local_cus is not None
            else format_local_manifest
            if args.format_local is not None
            else annotate_local_manifest
        )
        updated = renderer(original.decode("utf-8")).encode("utf-8")
        if updated != original:
            _save_profile(path, original, updated)
        if args.complete_local_cus is not None:
            print("Local reviewed CU table aligned. Claimed scope, execution settings and owner notes preserved.")
        else:
            operation = (
                "comments and field order aligned" if args.format_local is not None else "schema comments refreshed"
            )
            print(f"Local {operation}. All YAML values and owner notes preserved.")
        return 0

    if args.check:
        stale = check_artifacts()
        if stale:
            print("Generated SUT manifest artifacts are out of date:")
            for path in stale:
                print(f"  - {path.relative_to(TEST_CLIENT_ROOT)}")
            print("Regenerate with: python scripts/generate_sut_manifest_docs.py")
            return 1
        print(f"All {len(build_artifacts())} generated SUT manifest artifacts are up to date.")
        return 0

    changed = write_artifacts()
    if changed:
        print(f"Updated {len(changed)} generated artifact(s):")
        for path in changed:
            print(f"  - {path.relative_to(TEST_CLIENT_ROOT)}")
    else:
        print("Generated SUT manifest artifacts already up to date.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
