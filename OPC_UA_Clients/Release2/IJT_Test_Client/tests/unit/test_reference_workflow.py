"""Unit tests for reference workflow demos."""

import pytest

from helpers.reference_workflow import default_workflow_path, load_workflow, render_workflow_markdown


def test_default_reference_workflow_loads():
    workflow = load_workflow(default_workflow_path())
    assert workflow["id"] == "reference_joining_process_workflow"
    assert len(workflow["steps"]) >= 8


def test_reference_workflow_uses_generic_demo_values():
    workflow = load_workflow(default_workflow_path())
    rendered = render_workflow_markdown(workflow)

    assert "EXAMPLE-STATION-01" in rendered
    assert "EXAMPLE-TOOL-01" in rendered


def test_reference_workflow_markdown_contains_demo_tables():
    workflow = load_workflow(default_workflow_path())
    rendered = render_workflow_markdown(workflow)

    assert "## Demo Values" in rendered
    assert "## Step Flow" in rendered
    assert "| Step | Phase | Workflow Action | OPC UA Surface | Expected Outcome | Support |" in rendered
    assert "Select joining process" in rendered
    assert "Verify new result" in rendered


def test_validate_workflow_raises_on_missing_required_keys():
    from helpers.reference_workflow import validate_workflow

    with pytest.raises(ValueError, match="missing required key: id"):
        validate_workflow({"title": "Test", "steps": []})

    with pytest.raises(ValueError, match="missing required key: title"):
        validate_workflow({"id": "test", "steps": []})

    with pytest.raises(ValueError, match="missing required key: steps"):
        validate_workflow({"id": "test", "title": "Test"})


def test_validate_workflow_raises_on_empty_or_non_list_steps():
    from helpers.reference_workflow import validate_workflow

    with pytest.raises(ValueError, match="must be a non-empty list"):
        validate_workflow({"id": "test", "title": "Test", "steps": []})

    with pytest.raises(ValueError, match="must be a non-empty list"):
        validate_workflow({"id": "test", "title": "Test", "steps": "not-a-list"})


def test_validate_workflow_raises_on_invalid_step_format():
    from helpers.reference_workflow import validate_workflow

    with pytest.raises(ValueError, match="step 1 must be a mapping"):
        validate_workflow({"id": "test", "title": "Test", "steps": ["not-a-dict"]})

    with pytest.raises(ValueError, match="step 1 is missing required key: id"):
        validate_workflow(
            {"id": "test", "title": "Test", "steps": [{"phase": "p", "title": "t", "workflow_action": "a"}]}
        )

    with pytest.raises(ValueError, match="step 1 is missing required key: phase"):
        validate_workflow(
            {"id": "test", "title": "Test", "steps": [{"id": "s1", "title": "t", "workflow_action": "a"}]}
        )

    with pytest.raises(ValueError, match="step 1 is missing required key: expected_outcome"):
        validate_workflow(
            {"id": "test", "title": "Test", "steps": [{"id": "s1", "phase": "p", "title": "t", "workflow_action": "a"}]}
        )


def test_load_workflow_raises_on_non_dict(tmp_path):
    from helpers.reference_workflow import load_workflow

    path = tmp_path / "workflow.yaml"
    path.write_text("- this is a list\n- not a dict\n", encoding="utf-8")

    with pytest.raises(ValueError, match="must contain a mapping"):
        load_workflow(path)


def test_render_interactive_step_formats_correctly():
    from helpers.reference_workflow import render_interactive_step

    workflow = {"phases": [{"id": "p1", "title": "Phase One"}]}
    step = {
        "title": "Test Step",
        "phase": "p1",
        "workflow_action": "Do something",
        "opcua_surface": ["Method A", "Method B"],
        "expected_outcome": ["Result 1", "Result 2"],
        "simulator_support": "Full",
    }

    result = render_interactive_step(step, 1, 5, workflow)

    assert "[1/5] Test Step" in result
    assert "Phase: Phase One" in result
    assert "Action: Do something" in result
    assert "Method A" in result
    assert "Method B" in result
    assert "Result 1" in result
    assert "Result 2" in result
    assert "Support: Full" in result


def test_phase_title_returns_id_when_phase_not_found():
    """Test that _phase_title returns phase_id when no matching phase is found."""
    from helpers.reference_workflow import _phase_title

    workflow = {"phases": [{"id": "p1", "title": "Phase One"}]}
    result = _phase_title(workflow, "p2")
    assert result == "p2"


def test_as_text_returns_empty_for_none():
    """Test that _as_text returns empty string for None."""
    from helpers.reference_workflow import _as_text

    assert _as_text(None) == ""
