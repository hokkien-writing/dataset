"""Registry for managing latn systems."""

from typing import Dict, Type, Optional, List
from scripts.latn.config import LatnSystemConfig, PhoneticMapping
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


class LatnRegistry(ConverterRegistry):
    """Extended registry with translator support."""

    def __init__(self):
        super().__init__()
        self._translators: Dict[str, PhoneticMapping] = {}

    def register_translator(self, from_system: str, to_system: str, mapping: PhoneticMapping):
        """Register a translator between two systems."""
        key = f"{from_system.upper()}->{to_system.upper()}"
        self._translators[key] = mapping

    def create_translator(self, from_system: str, to_system: str) -> "LatnTranslator":
        """Create a translator between two systems."""
        from scripts.latn.translator import LatnTranslator
        
        from_key = from_system.upper()
        to_key = to_system.upper()
        
        source_conv = self.create_converter(from_key)
        target_conv = self.create_converter(to_key)
        
        mapping_key = f"{from_key}->{to_key}"
        mapping = self._translators.get(mapping_key)
        
        return LatnTranslator(source_conv, target_conv, mapping)
