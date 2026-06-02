#!/usr/bin/env python3
"""
Insert <!-- page:N --> markers into book markdown using Wikisource page data.

Algorithm:
  1. Aggregate <dt> counts per page_index across all Wikisource subpages
  2. Count entry lines (- **...) in cleaned markdown
  3. Walk pages in order, cumulate <dt> counts → map to entry line index
  4. Insert markers at correct positions (bottom-up to preserve indices)

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


def count_dts_per_page(cache: dict[str, str]) -> dict[int, int]:
    page_counts: dict[int, int] = defaultdict(int)
    for html in cache.values():
        markers = list(re.finditer(r'data-page-index="(\d+)"', html))
        for i, m in enumerate(markers):
            pg = int(m.group(1))
            chunk_start = m.end()
            chunk_end = markers[i + 1].start() if i + 1 < len(markers) else len(html)
            chunk = html[chunk_start:chunk_end]
            dts = re.findall(r'<dt[^>]*>', chunk)
            page_counts[pg] += len(dts)
    return dict(page_counts)


def find_entry_lines(lines: list[str], prefix: str) -> list[int]:
    indices = []
    for i, line in enumerate(lines):
        if line.strip().startswith(prefix):
            indices.append(i)
    return indices


def build_markers(page_counts: dict[int, int], entry_count: int) -> tuple[list[tuple[int, int]], int]:
    sorted_pages = sorted(page_counts)
    cumul = 0
    markers = []
    for pg in sorted_pages:
        count = page_counts[pg]
        if count == 0:
            continue
        if cumul >= entry_count:
            print(f"  WARNING: cumul={cumul} >= {entry_count} at page {pg}", file=sys.stderr)
            break
        markers.append((cumul, pg))
        cumul += count
    return markers, cumul


def insert_markers(lines: list[str], entry_indices: list[int], markers: list[tuple[int, int]]) -> list[str]:
    insertions = []
    for entry_offset, pg in markers:
        line_idx = entry_indices[entry_offset]
        insertions.append((line_idx, pg))

    for line_idx, pg in sorted(insertions, key=lambda x: x[0], reverse=True):
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

    page_counts = count_dts_per_page(cache)
    total_dt = sum(page_counts.values())
    pages_with_entries = sum(1 for c in page_counts.values() if c > 0)

    md_text = args.md.read_text(encoding="utf-8")
    cleaned = re.sub(r"<!-- page:\d+ -->\n?", "", md_text)
    lines = cleaned.split("\n")

    entry_indices = find_entry_lines(lines, args.entry_prefix)
    print(f"Wikisource: {total_dt} <dt> across {pages_with_entries} pages ({len(page_counts)} total page indices)")
    print(f"Markdown:   {len(entry_indices)} entry lines")

    if len(entry_indices) != total_dt:
        print(f"WARNING: entry count mismatch ({len(entry_indices)} vs {total_dt})", file=sys.stderr)

    markers, consumed = build_markers(page_counts, len(entry_indices))
    print(f"Markers:    {len(markers)} pages (consumed {consumed} entries)")

    for _, pg in markers[:3]:
        print(f"  page {pg}")
    print("  ...")
    for _, pg in markers[-3:]:
        print(f"  page {pg}")

    if args.dry_run:
        print("\n(dry run, not writing)")
        return

    lines = insert_markers(lines, entry_indices, markers)
    args.md.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nWrote {len(lines)} lines to {args.md.name}")


if __name__ == "__main__":
    main()
