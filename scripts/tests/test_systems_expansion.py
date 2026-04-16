"""Tests for expanded latn systems and translators."""

from scripts.latn import create_translator, list_systems


def test_hokkien_conversions():
    print("\n--- Testing Hokkien Group ---")

    poj_to_tl = create_translator("POJ", "TL")
    tl_to_poj = create_translator("TL", "POJ")

    samples = [
        ("sió-chiá", "sió-tsiá"),
        ("tâi-oân", "tâi-uân"),
        ("chiah-pùn", "tsiah-pùn"),
    ]

    for poj, tl_exp in samples:
        tl_out = poj_to_tl.translate(poj)
        poj_out = tl_to_poj.translate(tl_exp)
        print(f"POJ: {poj} -> TL: {tl_out} (Expected: {tl_exp})")
        print(f"TL: {tl_exp} -> POJ: {poj_out} (Expected: {poj})")
        assert tl_out == tl_exp
        assert poj_out == poj

    poj_to_bp = create_translator("POJ", "BP")
    bp_to_poj = create_translator("BP", "POJ")

    samples_bp = [
        ("ha̍k-sing", "hák-sīng"),
        ("lán-lâng", "lǎn-láng"),
    ]

    for poj, bp_exp in samples_bp:
        bp_out = poj_to_bp.translate(poj)
        poj_out = bp_to_poj.translate(bp_exp)
        print(f"POJ: {poj} -> BP: {bp_out} (Expected: {bp_exp})")
        print(f"BP: {bp_exp} -> POJ: {poj_out} (Expected: {poj})")
        assert bp_out == bp_exp
        assert poj_out == poj


def test_teochew_initials():
    print("\n--- Testing Teochew Initials (PUJ <-> DP) ---")

    puj_to_dp = create_translator("PUJ", "DP")
    dp_to_puj = create_translator("DP", "PUJ")

    samples = [
        ("pang", "bang1"),
        ("phang", "pang1"),
        ("bang", "bhang1"),
        ("tang", "dang1"),
        ("thang", "tang1"),
        ("kang", "gang1"),
        ("khang", "kang1"),
        ("gang", "ghang1"),
        ("tsang", "zang1"),
        ("tshang", "cang1"),
        ("chin", "zin1"),
        ("chhim", "cim1"),
        ("sang", "sang1"),
        ("hang", "hang1"),
        ("lang", "lang1"),
        ("mang", "mang1"),
        ("nang", "nang1"),
        ("ngang", "ngang1"),
    ]

    for puj, dp_exp in samples:
        dp_out = puj_to_dp.translate(puj)
        puj_out = dp_to_puj.translate(dp_exp)
        print(f"PUJ: {puj} -> DP: {dp_out} (Expected: {dp_exp})")
        print(f"DP: {dp_exp} -> PUJ: {puj_out} (Expected: {puj})")
        assert dp_out == dp_exp
        assert puj_out == puj


def test_teochew_vowels():
    print("\n--- Testing Teochew Vowels (PUJ <-> DP) ---")

    puj_to_dp = create_translator("PUJ", "DP")
    dp_to_puj = create_translator("DP", "PUJ")

    samples = [
        ("sa", "sa1"),
        ("sê", "sê5"),
        ("si", "si1"),
        ("so", "so1"),
        ("su", "su1"),
        ("sṳ", "se1"),
    ]

    for puj, dp_exp in samples:
        dp_out = puj_to_dp.translate(puj)
        puj_out = dp_to_puj.translate(dp_exp)
        print(f"PUJ: {puj} -> DP: {dp_out} (Expected: {dp_exp})")
        print(f"DP: {dp_exp} -> PUJ: {puj_out} (Expected: {puj})")
        # Note: DP uses se5 for ê tone 5, sê5 is not a valid DP notation
        # DP uses e with digit (no circumflex) for the second vowel
        assert dp_out == dp_exp
        assert puj_out == puj


def test_teochew_nasal_endings():
    print("\n--- Testing Teochew Nasal Endings (PUJ <-> DP) ---")

    puj_to_dp = create_translator("PUJ", "DP")
    dp_to_puj = create_translator("DP", "PUJ")

    samples = [
        ("sam", "sam1"),
        ("san", "san1"),
        ("sang", "sang1"),
    ]

    for puj, dp_exp in samples:
        dp_out = puj_to_dp.translate(puj)
        puj_out = dp_to_puj.translate(dp_exp)
        print(f"PUJ: {puj} -> DP: {dp_out} (Expected: {dp_exp})")
        print(f"DP: {dp_exp} -> PUJ: {puj_out} (Expected: {puj})")
        assert dp_out == dp_exp
        assert puj_out == puj


def test_teochew_entering_endings():
    print("\n--- Testing Teochew Entering Endings (PUJ <-> DP) ---")

    puj_to_dp = create_translator("PUJ", "DP")
    dp_to_puj = create_translator("DP", "PUJ")

    samples = [
        ("sap", "sab4"),
        ("sat", "sad4"),
        ("sak", "sag4"),
        ("sah", "sah4"),
    ]

    for puj, dp_exp in samples:
        dp_out = puj_to_dp.translate(puj)
        puj_out = dp_to_puj.translate(dp_exp)
        print(f"PUJ: {puj} -> DP: {dp_out} (Expected: {dp_exp})")
        print(f"DP: {dp_exp} -> PUJ: {puj_out} (Expected: {puj})")
        assert dp_out == dp_exp
        assert puj_out == puj


if __name__ == "__main__":
    print(f"Available systems: {list_systems()}")
    try:
        test_hokkien_conversions()
        test_teochew_initials()
        test_teochew_vowels()
        test_teochew_nasal_endings()
        test_teochew_entering_endings()
    except AssertionError as e:
        print(f"\nTest failed!")
        exit(1)
