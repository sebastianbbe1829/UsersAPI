import warnings

warnings.filterwarnings(
    "ignore",
    category=DeprecationWarning,
    message=".*Accessing argon2.__version__ is deprecated.*",
)
warnings.filterwarnings(
    "ignore",
    category=DeprecationWarning,
    message=".*Using `httpx` with `starlette.testclient` is deprecated.*",
)
warnings.filterwarnings(
    "ignore",
    category=DeprecationWarning,
    message=".*starlette.testclient.*deprecated.*",
)

from .main import app
