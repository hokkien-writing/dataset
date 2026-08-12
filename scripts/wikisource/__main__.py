"""Fetch a Wikisource Page-namespace book, convert to markdown, and postprocess.

Usage:
    PYTHONPATH=. python3 -m scripts.wikisource \\
        --title "Dictionary of the Swatow dialect.djvu" \\
        --start 1 --end 648 \\
        --output books/007_A_Pronouncing_and_Defining_Dictionary_of_the_Swatow_Dialect.md

    PYTHONPATH=. python3 -m scripts.wikisource \\
        --title "Dictionary of the Swatow dialect.djvu" \\
        --start 1 --end 648 \\
        --output book.md --offline
"""

from __future__ import annotations

import argparse
import importlib
import sys
from pathlib import Path

from scripts.wikisource.fetch import PAGE_PREFIX, run_fetch
from scripts.wikisource.wikitext import build_markdown, validate_page_markers

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

_SWATOW_MODULE = importlib.import_module(
    "scripts.wikisource.007_A_Pronouncing_and_Defining_Dictionary_of_the_Swatow_Dialect"
)
postprocess = _SWATOW_MODULE.postprocess


def main():
    parser = argparse.ArgumentParser(description="Fetch Wikisource book to markdown")
    parser.add_argument("--title", required=True, help="Wikisource index title (without Page: prefix)")
    parser.add_argument("--start", type=int, required=True, help="First page number")
    parser.add_argument("--end", type=int, required=True, help="Last page number")
    parser.add_argument("--output", required=True, help="Output markdown file path")
    parser.add_argument("--cache-dir", default=None, help="Directory for cached wikitext pages")
    parser.add_argument("--offline", action="store_true", help="Read from cache only, no network requests")
    args = parser.parse_args()

    page_prefix = f"{PAGE_PREFIX}{args.title}/"
    output = Path(args.output)
    cache_dir = Path(args.cache_dir) if args.cache_dir else PROJECT_ROOT / "tmp" / args.title.replace(".djvu", "").replace(" ", "_")

    pages: dict[int, str] = {}
    if args.offline:
        for n in range(args.start, args.end + 1):
            p = cache_dir / f"p{n:03d}.wikitext"
            if p.exists():
                pages[n] = p.read_text(encoding="utf-8")
        print(f"Read {len(pages)} pages from cache", file=sys.stderr)
    else:
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
    content = postprocess(content, args.title)
    validate_page_markers(content, args.start, args.end)

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(content, encoding="utf-8")
    print(f"Wrote {len(content):,} bytes, {content.count(chr(10)) + 1} lines to {output}", file=sys.stderr)


if __name__ == "__main__":
    main()
