# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Mark the given task lines in a tasks.md as done ([ ] -> [X]); refuse to write when any id is missing, already done,
or skips a TDD step (green before its red, refactor before its phase's greens).

Usage:
    uv run scripts/mark_done.py --tasks <tasks.md> T001 [T002 ...]
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

_ID = re.compile(r"^T(\d{3})$")
_TASK = re.compile(r"^- \[( |X|x)\] T(\d{3}) ")
_PHASE = re.compile(r"^## Phase (\d+):")
_STEP = re.compile(r"`/tdd (紅燈|綠燈|重構)`")
_CARD = re.compile(r"\bSL-\d+\b")


def _skipped_steps(lines: list[str], wanted: dict[int, str]) -> list[str]:
    # A green needs every red of its SL cards done; a refactor needs every green of its phase done.
    # Tasks marked in the same call count as done.
    tasks = []
    phase = None
    for line in lines:
        m = _PHASE.match(line)
        if m:
            phase = int(m.group(1))
            continue
        m = _TASK.match(line)
        if m:
            step = _STEP.search(line)
            tasks.append({
                "id": int(m.group(2)),
                "done": m.group(1) != " " or int(m.group(2)) in wanted,
                "phase": phase,
                "step": step.group(1) if step else None,
                "cards": set(_CARD.findall(line)),
            })
    problems = []
    for task in tasks:
        if task["id"] not in wanted:
            continue
        if task["step"] == "綠燈":
            blockers = [t for t in tasks if t["step"] == "紅燈" and t["cards"] & task["cards"] and not t["done"]]
            need = "its red"
        elif task["step"] == "重構":
            blockers = [t for t in tasks if t["step"] == "綠燈" and t["phase"] == task["phase"] and not t["done"]]
            need = "every green of its phase"
        else:
            continue
        if blockers:
            pending = " ".join(f"T{t['id']:03d}" for t in blockers)
            problems.append(f"{wanted[task['id']]} needs {need} done first; pending: {pending}")
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description="Mark the given task lines in a tasks.md as done ([ ] -> [X]).")
    parser.add_argument("--tasks", required=True, help="Path to the tasks.md produced by the tasks skill")
    parser.add_argument("ids", nargs="+", help="Task ids to mark, like T001 T002")
    args = parser.parse_args()
    path = Path(args.tasks)
    if not path.is_file():
        sys.stderr.write(f"error: '{path}' is not a file; pass the path to an existing tasks.md\n")
        return 2
    wanted: dict[int, str] = {}
    for raw in args.ids:
        m = _ID.match(raw)
        if not m:
            sys.stderr.write(f"error: '{raw}' is not a task id like T001\n")
            return 2
        wanted[int(m.group(1))] = raw
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    state: dict[int, tuple[int, bool]] = {}
    for index, line in enumerate(lines):
        m = _TASK.match(line)
        if m:
            state[int(m.group(2))] = (index, m.group(1) != " ")
    problems = []
    for tid, raw in wanted.items():
        if tid not in state:
            problems.append(f"{raw} not found")
        elif state[tid][1]:
            problems.append(f"{raw} already done")
    problems.extend(_skipped_steps(lines, wanted))
    if problems:
        # Refuse the whole call so a typo never leaves the file half-updated.
        sys.stderr.write("error: " + "; ".join(problems) + "; nothing written\n")
        return 1
    for tid in wanted:
        index = state[tid][0]
        lines[index] = lines[index].replace("- [ ] ", "- [X] ", 1)
    path.write_text("".join(lines), encoding="utf-8")
    sys.stdout.write("marked: " + " ".join(wanted.values()) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
