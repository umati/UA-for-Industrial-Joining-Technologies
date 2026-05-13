#!/usr/bin/env python3
"""Update the IJT Browser CI image pin after a verified image publish."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_IMAGE_RE = re.compile(r"^ghcr\.io/[a-z0-9._/-]+$")

_COMMENT = (
    "Single source of truth for the IJT Browser CI image consumed by "
    "integration.yml live-webclient-browser. IJT_BROWSER_CI_IMAGE is "
    "constructed at runtime as image@digest. Refresh procedure: the "
    "build-browser-ci-image workflow publishes a verified image, updates this "
    "file on the automation/ijt-browser-ci-image-pin branch, and opens or "
    "updates a reviewable PR. The workflow MUST fail fast if digest does not "
    "match ^sha256:[0-9a-f]{64}$."
)


def _load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def _validate_image(image: str) -> None:
    if ":" in image.rsplit("/", 1)[-1]:
        raise ValueError(f"image must not include a floating tag, got {image!r}")
    if not _IMAGE_RE.fullmatch(image):
        raise ValueError(f"image must be a lowercase ghcr.io reference, got {image!r}")


def _validate_digest(digest: str) -> None:
    if not _SHA256_RE.fullmatch(digest):
        raise ValueError(f"digest must match ^sha256:[0-9a-f]{{64}}$, got {digest!r}")


def _required_value(source: dict[str, Any], key: str) -> str:
    value = source.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"missing non-empty {key!r}")
    return value


def build_updated_pin(
    *,
    current: dict[str, Any],
    metadata: dict[str, Any],
    image: str,
    digest: str,
    image_revision: str,
    image_created: str,
    image_workflow_run: str,
) -> dict[str, Any]:
    """Build the next image-pin.json object from verified publish metadata."""
    _validate_image(image)
    _validate_digest(digest)
    if current.get("image") == image and current.get("digest") == digest:
        return dict(current)

    updated: dict[str, Any] = {
        "image": image,
        "digest": digest,
        "playwright_version": _required_value(metadata, "playwright_version"),
        "node_version": _required_value(metadata, "node_version"),
        "python_version": _required_value(metadata, "python_version"),
        "image_revision": image_revision,
        "image_created": image_created,
        "image_workflow_run": image_workflow_run,
    }

    base_digests = metadata.get("base_digests")
    if isinstance(base_digests, dict) and base_digests:
        updated["base_digests"] = base_digests

    for key, value in current.items():
        if key not in updated and key != "_comment":
            updated[key] = value

    updated["_comment"] = _COMMENT
    return updated


def update_pin(
    *,
    pin_path: Path,
    metadata_path: Path,
    image: str,
    digest: str,
    image_revision: str,
    image_created: str,
    image_workflow_run: str,
) -> dict[str, Any]:
    """Rewrite image-pin.json with the verified publish metadata."""
    current = _load_json(pin_path)
    updated = build_updated_pin(
        current=current,
        metadata=_load_json(metadata_path),
        image=image,
        digest=digest,
        image_revision=image_revision,
        image_created=image_created,
        image_workflow_run=image_workflow_run,
    )
    if updated == current:
        return updated
    pin_path.write_text(json.dumps(updated, indent=2) + "\n", encoding="utf-8")
    return updated


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pin", type=Path, required=True, help="Path to image-pin.json")
    parser.add_argument(
        "--metadata",
        type=Path,
        required=True,
        help="Path to /opt/ijt-browser-ci/metadata.json captured from the image",
    )
    parser.add_argument("--image", required=True, help="Lowercase ghcr.io image name")
    parser.add_argument("--digest", required=True, help="sha256:<64hex> image digest")
    parser.add_argument("--image-revision", required=True, help="Source git SHA")
    parser.add_argument("--image-created", required=True, help="UTC creation timestamp")
    parser.add_argument("--image-workflow-run", required=True, help="Workflow run URL")
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    update_pin(
        pin_path=args.pin,
        metadata_path=args.metadata,
        image=args.image,
        digest=args.digest,
        image_revision=args.image_revision,
        image_created=args.image_created,
        image_workflow_run=args.image_workflow_run,
    )


if __name__ == "__main__":
    main()
