"""Default phonetic mappings between latn systems."""

from scripts.latn.config import PhoneticMapping


def register_default_translators(registry):
    """Register standard translators between Hokkien and Teochew systems."""

    # --- Hokkien Group (POJ, TL, BP) ---

    # POJ -> TL
    registry.register_translator(
        "POJ",
        "TL",
        PhoneticMapping(
            initial_map={"ch": "ts", "chh": "tsh"},
            vowel_map={"o.": "oo", "oa": "ua", "oe": "ue"},
        ),
    )

    # TL -> POJ
    registry.register_translator(
        "TL",
        "POJ",
        PhoneticMapping(
            initial_map={"ts": "ch", "tsh": "chh"},
            vowel_map={"oo": "o.", "ua": "oa", "ue": "oe"},
        ),
    )

    # POJ -> BP
    registry.register_translator(
        "POJ",
        "BP",
        PhoneticMapping(
            initial_map={
                "p": "b",
                "ph": "p",
                "b": "bb",
                "m": "bbn",
                "t": "d",
                "th": "t",
                "d": "dd",
                "k": "g",
                "kh": "k",
                "g": "gg",
                "ng": "ggn",              
                "n": "ln",
                "ch": "z",
                "chh": "c",
                "j": "zz",
            },
            vowel_map={"o.": "oo"},
        ),
    )

    # BP -> POJ
    registry.register_translator(
        "BP",
        "POJ",
        PhoneticMapping(
            initial_map={
                "b": "p",
                "p": "ph",
                "bb": "b",
                "bbn": "m",
                "dd":"d",
                "d": "t",
                "t": "th",
                "g": "k",
                "k": "kh",
                "gg": "g",
                "ggn": "ng",
                "ln" :"n",
                "z": "ch",
                "c": "chh",
                "zz": "j",
            },
            vowel_map={"oo": "o."},
        ),
    )

    # TL -> BP
    registry.register_translator(
        "TL",
        "BP",
        PhoneticMapping(
            initial_map={
                "p": "b",
                "ph": "p",
                "b": "bb",
                "m": "bbn",
                "t": "d",
                "th": "t",
                "d": "dd",
                "k": "g",
                "kh": "k",
                "ng": "ggn",              
                "n": "ln",
                "g": "gg",
                "ts": "z",
                "tsh": "c",
                "j": "zz",
            },
        ),
    )

    # BP -> TL
    registry.register_translator(
        "BP",
        "TL",
        PhoneticMapping(
            initial_map={
                "b": "p",
                "p": "ph",
                "bb": "b",
                "bbn": "m",
                "dd":"d",
                "d": "t",
                "t": "th",
                "g": "k",
                "k": "kh",
                "ggn": "ng",
                "gg": "g",
                "z": "ts",
                "c": "tsh",
                "zz": "j",
            },
        ),
    )

    # --- Cross-Group (POJ <-> PUJ) ---

    # POJ -> PUJ
    registry.register_translator(
        "POJ",
        "PUJ",
        PhoneticMapping(
            initial_map={
                "chh": lambda init, vowel: "chh" if vowel[0] in ("i", "e") else "tsh",
                "ch": lambda init, vowel: "ch" if vowel[0] in ("i", "e") else "ts",
                "j": lambda init, vowel: "j" if vowel[0] in ("i", "e") else "z",
            },
            vowel_map={"oo": "ou", "oa": "ua", "oe": "ue"},
        ),
    )

    # PUJ -> POJ
    registry.register_translator(
        "PUJ",
        "POJ",
        PhoneticMapping(
            initial_map={
                "tsh": "chh",
                "ts": "ch",
                "chh": "chh",
                "ch": "ch",
                "z": "j",
                "j": "j",
            },
            vowel_map={"ou": "oo", "ua": "oa", "ue": "oe"},
        ),
    )

    # --- Teochew Group (PUJ, DP) ---

    # PUJ -> DP
    registry.register_translator(
        "PUJ",
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
                "ts": "z",
                "tsh": "c",
                "ch": "z",
                "chh": "c",
                "j": "r",
            },
            vowel_map={"ur": "e", "e": "ê"},
            ending_map={"p": "b", "t": "d", "k": "g"},
        ),
    )

    # DP -> PUJ
    registry.register_translator(
        "DP",
        "PUJ",
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
                "z": lambda init, vowel: "ch" if vowel in ("i", "ê") else "ts",
                "c": lambda init, vowel: "chh" if vowel in ("i", "ê") else "tsh",
                "r": lambda init, vowel: "j" if vowel in ("i", "ê") else "z",
            },
            vowel_map={"e": "ur", "ê": "e"},
            ending_map={"b": "p", "d": "t", "g": "k"},
        ),
    )
