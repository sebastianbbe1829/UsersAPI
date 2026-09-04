import importlib
import sys


for module_name in (
    "database",
    "logging_config",
    "security",
    "settings",
    "util",
):
    module = importlib.import_module(f"UsersAPI.{module_name}")
    sys.modules[f"{__name__}.{module_name}"] = module


for module_name in (
    "dependencies",
    "permission_definitions",
    "permissions",
    "rate_limiter",
):
    module = importlib.import_module(f"UsersAPI.security.{module_name}")
    sys.modules[f"{__name__}.security.{module_name}"] = module
    setattr(sys.modules[f"{__name__}.security"], module_name, module)
