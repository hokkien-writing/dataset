from __future__ import annotations

import sys
import time
from pathlib import Path

PAGE_PREFIX = "Page:"
BATCH_SIZE = 50
SLEEP_BETWEEN_BATCHES = 5.0
MAX_ATTEMPTS = 4


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
