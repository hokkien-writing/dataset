from __future__ import annotations

import re

_WORD_APOSTROPHE_RE = re.compile(r"(?<=\w)[‘’](?=\w)")
_ROMAN_SPACE_BEFORE_RE = re.compile(r"[^\S\r\n]+([,.;:!?\)])")
_ROMAN_SPACE_AFTER_OPEN_RE = re.compile(r"([\(])[^\S\r\n]+")
_CHINESE_SPACE_RE = re.compile(r"[ \t]*([，。；：！？（）“”‘’])[ \t]*")
_TERMINAL_CLOSERS_RE = re.compile(r"([\"')\]]*)$")

_TO_ROMAN = str.maketrans(
    {
        "，": ",",
        "。": ".",
        "；": ";",
        "：": ":",
        "！": "!",
        "？": "?",
        "（": "(",
        "）": ")",
        "“": '"',
        "”": '"',
        "‘": "'",
        "’": "'",
    }
)

_TO_CHINESE = {
    ",": "，",
    ".": "。",
    ";": "；",
    ":": "：",
    "!": "！",
    "?": "？",
    "(": "（",
    ")": "）",
}


def _is_word_apostrophe(text: str, index: int) -> bool:
    previous = text[index - 1] if index else ""
    following = text[index + 1] if index + 1 < len(text) else ""
    return previous.isalnum() and following.isalnum()


def _needs_roman_space(
    text: str,
    index: int,
    next_index: int,
    double_open: bool,
    single_open: bool,
) -> bool:
    if next_index >= len(text):
        return False
    next_char = text[next_index]
    if next_char in ",.;:!?)]}~*_]`":
        return False
    if next_char == '"' and not double_open:
        return False
    if next_char == "'" and (not single_open or _is_word_apostrophe(text, next_index)):
        return False
    previous = text[index - 1] if index else ""
    if previous.isdigit() and next_char.isdigit():
        return False
    if (
        text[index] == "."
        and previous.isalpha()
        and next_char.isalpha()
        and next_index + 1 < len(text)
        and text[next_index + 1] == "."
    ):
        return False
    return True


def _space_roman_punctuation(text: str) -> str:
    out: list[str] = []
    double_open = True
    single_open = True
    index = 0
    while index < len(text):
        char = text[index]
        out.append(char)
        if char == '"':
            double_open = not double_open
        elif char == "'" and not _is_word_apostrophe(text, index):
            single_open = not single_open
        if char in ",.;:!?":
            next_index = index + 1
            while (
                next_index < len(text)
                and text[next_index].isspace()
                and text[next_index] not in "\r\n"
            ):
                next_index += 1
            if _needs_roman_space(text, index, next_index, double_open, single_open):
                out.append(" ")
            index = next_index
            continue
        index += 1
    normalized = "".join(out)
    normalized = re.sub(r"(?<=\))(?=[\"'])", " ", normalized)
    return re.sub(r"(?<=\")(?=')", " ", normalized)


def to_roman_punctuation(text: str) -> str:
    normalized = _WORD_APOSTROPHE_RE.sub("'", text)
    normalized = normalized.translate(_TO_ROMAN)
    normalized = _ROMAN_SPACE_BEFORE_RE.sub(r"\1", normalized)
    normalized = _ROMAN_SPACE_AFTER_OPEN_RE.sub(r"\1", normalized)
    return _space_roman_punctuation(normalized)


def _terminal_mark(text: str) -> str:
    body = _TERMINAL_CLOSERS_RE.sub("", text.rstrip())
    return body[-1] if body and body[-1] in ".?!" else ""


def _insert_terminal_mark(text: str, mark: str) -> str:
    stripped = text.rstrip()
    match = _TERMINAL_CLOSERS_RE.search(stripped)
    closers = match.group(1) if match else ""
    body = stripped[: -len(closers)] if closers else stripped
    return f"{body}{mark}{closers}"


def normalize_english_gloss(text: str) -> str:
    normalized = to_roman_punctuation(text)
    normalized = re.sub(r"([,;:!?])(?=\*)", r"\1 ", normalized)
    return normalized


def normalize_roman_reading(text: str, gloss: str = "") -> str:
    normalized = to_roman_punctuation(text)
    gloss_mark = _terminal_mark(to_roman_punctuation(gloss))
    if gloss_mark not in ("?", "!"):
        return normalized
    reading_mark = _terminal_mark(normalized)
    if reading_mark:
        stripped = normalized.rstrip()
        match = _TERMINAL_CLOSERS_RE.search(stripped)
        closers = match.group(1) if match else ""
        body = stripped[: -len(closers)] if closers else stripped
        body = body[:-1]
        return f"{body}{gloss_mark}{closers}"
    stripped = normalized.rstrip()
    match = _TERMINAL_CLOSERS_RE.search(stripped)
    closers = match.group(1) if match else ""
    body = stripped[: -len(closers)] if closers else stripped
    if body.endswith((",", ";", ":")):
        body = body[:-1]
        return f"{body}{gloss_mark}{closers}"
    return _insert_terminal_mark(normalized, gloss_mark)


def _to_chinese_characters(text: str) -> str:
    out: list[str] = []
    double_open = True
    single_open = True
    for index, char in enumerate(text):
        previous = text[index - 1] if index else ""
        following = text[index + 1] if index + 1 < len(text) else ""
        if char == "'":
            if previous.isalnum() and following.isalnum():
                out.append(char)
            else:
                out.append("‘" if single_open else "’")
                single_open = not single_open
            continue
        if char == '"':
            out.append("“" if double_open else "”")
            double_open = not double_open
            continue
        out.append(_TO_CHINESE.get(char, char))
    return "".join(out)


def to_chinese_punctuation(text: str) -> str:
    normalized = _WORD_APOSTROPHE_RE.sub("'", text)
    normalized = _to_chinese_characters(normalized)
    return _CHINESE_SPACE_RE.sub(r"\1", normalized)
