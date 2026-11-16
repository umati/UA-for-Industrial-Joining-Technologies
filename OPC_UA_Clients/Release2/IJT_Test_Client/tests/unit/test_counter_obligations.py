from types import SimpleNamespace

import pytest
from asyncua import ua

from helpers.counter_obligations import (
    CounterEvidenceUnavailable,
    counter_negative_arguments,
    require_counter_delta,
    require_negative_counter_response,
)
from helpers.method_caller import MethodCallResult


def test_unknown_negative_probe_is_rejected_before_generating_method_arguments():
    with pytest.raises(ValueError, match="Unknown counter obligation"):
        counter_negative_arguments("tool", SimpleNamespace(), (), frozenset(), "unsupported_probe")


@pytest.mark.parametrize("business_status", [2, 4])
def test_negative_counter_requires_service_method_and_business_contract(business_status):
    result = MethodCallResult(
        success=False,
        service_good_confirmed=True,
        method_status_code=ua.StatusCodes.Uncertain,
        output=[business_status, ua.LocalizedText("Invalid scoped identity")],
        rpc_dispatched=True,
    )
    require_negative_counter_response(result, business_status)
    result.service_good_confirmed = False
    with pytest.raises(CounterEvidenceUnavailable, match="service"):
        require_negative_counter_response(result, business_status)
    result.service_good_confirmed = True
    result.method_status_code = ua.StatusCodes.BadInvalidArgument
    with pytest.raises(AssertionError, match="Uncertain"):
        require_negative_counter_response(result, business_status)
    result.method_status_code = ua.StatusCodes.Uncertain
    result.output = [business_status + 1, ua.LocalizedText("Wrong status")]
    with pytest.raises(AssertionError, match="business"):
        require_negative_counter_response(result, business_status)


@pytest.mark.parametrize("kind", ["invalid_piu", "unknown_process"])
def test_negative_arguments_keep_other_inputs_valid_and_prove_absence(kind):
    identification = SimpleNamespace(JoiningProcessId="valid", JoiningProcessOriginId="origin", SelectionName="")
    args, expected = counter_negative_arguments(
        "tool",
        identification,
        ("valid",),
        frozenset({"tool", "other-asset"}),
        kind,
    )
    assert args[2].Value == 1
    if kind == "invalid_piu":
        assert args[0].Value not in {"tool", "other-asset"}
        assert args[1].Value is identification
        assert expected == 2
    else:
        assert args[0].Value == "tool"
        assert args[1].Value.JoiningProcessId not in {"valid"}
        assert expected == frozenset({1, 4, 5})


@pytest.mark.parametrize("status", [1, 4, 5])
def test_unknown_process_accepts_opc_40450_1_table_55_process_rejection_statuses(status):
    from helpers.counter_obligations import counter_negative_rejected

    identification = SimpleNamespace(JoiningProcessId="valid", JoiningProcessOriginId="origin", SelectionName="")
    _, expected = counter_negative_arguments(
        "tool",
        identification,
        ("valid",),
        frozenset({"tool"}),
        "unknown_process",
    )
    result = MethodCallResult(
        success=False,
        service_good_confirmed=True,
        method_status_code=ua.StatusCodes.Uncertain,
        output=[status, ua.LocalizedText("No active batch sequence or unknown process")],
        rpc_dispatched=True,
    )
    assert counter_negative_rejected(result) is True
    require_negative_counter_response(result, expected)
    piu_category_result = MethodCallResult(
        success=False,
        service_good_confirmed=True,
        method_status_code=ua.StatusCodes.Uncertain,
        output=[2, ua.LocalizedText("ProductInstanceUri not found")],
        rpc_dispatched=True,
    )
    assert counter_negative_rejected(piu_category_result) is True
    with pytest.raises(AssertionError, match="business Status"):
        require_negative_counter_response(piu_category_result, expected)


def _counter_result(result_id, values):
    return SimpleNamespace(
        ResultMetaData=SimpleNamespace(
            ResultId=result_id,
            ResultCounters=[
                SimpleNamespace(Name=name, CounterType=kind, CounterValue=value) for name, kind, value in values
            ],
        )
    )


def test_counter_delta_does_not_guess_type_or_accept_stale_and_ambiguous_evidence():
    before = _counter_result("before", [("position", 17, 4), ("other", 8, 10)])
    after = _counter_result("after", [("position", 17, 6), ("other", 8, 10)])
    with pytest.raises(CounterEvidenceUnavailable, match="identity"):
        require_counter_delta(before, after, 2)
    require_counter_delta(before, after, 2, counter_name="position", counter_type=17)
    with pytest.raises(AssertionError) as error:
        require_counter_delta(before, after, 3, counter_name="position")
    assert "counter delta 3" in str(error.value)
    assert "before=4, after=6" in str(error.value)
    assert "ResultId='before'->'after'" in str(error.value)
    after.ResultMetaData.ResultId = "before"
    with pytest.raises(CounterEvidenceUnavailable, match="Distinct"):
        require_counter_delta(before, after, 2, counter_name="position")


@pytest.mark.parametrize("kind", ["invalid_piu", "unknown_process"])
def test_negative_probe_requires_other_arguments_to_be_currently_valid(kind):
    from helpers.cu_coverage_report import WorkflowEvidenceUnavailable

    identification = SimpleNamespace(JoiningProcessId="removed-process")
    with pytest.raises(WorkflowEvidenceUnavailable) as error:
        counter_negative_arguments("tool", identification, ("current-process",), frozenset({"tool"}), kind)
    assert error.value.ijt_properties["ijt_reason_code"] == "counter_negative_precondition_unproven"


@pytest.mark.parametrize("kind", ["invalid_piu", "unknown_process"])
def test_negative_probe_does_not_dispatch_a_generated_identity_that_is_exposed(monkeypatch, kind):
    from helpers.cu_coverage_report import WorkflowEvidenceUnavailable

    monkeypatch.setattr("helpers.counter_obligations.uuid.uuid4", lambda: SimpleNamespace(hex="collision"))
    identification = SimpleNamespace(JoiningProcessId="valid")
    with pytest.raises(WorkflowEvidenceUnavailable):
        counter_negative_arguments(
            "tool",
            identification,
            ("valid", "ijt-test-absent-collision"),
            frozenset({"tool", "urn:ijt-test-absent-collision"}),
            kind,
        )


@pytest.mark.parametrize("outputs", [[2], [True, ua.LocalizedText("Invalid")], [2, "Invalid"], [2, ua.LocalizedText()]])
def test_negative_rejection_needs_typed_status_and_explanatory_message(outputs):
    result = MethodCallResult(
        success=False, service_good_confirmed=True, method_status_code=ua.StatusCodes.Uncertain, output=outputs
    )
    with pytest.raises(AssertionError):
        require_negative_counter_response(result, 2)


def test_ambiguous_selected_counter_is_unavailable_but_malformed_counter_is_invalid():
    from helpers.counter_obligations import counter_snapshot

    duplicate = _counter_result("result", [("position", 17, 4), ("position", 17, 4)])
    with pytest.raises(CounterEvidenceUnavailable, match="ambiguous"):
        counter_snapshot(duplicate)
    malformed = _counter_result("result", [("position", True, 4)])
    with pytest.raises(ValueError, match="integers"):
        counter_snapshot(malformed)
    assert counter_snapshot(duplicate, counter_type=8) == {}


def test_counter_delta_accepts_same_result_id_partial_progression_and_checks_delta():
    before = SimpleNamespace(
        ResultMetaData=SimpleNamespace(
            ResultId="batch-1",
            IsPartial=True,
            SequenceNumber=1,
            ResultCounters=[
                SimpleNamespace(Name="batch_size", CounterType=2, CounterValue=3),
                SimpleNamespace(Name="batch_count", CounterType=3, CounterValue=1),
            ],
        ),
        ResultContent=[SimpleNamespace(ResultId="single-1")],
    )
    after = SimpleNamespace(
        ResultMetaData=SimpleNamespace(
            ResultId="batch-1",
            IsPartial=True,
            SequenceNumber=2,
            ResultCounters=[
                SimpleNamespace(Name="batch_size", CounterType=2, CounterValue=3),
                SimpleNamespace(Name="batch_count", CounterType=3, CounterValue=2),
            ],
        ),
        ResultContent=[SimpleNamespace(ResultId="single-1"), SimpleNamespace(ResultId="intervention-1")],
    )
    require_counter_delta(before, after, 1, counter_type=3)
    with pytest.raises(AssertionError, match="delta"):
        require_counter_delta(before, after, 2, counter_type=3)
    unchanged = SimpleNamespace(
        ResultMetaData=SimpleNamespace(
            ResultId="batch-1",
            IsPartial=True,
            SequenceNumber=1,
            ResultCounters=[SimpleNamespace(Name="batch_count", CounterType=3, CounterValue=2)],
        ),
        ResultContent=[SimpleNamespace(ResultId="single-1")],
    )
    with pytest.raises(CounterEvidenceUnavailable, match="Distinct"):
        require_counter_delta(unchanged, SimpleNamespace(**unchanged.__dict__), 0, counter_type=3)
