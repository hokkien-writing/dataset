from __future__ import annotations

import re
import unicodedata

from scripts.wikisource.postprocess import cleanup, fix_orphaned_semicolons

_HEADWORD_RE = re.compile(r"^\*?\s*\*\*(.+?)\*\*\s+(\S+)(?:\s+(\([^)]*\)))?\s*$")

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
    },
}


def _is_blank_or_marker(line: str) -> bool:
    s = line.strip()
    return s == "" or s.startswith("<!-- page:")


def reformat_entries(text: str) -> str:
    lines = text.split("\n")
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
        trailing_phrase = ""
        defn = ""
        pre_head_markers: list[str] = []
        post_entry_markers: list[str] = []
        j = i + 1
        while j < n and _is_blank_or_marker(lines[j]):
            if lines[j].strip().startswith("<!-- page:"):
                pre_head_markers.append(lines[j])
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
                    pre_head_markers.append(lines[j])
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
                    post_entry_markers.append(lines[k])
                k += 1
                continue
            if s2.startswith(";"):
                phrase = s2.lstrip(";").strip().rstrip(";").strip()
                gloss = ""
                kk = k + 1
                while kk < n and _is_blank_or_marker(lines[kk]):
                    if lines[kk].strip().startswith("<!-- page:"):
                        look = kk + 1
                        while look < n and _is_blank_or_marker(lines[look]):
                            look += 1
                        if look < n and lines[look].strip().startswith(":"):
                            post_entry_markers.append(lines[kk])
                        else:
                            examples.append((phrase, ""))
                            examples.append(lines[kk].strip())
                            phrase = ""
                    kk += 1
                if kk < n and lines[kk].strip().startswith(":"):
                    gloss = lines[kk].strip().lstrip(":").strip()
                    kk += 1
                    while kk < n and _is_blank_or_marker(lines[kk]):
                        if lines[kk].strip().startswith("<!-- page:"):
                            post_entry_markers.append(lines[kk])
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
                    k = kk
                else:
                    while kk < n:
                        if _is_blank_or_marker(lines[kk]):
                            if lines[kk].strip().startswith("<!-- page:"):
                                if phrase:
                                    examples.append((phrase, ""))
                                examples.append(lines[kk].strip())
                                phrase = ""
                            kk += 1
                            continue
                        nxt = lines[kk].strip()
                        if nxt.startswith((";", ":", "*", "#", "-")):
                            break
                        phrase = (phrase + " " + nxt).strip()
                        kk += 1
                        while kk < n and _is_blank_or_marker(lines[kk]):
                            if lines[kk].strip().startswith("<!-- page:"):
                                post_entry_markers.append(lines[kk])
                            kk += 1
                        if kk < n and lines[kk].strip().startswith(":"):
                            gloss = lines[kk].strip().lstrip(":").strip()
                            kk += 1
                            while kk < n and _is_blank_or_marker(lines[kk]):
                                if lines[kk].strip().startswith("<!-- page:"):
                                    post_entry_markers.append(lines[kk])
                                kk += 1
                            break
                    k = kk
                examples.append((phrase, gloss))
            elif s2.startswith(":"):
                k += 1
            else:
                break
        merged: list[tuple[str, str] | str] = []
        for item in examples:
            if isinstance(item, tuple) and re.fullmatch(r"\d+", item[0]):
                if merged and isinstance(merged[-1], tuple):
                    ph, gl = merged[-1]
                    merged[-1] = (ph, (gl + " " + item[0]).strip() if gl else item[0])
                elif defn:
                    defn = (defn + " " + item[0]).strip()
                else:
                    merged.append(item)
            else:
                merged.append(item)
        examples = merged
        out.extend(pre_head_markers)
        head = f"- **{hanzi}** {latn} {nums}"
        if defn:
            head += f" — {defn}"
        out.append(head)
        for item in examples:
            if isinstance(item, str):
                out.append(item)
            else:
                ph, gl = item
                if gl:
                    out.append(f"  - *{ph}* — {gl}")
                else:
                    out.append(f"  - *{ph}*")
        out.extend(post_entry_markers)
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


def postprocess(text: str, title: str = "") -> str:
    text = fix_puj_ocr_digits(text, title)
    out = reformat_entries(text)
    out = fix_orphaned_semicolons(out)
    out = convert_section_titles(out)
    out = cleanup(out)
    out = re.sub(r"\n{3,}", "\n\n", out)
    out = re.sub(r"(?:\n---\n){2,}", "\n---\n", out)
    out = re.sub(r"\n{3,}", "\n\n", out)
    return out.strip() + "\n"
