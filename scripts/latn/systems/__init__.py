"""Registration of all supported latn systems dynamically."""

import pkgutil
import importlib
from pathlib import Path

def register_default_systems(registry):
    """Automatically discover and register all system configs in this package."""
    package_dir = Path(__file__).parent
    
    # Iterate over all python modules in the current directory
    for _, module_name, is_pkg in pkgutil.iter_modules([str(package_dir)]):
        if not is_pkg:
            # Import the module dynamically
            module = importlib.import_module(f"scripts.latn.systems.{module_name}")
            
            # Check if the module has a create_config function and register it
            if hasattr(module, "create_config"):
                config = module.create_config()
                registry.register(config.name, config)


def get_system_module(system_name: str):
    return importlib.import_module(f"scripts.latn.systems.{system_name.lower()}")
