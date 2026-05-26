"""Shared frozen inputs for conformance summary byte-identity tests.

Both ``test_render_conformance_summary.py`` (the byte-identity regression gate)
and ``_capture_expected_summaries.py`` (the helper that regenerates the
expected Markdown fixtures when the report shape is intentionally changed)
must drive the renderer with **exactly the same** frozen inputs. Any drift
between the two would cause the byte-identity test to fire for the wrong
reason — not because the renderer regressed, but because the captured
fixtures and the test were rendered against different "frozen" values.

This module is the single source of truth for those inputs. Both callers
import from here; there is no second copy to keep in sync.

The ``now_utc`` value is intentionally ~1 day after the
``system_tests_full_conformance`` fixture baseline ``run_ts``
(``2026-05-12T13:09:41.281286Z``). The renderer no longer reads the
baseline at all (trend UI was removed), but the frozen
value is kept stable so byte-identity output stays deterministic across
runs.
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

# scripts/ is not a Python package; add it to sys.path so we can import the
# renderer module from this fixtures helper.
_SCRIPTS_DIR = Path(__file__).resolve().parents[3] / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from reporting.conformance_summary import ReportEnvironment  # noqa: E402

FIXED_RUN_TS = "2026-05-13 14:00 UTC"
FIXED_SERVER_URL = "opc.tcp://fixture.ijt.test:40451"

FROZEN_ENV = ReportEnvironment(
    git_sha="15bc900",
    python_version="3.14.3",
    asyncua_version="1.2b2",
    host_os="Windows-11-10.0.26200-SP0",
    run_logs_url="Not Applicable",
    glossary_url="OPC_UA_Clients/Release2/IJT_Test_Client/docs/REPORT_GLOSSARY.md",
    now_utc=datetime(2026, 5, 13, 14, 0, 0, tzinfo=timezone.utc),
)
