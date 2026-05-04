"""Utilities for reference workflow demos."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_DEFAULT_WORKFLOW_PATH = _PROJECT_ROOT / "reference_workflows" / "reference_joining_process_workflow.yaml"


def default_workflow_path() -> Path:
    """Return the checked-in reference workflow path."""
    return _DEFAULT_WORKFLOW_PATH


def load_workflow(path: Path | None = None) -> dict[str, Any]:
    """Load a reference workflow YAML file."""
    workflow_path = path or default_workflow_path()
    with workflow_path.open(encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}

    if not isinstance(data, dict):
        raise ValueError(f"Workflow file must contain a mapping: {workflow_path}")
    validate_workflow(data)
    return data


def validate_workflow(workflow: dict[str, Any]) -> None:
    """Validate the minimal schema used by the demo renderer."""
    for key in ("id", "title", "steps"):
        if key not in workflow:
            raise ValueError(f"Workflow is missing required key: {key}")

    steps = workflow["steps"]
    if not isinstance(steps, list) or not steps:
        raise ValueError("Workflow 'steps' must be a non-empty list")

    for index, step in enumerate(steps, start=1):
        if not isinstance(step, dict):
            raise ValueError(f"Workflow step {index} must be a mapping")
        for key in ("id", "phase", "title", "workflow_action", "expected_evidence"):
            if key not in step:
                raise ValueError(f"Workflow step {index} is missing required key: {key}")


def render_workflow_markdown(workflow: dict[str, Any]) -> str:
    """Render a Teams-friendly Markdown workflow walkthrough."""
    validate_workflow(workflow)

    lines: list[str] = [
        f"# {workflow['title']}",
        "",
        f"Workflow id: `{workflow['id']}`",
        "",
        _as_text(workflow.get("purpose", "")),
        "",
        "## Demo Values",
        "",
        _markdown_table(
            ["Name", "Value"],
            [[_humanize_key(key), str(value)] for key, value in workflow.get("demo_values", {}).items()],
        ),
        "",
        "## Actors",
        "",
        _markdown_table(
            ["Actor", "Role"],
            [[actor.get("name", ""), actor.get("role", "")] for actor in workflow.get("actors", [])],
        ),
        "",
        "## Step Flow",
        "",
        _markdown_table(
            ["Step", "Phase", "Workflow Action", "OPC UA Surface", "Expected Evidence", "Support"],
            [
                [
                    f"{index}. {step['title']}",
                    _phase_title(workflow, step["phase"]),
                    step.get("workflow_action", ""),
                    step.get("opcua_surface", []),
                    step.get("expected_evidence", []),
                    step.get("simulator_support", ""),
                ]
                for index, step in enumerate(workflow["steps"], start=1)
            ],
        ),
        "",
        "## Review Notes",
        "",
        _markdown_table(
            ["Step", "Demo Note"],
            [
                [f"{index}. {step['title']}", step.get("demo_note", "")]
                for index, step in enumerate(workflow["steps"], start=1)
                if step.get("demo_note")
            ],
        ),
        "",
        "## Server Change Policy",
        "",
        _markdown_table(
            ["No Server Change Needed For", "Server Change Needed If"],
            _policy_rows(workflow.get("server_change_policy", {})),
        ),
        "",
    ]
    return "\n".join(lines)


def render_interactive_step(step: dict[str, Any], index: int, total: int, workflow: dict[str, Any]) -> str:
    """Render one workflow step for terminal walkthrough mode."""
    return "\n".join(
        [
            f"[{index}/{total}] {step['title']}",
            f"Phase: {_phase_title(workflow, step['phase'])}",
            f"Action: {step.get('workflow_action', '')}",
            f"OPC UA: {_as_text(step.get('opcua_surface', []))}",
            f"Evidence: {_as_text(step.get('expected_evidence', []))}",
            f"Support: {step.get('simulator_support', '')}",
        ]
    )


def _policy_rows(policy: dict[str, Any]) -> list[list[Any]]:
    no_change = policy.get("no_server_change_needed_for", [])
    change = policy.get("server_change_needed_if", [])
    max_len = max(len(no_change), len(change), 1)
    rows: list[list[Any]] = []
    for index in range(max_len):
        rows.append(
            [
                no_change[index] if index < len(no_change) else "",
                change[index] if index < len(change) else "",
            ]
        )
    return rows


def _phase_title(workflow: dict[str, Any], phase_id: str) -> str:
    for phase in workflow.get("phases", []):
        if phase.get("id") == phase_id:
            return phase.get("title", phase_id)
    return phase_id


def _markdown_table(headers: list[str], rows: list[list[Any]]) -> str:
    normalized_rows = rows or [["" for _ in headers]]
    output = [
        "| " + " | ".join(_cell(header) for header in headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in normalized_rows:
        padded = list(row) + [""] * (len(headers) - len(row))
        output.append("| " + " | ".join(_cell(value) for value in padded[: len(headers)]) + " |")
    return "\n".join(output)


def _cell(value: Any) -> str:
    text = _as_text(value)
    return text.replace("|", "\\|").replace("\n", "<br>")


def _as_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        return "<br>".join(str(item) for item in value)
    return str(value).strip()


def _humanize_key(key: str) -> str:
    return key.replace("_", " ").title()
