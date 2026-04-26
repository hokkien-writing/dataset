---
name: tone-mark-rules
description: Use when adding or fixing tone mark placement rules for a romanization system, or when configuring tone_mark_priority and vowels in a latn system config. Applies when analyzing real corpus data to extract diacritic placement patterns.
---

# Tone Mark Rules Discovery & Implementation

## Overview

Tone mark placement in romanization systems (PUJ, POJ, TL, etc.) follows specific rules about **which vowel letter** in a syllable receives the diacritic. These rules are discovered by analyzing real corpus data, then codified into the `tone_mark_priority` list and composite `vowels` dict in each system's config.

**Critical**: Some systems (like PUJ) have **different rules for vowel-initial vs consonant-initial syllables**. Always check for this distinction when analyzing corpus data.

## When to Use

- Adding a new romanization system to the latn framework
- Fixing incorrect tone mark placement in an existing system
- When `to_handwriting()` puts the diacritic on the wrong vowel
- When round-trip `to_handwriting() → to_keyboard()` breaks for multi-vowel syllables

## Core Pattern

### Step 1: Extract Patterns from Corpus Data

Use a reference CSV (e.g., Handbook of the Swatow Vernacular) to statistically determine which vowel carries the tone mark for each rhyme pattern. **Separate vowel-initial from consonant-initial syllables** to detect different behaviors.

```python
import csv, re, unicodedata
from collections import defaultdict

with open('export/books/<corpus>.csv', encoding='utf-8') as f:
    rows = list(csv.DictReader(f))

syllables = set()
for row in rows:
    puj = row.get('puj', '')
    tokens = re.findall(r"[A-Za-z\u00E0-\u024F\u0300-\u036F\u1E00-\u1EFF\u207F]+", puj)
    for t in tokens:
        if len(t) > 1:
            nfd = unicodedata.normalize('NFD', t)
            has_mark = any(unicodedata.category(c).startswith('M') for c in nfd)
            if has_mark:
                syllables.add(t)

initials_longest = sorted(['tsh','chh','ts','ch','ph','th','kh','ng',
    'p','b','m','t','n','l','k','g','h','s','j','z'], key=len, reverse=True)

def analyze(syl):
    low = syl.lower()
    initial = ''
    for ini in initials_longest:
        if low.startswith(ini):
            initial = ini
            break
    rhyme = syl[len(initial):].lower() if initial else syl.lower()
    is_vi = (initial == '')

    nfd = unicodedata.normalize('NFD', rhyme)
    bases = []
    for c in nfd:
        if not unicodedata.category(c).startswith('M'):
            bases.append((c, False))
        elif bases:
            bases[-1] = (bases[-1][0], True)
    base = ''.join(b for b, _ in bases)
    marked = [b for b, m in bases if m]
    return base, marked[0] if marked else None, is_vi

# Compare vowel-initial vs consonant-initial for each rhyme
vi_marks = defaultdict(lambda: defaultdict(int))
ci_marks = defaultdict(lambda: defaultdict(int))
for syl in syllables:
    base, mark, is_vi = analyze(syl)
    if mark:
        if is_vi:
            vi_marks[base][mark] += 1
        else:
            ci_marks[base][mark] += 1

# Show discrepancies
for rhyme in sorted(set(list(vi_marks.keys()) + list(ci_marks.keys()))):
    vi = vi_marks[rhyme]
    ci = ci_marks[rhyme]
    if vi and ci:
        vi_dom = max(vi, key=vi.get)
        ci_dom = max(ci, key=ci.get)
        if vi_dom != ci_dom:
            print(f"  {rhyme}: vowel-initial→{vi_dom}, consonant-initial→{ci_dom}")
```

### Step 2: Identify Composite Vowel Rules

Filter for rhymes with 2+ vowels where the default priority would place the mark incorrectly. These need composite entries in the `vowels` dict.

Key question: **Does the rhyme have a different mark target than what simple vowel priority would produce?**

### Step 3: Add Composite Vowel Entries

For each composite rhyme that needs special handling, add an entry to the `vowels` dict. The composite entry defines where the mark goes for **consonant-initial syllables** (the default path):

```python
vowels = {
    "a": "a á à a â ã ā a̍",
    "e": "e é è e ê ẽ ē e̍",
    "i": "i í ì i î ĩ ī i̍",
    "o": "o ó ò o ô õ ō o̍",
    "u": "u ú ù u û ũ ū u̍",
    "ur": "ṳ ṳ́ ṳ̀ ṳ ṳ̂ ṳ̃ ṳ̄ ṳ̍",
    "n": "n ń ǹ n n̂ ñ n̄ n̍",
    "m": "m ḿ m̀ m m̂ m̃ m̄ m̍",
    "ua":   "ua úa ùa ua ûa ũa ūa u̍a",         # consonant-init: mark on u
    "uaⁿ":  "uaⁿ úaⁿ ùaⁿ uaⁿ ûaⁿ ũaⁿ ūaⁿ u̍aⁿ", # consonant-init: mark on u
    "uai":  "uai uái uài uai uâi uãi uāi ua̍i",   # mark on a
    "uan":  "uan uán uàn uan uân uãn uān ua̍n",   # mark on a
    "uang": "uang uáng uàng uang uâng uãng uāng ua̍ng", # mark on a
}
```

### Step 4: Order tone_mark_priority (longest match first)

Composite entries must appear **before** their shorter substrings:

```python
tone_mark_priority=[
    "uai",   # ua + i ending → mark on a
    "uan",   # ua + n ending → mark on a
    "uang",  # ua + ng ending → mark on a
    "uaⁿ",   # ua + nasal → mark on u (consonant-init)
    "ua",    # bare ua → mark on u (consonant-init)
    "a", "o", "ur", "u", "e", "i", "n", "m",
]
```

### Step 5: Handle Vowel-Initial Overrides

When corpus data shows vowel-initial syllables behave differently, use `vowel_initial_overrides`. This dict maps `{rhyme+tone}` → handwriting form for syllables with no initial consonant.

```python
vowel_initial_overrides={
    # ua bare: vowel-init marks a (not u)
    "ua1": "ua", "ua2": "uá", "ua3": "uà", "ua4": "ua",
    "ua5": "uâ", "ua6": "uã", "ua7": "uā", "ua8": "ua̍",
    # au: vowel-init marks u (not a)
    "au1": "au", "au2": "aú", "au3": "aù", "au4": "au",
    "au5": "aû", "au6": "aũ", "au7": "aū", "au8": "au̍",
    # ue bare: vowel-init marks e (not u)
    "ue1": "ue", "ue2": "ué", "ue3": "uè", "ue4": "ue",
    "ue5": "uê", "ue6": "uẽ", "ue7": "uē", "ue8": "ue̍",
    # uaⁿ: vowel-init marks a (not u)
    "uaⁿ1": "uaⁿ", "uaⁿ2": "uáⁿ", "uaⁿ3": "uàⁿ", "uaⁿ4": "uaⁿ",
    "uaⁿ5": "uâⁿ", "uaⁿ6": "uãⁿ", "uaⁿ7": "uāⁿ", "uaⁿ8": "ua̍ⁿ",
}
```

### Step 6: Handle Entering Tones (入聲)

When `entering_tone_mark_before_ending=True`, tone marks for syllables ending in p/t/k/h are placed on the vowel **before the ending** (scanning right-to-left), overriding normal priority. This requires the converter-level config, not vowel entries.

### Step 7: Handle Nasalization Suffix

`syllable_mappings` (e.g., `{"ⁿ": "nn"}`) must be applied **before** tone mark matching in `to_handwriting()`, so that `uann` becomes `uaⁿ` first, allowing the `uaⁿ` composite entry to match correctly instead of `uan`.

## PUJ Rules (Reference)

Derived from 8000+ entries in Handbook of the Swatow Vernacular:

### Consonant-Initial (輔音聲母)

| Pattern | Mark on | Example | Corpus % |
|---------|---------|---------|----------|
| 含 a 複合韻 (ai, ia, oi, ou...) | **a** | ái, iá, ói, óu | 97-100% |
| au | **a** | áu, khàu, tsáu | 100% |
| ua + ending (i/n/ng) | **a** | uái, uân, uáng | 87-100% |
| ua bare | **u** | Búa, Hûa, Tūa | 87% |
| uaⁿ | **u** | Hùaⁿ, Kùaⁿ, Tùaⁿ | 84% |
| ie series | **e** | ié, ién, iéⁿ | 95-100% |
| iu, ui, ue, ou, oi | **前元音** | iú, úi, úe, óu, ói | 90-98% |
| ng | **n** | n̂g | 100% |
| m (syllabic) | **m** | ḿ | 100% |
| entering (p/t/k/h) | **韻尾前元音** | ua̍h, ue̍h, ia̍h, ie̍h | 93-100% |

### Vowel-Initial (零聲母)

| Pattern | Mark on | Example | Corpus % |
|---------|---------|---------|----------|
| ua bare | **a** | uá, uâ, uà | 100% |
| au | **u** | aú, aû, aù | 88% |
| ue bare | **e** | ué, uê, uē | 63% |
| uaⁿ | **a** | uáⁿ, uâⁿ, uàⁿ | 67% |
| uan, uang | **a** | uân, uâng | 100% |

## Common Mistakes

| Mistake | Symptom | Fix |
|---------|---------|-----|
| Ignoring vowel-initial distinction | `ua2→úa` for vowel-init (wrong, should be `uá`) | Add `vowel_initial_overrides` |
| Missing composite entry | `uai2→úai` (wrong) instead of `uái` | Add `"uai"` to vowels dict |
| Wrong priority order | `au2→aú` instead of `áu` | Put `"a"` before `"u"` in priority |
| `uann` matches `uan` | `uann2→uáⁿ` instead of `ùaⁿ` | Apply syllable_mappings before tone matching |
| `uaⁿ` treated as bare `ua` | `uann2→úaⁿ` instead of `ùaⁿ` | Add `"uaⁿ"` composite entry before `"ua"` in priority |
| `uaⁿ` mark on wrong vowel | `kuaⁿ2→kuáⁿ` instead of `kúaⁿ` | Set `uaⁿ` vowel entry to mark u |
| Entering tone on wrong vowel | `tsuah8→tsu̍ah` instead of `tsua̍h` | Set `entering_tone_mark_before_ending=True` |
| Round-trip breaks on combining chars | `úa→uá4` | Add combining mark boundary check in `to_keyboard` |

## Verification Checklist

After making changes, verify:

1. **Unit tests pass**: `python3 -m unittest discover -s scripts/tests -p "test_latn_*.py"`
2. **Round-trip integrity**: Every `to_handwriting(kb) → to_keyboard(hw) == kb`
3. **Cross-system translation**: PUJ↔DP, POJ↔PUJ round-trips unchanged
4. **Corpus spot-check**: Sample 20+ words from reference CSV and verify handwriting matches
5. **Vowel-initial vs consonant-initial**: Check both categories for affected rhymes
