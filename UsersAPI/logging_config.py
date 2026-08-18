import logging
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path

LOG_DIR = Path(__file__).resolve().parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

LOG_FILE = LOG_DIR / "usersapi.log"

formatter = logging.Formatter(
    "%(asctime)s %(levelname)s [%(name)s] %(message)s",
    "%Y-%m-%d %H:%M:%S",
)

file_handler = TimedRotatingFileHandler(
    filename=LOG_FILE,
    when="midnight",
    interval=1,
    backupCount=356,
    encoding="utf-8",
    utc=False,
)
file_handler.setFormatter(formatter)
file_handler.suffix = "%Y-%m-%d.log"

console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)

logger = logging.getLogger("UsersAPI")
logger.setLevel(logging.DEBUG)
logger.propagate = False
if not logger.handlers:
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
