from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.latn.systems.puj import create_config as create_puj_config
from scripts.latn.systems.latn_norm import create_config as create_norm_config
from scripts.latn.converter import LatnConverter

_RIME_HEADER_RE = re.compile(r'\*\*([^*]+)\*\*')
_INITIAL_CELL_RE = re.compile(r'^[a-zA-Z∅]+$')
_TONE_GROUP_RE = re.compile(r'\x5c\[(\d)\x5c\](.*?)(?=\x5c\[|$)')
_HAN_RE = re.compile(r'[\u4e00-\u9fff\u3400-\u4dbf\uf000-\uf8ff\U00020000-\U0002a6df]')
_IMG_RE = re.compile(r'<img[^>]*>')
_SPAN_RE = re.compile(r'<span[^>]*>[^<]*</span>')

INITIAL_NORM = {
    'ts': 'ch',
    'tsh': 'chh',
    'z': 'j',
}


def _clean_han(text: str) -> list[str]:
    text = _IMG_RE.sub('', text)
    text = _SPAN_RE.sub('', text)
    return _HAN_RE.findall(text)


def parse_syllabary(md_text: str):
    puj_converter = LatnConverter(create_puj_config())
    norm_converter = LatnConverter(create_norm_config())

    rows = []
    current_rime = None

    for line in md_text.split('\n'):
        stripped = line.strip()

        if stripped.startswith('#') or not stripped.startswith('|'):
            continue

        if stripped.startswith('|--------'):
            continue

        cells = [c.strip() for c in stripped.split('|')]
        cells = [c for c in cells if c]

        if not cells:
            continue

        first_cell = cells[0]

        rime_match = _RIME_HEADER_RE.search(first_cell)
        if rime_match:
            current_rime = rime_match.group(1).strip()
            continue

        if current_rime is None:
            continue

        init_match = _INITIAL_CELL_RE.match(first_cell)
        if not init_match:
            continue

        initial = first_cell.strip()

        content = cells[1] if len(cells) > 1 else ''
        for tg in _TONE_GROUP_RE.finditer(content):
            tone = tg.group(1)
            han_text = tg.group(2)
            han_chars = _clean_han(han_text)

            if not han_chars:
                continue

            puj_syllable = initial + current_rime + tone
            if initial == '∅':
                puj_syllable = current_rime + tone
            puj = puj_converter.to_handwriting(puj_syllable)

            norm_initial = INITIAL_NORM.get(initial, initial)
            if initial == '∅':
                norm_initial = ''
            norm_syllable = norm_initial + current_rime + tone
            latn_norm = norm_converter.to_handwriting(norm_syllable)
            latn_norm = latn_norm.replace('ⁿ', 'nn')

            for han in han_chars:
                rows.append((latn_norm, puj, han))

    rows.sort(key=lambda r: r[0])
    return rows


def main():
    input_path = PROJECT_ROOT / 'books' / 'ssmp.md'
    output_path = PROJECT_ROOT / 'export' / 'books' / 'ssmp.csv'

    output_path.parent.mkdir(parents=True, exist_ok=True)

    md_text = input_path.read_text(encoding='utf-8')
    rows = parse_syllabary(md_text)

    with open(output_path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['latn_norm', 'puj', 'han'])
        for row in rows:
            writer.writerow(row)

    print(f'Wrote {len(rows)} entries to {output_path}')


if __name__ == '__main__':
    main()
