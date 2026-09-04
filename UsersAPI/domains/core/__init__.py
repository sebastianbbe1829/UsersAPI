import importlib
import sys


for module_name in (
    "database",
    "logging_config",
    "security",
    "settings",
    "util",
):
    sys.modules[f"{__name__}.{module_name}"] = importlib.import_module(
        f"UsersAPI.{module_name}"
    )
