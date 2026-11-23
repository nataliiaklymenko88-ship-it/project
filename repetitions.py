"""Модуль 3: повтори слів і словосполучень."""
from __future__ import annotations

import re
from collections import Counter
from importlib import resources
from typing import NamedTuple

from .models import Issue

_L = "A-Za-zА-Яа-яІіЇїЄєҐґ"
_WORD = re.compile(rf"[{_L}]+(?:['’ʼ\-][{_L}]+)*")
_BREAKS = re.compile(r"[.!?…;:,()\"«»]")


class Token(NamedTuple):
    word: str
    line: int
    column: int
    start: int  # абсолютна позиція в тексті
    end: int


def tokenize(text: str) -> list[Token]:
    """Слова з урахуванням кирилиці й апострофа («м'ясо»)."""
    tokens, offset = [], 0
    for n, line in enumerate(text.splitlines(keepends=True), 1):
        for m in _WORD.finditer(line):
            tokens.append(Token(m.group(), n, m.start() + 1, offset + m.start(), offset + m.end()))
        offset += len(line)
    return tokens


def load_stopwords(lang: str = "uk") -> set[str]:
    """Стоп-слова з data/stopwords_<lang>.txt."""
    try:
        path = resources.files("textsentinel").joinpath("data").joinpath(f"stopwords_{lang}.txt")
        data = path.read_text(encoding="utf-8")
    except (FileNotFoundError, OSError):
        return set()
    return {w.strip().lower() for w in data.splitlines() if w.strip() and not w.startswith("#")}


def find_repeated_words(text: str, min_length: int = 2, window: int = 1) -> list[Issue]:
    """Однакові слова поруч («що що», «це це»). Межі речень і коми — не повтор."""
    toks = tokenize(text)
    issues = []
    for i, t in enumerate(toks):
        w = t.word.lower()
        if len(w) < min_length:
            continue
        for p in toks[max(0, i - window):i]:
            if p.word.lower() == w and not _BREAKS.search(text[p.end:t.start]):
                issues.append(Issue("repeated_word", t.line, t.column, f"{p.word} {t.word}",
                                    f"Повтор слова «{t.word}»", "warning",
                                    f"Видаліть зайве «{t.word}»"))
                break
    return issues


def find_frequent_words(text: str, top_n: int = 10, stopwords: set[str] | None = None,
                        min_count: int = 3, min_length: int = 4) -> list[Issue]:
    """Слова, що зустрічаються надто часто (без стоп-слів)."""
    stop = load_stopwords() if stopwords is None else stopwords
    counts, first = Counter(), {}
    for t in tokenize(text):
        w = t.word.lower()
        if len(w) >= min_length and w not in stop:
            counts[w] += 1
            first.setdefault(w, t)
    issues = []
    for w, c in counts.most_common(top_n):
        if c >= min_count:
            t = first[w]
            issues.append(Issue("frequent_word", t.line, t.column, w,
                                f"Слово «{w}» вжито {c} разів", "info",
                                "Підберіть синоніми або скоротіть"))
    return issues


def find_repeated_bigrams(text: str, n: int = 2, min_count: int = 3,
                          stopwords: set[str] | None = None) -> list[Issue]:
    """Словосполучення з n слів, що повторюються min_count разів і більше."""
    stop = load_stopwords() if stopwords is None else stopwords
    toks = tokenize(text)
    counts, first = Counter(), {}
    for i in range(len(toks) - n + 1):
        gram = tuple(t.word.lower() for t in toks[i:i + n])
        if all(w in stop for w in gram):
            continue
        counts[gram] += 1
        first.setdefault(gram, toks[i])
    issues = []
    for gram, c in counts.most_common():
        if c >= min_count:
            t = first[gram]
            phrase = " ".join(gram)
            issues.append(Issue("repeated_phrase", t.line, t.column, phrase,
                                f"Словосполучення «{phrase}» повторюється {c} разів", "info",
                                "Перефразуйте"))
    return issues
