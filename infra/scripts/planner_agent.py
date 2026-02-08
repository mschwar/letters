from __future__ import annotations

import argparse
import os
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT_DIR))

from infra.scripts.task_analyzer import analyze_plan, build_parallel_groups, infer_dependencies, parse_plan  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Planner Agent with Task Analyzer output.")
    parser.add_argument(
        "--plan",
        type=Path,
        default=Path("IMPLEMENTATION_PLAN.md"),
        help="Path to IMPLEMENTATION_PLAN.md",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Optional path to write analysis markdown.",
    )
    parser.add_argument(
        "--agents",
        type=int,
        default=None,
        help="Number of agents for batch assignment (default: CPU count).",
    )
    parser.add_argument(
        "--no-mermaid",
        action="store_true",
        help="Disable Mermaid graph output.",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Execute a parallel simulation per group using multiprocessing.",
    )
    return parser.parse_args()


def run_task(label: str) -> str:
    return f"completed: {label}"


def execute_parallel(groups: list[list[str]], max_workers: int) -> list[str]:
    results: list[str] = []
    for group in groups:
        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(run_task, label): label for label in group}
            for future in as_completed(futures):
                results.append(future.result())
    return results


def main() -> None:
    args = parse_args()
    agent_count = args.agents or (os.cpu_count() or 1)
    include_mermaid = not args.no_mermaid

    analysis = analyze_plan(args.plan, agent_count=agent_count, include_mermaid=include_mermaid)
    if args.output:
        args.output.write_text(analysis, encoding="utf-8")
    else:
        print(analysis)

    if args.execute:
        markdown = args.plan.read_text(encoding="utf-8")
        tasks = parse_plan(markdown)
        result = infer_dependencies(tasks)
        groups = build_parallel_groups(result.tasks, result.dependencies)
        labels = [[task.display for task in group] for group in groups]
        output = execute_parallel(labels, max_workers=agent_count)
        for line in output:
            print(line)


if __name__ == "__main__":
    main()
