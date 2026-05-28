from .config import LatnSystemConfig
from .converter import LatnConverter
from .registry import LatnRegistry
from .systems import register_default_systems
from .mappings import register_default_translators

_registry = LatnRegistry()

register_default_systems(_registry)
register_default_translators(_registry)


def register_system(config: LatnSystemConfig, converter_class=LatnConverter):
    _registry.register(config.name, config, converter_class)


def create_converter(system: str = "PUJ") -> LatnConverter:
    return _registry.create_converter(system)


def list_systems() -> list:
    return _registry.list_systems()


def get_registry() -> LatnRegistry:
    return _registry


def create_translator(from_system: str, to_system: str):
    return _registry.create_translator(from_system, to_system)
