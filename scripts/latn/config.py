"""Configuration classes for latn systems."""

from typing import Dict, Optional, Any, Tuple, List
from dataclasses import dataclass, field


@dataclass
class LatnSystemConfig:
    """Configuration for a latn system."""

    name: str
    """System name (e.g., 'PUJ', 'POJ')"""

    description: str
    """Description of the latn system"""

    vowel_dict: Dict[str, str]
    """Mapping of vowel+tone (e.g., 'a2') to marked vowel character (e.g., 'á')"""

    nasal_endings: List[str] = field(default_factory=lambda: ["m", "n", "ng"])
    """Nasal endings that need special handling"""

    entering_endings: List[str] = field(default_factory=lambda: ["p", "t", "k", "h"])
    """Entering tone (入声) endings that identify tone 4/8"""

    # Advanced: Mapping for complex syllable endings if needed (e.g., 'ah8' -> 'a̍h')
    complex_syllable_map: Optional[Dict[str, str]] = None

    # Priority for marking tones on vowels or consonants
    tone_mark_priority: List[str] = field(
        default_factory=lambda: ["a", "o", "u", "e", "i", "ur", "n", "m"]
    )

    # Reverse mapping: marked char -> (base_char, tone_num)
    reverse_vowel_map: Optional[Dict[str, Tuple[str, int]]] = None

    # Reverse mapping for complex syllables: marked syllable end -> base_end + tone
    reverse_complex_map: Optional[Dict[str, Tuple[str, int]]] = None

    syllable_mappings: Dict[str, str] = field(default_factory=dict)
    """Extra mappings from marked symbols to keyboard symbols (e.g., {'ⁿ': 'nn'})"""

    def __post_init__(self):
        """Build reverse mappings automatically from forward mappings."""
        if self.reverse_vowel_map is None:
            self.reverse_vowel_map = {}
            for key, marked_vowel in self.vowel_dict.items():
                if len(key) >= 2 and key[-1].isdigit():
                    tone_num = int(key[-1])
                    base_vowel = key[:-1]
                    if marked_vowel not in self.reverse_vowel_map:
                        self.reverse_vowel_map[marked_vowel] = (base_vowel, tone_num)
        
        # Sort reverse_vowel_map by key length descending to handle multi-char vowels (like o͘)
        self.reverse_vowel_map = dict(
            sorted(self.reverse_vowel_map.items(), key=lambda x: len(x[0]), reverse=True)
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
                sorted(self.reverse_complex_map.items(), key=lambda x: len(x[0]), reverse=True)
            )

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LatnSystemConfig":
        """Create config from dictionary."""
        return cls(**data)
