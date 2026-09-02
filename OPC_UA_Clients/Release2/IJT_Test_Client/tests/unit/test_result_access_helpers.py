"""
Unit tests for specification_tests/test_result_access.py helper functions.

Validates:
- _extract_sequence_number across all OPC UA live payload shapes (Variant, ExtensionObject, dict, object)
- Rejection of invalid types (bool, string, negative, out-of-range UInt64)
- _get_request_results_config error propagation on non-existent profile files
- Environment variable overrides for filter strategy
"""

from __future__ import annotations

import os
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from asyncua import ua

from helpers.target_server_cu_config import UINT64_MAX, RequestResultsConfig
from specification_tests.test_result_access import (
    _assert_request_results_output,
    _extract_sequence_number,
    _get_request_results_args,
    _get_request_results_config,
)


class TestExtractSequenceNumber:
    def test_extract_none_returns_none(self):
        assert _extract_sequence_number(None) is None

    def test_extract_from_object_with_result_metadata(self):
        obj = SimpleNamespace(ResultMetaData=SimpleNamespace(SequenceNumber=42))
        assert _extract_sequence_number(obj) == 42

    def test_extract_from_dict_with_result_metadata(self):
        data = {"ResultMetaData": {"SequenceNumber": 123}}
        assert _extract_sequence_number(data) == 123

    def test_extract_from_direct_result_metadata(self):
        data = {"SequenceNumber": 999}
        assert _extract_sequence_number(data) == 999

    def test_extract_case_variants(self):
        assert _extract_sequence_number({"ResultMetaData": {"sequence_number": 55}}) == 55
        assert _extract_sequence_number({"ResultMetaData": {"Sequence_Number": 77}}) == 77

    def test_extract_from_variant_wrapper(self):
        variant = ua.Variant(500, ua.VariantType.UInt64)
        obj = SimpleNamespace(ResultMetaData=SimpleNamespace(SequenceNumber=variant))
        assert _extract_sequence_number(obj) == 500

    def test_extract_from_extension_object_body(self):
        body = SimpleNamespace(ResultMetaData=SimpleNamespace(SequenceNumber=789))
        ext = SimpleNamespace(Body=body)
        assert _extract_sequence_number(ext) == 789

    def test_extract_from_nested_variant_and_extension_object(self):
        inner = SimpleNamespace(ResultMetaData=SimpleNamespace(SequenceNumber=ua.Variant(1001, ua.VariantType.UInt64)))
        ext = SimpleNamespace(Body=inner)
        outer_variant = ua.Variant(ext, ua.VariantType.ExtensionObject)
        assert _extract_sequence_number(outer_variant) == 1001

    def test_extract_rejects_bool(self):
        assert _extract_sequence_number({"ResultMetaData": {"SequenceNumber": True}}) is None
        assert _extract_sequence_number({"ResultMetaData": {"SequenceNumber": False}}) is None

    def test_extract_rejects_zero_or_negative(self):
        assert _extract_sequence_number({"ResultMetaData": {"SequenceNumber": 0}}) is None
        assert _extract_sequence_number({"ResultMetaData": {"SequenceNumber": -10}}) is None

    def test_extract_rejects_overflow(self):
        assert _extract_sequence_number({"ResultMetaData": {"SequenceNumber": UINT64_MAX + 1}}) is None

    def test_extract_accepts_uint64_max(self):
        assert _extract_sequence_number({"ResultMetaData": {"SequenceNumber": UINT64_MAX}}) == UINT64_MAX

    def test_extract_rejects_non_numeric_string(self):
        assert _extract_sequence_number({"ResultMetaData": {"SequenceNumber": "not-a-number"}}) is None

    @pytest.mark.parametrize("value", ["42", b"42", 42.5])
    def test_extract_rejects_non_integer_values(self, value):
        assert _extract_sequence_number({"ResultMetaData": {"SequenceNumber": value}}) is None

    def test_sequence_filtered_args_require_decoded_trigger_sequence(self):
        with pytest.raises(pytest.fail.Exception, match="cannot be correlated safely"):
            _get_request_results_args(None, RequestResultsConfig())
        with pytest.raises(pytest.fail.Exception, match="cannot be correlated safely"):
            _get_request_results_args(b"opaque-extension-object", RequestResultsConfig())

    def test_timestamp_args_do_not_require_trigger_sequence(self):
        args = _get_request_results_args(None, RequestResultsConfig(filter_strategy="timestamp"))
        assert args[0].Value == 0
        assert args[1].Value == 0

    def test_request_results_output_requires_three_fields_and_good_status(self):
        assert _assert_request_results_output([0.0, 0, "OK"], "RequestResults")[1] == 0
        with pytest.raises(AssertionError, match="must return"):
            _assert_request_results_output([0.0, 0], "RequestResults")
        with pytest.raises(AssertionError, match="non-zero Status"):
            _assert_request_results_output([0.0, 1, "Failed"], "RequestResults")


class TestGetRequestResultsConfig:
    def test_default_when_no_env(self):
        with patch.dict(os.environ, {}, clear=True):
            cfg = _get_request_results_config()
            assert cfg.filter_strategy == "sequence_number"
            assert cfg.from_sequence_number == 1
            assert cfg.to_sequence_number == 50

    def test_missing_profile_raises_file_not_found(self):
        with patch.dict(os.environ, {"OPCUA_TARGET_SERVER_PROFILE": "nonexistent_profile_path.sut.yaml"}):
            with pytest.raises(FileNotFoundError, match="Configured profile does not exist"):
                _get_request_results_config()

    def test_env_strategy_override(self):
        with patch.dict(os.environ, {"OPCUA_REQUEST_RESULTS_FILTER_STRATEGY": "timestamp"}):
            cfg = _get_request_results_config()
            assert cfg.filter_strategy == "timestamp"

    def test_env_strategy_both(self):
        with patch.dict(os.environ, {"OPCUA_REQUEST_RESULTS_FILTER_STRATEGY": "both"}):
            cfg = _get_request_results_config()
            assert cfg.filter_strategy == "both"
