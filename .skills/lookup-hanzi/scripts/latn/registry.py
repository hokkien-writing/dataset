from typing import Dict, Type, Optional, List
from .config import LatnSystemConfig, PhoneticMapping
from .converter import LatnConverter

PIVOT = "LATN_NORM"


class ConverterRegistry:
    def __init__(self):
        self._systems: Dict[str, Type[LatnConverter]] = {}
        self._configs: Dict[str, LatnSystemConfig] = {}

    def register(
        self,
        system_name: str,
        config: LatnSystemConfig,
        converter_class: Type[LatnConverter] = LatnConverter,
    ):
        key = system_name.upper()
        self._systems[key] = converter_class
        self._configs[key] = config

    def create_converter(self, system_name: str) -> LatnConverter:
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
        return list(self._systems.keys())

    def get_config(self, system_name: str) -> Optional[LatnSystemConfig]:
        return self._configs.get(system_name.upper())


class LatnRegistry(ConverterRegistry):
    def __init__(self):
        super().__init__()
        self._translators: Dict[str, PhoneticMapping] = {}

    def register_translator(
        self, from_system: str, to_system: str, mapping: PhoneticMapping
    ):
        key = f"{from_system.upper()}->{to_system.upper()}"
        self._translators[key] = mapping

    def create_translator(self, from_system: str, to_system: str):
        from .translator import LatnTranslator

        from_key = from_system.upper()
        to_key = to_system.upper()

        if from_key == to_key:
            source_conv = self.create_converter(from_key)
            return LatnTranslator(source_conv, source_conv)

        mapping_key = f"{from_key}->{to_key}"
        mapping = self._translators.get(mapping_key)

        if mapping is not None:
            source_conv = self.create_converter(from_key)
            target_conv = self.create_converter(to_key)
            return LatnTranslator(source_conv, target_conv, mapping)

        return self._create_chained_translator(from_key, to_key)

    def _create_chained_translator(self, from_key: str, to_key: str):
        from .translator import LatnTranslator

        pivot_key = PIVOT
        if from_key == pivot_key or to_key == pivot_key:
            raise ValueError(
                f"No mapping for {from_key}->{to_key} and cannot chain through pivot"
            )

        map_to_pivot = self._translators.get(f"{from_key}->{pivot_key}")
        map_from_pivot = self._translators.get(f"{pivot_key}->{to_key}")

        if map_to_pivot is None or map_from_pivot is None:
            raise ValueError(
                f"No mapping path from {from_key} to {to_key} "
                f"(missing {from_key}->{pivot_key} or {pivot_key}->{to_key})"
            )

        source_conv = self.create_converter(from_key)
        pivot_conv = self.create_converter(pivot_key)
        target_conv = self.create_converter(to_key)

        leg1 = LatnTranslator(source_conv, pivot_conv, map_to_pivot)
        leg2 = LatnTranslator(pivot_conv, target_conv, map_from_pivot)

        class ChainedTranslator:
            def __init__(self, first, second):
                self._first = first
                self._second = second

            def translate(self, text):
                return self._second.translate(self._first.translate(text))

        return ChainedTranslator(leg1, leg2)
