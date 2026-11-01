---
name: tasks
description: 在 /test-plan 產出 test-plan.md 之後，要依其案例卡把功能拆成對應 /tdd 紅燈、綠燈、重構步驟的任務清單並產出 tasks.md 時，必須使用此 skill。
compatibility: Requires Python >=3.11 and uv
license: MIT
metadata:
  derived-from: github/spec-kit v1.2.2 templates/commands/tasks.md, templates/tasks-template.md (MIT, Copyright GitHub, Inc.)
  derived-from-url: https://github.com/github/spec-kit/blob/v1.2.2/templates/commands/tasks.md
  attribution: see NOTICE.md
---

# SOP

## Phase 1 -- 切 Phase
1. READ 讀取使用者指定的 `specs/<NNN>-<專案名>/test-plan.md` 的段落與每張卡的案例類型，以及同目錄 spec.md 的使用者故事優先序，依 `rules/Phase結構-規範.md` 定出各 Phase。

## Phase 2 -- 切任務
1. READ 讀取同目錄 `plan.md` 的系統介面盤點與 Source Code 樹，依 `rules/TDD任務-規範.md` 逐卡切出紅燈、綠燈與重構任務，並定出每個任務的檔案路徑。
2. THINK 依第 1 步讀取的同一份規範比對 research.md、techstack.md 的測試工具與 repo 現況，定出 Setup 的環境任務。

## Phase 3 -- 寫入 tasks.md
1. DELEGATE 以 uv run 執行 constitution skill 的 `affected.py`（位於 `.claude/skills/constitution` 的 scripts 目錄）`--root .claude/constitution --repo <repository root> --file <spec.md 同目錄>/tasks.md`，取得適用於 tasks.md 的憲法檔清單。
2. READ 讀取同目錄的 `research.md`、`techstack.md` 與 `analysis/` 底下全部產出，依 `rules/任務列-規範.md`、`rules/契約-規範.md` 與第 1 步取得的憲法檔（與 `rules/` 衝突時以憲法為準）寫出各任務列與契約。
3. WRITE 複製 `templates/tasks.md` 並參照 `templates/tasks.example.md` 改寫填位符號，寫入同目錄的 `tasks.md`。

## Phase 4 -- 回檢
1. DELEGATE 以 uv run 執行 `${CLAUDE_SKILL_DIR}/scripts/check_tasks.py --tasks <tasks.md 路徑> --feature-dir <specs/<NNN>-<專案名>>`，取得格式、識別碼與案例卡對應的違規清單；有違規即修正後重跑。
2. DELEGATE 以 uv run 執行 constitution skill 的 `affected.py`（位於 `.claude/skills/constitution` 的 scripts 目錄）`--root .claude/constitution --repo <repository root> --file <tasks.md 路徑> --check`，取得憲法 script 驗證的違規與需逐條自檢的 Rule；有違規即修正後重跑，並逐條自檢列出的 Rule 並修正，完成後向使用者回報產出路徑、套用的憲法檔與被覆寫的內建 Rule，以及執行中發現需上游修正的文件不一致。
