#!/usr/bin/env python3
"""
Insert <!-- page:N --> markers into book markdown using Wikisource page data.

Supports two source strategies controlled by BOOKS config table:

  | source_type | Discovery               | Entry HTML tag | md_entry_re         |
  |-------------|--------------------------|----------------|---------------------|
  | subpages    | Wikisource subpages API  | <dt>+<dd>      | `- \*\*(.+?)\*\*`   |
  | index       | Index: page → Page: NS   | <b>            | `\*\*(.+?)\*\*,`    |

Wikisource entries are extracted with their Han, PUJ, and English components.
Matching against the markdown uses all three to disambiguate short Han words
(e.g. distinguishing 鑿子 from 索子, which both have Levenshtein distance 1).

The BOOKS table maps book filename prefixes to strategy parameters.
Auto-detected from --md filename (e.g. "002_xxx.md" → prefix "002").

Usage:
    python3 scripts/add_page_markers.py --md books/001_Handbook_of_the_Swatow_Vernacular.md
    python3 scripts/add_page_markers.py --md books/002_English-Chinese_Vocabulary.md
    python3 scripts/add_page_markers.py --md books/002_xxx.md --dry-run

Cache is auto-populated from Wikisource when missing.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from collections import defaultdict
from pathlib import Path

API_BASE = "https://en.wikisource.org/w/api.php"
CORRECTION_RE = re.compile(r"~~([^~]+)~~\(([^)]+)\)")
IDEOGRAPHIC_SPACE = "\u3000"

BOOKS: dict[str, dict] = {
    "001": {
        "wikisource": "Handbook of the Swatow Vernacular",
        "source_type": "subpages",
        "entry_tag": "dt",
        "md_entry_re": r"- \*\*(.+?)\*\*",
        "first_entry_page": 17,
    },
    "002": {
        "wikisource": "Index:English-Chinese_Vocabulary_of_the_Vernacular_Or_Spoken_Language_of_Swatow.djvu",
        "source_type": "index",
        "entry_tag": "b",
        "md_entry_re": r"\*\*(.+?)\*\*,",
        "first_entry_page": 14,
        "last_entry_page": 315,
    },
}


def detect_config(md_path: Path) -> tuple[str, dict]:
    stem = md_path.stem
    for prefix, config in BOOKS.items():
        if stem.startswith(prefix + "_"):
            return prefix, config
    available = ", ".join(BOOKS.keys())
    raise ValueError(f"No BOOKS config for '{md_path.name}'. Available prefixes: {available}")


def api_get(params: dict, max_retries: int = 5) -> dict:
    url = f"{API_BASE}?{urllib.parse.urlencode(params)}"
    for attempt in range(max_retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "HokkienWritingDataset/1.0"})
            with urllib.request.urlopen(req, timeout=120) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < max_retries - 1:
                wait = 10 * (attempt + 1)
                print(f"    429, retrying in {wait}s...")
                time.sleep(wait)
            else:
                raise


def fetch_page_html(title: str) -> str:
    params = {
        "action": "parse",
        "page": title,
        "prop": "text",
        "format": "json",
        "formatversion": 2,
    }
    data = api_get(params)
    return data["parse"]["text"]


def discover_subpages(parent_title: str) -> list[str]:
    titles = [parent_title]
    prefix = parent_title + "/"
    params = {
        "action": "query",
        "list": "allpages",
        "apprefix": prefix,
        "aplimit": "max",
        "apnamespace": 0,
        "format": "json",
        "formatversion": 2,
    }
    while True:
        data = api_get(params)
        for entry in data.get("query", {}).get("allpages", []):
            titles.append(entry["title"])
        apcontinue = data.get("continue", {}).get("apcontinue")
        if not apcontinue:
            break
        params["apcontinue"] = apcontinue
        time.sleep(1)
    return sorted(titles)


def discover_index_pages(index_title: str) -> list[str]:
    html = fetch_page_html(index_title)
    djvu_name = index_title[len("Index:"):]
    page_re = r"(Page:" + re.escape(djvu_name) + r"/\d+)"
    titles = sorted(set(re.findall(page_re, html)), key=lambda t: int(t.rsplit("/", 1)[1]))
    return titles


def fetch_and_cache(cache_path: Path, config: dict) -> dict[str, str]:
    cache: dict[str, str] = {}
    if cache_path.exists():
        cache = json.loads(cache_path.read_text(encoding="utf-8"))

    source_type = config["source_type"]
    wikisource = config["wikisource"]

    if source_type == "subpages":
        pages = discover_subpages(wikisource)
    elif source_type == "index":
        pages = discover_index_pages(wikisource)
    else:
        raise ValueError(f"Unknown source_type: {source_type}")

    missing = [t for t in pages if t not in cache]
    print(f"Discovered {len(pages)} pages ({source_type}), {len(missing)} missing")

    for title in missing:
        short = title.split("/")[-1]
        print(f"  Fetching: {short}")
        try:
            html = fetch_page_html(title)
            cache[title] = html
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            cache_path.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
        except Exception as e:
            print(f"  ERROR: {e}", file=sys.stderr)
            sys.exit(1)
        time.sleep(3)

    print(f"Cache: {len(cache)} pages saved to {cache_path}")
    return cache


def all_page_numbers(cache: dict[str, str], config: dict) -> set[int]:
    pages: set[int] = set()
    source_type = config["source_type"]

    if source_type == "subpages":
        for html in cache.values():
            for m in re.finditer(r'data-page-index="(\d+)"', html):
                pages.add(int(m.group(1)))
    elif source_type == "index":
        for title in cache:
            m = re.search(r"/(\d+)$", title)
            if m:
                pages.add(int(m.group(1)))

    return pages


def _subpage_page_owners(cache: dict[str, str]) -> dict[int, str]:
    """For each page index, find the subpage that "owns" it.

    When a page appears in multiple subpages, the OWNER is the one where the
    page has the HIGHEST position within that subpage's range — i.e., the
    subpage that ENDS at or near this page. This avoids double-counting: the
    subpage that STARTS at this page is a new chapter, but the entries from
    the previous chapter's last page are what the markdown typically has
    immediately before the new chapter heading.
    """
    subpage_ranges: list[tuple[str, int, int]] = []
    for title, html in cache.items():
        pgs = sorted(set(int(m.group(1)) for m in re.finditer(r'data-page-index="(\d+)"', html)))
        if pgs:
            subpage_ranges.append((title, pgs[0], pgs[-1]))

    owners: dict[int, str] = {}
    best_pos: dict[int, float] = {}
    for title, first_pg, last_pg in subpage_ranges:
        for pg in range(first_pg, last_pg + 1):
            pos = (pg - first_pg) / max(1, last_pg - first_pg + 1)
            if pg not in owners or pos > best_pos[pg]:
                owners[pg] = title
                best_pos[pg] = pos
    return owners


def _html_to_title(cache: dict[str, str]) -> dict[int, str]:
    """Map each HTML object's id() to its title."""
    return {id(h): t for t, h in cache.items()}


def _extract_dt_entries(html: str) -> list[tuple[str, str, str]]:
    """Extract (han, puj, en) from each <dt>...</dt> in subpages HTML.

    Structure: <dt>HAN</dt><dd>PUJ<dl><dd>EN</dd></dl></dd>
    """
    entries: list[tuple[str, str, str]] = []
    dt_re = re.compile(r"<dt[^>]*>(.*?)</dt>", re.DOTALL)
    for m in dt_re.finditer(html):
        han = re.sub(r"<[^>]+>", "", m.group(1)).strip()
        han = han.replace(IDEOGRAPHIC_SPACE, " ").strip()
        if not han or han.startswith((".", "{", "/*")):
            continue
        rest = html[m.end():m.end() + 2000]
        dd_re = re.compile(r"<dd[^>]*>(.*?)(?=<dd[^>]*>|</dd>|<dt|$)", re.DOTALL)
        dds = []
        for dm in dd_re.finditer(rest):
            dds.append(re.sub(r"<[^>]+>", "", dm.group(1)).strip())
        puj = dds[0] if dds else ""
        en = dds[1] if len(dds) > 1 else ""
        puj = puj.replace(IDEOGRAPHIC_SPACE, " ").strip()
        en = en.replace(IDEOGRAPHIC_SPACE, " ").strip()
        entries.append((han, puj, en))
    return entries


def _extract_b_entries(html: str) -> list[tuple[str, str, str]]:
    """For index source: each <b> contains an English word (no separate Han/PUJ)."""
    entries: list[tuple[str, str, str]] = []
    b_re = re.compile(r"<b[^>]*>(.*?)</b>", re.DOTALL)
    for m in b_re.finditer(html):
        clean = re.sub(r"<[^>]+>", "", m.group(1)).strip()
        if clean and not clean.startswith((".", "{", "/*")):
            clean = clean.replace(IDEOGRAPHIC_SPACE, " ").strip()
            entries.append((clean, "", ""))
    return entries


def extract_page_entries(
    cache: dict[str, str], config: dict
) -> dict[int, list[tuple[str, str, str]]]:
    """For each page, return list of (han, puj, en) entries from its owner subpage."""
    source_type = config["source_type"]
    lo = config.get("first_entry_page", 1)
    hi = config.get("last_entry_page", 99999)

    page_entries: dict[int, list[tuple[str, str, str]]] = defaultdict(list)

    if source_type == "subpages":
        owners = _subpage_page_owners(cache)
        html_title = _html_to_title(cache)
        for html in cache.values():
            this_title = html_title.get(id(html), "")
            page_markers = list(re.finditer(r'data-page-index="(\d+)"', html))
            chunks = []
            for i, m in enumerate(page_markers):
                pg = int(m.group(1))
                if pg < lo or pg > hi:
                    continue
                if owners.get(pg) != this_title:
                    continue
                start = m.end()
                end = page_markers[i + 1].start() if i + 1 < len(page_markers) else len(html)
                chunks.append((pg, html[start:end]))
            for pg, chunk in chunks:
                page_entries[pg].extend(_extract_dt_entries(chunk))
    elif source_type == "index":
        for title, html in cache.items():
            m = re.search(r"/(\d+)$", title)
            if not m:
                continue
            pg = int(m.group(1))
            if pg < lo or pg > hi:
                continue
            page_entries[pg].extend(_extract_b_entries(html))

    return dict(page_entries)


def parse_md_entry(line: str, source_type: str) -> tuple[str, str, str, str] | None:
    """Parse a markdown entry line into (han_orig, han_corr, puj, en).

    For subpages (book 001): `- **HAN** PUJ ... ... ... ENGLISH.`
        HAN may contain corrections like `不~~是~~(毋)`:
        - han_orig = `不是` (original as printed in Wikisource)
        - han_corr = `不毋` (modern/corrected form)
    For index (book 002):    `**WORD**, ...`
        The bold word is the English headword; no separate Han/PUJ/EN.
    """
    if source_type == "subpages":
        m = re.match(r"-\s+\*\*(.+?)\*\*\s+(.+?)\s*$", line.strip())
        if not m:
            return None
        han_raw = m.group(1)
        rest = m.group(2)
        parts = re.split(r"\s*\.{3}\s*\.{2,}\s*", rest, maxsplit=1)
        if len(parts) == 2:
            puj = parts[0].strip()
            en = parts[1].strip()
        else:
            puj = rest.strip()
            en = ""
    elif source_type == "index":
        m = re.match(r"\*\*(.+?)\*\*,", line.strip())
        if not m:
            return None
        word = m.group(1)
        han_raw = word
        puj = ""
        en = word
    else:
        return None

    puj = puj.replace(IDEOGRAPHIC_SPACE, " ").strip()
    en = en.replace(IDEOGRAPHIC_SPACE, " ").strip()

    if CORRECTION_RE.search(han_raw):
        han_orig = CORRECTION_RE.sub(lambda mo: mo.group(1), han_raw)
        han_corr = CORRECTION_RE.sub(lambda mo: mo.group(2), han_raw)
    else:
        han_orig = han_raw
        han_corr = han_raw
    return (han_orig, han_corr, puj, en)


def find_md_entries(
    lines: list[str], md_entry_re: str, source_type: str
) -> list[tuple[int, str, str, str, str]]:
    """Return [(line_idx, han_orig, han_corr, puj, en), ...] for each entry."""
    compiled = re.compile(md_entry_re)
    out = []
    for i, line in enumerate(lines):
        if not compiled.match(line.strip()):
            continue
        parsed = parse_md_entry(line, source_type)
        if parsed:
            han_orig, han_corr, puj, en = parsed
            out.append((i, han_orig, han_corr, puj, en))
    return out


def find_entry_lines(lines: list[str], md_entry_re: str) -> list[int]:
    compiled = re.compile(md_entry_re)
    return [i for i, line in enumerate(lines) if compiled.match(line.strip())]


def build_markers(page_counts: dict[int, int], total_entries: int) -> list[tuple[int, int]]:
    cumul = 0
    markers = []
    for pg in sorted(page_counts):
        count = page_counts[pg]
        if count == 0:
            continue
        if cumul >= total_entries:
            break
        markers.append((cumul, pg))
        cumul += count
    return markers


def extract_page_first_entries(cache: dict[str, str], config: dict) -> dict[int, str]:
    page_first: dict[int, str] = {}
    source_type = config["source_type"]
    entry_tag = config["entry_tag"]
    tag_re = re.compile(rf"<{entry_tag}[^>]*>(.*?)</{entry_tag}>", re.DOTALL)
    lo = config.get("first_entry_page", 1)
    hi = config.get("last_entry_page", 99999)

    if source_type == "subpages":
        owners = _subpage_page_owners(cache)
        html_title = _html_to_title(cache)
        for html in cache.values():
            this_title = html_title.get(id(html), "")
            page_markers = list(re.finditer(r'data-page-index="(\d+)"', html))
            for i, m in enumerate(page_markers):
                pg = int(m.group(1))
                if pg < lo or pg > hi:
                    continue
                if owners.get(pg) != this_title:
                    continue
                chunk_start = m.end()
                chunk_end = page_markers[i + 1].start() if i + 1 < len(page_markers) else len(html)
                for em in tag_re.finditer(html[chunk_start:chunk_end]):
                    clean = re.sub(r"<[^>]+>", "", em.group(1)).strip()
                    if clean and not clean.startswith((".", "{", "/*")):
                        page_first[pg] = clean.replace(IDEOGRAPHIC_SPACE, " ").strip()
                        break
    elif source_type == "index":
        for title, html in cache.items():
            m = re.search(r"/(\d+)$", title)
            if not m:
                continue
            pg = int(m.group(1))
            if pg < lo or pg > hi:
                continue
            for em in tag_re.finditer(html):
                clean = re.sub(r"<[^>]+>", "", em.group(1)).strip()
                if clean and not clean.startswith((".", "{", "/*")):
                    page_first[pg] = clean.replace(IDEOGRAPHIC_SPACE, " ").strip()
                    break

    return page_first


def levenshtein(s1: str, s2: str) -> int:
    if abs(len(s1) - len(s2)) > max(len(s1), len(s2)) // 2 + 3:
        return max(len(s1), len(s2))
    n, m = len(s1), len(s2)
    if n == 0:
        return m
    if m == 0:
        return n
    prev = list(range(m + 1))
    for i in range(1, n + 1):
        curr = [i] + [0] * m
        for j in range(1, m + 1):
            cost = 0 if s1[i - 1] == s2[j - 1] else 1
            curr[j] = min(curr[j - 1] + 1, prev[j] + 1, prev[j - 1] + cost)
        prev = curr
    return prev[m]


def entry_score(ws: tuple[str, str, str], md: tuple[str, str, str, str]) -> tuple[int, int, int]:
    """Score a (ws, md) match. Lower is better.

    Considers Han (orig and corrected), PUJ, and English.
    """
    ws_han, ws_puj, ws_en = ws
    md_han_orig, md_han_corr, md_puj, md_en = md

    def han_score(a: str, b: str) -> int:
        a_low = a.lower()
        b_low = b.lower()
        if a_low == b_low:
            return 0
        if b_low.startswith(a_low) or a_low.startswith(b_low):
            return 1
        if len(a_low) <= 3:
            threshold = 1
        else:
            threshold = max(1, len(a_low) // 3)
        if levenshtein(a_low, b_low) <= threshold:
            return 2
        return 99

    s_han_orig = han_score(ws_han, md_han_orig)
    s_han_corr = han_score(ws_han, md_han_corr) if md_han_corr != md_han_orig else s_han_orig
    s_han = min(s_han_orig, s_han_corr)

    s_puj = 99
    if ws_puj and md_puj:
        if ws_puj.lower() == md_puj.lower():
            s_puj = 0
        else:
            d = levenshtein(ws_puj.lower(), md_puj.lower())
            if d <= 1:
                s_puj = 1

    s_en = 99
    if ws_en and md_en:
        ws_en_words = [w.lower() for w in re.findall(r"[A-Za-z]+", ws_en) if len(w) > 2]
        md_en_words = [w.lower() for w in re.findall(r"[A-Za-z]+", md_en) if len(w) > 2]
        if ws_en_words and md_en_words:
            if any(w in md_en.lower() for w in ws_en_words) or any(w in ws_en.lower() for w in md_en_words):
                s_en = 0
        else:
            d = levenshtein(ws_en.lower(), md_en.lower())
            if d <= 2:
                s_en = 1

    return (s_han, s_puj, s_en)


def build_markers_with_components(
    page_entries: dict[int, list[tuple[str, str, str]]],
    md_entries: list[tuple[int, str, str, str, str]],
) -> list[tuple[int, int]]:
    """Match Wikisource pages to markdown entries using Han + PUJ + English."""
    markers: list[tuple[int, int]] = []
    cumul = 0

    for pg in sorted(page_entries):
        entries = page_entries[pg]
        if not entries:
            continue

        ws_first = entries[0]
        count = len(entries)

        window_lo = max(0, cumul - 30)
        window_hi = min(len(md_entries), cumul + max(count, 1) + 80)

        best_idx = None
        best_score: tuple[int, int, int] = (99, 99, 99)
        for md_i in range(window_lo, window_hi):
            md = md_entries[md_i]
            md_tuple = (md[1], md[2], md[3], md[4])
            score = entry_score(ws_first, md_tuple)
            if score < best_score:
                best_score = score
                best_idx = md_i

        if best_idx is not None and best_score[0] < 99:
            markers.append((md_entries[best_idx][0], pg))
            cumul = best_idx + count
        else:
            if cumul < len(md_entries):
                markers.append((md_entries[cumul][0], pg))
            cumul += count

    return markers


def insert_markers(lines: list[str], markers: list[tuple[int, int]]) -> list[str]:
    for line_idx, pg in sorted(markers, key=lambda x: (-x[0], -x[1])):
        lines.insert(line_idx, f"<!-- page:{pg} -->")
    return lines


def main() -> None:
    parser = argparse.ArgumentParser(description="Insert page markers into markdown from Wikisource")
    parser.add_argument("--md", required=True, type=Path, help="Markdown file (modified in-place)")
    parser.add_argument("--cache", type=Path, help="Cache path (default: tmp/wikisource_{PREFIX}.json)")
    parser.add_argument("--dry-run", action="store_true", help="Print stats without writing")
    args = parser.parse_args()

    prefix, config = detect_config(args.md)
    print(f"Book: {prefix} | source_type: {config['source_type']} | entry_tag: <{config['entry_tag']}>")
    print(f"  Entry pages: {config.get('first_entry_page', 1)}–{config.get('last_entry_page', 'end')}")

    cache_path = args.cache or Path(f"tmp/wikisource_{prefix}.json")
    cache = fetch_and_cache(cache_path, config)

    page_entries = extract_page_entries(cache, config)
    total_entries = sum(len(v) for v in page_entries.values())
    pages_with_entries = sum(1 for v in page_entries.values() if v)

    md_text = args.md.read_text(encoding="utf-8")
    cleaned = re.sub(r"<!-- page:\d+ -->\n?", "", md_text)
    lines = cleaned.split("\n")
    while lines and lines[-1].strip() == "":
        lines.pop()

    md_entries = find_md_entries(lines, config["md_entry_re"], config["source_type"])
    print(f"Wikisource: {total_entries} entries across {pages_with_entries} pages")
    print(f"Markdown:   {len(md_entries)} entry lines")

    if len(md_entries) != total_entries:
        print(f"WARNING: entry count mismatch ({len(md_entries)} vs {total_entries})", file=sys.stderr)

    markers = build_markers_with_components(page_entries, md_entries)
    print(f"Entry markers (anchored): {len(markers)} pages")

    lo = config.get("first_entry_page", 1)
    hi = config.get("last_entry_page")
    all_pages = all_page_numbers(cache, config)
    front_pages = {pg for pg in all_pages if pg < lo}
    back_pages = set()
    if hi:
        back_pages = {pg for pg in all_pages if pg > hi}

    matter_markers = [(0, pg) for pg in sorted(front_pages)]
    if back_pages:
        matter_markers += [(len(lines), pg) for pg in sorted(back_pages)]
    if matter_markers:
        print(f"Front/back matter: {len(front_pages)}+{len(back_pages)} pages")
    markers = sorted(markers + matter_markers, key=lambda x: (x[0], x[1]))

    print(f"Total markers: {len(markers)} pages")
    for _, pg in markers[:5]:
        print(f"  page {pg}")
    if len(markers) > 10:
        print("  ...")
    for _, pg in markers[-3:]:
        print(f"  page {pg}")

    if args.dry_run:
        print("\n(dry run, not writing)")
        return

    lines = insert_markers(lines, markers)
    args.md.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nWrote {len(lines)} lines to {args.md.name}")


if __name__ == "__main__":
    main()
