# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Print the next executable batch of pending tasks from a tasks.md, with its Phase, Checkpoint and the
Independent Test of the phase's User Story taken from spec.md.

Usage:
    uv run scripts/next_batch.py --tasks <tasks.md> --spec <spec.md> [--range <T010-T030 | T010- | -T030 | T015 | phase:2 | phase:2-3>]
"""
import argparse
import re
import sys
import tomllib
from pathlib import Path

_PEP723 = r"(?m)^# /// (?P<type>[a-zA-Z0-9-]+)$\s(?P<content>(^#(| .*)$\s)+)^# ///$"


def _declared_dependencies() -> list[str]:
    # Read this file's own inline script metadata with the PEP 723 reference regex.
    src = Path(__file__).read_text(encoding="utf-8")
    block = next((m for m in re.finditer(_PEP723, src) if m.group("type") == "script"), None)
    if block is None:
        return []
    content = "".join(
        line[2:] if line.startswith("# ") else line[1:]
        for line in block.group("content").splitlines(keepends=True)
    )
    return tomllib.loads(content).get("dependencies", [])


def _require(*modules: str) -> None:
    # Fail fast with the exact remediation when a declared dependency is missing.
    missing = []
    for module in modules:
        try:
            __import__(module)
        except ImportError:
            missing.append(module)
    if not missing:
        return
    me = Path(__file__).resolve()
    deps = " ".join(f'"{d}"' for d in _declared_dependencies())
    sys.stderr.write(
        f"[{me.name}] missing module(s): {', '.join(missing)}\n"
        "Dependencies are declared in this file's '# /// script' block.\n"
        f"Preferred (uv manages the environment):  uv run {me}\n"
        "  install uv on macOS/Linux:  curl -LsSf https://astral.sh/uv/install.sh | sh\n"
        "  install uv on Windows:      powershell -ExecutionPolicy ByPass -c \"irm https://astral.sh/uv/install.ps1 | iex\"\n"
        f"Fallback (current interpreter):          {sys.executable} -m pip install {deps}\n"
    )
    sys.exit(1)


_require()

_PHASE = re.compile(r"^## Phase (\d+): (.+)$")
_SECTION = re.compile(r"^### (.+)$")
_TASK = re.compile(r"^- \[( |X|x)\] T(\d{3}) (.*)$")
_CHECKPOINT = re.compile(r"^\*\*Checkpoint\*\*: (.+)$")
_PHASE_STORY = re.compile(r"\bUser Story (\d+)\b")
_STORY = re.compile(r"^### User Story (\d+)\b")
_INDEPENDENT = re.compile(r"^\*\*Independent Test\*\*: (.+)$")
_RANGE_IDS = re.compile(r"^(?:T(\d{3}))?-(?:T(\d{3}))?$")
_RANGE_ONE = re.compile(r"^T(\d{3})$")
_RANGE_PHASE = re.compile(r"^phase:(\d+)(?:-(\d+))?$")
_PATH = re.compile(r"`([^`]+)`")


def _parse(text: str) -> tuple[list[dict], list[dict]]:
    # Split tasks.md into phases (title, checkpoint) and tasks (id, done, parallel, section, block).
    phases: list[dict] = []
    tasks: list[dict] = []
    section = None
    for line in text.splitlines():
        m = _PHASE.match(line)
        if m:
            phases.append({"number": int(m.group(1)), "title": line[3:].strip(), "checkpoint": None})
            section = None
            continue
        if not phases:
            continue
        m = _CHECKPOINT.match(line)
        if m:
            phases[-1]["checkpoint"] = m.group(1).strip()
            continue
        m = _SECTION.match(line)
        if m:
            section = m.group(1).strip()
            continue
        m = _TASK.match(line)
        if m:
            tasks.append({
                "id": int(m.group(2)),
                "done": m.group(1) != " ",
                "parallel": "[P]" in m.group(3),
                "phase": phases[-1]["number"],
                "section": section,
                "block": [line],
            })
            continue
        if tasks and line.startswith("  ") and tasks[-1]["phase"] == phases[-1]["number"]:
            tasks[-1]["block"].append(line)
    return phases, tasks


def _independent_tests(text: str) -> dict[int, str]:
    # Map each '### User Story K' in spec.md to the '**Independent Test**:' line inside its section.
    tests: dict[int, str] = {}
    story = None
    for line in text.splitlines():
        m = _STORY.match(line)
        if m:
            story = int(m.group(1))
            continue
        if line.startswith("## ") or line.startswith("### "):
            story = None
            continue
        m = _INDEPENDENT.match(line)
        if m and story is not None and story not in tests:
            tests[story] = m.group(1).strip()
    return tests


def _in_range(task: dict, spec: str | None) -> bool:
    # A task is executable only inside the --range; no range means every task.
    if spec is None:
        return True
    m = _RANGE_ONE.match(spec)
    if m:
        return task["id"] == int(m.group(1))
    m = _RANGE_IDS.match(spec)
    if m:
        low = int(m.group(1)) if m.group(1) else 1
        high = int(m.group(2)) if m.group(2) else 999
        return low <= task["id"] <= high
    m = _RANGE_PHASE.match(spec)
    if m:
        low = int(m.group(1))
        high = int(m.group(2)) if m.group(2) else low
        return low <= task["phase"] <= high
    raise ValueError(spec)


def _paths(task: dict) -> set[str]:
    # File paths are the backticked tokens after the last ' 於 ' of the task line.
    line = task["block"][0]
    _, sep, tail = line.rpartition(" 於 ")
    return set(_PATH.findall(tail)) if sep else set()


def _batch(tasks: list[dict], spec: str | None) -> list[dict]:
    # First pending task in range; a [P] task also takes the following pending [P] tasks of the same section,
    # stopping before the first one whose file paths are unknown or overlap the batch, so batched tasks stay independent.
    pending = [t for t in tasks if not t["done"] and _in_range(t, spec)]
    if not pending:
        return []
    head = pending[0]
    if not head["parallel"]:
        return [head]
    batch = [head]
    taken = _paths(head)
    if not taken:
        return batch
    start = tasks.index(head) + 1
    for t in tasks[start:]:
        if t["section"] != head["section"] or t["phase"] != head["phase"]:
            break
        if not t["parallel"]:
            break
        if not t["done"] and _in_range(t, spec):
            paths = _paths(t)
            if not paths or paths & taken:
                break
            taken |= paths
            batch.append(t)
    return batch


def _summary(phases: list[dict], tasks: list[dict]) -> str:
    lines = []
    for phase in phases:
        own = [t for t in tasks if t["phase"] == phase["number"]]
        done = sum(1 for t in own if t["done"])
        lines.append(f"{phase['title']} — {done}/{len(own)}")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Print the next executable batch of pending tasks from a tasks.md.")
    parser.add_argument("--tasks", required=True, help="Path to the tasks.md produced by the tasks skill")
    parser.add_argument("--spec", required=True, help="Path to the spec.md whose User Stories carry the Independent Test")
    parser.add_argument("--range", dest="range_spec", help="Limit to T010-T030, T010-, -T030, T015, phase:2 or phase:2-3")
    args = parser.parse_args()
    path = Path(args.tasks)
    if not path.is_file():
        sys.stderr.write(f"error: '{path}' is not a file; pass the path to an existing tasks.md\n")
        return 2
    spec_path = Path(args.spec)
    if not spec_path.is_file():
        sys.stderr.write(f"error: '{spec_path}' is not a file; pass the path to the feature's spec.md\n")
        return 2
    phases, tasks = _parse(path.read_text(encoding="utf-8"))
    if not tasks:
        sys.stderr.write(f"error: no task lines like '- [ ] T001 ...' under '## Phase N:' headings in '{path}'\n")
        return 2
    try:
        batch = _batch(tasks, args.range_spec)
    except ValueError as exc:
        sys.stderr.write(f"error: --range '{exc}' is not T010-T030, T010-, -T030, T015, phase:2 or phase:2-3\n")
        return 2
    if not batch:
        any_pending = any(not t["done"] for t in tasks)
        sys.stdout.write(("RANGE_DONE" if any_pending else "ALL_DONE") + "\n" + _summary(phases, tasks) + "\n")
        return 0
    phase = next(p for p in phases if p["number"] == batch[0]["phase"])
    remaining = [t for t in tasks if t["phase"] == phase["number"] and not t["done"] and t not in batch]
    phase_end = not remaining
    out = [
        f"PHASE: {phase['title']}",
        f"SECTION: {batch[0]['section'] or '(none)'}",
        "TASKS: " + " ".join(f"T{t['id']:03d}" for t in batch),
        f"PHASE_END: {'yes' if phase_end else 'no'}",
    ]
    if phase_end:
        out.append(f"CHECKPOINT: {phase['checkpoint'] or '(none)'}")
        story = _PHASE_STORY.search(phase["title"])
        if story:
            number = int(story.group(1))
            independent = _independent_tests(spec_path.read_text(encoding="utf-8")).get(number)
            if independent is None:
                sys.stderr.write(
                    f"error: phase '{phase['title']}' names User Story {number}, but '{spec_path}' has no "
                    f"'**Independent Test**:' line under '### User Story {number} - ...'\n"
                )
                return 2
            out.append(f"INDEPENDENT_TEST: {independent}")
    out.append("---")
    for t in batch:
        out.extend(t["block"])
    sys.stdout.write("\n".join(out) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
