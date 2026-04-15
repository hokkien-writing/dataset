from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class Entry:
    han: str
    han_orig: str
    puj: str
    puj_orig: str
    dp: str
    dp_orig: str
    bp: str
    bp_orig: str
    tl: str
    tl_orig: str
    en: str
    en_orig: str
    zh_CN: str
    zh_TW: str
    source: str


def generate_original(text: str) -> str:
    text = re.sub(r"\+\+\+\+", "", text)
    text = re.sub(r"\+\+([^\n+]+)\+\+", "", text)
    text = re.sub(r"~~([^\n~]+)~~\([^\n)]*\)", r"\1", text)
    text = re.sub(r"~~([^\n~]+)~~", r"\1", text)
    return text


def _make_replace_correction(placeholder: str):
    def _replace(m: re.Match) -> str:
        return m.group(2) if m.group(2) else placeholder

    return _replace


def generate_modified(text: str, placeholder: str = "") -> str:
    text = re.sub(r"\+\+\+\+", placeholder, text)
    text = re.sub(r"\+\+([^\n+]+)\+\+", r"\1", text)
    text = re.sub(
        r"~~([^\n~]+)~~\(([^\n)]*)\)", _make_replace_correction(placeholder), text
    )
    text = re.sub(r"~~([^\n~]+)~~", "", text)
    return text


class BookProcessor(ABC):
    @abstractmethod
    def extract_entries(self, text: str, source_name: str) -> list[Entry]:
        pass

    @staticmethod
    def clean(text: str) -> str:
        text = re.sub(r"\[\d+\]", "", text)
        return re.sub(r"\s+", " ", text).strip()
