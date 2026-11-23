"""Модуль 4: звіт, оцінка якості та рекомендації."""
from __future__ import annotations

import json
import os
import re
import sys
from collections import Counter
from dataclasses import asdict, dataclass, field

from . import punctuation, repetitions, whitespace
from .models import Issue

WEIGHTS = {"error": 3.0, "warning": 1.0, "info": 0.3}
_ORDER = {"error": 0, "warning": 1, "info": 2}
_COLORS = {"error": "\033[31m", "warning": "\033[33m", "info": "\033[36m"}
_RESET = "\033[0m"

RECOMMENDATIONS = {
    "double_space": "Подвійних пробілів: {count}. Залиште один пробіл між словами (або запустіть `fix`).",
    "trailing_space": "Пробілів у кінці рядків: {count}. Увімкніть автоприбирання в редакторі.",
    "whitespace_only_line": "Рядків лише з пробілами: {count}. Зробіть їх порожніми.",
    "empty_line_edge": "Зайві порожні рядки на краях тексту: {count}. Приберіть їх.",
    "excessive_newlines": "Надмірних серій порожніх рядків: {count}. Достатньо одного порожнього рядка.",
    "space_before_punct": "Пробілів перед розділовими знаками: {count}. Знак пишеться впритул до слова.",
    "missing_space_after": "Немає пробілу після знаків: {count}. Після коми, крапки тощо потрібен пробіл.",
    "repeated_punct": "Повторів розділових знаків: {count}. Залиште один знак (або «...»).",
    "unbalanced_bracket": "Проблем із дужками й лапками-«ялинками»: {count}. Перевірте парність.",
    "quote_style": "Прямих лапок: {count}. Використовуйте «ялинки».",
    "repeated_word": "Повторів слів поруч: {count}. Видаліть зайві.",
    "frequent_word": "Надто частих слів: {count}. Використайте синоніми.",
    "repeated_phrase": "Повторюваних словосполучень: {count}. Перефразуйте.",
}


@dataclass
class Report:
    issues: list[Issue]
    stats: dict
    score: int = 100
    summary: dict = field(default_factory=dict)


def compute_text_stats(text: str) -> dict:
    words = len(repetitions.tokenize(text))
    sentences = len(re.findall(r"[^.!?…]+[.!?…]+", text)) or (1 if words else 0)
    return {
        "words": words,
        "sentences": sentences,
        "lines": len(text.splitlines()),
        "avg_sentence_length": round(words / sentences, 1) if sentences else 0.0,
    }


def summarize(issues: list[Issue]) -> dict:
    return {
        "total": len(issues),
        "by_rule": dict(Counter(i.rule for i in issues)),
        "by_severity": dict(Counter(i.severity for i in issues)),
    }


def compute_score(report: Report) -> int:
    """100 мінус зважена кількість проблем у розрахунку на розмір тексту."""
    penalty = sum(WEIGHTS.get(i.severity, 1.0) for i in report.issues)
    size = max(report.stats.get("words", 0), 20)
    return max(0, round(100 - 100 * penalty / size))


def recommend(rule: str, count: int) -> str:
    template = RECOMMENDATIONS.get(rule, "Перегляньте знахідки правила «{rule}» ({count}).")
    return template.format(rule=rule, count=count)


def build_report(issues: list[Issue], text_stats: dict) -> Report:
    ordered = sorted(issues, key=lambda i: (i.line, i.column))
    report = Report(issues=ordered, stats=text_stats)
    report.summary = summarize(ordered)
    report.score = compute_score(report)
    return report


def analyze(text: str) -> Report:
    """Запускає всі перевірки та повертає готовий звіт."""
    issues: list[Issue] = []
    issues += whitespace.find_double_spaces(text)
    issues += whitespace.find_trailing_spaces(text)
    issues += whitespace.find_empty_lines(text)
    issues += whitespace.find_excessive_newlines(text)
    issues += punctuation.find_space_before_punct(text)
    issues += punctuation.find_missing_space_after(text)
    issues += punctuation.find_repeated_punct(text)
    issues += punctuation.find_unbalanced_brackets(text)
    issues += punctuation.check_quote_style(text)
    issues += repetitions.find_repeated_words(text)
    issues += repetitions.find_frequent_words(text)
    issues += repetitions.find_repeated_bigrams(text)
    return build_report(issues, compute_text_stats(text))


def _recommendations(report: Report) -> list[str]:
    by_rule = report.summary.get("by_rule", {})
    return [recommend(r, c) for r, c in sorted(by_rule.items(), key=lambda x: -x[1])]


def render_text(report: Report, color: bool | None = None) -> str:
    if color is None:
        color = sys.stdout.isatty() and "NO_COLOR" not in os.environ
    s, sev = report.stats, report.summary.get("by_severity", {})
    lines = [
        f"Оцінка якості: {report.score}/100",
        f"Слів: {s['words']}, речень: {s['sentences']}, рядків: {s['lines']}, "
        f"середня довжина речення: {s['avg_sentence_length']} слів",
        f"Знайдено проблем: {report.summary['total']} (помилок: {sev.get('error', 0)}, "
        f"попереджень: {sev.get('warning', 0)}, підказок: {sev.get('info', 0)})",
        "",
    ]
    for i in sorted(report.issues, key=lambda i: (i.line, i.column)):
        tag = f"{i.severity:<7}"
        if color:
            tag = f"{_COLORS.get(i.severity, '')}{tag}{_RESET}"
        sug = f" → {i.suggestion}" if i.suggestion else ""
        lines.append(f"[{i.line}:{i.column}] {tag} {i.rule}: {i.message} «{i.fragment}»{sug}")
    recs = _recommendations(report)
    if recs:
        lines += ["", "Рекомендації:"] + [f"  • {r}" for r in recs]
    return "\n".join(lines) + "\n"


def render_markdown(report: Report) -> str:
    s = report.stats
    esc = lambda x: str(x).replace("|", "\\|").replace("\n", " ")
    out = [
        "# Звіт textsentinel", "",
        f"**Оцінка якості:** {report.score}/100", "",
        "| Показник | Значення |", "|---|---|",
        f"| Слів | {s['words']} |", f"| Речень | {s['sentences']} |",
        f"| Рядків | {s['lines']} |",
        f"| Середня довжина речення | {s['avg_sentence_length']} |",
        f"| Проблем | {report.summary['total']} |", "",
        "## Знахідки", "",
        "| Рядок | Колонка | Правило | Серйозність | Опис | Пропозиція |",
        "|---|---|---|---|---|---|",
    ]
    for i in report.issues:
        out.append(f"| {i.line} | {i.column} | {i.rule} | {i.severity} | "
                   f"{esc(i.message)}: «{esc(i.fragment)}» | {esc(i.suggestion or '')} |")
    out += ["", "## Рекомендації", ""] + [f"- {r}" for r in _recommendations(report)]
    return "\n".join(out) + "\n"


def render_json(report: Report) -> str:
    return json.dumps({"score": report.score, "stats": report.stats,
                       "summary": report.summary,
                       "issues": [asdict(i) for i in report.issues]},
                      ensure_ascii=False, indent=2)
