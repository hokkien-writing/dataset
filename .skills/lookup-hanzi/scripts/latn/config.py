from typing import Callable, Dict, Optional, Any, Tuple, List, Union
from dataclasses import dataclass, field

InitialMappingValue = Union[str, Callable[[str, str], str]]


@dataclass
class PhoneticMapping:
    initial_map: Dict[str, InitialMappingValue] = field(default_factory=dict)
    vowel_map: Dict[str, str] = field(default_factory=dict)
    ending_map: Dict[str, str] = field(default_factory=dict)
    nasal_prefix: Optional[Dict[str, Tuple[str, str]]] = None
    remove_hyphens: bool = False


@dataclass
class LatnSystemConfig:
    name: str
    description: str
    vowel_dict: Dict[str, str]
    initials: List[str] = field(default_factory=list)
    nasal_endings: List[str] = field(default_factory=lambda: ["m", "n", "ng"])
    entering_endings: List[str] = field(default_factory=lambda: ["p", "t", "k", "h"])
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
        if self.reverse_vowel_map is None:
            self.reverse_vowel_map = {}
            for key, marked_vowel in self.vowel_dict.items():
                if len(key) >= 2 and key[-1].isdigit():
                    tone_num = int(key[-1])
                    base_vowel = key[:-1]
                    if marked_vowel not in self.reverse_vowel_map:
                        self.reverse_vowel_map[marked_vowel] = []
                    self.reverse_vowel_map[marked_vowel].append((base_vowel, tone_num))

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
        return cls(**data)

    @classmethod
    def from_simple_vowels(
        cls,
        name: str,
        description: str,
        vowels: Dict[str, str],
        **kwargs,
    ) -> "LatnSystemConfig":
        vowel_dict = {}
        for base, marks in vowels.items():
            mark_list = marks.split()
            for i, mark in enumerate(mark_list):
                tone_num = i + 1
                vowel_dict[f"{base}{tone_num}"] = mark

        return cls(name=name, description=description, vowel_dict=vowel_dict, **kwargs)
