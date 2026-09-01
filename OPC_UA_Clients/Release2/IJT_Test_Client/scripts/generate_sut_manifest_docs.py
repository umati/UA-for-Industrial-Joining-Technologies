"""
Generate the SUT manifest template, example manifests, and field reference.

Everything here is derived from the single authoritative schema metadata in
``helpers/sut_manifest.py`` (``MANIFEST_SCHEMA`` plus the built-in presets), so
the committed artifacts cannot drift away from the code that validates them.

Usage (from OPC_UA_Clients/Release2/IJT_Test_Client)::

    python scripts/generate_sut_manifest_docs.py            # write artifacts
    python scripts/generate_sut_manifest_docs.py --check    # fail on drift (CI/tests)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

TEST_CLIENT_ROOT = Path(__file__).resolve().parents[1]
if str(TEST_CLIENT_ROOT) not in sys.path:
    sys.path.insert(0, str(TEST_CLIENT_ROOT))

from helpers.sut_manifest import MANIFEST_SUFFIX, render_field_reference, render_manifest_yaml

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


def main(argv: list[str] | None = None) -> int:
    """CLI entry point. Returns a process exit code."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Do not write anything; exit non-zero when a committed artifact is stale.",
    )
    args = parser.parse_args(argv)

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
