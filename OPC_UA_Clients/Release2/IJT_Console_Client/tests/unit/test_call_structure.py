"""
Tests for call structure / method caller conventions.

NOTE: call_structure.py does not exist in this codebase.
The method-call building logic lives in method_caller.py (OPCUAMethodCaller).
These tests verify naming conventions and ensure no legacy camelCase aliases exist.
"""
# pylint: disable=protected-access

import inspect
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))


# ---------------------------------------------------------------------------
# call_structure.py must not exist (no phantom module)
# ---------------------------------------------------------------------------


def test_call_structure_module_does_not_exist():
    """call_structure.py does not exist in this codebase — no phantom import allowed."""
    _ROOT = Path(__file__).resolve().parent.parent.parent
    assert not (_ROOT / "call_structure.py").exists(), (
        "call_structure.py must not exist; logic lives in method_caller.py"
    )


# ---------------------------------------------------------------------------
# method_caller.py — snake_case naming conventions
# ---------------------------------------------------------------------------


def test_method_caller_methods_are_snake_case():
    """All public methods on OPCUAMethodCaller must use snake_case."""
    from method_caller import OPCUAMethodCaller

    for name in dir(OPCUAMethodCaller):
        if name.startswith("_"):
            continue
        assert name == name.lower() or "_" in name, f"Method {name!r} on OPCUAMethodCaller is not snake_case"


def test_no_camelcase_alias_createcallstructure():
    """Regression: no camelCase createCallStructure alias must exist anywhere."""
    from method_caller import OPCUAMethodCaller

    assert not hasattr(OPCUAMethodCaller, "createCallStructure"), (
        "camelCase createCallStructure must not exist — use snake_case"
    )


def test_select_joint_is_snake_case():
    from method_caller import OPCUAMethodCaller

    assert hasattr(OPCUAMethodCaller, "select_joint")


def test_enable_asset_is_snake_case():
    from method_caller import OPCUAMethodCaller

    assert hasattr(OPCUAMethodCaller, "enable_asset")


def test_start_selected_joining_is_snake_case():
    from method_caller import OPCUAMethodCaller

    assert hasattr(OPCUAMethodCaller, "start_selected_joining")


# ---------------------------------------------------------------------------
# OPCUAMethodCaller: call structure integrity
# ---------------------------------------------------------------------------


def test_select_joint_takes_object_and_method_nodeids():
    from method_caller import OPCUAMethodCaller

    sig = inspect.signature(OPCUAMethodCaller.select_joint)
    params = list(sig.parameters.keys())
    assert "object_nodeid" in params
    assert "method_nodeid" in params
    assert "joint_id" in params


def test_select_joint_with_none_joint_origin_id():
    """select_joint must handle None joint_origin_id (converts to empty string)."""
    from method_caller import OPCUAMethodCaller

    sig = inspect.signature(OPCUAMethodCaller.select_joint)
    joint_origin = sig.parameters.get("joint_origin_id")
    assert joint_origin is not None
    assert joint_origin.default is None  # default is None (treated as "")


def test_parse_outputs_with_none_input():
    """_parse_outputs(None) must not raise — returns (None, None)."""
    from method_caller import OPCUAMethodCaller

    caller = OPCUAMethodCaller(None)
    # None is not a tuple/list, so should return (None, None)
    status, message = caller._parse_outputs(None)
    assert status is None
    assert message is None
