from __future__ import annotations

import re
import unicodedata


def fix_orphaned_semicolons(text: str) -> str:
    lines = text.split("\n")
    out: list[str] = []
    i = 0
    n = len(lines)
    while i < n:
        s = lines[i].strip()
        if s.startswith("<!-- page:"):
            out.append(lines[i])
            i += 1
            continue
        if s.startswith(";") and not s.startswith("; ---") and not re.fullmatch(r";\s*\d+\s*;", s):
            phrase = s.lstrip(";").strip().rstrip(";").strip()
            if phrase:
                j = i + 1
                while j < n and lines[j].strip() == "":
                    j += 1
                if j < n and lines[j].strip().startswith(":"):
                    gloss = lines[j].strip().lstrip(":").strip()
                    out.append(f"  - *{phrase}* — {gloss}" if gloss else f"  - *{phrase}*")
                    i = j + 1
                    continue
        if s.endswith(";") and not s.startswith((";", ":", "*", "#", "-")):
            phrase = s.rstrip(";").strip()
            if phrase:
                j = i + 1
                while j < n and lines[j].strip() == "":
                    j += 1
                if j < n and lines[j].strip().startswith(":"):
                    gloss = lines[j].strip().lstrip(":").strip()
                    out.append(f"  - *{phrase}* — {gloss}" if gloss else f"  - *{phrase}*")
                    i = j + 1
                    continue
        if s and not s.startswith((";", ":", "*", "#", "-")) and not s.endswith(";"):
            accumulated = s
            markers: list[str] = []
            j = i + 1
            merged = False
            while j < n:
                sj = lines[j].strip()
                if sj == "":
                    j += 1
                    continue
                if sj.startswith("<!-- page:"):
                    markers.append(sj)
                    j += 1
                    continue
                if sj.endswith(";") and not sj.startswith((";", ":", "*", "#", "-")):
                    accumulated += " " + sj.rstrip(";").strip()
                    k = j + 1
                    while k < n and lines[k].strip() == "":
                        k += 1
                    if k < n and lines[k].strip().startswith(":"):
                        gloss = lines[k].strip().lstrip(":").strip()
                        out.append(f"  - *{accumulated.strip()}* — {gloss}" if gloss else f"  - *{accumulated.strip()}*")
                        out.extend(markers)
                        i = k + 1
                        merged = True
                    break
                if sj.startswith((";", ":", "*", "#", "-")):
                    break
                accumulated += " " + sj
                j += 1
            if merged:
                continue
        out.append(lines[i])
        i += 1
    return "\n".join(out)


def cleanup(text: str) -> str:
    text = text.replace("\xa0", " ")
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Cf")
    lines = [ln.rstrip() for ln in text.split("\n")]
    out: list[str] = []
    blank = 0
    for ln in lines:
        if ln.strip() == "":
            blank += 1
            if blank <= 1:
                out.append("")
        else:
            blank = 0
            out.append(ln)
    while out and out[0] == "":
        out.pop(0)
    while out and out[-1] == "":
        out.pop()
    return "\n".join(out)
