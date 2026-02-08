from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

PHASE_RE = re.compile(r"^##\s+Phase\s+(\d+):\s*(.+)$")
TASK_RE = re.compile(r"^###\s+([0-9]+(?:\.[0-9]+)?)\s+(.+)$")
TASK_REF_RE = re.compile(r"\b(\d+\.\d+)\b")
PHASE_REF_RE = re.compile(r"\bPhase\s+(\d+)\b", re.IGNORECASE)
PHASE_BULLET_RE = re.compile(r"^-\s+Phase\s+(\d+):\s*(.+)$", re.IGNORECASE)

KEYWORDS = {
    "frontend": [
        "frontend",
        "next.js",
        "ui",
        "route",
        "layout",
        "theme",
        "component",
        "page",
        "nav",
    ],
    "backend": [
        "fastapi",
        "api",
        "endpoint",
        "router",
        "auth",
        "jwt",
        "security",
    ],
    "database": [
        "db",
        "database",
        "schema",
        "migration",
        "alembic",
        "sqlite",
        "fts",
        "seed",
    ],
    "pipeline": [
        "ingestion",
        "pipeline",
        "hash",
        "dedupe",
        "extract",
        "convert",
        "index",
        "link",
        "worker",
        "watchdog",
    ],
    "search": ["search", "fts", "query", "filter", "pagination"],
    "observability": ["observability", "dashboard", "audit", "logging", "error"],
    "backup": ["backup", "restore", "export", "snapshot"],
    "hardening": ["performance", "security checks", "hardening"],
}

API_DEP_WORDS = [
    "api",
    "endpoint",
    "auth",
    "search",
    "ingest",
    "runs",
    "settings",
    "document",
    "metadata",
    "review",
    "graph",
    "data",
    "db",
]


@dataclass(frozen=True)
class Phase:
    index: int
    title: str


@dataclass
class Task:
    task_id: str
    title: str
    phase: Phase | None
    text: str
    tags: set[str] = field(default_factory=set)

    @property
    def display(self) -> str:
        if self.phase:
            return f"{self.task_id} {self.title} (Phase {self.phase.index}: {self.phase.title})"
        return f"{self.task_id} {self.title}"

    @property
    def sort_key(self) -> tuple[int, str]:
        phase_index = self.phase.index if self.phase else 999
        return (phase_index, self.task_id)

    @property
    def node_id(self) -> str:
        clean = self.task_id.replace(".", "_")
        phase_part = f"p{self.phase.index}_" if self.phase else ""
        return f"t_{phase_part}{clean}"


@dataclass
class AnalysisResult:
    tasks: list[Task]
    dependencies: dict[str, set[str]]


def load_plan(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def parse_plan(markdown: str) -> list[Task]:
    tasks: list[Task] = []
    phase_bullets: list[Task] = []
    current_phase: Phase | None = None
    current_task: Task | None = None
    buffer: list[str] = []
    in_phase_list = False
    saw_task_heading = False

    def finalize_task() -> None:
        nonlocal current_task, buffer
        if not current_task:
            return
        current_task.text = " ".join(buffer).strip()
        tasks.append(current_task)
        current_task = None
        buffer = []

    lines = markdown.splitlines()
    for line in lines:
        phase_match = PHASE_RE.match(line)
        if phase_match:
            finalize_task()
            current_phase = Phase(index=int(phase_match.group(1)), title=phase_match.group(2).strip())
            continue

        task_match = TASK_RE.match(line)
        if task_match:
            saw_task_heading = True
            finalize_task()
            current_task = Task(
                task_id=task_match.group(1).strip(),
                title=task_match.group(2).strip(),
                phase=current_phase,
                text="",
            )
            continue

        if line.startswith("## ") and "phase" in line.lower():
            in_phase_list = True
        elif line.startswith("## ") and "phase" not in line.lower():
            in_phase_list = False

        if in_phase_list:
            bullet_match = PHASE_BULLET_RE.match(line.strip())
            if bullet_match:
                phase_index = int(bullet_match.group(1))
                title = bullet_match.group(2).strip()
                phase = Phase(index=phase_index, title=title)
                phase_bullets.append(Task(task_id=f"{phase_index}.0", title=title, phase=phase, text=""))
                continue

        if current_task:
            stripped = line.strip()
            if stripped.startswith("-"):
                buffer.append(stripped.lstrip("- ").strip())
            elif stripped:
                buffer.append(stripped)

    finalize_task()
    if saw_task_heading:
        return tasks
    return phase_bullets


def infer_tags(tasks: Iterable[Task]) -> None:
    for task in tasks:
        text = f"{task.title} {task.text}"
        if task.phase:
            text = f"{text} {task.phase.title}"
        text_lower = text.lower()
        for tag, words in KEYWORDS.items():
            if any(word in text_lower for word in words):
                task.tags.add(tag)
        if task.phase and "frontend" in task.phase.title.lower():
            task.tags.add("frontend")
        if "frontend" in task.tags and any(word in text_lower for word in API_DEP_WORDS):
            task.tags.add("needs_api")
        if "fts" in text_lower:
            task.tags.add("search")
        if "pipeline" in text_lower:
            task.tags.add("pipeline")
        if "backend" in text_lower:
            task.tags.add("backend")


def _match_phase_tasks(tasks: Iterable[Task], phase_index: int) -> set[str]:
    return {task.node_id for task in tasks if task.phase and task.phase.index == phase_index}


def infer_dependencies(tasks: list[Task]) -> AnalysisResult:
    infer_tags(tasks)
    dependencies: dict[str, set[str]] = {task.node_id: set() for task in tasks}

    task_by_id = {task.task_id: task for task in tasks}

    for task in tasks:
        text = f"{task.title} {task.text}"
        text_lower = text.lower()
        for ref in TASK_REF_RE.findall(text):
            if ref in task_by_id and task_by_id[ref].node_id != task.node_id:
                dependencies[task.node_id].add(task_by_id[ref].node_id)
        for phase_ref in PHASE_REF_RE.findall(text):
            phase_tasks = _match_phase_tasks(tasks, int(phase_ref))
            dependencies[task.node_id].update(phase_tasks)

        if "frontend" in task.tags and "needs_api" in task.tags:
            for other in tasks:
                if other.node_id == task.node_id:
                    continue
                if other.tags.intersection({"backend", "database", "pipeline", "search"}):
                    dependencies[task.node_id].add(other.node_id)

        if "search" in task.tags:
            for other in tasks:
                if other.node_id == task.node_id:
                    continue
                if other.tags.intersection({"database", "pipeline"}):
                    dependencies[task.node_id].add(other.node_id)

        if "observability" in task.tags:
            for other in tasks:
                if other.node_id == task.node_id:
                    continue
                if "backend" in other.tags:
                    dependencies[task.node_id].add(other.node_id)

        if "backup" in task.tags:
            for other in tasks:
                if other.node_id == task.node_id:
                    continue
                if "database" in other.tags:
                    dependencies[task.node_id].add(other.node_id)

        if "hardening" in task.tags:
            for other in tasks:
                if other.node_id == task.node_id:
                    continue
                if task.phase and other.phase and other.phase.index < task.phase.index:
                    dependencies[task.node_id].add(other.node_id)

        if "pipeline" in task.tags and "database" not in task.tags:
            for other in tasks:
                if other.node_id == task.node_id:
                    continue
                if "database" in other.tags:
                    dependencies[task.node_id].add(other.node_id)

        if "metadata" in text_lower:
            for other in tasks:
                if other.node_id == task.node_id:
                    continue
                if "database" in other.tags:
                    dependencies[task.node_id].add(other.node_id)

    return AnalysisResult(tasks=tasks, dependencies=dependencies)


def build_parallel_groups(tasks: list[Task], dependencies: dict[str, set[str]]) -> list[list[Task]]:
    tasks_by_id = {task.node_id: task for task in tasks}
    remaining = set(tasks_by_id.keys())
    indegree = {task_id: len(dependencies[task_id]) for task_id in tasks_by_id}
    dependents: dict[str, set[str]] = {task_id: set() for task_id in tasks_by_id}
    for task_id, deps in dependencies.items():
        for dep in deps:
            dependents[dep].add(task_id)

    groups: list[list[Task]] = []

    while remaining:
        ready = [task_id for task_id in remaining if indegree[task_id] == 0]
        if not ready:
            break
        ready_tasks = sorted((tasks_by_id[task_id] for task_id in ready), key=lambda t: t.sort_key)
        groups.append(ready_tasks)
        for task in ready:
            remaining.remove(task)
            for dep in dependents[task]:
                indegree[dep] = max(0, indegree[dep] - 1)

    if remaining:
        cycle_tasks = sorted((tasks_by_id[task_id] for task_id in remaining), key=lambda t: t.sort_key)
        groups.append(cycle_tasks)

    return groups


def assign_agents(groups: list[list[Task]], agent_count: int) -> list[list[list[Task]]]:
    assignments: list[list[list[Task]]] = []
    agent_count = max(1, agent_count)
    for group in groups:
        buckets = [[] for _ in range(agent_count)]
        for idx, task in enumerate(group):
            buckets[idx % agent_count].append(task)
        assignments.append(buckets)
    return assignments


def render_mermaid(tasks: list[Task], dependencies: dict[str, set[str]]) -> str:
    lines: list[str] = ["graph TD"]
    phases = {}
    for task in tasks:
        phase_key = f"Phase {task.phase.index}: {task.phase.title}" if task.phase else "Unphased"
        phases.setdefault(phase_key, []).append(task)

    for phase_key, phase_tasks in phases.items():
        lines.append(f"  subgraph \"{phase_key}\"")
        for task in phase_tasks:
            label = f"{task.task_id} {task.title}".replace("\"", "'")
            lines.append(f"    {task.node_id}[\"{label}\"]")
        lines.append("  end")

    for task_id, deps in dependencies.items():
        for dep in deps:
            lines.append(f"  {dep} --> {task_id}")

    return "\n".join(lines)


def render_markdown(result: AnalysisResult, agent_count: int | None = None, include_mermaid: bool = True) -> str:
    tasks = result.tasks
    deps = result.dependencies
    groups = build_parallel_groups(tasks, deps)
    lines: list[str] = []

    lines.append(f"Tasks Parsed: {len(tasks)}")
    lines.append("")
    lines.append("Parallel Groups (Topological Layers)")
    lines.append("")
    for idx, group in enumerate(groups, start=1):
        lines.append(f"Group {idx}:")
        for task in group:
            lines.append(f"- {task.display}")
        lines.append("")

    if agent_count:
        assignments = assign_agents(groups, agent_count)
        lines.append(f"Agent Batches (Agents: {agent_count})")
        lines.append("")
        for group_idx, buckets in enumerate(assignments, start=1):
            lines.append(f"Group {group_idx}:")
            for agent_idx, tasks_for_agent in enumerate(buckets, start=1):
                if not tasks_for_agent:
                    continue
                task_list = "; ".join(task.display for task in tasks_for_agent)
                lines.append(f"- Agent {agent_idx}: {task_list}")
            lines.append("")

    if include_mermaid:
        lines.append("Dependency Graph")
        lines.append("")
        lines.append("```mermaid")
        lines.append(render_mermaid(tasks, deps))
        lines.append("```")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def analyze_plan(plan_path: Path, agent_count: int | None = None, include_mermaid: bool = True) -> str:
    markdown = load_plan(plan_path)
    tasks = parse_plan(markdown)
    result = infer_dependencies(tasks)
    return render_markdown(result, agent_count=agent_count, include_mermaid=include_mermaid)


__all__ = [
    "AnalysisResult",
    "Task",
    "Phase",
    "analyze_plan",
    "parse_plan",
    "infer_dependencies",
    "build_parallel_groups",
    "assign_agents",
    "render_mermaid",
]
