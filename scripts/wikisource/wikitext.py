from __future__ import annotations

import re

import mwparserfromhell as mwfh
from mwparserfromhell.nodes import (
    Comment,
    ExternalLink,
    HTMLEntity,
    Tag,
    Template,
    Text,
    Wikilink,
)

_DASH_HEADER_RE = re.compile(r"^—\s*([A-Za-zÀ-ÖØ-öø-ÿ0-9ⁿ]+)\s*—$")

DROP_TPL = {
    "multicol", "multicol-break", "multicol-end",
    "anchor", "rh", "runningheader", "rvh",
    "nop", "nopt", "ts", "right", "noprint", "core",
}
HR_TPL = {"dhr", "rule", "custom rule"}
FORMATTING_TPL = {
    "sc", "asc", "center", "larger", "x-larger", "xx-larger",
    "xxx-larger", "xxxx-larger", "x-larger block", "smaller",
    "small-caps", "uc", "em", "ti", "ae", "brace2", "sfrac", "c",
}


def _positional(tpl: Template) -> list:
    return [p.value for p in tpl.params if p.name.strip().isdigit()]


def wikicode_to_text(wc) -> str:
    if wc is None:
        return ""
    parts = []
    for node in getattr(wc, "nodes", [wc]):
        parts.append(node_to_text(node))
    return "".join(parts)


def node_to_text(node) -> str:
    if isinstance(node, Text):
        return str(node)
    if isinstance(node, Template):
        return template_to_text(node)
    if isinstance(node, Wikilink):
        if node.text is not None:
            return wikicode_to_text(node.text)
        return wikicode_to_text(node.title)
    if isinstance(node, HTMLEntity):
        return node.normalize()
    if isinstance(node, Comment):
        return ""
    if isinstance(node, ExternalLink):
        if node.title is not None:
            return wikicode_to_text(node.title)
        return str(node.url)
    if isinstance(node, Tag):
        return tag_to_text(node)
    stripped = getattr(node, "strip_code", None)
    if callable(stripped):
        return stripped() or ""
    return ""


def template_to_text(tpl: Template) -> str:
    name = str(tpl.name).strip().lower()
    pos = _positional(tpl)

    if name in DROP_TPL:
        return ""
    if name == "shc":
        return wikicode_to_text(pos[0]).strip() if pos else ""
    if name == "swatow entry":
        if len(pos) >= 5:
            nums = f"({wikicode_to_text(pos[2])}|{wikicode_to_text(pos[3])}|{wikicode_to_text(pos[4])})"
            return f"**{wikicode_to_text(pos[0])}** {wikicode_to_text(pos[1])} {nums}".strip()
        if len(pos) >= 3:
            nums = f"({wikicode_to_text(pos[2])})"
            return f"**{wikicode_to_text(pos[0])}** {wikicode_to_text(pos[1])} {nums}".strip()
        if len(pos) >= 2:
            return f"**{wikicode_to_text(pos[0])}** {wikicode_to_text(pos[1])}".strip()
        return wikicode_to_text(pos[0]).strip() if pos else ""
    if name == "sic":
        if len(pos) >= 2:
            orig = wikicode_to_text(pos[0]).replace("\n", " ").strip()
            corr = wikicode_to_text(pos[1]).replace("\n", " ").strip().replace(")", "")
            return f"~~{orig}~~({corr})"
        if len(pos) == 1:
            a = wikicode_to_text(pos[0]).replace("\n", " ").strip().replace(")", "")
            return f"~~{a}~~({a})"
        return ""
    if name in ("chinese rtl", "crl"):
        return wikicode_to_text(pos[0]).strip() if pos else ""
    if name == "species name":
        return f"*{wikicode_to_text(pos[0])}*" if pos else ""
    if name == "center":
        content = wikicode_to_text(pos[0]).strip() if pos else ""
        m = _DASH_HEADER_RE.match(content)
        if m:
            return f"\n\n### {m.group(1)}\n\n"
        return content
    if name == "suspect":
        return wikicode_to_text(pos[0]).strip() if pos else ""
    if name == "illegible":
        return "[illegible]"
    if name == "hws":
        return wikicode_to_text(pos[-1]).strip() if pos else ""
    if name == "hwe":
        return ""
    if name == "br":
        return "\n"
    if name in HR_TPL:
        return "\n\n---\n\n"
    if name == "ltc tone":
        return ""
    if name in FORMATTING_TPL:
        return wikicode_to_text(pos[-1]) if pos else ""
    return wikicode_to_text(pos[-1]) if pos else ""


def tag_to_text(node: Tag) -> str:
    raw_tag = str(node.tag).strip()
    if raw_tag.lower() in ("li", "dt", "dd", "ol", "ul", "dl"):
        return str(node)
    name = raw_tag.lower()
    if name == "br":
        return "\n"
    if name in ("section", "pagequality", "ref", "references", "noinclude",
                "includeonly", "gallery", "math", "nowiki"):
        return ""
    if name in ("h1", "h2", "h3", "h4"):
        level = int(name[1])
        inner = wikicode_to_text(node.contents) if node.contents else ""
        return f"\n\n{'#' * level} {inner.strip()}\n\n"
    if node.contents is not None:
        return wikicode_to_text(node.contents)
    return ""


def preprocess(raw: str) -> str:
    text = raw
    text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)
    text = re.sub(r"<pagequality\b[^>]*>", "", text)
    text = re.sub(r"<section\b[^>]*>", "", text)
    text = re.sub(r"</section>", "", text)
    text = re.sub(r"</?noinclude>", "", text)
    text = re.sub(r"\{\{nopt?\}\}", "", text)
    return text


def _find_table_end(text: str, start: int) -> int:
    depth = 0
    i = start
    while i < len(text):
        if text[i:i + 2] == "{|":
            depth += 1
            i += 2
        elif text[i:i + 2] == "|}":
            depth -= 1
            if depth == 0:
                return i
            i += 2
        else:
            i += 1
    return -1


def _convert_templates(text: str) -> str:
    if not text:
        return ""
    return wikicode_to_text(mwfh.parse(text))


def _restore(text: str, placeholders: list[str]) -> str:
    for i, md in enumerate(placeholders):
        text = text.replace(f"@@TBL{i}@@", md)
    return text


def _process(text: str) -> str:
    parts: list[str] = []
    i = 0
    while True:
        idx = text.find("{|", i)
        if idx == -1:
            parts.append(_convert_templates(text[i:]))
            break
        parts.append(_convert_templates(text[i:idx]))
        end = _find_table_end(text, idx)
        if end == -1:
            parts.append(_convert_templates(text[idx:]))
            break
        parts.append(_table_to_markdown(text[idx:end + 2]))
        i = end + 2
    return "".join(parts)


def _convert_inner(text: str, placeholders: list[str]) -> str:
    parts: list[str] = []
    i = 0
    while True:
        idx = text.find("{|", i)
        if idx == -1:
            parts.append(text[i:])
            break
        parts.append(text[i:idx])
        end = _find_table_end(text, idx)
        if end == -1:
            parts.append(text[idx:])
            break
        md = _table_to_markdown(text[idx:end + 2])
        placeholders.append(md)
        parts.append(f"@@TBL{len(placeholders) - 1}@@")
        i = end + 2
    return "".join(parts)


def _parse_cell_line(line: str):
    is_header = line.startswith("!")
    rest = line[1:].lstrip()
    depth = 0
    for i, c in enumerate(rest):
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
        elif c == "|" and depth <= 0:
            return rest[:i], rest[i + 1:].strip(), is_header
    return "", rest.strip(), is_header


def _split_inline(line: str) -> list[str]:
    lead = line[0]
    dbl = "!!" if lead == "!" else "||"
    out: list[str] = []
    buf = ""
    depth = 0
    i = 0
    while i < len(line):
        c = line[i]
        if c == "{":
            depth += 1
            buf += c
            i += 1
        elif c == "}":
            depth -= 1
            buf += c
            i += 1
        elif depth <= 0 and line[i:i + 2] == dbl:
            out.append(buf)
            buf = lead
            i += 2
        else:
            buf += c
            i += 1
    out.append(buf)
    return out


def _md_escape(cell: str) -> str:
    return cell.replace("|", "\\|").replace("\n", " ").strip()


def _is_cjk(s: str) -> bool:
    s = s.strip()
    if not (0 < len(s) <= 6):
        return False
    return any(ord(c) > 0x2E00 for c in s)


def _parse_table_rows(block: str):
    caption = ""
    rows: list[list[list]] = []
    cur: list[list] = []
    for ln in block.split("\n"):
        s = ln.strip()
        if not s or s.startswith("{|"):
            continue
        if s.startswith("|}"):
            break
        if s.startswith("|+"):
            caption = s[2:].strip()
            continue
        if s.startswith("|-"):
            if cur:
                rows.append(cur)
                cur = []
            continue
        if s.startswith("!") or s.startswith("|"):
            for piece in _split_inline(s):
                attrs, content, is_header = _parse_cell_line(piece)
                cur.append([attrs, content, is_header])
        elif cur:
            cur[-1][1] = (cur[-1][1] + " " + s).strip()
    if cur:
        rows.append(cur)
    return caption, rows


def _table_to_markdown(block: str) -> str:
    is_radical = "Anchor+|radical" in block
    m_open = re.match(r"\s*\{\|[^\n]*\n?", block)
    shell = block[m_open.end():] if m_open else block
    shell = re.sub(r"\|\}\s*$", "", shell)

    placeholders: list[str] = []
    shell = _convert_inner(shell, placeholders)
    caption_raw, rows = _parse_table_rows(shell)
    caption = _restore(_convert_templates(caption_raw), placeholders).strip()
    if not rows:
        return f"**{caption}**" if caption else ""
    ncols = max(len(r) for r in rows)

    is_grid = any("@@TBL" in c[1] for r in rows for c in r)
    if is_grid:
        out: list[str] = []
        if caption:
            out.append(f"##### {caption}")
            out.append("")
        for r in rows:
            for attrs, content, _ in r:
                md = _restore(_convert_templates(content), placeholders).strip()
                if md:
                    out.append(md)
                    out.append("")
        return "\n".join(out).strip()

    sections: list[tuple[str, list]] = []
    cur_title = ""
    cur_rows: list = []
    for row in rows:
        if len(row) == 1 and "colspan" in row[0][0].lower():
            if cur_rows:
                sections.append((cur_title, cur_rows))
                cur_rows = []
            cur_title = _restore(_convert_templates(row[0][1]), placeholders).strip(":. ")
            continue
        cur_rows.append(row)
    if cur_rows:
        sections.append((cur_title, cur_rows))

    out = []
    for title, srows in sections:
        first_converted = [_restore(_convert_templates(c[1]), placeholders) for c in srows[0]] if srows else []
        has_header = bool(srows) and len(srows[0]) == ncols and all(c[2] for c in srows[0])
        if has_header:
            header_cells = [_md_escape(first_converted[i]) for i in range(len(srows[0]))]
            body = srows[1:]
        elif is_radical and ncols == 6:
            header_cells = ["No.", "Radical", "Page", "Name", "Designation", "Meaning"]
            body = srows
        elif ncols == 2 and srows and _is_cjk(first_converted[0]):
            header_cells = ["字", "音"]
            body = srows
        else:
            header_cells = [""] * ncols
            body = srows
        if title:
            out.append("")
            out.append(f"#### {title}")
            out.append("")
        out.append("| " + " | ".join(header_cells) + " |")
        out.append("|" + "|".join([" --- "] * ncols) + "|")
        for r in body:
            cells = [_md_escape(_restore(_convert_templates(c[1]), placeholders)) for c in r]
            while len(cells) < ncols:
                cells.append("")
            out.append("| " + " | ".join(cells[:ncols]) + " |")
        out.append("")
    return "\n".join(out).strip()


def convert_page(raw: str) -> str:
    text = preprocess(raw)
    if not text.strip():
        return ""
    return _process(text)


def build_markdown(pages: dict[int, str], start: int, end: int) -> str:
    chunks: list[str] = []
    for pn in range(start, end + 1):
        raw = pages.get(pn, "")
        chunks.append(f"<!-- page:{pn} -->")
        if raw:
            body = convert_page(raw)
            if body:
                chunks.append("")
                chunks.append(body)
        chunks.append("")
    return "\n".join(chunks)


def validate_page_markers(text: str, start: int, end: int) -> None:
    marker_re = re.compile(r"<!-- page:(\d+) -->")
    markers: list[int] = []
    for line in text.splitlines():
        matches = marker_re.findall(line)
        if matches and marker_re.fullmatch(line.strip()) is None:
            raise ValueError(f"page marker must be on its own line: {line}")
        markers.extend(int(value) for value in matches)
    expected = list(range(start, end + 1))
    if markers != expected:
        raise ValueError(f"page markers must be exactly {start} through {end} in order")
