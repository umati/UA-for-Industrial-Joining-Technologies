# IJTLogger.py
import logging

logging.basicConfig(
    level=logging.INFO, format="[%(levelname)s] %(filename)s:%(funcName)s - %(message)s"
)

# Reduce verbosity of external libraries
logging.getLogger("asyncua").setLevel(logging.ERROR)

# Create a shared logger instance
ijt_logger = logging.getLogger("IJTLogger")
