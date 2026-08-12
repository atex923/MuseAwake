# MouseAwake Codex Handoff

## 專案用途
這是一個 Windows 防閒置小工具。
主要用途是避免使用者長時間沒有輸入時，被系統視為閒置。
程式同時具有一個視覺效果：閒置 3 分鐘後，
在桌面透明覆蓋層逐步畫出大量雙色火焰。

## 架構
### 1. Windows API
使用 `ctypes` 呼叫：
- `user32.dll`
- `kernel32.dll`
- `shell32.dll`

主要負責：
- `GetLastInputInfo`
- `GetTickCount64`
- `SendInput`
- Windows 原生系統匣
- 虛擬桌面範圍
- 火焰透明視窗的滑鼠穿透

### 2. MouseAwakeApp
主 Tkinter 圓形碼表視窗。

主要功能：
- 閒置秒數顯示
- 3 分鐘圓形進度
- 暫停 / 恢復
- 滑鼠訊號測試
- 火焰測試
- 系統匣
- 視窗拖曳

### 3. NativeTrayIcon
不使用第三方套件，
直接以 `Shell_NotifyIconW` 建立 Windows 系統匣圖示。

### 4. FlameOverlay
全螢幕透明火焰覆蓋層。

火焰不是圖片，而是由 `Canvas.create_polygon()` 搭配
兩組火焰座標 `OUTER_POINTS` / `INNER_POINTS` 即時繪製。

## V0.5.3 火焰輪次規則
### 基礎輪
先依網格將整個虛擬桌面鋪滿。
每格中心有輕微隨機 jitter，出現順序會打亂。

### 5 個位移輪
基礎輪完成後：
1. 等 20 秒 → 左移半格
2. 等 20 秒 → 下移半格
3. 等 20 秒 → 左移半格
4. 等 20 秒 → 下移半格
5. 等 20 秒 → 左移半格

位移採累積：
- `left`：`offset_x -= spacing / 2`
- `down`：`offset_y += spacing / 2`

每輪都重新建立錯位網格，但不清除先前火焰。

## 已修正過的重要問題
### V0.1 → V0.2
`GetTickCount` 原本錯誤從 `user32.dll` 呼叫。
已改為 `kernel32.GetTickCount64()`。

### V0.5 → V0.5.1
火焰透明視窗曾因重複加入 `WS_EX_LAYERED`
而在部分 Windows/Tk 組合完全不可見。
現在透明色交由 Tkinter 管理，
Windows API 只加入滑鼠穿透相關 extended style。

### V0.5.1 → V0.5.2
純隨機火焰容易一直重疊，造成桌面大片空白。
改成隨機順序的網格鋪滿。

### V0.5.2 → V0.5.3
加入 5 個錯位補滿輪：
左、下、左、下、左，每輪間隔 20 秒。

### V0.5.3 → V0.5.4
補齊 Windows message loop 的 ctypes 宣告，並在關閉時等待
tray thread 收尾。火焰網格計算也整理成較少重複屬性讀取，
輪次顯示改為跟隨 `FLAME_SHIFT_SEQUENCE` 長度。

### V0.5.4 → V0.5.5
升級主線版號與檔名，並同步建立 Google Drive 獨立版本資料夾。
V0.5.5 不主動改變 runtime 行為。

## 修改時不要破壞
- `GetTickCount64` 必須從 `kernel32` 呼叫。
- 火焰覆蓋層不要再次自行加入 `WS_EX_LAYERED`。
- 原生 tray thread 的 callback 必須透過 `root.after(...)`
  切回 Tk 主執行緒操作 GUI。
- 火焰覆蓋層需要支援 Windows 虛擬桌面，多螢幕座標可能為負。
- 關閉程式時要取消 `after` 計時器並移除 tray icon。
