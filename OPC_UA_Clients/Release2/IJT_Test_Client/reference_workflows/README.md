# Reference Workflows

This folder contains **static reference workflows** for IJT client demonstrations
and manual reviews.

Static means:

- no OPC UA connection is opened;
- no methods are called on a server;
- no CU result is passed or failed;
- the YAML is rendered into a Markdown or terminal walkthrough only.

Use this folder when you need a readable checklist or demo of the expected
joining-process flow. Use `run_target_server_cu.py` when you need preflight,
classification, or CU evidence for a server under test.

The reference workflow is intentionally kept separate from Target Server CU
execution. It explains the workflow to people; it does not validate a server.

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

The current runner does not contact an OPC UA server. It is a documentation and
walkthrough tool, not a conformance test runner.
