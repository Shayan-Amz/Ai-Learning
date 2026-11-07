from pathlib import Path

import pytest

from local_research_agent.evaluate import DEFAULT_DATASET, evaluate_retrieval, main


def test_sample_retrieval_evaluation_meets_expected_quality_floor():
    knowledge_dir = Path(__file__).resolve().parents[1] / "local_research_agent" / "knowledge"

    metrics = evaluate_retrieval(knowledge_dir, DEFAULT_DATASET, k=5)

    assert metrics["cases"] == 6
    assert metrics["hit_at_5"] >= 0.83
    assert metrics["mrr"] >= 0.65


def test_retrieval_evaluation_rejects_invalid_k(tmp_path: Path):
    dataset = tmp_path / "eval.json"
    dataset.write_text('[{"query":"test","relevant_files":["note.md"]}]', encoding="utf-8")
    with pytest.raises(ValueError, match="k must be between"):
        evaluate_retrieval(tmp_path, dataset, k=6)


def test_retrieval_evaluation_rejects_malformed_dataset(tmp_path: Path):
    dataset = tmp_path / "eval.json"
    dataset.write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="non-empty JSON list"):
        evaluate_retrieval(tmp_path, dataset)


def test_evaluation_cli_prints_retrieval_metrics(monkeypatch, capsys):
    monkeypatch.setattr(
        "sys.argv",
        ["evaluate", "--knowledge-dir", str(Path(__file__).resolve().parents[1] / "local_research_agent" / "knowledge"), "--k", "3"],
    )

    main()

    output = capsys.readouterr().out
    assert "Cases: 6" in output
    assert "Hit@3:" in output
    assert "MRR:" in output
