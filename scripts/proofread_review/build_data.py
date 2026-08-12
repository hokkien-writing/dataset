from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path

from scripts.proofread_review.correction_review import (
    build_correction_review_dataset,
    build_pre_correction_markdown,
    build_source_entries,
    split_markdown_pages,
)
from scripts.proofread_review.models import ReviewDataset, ReviewRecord
from scripts.wikisource.corrections import load_correction_catalog


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_ACTIONS = Path(__file__).resolve().parent / "review_actions_source.json"
DEFAULT_PROOFREAD = PROJECT_ROOT / "books/（合併校對&修正讀音）斐姑娘詞典.csv"
DEFAULT_CORRECTIONS = (
    PROJECT_ROOT
    / "scripts/wikisource/007_A_Pronouncing_and_Defining_Dictionary_of_the_Swatow_Dialect.csv"
)
DEFAULT_OUTPUT = Path(__file__).resolve().parent / "review_data.json"
DEFAULT_CACHE = PROJECT_ROOT / "tmp" / "dictionary_of_the_swatow_dialect"
DEFAULT_CACHE_START = 1
DEFAULT_CACHE_END = 648
DEFAULT_CACHE_TITLE = "Dictionary of the Swatow dialect.djvu"


def _load_existing_reading_corrections(path: Path) -> dict[tuple[str, str, str], str]:
    return load_correction_catalog(path).reading


def _is_truncated_gloss(action: dict[str, object]) -> bool:
    replacement = action.get("replacement")
    full = action.get("full_post_gloss")
    return (
        isinstance(replacement, str)
        and isinstance(full, str)
        and bool(replacement)
        and replacement != full
        and full.startswith(replacement)
    )


def build_review_dataset(
    actions_path: Path,
    proofread_path: Path,
    corrections_path: Path,
) -> ReviewDataset:
    actions = json.loads(actions_path.read_text(encoding="utf-8"))
    if not isinstance(actions, list):
        raise ValueError("actions must be a list")
    with proofread_path.open(encoding="utf-8-sig", newline="") as file:
        proofread_rows = list(csv.DictReader(file))
    existing = _load_existing_reading_corrections(corrections_path)

    reading_actions = [action for action in actions if action.get("type") == "t7_reading"]
    gloss_actions = [action for action in actions if action.get("type") == "t7_gloss"]
    proposed_reading_keys = {
        tuple(action["tbl_key"])
        for action in reading_actions
        if isinstance(action.get("tbl_key"), list)
    }

    issues_by_row: dict[int, set[str]] = defaultdict(set)
    actions_by_row: dict[int, list[dict[str, object]]] = defaultdict(list)

    def add(action: dict[str, object], issue: str) -> None:
        row = action.get("row")
        if not isinstance(row, int):
            raise ValueError("review action row must be an integer")
        issues_by_row[row].add(issue)
        if action not in actions_by_row[row]:
            actions_by_row[row].append(action)

    for action in gloss_actions:
        key_value = action.get("tbl_key")
        if not isinstance(key_value, list) or len(key_value) != 3:
            raise ValueError("review action table key is invalid")
        key = tuple(str(part) for part in key_value)
        if key[1] and (key in proposed_reading_keys or key in existing):
            add(action, "cross_type")
        if not key[1]:
            add(action, "empty_key")
        if _is_truncated_gloss(action):
            add(action, "truncated_gloss")

    for action in reading_actions:
        key_value = action.get("tbl_key")
        if not isinstance(key_value, list) or len(key_value) != 3:
            raise ValueError("review action table key is invalid")
        key = tuple(str(part) for part in key_value)
        replacement = action.get("replacement")
        if key in existing and existing[key] != replacement:
            add(action, "existing_key_conflict")

    reading_by_row = {
        action["row"]: action for action in reading_actions if action["row"] in issues_by_row
    }
    gloss_by_row = {
        action["row"]: action for action in gloss_actions if action["row"] in issues_by_row
    }
    records: list[ReviewRecord] = []
    for row_index in sorted(issues_by_row):
        if row_index >= len(proofread_rows):
            raise ValueError(f"proofread row out of range: {row_index}")
        row = proofread_rows[row_index]
        row_actions = actions_by_row[row_index]
        reading_action = reading_by_row.get(row_index)
        gloss_action = gloss_by_row.get(row_index)
        primary = gloss_action or reading_action or row_actions[0]
        key_value = primary.get("tbl_key")
        if not isinstance(key_value, list) or len(key_value) != 3:
            raise ValueError("review action table key is invalid")
        page_text = str(primary.get("page", ""))
        if not page_text.isdigit():
            raise ValueError(f"invalid dictionary page: {page_text}")
        current_reading = str(primary.get("007_puj", "") or row.get("007_puj", ""))
        current_gloss = str(
            (gloss_action or {}).get("full_post_gloss", "")
            or primary.get("007_en", "")
            or row.get("007_en", "")
        )
        proposal_reading = str(
            (reading_action or {}).get("replacement", "")
            or row.get("Proofread_读音", "")
        ).rstrip("; ")
        proposal_gloss = str(
            (gloss_action or {}).get("replacement", "")
            or row.get("Proofread_释义", "")
        )
        existing_value = existing.get(tuple(str(part) for part in key_value), "")
        record = ReviewRecord.from_dict(
            {
                "row": row_index,
                "page": int(page_text),
                "issues": sorted(issues_by_row[row_index]),
                "table_key": [str(part) for part in key_value],
                "current": {
                    "reading": current_reading,
                    "gloss": current_gloss,
                },
                "proposal": {
                    "reading": proposal_reading,
                    "gloss": proposal_gloss,
                },
                "context": {
                    "headword": str(row.get("007_字目") or row.get("字目") or ""),
                    "term": str(row.get("词条", "")),
                    "left_reading": str(row.get("读音", "")),
                    "left_gloss": str(row.get("释义", "")),
                    "kind": str(primary.get("kind", "")),
                    "existing_reading_correction": existing_value,
                },
            }
        )
        records.append(record)
    return ReviewDataset.from_records(records)


def build_corrections_dataset(
    corrections_path: Path,
    cache_dir: Path = DEFAULT_CACHE,
    start: int = DEFAULT_CACHE_START,
    end: int = DEFAULT_CACHE_END,
    title: str = DEFAULT_CACHE_TITLE,
) -> ReviewDataset:
    pages: dict[int, str] = {}
    for n in range(start, end + 1):
        path = cache_dir / f"p{n:03d}.wikitext"
        if path.exists():
            pages[n] = path.read_text(encoding="utf-8")
    if not pages:
        raise ValueError(f"no cached wikisource pages found in {cache_dir}")
    catalog = load_correction_catalog(corrections_path)
    pre = build_pre_correction_markdown(pages, start, end, title)
    source_entries = build_source_entries(pre)
    dataset = build_correction_review_dataset(catalog, source_entries)
    return ReviewDataset.from_records(
        list(dataset.records),
        page_markdown=split_markdown_pages(pre),
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("proofread", "corrections"), default="proofread")
    parser.add_argument("--actions", type=Path, default=DEFAULT_ACTIONS)
    parser.add_argument("--proofread", type=Path, default=DEFAULT_PROOFREAD)
    parser.add_argument("--corrections", type=Path, default=DEFAULT_CORRECTIONS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--cache", type=Path, default=DEFAULT_CACHE)
    parser.add_argument("--cache-start", type=int, default=DEFAULT_CACHE_START)
    parser.add_argument("--cache-end", type=int, default=DEFAULT_CACHE_END)
    parser.add_argument("--cache-title", default=DEFAULT_CACHE_TITLE)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.mode == "corrections":
        dataset = build_corrections_dataset(
            args.corrections,
            args.cache,
            args.cache_start,
            args.cache_end,
            args.cache_title,
        )
    else:
        dataset = build_review_dataset(args.actions, args.proofread, args.corrections)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(dataset.to_dict(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        f"输出 {len(dataset.records)} 个词条、"
        f"{sum(dataset.issue_counts.values())} 个问题到 {args.output}"
    )


if __name__ == "__main__":
    main()
