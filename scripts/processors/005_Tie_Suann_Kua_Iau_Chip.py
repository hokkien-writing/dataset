from __future__ import annotations

import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.processors.base import BookProcessor, Entry

_PAGE_RE = re.compile(r"<!--\s*page:(\d+)\s*-->")
_HEADING_RE = re.compile(r"^(#+)\s+(.+?)\s*$")
_IMG_MD_RE = re.compile(r"!\[[^\]]*\]\([^)]*\)")
_ITALIC_COMMENT_RE = re.compile(r"^\s*\*[^*]*\*\s*$")
_HR_RE = re.compile(r"^-{3,}\s*$")

_CIRCLED_RE = re.compile(
    "["
    "\u2295-\u229f"
    "\u2460-\u24ff"
    "\u3220-\u3229"
    "\u3280-\u32bf"
    "]"
)

_CJK_RE = re.compile(r"[\u4e00-\u9fff\u3400-\u4dbf\U00020000-\U0002a6df\uf000-\uf8ff]")

_SENTENCE_SPLIT_RE = re.compile(r"[，。！？；：,.!?;:\n]+")

_STRIP_CHARS = " \t\u3000\"'\u2018\u2019\u201c\u201d「」『』（）()《》〈〉、·．…—―－\\-*＊"

_END_OF_BOOK_RE = re.compile(r"广东人民出版社|新华书店|印刷厂|统一书号|第\d+版|选注|潮\s*汕\s*歌\s*谣\s*集")

_SKIP_TITLES = {
    "潮汕歌謠集", "潮汕歌谣集",
    "目錄", "目录",
    "序",
    "愿望", "原望",
    "失望",
    "同情",
    "嗟叹", "嗟嘆",
    "賛嘆", "贊嘆", "赞叹", "赞嘆",
    "吟咏故事",
    "即景、抒描", "即景抒描",
    "諷刺", "讽刺",
    "談諧", "谈谱", "谈谐",
    "喜劇", "喜剧",
    "悲劇", "悲剧",
    "游戏歌", "遊戲歌",
}


def _is_annotation_line(line: str) -> bool:
    stripped = line.lstrip(" \t\u3000")
    if not stripped:
        return False
    return bool(_CIRCLED_RE.match(stripped))


def _clean_text(text: str) -> str:
    text = _CIRCLED_RE.sub("", text)
    text = _IMG_MD_RE.sub("", text)
    return text


def _split_sentences(text: str) -> list[str]:
    out: list[str] = []
    for p in _SENTENCE_SPLIT_RE.split(text):
        s = p.strip(_STRIP_CHARS)
        if not s:
            continue
        if not _CJK_RE.search(s):
            continue
        out.append(s)
    return out


class Processor(BookProcessor):
    def extract_entries(self, text: str, source_name: str) -> list[Entry]:
        entries: list[Entry] = []
        page = ""
        title = ""
        in_song = False

        for raw in text.split("\n"):
            line = raw.rstrip()

            m = _PAGE_RE.search(line)
            if m:
                page = m.group(1)
                continue

            if _HR_RE.match(line):
                continue

            if not line.strip():
                continue

            m = _HEADING_RE.match(line)
            if m:
                heading = _clean_text(m.group(2)).strip()
                if heading in _SKIP_TITLES:
                    title = ""
                    in_song = False
                else:
                    title = heading
                    in_song = True
                continue

            if not in_song:
                continue

            if _END_OF_BOOK_RE.search(line):
                in_song = False
                continue

            if _ITALIC_COMMENT_RE.match(line):
                continue

            if line.lstrip().startswith("!["):
                continue

            if _is_annotation_line(line):
                continue

            cleaned = _clean_text(line)
            source = f"{source_name} > {title}" if title else source_name
            for sentence in _split_sentences(cleaned):
                entries.append(Entry(
                    han=sentence,
                    han_orig="",
                    puj="",
                    puj_orig="",
                    source=source,
                    page_num=page,
                ))

        return entries
