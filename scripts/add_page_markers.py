#!/usr/bin/env python3
"""
Insert <!-- page:N --> markers into book markdown using Wikisource page data.

Algorithm:
  1. Aggregate <dt> counts and first-<dt> text per page_index across all Wikisource subpages
  2. Count entry lines (- **...) in cleaned markdown, extract original word (stripping corrections)
  3. Walk pages in order: for each page boundary, use edit-distance anchor matching
     to find the actual MD entry position near the expected cumul offset
  4. Insert markers at verified positions (bottom-up to preserve indices)

This avoids drift caused by 1:1 entry mismatches between WS <dt> and MD - ** lines
(e.g. duplicate entries, variant characters, ~~correction~~ patterns).

Cache is auto-populated from Wikisource when missing or stale.

Usage:
    python3 scripts/add_page_markers.py \\
        --md books/001_Handbook_of_the_Swatow_Vernacular.md \\
        --wikisource "Handbook of the Swatow Vernacular" \\
        --cache tmp/wikisource_001.json

    # Reuse existing cache (skip fetch)
    python3 scripts/add_page_markers.py --cache tmp/wikisource_001.json --md books/001_XXX.md

    # Dry run
    python3 scripts/add_page_markers.py --cache tmp/xxx.json --md books/xxx.md --dry-run
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

CORRECTION_RE = re.compile(r"~~([^~]+)~~\([^)]+\)")
IDEOGRAPHIC_SPACE = "\u3000"


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


def discover_subpages(parent_title: str) -> list[str]:
    titles = [parent_title]
    params = {
        "action": "query",
        "list": "subpages",
        "sptitle": parent_title,
        "splimit": "max",
        "format": "json",
        "formatversion": 2,
    }
    while True:
        data = api_get(params)
        sp = data.get("query", {}).get("subpages", [])
        for entry in sp:
            titles.append(entry["title"])
        batchcomplete = data.get("batchcomplete")
        spcontinue = data.get("continue", {}).get("spcontinue")
        if batchcomplete or not spcontinue:
            break
        params["spcontinue"] = spcontinue
        time.sleep(1)
    return sorted(titles)


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


def fetch_and_cache(cache_path: Path, parent_title: str) -> dict[str, str]:
    cache: dict[str, str] = {}
    if cache_path.exists():
        cache = json.loads(cache_path.read_text(encoding="utf-8"))

    subpages = discover_subpages(parent_title)
    print(f"Discovered {len(subpages)} pages for '{parent_title}'")

    for title in subpages:
        if title in cache:
            print(f"  (cached) {title}")
            continue
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


def extract_page_data(cache: dict[str, str]) -> dict[int, tuple[int, str]]:
    page_counts: dict[int, int] = defaultdict(int)
    page_first_dt: dict[int, str] = {}

    for html in cache.values():
        markers = list(re.finditer(r'data-page-index="(\d+)"', html))
        for i, m in enumerate(markers):
            pg = int(m.group(1))
            chunk_start = m.end()
            chunk_end = markers[i + 1].start() if i + 1 < len(markers) else len(html)
            chunk = html[chunk_start:chunk_end]
            dts = re.findall(r'<dt[^>]*>(.*?)</dt>', chunk, re.DOTALL)
            for dt in dts:
                clean = re.sub(r"<[^>]+>", "", dt).strip()
                page_counts[pg] += 1
                if pg not in page_first_dt:
                    page_first_dt[pg] = clean.replace(IDEOGRAPHIC_SPACE, " ").strip()

    return {pg: (page_counts[pg], page_first_dt.get(pg, "")) for pg in page_counts}


def strip_corrections(text: str) -> str:
    return CORRECTION_RE.sub(r"\1", text)


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


def find_entry_lines(lines: list[str], prefix: str) -> list[tuple[int, str]]:
    entries = []
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith(prefix):
            m = re.match(r"- \*\*(.+?)\*\*", stripped)
            if m:
                orig = strip_corrections(m.group(1)).replace(IDEOGRAPHIC_SPACE, " ").strip()
                entries.append((i, orig))
    return entries


def build_markers_anchored(
    page_data: dict[int, tuple[int, str]],
    md_entries: list[tuple[int, str]],
) -> list[tuple[int, int]]:
    cumul = 0
    markers = []

    for pg in sorted(page_data):
        count, ws_first_dt = page_data[pg]
        if count == 0:
            continue

        best_md_idx = None
        best_dist = float("inf")

        search_lo = max(0, cumul - 5)
        search_hi = min(len(md_entries), cumul + count + 15)

        for md_i in range(search_lo, search_hi):
            _, md_word = md_entries[md_i]
            d = levenshtein(ws_first_dt, md_word)
            threshold = max(2, len(ws_first_dt) // 2)
            if d <= threshold and d < best_dist:
                best_dist = d
                best_md_idx = md_i

        if best_md_idx is not None:
            line_idx, _ = md_entries[best_md_idx]
            markers.append((line_idx, pg))
            cumul = best_md_idx + count
        else:
            if cumul < len(md_entries):
                line_idx, _ = md_entries[cumul]
                markers.append((line_idx, pg))
            cumul += count

    return markers


def insert_markers(lines: list[str], markers: list[tuple[int, int]]) -> list[str]:
    for line_idx, pg in sorted(markers, key=lambda x: x[0], reverse=True):
        lines.insert(line_idx, f"<!-- page:{pg} -->")
    return lines


def main() -> None:
    parser = argparse.ArgumentParser(description="Insert page markers into markdown from Wikisource")
    parser.add_argument("--md", required=True, type=Path, help="Markdown file (modified in-place)")
    parser.add_argument("--cache", type=Path, help="Wikisource HTML cache path")
    parser.add_argument("--wikisource", help="Wikisource parent page title (triggers auto-fetch)")
    parser.add_argument("--entry-prefix", default="- **", help="Line prefix identifying entry lines")
    parser.add_argument("--dry-run", action="store_true", help="Print stats without writing")
    args = parser.parse_args()

    cache_path = args.cache
    if not cache_path:
        print("ERROR: --cache is required", file=sys.stderr)
        sys.exit(1)

    if cache_path.exists():
        cache = json.loads(cache_path.read_text(encoding="utf-8"))
        print(f"Loaded cache: {len(cache)} pages from {cache_path}")
    elif args.wikisource:
        cache = fetch_and_cache(cache_path, args.wikisource)
    else:
        print(f"ERROR: Cache not found ({cache_path}). Use --wikisource to fetch.", file=sys.stderr)
        sys.exit(1)

    page_data = extract_page_data(cache)
    total_dt = sum(count for count, _ in page_data.values())
    pages_with_entries = sum(1 for count, _ in page_data.values() if count > 0)

    md_text = args.md.read_text(encoding="utf-8")
    cleaned = re.sub(r"<!-- page:\d+ -->\n?", "", md_text)
    lines = cleaned.split("\n")

    md_entries = find_entry_lines(lines, args.entry_prefix)
    print(f"Wikisource: {total_dt} <dt> across {pages_with_entries} pages ({len(page_data)} total page indices)")
    print(f"Markdown:   {len(md_entries)} entry lines")

    if len(md_entries) != total_dt:
        print(f"WARNING: entry count mismatch ({len(md_entries)} vs {total_dt})", file=sys.stderr)

    markers = build_markers_anchored(page_data, md_entries)
    print(f"Markers:    {len(markers)} pages")

    for _, pg in markers[:3]:
        print(f"  page {pg}")
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
