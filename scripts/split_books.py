#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
BOOKS_DIR = PROJECT_ROOT / "export" / "books"
OUTPUT_DIR = PROJECT_ROOT / "tmp"


_SOURCE_NOTE = "> 📌 資料來源：[hokkien-writing/dataset](https://github.com/AuTa/hokkien-writing-dataset) 專案。內容經過校勘處理。"

_ANNOTATION_RE = re.compile(r"\[(?:訓|音|替|白)\]")


def _clean_annotations(text: str) -> str:
    return _ANNOTATION_RE.sub("", text)


def _slugify(text: str) -> str:
    text = text.strip().rstrip(".")
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "_", text)
    return text.strip("_")[:80]


def _kebabify(text: str) -> str:
    text = text.strip().rstrip(".")
    text = text.lower()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    return text.strip("-")[:80]


def _make_front_matter(book_h1: str, chapter_title: str, p_value: str) -> str:
    title = book_h1
    if chapter_title:
        title = f"{book_h1} / {chapter_title}"
    date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return f"---\ntitle: {title}\np: {p_value}\ndate: {date}\n---\n\n"


def _split_sections(content: str, level: int) -> list[tuple[str, str]]:
    prefix = "#" * level
    pat = re.compile(rf"^{re.escape(prefix)}\s+(.+)", re.MULTILINE)
    matches = list(pat.finditer(content))
    if not matches:
        return []

    sections: list[tuple[str, str]] = []
    for i, m in enumerate(matches):
        title = m.group(1).strip()
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(content)
        sections.append((title, content[start:end]))

    preamble = content[: matches[0].start()]
    if preamble.strip():
        sections.insert(0, ("", preamble))

    return sections


def _extract_h1_preamble(content: str) -> tuple[str, str]:
    h2_pat = re.compile(r"^##\s+", re.MULTILINE)
    m = h2_pat.search(content)
    if not m:
        return content, ""
    preamble = content[: m.start()]
    rest = content[m.start() :]
    return preamble, rest


def split_book_file(md_path: Path) -> tuple[list[list[tuple[Path, str]]], str, str, str]:
    stem = md_path.stem
    book_prefix = re.sub(r"_modified$", "", stem)
    content = md_path.read_text(encoding="utf-8")

    h1_preamble, content = _extract_h1_preamble(content)
    h1_m = re.match(r"^#\s+(.+)", h1_preamble, re.MULTILINE)
    h1_title = h1_m.group(1).strip() if h1_m else ""

    h2_sections = _split_sections(content, 2)
    need_sub_split = len(h2_sections) < 6

    chapters_by_h2: list[list[tuple[str, str]]] = []
    if need_sub_split:
        for h2_title, h2_body in h2_sections:
            h3_sections = _split_sections(h2_body, 3)
            if h3_sections:
                sub: list[tuple[str, str]] = []
                for h3_title, h3_body in h3_sections:
                    sub.append((h3_title if h3_title else h2_title, h3_body))
                chapters_by_h2.append(sub)
            else:
                chapters_by_h2.append([(h2_title, h2_body)])
    else:
        for title, body in h2_sections:
            chapters_by_h2.append([(title, body)])

    book_dir = OUTPUT_DIR / book_prefix
    if book_dir.exists():
        for f in book_dir.iterdir():
            f.unlink()
    book_dir.mkdir(parents=True, exist_ok=True)

    book_path_prefix = re.sub(r"^\d+_", "", book_prefix)

    file_groups: list[list[tuple[Path, str]]] = []
    for h2_idx, group in enumerate(chapters_by_h2, 1):
        subgroup: list[tuple[Path, str]] = []
        paths_in_group: list[Path] = []
        first_is_empty = False
        for sub_idx, (title, body) in enumerate(group, 1):
            if title:
                slug = _slugify(title)
            else:
                slug = "preamble"

            if len(group) == 1:
                filename = f"{h2_idx:02d}_{slug}.md"
            else:
                filename = f"{h2_idx:02d}_{sub_idx:02d}_{slug}.md"

            p_val = f"{book_path_prefix}/{filename[:-3]}"

            fm = _make_front_matter(h1_title, title if title else h1_title, p_val)
            back_link = f"[↩️ 轉總目錄](/{book_path_prefix})\n\n"
            out_path = book_dir / filename
            out_path.write_text(fm + _SOURCE_NOTE + "\n\n\n" + back_link + _clean_annotations(body), encoding="utf-8")
            subgroup.append((out_path, title))
            paths_in_group.append(out_path)

            if sub_idx == 1:
                heading_m = re.match(r"^#{2,3}\s+.+", body, re.MULTILINE)
                after = body[body.index("\n") + 1:].strip() if "\n" in body else ""
                first_is_empty = bool(heading_m) and not after

        file_groups.append(subgroup)

        if len(paths_in_group) > 1 and first_is_empty:
            first_path = paths_in_group[0]
            first_body = first_path.read_text(encoding="utf-8")
            sub_links = [first_body.rstrip(), ""]
            for p in paths_in_group[1:]:
                t = _read_title(p)
                sub_links.append(f"- [{t}]({p.stem})")
            sub_links.append("")
            first_path.write_text("\n".join(sub_links), encoding="utf-8")

    return file_groups, book_prefix, h1_preamble, h1_title


def _read_title(p: Path) -> str:
    text = p.read_text(encoding="utf-8")
    if text.startswith("---"):
        end = text.find("---", 3)
        if end != -1:
            text = text[end + 3:]
    hm = re.search(r"^#{2,3}\s+(.+)", text, re.MULTILINE)
    return hm.group(1).strip() if hm else p.stem


def write_index(
    book_outputs: dict[str, tuple[str, str, list[list[tuple[Path, str]]]]],
) -> list[Path]:
    index_paths: list[Path] = []
    for book_prefix, (h1_preamble, h1_title, groups) in sorted(book_outputs.items()):
        book_dir = OUTPUT_DIR / book_prefix
        book_path_prefix = re.sub(r"^\d+_", "", book_prefix)
        parts: list[str] = []
        parts.append(_make_front_matter(h1_title, "", book_path_prefix))
        parts.append(_SOURCE_NOTE)
        if h1_preamble.strip():
            pre_lines = h1_preamble.split("\n")
            rest = "\n".join(pre_lines[1:]).strip()
            if rest:
                parts.append("")
                parts.append(rest)
        parts.append("")
        parts.append("---")
        parts.append("")
        for group in groups:
            if len(group) == 1:
                p, _ = group[0]
                title_line = _read_title(p)
                parts.append(f"- [{title_line}]({p.stem})")
            else:
                first_p, _ = group[0]
                first_heading = _read_title(first_p)
                parts.append(f"- **{first_heading}**")
                for p, _ in group[1:]:
                    title_line = _read_title(p)
                    parts.append(f"  - [{title_line}]({p.stem})")
        parts.append("")

        index_path = book_dir / "index.md"
        index_path.write_text("\n".join(parts), encoding="utf-8")
        index_paths.append(index_path)

    return index_paths


def main():
    md_files = sorted(BOOKS_DIR.glob("*_modified.md"))
    if not md_files:
        print("No *_modified.md files found in", BOOKS_DIR)
        sys.exit(1)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    book_outputs: dict[str, tuple[str, str, list[list[tuple[Path, str]]]]] = {}
    for md_path in md_files:
        file_groups, prefix, h1_preamble, h1_title = split_book_file(md_path)
        book_outputs[prefix] = (h1_preamble, h1_title, file_groups)
        count = sum(len(g) for g in file_groups)
        print(f"Split {md_path.name} -> {count} chapters in tmp/{prefix}/")

    index_path = write_index(book_outputs)
    print(f"Index written to {index_path}")


if __name__ == "__main__":
    main()
