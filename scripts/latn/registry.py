"""Registry for managing latn systems."""

from typing import Dict, Type, Optional, List
from scripts.latn.config import LatnSystemConfig
from scripts.latn.converter import LatnConverter

class ConverterRegistry:
    """Registry for latn system converters."""

    def __init__(self):
        self._systems: Dict[str, Type[LatnConverter]] = {}
        self._configs: Dict[str, LatnSystemConfig] = {}

    def register(self, system_name: str, config: LatnSystemConfig, converter_class: Type[LatnConverter] = LatnConverter):
        """
        Register a new latn system.
        """
        key = system_name.upper()
        self._systems[key] = converter_class
        self._configs[key] = config

    def create_converter(self, system_name: str) -> LatnConverter:
        """
        Create a converter for the specified system.
        """
        system_key = system_name.upper()

        if system_key not in self._systems:
            available = ", ".join(self._systems.keys())
            raise ValueError(
                f"Unsupported latn system: {system_name}. "
                f"Available systems: {available}"
            )

        converter_class = self._systems[system_key]
        config = self._configs[system_key]

        return converter_class(config)

    def list_systems(self) -> List[str]:
        """List all registered systems."""
        return list(self._systems.keys())

    def get_config(self, system_name: str) -> Optional[LatnSystemConfig]:
        """Get configuration for a system."""
        return self._configs.get(system_name.upper())
