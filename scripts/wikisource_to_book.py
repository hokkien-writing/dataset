#!/usr/bin/env python3
"""Download a book from Wikisource Page namespace and convert to markdown.

Usage:
    PYTHONPATH=. python3 scripts/wikisource_to_book.py \
        "First Lessons in the Tie-chiw Dialect.pdf" 10 61 \
        books/003_First_Lessons_in_the_Tie-chiw_Dialect.md

This script:
1. Downloads pages from Wikisource Page namespace via API (batch + HTML fallback)
2. Converts wikitext/HTML to clean markdown with <!-- page:N --> markers
3. Formats definition lists and tables as markdown pipe tables
4. Expands ditto marks (丨) using previous-line context
"""

from __future__ import annotations

import argparse
import html as html_mod
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
BASE_URL = "https://en.wikisource.org/w/api.php"
UA = "Mozilla/5.0 (X11; Linux x86_64; rv:127.0) Gecko/20100101 Firefox/127.0"
BATCH_SIZE = 5
BATCH_DELAY = 3
RETRY_DELAY = 30


def fetch_batch(pdf_title: str, page_nums: list[int]) -> dict[int, str]:
    titles = "|".join(f"Page:{pdf_title}/{n}" for n in page_nums)
    params = urllib.parse.urlencode({
        "action": "query",
        "titles": titles,
        "prop": "revisions",
        "rvprop": "content",
        "format": "json",
    })
    req = urllib.request.Request(f"{BASE_URL}?{params}", headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read())
    result: dict[int, str] = {}
    for page_data in data["query"]["pages"].values():
        m = re.search(r"/(\d+)$", page_data["title"])
        if m and "revisions" in page_data:
            result[int(m.group(1))] = page_data["revisions"][0]["*"]
    return result


def fetch_page_html(pdf_title: str, page_num: int) -> str:
    encoded = urllib.parse.quote(f"Page:{pdf_title}/{page_num}", safe=":/")
    url = f"https://en.wikisource.org/wiki/{encoded}"
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8", errors="replace")


def download_pages(pdf_title: str, start: int, end: int) -> dict[int, str]:
    all_pages: dict[int, str] = {}
    all_nums = list(range(start, end + 1))
    failed: list[int] = []

    for i in range(0, len(all_nums), BATCH_SIZE):
        batch = all_nums[i:i + BATCH_SIZE]
        try:
            data = fetch_batch(pdf_title, batch)
            all_pages.update(data)
            print(f"  API batch {batch}: OK ({len(data)} pages)", file=sys.stderr)
        except Exception as e:
            print(f"  API batch {batch}: FAILED - {e}", file=sys.stderr)
            failed.extend(batch)
        time.sleep(BATCH_DELAY)

    if failed:
        print(f"Retrying {len(failed)} pages via HTML...", file=sys.stderr)
        time.sleep(RETRY_DELAY)
        for pn in failed:
            try:
                html = fetch_page_html(pdf_title, pn)
                all_pages[pn] = html
                print(f"  HTML page {pn}: OK ({len(html)} bytes)", file=sys.stderr)
            except Exception as e:
                print(f"  HTML page {pn}: FAILED - {e}", file=sys.stderr)
            time.sleep(BATCH_DELAY)

    return all_pages


def strip_noinclude(text: str) -> str:
    return re.sub(r"<noinclude>.*?</noinclude>", "", text, flags=re.DOTALL)


def clean_wikitext(text: str) -> str:
    text = strip_noinclude(text)
    templates = [
        (r"\{\{c\|(.*?)\}\}", r"\1"),
        (r"\{\{xxx-larger\|(.*?)\}\}", r"\1"),
        (r"\{\{xx-larger\|(.*?)\}\}", r"\1"),
        (r"\{\{x-larger\|(.*?)\}\}", r"\1"),
        (r"\{\{larger\|(.*?)\}\}", r"\1"),
        (r"\{\{smaller\|(.*?)\}\}", r"\1"),
        (r"\{\{small\|(.*?)\}\}", r"\1"),
        (r"\{\{sc\|(.*?)\}\}", r"\1"),
        (r"\{\{blackletter\|(.*?)\}\}", r"\1"),
        (r"\{\{lsp\|[^|]*?\|(.*?)\}\}", r"\1"),
        (r"\{\{right\|(.*?)\}\}", r"\1"),
        (r"\{\{right\|(.*?)\|[^}]*\}\}", r"\1"),
    ]
    for pattern, repl in templates:
        text = re.sub(pattern, repl, text, flags=re.DOTALL)

    text = re.sub(r"\{\{dhr\|[^}]*\}\}", "", text)
    text = re.sub(r"\{\{dhr\}\}", "", text)
    text = re.sub(r"\{\{rule\|[^}]*\}\}", "\n------\n", text)
    text = re.sub(r"\{\{rule\}\}", "\n------\n", text)
    text = re.sub(r"\{\{sfrac nobar\|([^|]*)\|([^}]*)\}\}", r"\1/\2", text)
    text = re.sub(r"\{\{rh\|[^}]*\}\}", "", text)
    text = re.sub(r"\{\{pagequality[^}]*\}\}", "", text)

    text = re.sub(
        r"<h([23])[^>]*>(.*?)</h\1>",
        lambda m: "#" * int(m.group(1)) + " " + m.group(2).strip(),
        text, flags=re.DOTALL,
    )
    text = re.sub(r"<i>(.*?)</i>", r"*\1*", text, flags=re.DOTALL)
    text = re.sub(r"<b>(.*?)</b>", r"**\1**", text, flags=re.DOTALL)
    text = re.sub(r"<br\s*/?>", "\n", text)
    text = re.sub(r"<ref[^>]*>.*?</ref>", "", text, flags=re.DOTALL)
    text = re.sub(r"\[\[([^|\]]+)\|([^\]]+)\]\]", r"\2", text)
    text = re.sub(r"\[\[([^|\]]+)\]\]", r"\1", text)
    text = re.sub(r"\{\{.*?\}\}", "", text, flags=re.DOTALL)
    text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)
    return text.strip()


def convert_dl_to_pipe(text: str) -> str:
    lines = text.split("\n")
    result: list[str] = []
    eng = ""
    han = ""
    roman = ""

    def flush():
        nonlocal eng, han, roman
        if eng and (han or roman):
            parts = [eng]
            if han:
                parts.append(han)
            if roman and roman != han:
                parts.append(roman)
            result.append(" | ".join(parts))
        eng = han = roman = ""

    for line in lines:
        s = line.strip()
        if not s:
            flush()
            continue
        semi = re.match(r"^;\s*(.*)", s)
        colon = re.match(r"^::?\s*(.*)", s)
        if semi:
            flush()
            eng = semi.group(1).strip()
        elif colon:
            val = colon.group(1).strip()
            if not han:
                han = val
            else:
                roman = val
    flush()
    return "\n".join(result)


def process_wikitext_page(page_num: int, wikitext: str) -> str:
    text = clean_wikitext(wikitext)
    text = re.sub(r'<section end="[^"]*"\s*/?>', '', text)
    if re.search(r"^;", text, re.MULTILINE):
        text = convert_dl_to_pipe(text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def _html_clean(s: str) -> str:
    s = re.sub(r"<[^>]+>", "", s)
    return s.strip()


def process_html_page(html: str) -> str:
    html = html_mod.unescape(html)
    html = re.sub(r"<style[^>]*>.*?</style>", "", html, flags=re.DOTALL)

    m = re.search(r'<div class="pagetext">(.*?)</div>\s*</div>\s*</div>', html, re.DOTALL)
    content = m.group(1) if m else html

    text_parts: list[str] = []
    for h in re.finditer(r"<h[23][^>]*>(.*?)</h[23]>", content):
        level = 2 if "h2" in h.group(0)[:10] else 3
        text_parts.append(f"\n{'#' * level} {_html_clean(h.group(1))}")

    entries: list[str] = []
    nested = re.findall(
        r"<dl>\s*<dt>(.*?)</dt>\s*<dd>(.*?)<dl>\s*<dd>(.*?)</dd>\s*</dl>\s*</dd>\s*</dl>",
        content, re.DOTALL,
    )
    for dt, dd1, dd2 in nested:
        dt_c = _html_clean(dt)
        dd1_c = _html_clean(dd1)
        dd2_c = _html_clean(dd2)
        if dt_c:
            parts = [dt_c]
            if dd1_c:
                parts.append(dd1_c)
            if dd2_c and dd2_c != dd1_c:
                parts.append(dd2_c)
            entries.append(" | ".join(parts))

    if not nested:
        for tr in re.finditer(r"<tr[^>]*>(.*?)</tr>", content, re.DOTALL):
            cells = [_html_clean(td.group(1)) for td in re.finditer(r"<t[hd][^>]*>(.*?)</t[hd]>", tr.group(1), re.DOTALL)]
            if cells:
                entries.append(" | ".join(cells))

    result = "\n".join(text_parts)
    if entries:
        result += "\n\n" + "\n".join(entries)
    return re.sub(r"\n{3,}", "\n\n", result).strip()


def format_tables(content: str) -> str:
    lines = content.split("\n")
    result: list[str] = []
    in_table = False

    for line in lines:
        s = line.strip()
        is_entry = bool(re.match(r"^[^|#<\n].*\|.*\|", s)) and not s.startswith("|")
        if is_entry:
            cols = s.count("|") - 1
            if not in_table:
                header = "| " + " | ".join([""] * cols) + " |"
                sep = "|" + "|".join(["---"] * cols) + "|"
                result.append(header)
                result.append(sep)
                in_table = True
            result.append("| " + s + " |")
        else:
            in_table = False
            result.append(line)

    return "\n".join(result)


def expand_ditto(content: str) -> str:
    lines = content.split("\n")
    result: list[str] = []
    prev_hanzi = None

    for line in lines:
        m = re.match(r"^\|[^|]*\|([^|]*)\|[^|]*\|$", line)
        if m:
            hanzi = m.group(1).strip()
            if "丨" in hanzi and prev_hanzi:
                expanded = hanzi
                offset = 0
                for i, ch in enumerate(hanzi):
                    if ch == "丨" and i < len(prev_hanzi):
                        ditto_val = prev_hanzi[i]
                        ins = f"~~丨~~({ditto_val})"
                        expanded = expanded[:i + offset] + ins + expanded[i + offset + 1:]
                        offset += len(ins) - 1
                line = line.replace(hanzi, expanded, 1)
                prev_hanzi = expanded.replace("~~丨~~(", "").replace(")", "")
            else:
                prev_hanzi = hanzi
        else:
            prev_hanzi = None
        result.append(line)

    return "\n".join(result)


def build_markdown(pages: dict[int, str], start: int, end: int) -> str:
    sections: list[str] = []
    for pn in range(start, end + 1):
        raw = pages.get(pn, "")
        if not raw:
            continue
        if raw.lstrip().startswith("<"):
            body = process_html_page(raw)
        else:
            body = process_wikitext_page(pn, raw)
        if body:
            sections.append(f"<!-- page:{pn} -->\n\n{body}")
    return "\n\n".join(sections) + "\n"


def main():
    parser = argparse.ArgumentParser(description="Download Wikisource book to markdown")
    parser.add_argument("pdf_title", help="Wikisource PDF index title")
    parser.add_argument("start", type=int, help="First page number")
    parser.add_argument("end", type=int, help="Last page number")
    parser.add_argument("output", help="Output markdown file path")
    args = parser.parse_args()

    print(f"Downloading {args.pdf_title} pages {args.start}-{args.end}...", file=sys.stderr)
    pages = download_pages(args.pdf_title, args.start, args.end)

    missing = [n for n in range(args.start, args.end + 1) if n not in pages]
    if missing:
        print(f"Warning: missing pages: {missing}", file=sys.stderr)

    print("Building markdown...", file=sys.stderr)
    content = build_markdown(pages, args.start, args.end)
    content = format_tables(content)
    content = expand_ditto(content)

    output = Path(args.output)
    output.write_text(content, encoding="utf-8")
    print(f"Written {len(content)} chars to {output}", file=sys.stderr)


if __name__ == "__main__":
    main()
