---
name: implement
description: 在 /tasks 產出 tasks.md 之後，要依其 Phase、任務的 TDD 步驟與 Must Read / Optional / Why 契約逐任務實作程式碼、通過驗證並完成整個開發任務時，必須使用此 skill。
compatibility: Requires Python >=3.11 and uv
license: MIT
metadata:
  derived-from: github/spec-kit v1.2.2 templates/commands/implement.md (MIT, Copyright GitHub, Inc.)
  derived-from-url: https://github.com/github/spec-kit/blob/v1.2.2/templates/commands/implement.md
  attribution: see NOTICE.md
---

# SOP

## Phase 1 -- 確認輸入與環境
1. READ 讀取使用者指定的 `specs/<NNN>-<專案名>/tasks.md` 的檔首與 Phase 標題，以及使用者補充的程式碼根目錄與任務範圍；僅在 tasks.md 不存在時才交給 tasks skill 產出再繼續，已存在則直接使用、不重新產出；程式碼根目錄未指定時以 repository root 為準。
2. READ 讀取同目錄 `techstack.md` 的執行環境，確認本機具備所列的執行時版本與資料庫；缺少時自行安裝、啟動並建立測試資料庫，仍做不到則改採 research.md 已評估的替代方案並記入當責紀錄。

## Phase 2 -- 取得下一批任務
1. DELEGATE 以 uv run 執行 `${CLAUDE_SKILL_DIR}/scripts/next_batch.py --tasks <tasks.md 路徑> --spec <spec.md 路徑> [--range <任務範圍>]`，取得下一批可執行任務（彼此檔案不重疊的 [P] 任務，或單一任務）的全文、所在 Phase，以及該批完成後是否到達 Phase 末尾與其 Checkpoint 與對應使用者故事的 Independent Test；沒有未完成任務時進入 Phase 5。
2. DELEGATE 以 uv run 執行 constitution skill 的 `affected.py`（位於 `.claude/skills/constitution` 的 scripts 目錄）`--root .claude/constitution --repo <repository root> --file <任務列的檔案路徑> ...`，為批次中每個任務取得其檔案路徑適用的憲法檔清單。

## Phase 3 -- 實作
1. DELEGATE 為批次中的每個任務各開一個子代理平行執行，一個子代理只負責一個任務，只傳入該任務的全文（任務列與契約三段）、程式碼根目錄、`rules/參照-規範.md`、`rules/完成判準-規範.md`、`rules/執行順序-規範.md` 與 Phase 2 第 2 步取得的該任務憲法檔（與 `rules/` 衝突時以憲法為準），不傳 tasks.md 路徑；任務列帶 `/tdd <步驟>` 標記者，子代理以該步驟與任務全文呼叫 tdd skill 執行，其餘任務由子代理依規範讀取契約、實作、自行驗證並回報；全程不向使用者提問，文件未規定或互相衝突之處由子代理依規範裁決並列入回報。

## Phase 4 -- 驗證與記錄
1. DELEGATE 在程式碼根目錄執行該批任務所屬工作區的型別檢查、lint 與單元 / 整合測試一鍵指令，自行確認通過；未通過即把錯誤輸出交回同一個子代理修正並重跑，修正滿 3 次仍失敗則另開一個乾淨子代理帶完整失敗紀錄重做 1 次，仍失敗即由協調者依專業判斷採取最符合使用者目標且能讓驗證通過的做法完成該任務，並把決策、理由、風險與建議的後續修正記入當責紀錄；不跳過、不終止、不向使用者提問。
2. DELEGATE 以 uv run 執行 constitution skill 的 `affected.py`（位於 `.claude/skills/constitution` 的 scripts 目錄）`--root .claude/constitution --repo <repository root> --file <該批新增或修改的檔案> ... --check`，取得憲法 script 驗證的違規與需逐條自檢的 Rule；違規與自檢不符依第 1 步的方式交回子代理修正並重跑。
3. DELEGATE 確認批內每個任務都已交回五項回報，缺任務或缺項即交回該子代理補完；全數齊備後以 uv run 執行 `${CLAUDE_SKILL_DIR}/scripts/mark_done.py --tasks <tasks.md 路徑> <任務編號 ...>`，把通過的任務標記為 [X]，script 因 TDD 前一步未完成而拒絕時先完成該前一步；標記後以 uv run 執行 `${CLAUDE_SKILL_DIR}/scripts/check_trace.py --test-plan <test-plan.md 路徑> --tasks <tasks.md 路徑> --src <原始碼目錄 ...> --tests <測試目錄 ...>`，確認已完成案例卡的編號都標在測試名稱與主要負責的 function 上，違規依第 1 步的方式交回子代理修正並重跑；進度與子代理回報的決策只寫入執行紀錄，批次之間不向使用者輸出摘要，直接回到下一步。
4. READ 確認本批已依序走完 Phase 2 第 1 步到本步的每一步，有遺漏即補做該步；該批到達 Phase 末尾時讀取該 Phase 的 Checkpoint 與 Phase 2 第 1 步取得的 Independent Test，逐項實際執行確認（能以測試執行的跑測試，其餘實際啟動並以瀏覽器操作），全部通過才回到 Phase 2 第 1 步；未通過視同該 Phase 最後一個序列任務失敗，依第 1 步處理；未到 Phase 末尾則直接回到 Phase 2 第 1 步。

## Phase 5 -- 完成回報
1. READ 讀取 tasks.md 確認全部任務已為 [X]，向使用者回報完成的 Phase 與任務數、最後一次全量驗證的結果（含 `check_trace.py` 不帶 `--tasks` 的全量檢查）、當責紀錄（每個阻塞的決策、理由、風險與建議的後續修正）、實作中發現需上游修正的文件不一致與自行裁決的衝突、任務路徑之外新增或修改的檔案、套用的憲法檔與被覆寫的內建 Rule，以及文件未規定而自行決定的事項。
