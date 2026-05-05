from types import SimpleNamespace

from asyncua import ua

from helpers.result_navigation import (
    collect_result_values,
    collect_trace_entries,
    collect_trace_entries_from_content,
    iter_joining_results,
    unwrap_sequence,
    unwrap_variant,
)


def _value(name):
    return SimpleNamespace(Name=name)


def test_unwrap_variant_handles_nested_asyncua_variants():
    inner = SimpleNamespace(ResultId="r1")

    assert unwrap_variant(ua.Variant(ua.Variant(inner))) is inner


def test_unwrap_sequence_filters_none_and_unwraps_entries():
    item = SimpleNamespace(Name="item")

    assert unwrap_sequence([ua.Variant(item), ua.Variant(None)]) == [item]
    assert unwrap_sequence("not-a-sequence") == []


def test_iter_joining_results_traverses_nested_result_content_once():
    nested = SimpleNamespace(OverallResultValues=[_value("nested")])
    child = SimpleNamespace(ResultContent=[ua.Variant(nested)], StepResults=[])
    root = SimpleNamespace(ResultContent=[ua.Variant(child), ua.Variant(child)])

    paths = [path for path, _ in iter_joining_results(root)]

    assert paths == ["$.ResultContent[0]", "$.ResultContent[0].ResultContent[0]"]


def test_collect_result_values_includes_metadata_overall_and_step_values():
    meta_value = _value("meta")
    overall = _value("overall")
    step_value = _value("step")
    step = SimpleNamespace(StepResultValues=[ua.Variant(step_value)])
    child = SimpleNamespace(OverallResultValues=[overall], StepResults=[ua.Variant(step)])
    root = SimpleNamespace(
        ResultMetaData=SimpleNamespace(OverallResultValues=[ua.Variant(meta_value)]),
        ResultContent=[ua.Variant(child)],
    )

    values = collect_result_values(root)

    assert values == [meta_value, overall, step_value]


def test_collect_trace_entries_returns_paths_and_content_indexes():
    trace_a = SimpleNamespace(TraceId="a")
    trace_b = SimpleNamespace(TraceId="b")
    nested = SimpleNamespace(Trace=ua.Variant(trace_b))
    child = SimpleNamespace(Trace=ua.Variant(trace_a), ResultContent=[ua.Variant(nested)])
    root = SimpleNamespace(ResultContent=[ua.Variant(child)])

    assert collect_trace_entries(root) == [
        ("$.ResultContent[0]", trace_a),
        ("$.ResultContent[0].ResultContent[0]", trace_b),
    ]
    assert collect_trace_entries_from_content(root.ResultContent) == [(0, trace_a)]
    assert collect_trace_entries_from_content(None) == []
