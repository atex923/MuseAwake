# MuseAwake / MouseAwake

MuseAwake repo 目前收錄的主程式是 MouseAwake：一個 Windows 專用的防閒置小工具。它用圓形碼表顯示最後輸入後的閒置時間，閒置滿 3 分鐘後送出極小的滑鼠移動訊號，讓系統維持喚醒狀態，同時以透明桌面覆蓋層畫出多輪火焰效果。

## 程式特色

- Windows 原生閒置偵測：透過 `GetLastInputInfo` 取得鍵盤與滑鼠最後輸入時間。
- 微小滑鼠訊號：以 `SendInput` 右移 1 點後立即移回，不改變游標位置。
- 圓形碼表介面：Tkinter 繪製無標題列碼表、3 分鐘進度環、指針與數位時間。
- 原生系統匣：直接使用 `Shell_NotifyIconW`，不依賴 `pystray` 或 Pillow。
- 桌面火焰模式：閒置滿 3 分鐘後啟動透明、Topmost、滑鼠穿透的火焰覆蓋層。
- 多輪補滿火焰：基礎網格鋪滿後，依序左、下、左、下、左位移半格補滿空隙。
- 多螢幕支援：火焰覆蓋層讀取 Windows 虛擬桌面範圍，可處理負座標螢幕配置。
- 零 runtime 第三方套件：執行只需要 Python 標準函式庫。

## 目前版本

`V0.5.4`

主程式：

```text
source/MouseAwake_V0.5.4.pyw
```

除錯用副本：

```text
source/MouseAwake_V0.5.4.py
```

## 執行方式

Windows 上可直接執行：

```bat
scripts\run_pyw.bat
```

或手動執行：

```bat
pyw source\MouseAwake_V0.5.4.pyw
```

## 檢查與打包

語法檢查：

```bat
scripts\syntax_check.bat
```

Nuitka onefile 打包：

```bat
scripts\build_nuitka_onefile.bat
```

## 開發交接

Codex 或後續維護者請先讀：

```text
docs/CODEX_START_HERE.md
docs/CODEX_HANDOFF.md
```

## 授權

本 repo 使用 GPL-3.0 License。
