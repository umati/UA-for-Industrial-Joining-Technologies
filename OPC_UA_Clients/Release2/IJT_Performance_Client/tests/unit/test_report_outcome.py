"""Unit tests for management summary scale + OK / INFORMATION / ACTION NEEDED outcomes."""

from __future__ import annotations

from src.diagnostics import DiagnosticVerdict
from src.reporters._metrics import (
    OUTCOME_ACTION_NEEDED,
    OUTCOME_INFORMATION,
    OUTCOME_OK,
    classify_report_outcome,
    summarize_scale,
)
from src.results import LatencySample


def _verdict(code: str, **kwargs) -> DiagnosticVerdict:
    return DiagnosticVerdict(
        primary_bottleneck=code,
        headline=kwargs.get("headline", code),
        explanation=kwargs.get("explanation", "expl"),
        recommendation=kwargs.get("recommendation", "next"),
        metrics_summary=kwargs.get("metrics_summary", {}),
        warnings=kwargs.get("warnings", []),
    )


def test_summarize_scale_uniform_product():
    samples = [
        LatencySample(sample_id=1, endpoint="opc.tcp://a:1", delivery_time_ms=10.0),
        LatencySample(sample_id=2, endpoint="opc.tcp://a:1", delivery_time_ms=11.0),
        LatencySample(sample_id=3, endpoint="opc.tcp://a:2", delivery_time_ms=12.0),
        LatencySample(sample_id=4, endpoint="opc.tcp://a:2", delivery_time_ms=13.0),
    ]
    scale = summarize_scale(samples, samples_per_endpoint=2)
    assert scale.servers == 2
    assert scale.results_per_server_text == "2"
    assert "2 servers × 2 each" in scale.total_results_text


def test_summarize_scale_uneven_with_target():
    samples = [
        LatencySample(sample_id=1, endpoint="opc.tcp://a:1", delivery_time_ms=10.0),
        LatencySample(sample_id=2, endpoint="opc.tcp://a:1", delivery_time_ms=11.0),
        LatencySample(sample_id=3, endpoint="opc.tcp://a:2", delivery_time_ms=12.0),
    ]
    scale = summarize_scale(samples, samples_per_endpoint=2)
    assert "1–2" in scale.results_per_server_text
    assert "target 2" in scale.results_per_server_text


def test_outcome_ok_when_healthy_under_comfort():
    samples = [
        LatencySample(
            sample_id=1,
            endpoint="opc.tcp://a:1",
            delivery_time_ms=40.0,
            total_result_transfer_time_ms=50.0,
        )
    ]
    outcome = classify_report_outcome(
        _verdict("NONE (OPC UA PIPELINE HEALTHY)"),
        samples,
        scale=summarize_scale(samples, samples_per_endpoint=1),
    )
    assert outcome.label == OUTCOME_OK
    assert outcome.footer.startswith("OK —")


def test_outcome_information_for_local_host_cpu_under_500():
    samples = [
        LatencySample(
            sample_id=i,
            endpoint=f"opc.tcp://127.0.0.1:{41000 + i}",
            delivery_time_ms=113.0,
            total_result_transfer_time_ms=128.0,
        )
        for i in range(3)
    ]
    outcome = classify_report_outcome(
        _verdict("LOCAL_HOST_CPU"),
        samples,
        scale=summarize_scale(samples, samples_per_endpoint=1),
    )
    assert outcome.label == OUTCOME_INFORMATION
    assert outcome.footer.startswith("INFORMATION —")
    assert "ACTION NEEDED" not in outcome.footer
    assert "LOCAL_HOST_CPU" in outcome.footer


def test_outcome_information_when_p90_above_comfort_without_sla():
    samples = [
        LatencySample(
            sample_id=1,
            endpoint="opc.tcp://a:1",
            delivery_time_ms=620.0,
            total_result_transfer_time_ms=650.0,
        )
    ]
    outcome = classify_report_outcome(
        _verdict("NONE (OPC UA PIPELINE HEALTHY)"),
        samples,
    )
    # Healthy bottleneck but P90 >= 500 → INFORMATION (plant comfort)
    assert outcome.label == OUTCOME_INFORMATION
    assert "500" in outcome.footer


def test_outcome_action_needed_on_fail_p90():
    samples = [
        LatencySample(
            sample_id=1,
            endpoint="opc.tcp://a:1",
            delivery_time_ms=620.0,
            total_result_transfer_time_ms=650.0,
        )
    ]
    outcome = classify_report_outcome(
        _verdict("LOCAL_HOST_CPU"),
        samples,
        fail_p90_ms=500.0,
    )
    assert outcome.label == OUTCOME_ACTION_NEEDED
    assert outcome.footer.startswith("ACTION NEEDED —")
    assert "exceeded limit" in outcome.footer


def test_outcome_action_needed_on_integrity_shortfall():
    samples = [
        LatencySample(sample_id=1, endpoint="opc.tcp://a:1", delivery_time_ms=20.0),
        LatencySample(
            sample_id=2,
            endpoint="opc.tcp://a:1",
            delivery_time_ms=20.0,
            integrity_status="INCOMPLETE",
        ),
    ]
    outcome = classify_report_outcome(_verdict("LOCAL_HOST_CPU"), samples)
    assert outcome.label == OUTCOME_ACTION_NEEDED
    assert "used for stats" in outcome.footer.lower()
