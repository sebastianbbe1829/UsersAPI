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


for layer_name in ("controllers", "models", "repositories", "routes", "schemas", "services"):
    core_module = importlib.import_module(
        f"{__name__}.domains.core.{layer_name}"
    )
    sys.modules[f"{__name__}.{layer_name}"] = core_module
    setattr(sys.modules[__name__], layer_name, core_module)

    core_prefix = f"{__name__}.domains.core.{layer_name}."
    legacy_prefix = f"{__name__}.{layer_name}."
    for module_name, module in list(sys.modules.items()):
        if module_name.startswith(core_prefix):
            legacy_name = legacy_prefix + module_name[len(core_prefix):]
            sys.modules[legacy_name] = module
