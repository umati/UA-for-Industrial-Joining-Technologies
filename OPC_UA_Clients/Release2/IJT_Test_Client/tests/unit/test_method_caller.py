"""
Unit tests for helpers/method_caller.py

Tests the pure-Python components that do not require a live OPC UA server:
  - OpcUaStatusHelper static methods
  - MethodCallResult dataclass and output_list property
"""

from asyncua import ua

from helpers.method_caller import MethodCallResult, OpcUaStatusHelper


class TestOpcUaStatusHelperIsBad:
    def test_bad_status_code_returns_true(self):
        assert OpcUaStatusHelper.is_bad(0x80340000) is True

    def test_bad_not_found_returns_true(self):
        assert OpcUaStatusHelper.is_bad(OpcUaStatusHelper.BAD_NOT_FOUND) is True

    def test_bad_invalid_argument_returns_true(self):
        assert OpcUaStatusHelper.is_bad(OpcUaStatusHelper.BAD_INVALID_ARGUMENT) is True

    def test_good_status_returns_false(self):
        assert OpcUaStatusHelper.is_bad(0x00000000) is False

    def test_uncertain_status_returns_false(self):
        assert OpcUaStatusHelper.is_bad(0x40000000) is False

    def test_all_known_bad_codes(self):
        bad_codes = [
            OpcUaStatusHelper.BAD_NOT_FOUND,
            OpcUaStatusHelper.BAD_INVALID_ARGUMENT,
            OpcUaStatusHelper.BAD_NODE_ID_UNKNOWN,
            OpcUaStatusHelper.BAD_NOT_SUPPORTED,
            OpcUaStatusHelper.BAD_ARGUMENTS_MISSING,
        ]
        for code in bad_codes:
            assert OpcUaStatusHelper.is_bad(code) is True, f"Expected bad: 0x{code:08X}"


class TestOpcUaStatusHelperIsGood:
    def test_zero_is_good(self):
        assert OpcUaStatusHelper.is_good(0x00000000) is True

    def test_bad_code_is_not_good(self):
        assert OpcUaStatusHelper.is_good(0x80340000) is False

    def test_uncertain_is_not_good(self):
        assert OpcUaStatusHelper.is_good(0x40000000) is False

    def test_good_with_info_bits(self):
        assert OpcUaStatusHelper.is_good(0x00FF0000) is True


class TestOpcUaStatusHelperIsUncertain:
    def test_uncertain_base_is_uncertain(self):
        assert OpcUaStatusHelper.is_uncertain(0x40000000) is True

    def test_uncertain_with_bits(self):
        assert OpcUaStatusHelper.is_uncertain(0x40FF0000) is True

    def test_bad_is_not_uncertain(self):
        assert OpcUaStatusHelper.is_uncertain(0x80340000) is False

    def test_good_is_not_uncertain(self):
        assert OpcUaStatusHelper.is_uncertain(0x00000000) is False


class TestOpcUaStatusHelperClassify:
    def test_classify_good(self):
        assert OpcUaStatusHelper.classify(0x00000000) == "Good"

    def test_classify_bad(self):
        assert OpcUaStatusHelper.classify(0x80340000) == "Bad"

    def test_classify_uncertain(self):
        assert OpcUaStatusHelper.classify(0x40000000) == "Uncertain"

    def test_classify_good_with_code(self):
        assert OpcUaStatusHelper.classify(0x00FF0000) == "Good"

    def test_classify_bad_all_known(self):
        for code in [
            OpcUaStatusHelper.BAD_NOT_FOUND,
            OpcUaStatusHelper.BAD_INVALID_ARGUMENT,
            OpcUaStatusHelper.BAD_NODE_ID_UNKNOWN,
            OpcUaStatusHelper.BAD_NOT_SUPPORTED,
            OpcUaStatusHelper.BAD_ARGUMENTS_MISSING,
        ]:
            assert OpcUaStatusHelper.classify(code) == "Bad"


class TestOpcUaStatusHelperFormatStatus:
    def test_format_non_ua_error_falls_back_to_str(self):
        exc = ValueError("something went wrong")
        result = OpcUaStatusHelper.format_status(exc)
        assert result == "something went wrong"

    def test_format_runtime_error(self):
        exc = RuntimeError("timeout")
        result = OpcUaStatusHelper.format_status(exc)
        assert "timeout" in result

    def test_format_ua_error_without_code_falls_back_to_str(self):
        exc = ua.UaError("ua error without code")
        result = OpcUaStatusHelper.format_status(exc)
        assert isinstance(result, str)

    def test_format_ua_status_code_error_formats_hex(self):
        # ua.UaStatusCodeError naturally has a .code attribute
        exc = ua.UaStatusCodeError(0x80340000)
        result = OpcUaStatusHelper.format_status(exc)
        assert isinstance(result, str)
        assert len(result) > 0


class TestMethodCallResult:
    def test_success_result(self):
        r = MethodCallResult(success=True, output=[1, 2, 3], method_name="TestMethod")
        assert r.success is True
        assert r.output == [1, 2, 3]
        assert r.error is None

    def test_failure_result(self):
        err = Exception("OPC UA error")
        r = MethodCallResult(success=False, error=err, method_name="TestMethod")
        assert r.success is False
        assert r.error is err
        assert r.output is None

    def test_default_method_name_is_empty(self):
        r = MethodCallResult(success=True)
        assert r.method_name == ""

    def test_output_list_with_none(self):
        r = MethodCallResult(success=True, output=None)
        assert r.output_list == []

    def test_output_list_with_list(self):
        r = MethodCallResult(success=True, output=[10, 20, 30])
        assert r.output_list == [10, 20, 30]

    def test_output_list_with_tuple(self):
        r = MethodCallResult(success=True, output=(1, 2))
        assert r.output_list == [1, 2]

    def test_output_list_with_scalar(self):
        r = MethodCallResult(success=True, output=42)
        assert r.output_list == [42]

    def test_output_list_with_string_scalar(self):
        r = MethodCallResult(success=True, output="hello")
        assert r.output_list == ["hello"]

    def test_status_code_field(self):
        r = MethodCallResult(success=False, status_code=0x80340000)
        assert r.status_code == 0x80340000
