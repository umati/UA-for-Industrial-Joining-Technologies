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


def test_unwrap_variant_handles_exception():
    """Test that unwrap_variant returns item unchanged on exception."""

    # Create an object that will raise an exception when accessing Value
    class BadVariant:
        @property
        def Value(self):
            raise RuntimeError("Cannot read Value")

    bad_variant = BadVariant()
    result = unwrap_variant(bad_variant)
    assert result is bad_variant


def test_unwrap_variant_handles_none_inner():
    """Test that unwrap_variant returns None when inner Value is None."""
    result = unwrap_variant(ua.Variant(None))
    assert result is None


def test_iter_joining_results_handles_none_result_content():
    """Test that iter_joining_results handles None ResultContent gracefully."""
    root = SimpleNamespace(OverallResultValues=[], StepResults=[], Trace=None)
    paths = list(iter_joining_results(root))
    assert len(paths) == 1
    assert paths[0][0] == "$"


def test_unwrap_variant_returns_inner_when_double_wrapped():
    """Test that unwrap_variant handles double-wrapped Variants."""
    inner = SimpleNamespace(ResultId="r1")
    result = unwrap_variant(ua.Variant(ua.Variant(inner)))
    assert result is inner


def test_iter_joining_results_skips_none_items():
    """Test that iter_joining_results skips None items in ResultContent."""
    child = SimpleNamespace(OverallResultValues=[])
    root = SimpleNamespace(ResultContent=[ua.Variant(child), ua.Variant(None)])

    paths = list(iter_joining_results(root))

    # Should yield child but skip None (root doesn't have joining result attributes)
    assert len(paths) == 1


def test_collect_trace_entries_from_content_skips_none_joining_results():
    """Test that collect_trace_entries_from_content skips None joining results."""
    trace = SimpleNamespace(TraceId="a")
    child = SimpleNamespace(Trace=ua.Variant(trace))
    content = [ua.Variant(child), ua.Variant(None)]

    result = collect_trace_entries_from_content(content)

    assert len(result) == 1
    assert result[0] == (0, trace)
