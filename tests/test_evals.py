from pathlib import Path

from qwable_lab.evals import load_cases, score_text, summarize


def test_load_default_cases() -> None:
    cases = load_cases(Path("scenarios/default.jsonl"))
    assert len(cases) >= 5
    assert cases[0].id == "reasoning-01"


def test_score_text_keyword_checks() -> None:
    score = score_text(
        "The answer is 154 crates.",
        {"must_include": ["154"], "must_avoid": ["168"]},
    )
    assert score["ratio"] == 1.0
    assert score["missing"] == []
    assert score["violations"] == []


def test_summarize_empty() -> None:
    assert summarize([])["cases"] == 0
