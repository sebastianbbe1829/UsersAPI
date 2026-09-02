import logging
import re
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path

LOG_DIR = Path(__file__).resolve().parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

LOG_FILE = LOG_DIR / "usersapi.log"


class SensitiveDataFilter(logging.Filter):
    """Redacts sensitive authentication and infrastructure data from logs."""

    _EMAIL = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
    _IPV4 = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
    _SENSITIVE_FIELDS = re.compile(
        r"(password|token|secret|otp|authorization|session_id|client_host|"
        r"tenant_id|user_tenant_id)\s*=\s*([^\s,;]+)",
        re.IGNORECASE,
    )

    def filter(self, record: logging.LogRecord) -> bool:
        message = record.getMessage()
        message = self._SENSITIVE_FIELDS.sub(r"\1=[REDACTED]", message)
        message = self._EMAIL.sub("[EMAIL_REDACTED]", message)
        message = self._IPV4.sub("[IP_REDACTED]", message)

        record.msg = message
        record.args = ()
        return True


formatter = logging.Formatter(
    "%(asctime)s %(levelname)s [%(name)s] %(message)s",
    "%Y-%m-%d %H:%M:%S",
)

sensitive_data_filter = SensitiveDataFilter()

file_handler = TimedRotatingFileHandler(
    filename=LOG_FILE,
    when="midnight",
    interval=1,
    backupCount=356,
    encoding="utf-8",
    utc=False,
)
file_handler.addFilter(sensitive_data_filter)
file_handler.setFormatter(formatter)
file_handler.suffix = "%Y-%m-%d.log"

console_handler = logging.StreamHandler()
console_handler.addFilter(sensitive_data_filter)
console_handler.setFormatter(formatter)

logger = logging.getLogger("UsersAPI")
logger.setLevel(logging.DEBUG)
logger.propagate = False
if not logger.handlers:
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
