from __future__ import annotations

import re
import sys
from pathlib import Path

_CJK = re.compile(r"[\u3400-\u9fff\U00020000-\U0002ffff\U00030000-\U0003ffff\uf900-\ufaff]")
_INDEX_LINE = re.compile(
    r"^(?:__NOTOC__)?"
    r"([\u3400-\u9fff\U00020000-\U0002ffff\U00030000-\U0003ffff\uf900-\ufaff]+(?:[\u3400-\u9fff\U00020000-\U0002ffff\U00030000-\U0003ffff\uf900-\ufaff]|ʻ)*)"
    r"\s*"
    r"(.*)"
    r"$"
)


def _is_cjk(ch: str) -> bool:
    return bool(_CJK.fullmatch(ch))


def _tone_symbol(t: str | None) -> str:
    if not t:
        return ""
    return t


def parse_entry_head(head: str) -> list[tuple[str, str]]:
    chars: list[tuple[str, str]] = []
    buf = ""
    tone = ""
    i = 0
    while i < len(head):
        if _is_cjk(head[i]):
            if buf and tone:
                chars.append((buf, tone))
                buf = ""
                tone = ""
            elif buf and not tone:
                chars.append((buf, ""))
                buf = ""
            buf += head[i]
            i += 1
        elif head[i] in "-1234" and buf:
            tone += head[i]
            i += 1
        else:
            i += 1
    if buf:
        chars.append((buf, tone))
    return chars


def reformat_entry(line: str) -> str:
    s = line.lstrip()
    if s.startswith("__NOTOC__"):
        s = s[len("__NOTOC__"):]
    if not s.startswith(";"):
        return line
    s = s[1:]
    colon = s.find(":")
    if colon == -1:
        return line
    head = s[:colon]
    defn = s[colon + 1:].strip()
    pairs = parse_entry_head(head)
    if not pairs:
        return line
    parts = _format_pairs(pairs)
    return "- " + " · ".join(parts) + " — " + defn


def reformat_index_line(line: str) -> str:
    s = line.lstrip()
    if s.startswith("__NOTOC__"):
        s = s[len("__NOTOC__"):]
    m = _INDEX_LINE.match(s)
    if not m:
        return line
    hanzi = m.group(1)
    rest = m.group(2).strip()
    readings = re.findall(r"\.\./([^/]+)/", rest)
    bare = re.sub(r"\.\./[^/]+/\s*", "", rest).strip()
    label = f"**{hanzi}**"
    parts = []
    if bare and bare not in readings:
        parts.append(bare)
    parts.extend(readings)
    if parts:
        return f"- {label} — " + ", ".join(parts)
    return f"- {label}"


def _format_pairs(pairs: list[tuple[str, str]]) -> list[str]:
    parts = []
    for hz, tone in pairs:
        if tone:
            parts.append(f"**{hz}** <sup>{_tone_symbol(tone)}</sup>")
        else:
            parts.append(f"**{hz}**")
    return parts


def reformat_raw_entry(line: str) -> str:
    s = line.lstrip()
    m = re.match(
        r"^([\u3400-\u9fff\U00020000-\U0002ffff\U00030000-\U0003ffff\uf900-\ufaff]+)\s+(.*)",
        s,
    )
    if not m:
        return line
    hanzi = m.group(1)
    rest = m.group(2)
    return f"- **{hanzi}** — {rest}"


def main():
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(
        "books/008_A_Chinese_and_English_Vocabulary_in_the_Tie-chiu_Dialect.md"
    )
    text = path.read_text(encoding="utf-8")
    lines = text.split("\n")
    out: list[str] = []
    pending_head: str | None = None
    pending_parts: list[str] = []

    def _flush() -> None:
        nonlocal pending_head, pending_parts
        if pending_head is None:
            return
        pairs = parse_entry_head(pending_head)
        if pairs:
            parts = _format_pairs(pairs)
            defn_str = " — ".join(pending_parts)
            if defn_str:
                out.append("- " + " · ".join(parts) + " — " + defn_str)
            else:
                out.append("- " + " · ".join(parts))
        pending_head = None
        pending_parts = []

    for ln in lines:
        s = ln.lstrip()

        # Flush pending ; entry when hitting another ; or a non-continuation line
        if pending_head is not None:
            if s.startswith(";") or s.startswith("__NOTOC__"):
                _flush()

        if s.startswith(";") or s.startswith("__NOTOC__;"):
            s2 = s
            if s2.startswith("__NOTOC__"):
                s2 = s2[len("__NOTOC__"):]
            s2 = s2[1:]
            colon = s2.find(":")
            if colon != -1:
                _flush()
                out.append(reformat_entry(ln))
                continue
            else:
                _flush()
                pending_head = s2.strip()
                pending_parts = []
                continue

        if s == "__NOTOC__":
            _flush()
            out.append("")
            continue

        if s.startswith("__NOTOC__"):
            _flush()
            rest = s[len("__NOTOC__"):].strip()
            if _is_cjk(rest[:1]):
                out.append(reformat_index_line(ln))
            else:
                out.append(rest)
            continue

        if "../" in s and _is_cjk(s[:1]) and not s.startswith((";", ":", "*", "#", "-", "|")):
            _flush()
            out.append(reformat_index_line(ln))
            continue

        # Piped wikilinks like [[../Me/|Mĕ]] lose ../ during wikitext conversion;
        # catch remaining CJK-starting lines that are not formatted
        if (_is_cjk(s[:1])
                and not s.startswith((";", ":", "*", "#", "-", "|", "=", "<", "["))):
            _flush()
            out.append(reformat_raw_entry(ln))
            continue

        if re.match(r"^={2,}\d", s):
            _flush()
            num = s.strip("= ")
            out.append(f"**{num} strokes**")
            continue

        # Handle continuation lines for pending ; entry
        if pending_head is not None:
            if s.startswith(":"):
                pending_parts.append(s[1:].strip())
                continue
            if s and not s.startswith((";", ":", "*", "#", "-", "|", "=", "<", "[")):
                pending_parts.append(s)
                continue
            _flush()

        out.append(ln)

    _flush()

    out_text = "\n".join(out)
    out_text = re.sub(r"\n{3,}", "\n\n", out_text)
    path.write_text(out_text, encoding="utf-8")
    print(f"Processed {path}: {len(lines)} lines", file=sys.stderr)


if __name__ == "__main__":
    main()
