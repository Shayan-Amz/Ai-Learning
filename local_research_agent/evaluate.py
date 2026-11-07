from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .core import ToolCall
from .tools import MAX_SEARCH_RESULTS, build_read_only_tools

DEFAULT_KNOWLEDGE_DIR = Path(__file__).with_name("knowledge")
DEFAULT_DATASET = Path(__file__).with_name("evaluation_set.json")


def evaluate_retrieval(
    knowledge_dir: Path,
    dataset_path: Path = DEFAULT_DATASET,
    k: int = 5,
) -> dict[str, float | int]:
    if k < 1 or k > MAX_SEARCH_RESULTS:
        raise ValueError(f"k must be between 1 and {MAX_SEARCH_RESULTS}")
    dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
    if not isinstance(dataset, list) or not dataset:
        raise ValueError("Evaluation dataset must be a non-empty JSON list.")

    tools = build_read_only_tools(knowledge_dir)
    reciprocal_ranks: list[float] = []
    hit_count = 0
    for index, case in enumerate(dataset, start=1):
        if not isinstance(case, dict):
            raise ValueError(f"Evaluation case {index} must be a JSON object.")
        query = case.get("query")
        relevant_files = case.get("relevant_files")
        if (
            not isinstance(query, str)
            or not query.strip()
            or not isinstance(relevant_files, list)
            or not all(isinstance(item, str) for item in relevant_files)
        ):
            raise ValueError(f"Evaluation case {index} needs a query and relevant_files list.")

        observation = tools.execute(ToolCall("search_documents", {"query": query}))
        if observation.error:
            raise RuntimeError(f"Evaluation search failed in case {index}: {observation.error}")
        results = observation.result if isinstance(observation.result, list) else []
        ranked_paths = [
            str(item["path"])
            for item in results[:k]
            if isinstance(item, dict) and isinstance(item.get("path"), str)
        ]
        first_relevant_rank = next(
            (rank for rank, path in enumerate(ranked_paths, start=1) if path in relevant_files),
            None,
        )
        if first_relevant_rank is None:
            reciprocal_ranks.append(0.0)
        else:
            hit_count += 1
            reciprocal_ranks.append(1.0 / first_relevant_rank)

    cases = len(reciprocal_ranks)
    return {
        "cases": cases,
        f"hit_at_{k}": hit_count / cases,
        "mrr": sum(reciprocal_ranks) / cases,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate local document retrieval.")
    parser.add_argument("--knowledge-dir", type=Path, default=DEFAULT_KNOWLEDGE_DIR)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--k", type=int, default=5)
    arguments = parser.parse_args()
    metrics: dict[str, Any] = evaluate_retrieval(
        arguments.knowledge_dir,
        arguments.dataset,
        arguments.k,
    )
    print("Local Research Agent — retrieval evaluation")
    print(f"Cases: {metrics['cases']}")
    print(f"Hit@{arguments.k}: {metrics[f'hit_at_{arguments.k}']:.1%}")
    print(f"MRR: {metrics['mrr']:.3f}")


if __name__ == "__main__":
    main()
