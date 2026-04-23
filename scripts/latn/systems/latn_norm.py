"""LATN_NORM (Normalized Latin) system configuration.

A normalized intermediate system based on PUJ, used as a pivot for
cross-system conversion. Differences from PUJ:
  - ts/tsh unified to ch/chh
  - iou normalized to iau
  - z/j unified to j
"""

from scripts.latn.config import LatnSystemConfig


def create_config() -> LatnSystemConfig:
    vowels = {
        "a": "a1 a2 a3 a4 a5 a6 a7 a8",
        "e": "e1 e2 e3 e4 e5 e6 e7 e8",
        "i": "i1 i2 i3 i4 i5 i6 i7 i8",
        "o": "o1 o2 o3 o4 o5 o6 o7 o8",
        "u": "u1 u2 u3 u4 u5 u6 u7 u8",
        "ur": "ur1 ur2 ur3 ur4 ur5 ur6 ur7 ur8",
        "n": "n1 n2 n3 n4 n5 n6 n7 n8",
        "m": "m1 m2 m3 m4 m5 m6 m7 m8",
    }

    return LatnSystemConfig.from_simple_vowels(
        name="LATN_NORM",
        description="Normalized Latin (PUJ-based pivot, ts→ch, tsh→chh)",
        vowels=vowels,
        initials=[
            "chh",
            "ch",
            "ph",
            "th",
            "kh",
            "ng",
            "p",
            "b",
            "m",
            "t",
            "n",
            "l",
            "k",
            "g",
            "h",
            "s",
            "j",
        ],
        nasal_endings=["m", "n", "ng", "nn"],
        entering_endings=["nnh", "p", "t", "k", "h"],
        tone_mark_priority=[],
    )
