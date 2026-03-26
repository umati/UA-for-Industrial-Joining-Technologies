"""Logging configuration for the IJT Web Client backend.

Provides a pre-configured :data:`ijt_log` logger that emits millisecond-
precision timestamps via :class:`MillisecondFormatter`, and suppresses noisy
output from third-party libraries such as *asyncua*.
"""

import logging
from datetime import datetime
from logging import LogRecord


class MillisecondFormatter(logging.Formatter):
    """Log formatter that truncates timestamps to millisecond precision.

    Overrides :meth:`formatTime` to emit ``"YYYY-MM-DD HH:MM:SS.mmm"``
    (3 decimal places) rather than Python's default microsecond output.
    """

    def formatTime(self, record: LogRecord, datefmt: str | None = None) -> str:
        """Format the creation time of a log record with millisecond precision.

        Args:
            record: The :class:`logging.LogRecord` being formatted.
            datefmt: Optional strftime format string.  When provided, the last
                3 characters (microseconds) are stripped to yield milliseconds.

        Returns:
            A formatted timestamp string with millisecond precision.
        """
        ct = datetime.fromtimestamp(record.created)
        if datefmt:
            s = ct.strftime(datefmt)
            return s[:-3]  # Trim microseconds to milliseconds
        return ct.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]


formatter = MillisecondFormatter(
    "[%(asctime)s] [%(levelname)s] %(filename)s:%(funcName)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S.%f",
)

handler = logging.StreamHandler()
handler.setFormatter(formatter)

ijt_log = logging.getLogger("ijt_logger")
ijt_log.setLevel(logging.INFO)
ijt_log.addHandler(handler)
ijt_log.propagate = False

# Reduce verbosity of external libraries
logging.getLogger("asyncua").setLevel(logging.ERROR)
logging.getLogger("asyncua.client.ua_client").setLevel(logging.CRITICAL)
