from .config import PhoneticMapping
from .systems import get_system_module

PIVOT = "LATN_NORM"

_SYSTEM_NAMES = ["poj", "puj", "tl", "bp", "dp"]


def register_default_translators(registry):
    for name in _SYSTEM_NAMES:
        mod = get_system_module(name)
        system_name = mod.SYSTEM_NAME
        fwd = mod.create_latn_norm_mapping()
        rev = mod.create_reverse_mapping()
        if fwd:
            registry.register_translator(system_name, PIVOT, fwd)
        if rev:
            registry.register_translator(PIVOT, system_name, rev)
