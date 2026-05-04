# Reference Workflows

This folder contains portable reference workflow scenarios for IJT client
demonstrations and future workflow-level automation.

Each workflow is described as reviewable YAML so the same definition can support
documentation, interactive walkthroughs, and future live execution.

## Current Workflow

| File | Purpose |
|---|---|
| `reference_joining_process_workflow.yaml` | Generic joining-process workflow covering connection, tool discovery, identifiers, process selection, execution, result capture, and cleanup. |

## Demo Command

Generate a Teams-friendly Markdown walkthrough:

```bash
python scripts/run_reference_workflow.py --output test-results/reference-workflows/reference_joining_process_workflow.md
```

Run it step by step in a terminal:

```bash
python scripts/run_reference_workflow.py --interactive
```

The current runner is a deterministic demo/report lane. It does not contact an
OPC UA server. Live workflow execution should be added as a separate mode after
the reviewed workflow data is stable.
