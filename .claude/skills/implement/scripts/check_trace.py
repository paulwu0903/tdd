# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Check that every test-plan case card is traceable to a test name and to the code that implements it.

Rules checked (each violation is printed as `<code> <location>: <message>`):
  T1  a card in test-plan.md has no test whose name carries its id (`it('SL-012 ...')`, `test_sl_012_...`);
      in a test-side file with no test calls (e.g. a coverage config) any mention of the id counts
  T2  a card has no annotation in source code: a comment carrying the id outside the file-top header block,
      normally placed right above the function / method / table / selector that is mainly responsible
  T3  an id mentioned in source or test files does not exist in test-plan.md
  T4  a file-top header block ("Test-plan cases ...") lists ids that differ from the ids annotated in that file

With --tasks, T1 and T2 apply only to cards whose every task line in tasks.md is done ([X]), so the check
can run after each /implement batch; T3 and T4 always apply.

Usage:
    uv run scripts/check_trace.py --test-plan <test-plan.md> --src <dir|file> [...] --tests <dir|file> [...]
                                  [--tasks <tasks.md>]
Exit code 0 when no violation, 1 otherwise.
"""
import argparse
import re
import sys
from pathlib import Path

CARD = re.compile(r"^#{2,4}\s+(SL-\d{3})\b", re.M)
ID = re.compile(r"\bSL-(\d{3})\b")
TEST_CALL = re.compile(r"\b(?:it|test|describe)(?:\.\w+)*\(\s*[`'\"]")
TEST_NAME = re.compile(r"\b(?:it|test|describe)(?:\.\w+)*\(\s*[`'\"][^`'\"\n]*?\bSL-(\d{3})\b")
PY_NAME = re.compile(r"\btest_sl_(\d{3})", re.I)
HEADER_MARK = "Test-plan cases"
CODE_EXT = {".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".py", ".sql", ".css", ".html", ".go", ".rs", ".java", ".kt"}
SKIP_DIRS = {"node_modules", "dist", "build", "coverage", ".git", "__pycache__", "test-results"}


def files(paths: list[str]) -> list[Path]:
    out: list[Path] = []
    for p in map(Path, paths):
        if p.is_file():
            out.append(p)
        elif p.is_dir():
            out += [f for f in sorted(p.rglob("*")) if f.is_file() and f.suffix in CODE_EXT
                    and not SKIP_DIRS.intersection(f.parts)]
    return out


def is_test_file(f: Path) -> bool:
    n = f.name
    return any(t in n for t in (".test.", ".spec.", ".bench.")) or n.startswith("test_") or "tests" in f.parts


def header_span(lines: list[str]) -> tuple[int, int]:
    """Return [start, end) of the file-top comment block containing HEADER_MARK, or (0, 0)."""
    i = 0
    while i < len(lines) and (lines[i].lower().startswith(("<!doctype", "#!")) or not lines[i].strip()):
        i += 1
    start = i
    while i < len(lines):
        s = lines[i].strip()
        if not s or not (s.startswith(("//", "/*", "*", "--", "<!--", "#", "-->")) or "Test-plan" in s
                         or ID.search(s)):
            break
        i += 1
    block = "\n".join(lines[start:i])
    return (start, i) if HEADER_MARK in block else (0, 0)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--test-plan", required=True)
    ap.add_argument("--src", nargs="+", required=True, help="source dirs/files (implementation, configs)")
    ap.add_argument("--tests", nargs="+", required=True, help="test dirs/files")
    ap.add_argument("--tasks", help="tasks.md; limit T1/T2 to cards whose tasks are all [X]")
    a = ap.parse_args()

    plan = Path(a.test_plan).read_text(encoding="utf-8")
    cards = list(dict.fromkeys(CARD.findall(plan)))
    known = set(cards)
    errors: list[str] = []

    tested: set[str] = set()
    test_files = files(a.tests)
    for f in test_files:
        text = f.read_text(encoding="utf-8")
        found = {f"SL-{n}" for n in TEST_NAME.findall(text)} | {f"SL-{n}" for n in PY_NAME.findall(text)}
        if not TEST_CALL.search(text) and not PY_NAME.search(text):
            found |= {f"SL-{n}" for n in ID.findall(text)}
        tested |= found
        for n in sorted(set(ID.findall(text)) | set(PY_NAME.findall(text))):
            if f"SL-{n}" not in known:
                errors.append(f"T3 {f}: SL-{n} is not a card in {a.test_plan}")

    annotated: set[str] = set()
    test_set = set(test_files)
    for f in files(a.src):
        if f in test_set or is_test_file(f):
            continue
        lines = f.read_text(encoding="utf-8").splitlines()
        hs, he = header_span(lines)
        head_ids = {f"SL-{n}" for n in ID.findall("\n".join(lines[hs:he]))}
        body_ids = {f"SL-{n}" for n in ID.findall("\n".join(lines[:hs] + lines[he:]))}
        annotated |= body_ids
        for i in sorted(head_ids | body_ids):
            if i not in known:
                errors.append(f"T3 {f}: {i} is not a card in {a.test_plan}")
        if he and head_ids != body_ids:
            if head_ids - body_ids:
                errors.append(f"T4 {f}: header lists {', '.join(sorted(head_ids - body_ids))} "
                              "but no function in the file is annotated with them")
            if body_ids - head_ids:
                errors.append(f"T4 {f}: annotated {', '.join(sorted(body_ids - head_ids))} "
                              "missing from the file-top header")

    due = cards
    if a.tasks:
        state: dict[str, bool] = {}
        for line in Path(a.tasks).read_text(encoding="utf-8").splitlines():
            m = re.match(r"^- \[( |X|x)\] T\d+", line)
            if not m:
                continue
            for c in set(ID.findall(line.split("於")[0])):
                c = f"SL-{c}"
                state[c] = state.get(c, True) and m.group(1) != " "
        due = [c for c in cards if state.get(c)]
    for c in due:
        if c not in tested:
            errors.append(f"T1 {c}: no test name carries this id")
        if c not in annotated:
            errors.append(f"T2 {c}: no source annotation outside file headers")

    for e in errors:
        print(e)
    print(f"cards={len(cards)} checked={len(due)} tested={len(tested & known)} annotated={len(annotated & known)} "
          f"violations={len(errors)}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
