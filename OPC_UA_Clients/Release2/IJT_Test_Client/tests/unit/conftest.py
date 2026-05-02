"""
Shared fixtures for unit tests.

All unit tests are synchronous pure-Python tests — no OPC UA server required.
Uses types.SimpleNamespace for mock OPC UA objects instead of MagicMock.
"""

import types

import pytest


@pytest.fixture()
def valid_result_value():
    """Minimal valid ResultValueDataType mock."""
    return types.SimpleNamespace(MeasuredValue=42.0)


@pytest.fixture()
def valid_result_meta():
    """Minimal valid ResultMetaDataType mock."""
    return types.SimpleNamespace(
        ResultId="result-001",
        Classification=1,
        ResultEvaluation=1,
        CreationTime=object(),
    )


@pytest.fixture()
def valid_step_result():
    """Minimal valid StepResultDataType mock."""
    return types.SimpleNamespace(
        StepResultId="step-001",
        StepResultValues=[types.SimpleNamespace(MeasuredValue=10.0)],
    )


@pytest.fixture()
def valid_error_info():
    """Minimal valid ErrorInformationDataType mock."""
    return types.SimpleNamespace(ErrorType=3, ErrorId="ERR-001", ErrorMessage=types.SimpleNamespace(Text="Step error"))


@pytest.fixture()
def valid_joining_result(valid_result_value):
    """Minimal valid JoiningResultDataType mock."""
    return types.SimpleNamespace(
        ResultId="join-001",
        OverallResultValues=[valid_result_value],
        StepResults=[],
        Errors=[],
    )
