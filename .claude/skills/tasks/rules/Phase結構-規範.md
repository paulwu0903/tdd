# Rule 1 - Phase 固定序 [MUST]
- Phase 依序為 Setup、各 User Story、全域 NFR、Acceptance Gates，不設 Foundational。
- test-plan.md 的每個 `## User Story n` 段各一個 Phase，依 spec.md 的優先序（P1、P2 …）排列，不合併、不拆分；標題沿用 spec.md 的故事標題與優先序。
- test-plan.md 沒有 `## 全域 NFR` 段時省略全域 NFR Phase；沒有任何旅程卡時省略 Acceptance Gates Phase。

## Good Example
- Setup 在前，兩個 User Story 依 P1、P2 各占一個 Phase，全域 NFR 在故事之後，Acceptance Gates 固定在最後。

```
## Phase 1: Setup
## Phase 2: User Story 1 - 同房玩家在準備與對戰時即時傳送文字訊息 (P1)
## Phase 3: User Story 2 - 聊天紀錄延續：重新整理、換挑戰者與賽後檢視 (P2)
## Phase 4: 全域 NFR
## Phase 5: Acceptance Gates
```

## Bad Example
- 多了 Foundational，且 Acceptance Gates 排在全域 NFR 之前，旅程會在 NFR 調校改動程式之前就跑完。

```
## Phase 1: Setup
## Phase 2: Foundational
## Phase 3: User Story 1 - 同房玩家在準備與對戰時即時傳送文字訊息 (P1)
## Phase 4: User Story 2 - 聊天紀錄延續：重新整理、換挑戰者與賽後檢視 (P2)
## Phase 5: Acceptance Gates
## Phase 6: 全域 NFR
```

# Rule 2 - Checkpoint 寫可驗證的狀態 [MUST]
- 每個 Phase 末尾的 Checkpoint 寫做完後能實際操作或執行來確認的狀態，不寫「本 Phase 完成」這類無法驗證的句子。
- 最後一個 Phase 不寫 Checkpoint。

## Good Example
- 兩個指令能執行、NFR 專案能被單獨挑選，每一項都能實際確認。

```
**Checkpoint**: 後端測試指令與前端 E2E 指令都能執行且沒有失敗；NFR 量測專案能被單獨挑選執行
```

## Bad Example
- 只說完成，沒有任何可操作或可執行的確認方式。

```
**Checkpoint**: Setup 相關任務全部完成
```

# Rule 3 - User Story 的 Checkpoint 引用 Independent Test [MUST]
- User Story Phase 的 Checkpoint 以「可完成 `spec.md` 使用者故事 n 的 Independent Test」引用驗證流程，不在 tasks.md 重寫流程內容。
- 之後的 User Story Phase 一併引用先前故事的 Independent Test，表明先前故事仍可獨立驗證。

## Good Example
- 只引用 spec.md 的 Independent Test，第二個故事同時引用兩個故事。

```
**Checkpoint**: 本 phase 測試全綠；可完成 `spec.md` 使用者故事 1 的 Independent Test；MVP 可展示
**Checkpoint**: 本 phase 測試全綠；可分別完成 `spec.md` 使用者故事 1 與使用者故事 2 的 Independent Test
```

## Bad Example
- 把 spec.md 的 Independent Test 流程抄進 Checkpoint，spec 改了之後 tasks.md 不會跟著改。

```
**Checkpoint**: A 以配對碼 1234 開房、B 輸入 1234 加入；A 送出「哈囉」，B 的聊天室 2 秒內出現「哈囉」，A 端標示「我」、B 端標示「對手」
```
