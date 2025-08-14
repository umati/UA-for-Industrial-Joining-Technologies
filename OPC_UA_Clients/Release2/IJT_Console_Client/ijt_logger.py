import logging
from datetime import datetime


class MillisecondFormatter(logging.Formatter):
    def formatTime(self, record, datefmt=None):
        ct = datetime.fromtimestamp(record.created)
        if datefmt:
            s = ct.strftime(datefmt)
            return s[:-3]  # Trim microseconds to milliseconds
        else:
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
