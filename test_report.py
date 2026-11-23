import json

from textsentinel.report import (analyze, compute_score, recommend, render_json,
                                 render_markdown, render_text, summarize)


def test_clean_text_scores_100():
    report = analyze("Це гарний текст. Він чистий.")
    assert report.issues == [] and report.score == 100


def test_dirty_text_lowers_score():
    report = analyze("Привіт ,  світе")
    assert report.score < 100
    assert report.summary["total"] >= 2


def test_summarize_and_recommend():
    report = analyze("Привіт ,  світе")
    assert "space_before_punct" in summarize(report.issues)["by_rule"]
    assert "1" in recommend("double_space", 1)
    assert 0 <= compute_score(report) <= 100


def test_renderers():
    report = analyze("Привіт ,  світе")
    assert "Оцінка якості" in render_text(report, color=False)
    assert render_markdown(report).startswith("# Звіт")
    assert json.loads(render_json(report))["score"] == report.score
