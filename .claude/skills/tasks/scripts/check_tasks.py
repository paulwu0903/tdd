# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "pyyaml>=6,<7",
# ]
# ///
"""Check a tasks.md against its test-plan.md: TDD step markers, phase structure, card coverage and contract references.

Usage:
    uv run scripts/check_tasks.py --tasks <tasks.md> --feature-dir <specs/NNN-name>
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


_require("yaml")

import yaml  # noqa: E402

_TASK_LINE = re.compile(r"^- \[ \] T(\d{3}) (?P<p>\[P\] )?(?:\[US(?P<us>\d+)\] )?(?P<rest>.*)$")
_MARKER = re.compile(r"^`(環境|/tdd 紅燈|/tdd 綠燈|/tdd 重構)` (.*)$")
_PATHS = r"`[^`]+`(?:、`[^`]+`)*"
_RED = re.compile(rf"^撰寫 (SL-\d{{3}}) 的測試於 {_PATHS}$")
_GREEN = re.compile(rf"^實作 (SL-\d{{3}}) 的行為於 {_PATHS}$")
_REFACTOR = re.compile(rf"^整理(?: User Story (\d+)|全域 NFR) 的程式碼於 {_PATHS}$")
_ENV_PATHS = re.compile(rf"於 {_PATHS}$")
_PHASE = re.compile(r"^## Phase (\d+): (.+)$")
_US_PHASE = re.compile(r"^User Story (\d+) - .+ \(P\d+\)$")
_CHECKPOINT = re.compile(r"^\*\*Checkpoint\*\*:")
_CONTRACT_LINE = re.compile(r"^    - `([^`]+)` -> (.+)$")
_PART = re.compile(r"`([^`]+)`")
_VERSION = re.compile(r"\d+\.\d+\.\d+")
_REQ_ID = re.compile(r"^(FR|NFR|SC)-\d+$")
_RESEARCH_SECTION = re.compile(r"^(R\d+\. [^›]+?)(?: › .+)?$")
_TABLE_COLUMN = re.compile(r"^Table (\w+)\.(\w+)$")
_TABLE = re.compile(r"^Table (\w+)$")
_SCHEMA = re.compile(r"^schemas\.(\w+)$")
_BACKTICK_SPAN = re.compile(r"`[^`]*`")
_DOC_ONLY_LINE = re.compile(r"^    - `([^`]+)`$")
_INPUT_DOCS_LINE = re.compile(r"^\*\*Input Documents\*\*:(.*)$")

# test-plan.md structure
_TP_SECTION = re.compile(r"^## (.+)$")
_TP_US_SECTION = re.compile(r"^User Story (\d+)(?: - .+)?$")
_TP_CARD = re.compile(r"^### (SL-\d{3}) - ")
_TP_TYPE = re.compile(r"^- \*\*案例類型\*\*: (.+)$")
_TP_FIXTURE = re.compile(r"^\| ([A-Z]+-FX-[A-Z0-9-]+) \|")
_FIXTURE_ID = re.compile(r"^[A-Z]+-FX-[A-Z0-9-]+$")
_SLICE, _REGRESSION, _JOURNEY, _NFR = "TDD Slice", "防回歸（預期不先紅）", "旅程（預期不先紅）", "NFR 量測"
_GREEN_TYPES = (_SLICE, _NFR)
_CARD_TYPES = (_SLICE, _REGRESSION, _JOURNEY, _NFR)
# Phase kinds in their required order.
_RANK = {"setup": 0, "us": 1, "nfr": 2, "gates": 3}


def _parse_input_documents(text: str) -> list[str]:
    # Read the Input Documents list from the file header; entries ending with "/" are directory prefixes.
    for line in text.splitlines():
        match = _INPUT_DOCS_LINE.match(line)
        if match:
            return _PART.findall(match.group(1))
    return []


def _parse_test_plan(text: str) -> dict:
    # Collect cards (section key and case type), fixture ids and second-level section names of test-plan.md.
    cards: dict[str, dict] = {}
    fixtures: set[str] = set()
    sections: set[str] = set()
    section_key = None
    current = None
    for line in text.splitlines():
        head = _TP_SECTION.match(line)
        if head:
            name = head.group(1).strip()
            us = _TP_US_SECTION.match(name)
            if us:
                section_key = ("us", int(us.group(1)))
                sections.add(f"User Story {us.group(1)}")
            elif name == "全域 NFR":
                section_key = ("nfr", None)
                sections.add(name)
            elif name == "跨故事旅程":
                section_key = ("journey", None)
                sections.add(name)
            else:
                section_key = None
            current = None
            continue
        card = _TP_CARD.match(line)
        if card:
            current = card.group(1)
            cards[current] = {"section": section_key, "type": None}
            continue
        kind = _TP_TYPE.match(line)
        if kind and current:
            cards[current]["type"] = kind.group(1).strip()
            continue
        fixture = _TP_FIXTURE.match(line)
        if fixture:
            fixtures.add(fixture.group(1))
    return {"cards": cards, "fixtures": fixtures, "sections": sections}


def _classify_phase(title: str) -> tuple[str | None, int | None]:
    # Map a phase title to its kind; unknown titles return (None, None).
    if title == "Setup":
        return "setup", None
    us = _US_PHASE.match(title)
    if us:
        return "us", int(us.group(1))
    if title == "全域 NFR":
        return "nfr", None
    if title == "Acceptance Gates":
        return "gates", None
    return None, None


def _parse_tasks(text: str) -> tuple[list[dict], list[dict]]:
    # Split tasks.md into phases and tasks; each task keeps its phase, marker, sentence, contract lines and Why text.
    tasks: list[dict] = []
    phases: list[dict] = []
    section = None
    for line in text.splitlines():
        phase = _PHASE.match(line)
        if phase:
            kind, story = _classify_phase(phase.group(2).strip())
            phases.append({"number": int(phase.group(1)), "title": phase.group(2).strip(),
                           "kind": kind, "story": story, "tasks": [], "checkpoint": False})
            section = None
            continue
        if phases and _CHECKPOINT.match(line):
            phases[-1]["checkpoint"] = True
        match = _TASK_LINE.match(line)
        if match:
            task = {"id": int(match.group(1)), "parallel": bool(match.group("p")),
                    "us": int(match.group("us")) if match.group("us") else None,
                    "rest": match.group("rest"), "phase": phases[-1] if phases else None,
                    "sections": {}, "lines": {}}
            tasks.append(task)
            if phases:
                phases[-1]["tasks"].append(task)
            section = None
            continue
        if not tasks or not line.startswith("  "):
            section = None
            continue
        stripped = line.strip()
        if stripped in ("- Must Read:", "- Optional:"):
            section = stripped[2:-1]
            tasks[-1]["sections"][section] = True
            tasks[-1]["lines"].setdefault(section, [])
        elif stripped.startswith("- Why:"):
            tasks[-1]["sections"]["Why"] = True
            tasks[-1]["why"] = stripped[len("- Why:"):].strip()
            section = None
        elif section and line.startswith("    - "):
            tasks[-1]["lines"][section].append(line)
    return tasks, phases


class _Docs:
    # Lazily load the headings and keys of each input document that a contract may cite.
    def __init__(self, feature_dir: Path) -> None:
        self.feature_dir = feature_dir
        self._cache: dict[str, object] = {}

    def text(self, rel: str) -> str | None:
        path = self.feature_dir / rel
        if rel not in self._cache:
            self._cache[rel] = path.read_text(encoding="utf-8") if path.is_file() else None
        return self._cache[rel]  # type: ignore[return-value]

    def headings(self, rel: str, levels: tuple[str, ...]) -> set[str] | None:
        text = self.text(rel)
        if text is None:
            return None
        found = set()
        for line in text.splitlines():
            for prefix in levels:
                if line.startswith(prefix):
                    found.add(line[len(prefix):].strip())
        return found

    def dbml_tables(self) -> dict[str, set[str]] | None:
        text = self.text("analysis/schema.dbml")
        if text is None:
            return None
        tables: dict[str, set[str]] = {}
        current = None
        for line in text.splitlines():
            head = re.match(r"^Table (\w+)\s*\{", line)
            if head:
                current = head.group(1)
                tables[current] = set()
                continue
            if current is None:
                continue
            if line.startswith("}"):
                current = None
                continue
            column = re.match(r"^  (\w+) ", line)
            if column and not line.startswith(("  indexes", "  checks", "  Note")):
                tables[current].add(column.group(1))
        return tables

    def openapi(self) -> tuple[set[str], set[str]] | None:
        text = self.text("analysis/openapi.yaml")
        if text is None:
            return None
        data = yaml.safe_load(text) or {}
        paths = set((data.get("paths") or {}).keys())
        schemas = set(((data.get("components") or {}).get("schemas") or {}).keys())
        return paths, schemas


def _check_part(doc: str, part: str, docs: _Docs, plan: dict) -> str | None:
    # Return a reason when the cited part cannot be found in the input document; None when found or unchecked.
    if doc.endswith("test-plan.md"):
        if part.startswith("SL-"):
            return None if part in plan["cards"] else f"test-plan.md 沒有案例卡 {part}"
        if _FIXTURE_ID.match(part):
            return None if part in plan["fixtures"] else f"test-plan.md 沒有 Fixture {part}"
        if part in plan["sections"]:
            return None
        return f"test-plan.md 沒有段落或識別碼 {part}"
    if doc.endswith("spec.md"):
        if _REQ_ID.match(part):
            text = docs.text("spec.md")
            if text is None:
                return "spec.md 不存在"
            if part not in text:
                return f"spec.md 找不到 {part}"
        return None
    if doc.endswith("research.md"):
        match = _RESEARCH_SECTION.match(part)
        if match:
            headings = docs.headings("research.md", ("## ",))
            if headings is None:
                return "research.md 不存在"
            if match.group(1).strip() not in headings:
                return f"research.md 沒有 ## {match.group(1).strip()}"
        return None
    if doc.endswith("schema.dbml"):
        tables = docs.dbml_tables()
        column = _TABLE_COLUMN.match(part)
        table = _TABLE.match(part)
        if column or table:
            if tables is None:
                return "analysis/schema.dbml 不存在"
            name = (column or table).group(1)
            if name not in tables:
                return f"schema.dbml 沒有 Table {name}"
            if column and column.group(2) not in tables[name]:
                return f"schema.dbml 的 Table {name} 沒有欄位 {column.group(2)}"
        return None
    if doc.endswith("openapi.yaml"):
        schema = _SCHEMA.match(part)
        if part.startswith("/") or schema:
            loaded = docs.openapi()
            if loaded is None:
                return "analysis/openapi.yaml 不存在"
            paths, schemas = loaded
            if part.startswith("/") and part not in paths:
                return f"openapi.yaml 的 paths 沒有 {part}"
            if schema and schema.group(1) not in schemas:
                return f"openapi.yaml 的 components.schemas 沒有 {schema.group(1)}"
        return None
    if doc.endswith("frontend.md"):
        headings = docs.headings("analysis/frontend.md", ("## ", "### "))
        if headings is None:
            return "analysis/frontend.md 不存在"
        section = part.split(" › ")[0].strip()
        if section not in headings:
            return f"frontend.md 沒有章節 {section}"
        return None
    return None


def _doc_allowed(doc: str, input_docs: list[str]) -> bool:
    # A cited document must be one of the Input Documents; a trailing "/" entry matches by prefix.
    return any(doc == entry or (entry.endswith("/") and doc.startswith(entry)) for entry in input_docs)


def _check_contracts(tasks: list[dict], docs: _Docs, plan: dict, input_docs: list[str]) -> list[str]:
    # Contract completeness, contract-line format, Why wording, Input Documents scope and reference existence.
    violations: list[str] = []
    for index, task in enumerate(tasks, start=1):
        tid = f"T{task['id']:03d}"
        if task["id"] != index:
            violations.append(f"{tid}: 編號不連續，預期 T{index:03d}")
        for label in ("Must Read", "Optional", "Why"):
            if label not in task["sections"]:
                violations.append(f"{tid}: 缺少 {label}")
        for label in ("Must Read", "Optional"):
            for line in task["lines"].get(label, []):
                outside = _BACKTICK_SPAN.sub("", line)
                if "（" in outside:
                    violations.append(f"{tid}: {label} 契約行含括號說明：{line.strip()}")
                if _VERSION.search(outside):
                    violations.append(f"{tid}: {label} 契約行含版本號：{line.strip()}")
                match = _CONTRACT_LINE.match(line) or _DOC_ONLY_LINE.match(line)
                if match and input_docs and not _doc_allowed(match.group(1), input_docs):
                    violations.append(f"{tid}: {label} `{match.group(1)}` 不在 Input Documents 內")
        why = task.get("why")
        if why is not None:
            if "`" in why:
                violations.append(f"{tid}: Why 含程式識別碼：{why}")
            # A semicolon joins clauses of one sentence; only a second full stop starts another sentence.
            if why.count("。") >= 2 or (why.count("。") == 1 and not why.endswith("。")):
                violations.append(f"{tid}: Why 超過一句：{why}")
        for line in task["lines"].get("Must Read", []):
            match = _CONTRACT_LINE.match(line)
            if not match:
                continue
            doc, rest = match.group(1), match.group(2)
            for part in _PART.findall(rest):
                reason = _check_part(doc, part, docs, plan)
                if reason:
                    violations.append(f"{tid}: Must Read `{doc}` -> `{part}`：{reason}")
    return violations


def _test_plan_parts(task: dict) -> list[str]:
    # Parts the task's Must Read cites from test-plan.md.
    parts: list[str] = []
    for line in task["lines"].get("Must Read", []):
        match = _CONTRACT_LINE.match(line)
        if match and match.group(1).endswith("test-plan.md"):
            parts.extend(_PART.findall(match.group(2)))
    return parts


def _classify_task(task: dict, tid: str, violations: list[str]) -> None:
    # Resolve the TDD step marker and the fixed sentence pattern of the task line.
    task["step"] = task["card"] = task["refactor_of"] = None
    marker = _MARKER.match(task["rest"])
    if not marker:
        violations.append(f"{tid}: 缺少步驟標記，任務描述須以 `環境`、`/tdd 紅燈`、`/tdd 綠燈` 或 `/tdd 重構` 開頭")
        return
    step, sentence = marker.group(1), marker.group(2)
    task["step"] = step
    if step == "/tdd 紅燈":
        match = _RED.match(sentence)
        if not match:
            violations.append(f"{tid}: 紅燈句型須為「撰寫 SL-nnn 的測試於 `路徑`」：{sentence}")
            return
        task["card"] = match.group(1)
    elif step == "/tdd 綠燈":
        match = _GREEN.match(sentence)
        if not match:
            violations.append(f"{tid}: 綠燈句型須為「實作 SL-nnn 的行為於 `路徑`」：{sentence}")
            return
        task["card"] = match.group(1)
    elif step == "/tdd 重構":
        match = _REFACTOR.match(sentence)
        if not match:
            violations.append(f"{tid}: 重構句型須為「整理 User Story n 的程式碼於 `路徑`」或「整理全域 NFR 的程式碼於 `路徑`」：{sentence}")
            return
        task["refactor_of"] = ("us", int(match.group(1))) if match.group(1) else ("nfr", None)
    elif "於 `" in sentence and not _ENV_PATHS.search(sentence):
        violations.append(f"{tid}: 環境任務的路徑須以「於 `路徑`」收尾、多個路徑以「、」分隔：{sentence}")


def _check_phases(phases: list[dict], violations: list[str]) -> None:
    # Phase numbering, order Setup -> User Story n... -> 全域 NFR -> Acceptance Gates, and Checkpoint placement.
    last_rank, last_story, seen = -1, 0, set()
    for index, phase in enumerate(phases, start=1):
        label = f"Phase {phase['number']}"
        if phase["number"] != index:
            violations.append(f"{label}: Phase 編號不連續，預期 Phase {index}")
        kind = phase["kind"]
        if kind is None:
            violations.append(f"{label}: 標題「{phase['title']}」不是 Setup、User Story n - 標題 (Pn)、全域 NFR 或 Acceptance Gates")
            continue
        rank = _RANK[kind]
        if rank < last_rank or (kind != "us" and kind in seen):
            violations.append(f"{label}: Phase 順序須為 Setup → 各 User Story → 全域 NFR → Acceptance Gates，且 Setup、全域 NFR、Acceptance Gates 各至多一個")
        if kind == "us":
            if rank == last_rank and phase["story"] <= last_story:
                violations.append(f"{label}: User Story Phase 須依故事編號遞增排列")
            last_story = phase["story"]
        seen.add(kind)
        last_rank = max(last_rank, rank)
        is_last = index == len(phases)
        if is_last and phase["checkpoint"]:
            violations.append(f"{label}: 最後一個 Phase 不寫 Checkpoint")
        if not is_last and not phase["checkpoint"]:
            violations.append(f"{label}: 缺少 Checkpoint")


def _check_phase_tasks(phases: list[dict], violations: list[str]) -> None:
    # Which steps each phase may hold, [US] labels, [P] scope and the closing refactor task.
    for phase in phases:
        kind, story = phase["kind"], phase["story"]
        label = f"Phase {phase['number']}"
        for task in phase["tasks"]:
            tid = f"T{task['id']:03d}"
            step = task["step"]
            if task["parallel"] and step != "環境":
                violations.append(f"{tid}: [P] 只用於 `環境` 任務")
            if kind == "us" and task["us"] != story:
                violations.append(f"{tid}: User Story {story} Phase 的任務須標 [US{story}]")
            if kind != "us" and task["us"] is not None:
                violations.append(f"{tid}: 只有 User Story Phase 的任務標 [US]")
            if (step == "環境") != (kind == "setup") and step is not None and kind is not None:
                violations.append(f"{tid}: `環境` 任務只放 Setup，Setup 也只放 `環境` 任務")
            if kind == "gates" and step not in (None, "/tdd 紅燈"):
                violations.append(f"{tid}: Acceptance Gates 只放旅程卡的紅燈任務")
            if step == "/tdd 重構":
                expected = (kind, story) if kind in ("us", "nfr") else None
                if task["refactor_of"] is not None and task["refactor_of"] != expected:
                    violations.append(f"{tid}: 重構任務整理的範圍須是所在的 {phase['title']} Phase，且只放在 User Story 與全域 NFR Phase")
        if kind in ("us", "nfr"):
            refactors = [t for t in phase["tasks"] if t["step"] == "/tdd 重構"]
            if len(refactors) != 1 or not phase["tasks"] or phase["tasks"][-1]["step"] != "/tdd 重構":
                violations.append(f"{label}: 須以恰好一個 `/tdd 重構` 任務收尾")


def _expected_phase(card: dict) -> tuple[str, int | None] | None:
    # Journey cards go to Acceptance Gates; other cards go to the phase of their test-plan section.
    section = card["section"]
    if card["type"] == _JOURNEY:
        return ("gates", None)
    if section is None or section[0] == "journey":
        return None
    return section


def _check_cards(tasks: list[dict], plan: dict, violations: list[str]) -> None:
    # Every card has one red task; TDD Slice and NFR cards also one later green task; cards sit in the right phase.
    reds: dict[str, list[dict]] = {}
    greens: dict[str, list[dict]] = {}
    for task in tasks:
        tid = f"T{task['id']:03d}"
        card_id = task["card"]
        if card_id is None:
            continue
        card = plan["cards"].get(card_id)
        if card is None:
            violations.append(f"{tid}: test-plan.md 沒有案例卡 {card_id}")
            continue
        (reds if task["step"] == "/tdd 紅燈" else greens).setdefault(card_id, []).append(task)
        expected = _expected_phase(card)
        phase = task["phase"]
        if phase is not None and expected is not None and (phase["kind"], phase["story"]) != expected:
            where = "Acceptance Gates" if expected[0] == "gates" else ("全域 NFR" if expected[0] == "nfr" else f"User Story {expected[1]}")
            violations.append(f"{tid}: {card_id} 須放在 {where} Phase")
        parts = _test_plan_parts(task)
        if card_id not in parts:
            violations.append(f"{tid}: Must Read 須含 `test-plan.md` -> `{card_id}`")
        if task["step"] == "/tdd 紅燈" and not any(_FIXTURE_ID.match(p) for p in parts):
            violations.append(f"{tid}: 紅燈 Must Read 須含 {card_id} 用到的 Fixture")
    for card_id, card in plan["cards"].items():
        if card["type"] not in _CARD_TYPES:
            violations.append(f"{card_id}: test-plan.md 的案例類型無法辨識：{card['type']}")
            continue
        red = reds.get(card_id, [])
        green = greens.get(card_id, [])
        if len(red) != 1:
            violations.append(f"{card_id}: 須恰好一個紅燈任務，現有 {len(red)} 個")
        if card["type"] in _GREEN_TYPES:
            if len(green) != 1:
                violations.append(f"{card_id}: {card['type']} 卡須恰好一個綠燈任務，現有 {len(green)} 個")
            elif red and green[0]["id"] < red[0]["id"]:
                violations.append(f"T{green[0]['id']:03d}: {card_id} 的綠燈任務須排在紅燈任務之後")
        elif green:
            violations.append(f"{card_id}: {card['type']} 卡不切綠燈任務")


def _check(tasks: list[dict], phases: list[dict], docs: _Docs, plan: dict, input_docs: list[str]) -> list[str]:
    violations = _check_contracts(tasks, docs, plan, input_docs)
    for task in tasks:
        _classify_task(task, f"T{task['id']:03d}", violations)
        if task["phase"] is None:
            violations.append(f"T{task['id']:03d}: 任務不在任何 Phase 底下")
    _check_phases(phases, violations)
    _check_phase_tasks(phases, violations)
    _check_cards(tasks, plan, violations)
    return violations


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Check a tasks.md against its test-plan.md: TDD step markers, phase structure, card coverage and contract references."
    )
    parser.add_argument("--tasks", required=True, help="Path to the tasks.md to check")
    parser.add_argument("--feature-dir", required=True, help="Feature directory holding spec.md, test-plan.md, research.md and analysis/")
    args = parser.parse_args()
    tasks_path = Path(args.tasks)
    feature_dir = Path(args.feature_dir)
    if not tasks_path.is_file():
        sys.stderr.write(f"error: '{tasks_path}' is not a file; pass the path to the generated tasks.md\n")
        return 2
    if not feature_dir.is_dir():
        sys.stderr.write(f"error: '{feature_dir}' is not a directory; pass the specs/<NNN>-<name> directory\n")
        return 2
    test_plan_path = feature_dir / "test-plan.md"
    if not test_plan_path.is_file():
        sys.stderr.write(f"error: '{test_plan_path}' not found; run /test-plan for this feature first\n")
        return 2
    plan = _parse_test_plan(test_plan_path.read_text(encoding="utf-8"))
    if not plan["cards"]:
        sys.stderr.write(f"error: no case cards like '### SL-001 - ...' found in '{test_plan_path}'\n")
        return 2
    text = tasks_path.read_text(encoding="utf-8")
    tasks, phases = _parse_tasks(text)
    if not tasks:
        sys.stderr.write(f"error: no task lines like '- [ ] T001 ...' found in '{tasks_path}'\n")
        return 2
    violations = _check(tasks, phases, _Docs(feature_dir), plan, _parse_input_documents(text))
    if not violations:
        sys.stdout.write("OK\n")
        return 0
    sys.stdout.write("\n".join(violations) + "\n")
    return 1


if __name__ == "__main__":
    sys.exit(main())
