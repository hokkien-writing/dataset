"""Default phonetic mappings between latn systems."""

from scripts.latn.config import PhoneticMapping

PIVOT = "LATN_NORM"


def register_default_translators(registry):
    """Register translators between each system and LATN_NORM (pivot)."""

    # --- PUJ <-> LATN_NORM ---

    registry.register_translator(
        "PUJ",
        PIVOT,
        PhoneticMapping(
            initial_map={"ts": "ch", "tsh": "chh", "z": "j"},
        ),
    )

    registry.register_translator(
        PIVOT,
        "PUJ",
        PhoneticMapping(
            initial_map={
                "ch": lambda init, vowel: (
                    "ch" if vowel and vowel[0] in ("i", "e") else "ts"
                ),
                "chh": lambda init, vowel: (
                    "chh" if vowel and vowel[0] in ("i", "e") else "tsh"
                ),
                "j": lambda init, vowel: (
                    "j" if vowel and vowel[0] in ("i", "e") else "z"
                ),
            },
        ),
    )

    # --- POJ <-> LATN_NORM ---

    registry.register_translator(
        "POJ",
        PIVOT,
        PhoneticMapping(
            vowel_map={"oo": "ou", "oa": "ua", "oe": "ue"},
            ending_map={
                "n": lambda ending, tone: "t" if tone in (4, 8) else ending,
                "m": lambda ending, tone: "p" if tone in (4, 8) else ending,
                "ng": lambda ending, tone: "k" if tone in (4, 8) else ending,
            },
        ),
    )

    registry.register_translator(
        PIVOT,
        "POJ",
        PhoneticMapping(
            vowel_map={"ou": "oo", "ua": "oa", "ue": "oe"},
        ),
    )

    # --- TL <-> LATN_NORM ---

    registry.register_translator(
        "TL",
        PIVOT,
        PhoneticMapping(
            initial_map={"ts": "ch", "tsh": "chh"},
        ),
    )

    registry.register_translator(
        PIVOT,
        "TL",
        PhoneticMapping(
            initial_map={"ch": "ts", "chh": "tsh"},
        ),
    )

    # --- BP <-> LATN_NORM ---

    registry.register_translator(
        "BP",
        PIVOT,
        PhoneticMapping(
            initial_map={
                "b": "p",
                "p": "ph",
                "bb": "b",
                "bbn": "m",
                "ln": "n",
                "dd": "d",
                "d": "t",
                "t": "th",
                "g": "k",
                "k": "kh",
                "ggn": "ng",
                "gg": "g",
                "z": "ch",
                "c": "chh",
                "zz": "j",
            },
            vowel_map={"oo": "ou"},
        ),
    )

    registry.register_translator(
        PIVOT,
        "BP",
        PhoneticMapping(
            initial_map={
                "p": "b",
                "ph": "p",
                "b": "bb",
                "m": "bbn",
                "n": "ln",
                "d": "dd",
                "t": "d",
                "th": "t",
                "k": "g",
                "kh": "k",
                "ng": "ggn",
                "g": "gg",
                "ch": "z",
                "chh": "c",
                "j": "zz",
            },
            vowel_map={"ou": "oo"},
            nasal_prefix={"nn": ("n", ""), "nnh": ("n", "h")},
        ),
    )

    # --- DP <-> LATN_NORM ---

    registry.register_translator(
        "DP",
        PIVOT,
        PhoneticMapping(
            initial_map={
                "b": "p",
                "p": "ph",
                "bh": "b",
                "d": "t",
                "t": "th",
                "g": "k",
                "k": "kh",
                "gh": "g",
                "z": "ch",
                "c": "chh",
                "r": "j",
            },
            vowel_map={"e": "ur", "ê": "e", "uê": "ue", "iê": "ie"},
            ending_map={"b": "p", "d": "t", "g": "k"},
        ),
    )

    registry.register_translator(
        PIVOT,
        "DP",
        PhoneticMapping(
            initial_map={
                "p": "b",
                "ph": "p",
                "b": "bh",
                "t": "d",
                "th": "t",
                "k": "g",
                "kh": "k",
                "g": "gh",
                "ch": "z",
                "chh": "c",
                "j": "r",
            },
            vowel_map={"ur": "e", "e": "ê", "ue": "uê", "ie": "iê"},
            ending_map={"p": "b", "t": "d", "k": "g"},
        ),
    )
