#!/usr/bin/env python3
"""
create_structure.py — IJT Web Client one-time directory/file setup
===================================================================
Creates Resources/css/ and tests/legacy/ with the correct content.

Run once (or let RUN_ALL_TESTS.bat call it automatically):
    python create_structure.py
"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent

_TEST_SUBSCRIPTION_HANDLER_PY = """\
from asyncio import Future


class SubHandler:
    def __init__(self, filter):
        self.filter = filter
        self.my_future = Future()

    def getFuture(self):
        return self.my_future

    def event_notification(self, event):
        print("EVENT RECEIVED")

        if self.filter(event):
            self.my_future.set_result(event)


def conditionNameFilter(event, name):
    if event.ConditionClassName.Text == name:
        return True
    return False


def subConditionNameFilter(event, names):
    eventSubCondNames = []
    for sub in event.ConditionSubClassName:
        eventSubCondNames.append(sub.Text)
    for name in names:
        if name not in eventSubCondNames:
            return False
    return True


def combinedNameFilter(event, name, subnames):
    if conditionNameFilter(event, name) and subConditionNameFilter(event, subnames):
        return True
    return False
"""

_TEST_EXAMPLE_PY = """\
import os
import pytest
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from python.connection import Connection
from tests.legacy.TestSubscriptionHandler import SubHandler, combinedNameFilter

# Make sure you are in the venv
# python -m pytest tests/legacy/TestExample.py -v
# Set OPCUA_TEST_ENDPOINT env var to override the default server URL.

pytestmark = pytest.mark.legacy

SERVER_URL = os.getenv("OPCUA_TEST_ENDPOINT", "opc.tcp://10.46.19.106:40451")


@pytest.fixture
async def connect(url):
    connection = Connection(url, None)
    await connection.connect()
    return connection


@pytest.fixture
async def subscribe(connection, cond):
    handler = SubHandler(cond)
    await connection.subscribe({"eventtype": ["joiningsystemevent"]}, handler)
    return asyncio.wait_for(handler.getFuture(), timeout=10)


@pytest.mark.asyncio
async def test_opcua_client(connect, subscribe):
    def cond(ev):
        return combinedNameFilter(
            ev, "SystemConditionClassType", ["AssetConnectedConditionClassType"]
        )

    try:
        connection = connect(SERVER_URL, cond)
        timedFuture = subscribe(connection, cond)

        call = {
            "objectnode": {
                "Identifier": "TighteningSystem/Simulations/SimulateEventsAndConditions",
                "NamespaceIndex": "1",
            },
            "methodnode": {
                "Identifier": "TighteningSystem/Simulations/SimulateEventsAndConditions/SimulateEvents",
                "NamespaceIndex": "1",
            },
            "arguments": [
                {"dataType": 7, "value": 1}  # 1 means 'Tool connected' simulation
            ],
        }
        await connection.methodcall(call)

        eventRaw = await timedFuture

        event = eventRaw.get_event_props_as_fields_dict()

        # Test joining technology
        assert (
            event["JoiningSystemEventContent/JoiningTechnology"].Value.Text
            == "Tightening"
        )

        # test severity
        assert event["Severity"].Value == 1001  # Severity of event should be 100

        # Test message
        assert (
            event["Message"].Value.Text == "Tool Connected"
        )  # Message of event should be 'Tool Connected'

        # Test associatedEntities
        associatedEntities = event["JoiningSystemEventContent/AssociatedEntities"].Value
        productInstanceNr = 0
        for entity in associatedEntities:
            if entity.EntityType == 4:
                productInstanceNr = productInstanceNr + 1
        assert (
            productInstanceNr == 1
        )  # Exactly one associatedEntity for productInstanceUri

        await connection.terminate()

    except asyncio.TimeoutError:
        assert 1 == 0  # No answer in 10 seconds
        await connection.terminate()


if __name__ == "__main__":
    asyncio.run(test_opcua_client())
"""

_LEGACY_README_MD = """\
# Legacy Tests

These tests were developer exploration scripts, preserved for reference.
They require a live OPC UA server at a specific IP and are NOT part of the
automated CI test suite.

To run manually:
```bash
python -m pytest tests/legacy/TestExample.py -v
```

> **Note:** Update the hardcoded server URL in `TestExample.py` before running,
> or set the `OPCUA_TEST_ENDPOINT` environment variable.
"""


# ---------------------------------------------------------------------------
# Setup logic
# ---------------------------------------------------------------------------

def _write(path: Path, content: str, *, description: str) -> None:
    if path.exists():
        print(f"  [SKIP]   {description} — already exists")
        return
    path.write_text(content, encoding="utf-8")
    print(f"  [CREATED] {description}")


def main() -> int:
    print()
    print("=" * 60)
    print("  IJT Web Client — Project Structure Setup")
    print("=" * 60)

    # Read root nodeStyle.css NOW before we potentially turn it into a shim
    root_css_path = ROOT / "nodeStyle.css"
    root_css_content = root_css_path.read_text(encoding="utf-8")
    is_shim = "@import" in root_css_content[:300]

    # --- Resources/css/ ---
    css_dir = ROOT / "Resources" / "css"
    css_dir.mkdir(parents=True, exist_ok=True)
    if is_shim:
        print("  [WARN]   root nodeStyle.css is already a shim — Resources/css/nodeStyle.css")
        print("           must be created manually from the original CSS content.")
    else:
        _write(css_dir / "nodeStyle.css", root_css_content, description="Resources/css/nodeStyle.css")
        # Now that the real CSS lives in Resources/css/, turn root into the backward-compat shim
        shim = (
            "/*\n"
            " * nodeStyle.css — MOVED to Resources/css/nodeStyle.css\n"
            " * This file kept for backward compatibility only.\n"
            " * index.html now references Resources/css/nodeStyle.css directly.\n"
            " */\n"
            "@import url('Resources/css/nodeStyle.css');\n"
        )
        root_css_path.write_text(shim, encoding="utf-8")
        print("  [SHIMMED] root nodeStyle.css → @import shim")

    # --- tests/legacy/ ---
    legacy_dir = ROOT / "tests" / "legacy"
    legacy_dir.mkdir(parents=True, exist_ok=True)
    _write(legacy_dir / "README.md",                  _LEGACY_README_MD,             description="tests/legacy/README.md")
    _write(legacy_dir / "TestSubscriptionHandler.py", _TEST_SUBSCRIPTION_HANDLER_PY, description="tests/legacy/TestSubscriptionHandler.py")
    _write(legacy_dir / "TestExample.py",             _TEST_EXAMPLE_PY,             description="tests/legacy/TestExample.py")
    _write(legacy_dir / "test.json",                  "",                            description="tests/legacy/test.json")

    print()
    print("  Structure setup complete.")
    print("=" * 60)
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
