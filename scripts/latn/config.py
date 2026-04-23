"""Configuration classes for latn systems."""

from typing import Callable, Dict, Optional, Any, Tuple, List, Union
from dataclasses import dataclass, field

InitialMappingValue = Union[str, Callable[[str, str], str]]


@dataclass
class PhoneticMapping:
    """Mapping of phonetic parts between systems.

    Each syllable is parsed into: initial (聲母) + vowel nucleus + ending (韻尾) + tone.
    Each part is mapped exactly once, longest match first.
    """

    initial_map: Dict[str, InitialMappingValue] = field(default_factory=dict)
    """Mapping of source initial to target initial.
    Values can be a string (simple) or a callable(initial, vowel) -> str (context-sensitive)."""

    vowel_map: Dict[str, str] = field(default_factory=dict)
    """Mapping of source vowel nucleus to target vowel nucleus."""

    ending_map: Dict[str, str] = field(default_factory=dict)
    """Mapping of source syllable ending to target ending (e.g., entering p->b)."""

    nasal_prefix: Optional[Dict[str, Tuple[str, str]]] = None
    """Map nasal ending to (vowel_prefix, remaining_ending). E.g. {"nn": ("n", ""), "nnh": ("n", "h")}"""

    remove_hyphens: bool = False
    """Whether to remove hyphens between syllables in the output"""


@dataclass
class LatnSystemConfig:
    """Configuration for a latn system."""

    name: str
    """System name (e.g., 'PUJ', 'POJ')"""

    description: str
    """Description of the latn system"""

    vowel_dict: Dict[str, str]
    """Mapping of vowel+tone (e.g., 'a2') to marked vowel character (e.g., 'á')"""

    initials: List[str] = field(default_factory=list)
    """Valid initials for this system, sorted longest-first for parsing."""

    nasal_endings: List[str] = field(default_factory=lambda: ["m", "n", "ng"])
    """Nasal endings that need special handling"""

    entering_endings: List[str] = field(default_factory=lambda: ["p", "t", "k", "h"])
    """Entering tone (入声) endings that identify tone 4/8"""

    complex_syllable_map: Optional[Dict[str, str]] = None

    tone_mark_priority: List[str] = field(
        default_factory=lambda: ["a", "o", "u", "e", "i", "ur", "n", "m"]
    )

    entering_tone_mark_before_ending: bool = False

    vowel_initial_reversed_priority: list = field(default_factory=list)

    vowel_initial_overrides: Dict[str, str] = field(default_factory=dict)

    reverse_vowel_map: Optional[Dict[str, List[Tuple[str, int]]]] = None

    reverse_complex_map: Optional[Dict[str, Tuple[str, int]]] = None

    syllable_mappings: Dict[str, str] = field(default_factory=dict)

    superscript_tones: bool = False

    def __post_init__(self):
        """Build reverse mappings automatically from forward mappings."""
        if self.reverse_vowel_map is None:
            self.reverse_vowel_map = {}
            for key, marked_vowel in self.vowel_dict.items():
                if len(key) >= 2 and key[-1].isdigit():
                    tone_num = int(key[-1])
                    base_vowel = key[:-1]
                    if marked_vowel not in self.reverse_vowel_map:
                        self.reverse_vowel_map[marked_vowel] = []
                    self.reverse_vowel_map[marked_vowel].append((base_vowel, tone_num))

        # Sort reverse_vowel_map by key length descending
        self.reverse_vowel_map = dict(
            sorted(
                self.reverse_vowel_map.items(), key=lambda x: len(x[0]), reverse=True
            )
        )

        if self.reverse_complex_map is None:
            self.reverse_complex_map = {}
            if self.complex_syllable_map:
                for base_key, marked_syllable in self.complex_syllable_map.items():
                    if base_key and base_key[-1].isdigit():
                        tone_num = int(base_key[-1])
                        base_part = base_key[:-1]
                        if marked_syllable not in self.reverse_complex_map:
                            self.reverse_complex_map[marked_syllable] = (
                                base_part,
                                tone_num,
                            )

        # Sort reverse_complex_map by key length descending
        if self.reverse_complex_map:
            self.reverse_complex_map = dict(
                sorted(
                    self.reverse_complex_map.items(),
                    key=lambda x: len(x[0]),
                    reverse=True,
                )
            )

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LatnSystemConfig":
        """Create config from dictionary."""
        return cls(**data)

    @classmethod
    def from_simple_vowels(
        cls,
        name: str,
        description: str,
        vowels: Dict[str, str],
        **kwargs,
    ) -> "LatnSystemConfig":
        """
        Create LatnSystemConfig from a simplified vowel map.

        vowels: Dict where key is base vowel (e.g. 'a') and value is a space-separated
                string of marked vowels for tones 1-8.
                Example: {"a": "a á à a â ã ā a̍"}
        """
        vowel_dict = {}
        for base, marks in vowels.items():
            mark_list = marks.split()
            for i, mark in enumerate(mark_list):
                tone_num = i + 1
                vowel_dict[f"{base}{tone_num}"] = mark

        return cls(name=name, description=description, vowel_dict=vowel_dict, **kwargs)
