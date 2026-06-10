from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.processors.base import BookProcessor, Entry

_PAGE_RE = re.compile(r"<!-- page:(\d+) -->")
_TABLE_ROW_RE = re.compile(r"^\|(.+)\|\s*$")
_SEPARATOR_RE = re.compile(r"^\|[\s\-:|]+\|\s*$")
_OCR_ARTIFACT_RE = re.compile(r"~~.+?~~\(([^)]*)\)")
_OCR_ORIG_RE = re.compile(r"~~(.+?)~~\([^)]*\)")
_PLUS_PLUS_RE = re.compile(r"\+\+(.+?)\+\+")
_CJK_RE = re.compile(r"[\u4e00-\u9fff\u3400-\u4dbf]")
_SYLLABLE_RE = re.compile(
    r"[A-Za-z\u00C0-\u00FF\u0128\u0129\u0131\u02bc\u0142\u2019"
    r"\u0103\u0115\u012d\u014f\u016d\u0300-\u036f]+"
)
_BREVE_CHARS = frozenset("\u0103\u0115\u012d\u014f")
_BREVE_TRANS = str.maketrans({
    "\u0103": "a",
    "\u0115": "e",
    "\u012d": "i",
    "\u014f": "o",
    "\u016d": "u",
})
_TONE_DIGIT_RE = re.compile(r"[1-8]$")
_ENTERING_END_RE = re.compile(r"[ptk]$")
_NN_RE = re.compile(r"nn$")
_GLOTTAL_BOUNDARY_RE = re.compile(r"\u02bc(?=[bcdfgjklmnpqrstvwxyz])", re.IGNORECASE)
_M_GLOTTAL_VOWEL_RE = re.compile(r"m\u02bc(?=[aeiou])", re.IGNORECASE)
_DEAN_PUJ_OVERRIDES: dict[tuple[str, str], str] = {
    ("能", "oi"): "õi",
}
_NASAL_CODA_RE = re.compile(r"(\u00f1h?|nnh?|m|ng|n)$")
_CONSONANT_CODA_RE = re.compile(r"(ng|[ptkmn])$")


def _strip_tone(s: str) -> str:
    return _TONE_DIGIT_RE.sub("", s)


def parse_markdown(text: str) -> list[tuple[str, str, str, str, str, str]]:
    rows: list[tuple[str, str, str, str, str, str]] = []
    page = ""

    for line in text.splitlines():
        m = _PAGE_RE.match(line)
        if m:
            page = m.group(1)
            continue

        if not page:
            continue

        if _SEPARATOR_RE.match(line):
            continue

        m = _TABLE_ROW_RE.match(line)
        if not m:
            continue

        cells = [c.strip() for c in m.group(1).split("|")]
        if len(cells) < 3:
            continue

        han_raw = cells[1]
        han = _OCR_ARTIFACT_RE.sub(r"\1", han_raw)
        han = _PLUS_PLUS_RE.sub(r"\1", han)
        dean_latn_raw = cells[2]

        if not _CJK_RE.search(han):
            continue

        english_raw = cells[0]
        english = _OCR_ARTIFACT_RE.sub(r"\1", english_raw)

        rows.append((page, english, english_raw, han, han_raw, dean_latn_raw))

    return rows


def _preprocess_dean(text: str) -> str:
    text = _GLOTTAL_BOUNDARY_RE.sub("\u02bc ", text)
    text = _M_GLOTTAL_VOWEL_RE.sub("m ", text)
    return text


def split_dean_syllables(text: str) -> list[str]:
    text = _preprocess_dean(text)
    result: list[str] = []
    for word in text.split():
        result.extend(_SYLLABLE_RE.findall(word.lower()))
    return result


def normalize_dean_syllable(syllable: str) -> str:
    has_breve = bool(_BREVE_CHARS & set(syllable))
    s = syllable.lower().translate(_BREVE_TRANS)
    if has_breve and not _ENTERING_END_RE.search(s):
        s = s + "h"
    if s.startswith("gn") or s.startswith("g\u00f1"):
        s = "ng" + s[2:]
    s = s.replace("\u00f1", "n")
    s = s.replace("\u02bc", "")
    s = s.replace("aou", "au")
    s = s.replace("yiw", "iu")
    s = s.replace("iw", "iu")
    s = s.replace("ow", "ou")
    s = s.replace("ey", "e")
    s = s.replace("aw", "o")
    return s


def _dean_syllable_to_latn_norm(syl: str) -> str:
    has_breve = bool(_BREVE_CHARS & set(syl))
    s = syl.lower().translate(_BREVE_TRANS)
    if has_breve and not _ENTERING_END_RE.search(s):
        s = s + "h"
    is_nasal = "\u00f1" in s
    s = s.replace("p\u00f1", "ph")
    if s.startswith("gn") or s.startswith("g\u00f1"):
        if "\u00f1" not in s[2:]:
            is_nasal = False
        s = "ng" + s[2:]
    pos = s.find("\u00f1")
    while pos >= 0:
        if pos + 1 < len(s) and s[pos + 1] not in "aeiou\u00f1":
            s = s[:pos] + "n" + s[pos + 1:]
        else:
            s = s[:pos] + s[pos + 1:]
        pos = s.find("\u00f1")
    s = s.replace("\u02bc", "")
    s = s.replace("aou", "au")
    s = s.replace("yiw", "iu")
    s = s.replace("iw", "iu")
    s = s.replace("ow", "ou")
    s = s.replace("ey", "e")
    s = s.replace("aw", "o")
    if is_nasal:
        s = s + "nn"
    s = s.replace("ur", "\u1e73")
    if len(s) > 1 and s[0] == "j" and s[1] not in "ie":
        s = "z" + s[1:]
    if s.startswith("chh") and len(s) > 3 and s[3] not in "ie":
        s = "tsh" + s[3:]
    elif s.startswith("ch") and not s.startswith("chh") and len(s) > 2 and s[2] not in "ie":
        s = "ts" + s[2:]
    return s


def dean_to_latn_norm(text: str) -> str:
    return " ".join(_dean_syllable_to_latn_norm(s) for s in split_dean_syllables(text))


def levenshtein(s1: str, s2: str) -> int:
    if len(s1) < len(s2):
        return levenshtein(s2, s1)
    if len(s2) == 0:
        return len(s1)
    prev = list(range(len(s2) + 1))
    for i, c1 in enumerate(s1):
        curr = [i + 1]
        for j, c2 in enumerate(s2):
            cost = 0 if c1 == c2 else 1
            curr.append(min(curr[j] + 1, prev[j + 1] + 1, prev[j] + cost))
        prev = curr
    return prev[-1]


def _has_combining(puj: str) -> bool:
    return any("\u0300" <= c <= "\u036f" for c in puj)


def build_han_index(reader: csv.DictReader) -> dict[str, list[tuple[str, str, int]]]:
    index: dict[str, list[tuple[str, str, int]]] = {}
    seen_sources: dict[str, set[str]] = {}
    for row in reader:
        puj = (row.get("puj") or "").strip()
        latn_norm = (row.get("latn_norm") or "").strip()
        han = (row.get("han") or "").strip()
        source = (row.get("source") or "").strip()
        if puj and latn_norm and han:
            sk = f"{han}\x00{latn_norm}"
            if sk not in seen_sources:
                seen_sources[sk] = set()
            if source and source not in seen_sources[sk]:
                seen_sources[sk].add(source)
            existing = {c[1]: i for i, c in enumerate(index.get(han, []))}
            if latn_norm in existing:
                i = existing[latn_norm]
                if not _has_combining(index[han][i][0]) and _has_combining(puj):
                    index[han][i] = (puj, latn_norm, len(seen_sources[sk]))
            else:
                index.setdefault(han, []).append((puj, latn_norm, len(seen_sources[sk])))
    return index


def _base_form(s: str) -> str:
    return _NN_RE.sub("\u00f1", _TONE_DIGIT_RE.sub("", s))


def _has_consonant_coda(s: str) -> bool:
    base = _base_form(s)
    return bool(_CONSONANT_CODA_RE.search(base))


def _common_prefix_len(a: str, b: str) -> int:
    n = min(len(a), len(b))
    for i in range(n):
        if a[i] != b[i]:
            return i
    return n


def _pre_coda(s: str) -> str:
    return _NASAL_CODA_RE.sub("", _base_form(s))


def lookup_puj_for_row(
    han_chars: list[str],
    dean_syllables: list[str],
    han_index: dict[str, list[tuple[str, str, int]]],
) -> tuple[list[str | None], set[int]]:
    n_dean = len(dean_syllables)
    n_han = len(han_chars)
    if n_dean == 0 or n_han == 0:
        return None, set()
    if n_dean > n_han:
        return None, set()
    offset = n_han - n_dean
    tail_han = han_chars[offset:]
    tail_dean = dean_syllables
    for ch in tail_han:
        if ch not in han_index:
            return None, set()
    result: list[str | None] = []
    tie_indices: set[int] = set()
    for idx, (han, raw_dean) in enumerate(zip(tail_han, tail_dean)):
        norm_dean_raw = normalize_dean_syllable(raw_dean)
        override = _DEAN_PUJ_OVERRIDES.get((han, norm_dean_raw))
        if override:
            result.append(override)
            continue
        candidates = han_index[han]
        if len(candidates) == 1:
            result.append(candidates[0][0])
        else:
            norm_dean = normalize_dean_syllable(raw_dean)
            dean_len = len(norm_dean)
            scored = [(
                levenshtein(norm_dean, _base_form(c[1])),
                _has_consonant_coda(c[1]),
                abs(len(_base_form(c[1])) - dean_len),
                -_common_prefix_len(norm_dean, _base_form(c[1])),
                -c[2],
                c,
            ) for c in candidates]
            scored.sort(key=lambda x: (x[0], x[1], x[2], x[3], x[4], x[5][0]))
            if len(scored) > 1 and scored[0][:4] == scored[1][:4]:
                tie_indices.add(idx)
            result.append(scored[0][5][0])
    return result, tie_indices


def _extract_han_chars(text: str) -> list[str]:
    return _CJK_RE.findall(text)


def _reconstruct_tail(original: str, replacements: list[str]) -> str:
    syllable_matches = list(_SYLLABLE_RE.finditer(original))
    if not syllable_matches or not replacements:
        return original
    skip = len(syllable_matches) - len(replacements)
    if skip < 0:
        skip = 0
    result = original
    offset = 0
    for i, m in enumerate(syllable_matches):
        if i >= skip and replacements:
            repl = replacements.pop(0)
            if m.group()[0].isupper() and repl:
                repl = repl[0].upper() + repl[1:]
            result = result[:m.start() + offset] + repl + result[m.end() + offset:]
            offset += len(repl) - len(m.group())
    return result


def _reconstruct(original: str, replacements: list[str]) -> str:
    if len(replacements) == len(list(_SYLLABLE_RE.finditer(original))):
        return _reconstruct_tail(original, replacements)
    return _reconstruct_tail(original, replacements)


def _differs_after_fix(raw: str, fixed: str) -> str:
    orig = _OCR_ORIG_RE.sub(r"\1", raw) if _OCR_ORIG_RE.search(raw) else raw
    orig = _PLUS_PLUS_RE.sub("", orig)
    return orig.strip() if orig.strip() and orig.strip() != fixed else ""


class Processor(BookProcessor):
    _han_index: dict[str, list[tuple[str, str, int]]] | None = None

    @classmethod
    def _load_han_index(cls) -> dict[str, list[tuple[str, str, int]]]:
        if cls._han_index is None:
            teochew_path = PROJECT_ROOT / "export" / "teochew.csv"
            with open(teochew_path, encoding="utf-8", newline="") as f:
                cls._han_index = build_han_index(csv.DictReader(f))
        return cls._han_index

    def extract_entries(self, text: str, source_name: str) -> list[Entry]:
        rows = parse_markdown(text)
        if not rows:
            return []

        han_index = self._load_han_index()
        entries: list[Entry] = []

        for page, english, english_raw, han, han_raw, dean_latn in rows:
            han_chars = _extract_han_chars(han)
            if not han_chars:
                continue

            dean_latn_clean = _OCR_ARTIFACT_RE.sub(r"\1", dean_latn)
            dean_preprocessed = _preprocess_dean(dean_latn_clean)
            dean_syllables = split_dean_syllables(dean_latn_clean)

            puj_entries = lookup_puj_for_row(han_chars, dean_syllables, han_index)
            if puj_entries[0] is None:
                norm_syllables = [_dean_syllable_to_latn_norm(s) for s in dean_syllables]
                puj = "*" + _reconstruct(dean_preprocessed, norm_syllables)
                source = f"{source_name} > rule"
            else:
                puj_list, tie_indices = puj_entries
                mixed: list[str] = []
                for i, entry in enumerate(puj_list):
                    if entry is not None:
                        mixed.append(entry)
                    else:
                        mixed.append(_dean_syllable_to_latn_norm(dean_syllables[i]))
                puj = _reconstruct(dean_preprocessed, mixed)
                if any(e is None for e in puj_list) or tie_indices:
                    puj = "*" + puj
                    source = f"{source_name} > {'rule' if any(e is None for e in puj_list) else 'tiebreak'}"
                else:
                    source = source_name

            entries.append(Entry(
                han=han,
                han_orig=_differs_after_fix(han_raw, han),
                puj=puj,
                puj_orig=dean_latn_clean,
                en=english,
                en_orig=_differs_after_fix(english_raw, english),
                source=source,
                page_num=page,
            ))

        return entries
