from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ExternalEntry:
    latn_norm: str = ""
    puj: str = ""
    dp: str = ""
    poj: str = ""
    tl: str = ""
    bp: str = ""
    han: str = ""
    han_variants: str = ""
    en: str = ""
    zh_CN: str = ""
    zh_TW: str = ""
    source: str = ""


class ExternalImporter(ABC):
    @abstractmethod
    def import_file(self, csv_path: Path, source_id: str) -> list[ExternalEntry]:
        pass

    @abstractmethod
    def get_source_name(self) -> str:
        pass
