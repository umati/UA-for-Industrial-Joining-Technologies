"""Render IJT reference workflow demos."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from helpers.reference_workflow import (
    default_workflow_path,
    load_workflow,
    render_interactive_step,
    render_workflow_markdown,
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Render a reference joining-process workflow for review and demo use.")
    parser.add_argument(
        "--workflow",
        type=Path,
        default=default_workflow_path(),
        help="Workflow YAML file to render.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional Markdown report path.",
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Pause between workflow steps for live walkthroughs.",
    )
    parser.add_argument(
        "--no-console",
        action="store_true",
        help="Do not print the full Markdown report to stdout.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Run the workflow demo renderer."""
    args = parse_args(argv)
    workflow = load_workflow(args.workflow)
    markdown = render_workflow_markdown(workflow)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(markdown, encoding="utf-8", newline="\n")
        print(f"Wrote workflow report: {args.output}")

    if not args.no_console:
        print(markdown)

    if args.interactive:
        steps = workflow["steps"]
        total = len(steps)
        print("\nInteractive walkthrough")
        for index, step in enumerate(steps, start=1):
            print()
            print(render_interactive_step(step, index, total, workflow))
            if index < total:
                input("Press Enter for next step...")

    return 0


if __name__ == "__main__":
    sys.exit(main())
