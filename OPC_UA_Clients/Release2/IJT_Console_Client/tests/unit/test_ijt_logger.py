"""
Tests for ijt_logger.py (MillisecondFormatter and ijt_log).
"""
import inspect
import logging
from logging import LogRecord

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from ijt_logger import MillisecondFormatter, ijt_log


# ---------------------------------------------------------------------------
# MillisecondFormatter
# ---------------------------------------------------------------------------

def _make_record(message="test message"):
    record = LogRecord(
        name="test",
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg=message,
        args=(),
        exc_info=None,
    )
    return record


def test_format_time_returns_string():
    fmt = MillisecondFormatter()
    record = _make_record()
    result = fmt.formatTime(record)
    assert isinstance(result, str)


def test_format_time_contains_date():
    fmt = MillisecondFormatter()
    record = _make_record()
    result = fmt.formatTime(record)
    assert "-" in result  # YYYY-MM-DD format


def test_format_time_with_datefmt():
    fmt = MillisecondFormatter()
    record = _make_record()
    result = fmt.formatTime(record, datefmt="%Y-%m-%d %H:%M:%S.%f")
    assert isinstance(result, str)
    assert len(result) > 0


def test_format_time_has_type_hint():
    hints = MillisecondFormatter.formatTime.__annotations__
    assert "return" in hints or len(hints) >= 1  # at least one hint present


def test_format_time_type_hint_on_record():
    sig = inspect.signature(MillisecondFormatter.formatTime)
    params = sig.parameters
    assert "record" in params


# ---------------------------------------------------------------------------
# ijt_log logger instance
# ---------------------------------------------------------------------------

def test_ijt_log_has_info_method():
    assert hasattr(ijt_log, "info")
    assert callable(ijt_log.info)


def test_ijt_log_has_warning_method():
    assert hasattr(ijt_log, "warning")
    assert callable(ijt_log.warning)


def test_ijt_log_has_error_method():
    assert hasattr(ijt_log, "error")
    assert callable(ijt_log.error)


def test_ijt_log_has_debug_method():
    assert hasattr(ijt_log, "debug")
    assert callable(ijt_log.debug)


def test_ijt_log_is_logging_logger():
    assert isinstance(ijt_log, logging.Logger)


def test_log_level_can_be_set():
    original_level = ijt_log.level
    try:
        ijt_log.setLevel(logging.DEBUG)
        assert ijt_log.level == logging.DEBUG
        ijt_log.setLevel(logging.ERROR)
        assert ijt_log.level == logging.ERROR
    finally:
        ijt_log.setLevel(original_level)


def test_info_does_not_raise():
    ijt_log.info("test info message from unit test")


def test_warning_does_not_raise():
    ijt_log.warning("test warning from unit test")


def test_error_does_not_raise():
    ijt_log.error("test error from unit test")
