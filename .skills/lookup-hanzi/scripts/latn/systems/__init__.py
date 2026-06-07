import pkgutil
import importlib
from pathlib import Path


def register_default_systems(registry):
    package_dir = Path(__file__).parent

    for _, module_name, is_pkg in pkgutil.iter_modules([str(package_dir)]):
        if not is_pkg:
            module = importlib.import_module(f".{module_name}", __package__)

            if hasattr(module, "create_config"):
                config = module.create_config()
                registry.register(config.name, config)


def get_system_module(system_name: str):
    return importlib.import_module(f".{system_name.lower()}", __package__)
