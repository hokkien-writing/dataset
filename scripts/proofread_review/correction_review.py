from __future__ import annotations

import importlib
from dataclasses import dataclass

from scripts.processors.base import generate_modified, generate_original
from scripts.proofread_review.models import ReviewDataset, ReviewRecord
from scripts.wikisource.corrections import CorrectionCatalog, CorrectionRule, catalog_digest
from scripts.wikisource.wikitext import build_markdown

_SWATOW = importlib.import_module(
    "scripts.wikisource.007_A_Pronouncing_and_Defining_Dictionary_of_the_Swatow_Dialect"
)


@dataclass(frozen=True)
class SourceEntry:
    page: int
    headword: str
    reading: str
    gloss: str
    key: tuple[str, str, str]


SourceIndex = dict[tuple[str, str, str], list[int]]
SourcePairIndex = dict[tuple[str, str], list[int]]


def build_pre_correction_markdown(
    pages: dict[int, str],
    start: int,
    end: int,
    title: str = "",
) -> str:
    content = build_markdown(pages, start, end)
    return _SWATOW.preprocess_before_corrections(content, title)


def build_source_entries(text: str) -> list[SourceEntry]:
    entries: list[SourceEntry] = []
    page = 0
    for line in text.split("\n"):
        marker = _SWATOW._PAGE_MARKER_RE.search(line.strip())
        if marker:
            page = int(marker.group(1))
            continue
        match = _SWATOW._HEAD_LINE_RE.match(line)
        if match:
            prefix, reading, suffix, gloss = match.groups()
            entries.append(
                SourceEntry(
                    page=page,
                    headword=_SWATOW._headword_from_prefix(prefix),
                    reading=reading,
                    gloss=gloss or "",
                    key=_entry_key(reading, gloss, page),
                )
            )
            continue
        match = _SWATOW._EX_LINE_RE.match(line)
        if match:
            prefix, reading, suffix, gloss = match.groups()
            entries.append(
                SourceEntry(
                    page=page,
                    headword="",
                    reading=reading,
                    gloss=gloss or "",
                    key=_entry_key(reading, gloss, page),
                )
            )
    return entries


def split_markdown_pages(text: str) -> dict[int, str]:
    pages: dict[int, list[str]] = {}
    page = 0
    for line in text.splitlines():
        marker = _SWATOW._PAGE_MARKER_RE.fullmatch(line.strip())
        if marker:
            page = int(marker.group(1))
            pages.setdefault(page, [])
        elif page:
            pages[page].append(line)
    return {
        number: "\n".join(lines).strip() + "\n"
        for number, lines in pages.items()
        if any(line.strip() for line in lines)
    }


def _entry_key(reading: str, gloss: str, page: int) -> tuple[str, str, str]:
    return (
        _SWATOW._clean(generate_original(reading)),
        _SWATOW._clean(generate_modified(gloss or "")),
        page,
    )


def _index_sources(
    entries: list[SourceEntry],
) -> tuple[SourceIndex, SourceIndex, SourcePairIndex]:
    by_key: SourceIndex = {}
    by_norm: SourceIndex = {}
    by_norm_pair: SourcePairIndex = {}
    for index, entry in enumerate(entries):
        normalized = _SWATOW._review_compatible_key(entry.key)
        by_key.setdefault(entry.key, []).append(index)
        by_norm.setdefault(normalized, []).append(index)
        by_norm_pair.setdefault(normalized[:2], []).append(index)
    return by_key, by_norm, by_norm_pair


def _resolve_index(
    rule: CorrectionRule,
    entries: list[SourceEntry],
    by_key: SourceIndex,
    by_norm: SourceIndex,
    by_norm_pair: SourcePairIndex,
) -> tuple[int, SourceEntry]:
    reading, gloss, key_page = rule.key
    key_page_number = int(key_page)
    lookup_key = (reading, gloss, key_page_number)
    compatible = _SWATOW._review_compatible_key(lookup_key)
    lookup_keys = [lookup_key, compatible] if compatible != lookup_key else [lookup_key]
    if rule.rule_type == "headword_review":

        def matches_headword(index: int) -> bool:
            return entries[index].headword == rule.headword

    else:

        def matches_headword(index: int) -> bool:
            return True

    exact: list[int] = []
    for candidate in lookup_keys:
        for index in by_key.get(candidate, []):
            if matches_headword(index) and index not in exact:
                exact.append(index)
        for index in by_norm.get(candidate, []):
            if matches_headword(index) and index not in exact:
                exact.append(index)
    if len(exact) > 1:
        raise ValueError(
            f"rule {rule.rule_id} ({rule.rule_type}) ambiguous: "
            f"multiple source entries match key {rule.key}"
        )
    if len(exact) == 1:
        index = exact[0]
        return index, entries[index]
    pairs = [(reading, gloss)]
    compatible_pair = (compatible[0], compatible[1])
    if compatible_pair not in pairs:
        pairs.append(compatible_pair)
    nearby = [
        index
        for pair in pairs
        for index in by_norm_pair.get(pair, [])
        if matches_headword(index)
        and entries[index].page != key_page_number
        and abs(entries[index].page - key_page_number) <= 2
    ]
    nearby = list(dict.fromkeys(nearby))
    if len(nearby) > 1:
        raise ValueError(
            f"rule {rule.rule_id} ({rule.rule_type}) ambiguous: "
            f"multiple nearby source entries match key {rule.key}"
        )
    if len(nearby) == 1:
        index = nearby[0]
        return index, entries[index]
    raise ValueError(
        f"rule {rule.rule_id} ({rule.rule_type}) unresolved: "
        f"no source entry matches key {rule.key}"
    )


def build_correction_review_dataset(
    catalog: CorrectionCatalog,
    source_entries: list[SourceEntry],
) -> ReviewDataset:
    groups: dict[str, list[CorrectionRule]] = {}
    for rule in catalog.rules:
        groups.setdefault(rule.rule_id, []).append(rule)
    by_key, by_norm, by_norm_pair = _index_sources(source_entries)
    digest = catalog_digest(catalog)
    records: list[ReviewRecord] = []
    errors: list[str] = []
    for rule_id in sorted(groups):
        group = sorted(groups[rule_id], key=lambda rule: rule.output_index)
        rule = group[0]
        try:
            index, resolved = _resolve_index(
                rule, source_entries, by_key, by_norm, by_norm_pair
            )
        except ValueError as error:
            errors.append(str(error))
            continue
        current = {"reading": resolved.reading, "gloss": resolved.gloss}
        if rule.rule_type == "example_split":
            proposal = {
                "reading": "\n".join(item.replacement_reading for item in group),
                "gloss": "\n".join(item.replacement_gloss for item in group),
            }
            reading_lines = [line for line in proposal["reading"].split("\n") if line]
            gloss_lines = [line for line in proposal["gloss"].split("\n") if line]
            if len(reading_lines) != len(gloss_lines):
                errors.append(
                    f"rule {rule.rule_id} ({rule.rule_type}) proposal line counts differ"
                )
                continue
        else:
            proposal = {
                "reading": rule.replacement_reading or current["reading"],
                "gloss": rule.replacement_gloss or current["gloss"],
            }
        context = {
            "rule_id": rule.rule_id,
            "rule_type": rule.rule_type,
            "headword": rule.headword,
            "key_reading": rule.key[0],
            "key_gloss": rule.key[1],
            "key_page": rule.key[2],
            "resolved_page": str(resolved.page),
            "output_count": str(len(group)),
            "catalog_digest": digest,
        }
        if len(group) > 1:
            context["output_indexes"] = ",".join(str(item.output_index) for item in group)
        records.append(
            ReviewRecord.from_dict(
                {
                    "row": index,
                    "page": resolved.page,
                    "issues": ["rule_review"],
                    "table_key": list(resolved.key),
                    "current": current,
                    "proposal": proposal,
                    "context": context,
                }
            )
        )
    if errors:
        raise ValueError("; ".join(errors))
    return ReviewDataset.from_records(records)
