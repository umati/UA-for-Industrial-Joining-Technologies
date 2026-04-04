import logging
from datetime import datetime
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path


class MillisecondFormatter(logging.Formatter):
    def formatTime(self, record: logging.LogRecord, datefmt: str | None = None) -> str:
        ct = datetime.fromtimestamp(record.created)
        if datefmt:
            s = ct.strftime(datefmt)
            return s[:-3]  # Trim microseconds to milliseconds
        return ct.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]


LOG_FORMAT = "[%(asctime)s] [%(levelname)s] %(filename)s:%(funcName)s - %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S.%f"

_formatter = MillisecondFormatter(LOG_FORMAT, datefmt=DATE_FORMAT)

# Console handler
_console_handler = logging.StreamHandler()
_console_handler.setFormatter(_formatter)

# File handler with daily rotation
_log_dir = Path("logs")
_log_dir.mkdir(exist_ok=True)
_file_handler = TimedRotatingFileHandler(_log_dir / "client.log", when="midnight", backupCount=7, encoding="utf-8")
_file_handler.setFormatter(_formatter)

# Logger setup
ijt_log = logging.getLogger("ijt_logger")
ijt_log.setLevel(logging.INFO)
ijt_log.addHandler(_console_handler)
ijt_log.addHandler(_file_handler)
ijt_log.propagate = False

# Reduce verbosity of external libraries
logging.getLogger("asyncua").setLevel(logging.ERROR)
