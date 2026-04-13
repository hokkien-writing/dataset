"""Latn converter module."""

from scripts.latn.config import LatnSystemConfig
from scripts.latn.converter import LatnConverter
from scripts.latn.registry import ConverterRegistry
from scripts.latn.systems import register_default_systems

# Initialize global registry
_registry = ConverterRegistry()

# Register default systems
register_default_systems(_registry)

def register_system(config: LatnSystemConfig, converter_class=LatnConverter):
    """Register a latn system in the global registry."""
    _registry.register(config.name, config, converter_class)

def create_converter(system: str = "PUJ") -> LatnConverter:
    """Create a latn converter for the specified system."""
    return _registry.create_converter(system)

def list_systems() -> list:
    """List all available latn systems."""
    return _registry.list_systems()

def get_registry() -> ConverterRegistry:
    """Get the global converter registry."""
    return _registry

__all__ = [
    "LatnSystemConfig",
    "LatnConverter",
    "ConverterRegistry",
    "register_system",
    "create_converter",
    "list_systems",
    "get_registry",
]
