# MouseAwake V0.5.3 — Codex 接手起點

## 主線版本
- 目前版本：`V0.5.3`
- 主程式：`source/MouseAwake_V0.5.3.pyw`
- 除錯用副本：`source/MouseAwake_V0.5.3.py`
- 平台：Windows
- GUI：Tkinter
- 外部套件：無
- 火焰圖案：完全由 Python Canvas 繪製，不載入外部 PNG

## Codex 接手原則
1. 以 `MouseAwake_V0.5.3.pyw` 為唯一主線。
2. 修改前先保留既有功能，不要因重構移除任何已完成行為。
3. 每次修改後先做 Python 語法檢查。
4. Windows API / ctypes 結構修改後，要特別留意 32/64 位元相容性。
5. Tkinter 透明視窗不要自行重複加入 `WS_EX_LAYERED`，
   因為 V0.5 曾造成透明覆蓋層完全不可見。
6. 火焰覆蓋視窗必須維持：
   - 透明背景
   - Topmost
   - 滑鼠穿透
   - 不阻擋桌面操作
7. `.pyw` 為正式執行檔來源；`.py` 只方便除錯。

## 現行核心行為
- 偵測最後一次鍵盤/滑鼠輸入。
- 閒置滿 180 秒後送出極小的滑鼠移動訊號。
- 圓形碼表介面顯示閒置時間與 3 分鐘進度。
- 可暫停、測試、縮到系統匣、結束。
- Windows 原生系統匣，不依賴 pystray/Pillow。
- 閒置 3 分鐘後啟動桌面火焰。
- 火焰先完成基礎網格鋪滿。
- 基礎輪完成後，每隔 20 秒進行下一輪位移補滿。
- 位移順序固定：左 → 下 → 左 → 下 → 左。
- 每次位移量：目前網格間距的 1/2。
- 舊火焰全部保留，不清除。
- 共 5 次位移輪。
- 測試模式可完整觀看 5 次位移輪。

## 重要參數
```python
IDLE_SECONDS = 180
CHECK_INTERVAL_MS = 500
SIGNAL_COOLDOWN_SECONDS = 5

FLAME_ADD_INTERVAL_MS = 90
FLAME_TEST_SECONDS = 180
FLAME_ROUND_WAIT_MS = 20000

FLAME_SHIFT_SEQUENCE = (
    "left",
    "down",
    "left",
    "down",
    "left",
)
```

## 建議第一步
在 Windows 上直接執行 `source/MouseAwake_V0.5.3.pyw`，
先確認：
1. 圓形碼表正常。
2. 系統匣正常。
3. 小火焰測試按鈕可啟動桌面火焰。
4. 基礎輪鋪滿後等待 20 秒。
5. 5 個位移輪依「左下左下左」執行。
