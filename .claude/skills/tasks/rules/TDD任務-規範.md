# Rule 1 - 依案例類型切紅燈與綠燈 [MUST]
- 每張案例卡切恰好一個紅燈任務。
- 案例類型為 `TDD Slice` 或 `NFR 量測` 的卡，再切一個綠燈任務，緊接在該卡的紅燈之後。
- 案例類型為 `防回歸（預期不先紅）` 或 `旅程（預期不先紅）` 的卡只切紅燈，不切綠燈。

## Good Example
- SL-007 是 TDD Slice，紅燈後緊接綠燈；SL-003 是防回歸，只有紅燈。

```
- [ ] T007 [US1] `/tdd 紅燈` 撰寫 SL-003 的測試於 `backend/tests/test_chat.py`、`backend/tests/helpers.py`
- [ ] T011 [US1] `/tdd 紅燈` 撰寫 SL-007 的測試於 `backend/tests/test_chat.py`
- [ ] T012 [US1] `/tdd 綠燈` 實作 SL-007 的行為於 `backend/app/chat_rules.py`、`backend/app/chat.py`
```

## Bad Example
- 防回歸卡 SL-003 被切了綠燈，它預期一寫就綠，綠燈任務沒有可實作的行為。

```
- [ ] T007 [US1] `/tdd 紅燈` 撰寫 SL-003 的測試於 `backend/tests/test_chat.py`、`backend/tests/helpers.py`
- [ ] T008 [US1] `/tdd 綠燈` 實作 SL-003 的行為於 `backend/app/chat.py`
```

# Rule 2 - 任務依 test-plan.md 的段落與卡片順序排列 [MUST]
- `## User Story n` 段的卡放在 User Story n 的 Phase，`## 全域 NFR` 段的卡放在全域 NFR Phase。
- Phase 內的任務依卡片在 test-plan.md 的出現順序排列，不依端點或檔案重新分組。

## Good Example
- 依 test-plan.md 的順序，UI 卡 SL-001、SL-002 之後才是 API 卡 SL-003。

```
- [ ] T003 [US1] `/tdd 紅燈` 撰寫 SL-001 的測試於 `frontend/e2e/chat.spec.ts`、`frontend/e2e/support.ts`
- [ ] T004 [US1] `/tdd 綠燈` 實作 SL-001 的行為於 `backend/app/models.py`、`backend/app/chat.py`、`backend/app/main.py`、`frontend/lib/api.ts`、`frontend/lib/use-messages.ts`、`frontend/app/rooms/[id]/chat.tsx`、`frontend/app/rooms/[id]/room.tsx`
- [ ] T005 [US1] `/tdd 紅燈` 撰寫 SL-002 的測試於 `frontend/e2e/chat.spec.ts`
```

## Bad Example
- 為了先做後端，把 API 卡 SL-003 提到 SL-001 之前，順序與 test-plan.md 不一致。

```
- [ ] T003 [US1] `/tdd 紅燈` 撰寫 SL-003 的測試於 `backend/tests/test_chat.py`、`backend/tests/helpers.py`
- [ ] T004 [US1] `/tdd 紅燈` 撰寫 SL-001 的測試於 `frontend/e2e/chat.spec.ts`、`frontend/e2e/support.ts`
```

# Rule 3 - 旅程卡的紅燈放 Acceptance Gates [MUST]
- 案例類型為 `旅程（預期不先紅）` 的卡，不論位於 `## User Story n` 段或 `## 跨故事旅程` 段，紅燈一律放在 Acceptance Gates Phase。
- Acceptance Gates 的任務不標 [US]，此 Phase 不放重構。

## Good Example
- US1 段內的旅程卡 SL-026 與跨故事旅程 SL-034 都在 Acceptance Gates，沒有 [US]。

```
## Phase 5: Acceptance Gates

- [ ] T064 `/tdd 紅燈` 撰寫 SL-026 的測試於 `frontend/e2e/chat.spec.ts`
- [ ] T065 `/tdd 紅燈` 撰寫 SL-034 的測試於 `frontend/e2e/chat.spec.ts`
```

## Bad Example
- SL-026 依所在段落放進 User Story 1 Phase，旅程在全域 NFR 調校之前就執行，無法證明後續修改沒有破壞它。

```
- [ ] T044 [US1] `/tdd 紅燈` 撰寫 SL-026 的測試於 `frontend/e2e/chat.spec.ts`
- [ ] T045 [US1] `/tdd 重構` 整理 User Story 1 的程式碼於 `backend/app/chat.py`
```

# Rule 4 - 重構只在 Phase 末尾一個 [MUST]
- 每個 User Story Phase 與全域 NFR Phase 的最後一個任務是恰好一個重構任務。
- 不在每張卡的綠燈之後各放一個重構。

## Good Example
- User Story 1 Phase 的全部卡之後才有一個重構任務。

```
- [ ] T043 [US1] `/tdd 綠燈` 實作 SL-025 的行為於 `frontend/lib/use-messages.ts`、`frontend/app/rooms/[id]/chat.tsx`
- [ ] T044 [US1] `/tdd 重構` 整理 User Story 1 的程式碼於 `backend/app/chat.py`、`backend/app/chat_rules.py`、`backend/app/models.py`、`frontend/lib/use-messages.ts`、`frontend/app/rooms/[id]/chat.tsx`、`backend/tests/helpers.py`、`frontend/e2e/support.ts`
```

## Bad Example
- 每張卡的綠燈後都接一個重構，同一批檔案被反覆整理，Phase 末尾也沒有收斂整個故事的重構。

```
- [ ] T012 [US1] `/tdd 綠燈` 實作 SL-007 的行為於 `backend/app/chat_rules.py`、`backend/app/chat.py`
- [ ] T013 [US1] `/tdd 重構` 整理 User Story 1 的程式碼於 `backend/app/chat_rules.py`
```

# Rule 5 - 紅燈的檔案取卡片的測試檔與新增的 helper 檔 [MUST]
- 紅燈任務的路徑是該卡「測試檔」欄位的檔案。
- 卡片的建立方式用到尚未在先前紅燈中建立的 helper 時，再加上 plan.md Source Code 樹中標為該 seam fixture helper 的檔。

## Good Example
- SL-001 是第一張 UI 卡，要建立 helper，所以加上 support.ts；SL-002 用的 helper 已存在，只有測試檔。

```
- [ ] T003 [US1] `/tdd 紅燈` 撰寫 SL-001 的測試於 `frontend/e2e/chat.spec.ts`、`frontend/e2e/support.ts`
- [ ] T005 [US1] `/tdd 紅燈` 撰寫 SL-002 的測試於 `frontend/e2e/chat.spec.ts`
```

## Bad Example
- 路徑不是卡片的測試檔欄位，而是自行命名的單元測試檔。

```
- [ ] T005 [US1] `/tdd 紅燈` 撰寫 SL-002 的測試於 `frontend/tests/unit/chat-empty.test.tsx`
```

# Rule 6 - 綠燈的檔案取涉及系統介面在 plan.md 樹標註的實作檔 [MUST]
- 綠燈任務的路徑取自該卡「涉及系統介面」在 plan.md Source Code 樹中標註的實作檔，只列此卡行為需要改動的檔。
- 測試檔與 helper 檔不列在綠燈任務。

## Good Example
- SL-007 只涉及聊天 API 介面，路徑是樹中標為聊天 API 介面、負責驗證與送出的兩個檔。

```
- [ ] T012 [US1] `/tdd 綠燈` 實作 SL-007 的行為於 `backend/app/chat_rules.py`、`backend/app/chat.py`
```

## Bad Example
- SL-007 沒有涉及聊天室介面，卻列了前端檔，並把測試檔也列進來。

```
- [ ] T012 [US1] `/tdd 綠燈` 實作 SL-007 的行為於 `backend/app/chat_rules.py`、`frontend/app/rooms/[id]/chat.tsx`、`backend/tests/test_chat.py`
```

# Rule 7 - Setup 只放補齊測試工具的環境任務 [MUST]
- Setup 只放不走 TDD 的 `環境` 任務，內容是 research.md、techstack.md 定案的測試工具中，repo 現況尚未具備的依賴、設定與執行指令。
- repo 已具備的工具不列任務；資料表、共用程式等產品程式碼不放 Setup，由第一張需要它的卡的綠燈帶出。

## Good Example
- research.md 定案了負載量測與畫面量測，repo 尚缺 marker 與 NFR 專案，各列一個環境任務。

```
- [ ] T001 [P] `環境` 加入負載量測的依賴與 pytest marker 於 `backend/pyproject.toml`
- [ ] T002 [P] `環境` 新增 NFR 量測的 Playwright 專案與畫面寬度設定於 `frontend/playwright.config.ts`
```

## Bad Example
- 把資料表模型放進 Setup，這是 SL-001 綠燈要實作的行為，提前寫好會讓紅燈失去失敗的理由。

```
- [ ] T001 `環境` 建立聊天訊息資料表模型與 (room_id, seq) 唯一鍵於 `backend/app/models.py`
```
