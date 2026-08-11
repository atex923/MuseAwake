# MouseAwake 版本歷史

## V0.1
- 建立 Windows 防閒置工具。
- 閒置 3 分鐘後送出微小滑鼠移動訊號。
- 暫停、立即測試、結束。

## V0.2
- 修正 `GetTickCount` DLL 呼叫錯誤。
- 改用 `kernel32.GetTickCount64()`。
- 調整 SendInput 結構。

## V0.3
- 新增最小化到 Windows 系統匣。
- 使用 Windows 原生 Shell_NotifyIcon。
- 不依賴 pystray / Pillow。
- 雙擊 tray 恢復視窗，右鍵可控制。

## V0.4
- 一般矩形 GUI 改成圓形碼表介面。
- 無標題列。
- 外圈 3 分鐘進度。
- 中央數位閒置時間。
- 指針動畫。
- 可拖曳視窗。

## V0.5
- 閒置 3 分鐘後新增桌面火焰效果。
- 火焰由 Python Canvas 直接繪製。
- 新增火焰測試按鈕。
- 透明、Topmost、滑鼠穿透覆蓋層。

## V0.5.1
- 修正部分 Windows 測試火焰完全看不到。
- 不再重複加入 WS_EX_LAYERED。
- 測試啟動時立即先畫數個火焰。

## V0.5.2
- 修正火焰沒有持續鋪滿整個桌面。
- 改為「隨機網格鋪滿」。
- 每個區塊至少安排一個火焰。

## V0.5.3
- 基礎輪完成後每隔 20 秒進行位移補滿。
- 位移順序：左 → 下 → 左 → 下 → 左。
- 每次位移半個網格。
- 共 5 個位移輪。
- 舊火焰全部保留。

## V0.5.4
- 補齊 Windows message loop 的 ctypes 函式宣告。
- 關閉時等待系統匣 thread 收尾，降低 tray icon 殘留機率。
- 整理火焰網格計算，減少重複屬性讀取。
- 輪次顯示改為跟隨 `FLAME_SHIFT_SEQUENCE` 設定值。
- 修正 Windows 批次腳本入口版本與檔頭。
