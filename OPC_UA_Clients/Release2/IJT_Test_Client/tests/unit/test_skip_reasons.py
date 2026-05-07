import pytest

from helpers.cu_registry import CU
from helpers.skip_reasons import (
    accepted_policy_reason,
    blocked_reason,
    environment_reason,
    feature_not_supported_reason,
    not_supported_reason,
    skip_accepted_policy,
    skip_blocked,
    skip_environment,
    skip_feature_not_supported,
    skip_not_supported,
)


def test_not_supported_reason_for_cu_key():
    assert (
        not_supported_reason(CU.SEND_JOINING_PROCESS)
        == "IJT Send Joining Process - Method: SendJoiningProcess NOT SUPPORTED"
    )


def test_not_supported_reason_for_method_name():
    assert (
        not_supported_reason("SendJoiningProcess")
        == "IJT Send Joining Process - Method: SendJoiningProcess NOT SUPPORTED"
    )


def test_not_supported_reason_with_detail():
    assert not_supported_reason("SetCalibration", detail="method node absent").endswith(
        "NOT SUPPORTED - method node absent"
    )


def test_feature_not_supported_reason_with_detail():
    assert (
        feature_not_supported_reason(
            "JoiningSystemConditionType",
            detail=(
                "retained Acknowledgeable Conditions are not exposed by this server/package; "
                "ConditionClass fields on JoiningSystemEventType events remain supported"
            ),
        )
        == "IJT JoiningSystemConditionType NOT SUPPORTED - retained Acknowledgeable Conditions are "
        "not exposed by this server/package; "
        "ConditionClass fields on JoiningSystemEventType events remain supported"
    )


def test_blocked_reason_names_method_status_and_precondition():
    assert (
        blocked_reason("no active process is available", method="AbortJoiningProcess", status="Uncertain")
        == "BLOCKED - Method: AbortJoiningProcess - Status: Uncertain - no active process is available"
    )


def test_accepted_policy_reason_names_method_status_and_policy():
    assert (
        accepted_policy_reason(
            "no program is currently selected", method="GetSelectedJoiningProgram", status="Uncertain"
        )
        == "ACCEPTED POLICY - Method: GetSelectedJoiningProgram - Status: Uncertain - no program is currently selected"
    )


def test_environment_reason():
    assert environment_reason("Docker backend not reachable") == "ENVIRONMENT - Docker backend not reachable"


def test_skip_not_supported_raises_pytest_skip():
    with pytest.raises(pytest.skip.Exception) as exc:
        skip_not_supported("SendJoiningProcess")
    assert "IJT Send Joining Process - Method: SendJoiningProcess NOT SUPPORTED" in str(exc.value)


def test_skip_feature_not_supported_raises_pytest_skip():
    with pytest.raises(pytest.skip.Exception) as exc:
        skip_feature_not_supported("JoiningSystemConditionType", detail="event was not generated")
    assert "IJT JoiningSystemConditionType NOT SUPPORTED - event was not generated" in str(exc.value)


def test_skip_blocked_raises_pytest_skip():
    with pytest.raises(pytest.skip.Exception) as exc:
        skip_blocked("no active process is available", method="AbortJoiningProcess")
    assert "BLOCKED - Method: AbortJoiningProcess" in str(exc.value)


def test_skip_accepted_policy_raises_pytest_skip():
    with pytest.raises(pytest.skip.Exception) as exc:
        skip_accepted_policy(
            "no program is currently selected",
            method="GetSelectedJoiningProgram",
            status="Uncertain",
        )
    assert "ACCEPTED POLICY - Method: GetSelectedJoiningProgram - Status: Uncertain" in str(exc.value)


def test_skip_environment_raises_pytest_skip():
    with pytest.raises(pytest.skip.Exception) as exc:
        skip_environment("Docker backend not reachable")
    assert "ENVIRONMENT - Docker backend not reachable" in str(exc.value)
