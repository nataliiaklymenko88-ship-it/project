# textsentinel-ua

Простий CLI та бібліотека для пошуку типових проблем у тексті.

## Встановлення (для розробки)

    python -m venv .venv
    pip install -e ".[dev]"

## Використання

    textsentinel check text.txt
    textsentinel check text.txt --format md -o report.md
    textsentinel fix text.txt -o clean.txt

## Тести

    pytest --cov=textsentinel
