from __future__ import annotations

import re
import unicodedata
from collections.abc import Callable
from pathlib import Path

from scripts.processors.base import generate_modified, generate_original
from scripts.punctuation import (
    normalize_english_gloss,
    normalize_roman_reading,
    to_chinese_punctuation,
    to_roman_punctuation,
)
from scripts.wikisource.corrections import load_correction_catalog
from scripts.wikisource.postprocess import cleanup, fix_orphaned_semicolons

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

CORRECTION_CATALOG = load_correction_catalog(
    PROJECT_ROOT
    / "scripts/wikisource/007_A_Pronouncing_and_Defining_Dictionary_of_the_Swatow_Dialect.csv"
)

_HEADWORD_RE = re.compile(
    r"^\*?\s*\*\*(.+?)\*\*\s+(\S+)(?:\s+(\([^)]*\)))?(?:\s+(.*?))?\s*$"
)
_HYPHEN_SPACE_RE = re.compile(r"(?<=\w)- (?=\w)")
_MARKDOWN_HEAD_PUNCTUATION_RE = re.compile(
    r"^(- \*\*)(.+?)(\*\*\s+)(.*?)(\s+—\s+)(.*)$"
)
_MARKDOWN_HEAD_ONLY_RE = re.compile(r"^(- \*\*)(.+?)(\*\*\s+)(.+)$")
_MARKDOWN_EXAMPLE_PUNCTUATION_RE = re.compile(
    r"^(\s*- \*)(.+?)(\*)(\s+—\s+)(.*)$"
)
_MARKDOWN_EXAMPLE_ONLY_RE = re.compile(r"^(\s*- \*)(.+?)(\*)$")
_CORRECTION_MARKUP_RE = re.compile(r"~~([^\n~]+)~~\(([^\n)]*)\)")

_PUJ_OCR_FIXES: dict[str, str] = {}

_BOOK_PUJ_OCR_FIXES: dict[str, dict[str, str]] = {
    "Dictionary of the Swatow dialect.djvu": {
        "n6ang": "nâng",
        "b2 tôi": "bé tôi",
        "3aⁿ": "ùaⁿ",
        "1âi": "lâi",
        "c5k": "cêk",
        "t6ng": "tn̆g",
        "al5i": "lâi",
        "ka1-thì": "ka-thì",
        "nn̄g": "n̄ng",
    },
}

_PROOFREAD_HEADWORD_FIXES: dict[str, str] = {
    "澤": "凙",
    "巿": "市",
    "賖": "賒",
    "湊": "凑",
    "簒": "篡",
    "鮔": "䱌",
    "鄷": "酆",
    "傳": "傅",
    "囁濡": "囁嚅",
    "肓": "育",
    "自已": "自己",
    "噴嚔": "噴嚏",
    "蟆蝦": "蝦蟆",
    "颳𬱽": "颴颳",
    "既": "旣",
    "減": "减",
    "劫": "刧",
    "灸": "炙",
    "巹": "卺",
    "戅": "戇",
    "㰖": "欖",
    "襤䄛": "襤褸",
    "𨤸": "釐",
    "蜾贏": "蜾蠃",
    "膿": "朧",
    "研": "硏",
    "瞬": "⿰耳舜",
    "栜": "棟",
    "瘦": "痺",
    "杷枇": "枇杷",
    "琶琵": "琵琶",
    "别": "別",
    "嗶吱": "吱嗶",
    "皮": "培",
    "蛸蟰": "蟰蛸",
    "叨絮": "絮叨",
    "失散": "散失",
    "蜓蜻": "蜻蜓",
    "菓檬": "檬菓",
    "夊": "夂",
    "遂": "瑞",
    "戌": "戍",
    "值": "値",
    "窗": "窓",
    "脫": "蛻",
    "猥": "猬",
}


def fix_proofread_headwords(text: str) -> str:
    lines: list[str] = []
    for line in text.splitlines(keepends=True):
        body = line.rstrip("\r\n")
        ending = line[len(body):]
        match = re.match(r"^(- \*\*)(.+?)(\*\*\s+.*)$", body)
        if match:
            prefix, headword, suffix = match.groups()
            body = f"{prefix}{_PROOFREAD_HEADWORD_FIXES.get(headword, headword)}{suffix}"
        lines.append(body + ending)
    return "".join(lines)


def _clean(text: str) -> str:
    text = re.sub(r"\[\d+\]", "", text)
    return re.sub(r"\s+", " ", text).strip()


def _normalize_preserving_corrections(
    text: str,
    converter: Callable[[str], str],
) -> str:
    corrections: list[str] = []

    def replace(match: re.Match[str]) -> str:
        old = converter(match.group(1))
        new = converter(match.group(2))
        corrections.append(f"~~{old}~~({new})")
        return f"\ue000{len(corrections) - 1}\ue001"

    protected = _CORRECTION_MARKUP_RE.sub(replace, text)
    normalized = converter(protected)
    for index, correction in enumerate(corrections):
        normalized = normalized.replace(f"\ue000{index}\ue001", correction)
    return normalized


def _normalize_english_preserving_corrections(text: str) -> str:
    normalized = _normalize_preserving_corrections(text, to_roman_punctuation)
    semantic = generate_modified(normalized)
    if semantic == normalize_english_gloss(semantic):
        return normalized
    return normalized + "."


def _normalize_reading_preserving_corrections(text: str, gloss: str) -> str:
    normalized = _normalize_preserving_corrections(text, to_roman_punctuation)
    semantic = generate_modified(normalized)
    normalized_semantic = normalize_roman_reading(semantic, generate_modified(gloss))
    if normalized_semantic == semantic:
        return normalized
    if normalized_semantic[:-1] == semantic:
        return normalized + normalized_semantic[-1]
    return normalize_roman_reading(normalized, generate_modified(gloss))


def normalize_entry_punctuation(text: str) -> str:
    out: list[str] = []
    for line in text.splitlines(keepends=True):
        body = line.rstrip("\r\n")
        ending = line[len(body):]
        match = _MARKDOWN_HEAD_PUNCTUATION_RE.match(body)
        if match:
            prefix, headword, separator, reading, dash, gloss = match.groups()
            normalized_gloss = _normalize_english_preserving_corrections(gloss)
            body = (
                f"{prefix}{_normalize_preserving_corrections(headword, to_chinese_punctuation)}"
                f"{separator}{_normalize_reading_preserving_corrections(reading, normalized_gloss)}"
                f"{dash}{normalized_gloss}"
            )
        else:
            match = _MARKDOWN_HEAD_ONLY_RE.match(body)
            if match:
                prefix, headword, separator, reading = match.groups()
                body = (
                    f"{prefix}{_normalize_preserving_corrections(headword, to_chinese_punctuation)}"
                    f"{separator}{_normalize_preserving_corrections(reading, to_roman_punctuation)}"
                )
            else:
                match = _MARKDOWN_EXAMPLE_PUNCTUATION_RE.match(body)
                if match:
                    prefix, reading, marker, dash, gloss = match.groups()
                    normalized_gloss = _normalize_english_preserving_corrections(gloss)
                    body = (
                        f"{prefix}{_normalize_reading_preserving_corrections(reading, normalized_gloss)}"
                        f"{marker}{dash}{normalized_gloss}"
                    )
                else:
                    match = _MARKDOWN_EXAMPLE_ONLY_RE.match(body)
                    if match:
                        prefix, reading, marker = match.groups()
                        body = (
                            f"{prefix}{_normalize_preserving_corrections(reading, to_roman_punctuation)}"
                            f"{marker}"
                        )
        out.append(body + ending)
    return "".join(out)


_BOOK_CORRECTION_PRE_KEYS: frozenset[tuple[str, str]] = frozenset(
    k[:2] for k in (
        *CORRECTION_CATALOG.reading,
        *CORRECTION_CATALOG.gloss,
        *CORRECTION_CATALOG.example_splits,
        *CORRECTION_CATALOG.review,
    )
)

_PROOFREAD_EXAMPLE_DELETIONS: frozenset[tuple[str, str, str]] = frozenset(
    {
        (
            "A place",
            "a seat; a post; a position; the throne; the room a thing takes up; "
            "the place it ought to be in; a classifier of persons, diginifying them.",
            "635",
        ),
    }
)

_PROOFREAD_EXAMPLE_INSERTIONS: dict[
    tuple[str, str, str], tuple[tuple[str, str], ...]
] = {
    (
        "cu ūi, chíaⁿ cŏ̤",
        "I beg you all to be seated.",
        "635",
    ): (("lîet ūi, thiaⁿ úa tàⁿ", "hear me, all of you."),),
}


_PAGE_MARKER_RE = re.compile(r"<!-- page:(\d+) -->")
_HEAD_LINE_RE = re.compile(
    r"^(- \*\*.+?\*\*\s+)(.+?)((?:\s+\([^)]*\))?(?:\s*—\s*(.*))?)$"
)
_EX_LINE_RE = re.compile(r"^(\s*- \*)(.+?)(\*(?:\s*—\s*(.*))?)$")


def _apply_correction(prefix: str, reading: str, suffix: str, gloss: str, replacement: str) -> str:
    if "; " in replacement and gloss:
        seg = replacement.split("; ")[-1].strip()
        if gloss.startswith(seg + "; "):
            return f"{prefix}{replacement}* — {gloss[len(seg) + 2:].strip()}"
    return f"{prefix}{replacement}{suffix}"


def _apply_gloss_correction(prefix: str, reading: str, suffix: str, gloss: str, replacement: str) -> str:
    if gloss and suffix.endswith(gloss):
        suffix = suffix[: -len(gloss)]
    return f"{prefix}{reading}{suffix}{replacement}"


def _apply_example_split(prefix: str, reading: str, suffix: str, gloss: str, items: list[tuple[str, str]]) -> str:
    tail = suffix[: -len(gloss)] if gloss and suffix.endswith(gloss) else suffix
    lines = [f"{prefix}{items[0][0]}{tail}{items[0][1]}"]
    lines += [f"  - *{rd}* — {gl}" for rd, gl in items[1:]]
    return "\n".join(lines)


def _apply_review_correction(
    prefix: str,
    reading: str,
    suffix: str,
    gloss: str,
    replacement: tuple[str | None, str | None],
) -> str:
    reading_replacement, gloss_replacement = replacement
    new_reading = reading if reading_replacement is None else reading_replacement
    if gloss_replacement is None:
        return f"{prefix}{new_reading}{suffix}"
    tail = suffix[: -len(gloss)] if gloss and suffix.endswith(gloss) else suffix
    if gloss_replacement:
        if not gloss and "—" not in tail:
            tail = f"{tail.rstrip()} — "
        return f"{prefix}{new_reading}{tail}{gloss_replacement}"
    tail = re.sub(r"\s*—\s*$", "", tail)
    return f"{prefix}{new_reading}{tail}"


def _headword_from_prefix(prefix: str) -> str:
    match = re.search(r"\*\*(.+?)\*\*", prefix)
    return _clean(match.group(1)) if match else ""


def _review_compatible_key(key: tuple[str, str, str]) -> tuple[str, str, str]:
    reading, gloss, page = key
    return (
        re.sub(r"-\s+", "-", reading),
        re.sub(r"-\s+", "-", gloss),
        page,
    )


def _lookup_correction(
    table: dict,
    key: tuple[str, str, str],
    *,
    allow_empty_nearby: bool = False,
):
    compatible = _review_compatible_key(key)
    for candidate in (key, compatible):
        if candidate in table:
            return table[candidate]
    if not compatible[1] and not allow_empty_nearby:
        return None
    nearby = [
        value
        for table_key, value in table.items()
        if table_key[:2] == compatible[:2]
        and abs(int(table_key[2]) - int(key[2])) <= 2
    ]
    return nearby[0] if len(nearby) == 1 else None


def _lookup_headword_correction(headword: str, key: tuple[str, str, str]):
    table = CORRECTION_CATALOG.headword_review
    compatible = _review_compatible_key(key)
    for candidate in ((headword, *key), (headword, *compatible)):
        if candidate in table:
            return table[candidate]
    nearby = [
        value
        for table_key, value in table.items()
        if table_key[0] == headword
        and table_key[1:3] == compatible[:2]
        and abs(int(table_key[3]) - int(key[2])) <= 2
    ]
    return nearby[0] if len(nearby) == 1 else None


def fix_reading_corrections(text: str) -> str:
    lines = text.split("\n")
    out: list[str] = []
    page = ""
    for line in lines:
        pm = _PAGE_MARKER_RE.search(line.strip())
        if pm:
            page = pm.group(1)
            out.append(line)
            continue
        m = _HEAD_LINE_RE.match(line)
        if m:
            prefix, reading, suffix, gloss = m.groups()
            key = (
                _clean(generate_original(reading)),
                _clean(generate_modified(gloss or "")),
                page,
            )
            headword = _headword_from_prefix(prefix)
            contextual = _lookup_headword_correction(headword, key)
            if contextual is not None:
                out.append(_apply_review_correction(prefix, reading, suffix, gloss, contextual))
                continue
            review = _lookup_correction(CORRECTION_CATALOG.review, key)
            if review is not None:
                out.append(_apply_review_correction(prefix, reading, suffix, gloss, review))
                continue
            split = _lookup_correction(CORRECTION_CATALOG.example_splits, key)
            if split is not None:
                out.append(_apply_example_split(prefix, reading, suffix, gloss, split))
                continue
            gloss_replacement = _lookup_correction(CORRECTION_CATALOG.gloss, key)
            if gloss_replacement is not None:
                out.append(_apply_gloss_correction(prefix, reading, suffix, gloss, gloss_replacement))
                continue
            replacement = _lookup_correction(CORRECTION_CATALOG.reading, key)
            out.append(_apply_correction(prefix, reading, suffix, gloss, replacement) if replacement is not None else line)
            continue
        m = _EX_LINE_RE.match(line)
        if m:
            prefix, reading, suffix, gloss = m.groups()
            key = (
                _clean(generate_original(reading)),
                _clean(generate_modified(gloss or "")),
                page,
            )
            if key in _PROOFREAD_EXAMPLE_DELETIONS:
                continue
            insertions = _PROOFREAD_EXAMPLE_INSERTIONS.get(key)
            if insertions is not None:
                out.append(line)
                out.extend(f"{prefix}{rd}* — {gl}" for rd, gl in insertions)
                continue
            review = _lookup_correction(
                CORRECTION_CATALOG.review, key, allow_empty_nearby=True
            )
            if review is not None:
                out.append(_apply_review_correction(prefix, reading, suffix, gloss, review))
                continue
            split = _lookup_correction(
                CORRECTION_CATALOG.example_splits, key, allow_empty_nearby=True
            )
            if split is not None:
                out.append(_apply_example_split(prefix, reading, suffix, gloss, split))
                continue
            gloss_replacement = _lookup_correction(
                CORRECTION_CATALOG.gloss, key, allow_empty_nearby=True
            )
            if gloss_replacement is not None:
                out.append(_apply_gloss_correction(prefix, reading, suffix, gloss, gloss_replacement))
                continue
            replacement = _lookup_correction(
                CORRECTION_CATALOG.reading, key, allow_empty_nearby=True
            )
            out.append(_apply_correction(prefix, reading, suffix, gloss, replacement) if replacement is not None else line)
            continue
        out.append(line)
    return "\n".join(out)


def _is_blank_or_marker(line: str) -> bool:
    s = line.strip()
    return s == "" or s.startswith("<!-- page:")


def _restore_orphaned_examples(lines: list[str]) -> list[str]:
    n = len(lines)
    for i in range(n):
        s = lines[i].strip()
        if not s or s.startswith((";", ":", "*", "#", "-", "|", "<")) or not s.endswith(";"):
            continue
        look = i + 1
        while look < n and _is_blank_or_marker(lines[look]):
            look += 1
        if not (look < n and lines[look].strip().startswith(":")):
            continue
        prev = i - 1
        while prev >= 0 and _is_blank_or_marker(lines[prev]):
            prev -= 1
        if prev >= 0:
            ptxt = lines[prev].strip()
            if ptxt.startswith(";") and not ptxt.endswith(";"):
                continue
            if not ptxt.startswith((";", ":", "*", "#", "-", "|", "<")):
                continue
        lines[i] = f"; {s}"
    return lines


_READING_SEG_RE = re.compile(r"^[A-Za-z0-9\u00C0-\u024F\u1E00-\u1EFF\u207F\u0300-\u036F\u00B7\s-]+$")
_READING_LIKE_RE = re.compile(r"^[A-Za-z0-9\u00C0-\u024F\u1E00-\u1EFF\u207F\u0300-\u036F\u00B7\s\-',’?;!]+$")
_DIAC_MARK_RE = re.compile(r"[\u00C0-\u024F\u1E00-\u1EFF\u207F\u0300-\u036F\u00B7]")


def _is_reading_seg(seg: str) -> bool:
    seg = seg.strip()
    if not seg or not seg[0].islower():
        return False
    if not _READING_LIKE_RE.match(seg):
        return False
    if any(separator in seg for separator in (",", ";")):
        return False
    tokens = [t for t in re.split(r"[\s,]+", seg) if t]
    if not tokens:
        return False
    marked = sum(1 for t in tokens if _DIAC_MARK_RE.search(t))
    return marked >= 1


def _extract_embedded_reading(seg: str) -> tuple[str, str] | None:
    seg = seg.strip()
    if not seg:
        return None
    if _is_reading_seg(seg):
        return "", seg
    for m in reversed(list(re.finditer(r"[,;.]\s*", seg))):
        reading = seg[m.end():].lstrip()
        leading = ""
        while reading.startswith(('"', "\u201c", "\u201d")):
            leading += reading[0]
            reading = reading[1:].lstrip()
        if _is_reading_seg(reading):
            prefix = seg[: m.start()].strip()
            if seg[m.start()] in ",;":
                prefix = prefix.rstrip(",; ")
            else:
                prefix = (prefix + seg[m.start()]).strip()
            return prefix + leading, reading
    return None


def _split_embedded_gloss(gloss: str) -> tuple[str, list[tuple[str, str]]] | None:
    parts = [p.strip() for p in gloss.split("; ")]
    for k, part in enumerate(parts):
        hit = _extract_embedded_reading(part)
        if hit is not None:
            break
    else:
        return None
    prefix, reading = hit
    gloss1 = prefix if k == 0 else "; ".join(parts[:k]) + (f" {prefix}" if prefix else "")
    readings = [reading]
    j = k + 1
    while j < len(parts) and _is_reading_seg(parts[j]):
        readings.append(parts[j])
        j += 1
    if j >= len(parts):
        return None
    subgloss = "; ".join(parts[j:])
    items = [(r, "") for r in readings[:-1]]
    items.append((readings[-1], subgloss))
    return gloss1, items


def _classify_chunk(chunk: str) -> str:
    c = chunk.strip()
    if not c:
        return "ambiguous"
    if _is_reading_seg(c.rstrip("?!.")):
        return "reading"
    if ";" in c:
        before, sep, after = c.partition(";")
        if sep and _is_reading_seg(before.strip()) and (not after.strip() or after.strip().isascii()):
            return "mixed"
    if c.isascii():
        return "english"
    return "ambiguous"


def _split_phrase_chunks(ph: str) -> list[tuple[str, str]]:
    chunks: list[str] = []
    rest = ph.strip()
    while rest:
        m = re.search(r"[?!.]\s+", rest)
        if not m:
            chunks.append(rest)
            break
        chunks.append(rest[: m.end()].strip())
        rest = rest[m.end():].strip()
    return [(_classify_chunk(c), c) for c in chunks]


def _expand_single_reading(ph: str, gl: str) -> list[tuple[str, str]]:
    hit = _split_embedded_gloss(gl)
    if hit is None:
        return [(ph, gl)]
    gloss1, items = hit
    if gloss1:
        if not gloss1.endswith((".", "?", "!")):
            gloss1 += "."
        return [(ph, gloss1)] + items
    readings = "; ".join(r for r, _ in items)
    return [(f"{ph}; {readings}".strip("; "), items[-1][1])]


def _expand_example(ph: str, gl: str) -> list[tuple[str, str]]:
    if not ph:
        return [(ph, gl)]
    chunks = _split_phrase_chunks(ph)
    if len(chunks) == 1:
        kind, t = chunks[0]
        if kind == "reading":
            return _expand_single_reading(t, gl)
        hit = _split_embedded_gloss(gl)
        if hit is not None:
            gloss1, items = hit
            if gloss1:
                return [(ph, gloss1)] + items
            readings = "; ".join(r for r, _ in items)
            return [(f"{ph}; {readings}".strip("; "), items[-1][1])]
        return [(ph, gl)]
    if chunks[0][0] not in ("reading", "mixed"):
        return [(ph, gl)]
    out: list[tuple[str, str]] = []
    pending: str | None = None
    for kind, t in chunks:
        if kind == "reading":
            if pending is not None:
                return [(ph, gl)]
            pending = t
        elif kind == "mixed":
            if pending is not None:
                return [(ph, gl)]
            before, _, after = t.partition(";")
            out.append((before.strip(), after.strip()))
        elif kind == "ambiguous":
            return [(ph, gl)]
        else:
            if pending is not None:
                out.append((pending, t))
                pending = None
            elif out:
                out[-1] = (out[-1][0], (out[-1][1] + " " + t).strip())
            else:
                return [(ph, gl)]
    if pending is None and gl:
        expanded_gloss = _expand_example(gl, "")
        if expanded_gloss != [(gl, "")] and all(reading for reading, _ in expanded_gloss):
            out.extend(expanded_gloss)
            return out
    hit = _split_embedded_gloss(gl)
    if pending is not None:
        if hit is not None:
            gloss1, items = hit
            if gloss1:
                out.append((pending, gloss1))
                out.extend(items)
            else:
                out.append((pending, items[-1][1]))
        else:
            out.append((pending, gl))
    elif hit is not None:
        gloss1, items = hit
        if gloss1:
            if out:
                out[-1] = (out[-1][0], (out[-1][1] + " " + gloss1).strip())
            else:
                out.append(("", gloss1))
            out.extend(items)
        else:
            out.extend(items)
    elif gl and out:
        out[-1] = (out[-1][0], (out[-1][1] + " " + gl).strip())
    elif gl and not out:
        out.append(("", gl))
    return out


def _split_variant_readings(phrase: str, gloss: str) -> tuple[str, str]:
    parts = gloss.split("; ")
    readings: list[str] = []
    for part in parts[:-1]:
        seg = part.strip()
        tokens = seg.split()
        non_ascii = [t for t in tokens if not t.isascii()]
        if (
            seg.isascii()
            or len(seg) > 40
            or not _READING_SEG_RE.match(seg)
            or len(non_ascii) * 2 < len(tokens)
        ):
            break
        readings.append(seg)
    if not readings:
        return phrase, gloss
    english = "; ".join(parts[len(readings) :]).strip()
    return f"{phrase}; {'; '.join(readings)}".strip(), english


def _is_reading_phrase_line(content: str) -> bool:
    c = content.strip()
    if not c.endswith(";"):
        return False
    body = c[:-1].strip()
    if not body:
        return False
    if "; " in body:
        return True
    return _DIAC_MARK_RE.search(body) is not None


def _handle_bare_colon(
    lines: list[str],
    k: int,
    defn: str,
    examples: list[tuple[str, str] | str],
) -> tuple[int, str]:
    n = len(lines)
    content = lines[k].strip().lstrip(":").strip()
    if not content:
        return k + 1, defn
    look = k + 1
    while look < n and _is_blank_or_marker(lines[look]):
        look += 1
    if look < n and lines[look].strip().startswith(":") and _is_reading_phrase_line(content):
        markers: list[str] = []
        for t in range(k + 1, look):
            if lines[t].strip().startswith("<!-- page:"):
                markers.append(lines[t].strip())
        examples.append((content.rstrip(";").strip(), lines[look].strip().lstrip(":").strip()))
        examples.extend(markers)
        return look + 1, defn
    idx = len(examples) - 1
    while idx >= 0 and isinstance(examples[idx], str):
        idx -= 1
    if idx >= 0 and isinstance(examples[idx], tuple):
        prev_ph, prev_gl = examples[idx]
        examples[idx] = (prev_ph, (prev_gl + " " + content).strip() if prev_gl else content)
    elif defn and defn.startswith(";") and defn.endswith(";") and defn.strip("; "):
        examples.append((defn.strip().strip(";").strip(), content))
        defn = ""
    elif defn:
        defn = (defn + " " + content).strip()
    return k + 1, defn


def reformat_entries(text: str) -> str:
    lines = text.split("\n")
    lines = _restore_orphaned_examples(lines)
    out: list[str] = []
    i = 0
    n = len(lines)
    while i < n:
        s = lines[i].strip()
        m = _HEADWORD_RE.match(s)
        if not m:
            if s == ";":
                i += 1
                continue
            out.append(lines[i])
            i += 1
            continue
        hanzi = m.group(1)
        latn = m.group(2) or ""
        nums = m.group(3) or ""
        trailing_phrase = re.sub(
            r"(?<=\w)\.(?=\w)", "-", (m.group(4) or "").rstrip(";").strip()
        )
        defn = trailing_phrase if trailing_phrase[:1].isupper() else ""
        if defn:
            trailing_phrase = ""
        after_head_markers: list[str] = []
        j = i + 1
        while j < n and _is_blank_or_marker(lines[j]):
            if lines[j].strip().startswith("<!-- page:"):
                after_head_markers.append(lines[j].strip())
            j += 1
        if j < n:
            cand = lines[j].strip()
            if cand.startswith("*") and not _HEADWORD_RE.match(cand):
                defn = cand.lstrip("*").strip()
                j += 1
        while j < n:
            s3 = lines[j].strip()
            if _is_blank_or_marker(lines[j]):
                if s3.startswith("<!-- page:"):
                    after_head_markers.append(lines[j].strip())
                j += 1
                continue
            if s3.startswith((";", ":", "*", "#", "-")):
                break
            defn = (defn + " " + s3).strip() if defn else s3
            j += 1
        examples: list[tuple[str, str] | str] = []
        if trailing_phrase:
            examples.append((trailing_phrase, ""))
        k = j
        while k < n:
            s2 = lines[k].strip()
            if _is_blank_or_marker(lines[k]):
                if s2.startswith("<!-- page:"):
                    examples.append(s2)
                k += 1
                continue
            if s2.startswith(";"):
                phrase = s2.lstrip(";").strip().rstrip(";").strip()
                gloss = ""
                terminated = bool(phrase) and s2.endswith(";")
                complete = terminated or (bool(phrase) and phrase.endswith(("?", "!", ".")))
                unterminated = bool(phrase) and not s2.endswith(";") and not phrase.startswith("---")
                cross_markers: list[str] = []
                post_gloss_markers: list[str] = []
                kk = k + 1
                while kk < n and _is_blank_or_marker(lines[kk]):
                    if lines[kk].strip().startswith("<!-- page:"):
                        look = kk + 1
                        while look < n and _is_blank_or_marker(lines[look]):
                            look += 1
                        if look < n and lines[look].strip().startswith(":"):
                            post_gloss_markers.append(lines[kk].strip())
                        elif (
                            unterminated
                            and look < n
                            and lines[look].strip().endswith(";")
                            and not lines[look].strip().startswith((";", ":", "*", "#", "-"))
                        ):
                            cross_markers.append(lines[kk].strip())
                        else:
                            post_gloss_markers.append(lines[kk].strip())
                    kk += 1
                if kk < n and lines[kk].strip().startswith(":"):
                    gloss = lines[kk].strip().lstrip(":").strip()
                    kk += 1
                    while kk < n and _is_blank_or_marker(lines[kk]):
                        if lines[kk].strip().startswith("<!-- page:"):
                            post_gloss_markers.append(lines[kk].strip())
                        kk += 1
                    if kk < n:
                        nxt = lines[kk].strip()
                        if nxt and not nxt.startswith((";", ":", "*", "#", "-")):
                            look = kk + 1
                            while look < n and (lines[look].strip() == "" or lines[look].strip().startswith("<!-- page:")):
                                look += 1
                            if not (look < n and lines[look].strip().endswith(";") and not lines[look].strip().startswith((";", ":", "*", "#", "-"))):
                                gloss = (gloss + " " + nxt).strip()
                                kk += 1
                    if phrase and not unterminated:
                        pre_key = (_clean(generate_original(phrase)), _clean(generate_modified(gloss)))
                        if pre_key not in _BOOK_CORRECTION_PRE_KEYS:
                            phrase, gloss = _split_variant_readings(phrase, gloss)
                    k = kk
                else:
                    while kk < n:
                        if _is_blank_or_marker(lines[kk]):
                            if lines[kk].strip().startswith("<!-- page:"):
                                if complete:
                                    post_gloss_markers.append(lines[kk].strip())
                                elif phrase:
                                    examples.append((phrase, ""))
                                    examples.append(lines[kk].strip())
                                    phrase = ""
                            kk += 1
                            continue
                        nxt = lines[kk].strip()
                        if nxt.startswith((";", ":", "*", "#", "-")):
                            break
                        if cross_markers and nxt.endswith(";"):
                            nxt = nxt.rstrip(";").strip()
                        if complete:
                            gloss = (gloss + " " + nxt).strip() if gloss else nxt
                        elif phrase.endswith("-"):
                            phrase = (phrase + nxt).strip()
                        else:
                            phrase = (phrase + " " + nxt).strip()
                        kk += 1
                        while kk < n and _is_blank_or_marker(lines[kk]):
                            if lines[kk].strip().startswith("<!-- page:"):
                                post_gloss_markers.append(lines[kk].strip())
                            kk += 1
                        if kk < n and lines[kk].strip().startswith(":"):
                            gloss = lines[kk].strip().lstrip(":").strip()
                            kk += 1
                            while kk < n and _is_blank_or_marker(lines[kk]):
                                if lines[kk].strip().startswith("<!-- page:"):
                                    post_gloss_markers.append(lines[kk].strip())
                                kk += 1
                            break
                    k = kk
                examples.extend(cross_markers)
                examples.append((phrase, gloss))
                examples.extend(post_gloss_markers)
            elif s2.startswith(":"):
                k, defn = _handle_bare_colon(lines, k, defn, examples)
            else:
                break
        expanded: list[tuple[str, str] | str] = []
        for item in examples:
            if not isinstance(item, tuple):
                expanded.append(item)
                continue
            ph, gl = item
            pre_key = (_clean(generate_original(ph)), _clean(generate_modified(gl)))
            if pre_key in _BOOK_CORRECTION_PRE_KEYS:
                expanded.append(item)
                continue
            expanded.extend(_expand_example(ph, gl))
        examples = expanded
        merged: list[tuple[str, str] | str] = []
        for item in examples:
            if not isinstance(item, tuple):
                merged.append(item)
                continue
            ph, gl = item
            if not ph:
                if gl:
                    idx = len(merged) - 1
                    while idx >= 0 and isinstance(merged[idx], str):
                        idx -= 1
                    if idx >= 0 and isinstance(merged[idx], tuple) and not merged[idx][1]:
                        prev_ph, _ = merged[idx]
                        merged[idx] = (prev_ph, gl)
                continue
            if re.fullmatch(r"\d+", ph):
                if merged and isinstance(merged[-1], tuple):
                    ph0, gl0 = merged[-1]
                    merged[-1] = (ph0, (gl0 + " " + ph).strip() if gl0 else ph)
                elif defn:
                    defn = (defn + " " + ph).strip()
                else:
                    merged.append(item)
            else:
                merged.append(item)
        examples = merged
        head = f"- **{hanzi}** {latn} {nums}"
        if defn:
            head += f" — {defn}"
        out.append(head)
        out.extend(after_head_markers)
        for item in examples:
            if isinstance(item, str):
                out.append(item)
            else:
                ph, gl = item
                if gl:
                    out.append(f"  - *{ph}* — {gl}")
                else:
                    out.append(f"  - *{ph}*")
        i = k
    return "\n".join(out)


def convert_section_titles(text: str) -> str:
    lines = text.split("\n")
    out: list[str] = []
    i = 0
    n = len(lines)
    in_body = False
    pending_title: str | None = None
    while i < n:
        s = lines[i].strip()
        if not in_body:
            if s == "PREFACE.":
                in_body = True
                out.append(f"## {s}")
            else:
                out.append(lines[i])
            i += 1
            continue
        if pending_title is not None:
            if s == "":
                out.append("")
                i += 1
                continue
            if s == "of the":
                pending_title += " OF THE"
                i += 1
                continue
            if s.startswith("SWATOW DIALECT"):
                out.append(f"## {pending_title} SWATOW DIALECT.")
                pending_title = None
                i += 1
                continue
            out.append(f"## {pending_title}")
            pending_title = None
            continue
        if s == "ALPHABETIC DICTIONARY":
            pending_title = s
            i += 1
            continue
        if s in ("Vowels.", "Consonants."):
            out.append(f"**{s}**")
            i += 1
            continue
        if s == "The radicals.—jī-bó̤.":
            out.append(f"### {s}")
            i += 1
            continue
        if s and s.endswith(".") and s == s.upper() and len(s) > 3 \
                and not s.startswith(("-", "*", "#", ";", ":", "|")) \
                and not re.match(r"^\d", s):
            level = 2 if s in ("PREFACE.", "INTRODUCTION.") else 3
            out.append(f"{'#' * level} {s}")
            i += 1
            continue
        out.append(lines[i])
        i += 1
    return "\n".join(out)


def fix_puj_ocr_digits(text: str, title: str) -> str:
    fixes = {**_PUJ_OCR_FIXES, **_BOOK_PUJ_OCR_FIXES.get(title, {})}
    for wrong, correct in fixes.items():
        text = text.replace(wrong, correct)
    return text


def preprocess_before_corrections(text: str, title: str = "") -> str:
    text = fix_puj_ocr_digits(text, title)
    out = reformat_entries(text)
    out = fix_proofread_headwords(out)
    out = fix_orphaned_semicolons(out)
    out = convert_section_titles(out)
    return cleanup(out)


def postprocess(text: str, title: str = "") -> str:
    out = preprocess_before_corrections(text, title)
    out = fix_reading_corrections(out)
    out = _HYPHEN_SPACE_RE.sub("-", out)
    out = normalize_entry_punctuation(out)
    out = re.sub(r"\n{3,}", "\n\n", out)
    out = re.sub(r"(?:\n---\n){2,}", "\n---\n", out)
    out = re.sub(r"\n{3,}", "\n\n", out)
    return unicodedata.normalize("NFC", out.strip()) + "\n"
