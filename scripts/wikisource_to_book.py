#!/usr/bin/env python3
"""Fetch a Wikisource Page-namespace book and convert to markdown.

Uses pywikibot for fetching and mwparserfromhell for wikitext conversion.
Currently specialised for the Fielde 1883 Swatow dictionary.

Usage:
    PYTHONPATH=. python3 scripts/wikisource_to_book.py \
        --title "Dictionary of the Swatow dialect.djvu" \
        --start 1 --end 648 \
        --output books/007_A_Pronouncing_and_Defining_Dictionary_of_the_Swatow_Dialect.md
"""

from __future__ import annotations

import argparse
import os
import re
import sys
import time
from pathlib import Path

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

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PAGE_PREFIX = "Page:"
BATCH_SIZE = 50
SLEEP_BETWEEN_BATCHES = 5.0
MAX_ATTEMPTS = 4

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

_HEADWORD_RE = re.compile(r"^\*?\s*\*\*(.+?)\*\*\s+(\S+)(?:\s+(\([^)]*\)))?\s*$")


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


def cleanup(text: str) -> str:
    text = text.replace("\xa0", " ")
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


def fix_orphaned_semicolons(text: str) -> str:
    lines = text.split("\n")
    out: list[str] = []
    i = 0
    n = len(lines)
    while i < n:
        s = lines[i].strip()
        if s.startswith(";") and not s.startswith("; ---"):
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
            j = i + 1
            merged = False
            while j < n:
                sj = lines[j].strip()
                if sj == "":
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
        examples: list[tuple[str, str]] = []
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
                        post_entry_markers.append(lines[kk])
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
                    if kk < n and lines[kk].strip():
                        nxt = lines[kk].strip()
                        if not nxt.startswith((";", ":", "*", "#", "-")):
                            gloss = nxt
                            kk += 1
                    k = kk
                examples.append((phrase, gloss))
            elif s2.startswith(":"):
                k += 1
            else:
                break
        out.extend(pre_head_markers)
        head = f"- **{hanzi}** {latn} {nums}"
        if defn:
            head += f" — {defn}"
        out.append(head)
        for ph, gl in examples:
            if gl:
                out.append(f"  - *{ph}* — {gl}")
            else:
                out.append(f"  - *{ph}*")
        out.extend(post_entry_markers)
        i = k
    return "\n".join(out)


def convert_page(raw: str) -> str:
    text = preprocess(raw)
    if not text.strip():
        return ""
    return _process(text)


def fetch_wikitext(site, title: str) -> dict[int, str]:
    from pywikibot.data import api

    results: dict[int, str] = {}
    req = api.Request(
        site=site,
        parameters={
            "action": "query",
            "prop": "revisions",
            "rvprop": "content",
            "rvslots": "main",
            "titles": "|".join(title),
            "maxage": 0,
        },
    )
    data = req.submit()
    pages = data.get("query", {}).get("pages", {})
    if isinstance(pages, list):
        pages = {p["pageid"]: p for p in pages}
    for pageinfo in pages.values():
        t = pageinfo.get("title", "")
        try:
            n = int(t.rsplit("/", 1)[-1])
        except ValueError:
            continue
        revs = pageinfo.get("revisions", [])
        if not revs:
            continue
        rev0 = revs[0]
        text = rev0.get("slots", {}).get("main", {}).get("*")
        if text is None:
            text = rev0.get("*")
        if text is not None:
            results[n] = text
    return results


def fetch_batch(site, numbers: list[int], page_prefix: str) -> dict[int, str]:
    titles = [f"{page_prefix}{n}" for n in numbers]
    return fetch_wikitext(site, titles)


def run_fetch(site, page_prefix: str, start: int, end: int, cache_dir: Path) -> dict[int, str]:
    cache_dir.mkdir(parents=True, exist_ok=True)
    all_pages: dict[int, str] = {}
    all_nums = list(range(start, end + 1))
    batches = [all_nums[i:i + BATCH_SIZE] for i in range(0, len(all_nums), BATCH_SIZE)]

    for bi, batch in enumerate(batches, 1):
        cached = {}
        to_fetch = []
        for n in batch:
            p = cache_dir / f"p{n:03d}.wikitext"
            if p.exists():
                cached[n] = p.read_text(encoding="utf-8")
            else:
                to_fetch.append(n)

        all_pages.update(cached)

        if to_fetch:
            attempt = 0
            result = None
            while attempt < MAX_ATTEMPTS:
                attempt += 1
                try:
                    result = fetch_batch(site, to_fetch, page_prefix)
                    break
                except Exception as exc:
                    print(f"  batch {bi} attempt {attempt} error: {exc}", file=sys.stderr)
                    if attempt >= MAX_ATTEMPTS:
                        break
                    time.sleep(2 ** attempt)

            if result:
                for n in to_fetch:
                    text = result.get(n)
                    if text is not None:
                        all_pages[n] = text
                        p = cache_dir / f"p{n:03d}.wikitext"
                        p.write_text(text, encoding="utf-8")

        ok = sum(1 for n in batch if n in all_pages)
        print(f"  batch {bi}/{len(batches)}: {ok}/{len(batch)} pages", file=sys.stderr)
        time.sleep(SLEEP_BETWEEN_BATCHES)

    return all_pages


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


def postprocess(text: str) -> str:
    out = reformat_entries(text)
    out = fix_orphaned_semicolons(out)
    out = convert_section_titles(out)
    out = cleanup(out)
    out = re.sub(r"\n{3,}", "\n\n", out)
    out = re.sub(r"(?:\n---\n){2,}", "\n---\n", out)
    out = re.sub(r"\n{3,}", "\n\n", out)
    return out.strip() + "\n"


def main():
    parser = argparse.ArgumentParser(description="Fetch Wikisource book to markdown")
    parser.add_argument("--title", required=True, help="Wikisource index title (without Page: prefix)")
    parser.add_argument("--start", type=int, required=True, help="First page number")
    parser.add_argument("--end", type=int, required=True, help="Last page number")
    parser.add_argument("--output", required=True, help="Output markdown file path")
    parser.add_argument("--cache-dir", default=None, help="Directory for cached wikitext pages")
    args = parser.parse_args()

    page_prefix = f"{PAGE_PREFIX}{args.title}/"
    output = Path(args.output)
    cache_dir = Path(args.cache_dir) if args.cache_dir else PROJECT_ROOT / "tmp" / args.title.replace(".djvu", "").replace(" ", "_")

    sys.argv = ["fetch", f"-dir:{PROJECT_ROOT / '.progress' / 'swatow-dict-fetch'}"]
    import pywikibot
    site = pywikibot.Site("en", "wikisource")

    print(f"Fetching pages {args.start}-{args.end}...", file=sys.stderr)
    pages = run_fetch(site, page_prefix, args.start, args.end, cache_dir)

    missing = [n for n in range(args.start, args.end + 1) if n not in pages]
    if missing:
        print(f"Warning: {len(missing)} missing pages", file=sys.stderr)

    print("Building markdown...", file=sys.stderr)
    content = build_markdown(pages, args.start, args.end)
    content = postprocess(content)

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(content, encoding="utf-8")
    print(f"Wrote {len(content):,} bytes, {content.count(chr(10)) + 1} lines to {output}", file=sys.stderr)


if __name__ == "__main__":
    main()
