from __future__ import annotations

import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.latn.converter import LatnConverter
from scripts.latn.systems.puj import create_config as create_puj_config
from scripts.processors.base import BookProcessor, Entry

_PUJ_CONVERTER = LatnConverter(create_puj_config())

_PAGE_RE = re.compile(r"<!-- page:(\d+) -->")

_SECTION_RE = re.compile(r"# （([^）]+)）部(.+)")

_INITIAL_RE = re.compile(r"^（([^）]+)）\s*$")

_ENTRY_RE = re.compile(r"^-\s+(.+)$")

_CJK_RE = re.compile(
    r"[\u4e00-\u9fff\u3400-\u4dbf\uf900-\ufaff"
    r"\U00020000-\U0002a6df\U0002a700-\U0002ebef"
    r"\U0002f800-\U0002fa1f]"
)

_CJK_START_RE = re.compile(
    r"^[\u4e00-\u9fff\u3400-\u4dbf\uf900-\ufaff"
    r"\U00020000-\U0002a6df\U0002a700-\U0002ebef"
    r"\U0002f800-\U0002fa1f]"
)

_INITIAL_PUJ: dict[str, str] = {
    "柳": "l",
    "邊": "p",
    "求": "k",
    "去": "kh",
    "地": "t",
    "坡": "ph",
    "他": "th",
    "增": "ts",
    "曾": "ts",
    "入": "j",
    "時": "s",
    "英": "",
    "文": "b",
    "語": "g",
    "出": "tsh",
    "喜": "h",
}

_VALID_INITIALS = frozenset(_INITIAL_PUJ.keys())

_DITTO_RE = re.compile(r"[丨｜]")

_TONE_MAP: dict[str, str] = {
    "上平聲": "1",
    "上上聲": "2",
    "上去聲": "3",
    "上入聲": "4",
    "下平聲": "5",
    "下上聲": "6",
    "下去聲": "7",
    "下入聲": "8",
}
_RIME_PUJ: dict[str, tuple[str, str]] = {
    "君": ("un", "ut"),
    "家": ("e", "eh"),
    "高": ("au", "auh"),
    "金": ("im", "ip"),
    "雞": ("oi", "oih"),
    "公": ("ong", "ok"),
    "姑": ("ou", "oh"),
    "兼": ("iam", "iap"),
    "基": ("i", "ih"),
    "堅": ("ian", "iat"),
    "京": ("iann", "iannh"),
    "官": ("uan", "uat"),
    "皆": ("ai", "aih"),
    "恭": ("iong", "iok"),
    "囗君": ("in", "it"),
    "⿴囗君": ("in", "it"),
    "鈎": ("au", "auh"),
    "居": ("ur", "urh"),
    "歌": ("o", "oh"),
    "光": ("uang", "uak"),
    "歸": ("ui", "uih"),
    "庚": ("enn", "ennh"),
    "鳩": ("iu", "iuh"),
    "囗瓜": ("ua", "uah"),
    "⿴囗瓜": ("ua", "uah"),
    "江": ("ang", "ak"),
    "膠": ("a", "ah"),
    "嬌": ("iou", "iouh"),
    "乖": ("uai", "uaih"),
    "肩": ("oin", "oit"),
    "扛": ("ng", "ngh"),
    "弓": ("eng", "ek"),
    "龜": ("u", "uh"),
    "柑": ("an", "at"),
    "佳": ("e", "eh"),
    "甘": ("am", "ap"),
    "瓜": ("ue", "ueh"),
    "薑": ("iang", "iak"),
    "燒": ("io", "ioh"),
}


def _extract_headword(text: str) -> str:
    for ch in text.strip():
        if _CJK_RE.match(ch):
            return ch
    return ""


class Processor(BookProcessor):
    def extract_entries(self, text: str, source_name: str) -> list[Entry]:
        entries: list[Entry] = []
        page = ""
        current_rime = ""
        current_tone_label = ""
        current_tone_num = ""
        current_initial = ""

        for line in text.splitlines():
            m = _PAGE_RE.match(line)
            if m:
                page = m.group(1)
                continue

            if not page:
                continue
            if page in ("1", "2", "3", "4"):
                continue

            m = _SECTION_RE.match(line)
            if m:
                current_rime = m.group(1)
                current_tone_label = m.group(2).strip()
                current_tone_num = _TONE_MAP.get(current_tone_label, "")
                current_initial = ""
                continue

            m = _INITIAL_RE.match(line)
            if m and m.group(1) in _VALID_INITIALS:
                current_initial = m.group(1)
                continue

            if not current_rime or not current_tone_num or not current_initial:
                continue

            content = self._extract_entry_content(line)
            if content is None:
                continue

            headword = _extract_headword(content)
            if not headword:
                continue

            if headword == "\u4e28":
                continue

            headword_pos = content.index(headword)
            definition = content[headword_pos + len(headword):].strip()
            if len(definition) == 0:
                continue
            definition = _DITTO_RE.sub(headword, definition)

            puj = self._reconstruct_puj(current_rime, current_initial, current_tone_num)
            if not puj:
                continue

            section_label = f"（{current_rime}）部{current_tone_label}" if current_tone_label else f"（{current_rime}）部"
            fanqie = f"{current_initial}{current_rime}切"
            entries.append(Entry(
                han=headword,
                han_orig="",
                puj=puj,
                puj_orig="",
                zh_TW=definition,
                source=f"{source_name} > {section_label}",
                page_num=page,
                fanqie=fanqie,
            ))

        return entries

    @staticmethod
    def _extract_entry_content(line: str) -> str | None:
        stripped = line.strip()
        if not stripped:
            return None
        if stripped.startswith(("#", "<", "（")):
            return None
        m = _ENTRY_RE.match(line)
        if m:
            return m.group(1).strip()
        if _CJK_START_RE.match(stripped):
            return stripped
        return None

    def _reconstruct_puj(self, rime: str, initial: str, tone_num: str) -> str:
        rime_entry = _RIME_PUJ.get(rime)
        if not rime_entry:
            return ""

        init = _INITIAL_PUJ.get(initial, "")
        non_enter, enter = rime_entry
        rh = enter if tone_num in ("4", "8") else non_enter

        latn_norm = init + rh + tone_num
        return _PUJ_CONVERTER.to_handwriting(latn_norm)
