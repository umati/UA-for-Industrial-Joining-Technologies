"""Operator-reviewed refresh of exact process references in one local manifest."""

from __future__ import annotations

import difflib
import json
import os
import stat
import tempfile
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from yaml.nodes import MappingNode, Node, ScalarNode, SequenceNode

from helpers.process_selectors import matching_processes, selection_names
from helpers.sut_manifest import SutManifest, parse_sut_manifest
from helpers.target_server_readiness import check_live_process_selectors

_IDENTIFIERS = {
    "joining_process_id": "id",
    "joining_process_origin_id": "origin_id",
    "selection_name": "selection_name",
}
type FieldPath = tuple[str | int, ...]


@dataclass(frozen=True)
class ProcessReference:
    """One exact process reference; its path addresses the original YAML."""

    path: FieldPath
    selector: Mapping[str, Any]

    @property
    def label(self) -> str:
        return ".".join(str(part) for part in self.path)


def _document(source: str) -> tuple[dict[str, Any], dict[FieldPath, Node]]:
    if any(getattr(event, "anchor", None) for event in yaml.parse(source)):
        raise ValueError("Refresh does not edit YAML anchors/aliases. Use explicit selector mappings.")
    nodes: dict[FieldPath, Node] = {}

    def visit(node: Node, path: FieldPath) -> None:
        nodes[path] = node
        if isinstance(node, MappingNode):
            keys: set[str] = set()
            for key, value in node.value:
                if not isinstance(key, ScalarNode) or key.value in keys or key.value == "<<":
                    raise ValueError("Refresh requires unique scalar YAML keys and no merge keys.")
                keys.add(key.value)
                visit(value, (*path, key.value))
        elif isinstance(node, SequenceNode):
            for index, value in enumerate(node.value):
                visit(value, (*path, index))

    root = yaml.compose(source)
    if not isinstance(root, MappingNode):
        raise ValueError("The profile must be a YAML mapping.")
    visit(root, ())
    return yaml.safe_load(source), nodes


def parse_refresh_manifest(source: str, path: Path) -> SutManifest:
    """Validate the actual snapshot, without the manifest loader's file cache."""
    raw, _ = _document(source)
    return parse_sut_manifest(raw, source_path=str(path))


def _reference_groups(raw: dict[str, Any]) -> list[list[ProcessReference]]:
    workflows = raw.get("workflows") or {}
    references = []
    default = workflows.get("process_selector") or {}
    if default.get("policy") == "exact_match":
        references.append(ProcessReference(("workflows", "process_selector"), default))
    for role, selector in (workflows.get("process_selectors_by_classification") or {}).items():
        if selector.get("policy") == "exact_match":
            references.append(ProcessReference(("workflows", "process_selectors_by_classification", role), selector))
    policy = raw.get("execution_policy") or {}
    references.extend(
        ProcessReference(("execution_policy", "counter_effects", index), effect)
        for index, effect in enumerate(policy.get("counter_effects", []))
    )
    parent = (policy.get("intervention") or {}).get("parent_process") or {}
    if any(parent.get(key) for key in _IDENTIFIERS):
        references.append(ProcessReference(("execution_policy", "intervention", "parent_process"), parent))

    def value(reference: ProcessReference, key: str) -> str:
        return str(reference.selector.get(key) or "").strip().casefold()

    def related(left: ProcessReference, right: ProcessReference) -> bool:
        if value(left, "joining_process_id") and value(right, "joining_process_id"):
            return value(left, "joining_process_id") == value(right, "joining_process_id")
        shared = [key for key in _IDENTIFIERS if value(left, key) and value(right, key)]
        if not value(left, "joining_process_id") and not value(right, "joining_process_id"):
            if any(item.selector.get("match_by", "joining_process_id") not in shared for item in (left, right)):
                return False
        return bool(shared) and all(value(left, key) == value(right, key) for key in shared)

    groups: list[list[ProcessReference]] = []
    for reference in references:
        matches = [group for group in groups if any(related(reference, other) for other in group)]
        if len(matches) > 1:
            raise ValueError(f"Ambiguous related references at {reference.label}; review their configured identities.")
        if matches:
            combined = [*matches[0], reference]
            identified = [item for item in combined if value(item, "joining_process_id")]
            if identified:
                ambiguous = len({value(item, "joining_process_id") for item in identified}) != 1 or any(
                    not any(related(item, anchor) for anchor in identified)
                    for item in combined
                    if not value(item, "joining_process_id")
                )
            else:
                ambiguous = any(not related(left, right) for left in combined for right in combined)
            if ambiguous:
                raise ValueError(
                    f"Ambiguous related references at {reference.label}; review their configured identities."
                )
            matches[0].append(reference)
        else:
            groups.append([reference])
    return groups


def _updated_identifiers(
    reference: ProcessReference, process: dict[str, Any], processes: list[dict[str, Any]]
) -> dict[str, str]:
    selector = reference.selector
    match_by = selector.get("match_by", "joining_process_id")
    strategy = selector.get("identifier_strategy", "id_only")
    required = {"joining_process_id", match_by}
    if strategy == "id_with_origin":
        required.add("joining_process_origin_id")
    elif strategy == "id_with_selection_name":
        required.add("selection_name")
    elif strategy == "selection_name_only":
        required.add("selection_name")
    elif strategy == "all_available":
        required.update(("joining_process_origin_id", "selection_name"))
    values = {key: str(process.get(field) or "") for key, field in _IDENTIFIERS.items()}
    names = selection_names(process)
    configured_name = str(selector.get("selection_name") or "")
    if configured_name in names:
        values["selection_name"] = configured_name
    elif len(names) == 1:
        values["selection_name"] = next(iter(names))
    elif len(names) > 1 and ("selection_name" in required or "selection_name" in selector):
        raise ValueError(
            f"{reference.label}: selection_name requires one advertised name or an explicit advertised name; "
            f"advertised names: {json.dumps(sorted(names))}."
        )
    if any(not values[key] for key in required):
        raise ValueError(f"{reference.label}: selected process lacks an identifier required by {match_by}/{strategy}.")
    if (
        len(matching_processes(processes, values, match_by)) != 1
        or len(matching_processes(processes, values, "joining_process_id")) != 1
        or strategy == "selection_name_only"
        and len(matching_processes(processes, values, "selection_name")) != 1
    ):
        raise ValueError(
            f"{reference.label}: selected process is ambiguous by {match_by}, JoiningProcessId or wire SelectionName."
        )
    return {key: value for key, value in values.items() if key in selector or key in required}


def _patch_identifiers(source: str, changes: dict[FieldPath, str]) -> str:
    _, nodes = _document(source)
    edits: list[tuple[int, int, str]] = []
    additions: dict[FieldPath, dict[str, str]] = {}
    newline = "\r\n" if "\r\n" in source else "\n"
    for path, value in changes.items():
        if path not in nodes:
            additions.setdefault(path[:-1], {})[str(path[-1])] = value
            continue
        node = nodes[path]
        if not isinstance(node, ScalarNode):
            raise ValueError(f"Cannot replace non-scalar identifier at {path}.")
        if node.style in {"|", ">"}:
            raise ValueError(f"Use a plain or quoted scalar identifier at {path}, not a YAML block scalar.")
        # JSON strings are valid YAML scalars and cannot inject new YAML fields.
        edits.append((node.start_mark.index, node.end_mark.index, json.dumps(value)))
    for path, values in additions.items():
        node = nodes[path]
        if not isinstance(node, MappingNode):
            raise ValueError(f"Cannot add identifiers to non-mapping selector at {path}.")
        if node.flow_style:
            position = node.start_mark.index + 1
            text = ", ".join(f"{json.dumps(key)}: {json.dumps(value)}" for key, value in values.items())
            text += ", " if node.value else ""
        else:
            position = node.start_mark.index
            indent = " " * node.start_mark.column
            text = "".join(f"{key}: {json.dumps(value)}{newline}{indent}" for key, value in values.items())
        edits.append((position, position, text))
    for start, end, value in sorted(edits, reverse=True):
        source = source[:start] + value + source[end:]
    return source


def _save_profile(path: Path, original: bytes, updated: bytes) -> None:
    mode = stat.S_IMODE(path.stat().st_mode)
    if not mode & stat.S_IWUSR:
        raise PermissionError("Profile is read-only; nothing saved.")
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp", delete=False) as handle:
        temporary = Path(handle.name)
        try:
            handle.write(updated)
            handle.flush()
            os.fsync(handle.fileno())
        except BaseException:
            handle.close()
            temporary.unlink(missing_ok=True)
            raise
    try:
        os.chmod(temporary, mode)
        if path.read_bytes() != original:
            raise ValueError("Profile changed during review; nothing saved. Run refresh-profile again.")
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def guide_process_refresh(
    path: Path,
    original: bytes,
    processes: list[dict[str, Any]],
    *,
    prompt: Callable[[str], str] = input,
    emit: Callable[[str], None] = print,
) -> int:
    """Review all exact references, then atomically save only approved ID changes."""
    source = original.decode("utf-8")
    parse_refresh_manifest(source, path)
    raw, _ = _document(source)
    groups = _reference_groups(raw)
    if not groups:
        emit("No exact process references to refresh; profile unchanged.")
        return 0
    if not processes:
        raise ValueError("GetJoiningProcessList returned no processes; profile unchanged.")

    emit("Current GetJoiningProcessList catalog (process metadata does not prove result capability):")
    for number, process in enumerate(processes, 1):
        emit(
            f"  {number}: {json.dumps(process.get('name', ''))} | ID={json.dumps(process.get('id', ''))} | "
            f"Origin={json.dumps(process.get('origin_id', ''))} | "
            f"SelectionNames={json.dumps(sorted(selection_names(process)))} | "
            f"Classification={process.get('classification', '')}"
        )
    changes: dict[FieldPath, str] = {}
    for group in groups:
        emit("\nReferences updated together:")
        for reference in group:
            key = reference.selector.get("match_by", "joining_process_id")
            emit(f"  {reference.label}: {key}={json.dumps(reference.selector.get(key, ''))}")
        current_matches = [
            matching_processes(processes, reference.selector, reference.selector.get("match_by", "joining_process_id"))
            for reference in group
        ]
        can_keep = (
            all(len(matches) == 1 for matches in current_matches)
            and len({str(matches[0].get("id", "")).casefold() for matches in current_matches}) == 1
        )
        if can_keep:
            try:
                can_keep = all(
                    str(reference.selector.get(key) or "") == value
                    for reference, matches in zip(group, current_matches, strict=True)
                    for key, value in _updated_identifiers(reference, matches[0], processes).items()
                )
            except ValueError as exc:
                can_keep = False
                emit(f"Current identifiers require review: {exc}")
        while True:
            choice = prompt("Choose process number, k to keep a current match, or q to cancel: ").strip().lower()
            if choice in {"", "q"}:
                emit("Cancelled; profile unchanged.")
                return 1
            if choice == "k" and can_keep:
                break
            if not choice.isdecimal() or not 1 <= int(choice) <= len(processes):
                emit("Choose a listed process number; keep is allowed only for unique current matches.")
                continue
            process = processes[int(choice) - 1]
            for reference in group:
                for key, value in _updated_identifiers(reference, process, processes).items():
                    if reference.selector.get(key, "") != value:
                        changes[(*reference.path, key)] = value
            break
    if not changes:
        emit("All reviewed references are current; profile unchanged.")
        return 0
    updated = _patch_identifiers(source, changes)
    manifest = parse_refresh_manifest(updated, path)
    blocked = [
        check for check in check_live_process_selectors(manifest.to_execution_profile(), processes) if not check.passed
    ]
    if blocked:
        raise ValueError("Refreshed selectors are not ready: " + "; ".join(check.detail for check in blocked))
    emit(
        "\n"
        + "".join(
            difflib.unified_diff(
                source.splitlines(True), updated.splitlines(True), fromfile=str(path), tofile=str(path)
            )
        )
    )
    confirmation = f"REFRESH {path.name}"
    if prompt(f"Type {confirmation} to save this local file only: ").strip() != confirmation:
        emit("Not confirmed; profile unchanged.")
        return 1
    _save_profile(path, original, updated.encode("utf-8"))
    emit("Profile refreshed. No selection, joining, counter, restart or test workload was executed.")
    return 0
