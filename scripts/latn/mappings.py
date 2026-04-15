"""Default phonetic mappings between latn systems."""

from scripts.latn.config import PhoneticMapping


def register_default_translators(registry):
    """Register standard translators between Hokkien and Teochew systems."""

    # --- Hokkien Group (POJ, TL, BP) ---

    # POJ <-> TL
    registry.register_translator(
        "POJ",
        "TL",
        PhoneticMapping(
            vowel_map={"o.": "oo", "oa": "ua", "oe": "ue"},
            consonant_map={"ch": "ts", "chh": "tsh"},
        ),
    )
    registry.register_translator(
        "TL",
        "POJ",
        PhoneticMapping(
            vowel_map={"oo": "o.", "ua": "oa", "ue": "oe"},
            consonant_map={"ts": "ch", "tsh": "chh"},
        ),
    )

    # POJ <-> BP
    poj_to_bp_initials = {
        "p": "b",
        "ph": "p",
        "b": "bb",
        "t": "d",
        "th": "t",
        "k": "g",
        "kh": "k",
        "g": "gg",
        "ch": "z",
        "chh": "c",
        "j": "r",
    }
    registry.register_translator(
        "POJ",
        "BP",
        PhoneticMapping(
            vowel_map={"o.": "oo"},
            consonant_map=poj_to_bp_initials,
        ),
    )

    bp_to_poj_initials = {
        "b": "p",
        "p": "ph",
        "bb": "b",
        "d": "t",
        "t": "th",
        "g": "k",
        "k": "kh",
        "gg": "g",
        "z": "ch",
        "c": "chh",
        "r": "j",
    }
registry.register_translator(
        "DP",
        "PUJ",
        PhoneticMapping(
            vowel_map={"e": "ṳ", "ê": "e"},
            consonant_map=dp_to_puj_initials,
        ),
    )
    # TL <-> BP
    registry.register_translator(
        "TL",
        "BP",
        PhoneticMapping(
            consonant_map={
                "p": "b",
                "ph": "p",
                "b": "bb",
                "t": "d",
                "th": "t",
                "k": "g",
                "kh": "k",
                "g": "gg",
                "ts": "z",
                "tsh": "c",
                "j": "r",
            }
        ),
    )
    registry.register_translator(
        "BP",
        "TL",
        PhoneticMapping(
            consonant_map={
                "b": "p",
                "p": "ph",
                "bb": "b",
                "d": "t",
                "t": "th",
                "g": "k",
                "k": "kh",
                "gg": "g",
                "z": "ts",
                "c": "tsh",
                "r": "j",
            }
        ),
    )

    # --- Teochew Group (PUJ, DP) ---

    puj_to_dp_initials = {
        "ts": "z",
        "tsh": "c",
        "ch": "z",
        "chh": "c",
        "p": "b",
        "ph": "p",
        "b": "bh",
        "t": "d",
        "th": "t",
        "k": "g",
        "kh": "k",
        "g": "gh",
        "j": "r",
    }
    registry.register_translator(
        "PUJ",
        "DP",
        PhoneticMapping(
            vowel_map={"ṳ": "e"},
            consonant_map=puj_to_dp_initials,
        ),
    )

    dp_to_puj_initials = {
        "z": "ts",
        "c": "tsh",
        "ch": "j",
        "chh": "r",
        "b": "p",
        "p": "ph",
        "bh": "b",
        "d": "t",
        "t": "th",
        "g": "k",
        "k": "kh",
        "gh": "g",
        "j": "r",
    }
    registry.register_translator(
        "BP",
        "POJ",
        PhoneticMapping(
            vowel_map={"oo": "o."},
            consonant_map=bp_to_poj_initials,
            # Apply vowel map first, then conversion_rules to fix the context
            # Convert zin -> chin, cim -> chhim, zang -> tsang
            conversion_rules=[
                # zin -> chin
                (r"tsin", r"chin"),
                (r"tsim", r"chhim"),
                (r"tsik", r"chek"),
                # cim -> chhim
                (r"tshim", r"chhim"),
                # zang -> tsang stays as is
            ],
        ),
    )
