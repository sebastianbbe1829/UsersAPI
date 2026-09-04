import importlib
import sys
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


for layer_name in ("controllers", "repositories", "routes", "services"):
    sys.modules[f"{__name__}.{layer_name}"] = importlib.import_module(
        f"{__name__}.domains.core.{layer_name}"
    )
