"""Unit tests for ``parse_xml_root`` and ``parse_coverage`` parsers.

These tests pin the security contract of the local CI artifact parser shared
by ``reporting/ci_run_summary.py`` and ``reporting/system_tests_run_summary.py``:

1. Bare external DOCTYPE declarations (the shape Vitest emits for cobertura
   coverage) MUST parse successfully, so the downstream ``parse_coverage``
   reports the real ``line-rate`` instead of returning ``None`` and triggering
   a false-positive ``Artifact Warnings`` entry.
2. Entity declarations (``<!ENTITY ...>``) MUST be rejected — these are the
   actual XXE / billion-laughs injection vector.
3. Internal-subset DOCTYPE (``<!DOCTYPE name [ ... ]>``) MUST be rejected —
   internal subsets are the standard place to declare entities.

Background: Vitest's cobertura output begins with
``<!DOCTYPE coverage SYSTEM "http://cobertura.sourceforge.net/xml/coverage-04.dtd">``.
Python ``xml.etree.ElementTree`` does not fetch external DTDs and does not
expand external entity references, so the bare external DOCTYPE shape is safe
to accept.
"""

from __future__ import annotations

import importlib
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


COBERTURA_VITEST_PAYLOAD = b"""<?xml version="1.0" ?>
<!DOCTYPE coverage SYSTEM "http://cobertura.sourceforge.net/xml/coverage-04.dtd">
<coverage lines-valid="1142" lines-covered="1106" line-rate="0.9684"
          branches-valid="688" branches-covered="611" branch-rate="0.888"
          timestamp="1700000000000" complexity="0" version="0.1">
</coverage>
"""

COBERTURA_NO_DOCTYPE_PAYLOAD = b"""<?xml version="1.0" ?>
<coverage line-rate="0.9876" />
"""

INTERNAL_SUBSET_DOCTYPE_PAYLOAD = b"""<?xml version="1.0" ?>
<!DOCTYPE coverage [
  <!ENTITY xxe SYSTEM "file:///etc/passwd">
]>
<coverage line-rate="0.99" />
"""

ENTITY_DECL_PAYLOAD = b"""<?xml version="1.0" ?>
<!ENTITY xxe "data">
<coverage line-rate="0.5" />
"""

PADDED_INTERNAL_SUBSET_DOCTYPE_PAYLOAD = (
    b'<?xml version="1.0" ?>\n'
    + (b" " * 2100)
    + b"""<!DOCTYPE coverage [
  <!ENTITY xxe "expanded">
]>
<coverage line-rate="0.99">&xxe;</coverage>
"""
)


@pytest.fixture(params=["ci_run_summary", "system_tests_run_summary"])
def parser_module(request):
    """Import each shared parser module under test."""
    return importlib.import_module(f"reporting.{request.param}")


def _write(tmp_path: Path, payload: bytes, name: str = "cobertura-coverage.xml") -> Path:
    target = tmp_path / name
    target.write_bytes(payload)
    return target


def test_parse_xml_root_accepts_vitest_cobertura_doctype(parser_module, tmp_path: Path) -> None:
    """The bare external Vitest DOCTYPE must parse without raising."""
    target = _write(tmp_path, COBERTURA_VITEST_PAYLOAD)
    root = parser_module.parse_xml_root(str(target))
    assert root.tag == "coverage"
    assert root.get("line-rate") == "0.9684"


def test_parse_xml_root_accepts_payload_without_doctype(parser_module, tmp_path: Path) -> None:
    """Existing DOCTYPE-free coverage shapes must still parse (regression guard)."""
    target = _write(tmp_path, COBERTURA_NO_DOCTYPE_PAYLOAD)
    root = parser_module.parse_xml_root(str(target))
    assert root.tag == "coverage"
    assert root.get("line-rate") == "0.9876"


def test_parse_xml_root_rejects_internal_subset_doctype(parser_module, tmp_path: Path) -> None:
    """Internal-subset DOCTYPE is the entity-injection vector and must be rejected."""
    target = _write(tmp_path, INTERNAL_SUBSET_DOCTYPE_PAYLOAD)
    with pytest.raises(ValueError, match="DTD/entity"):
        parser_module.parse_xml_root(str(target))


def test_parse_xml_root_rejects_entity_declaration(parser_module, tmp_path: Path) -> None:
    """``<!ENTITY ...>`` outside any DOCTYPE must also be rejected."""
    target = _write(tmp_path, ENTITY_DECL_PAYLOAD)
    with pytest.raises(ValueError, match="DTD/entity"):
        parser_module.parse_xml_root(str(target))


def test_parse_xml_root_rejects_padded_internal_subset_doctype(
    parser_module, tmp_path: Path
) -> None:
    """DTD/entity guards must not be limited to the first bytes of the file."""
    target = _write(tmp_path, PADDED_INTERNAL_SUBSET_DOCTYPE_PAYLOAD)
    with pytest.raises(ValueError, match="DTD/entity"):
        parser_module.parse_xml_root(str(target))


def test_parse_coverage_returns_real_percent_for_vitest_payload(tmp_path: Path) -> None:
    """parse_coverage must return the real percentage, not None.

    This is the contract test for the false-positive ``Artifact Warnings``
    bug that surfaced on CI run 25893480815: ``coverage/cobertura-coverage.xml``
    existed in the artifact with a valid ``line-rate`` but ``parse_coverage``
    returned ``None`` because the DOCTYPE guard rejected it before
    ``ElementTree.fromstring`` could read the line-rate attribute.
    """
    from reporting import ci_run_summary

    target = _write(tmp_path, COBERTURA_VITEST_PAYLOAD)
    pct = ci_run_summary.parse_coverage(str(target))
    assert pct == pytest.approx(96.8, abs=0.1)


def test_parse_coverage_returns_none_for_missing_path(tmp_path: Path) -> None:
    """A non-existent glob is the expected ``None`` path (no file emitted)."""
    from reporting import ci_run_summary

    pct = ci_run_summary.parse_coverage(str(tmp_path / "missing-coverage.xml"))
    assert pct is None


def test_parse_coverage_returns_none_for_internal_subset_doctype(tmp_path: Path) -> None:
    """Internal-subset DOCTYPE is suppressed by parse_coverage's contextlib guard.

    parse_coverage wraps parse_xml_root in ``contextlib.suppress(Exception)``,
    so the rejection of internal-subset DOCTYPE surfaces as ``None`` (which
    downstream renders an Artifact Warnings entry — the correct behavior for
    untrusted XML, just not for benign Vitest cobertura).
    """
    from reporting import ci_run_summary

    target = _write(tmp_path, INTERNAL_SUBSET_DOCTYPE_PAYLOAD)
    assert ci_run_summary.parse_coverage(str(target)) is None
