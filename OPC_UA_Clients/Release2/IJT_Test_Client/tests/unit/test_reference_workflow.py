"""Unit tests for reference workflow demos."""

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
