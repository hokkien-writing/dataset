"""Latn converter module."""

from scripts.latn.config import LatnSystemConfig
from scripts.latn.converter import LatnConverter
from scripts.latn.registry import LatnRegistry
from scripts.latn.systems import register_default_systems
from scripts.latn.mappings import register_default_translators

# Initialize global registry
_registry = LatnRegistry()

# Register default systems and translators
register_default_systems(_registry)
register_default_translators(_registry)

def register_system(config: LatnSystemConfig, converter_class=LatnConverter):
    """Register a latn system in the global registry."""
    _registry.register(config.name, config, converter_class)

def create_converter(system: str = "PUJ") -> LatnConverter:
    """Create a latn converter for the specified system."""
    return _registry.create_converter(system)

def list_systems() -> list:
    """List all available latn systems."""
    return _registry.list_systems()

def get_registry() -> LatnRegistry:
    """Get the global converter registry."""
    return _registry

def create_translator(from_system: str, to_system: str):
    """Create a translator between two systems."""
    return _registry.create_translator(from_system, to_system)

__all__ = [
    "LatnSystemConfig",
    "LatnConverter",
    "LatnRegistry",
    "register_system",
    "create_converter",
    "create_translator",
    "list_systems",
    "get_registry",
]
