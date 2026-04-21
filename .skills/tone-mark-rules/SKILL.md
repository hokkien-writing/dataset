---
name: tone-mark-rules
description: Use when adding or fixing tone mark placement rules for a romanization system, or when configuring tone_mark_priority and vowels in a latn system config. Applies when analyzing real corpus data to extract diacritic placement patterns.
---

# Tone Mark Rules Discovery & Implementation

## Overview

Tone mark placement in romanization systems (PUJ, POJ, TL, etc.) follows specific rules about **which vowel letter** in a syllable receives the diacritic. These rules are discovered by analyzing real corpus data, then codified into the `tone_mark_priority` list and composite `vowels` dict in each system's config.

## When to Use

- Adding a new romanization system to the latn framework
- Fixing incorrect tone mark placement in an existing system
- When `to_handwriting()` puts the diacritic on the wrong vowel
- When round-trip `to_handwriting() → to_keyboard()` breaks for multi-vowel syllables

## Core Pattern

### Step 1: Extract Patterns from Corpus Data

Use a reference CSV (e.g., Handbook of the Swatow Vernacular) to statistically determine which vowel carries the tone mark for each rhyme pattern.

```python
import csv, re, unicodedata
from collections import defaultdict

with open('export/books/<corpus>.csv', encoding='utf-8') as f:
    rows = list(csv.DictReader(f))

# Collect single syllables with tone marks
syllables = set()
for row in rows:
    puj = row.get('puj', '')
    tokens = re.findall(r"[a-z\u00E0-\u024F\u0300-\u036F\u1E00-\u1EFF\u207F]+", puj.lower())
    for t in tokens:
        if len(t) > 1 and any(ord(c) > 0x7F for c in t):
            syllables.add(t)

# Strip initial consonants and analyze which base vowel has the mark
initials_longest = sorted(['tsh','chh','ts','ch','ph','th','kh','ng',
    'p','b','m','t','n','l','k','g','h','s','j','z'], key=len, reverse=True)

def strip_initial(syl):
    for ini in initials_longest:
        if syl.startswith(ini):
            return syl[len(ini):]
    return syl

rhyme_patterns = defaultdict(lambda: defaultdict(int))
for syl in sorted(syllables):
    rhyme = strip_initial(syl)
    nfd = unicodedata.normalize('NFD', rhyme)
    bases = []
    for c in nfd:
        if not unicodedata.category(c).startswith('M'):
            bases.append((c, False))
        elif bases:
            bases[-1] = (bases[-1][0], True)
    base_rhyme = ''.join(b for b, _ in bases)
    marked = [b for b, m in bases if m]
    if marked:
        rhyme_patterns[base_rhyme][marked[0]] += 1
```

### Step 2: Identify Composite Vowel Rules

Filter for rhymes with 2+ vowels where the default priority would place the mark incorrectly. These need composite entries in the `vowels` dict.

Key question: **Does the rhyme have a different mark target than what simple vowel priority would produce?**

### Step 3: Add Composite Vowel Entries

For each composite rhyme that needs special handling, add an entry to the `vowels` dict:

```python
vowels = {
    # ... basic vowels ...
    "ua":  "ua úa ùa ua ûa ũa ūa u̍a",       # bare ua → mark on u
    "uai": "uai uái uài uai uâi uãi uāi ua̍i", # ua+i ending → mark on a
    "uan": "uan uán uàn uan uân uãn uān ua̍n", # ua+n ending → mark on a
    "uaⁿ": "uaⁿ uáⁿ uàⁿ uaⁿ uâⁿ uãⁿ uāⁿ ua̍ⁿ", # ua+nasal → mark on a
}
```

### Step 4: Order tone_mark_priority (longest match first)

Composite entries must appear **before** their shorter substrings:

```python
tone_mark_priority=[
    "uai",   # 3-char: ua + i ending → mark on a
    "uan",   # 3-char: ua + n ending → mark on a
    "uang",  # 4-char: ua + ng ending → mark on a
    "uaⁿ",   # 3-char: ua + nasal → mark on a
    "ua",    # 2-char: bare ua → mark on u
    "a", "o", "ur", "u", "e", "i", "n", "m",
]
```

### Step 5: Handle Entering Tones (入聲)

When `entering_tone_mark_before_ending=True`, tone marks for syllables ending in p/t/k/h are placed on the vowel **before the ending** (scanning right-to-left), overriding normal priority. This requires the converter-level config, not vowel entries.

### Step 6: Handle Nasalization Suffix

`syllable_mappings` (e.g., `{"ⁿ": "nn"}`) must be applied **before** tone mark matching in `to_handwriting()`, so that `uann` becomes `uaⁿ` first, allowing the `uaⁿ` composite entry to match correctly instead of `uan`.

## PUJ Rules (Reference)

Derived from 8000+ entries in Handbook of the Swatow Vernacular:

| Pattern | Mark on | Example | Rationale |
|---------|---------|---------|-----------|
| 含 a 複合韻 (ai, au, ia, oi, ou...) | **a** | ái, áu, iá, ói | a > o > u > e > i |
| ua (bare) | **u** | úa, úe, úi | u is nucleus |
| ua + ending (i/n/ng/ⁿ) | **a** | uái, uân, uáng, kuáⁿ | a is nucleus before ending |
| ie series | **e** | ié, ién, iéⁿ | e is nucleus |
| iu, ui, ue, ou, oi | **前元音** | iú, úi, úe, óu, ói | first vowel is nucleus |
| ng | **n** | n̂g | 双字母标前 |
| m (syllabic) | **m** | ḿ | sole vowel |
| entering (p/t/k/h) | **韵尾前元音** | tsua̍h, ue̍h, ai̍h | before ending |

## Common Mistakes

| Mistake | Symptom | Fix |
|---------|---------|-----|
| Missing composite entry | `uai2→úai` (wrong) instead of `uái` | Add `"uai"` to vowels dict |
| Wrong priority order | `au2→aú` instead of `áu` | Put `"a"` before `"u"` in priority |
| `uann` matches `uan` | `uann2→uáⁿ` instead of `uáⁿ` (wa, should be `uáⁿ`) | Apply syllable_mappings before tone matching |
| `uaⁿ` treated as bare `ua` | `uann2→úaⁿ` instead of `uáⁿ` | Add `"uaⁿ"` composite entry |
| Entering tone on wrong vowel | `tsuah8→tsu̍ah` instead of `tsua̍h` | Set `entering_tone_mark_before_ending=True` |
| Round-trip breaks on combining chars | `úa→uá4` | Add combining mark boundary check in `to_keyboard` |

## Verification Checklist

After making changes, verify:

1. **Unit tests pass**: `python3 -m unittest discover -s scripts/tests -p "test_latn_*.py"`
2. **Round-trip integrity**: Every `to_handwriting(kb) → to_keyboard(hw) == kb`
3. **Cross-system translation**: PUJ↔DP, POJ↔PUJ round-trips unchanged
4. **Corpus spot-check**: Sample 20+ words from reference CSV and verify handwriting matches
