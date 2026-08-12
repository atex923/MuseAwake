# -*- coding: utf-8 -*-
"""
MouseAwake V0.5.5
Windows 專用－圓形碼表介面

功能：
1. 偵測滑鼠或鍵盤最後一次操作時間。
2. 連續 3 分鐘沒有操作時，送出極小的滑鼠移動訊號。
3. 滑鼠向右移動 1 點後立即移回，游標位置不改變。
4. 圓形碼表介面，外圈顯示 3 分鐘閒置進度。
5. 可拖曳移動視窗。
6. 可暫停、重新啟用、立即測試、縮到系統匣及結束。
7. 雙擊系統匣圖示恢復視窗。
8. 系統匣右鍵選單可顯示視窗、暫停及結束程式。

V0.5.3：
- 火焰改成多輪次鋪滿。
- 基礎網格鋪滿後等待 20 秒，再開始位移補滿。
- 位移順序固定為：左、下、左、下、左。
- 每次位移量為網格間距的一半。
- 5 次位移輪全部保留前一輪火焰，不清除畫面。
- 左移與下移採累積位移，使火焰逐輪填補原網格空隙。
- 測試模式可完整觀看 5 次位移輪。

V0.5.4：
- 補齊 Windows message loop 的 ctypes 函式宣告。
- 關閉程式時等待 tray thread 收尾，降低系統匣圖示殘留機率。
- 整理火焰網格計算，減少重複屬性讀取並讓輪次顯示跟隨設定值。

V0.5.5：
- 升級版號與主程式檔名，對應雲端硬碟獨立版本資料夾同步。
"""

from __future__ import annotations

import ctypes
from ctypes import wintypes
import math
import os
import random
import sys
import threading
import time
import tkinter as tk
from tkinter import messagebox
from typing import Callable, Optional


APP_NAME = "MouseAwake"
VERSION = "V0.5.5"

IDLE_SECONDS = 180
CHECK_INTERVAL_MS = 500
SIGNAL_COOLDOWN_SECONDS = 5

WINDOW_SIZE = 360
TRANSPARENT_COLOR = "#010203"

COLOR_OUTER = "#24272B"
COLOR_RING = "#4B5057"
COLOR_FACE = "#151719"
COLOR_INNER = "#202327"
COLOR_PROGRESS = "#E59C3A"
COLOR_PROGRESS_PAUSED = "#777C83"
COLOR_TEXT = "#F4F4F4"
COLOR_SUBTEXT = "#AEB4BA"
COLOR_BUTTON = "#30343A"
COLOR_BUTTON_HOVER = "#484E56"
COLOR_BUTTON_ACTIVE = "#E59C3A"
COLOR_DANGER = "#A94A4A"
COLOR_DANGER_HOVER = "#C95A5A"
COLOR_FLAME_OUTER = "#F86D5A"
COLOR_FLAME_INNER = "#FFD463"

FLAME_ADD_INTERVAL_MS = 90
FLAME_TEST_SECONDS = 180

# 火焰多輪補滿設定
FLAME_ROUND_WAIT_MS = 20000
FLAME_SHIFT_SEQUENCE = (
    "left",
    "down",
    "left",
    "down",
    "left",
)
TRAY_SHUTDOWN_TIMEOUT_SECONDS = 1.5


if os.name != "nt":
    raise RuntimeError("本程式僅支援 Windows。")


# ----------------------------------------------------------------------
# Windows API
# ----------------------------------------------------------------------

user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
shell32 = ctypes.WinDLL("shell32", use_last_error=True)


LRESULT = ctypes.c_ssize_t
WPARAM = ctypes.c_size_t
LPARAM = ctypes.c_ssize_t

WM_DESTROY = 0x0002
WM_CLOSE = 0x0010
WM_COMMAND = 0x0111
WM_NULL = 0x0000
WM_LBUTTONDBLCLK = 0x0203
WM_RBUTTONUP = 0x0205
WM_CONTEXTMENU = 0x007B
WM_APP = 0x8000
WM_TRAYICON = WM_APP + 1

NIM_ADD = 0x00000000
NIM_MODIFY = 0x00000001
NIM_DELETE = 0x00000002

NIF_MESSAGE = 0x00000001
NIF_ICON = 0x00000002
NIF_TIP = 0x00000004

IMAGE_ICON = 1
LR_DEFAULTSIZE = 0x00000040
LR_SHARED = 0x00008000
IDI_APPLICATION = 32512

MF_STRING = 0x00000000
MF_SEPARATOR = 0x00000800

TPM_RIGHTBUTTON = 0x0002
TPM_RETURNCMD = 0x0100

TRAY_ID = 1
MENU_RESTORE = 1001
MENU_TOGGLE = 1002
MENU_TEST = 1003
MENU_EXIT = 1004

INPUT_MOUSE = 0
MOUSEEVENTF_MOVE = 0x0001

GWL_EXSTYLE = -20
WS_EX_TRANSPARENT = 0x00000020
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_LAYERED = 0x00080000
WS_EX_NOACTIVATE = 0x08000000

SM_XVIRTUALSCREEN = 76
SM_YVIRTUALSCREEN = 77
SM_CXVIRTUALSCREEN = 78
SM_CYVIRTUALSCREEN = 79


class GUID(ctypes.Structure):
    _fields_ = [
        ("Data1", wintypes.DWORD),
        ("Data2", wintypes.WORD),
        ("Data3", wintypes.WORD),
        ("Data4", ctypes.c_ubyte * 8),
    ]


class NOTIFYICONDATAW(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("hWnd", wintypes.HWND),
        ("uID", wintypes.UINT),
        ("uFlags", wintypes.UINT),
        ("uCallbackMessage", wintypes.UINT),
        ("hIcon", wintypes.HICON),
        ("szTip", wintypes.WCHAR * 128),
        ("dwState", wintypes.DWORD),
        ("dwStateMask", wintypes.DWORD),
        ("szInfo", wintypes.WCHAR * 256),
        ("uTimeoutOrVersion", wintypes.UINT),
        ("szInfoTitle", wintypes.WCHAR * 64),
        ("dwInfoFlags", wintypes.DWORD),
        ("guidItem", GUID),
        ("hBalloonIcon", wintypes.HICON),
    ]


WNDPROC = ctypes.WINFUNCTYPE(
    LRESULT,
    wintypes.HWND,
    wintypes.UINT,
    WPARAM,
    LPARAM,
)


class WNDCLASSW(ctypes.Structure):
    _fields_ = [
        ("style", wintypes.UINT),
        ("lpfnWndProc", WNDPROC),
        ("cbClsExtra", ctypes.c_int),
        ("cbWndExtra", ctypes.c_int),
        ("hInstance", wintypes.HINSTANCE),
        ("hIcon", wintypes.HICON),
        ("hCursor", wintypes.HCURSOR),
        ("hbrBackground", wintypes.HBRUSH),
        ("lpszMenuName", wintypes.LPCWSTR),
        ("lpszClassName", wintypes.LPCWSTR),
    ]


class LASTINPUTINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.UINT),
        ("dwTime", wintypes.DWORD),
    ]


ULONG_PTR = wintypes.WPARAM


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]


class INPUT_UNION(ctypes.Union):
    _fields_ = [
        ("mi", MOUSEINPUT),
    ]


class INPUT(ctypes.Structure):
    _anonymous_ = ("union",)
    _fields_ = [
        ("type", wintypes.DWORD),
        ("union", INPUT_UNION),
    ]


user32.GetLastInputInfo.argtypes = [
    ctypes.POINTER(LASTINPUTINFO),
]
user32.GetLastInputInfo.restype = wintypes.BOOL

user32.SendInput.argtypes = [
    wintypes.UINT,
    ctypes.POINTER(INPUT),
    ctypes.c_int,
]
user32.SendInput.restype = wintypes.UINT

kernel32.GetTickCount64.argtypes = []
kernel32.GetTickCount64.restype = ctypes.c_ulonglong

kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
kernel32.GetModuleHandleW.restype = wintypes.HMODULE

user32.RegisterClassW.argtypes = [
    ctypes.POINTER(WNDCLASSW),
]
user32.RegisterClassW.restype = wintypes.ATOM

user32.CreateWindowExW.argtypes = [
    wintypes.DWORD,
    wintypes.LPCWSTR,
    wintypes.LPCWSTR,
    wintypes.DWORD,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    wintypes.HWND,
    wintypes.HMENU,
    wintypes.HINSTANCE,
    wintypes.LPVOID,
]
user32.CreateWindowExW.restype = wintypes.HWND

user32.DefWindowProcW.argtypes = [
    wintypes.HWND,
    wintypes.UINT,
    WPARAM,
    LPARAM,
]
user32.DefWindowProcW.restype = LRESULT

user32.DestroyWindow.argtypes = [wintypes.HWND]
user32.DestroyWindow.restype = wintypes.BOOL

user32.PostQuitMessage.argtypes = [ctypes.c_int]
user32.PostQuitMessage.restype = None

user32.PostMessageW.argtypes = [
    wintypes.HWND,
    wintypes.UINT,
    WPARAM,
    LPARAM,
]
user32.PostMessageW.restype = wintypes.BOOL

user32.GetMessageW.argtypes = [
    ctypes.POINTER(wintypes.MSG),
    wintypes.HWND,
    wintypes.UINT,
    wintypes.UINT,
]
user32.GetMessageW.restype = wintypes.BOOL

user32.TranslateMessage.argtypes = [
    ctypes.POINTER(wintypes.MSG),
]
user32.TranslateMessage.restype = wintypes.BOOL

user32.DispatchMessageW.argtypes = [
    ctypes.POINTER(wintypes.MSG),
]
user32.DispatchMessageW.restype = LRESULT

user32.LoadImageW.argtypes = [
    wintypes.HINSTANCE,
    ctypes.c_void_p,
    wintypes.UINT,
    ctypes.c_int,
    ctypes.c_int,
    wintypes.UINT,
]
user32.LoadImageW.restype = wintypes.HANDLE

user32.CreatePopupMenu.argtypes = []
user32.CreatePopupMenu.restype = wintypes.HMENU

user32.AppendMenuW.argtypes = [
    wintypes.HMENU,
    wintypes.UINT,
    ctypes.c_size_t,
    wintypes.LPCWSTR,
]
user32.AppendMenuW.restype = wintypes.BOOL

user32.TrackPopupMenu.argtypes = [
    wintypes.HMENU,
    wintypes.UINT,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    wintypes.HWND,
    ctypes.c_void_p,
]
user32.TrackPopupMenu.restype = wintypes.UINT

user32.DestroyMenu.argtypes = [wintypes.HMENU]
user32.DestroyMenu.restype = wintypes.BOOL

user32.SetForegroundWindow.argtypes = [wintypes.HWND]
user32.SetForegroundWindow.restype = wintypes.BOOL

user32.GetCursorPos.argtypes = [ctypes.POINTER(wintypes.POINT)]
user32.GetCursorPos.restype = wintypes.BOOL

user32.GetSystemMetrics.argtypes = [ctypes.c_int]
user32.GetSystemMetrics.restype = ctypes.c_int

user32.GetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int]
user32.GetWindowLongW.restype = ctypes.c_long

user32.SetWindowLongW.argtypes = [
    wintypes.HWND,
    ctypes.c_int,
    ctypes.c_long,
]
user32.SetWindowLongW.restype = ctypes.c_long

shell32.Shell_NotifyIconW.argtypes = [
    wintypes.DWORD,
    ctypes.POINTER(NOTIFYICONDATAW),
]
shell32.Shell_NotifyIconW.restype = wintypes.BOOL


# ----------------------------------------------------------------------
# 滑鼠閒置偵測
# ----------------------------------------------------------------------

def get_idle_seconds() -> float:
    """取得最後一次鍵盤或滑鼠操作後經過的秒數。"""
    info = LASTINPUTINFO()
    info.cbSize = ctypes.sizeof(LASTINPUTINFO)

    if not user32.GetLastInputInfo(ctypes.byref(info)):
        error_code = ctypes.get_last_error()
        raise ctypes.WinError(error_code)

    current_tick = int(kernel32.GetTickCount64() & 0xFFFFFFFF)
    elapsed_ms = (current_tick - int(info.dwTime)) & 0xFFFFFFFF

    return elapsed_ms / 1000.0


def send_relative_mouse_move(dx: int, dy: int) -> None:
    """送出一次相對滑鼠移動訊號。"""
    mouse_input = INPUT(
        type=INPUT_MOUSE,
        mi=MOUSEINPUT(
            dx=dx,
            dy=dy,
            mouseData=0,
            dwFlags=MOUSEEVENTF_MOVE,
            time=0,
            dwExtraInfo=0,
        ),
    )

    sent = user32.SendInput(
        1,
        ctypes.byref(mouse_input),
        ctypes.sizeof(INPUT),
    )

    if sent != 1:
        error_code = ctypes.get_last_error()

        if error_code:
            raise ctypes.WinError(error_code)

        raise RuntimeError("Windows 未接受滑鼠移動訊號。")


def send_tiny_mouse_move() -> None:
    """右移 1 點後立即移回原位置。"""
    send_relative_mouse_move(1, 0)
    time.sleep(0.02)
    send_relative_mouse_move(-1, 0)


# ----------------------------------------------------------------------
# Windows 原生系統匣圖示
# ----------------------------------------------------------------------

class NativeTrayIcon:
    """使用 Windows Shell_NotifyIcon 建立系統匣圖示。"""

    def __init__(
        self,
        tooltip: str,
        on_restore: Callable[[], None],
        on_toggle: Callable[[], None],
        on_test: Callable[[], None],
        on_exit: Callable[[], None],
        is_enabled: Callable[[], bool],
    ) -> None:
        self.tooltip = tooltip[:127]
        self.on_restore = on_restore
        self.on_toggle = on_toggle
        self.on_test = on_test
        self.on_exit = on_exit
        self.is_enabled = is_enabled

        self.hwnd: Optional[int] = None
        self.icon_data: Optional[NOTIFYICONDATAW] = None
        self.thread: Optional[threading.Thread] = None
        self.started_event = threading.Event()
        self._wnd_proc_reference = None

    def start(self) -> None:
        if self.thread is not None and self.thread.is_alive():
            return

        self.started_event.clear()
        self.thread = threading.Thread(
            target=self._message_loop,
            name="MouseAwakeTray",
            daemon=True,
        )
        self.thread.start()
        self.started_event.wait(timeout=3)

    def stop(self) -> None:
        hwnd = self.hwnd

        if hwnd:
            user32.PostMessageW(hwnd, WM_CLOSE, 0, 0)

        thread = self.thread

        if (
            thread is not None
            and thread.is_alive()
            and thread is not threading.current_thread()
        ):
            thread.join(timeout=TRAY_SHUTDOWN_TIMEOUT_SECONDS)

    def update_tooltip(self, text: str) -> None:
        self.tooltip = text[:127]

        if self.icon_data is None:
            return

        self.icon_data.szTip = self.tooltip
        shell32.Shell_NotifyIconW(
            NIM_MODIFY,
            ctypes.byref(self.icon_data),
        )

    def _message_loop(self) -> None:
        class_name = (
            f"{APP_NAME}_{VERSION}_TrayWindow_"
            f"{os.getpid()}_{id(self)}"
        )

        hinstance = kernel32.GetModuleHandleW(None)
        self._wnd_proc_reference = WNDPROC(self._wnd_proc)

        wnd_class = WNDCLASSW()
        wnd_class.style = 0
        wnd_class.lpfnWndProc = self._wnd_proc_reference
        wnd_class.cbClsExtra = 0
        wnd_class.cbWndExtra = 0
        wnd_class.hInstance = hinstance
        wnd_class.hIcon = None
        wnd_class.hCursor = None
        wnd_class.hbrBackground = None
        wnd_class.lpszMenuName = None
        wnd_class.lpszClassName = class_name

        atom = user32.RegisterClassW(ctypes.byref(wnd_class))

        if not atom:
            self.started_event.set()
            return

        hwnd = user32.CreateWindowExW(
            0,
            class_name,
            class_name,
            0,
            0,
            0,
            0,
            0,
            None,
            None,
            hinstance,
            None,
        )

        if not hwnd:
            self.started_event.set()
            return

        self.hwnd = hwnd

        icon_handle = user32.LoadImageW(
            None,
            ctypes.c_void_p(IDI_APPLICATION),
            IMAGE_ICON,
            0,
            0,
            LR_DEFAULTSIZE | LR_SHARED,
        )

        icon_data = NOTIFYICONDATAW()
        icon_data.cbSize = ctypes.sizeof(NOTIFYICONDATAW)
        icon_data.hWnd = hwnd
        icon_data.uID = TRAY_ID
        icon_data.uFlags = NIF_MESSAGE | NIF_ICON | NIF_TIP
        icon_data.uCallbackMessage = WM_TRAYICON
        icon_data.hIcon = icon_handle
        icon_data.szTip = self.tooltip

        self.icon_data = icon_data

        added = shell32.Shell_NotifyIconW(
            NIM_ADD,
            ctypes.byref(icon_data),
        )

        self.started_event.set()

        if not added:
            user32.DestroyWindow(hwnd)
            self.hwnd = None
            return

        message = wintypes.MSG()

        while user32.GetMessageW(
            ctypes.byref(message),
            None,
            0,
            0,
        ) > 0:
            user32.TranslateMessage(ctypes.byref(message))
            user32.DispatchMessageW(ctypes.byref(message))

        self.hwnd = None
        self.icon_data = None

    def _wnd_proc(
        self,
        hwnd: int,
        message: int,
        wparam: int,
        lparam: int,
    ) -> int:
        if message == WM_TRAYICON:
            event_code = int(lparam) & 0xFFFF

            if event_code == WM_LBUTTONDBLCLK:
                self.on_restore()
                return 0

            if event_code in (WM_RBUTTONUP, WM_CONTEXTMENU):
                self._show_context_menu(hwnd)
                return 0

        if message == WM_COMMAND:
            command_id = int(wparam) & 0xFFFF
            self._run_menu_command(command_id)
            return 0

        if message == WM_CLOSE:
            user32.DestroyWindow(hwnd)
            return 0

        if message == WM_DESTROY:
            if self.icon_data is not None:
                shell32.Shell_NotifyIconW(
                    NIM_DELETE,
                    ctypes.byref(self.icon_data),
                )

            user32.PostQuitMessage(0)
            return 0

        return user32.DefWindowProcW(
            hwnd,
            message,
            wparam,
            lparam,
        )

    def _show_context_menu(self, hwnd: int) -> None:
        menu = user32.CreatePopupMenu()

        if not menu:
            return

        toggle_text = "暫停防閒置" if self.is_enabled() else "重新啟用"

        user32.AppendMenuW(
            menu,
            MF_STRING,
            MENU_RESTORE,
            "顯示碼表",
        )
        user32.AppendMenuW(
            menu,
            MF_STRING,
            MENU_TOGGLE,
            toggle_text,
        )
        user32.AppendMenuW(
            menu,
            MF_STRING,
            MENU_TEST,
            "立即測試",
        )
        user32.AppendMenuW(menu, MF_SEPARATOR, 0, None)
        user32.AppendMenuW(
            menu,
            MF_STRING,
            MENU_EXIT,
            "結束程式",
        )

        point = wintypes.POINT()

        if not user32.GetCursorPos(ctypes.byref(point)):
            user32.DestroyMenu(menu)
            return

        user32.SetForegroundWindow(hwnd)

        command_id = user32.TrackPopupMenu(
            menu,
            TPM_RIGHTBUTTON | TPM_RETURNCMD,
            point.x,
            point.y,
            0,
            hwnd,
            None,
        )

        user32.PostMessageW(hwnd, WM_NULL, 0, 0)
        user32.DestroyMenu(menu)

        if command_id:
            self._run_menu_command(command_id)

    def _run_menu_command(self, command_id: int) -> None:
        if command_id == MENU_RESTORE:
            self.on_restore()
        elif command_id == MENU_TOGGLE:
            self.on_toggle()
        elif command_id == MENU_TEST:
            self.on_test()
        elif command_id == MENU_EXIT:
            self.on_exit()



# ----------------------------------------------------------------------
# 桌面火焰覆蓋層
# ----------------------------------------------------------------------

class FlameOverlay:
    """
    全螢幕透明火焰覆蓋層。

    V0.5.3 多輪鋪滿：
    - 先完成基礎網格。
    - 基礎完成後每隔 20 秒開始下一輪。
    - 位移輪固定為：左、下、左、下、左。
    - 每次位移半個網格。
    - 舊火焰不清除，持續疊加。
    """

    OUTER_POINTS = [
        (0.50, 0.00),
        (0.42, 0.11),
        (0.43, 0.26),
        (0.56, 0.48),
        (0.67, 0.64),
        (0.70, 0.50),
        (0.79, 0.34),
        (0.82, 0.53),
        (0.79, 0.76),
        (0.68, 0.91),
        (0.54, 0.99),
        (0.39, 0.98),
        (0.23, 0.90),
        (0.11, 0.76),
        (0.05, 0.60),
        (0.06, 0.43),
        (0.16, 0.25),
        (0.18, 0.43),
        (0.25, 0.49),
        (0.24, 0.31),
        (0.31, 0.17),
        (0.40, 0.07),
    ]

    INNER_POINTS = [
        (0.47, 0.40),
        (0.40, 0.49),
        (0.36, 0.61),
        (0.38, 0.74),
        (0.44, 0.82),
        (0.38, 0.77),
        (0.32, 0.69),
        (0.29, 0.79),
        (0.30, 0.89),
        (0.36, 0.96),
        (0.47, 1.00),
        (0.58, 0.98),
        (0.65, 0.91),
        (0.68, 0.82),
        (0.66, 0.72),
        (0.62, 0.66),
        (0.63, 0.82),
        (0.58, 0.90),
        (0.59, 0.79),
        (0.55, 0.67),
        (0.49, 0.57),
        (0.46, 0.49),
    ]

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.window = tk.Toplevel(root)
        self.window.withdraw()
        self.window.overrideredirect(True)
        self.window.configure(bg=TRANSPARENT_COLOR)

        try:
            self.window.wm_attributes(
                "-transparentcolor",
                TRANSPARENT_COLOR,
            )
        except tk.TclError:
            pass

        try:
            self.window.wm_attributes("-topmost", True)
        except tk.TclError:
            pass

        self.canvas = tk.Canvas(
            self.window,
            bg=TRANSPARENT_COLOR,
            highlightthickness=0,
            bd=0,
        )
        self.canvas.pack(fill="both", expand=True)

        self.running = False
        self.after_id: Optional[str] = None

        self.flame_count = 0
        self.flames_per_tick = 1
        self.coverage_plan: list[tuple[float, float]] = []
        self.coverage_index = 0
        self.coverage_spacing = 96
        self.fast_fill = False

        # 多輪次狀態
        self.shift_sequence = list(FLAME_SHIFT_SEQUENCE)
        self.shift_round_index = 0
        self.current_direction = "base"
        self.offset_x = 0.0
        self.offset_y = 0.0
        self.waiting_for_next_round = False
        self.next_round_at = 0.0
        self.sequence_finished = False

        self.virtual_x = 0
        self.virtual_y = 0
        self.virtual_width = 1920
        self.virtual_height = 1080

    def _read_virtual_screen(self) -> None:
        self.virtual_x = user32.GetSystemMetrics(
            SM_XVIRTUALSCREEN
        )
        self.virtual_y = user32.GetSystemMetrics(
            SM_YVIRTUALSCREEN
        )
        self.virtual_width = max(
            1,
            user32.GetSystemMetrics(
                SM_CXVIRTUALSCREEN
            ),
        )
        self.virtual_height = max(
            1,
            user32.GetSystemMetrics(
                SM_CYVIRTUALSCREEN
            ),
        )

        min_dimension = min(
            self.virtual_width,
            self.virtual_height,
        )

        self.coverage_spacing = max(
            78,
            min(
                108,
                int(min_dimension * 0.09),
            ),
        )

    def _build_coverage_plan(self) -> None:
        """
        依目前 offset_x / offset_y 建立一輪網格。

        邊界額外多建立一圈格子，讓半格位移後，
        桌面四周仍然能被火焰覆蓋。
        """
        plan: list[tuple[float, float]] = []

        spacing = self.coverage_spacing
        half_spacing = spacing / 2
        margin = spacing
        max_x = self.virtual_width + margin
        max_y = self.virtual_height + margin

        rows = max(
            1,
            math.ceil(
                self.virtual_height
                / spacing
            ),
        )
        columns = max(
            1,
            math.ceil(
                self.virtual_width
                / spacing
            ),
        )

        # 位移輪的重點是補縫，所以 jitter 比 V0.5.2 小，
        # 保留「半格錯位」效果。
        jitter = spacing * 0.12

        for row in range(-1, rows + 2):
            for column in range(-1, columns + 2):
                center_x = (
                    column * spacing
                    + half_spacing
                    + self.offset_x
                )
                center_y = (
                    row * spacing
                    + half_spacing
                    + self.offset_y
                )

                center_x += random.uniform(
                    -jitter,
                    jitter,
                )
                center_y += random.uniform(
                    -jitter,
                    jitter,
                )

                if (
                    -margin <= center_x
                    <= max_x
                    and
                    -margin <= center_y
                    <= max_y
                ):
                    plan.append(
                        (center_x, center_y)
                    )

        random.shuffle(plan)

        self.coverage_plan = plan
        self.coverage_index = 0

        # 每一輪鋪滿速度：
        # 測試約 9 秒，正式閒置約 16 秒。
        fill_target_ms = (
            9000
            if self.fast_fill
            else 16000
        )

        target_ticks = max(
            1,
            int(
                fill_target_ms
                / FLAME_ADD_INTERVAL_MS
            ),
        )

        self.flames_per_tick = max(
            1,
            math.ceil(
                len(self.coverage_plan)
                / target_ticks
            ),
        )

    def _apply_click_through(self) -> None:
        try:
            self.window.update_idletasks()
            hwnd = self.window.winfo_id()

            ex_style = user32.GetWindowLongW(
                hwnd,
                GWL_EXSTYLE,
            )
            ex_style |= (
                WS_EX_TRANSPARENT
                | WS_EX_TOOLWINDOW
                | WS_EX_NOACTIVATE
            )

            user32.SetWindowLongW(
                hwnd,
                GWL_EXSTYLE,
                ex_style,
            )
        except Exception:
            pass

    def _raise_overlay(self) -> None:
        if not self.running:
            return

        try:
            self.window.lift()
            self.window.wm_attributes(
                "-topmost",
                True,
            )
        except tk.TclError:
            pass

    def _draw_initial_flames(self) -> None:
        initial_count = min(
            10,
            len(self.coverage_plan),
        )

        for _ in range(initial_count):
            if self.coverage_index >= len(
                self.coverage_plan
            ):
                break

            self._add_next_flame()

        self.canvas.update_idletasks()

    def start(
        self,
        clear_first: bool = True,
        fast_fill: bool = False,
    ) -> None:
        self.fast_fill = fast_fill

        if clear_first:
            self.canvas.delete("flame")
            self.flame_count = 0

        self.shift_round_index = 0
        self.current_direction = "base"
        self.offset_x = 0.0
        self.offset_y = 0.0
        self.waiting_for_next_round = False
        self.next_round_at = 0.0
        self.sequence_finished = False

        self._read_virtual_screen()
        self._build_coverage_plan()

        geometry = (
            f"{self.virtual_width}x{self.virtual_height}"
            f"{self.virtual_x:+d}{self.virtual_y:+d}"
        )

        self.window.geometry(geometry)
        self.canvas.configure(
            width=self.virtual_width,
            height=self.virtual_height,
        )

        self.window.deiconify()
        self.window.lift()

        try:
            self.window.wm_attributes(
                "-topmost",
                True,
            )
        except tk.TclError:
            pass

        self.window.update_idletasks()

        try:
            self.window.update()
        except tk.TclError:
            return

        self.running = True
        self._draw_initial_flames()
        self._apply_click_through()
        self.root.after(
            80,
            self._raise_overlay,
        )

        self._cancel_timer()
        self._schedule_next_batch()

    def _cancel_timer(self) -> None:
        if self.after_id is not None:
            try:
                self.root.after_cancel(
                    self.after_id
                )
            except tk.TclError:
                pass
            self.after_id = None

    def stop(self) -> None:
        self.running = False
        self._cancel_timer()

        self.waiting_for_next_round = False
        self.next_round_at = 0.0

        self.canvas.delete("flame")
        self.flame_count = 0

        try:
            self.window.withdraw()
        except tk.TclError:
            pass

    def destroy(self) -> None:
        self.stop()

        try:
            self.window.destroy()
        except tk.TclError:
            pass

    def _schedule_next_batch(self) -> None:
        if not self.running:
            return

        self.after_id = self.root.after(
            FLAME_ADD_INTERVAL_MS,
            self._add_flame_batch,
        )

    def _add_flame_batch(self) -> None:
        self.after_id = None

        if not self.running:
            return

        for _ in range(self.flames_per_tick):
            if self.coverage_index >= len(
                self.coverage_plan
            ):
                break

            self._add_next_flame()

        if self.coverage_index < len(
            self.coverage_plan
        ):
            self._schedule_next_batch()
            return

        # 目前這一輪完成。
        self._current_round_completed()

    def _current_round_completed(self) -> None:
        if not self.running:
            return

        # shift_round_index 表示已完成幾次「位移輪」。
        # 基礎輪不計入左/下 5 次位移輪。
        if self.shift_round_index >= len(
            self.shift_sequence
        ):
            self.sequence_finished = True
            self.waiting_for_next_round = False
            self.next_round_at = 0.0
            return

        self.waiting_for_next_round = True
        self.next_round_at = (
            time.monotonic()
            + FLAME_ROUND_WAIT_MS / 1000.0
        )

        self.after_id = self.root.after(
            FLAME_ROUND_WAIT_MS,
            self._begin_next_shift_round,
        )

    def _begin_next_shift_round(self) -> None:
        self.after_id = None

        if not self.running:
            return

        if self.shift_round_index >= len(
            self.shift_sequence
        ):
            self.sequence_finished = True
            return

        direction = self.shift_sequence[
            self.shift_round_index
        ]
        self.shift_round_index += 1
        self.current_direction = direction

        half = self.coverage_spacing / 2.0

        if direction == "left":
            self.offset_x -= half
        elif direction == "down":
            self.offset_y += half

        self.waiting_for_next_round = False
        self.next_round_at = 0.0

        # 不清除舊火焰，只建立新的錯位網格。
        self._build_coverage_plan()

        # 每輪開始先立即冒幾個火焰。
        initial_count = min(
            6,
            len(self.coverage_plan),
        )

        for _ in range(initial_count):
            if self.coverage_index >= len(
                self.coverage_plan
            ):
                break
            self._add_next_flame()

        self._schedule_next_batch()

    def _add_next_flame(self) -> None:
        if self.coverage_index >= len(
            self.coverage_plan
        ):
            return

        x, y = self.coverage_plan[
            self.coverage_index
        ]
        self.coverage_index += 1

        size = random.randint(
            int(self.coverage_spacing * 1.12),
            int(self.coverage_spacing * 1.58),
        )
        size = min(
            195,
            max(82, size),
        )

        angle = random.uniform(
            -16.0,
            16.0,
        )

        self.draw_flame(
            self.canvas,
            x,
            y,
            size,
            angle,
            tags=("flame",),
        )

        self.flame_count += 1

    def is_coverage_complete(self) -> bool:
        return (
            len(self.coverage_plan) > 0
            and self.coverage_index
            >= len(self.coverage_plan)
        )

    def fill_progress(self) -> float:
        if not self.coverage_plan:
            return 0.0

        return min(
            1.0,
            self.coverage_index
            / len(self.coverage_plan),
        )

    def seconds_until_next_round(self) -> int:
        if (
            not self.waiting_for_next_round
            or self.next_round_at <= 0
        ):
            return 0

        return max(
            0,
            math.ceil(
                self.next_round_at
                - time.monotonic()
            ),
        )

    def next_direction_text(self) -> str:
        if self.shift_round_index >= len(
            self.shift_sequence
        ):
            return ""

        direction = self.shift_sequence[
            self.shift_round_index
        ]

        if direction == "left":
            return "左移半格"
        if direction == "down":
            return "下移半格"
        return direction

    def round_status_text(self) -> str:
        """
        顯示目前輪次。

        基礎網格完成後，依序執行 5 個位移輪：
        左 → 下 → 左 → 下 → 左。
        """
        total_rounds = len(self.shift_sequence)

        if self.sequence_finished:
            return f"{total_rounds}/{total_rounds} 位移輪完成"

        if self.waiting_for_next_round:
            seconds = self.seconds_until_next_round()
            next_text = self.next_direction_text()
            return (
                f"等待 {seconds} 秒 → {next_text}"
            )

        progress = int(
            self.fill_progress() * 100
        )

        if self.current_direction == "base":
            return (
                f"基礎鋪滿：{progress}%"
            )

        direction_text = (
            "左移半格"
            if self.current_direction == "left"
            else "下移半格"
        )

        return (
            f"位移輪 {self.shift_round_index}/{total_rounds} "
            f"{direction_text}：{progress}%"
        )

    @classmethod
    def draw_flame(
        cls,
        canvas: tk.Canvas,
        x: float,
        y: float,
        size: float,
        angle_degrees: float = 0.0,
        tags: tuple[str, ...] = (),
    ) -> None:
        """以 Canvas 平滑多邊形畫出雙色火焰。"""
        angle = math.radians(angle_degrees)
        cos_a = math.cos(angle)
        sin_a = math.sin(angle)

        width = size * 0.78
        height = size

        def transform(
            points: list[tuple[float, float]],
        ) -> list[float]:
            transformed: list[float] = []

            for px, py in points:
                local_x = (px - 0.5) * width
                local_y = (py - 0.5) * height

                rotated_x = local_x * cos_a - local_y * sin_a
                rotated_y = local_x * sin_a + local_y * cos_a

                transformed.extend(
                    [
                        x + rotated_x,
                        y + rotated_y,
                    ]
                )

            return transformed

        outer_tags = tuple(tags) + ("flame_outer",)
        inner_tags = tuple(tags) + ("flame_inner",)

        canvas.create_polygon(
            transform(cls.OUTER_POINTS),
            fill=COLOR_FLAME_OUTER,
            outline="",
            smooth=True,
            splinesteps=24,
            tags=outer_tags,
        )
        canvas.create_polygon(
            transform(cls.INNER_POINTS),
            fill=COLOR_FLAME_INNER,
            outline="",
            smooth=True,
            splinesteps=24,
            tags=inner_tags,
        )

# ----------------------------------------------------------------------
# 圓形碼表主視窗
# ----------------------------------------------------------------------

class MouseAwakeApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.enabled = True
        self.closing = False
        self.last_signal_time = 0.0
        self.after_id: Optional[str] = None

        self.flame_active = False
        self.flame_test_mode = False
        self.flame_test_until = 0.0
        self.previous_idle_seconds = 0.0
        self.last_injected_at = 0.0

        self.dragging = False
        self.drag_start_x = 0
        self.drag_start_y = 0
        self.window_start_x = 0
        self.window_start_y = 0

        self.root.title(f"{APP_NAME} {VERSION}")
        self.root.geometry(f"{WINDOW_SIZE}x{WINDOW_SIZE}")
        self.root.resizable(False, False)
        self.root.overrideredirect(True)
        self.root.configure(bg=TRANSPARENT_COLOR)

        try:
            self.root.wm_attributes("-transparentcolor", TRANSPARENT_COLOR)
        except tk.TclError:
            pass

        self.canvas = tk.Canvas(
            root,
            width=WINDOW_SIZE,
            height=WINDOW_SIZE,
            bg=TRANSPARENT_COLOR,
            highlightthickness=0,
            bd=0,
        )
        self.canvas.pack(fill="both", expand=True)

        self.context_menu = tk.Menu(
            root,
            tearoff=False,
            font=("Microsoft JhengHei UI", 10),
        )
        self.context_menu.add_command(
            label="暫停防閒置",
            command=self.toggle_enabled,
        )
        self.context_menu.add_command(
            label="立即測試",
            command=self.test_signal,
        )
        self.context_menu.add_command(
            label="測試桌面火焰",
            command=self.test_flames,
        )
        self.context_menu.add_separator()
        self.context_menu.add_command(
            label="縮到系統匣",
            command=self.minimize_to_tray,
        )
        self.context_menu.add_command(
            label="結束程式",
            command=self.close_app,
        )

        self.button_data = {
            "toggle": {
                "x": 94,
                "y": 286,
                "r": 21,
                "text": "Ⅱ",
                "command": self.toggle_enabled,
                "fill": COLOR_BUTTON,
            },
            "test": {
                "x": 138,
                "y": 315,
                "r": 20,
                "text": "↻",
                "command": self.test_signal,
                "fill": COLOR_BUTTON,
            },
            "flame": {
                "x": 180,
                "y": 326,
                "r": 20,
                "text": "",
                "command": self.test_flames,
                "fill": "#56352D",
            },
            "minimize": {
                "x": 222,
                "y": 315,
                "r": 20,
                "text": "−",
                "command": self.minimize_to_tray,
                "fill": COLOR_BUTTON,
            },
            "close": {
                "x": 266,
                "y": 286,
                "r": 21,
                "text": "×",
                "command": self.close_app,
                "fill": COLOR_DANGER,
            },
        }

        self.flame_overlay = FlameOverlay(self.root)

        self.draw_static_face()
        self.create_dynamic_items()
        self.create_control_buttons()

        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        self.canvas.bind("<Button-3>", self.show_context_menu)

        self.root.bind("<Escape>", self.escape_action)

        self.tray_icon = NativeTrayIcon(
            tooltip=f"{APP_NAME} {VERSION}－啟用中",
            on_restore=self._tray_restore_request,
            on_toggle=self._tray_toggle_request,
            on_test=self._tray_test_request,
            on_exit=self._tray_exit_request,
            is_enabled=lambda: self.enabled,
        )
        self.tray_icon.start()

        self.schedule_update()
        self.center_window()

    # ------------------------------------------------------------------
    # 畫面繪製
    # ------------------------------------------------------------------

    def draw_static_face(self) -> None:
        center = WINDOW_SIZE // 2

        # 碼表上方按鈕與錶冠
        self._create_rounded_rectangle(
            159,
            2,
            201,
            35,
            10,
            fill=COLOR_OUTER,
            outline=COLOR_RING,
            width=2,
            tags=("body",),
        )
        self._create_rounded_rectangle(
            168,
            0,
            192,
            18,
            7,
            fill=COLOR_RING,
            outline=COLOR_RING,
            tags=("body",),
        )

        # 左右小按鈕，增加碼表外觀
        self._create_rounded_rectangle(
            84,
            31,
            126,
            48,
            7,
            fill=COLOR_OUTER,
            outline=COLOR_RING,
            width=2,
            tags=("body",),
        )
        self._create_rounded_rectangle(
            234,
            31,
            276,
            48,
            7,
            fill=COLOR_OUTER,
            outline=COLOR_RING,
            width=2,
            tags=("body",),
        )

        # 外殼
        self.canvas.create_oval(
            18,
            18,
            WINDOW_SIZE - 18,
            WINDOW_SIZE - 18,
            fill=COLOR_OUTER,
            outline="#0B0C0D",
            width=3,
            tags=("body",),
        )
        self.canvas.create_oval(
            29,
            29,
            WINDOW_SIZE - 29,
            WINDOW_SIZE - 29,
            fill=COLOR_FACE,
            outline=COLOR_RING,
            width=4,
            tags=("body",),
        )
        self.canvas.create_oval(
            47,
            47,
            WINDOW_SIZE - 47,
            WINDOW_SIZE - 47,
            fill=COLOR_INNER,
            outline="#101214",
            width=2,
            tags=("body",),
        )

        # 刻度
        for index in range(60):
            angle = math.radians(index * 6 - 90)
            is_major = index % 5 == 0

            outer_radius = 137
            inner_radius = 123 if is_major else 129

            x1 = center + math.cos(angle) * inner_radius
            y1 = center + math.sin(angle) * inner_radius
            x2 = center + math.cos(angle) * outer_radius
            y2 = center + math.sin(angle) * outer_radius

            self.canvas.create_line(
                x1,
                y1,
                x2,
                y2,
                fill=COLOR_TEXT if is_major else "#70767D",
                width=3 if is_major else 1,
                tags=("body",),
            )

        # 主要分鐘數字
        number_positions = [
            ("0", 180, 67),
            ("1", 274, 112),
            ("2", 286, 210),
            ("3", 225, 274),
            ("", 180, 292),
            ("", 135, 274),
            ("", 74, 210),
            ("", 86, 112),
        ]
        for text, x, y in number_positions:
            if text:
                self.canvas.create_text(
                    x,
                    y,
                    text=text,
                    fill=COLOR_SUBTEXT,
                    font=("Segoe UI", 11, "bold"),
                    tags=("body",),
                )

        self.canvas.create_text(
            center,
            91,
            text="MOUSE AWAKE",
            fill=COLOR_SUBTEXT,
            font=("Segoe UI", 10, "bold"),
            tags=("body",),
        )
        self.canvas.create_text(
            center,
            108,
            text=f"3 MIN  •  {VERSION}",
            fill="#777D84",
            font=("Segoe UI", 8),
            tags=("body",),
        )

        # 中央數位顯示框
        self._create_rounded_rectangle(
            88,
            130,
            272,
            205,
            14,
            fill="#0A0C0D",
            outline="#3C4248",
            width=2,
            tags=("body",),
        )

        self.canvas.create_text(
            center,
            220,
            text="閒置時間",
            fill=COLOR_SUBTEXT,
            font=("Microsoft JhengHei UI", 9),
            tags=("body",),
        )

        self.canvas.create_text(
            center,
            252,
            text="拖曳可移動｜火焰鍵測試｜Esc 清除/縮匣",
            fill="#777D84",
            font=("Microsoft JhengHei UI", 8),
            tags=("body",),
        )

    def create_dynamic_items(self) -> None:
        # 外圈進度
        self.progress_arc = self.canvas.create_arc(
            35,
            35,
            WINDOW_SIZE - 35,
            WINDOW_SIZE - 35,
            start=90,
            extent=0,
            style="arc",
            outline=COLOR_PROGRESS,
            width=8,
            tags=("body",),
        )

        # 指針
        self.needle = self.canvas.create_line(
            180,
            180,
            180,
            74,
            fill=COLOR_PROGRESS,
            width=3,
            arrow=tk.LAST,
            arrowshape=(8, 10, 4),
            tags=("body",),
        )
        self.canvas.create_oval(
            172,
            172,
            188,
            188,
            fill=COLOR_PROGRESS,
            outline="#0B0C0D",
            width=2,
            tags=("body",),
        )

        self.time_text = self.canvas.create_text(
            180,
            160,
            text="00:00",
            fill=COLOR_TEXT,
            font=("Consolas", 29, "bold"),
            tags=("body",),
        )
        self.status_text = self.canvas.create_text(
            180,
            190,
            text="啟用中",
            fill=COLOR_PROGRESS,
            font=("Microsoft JhengHei UI", 11, "bold"),
            tags=("body",),
        )
        self.message_text = self.canvas.create_text(
            180,
            237,
            text="尚未送出移動訊號",
            fill=COLOR_SUBTEXT,
            font=("Microsoft JhengHei UI", 8),
            tags=("body",),
        )

    def create_control_buttons(self) -> None:
        for name, data in self.button_data.items():
            x = data["x"]
            y = data["y"]
            r = data["r"]

            oval_tag = f"{name}_oval"
            text_tag = f"{name}_text"

            self.canvas.create_oval(
                x - r,
                y - r,
                x + r,
                y + r,
                fill=data["fill"],
                outline="#5D636A",
                width=2,
                tags=("control", name, oval_tag),
            )
            if name == "flame":
                FlameOverlay.draw_flame(
                    self.canvas,
                    x,
                    y + 1,
                    24,
                    0,
                    tags=("control", name, text_tag),
                )
            else:
                self.canvas.create_text(
                    x,
                    y - 1,
                    text=data["text"],
                    fill=COLOR_TEXT,
                    font=("Segoe UI Symbol", 15, "bold"),
                    tags=("control", name, text_tag),
                )

            self.canvas.tag_bind(
                name,
                "<Enter>",
                lambda _event, button_name=name: self.set_button_hover(
                    button_name,
                    True,
                ),
            )
            self.canvas.tag_bind(
                name,
                "<Leave>",
                lambda _event, button_name=name: self.set_button_hover(
                    button_name,
                    False,
                ),
            )
            self.canvas.tag_bind(
                name,
                "<ButtonRelease-1>",
                lambda _event, button_name=name: self.run_button(
                    button_name
                ),
            )

    def set_button_hover(self, name: str, hovering: bool) -> None:
        if name == "close":
            fill = COLOR_DANGER_HOVER if hovering else COLOR_DANGER
        elif name == "flame":
            fill = "#7A4637" if hovering else "#56352D"
        elif name == "toggle" and not self.enabled:
            fill = COLOR_BUTTON_HOVER if hovering else COLOR_BUTTON_ACTIVE
        else:
            fill = COLOR_BUTTON_HOVER if hovering else COLOR_BUTTON

        self.canvas.itemconfigure(
            f"{name}_oval",
            fill=fill,
        )

    def update_stopwatch_display(self, idle_seconds: float) -> None:
        capped_idle = min(max(idle_seconds, 0.0), float(IDLE_SECONDS))
        minutes = int(idle_seconds) // 60
        seconds = int(idle_seconds) % 60

        self.canvas.itemconfigure(
            self.time_text,
            text=f"{minutes:02d}:{seconds:02d}",
        )

        ratio = capped_idle / IDLE_SECONDS
        extent = -359.9 * ratio

        progress_color = (
            COLOR_PROGRESS if self.enabled else COLOR_PROGRESS_PAUSED
        )

        self.canvas.itemconfigure(
            self.progress_arc,
            extent=extent,
            outline=progress_color,
        )

        # 0 秒指向正上方，180 秒繞一整圈。
        angle = math.radians(-90 + 360 * ratio)
        needle_length = 105
        needle_x = 180 + math.cos(angle) * needle_length
        needle_y = 180 + math.sin(angle) * needle_length

        self.canvas.coords(
            self.needle,
            180,
            180,
            needle_x,
            needle_y,
        )
        self.canvas.itemconfigure(
            self.needle,
            fill=progress_color,
        )

    def _create_rounded_rectangle(
        self,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        radius: float,
        **kwargs,
    ) -> int:
        points = [
            x1 + radius,
            y1,
            x2 - radius,
            y1,
            x2,
            y1,
            x2,
            y1 + radius,
            x2,
            y2 - radius,
            x2,
            y2,
            x2 - radius,
            y2,
            x1 + radius,
            y2,
            x1,
            y2,
            x1,
            y2 - radius,
            x1,
            y1 + radius,
            x1,
            y1,
        ]
        return self.canvas.create_polygon(
            points,
            smooth=True,
            splinesteps=36,
            **kwargs,
        )

    # ------------------------------------------------------------------
    # 視窗操作
    # ------------------------------------------------------------------

    def center_window(self) -> None:
        self.root.update_idletasks()
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()

        x = max(0, (screen_width - WINDOW_SIZE) // 2)
        y = max(0, (screen_height - WINDOW_SIZE) // 2)

        self.root.geometry(f"{WINDOW_SIZE}x{WINDOW_SIZE}+{x}+{y}")

    def on_press(self, event: tk.Event) -> None:
        current_items = self.canvas.find_withtag("current")

        if current_items:
            tags = self.canvas.gettags(current_items[0])
            if "control" in tags:
                self.dragging = False
                return

        self.dragging = True
        self.drag_start_x = event.x_root
        self.drag_start_y = event.y_root
        self.window_start_x = self.root.winfo_x()
        self.window_start_y = self.root.winfo_y()

    def on_drag(self, event: tk.Event) -> None:
        if not self.dragging:
            return

        delta_x = event.x_root - self.drag_start_x
        delta_y = event.y_root - self.drag_start_y

        new_x = self.window_start_x + delta_x
        new_y = self.window_start_y + delta_y

        self.root.geometry(f"+{new_x}+{new_y}")

    def on_release(self, _event: tk.Event) -> None:
        self.dragging = False

    def show_context_menu(self, event: tk.Event) -> None:
        self.context_menu.entryconfigure(
            0,
            label="暫停防閒置" if self.enabled else "重新啟用",
        )
        try:
            self.context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.context_menu.grab_release()

    def run_button(self, name: str) -> None:
        data = self.button_data.get(name)

        if data is None:
            return

        command = data.get("command")
        if callable(command):
            command()

    # ------------------------------------------------------------------
    # 程式功能
    # ------------------------------------------------------------------

    def toggle_enabled(self) -> None:
        self.enabled = not self.enabled

        if not self.enabled and self.flame_active:
            self.stop_flames("已暫停，桌面火焰已清除")

        if self.enabled:
            self.canvas.itemconfigure(
                self.status_text,
                text="啟用中",
                fill=COLOR_PROGRESS,
            )
            self.canvas.itemconfigure(
                "toggle_text",
                text="Ⅱ",
            )
            self.canvas.itemconfigure(
                "toggle_oval",
                fill=COLOR_BUTTON,
            )
            self.canvas.itemconfigure(
                self.message_text,
                text="已重新啟用",
            )
            self.tray_icon.update_tooltip(
                f"{APP_NAME} {VERSION}－啟用中"
            )
        else:
            self.canvas.itemconfigure(
                self.status_text,
                text="已暫停",
                fill=COLOR_SUBTEXT,
            )
            self.canvas.itemconfigure(
                "toggle_text",
                text="▶",
            )
            self.canvas.itemconfigure(
                "toggle_oval",
                fill=COLOR_BUTTON_ACTIVE,
            )
            self.canvas.itemconfigure(
                self.message_text,
                text="暫停期間不會送出滑鼠訊號",
            )
            self.tray_icon.update_tooltip(
                f"{APP_NAME} {VERSION}－已暫停"
            )

        self.context_menu.entryconfigure(
            0,
            label="暫停防閒置" if self.enabled else "重新啟用",
        )

    def test_signal(self) -> None:
        try:
            send_tiny_mouse_move()
            now_text = time.strftime("%H:%M:%S")
            self.canvas.itemconfigure(
                self.message_text,
                text=f"{now_text} 已送出測試訊號",
            )
        except Exception as exc:
            messagebox.showerror(
                "滑鼠訊號錯誤",
                f"無法送出滑鼠移動訊號：\n\n{exc}",
                parent=self.root,
            )

    def test_flames(self) -> None:
        """
        測試桌面火焰。

        再按一次火焰按鈕可提前停止；
        測試會完整執行 5 次位移輪，
        每輪之間固定等待 20 秒。
        """
        if self.flame_test_mode and self.flame_active:
            self.stop_flames("火焰測試已停止")
            return

        self.flame_test_mode = True
        self.flame_test_until = (
            time.monotonic() + FLAME_TEST_SECONDS
        )
        self.flame_active = True
        self.flame_overlay.start(
            clear_first=True,
            fast_fill=True,
        )

        self.canvas.itemconfigure(
            self.message_text,
            text="火焰測試：基礎鋪滿開始",
        )

    def start_idle_flames(self) -> None:
        if self.flame_active and not self.flame_test_mode:
            return

        self.flame_test_mode = False
        self.flame_test_until = 0.0
        self.flame_active = True
        self.flame_overlay.start(
            clear_first=True,
            fast_fill=False,
        )

        self.canvas.itemconfigure(
            self.message_text,
            text="閒置 3 分鐘：基礎火焰鋪滿開始",
        )

    def stop_flames(self, message: str = "") -> None:
        self.flame_active = False
        self.flame_test_mode = False
        self.flame_test_until = 0.0
        self.flame_overlay.stop()

        if message:
            self.canvas.itemconfigure(
                self.message_text,
                text=message,
            )

    def escape_action(self, _event: tk.Event) -> None:
        if self.flame_active:
            self.stop_flames("桌面火焰已清除")
        else:
            self.minimize_to_tray()

    def minimize_to_tray(self) -> None:
        if self.closing:
            return

        self.root.withdraw()

    def restore_from_tray(self) -> None:
        if self.closing:
            return

        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()

        self.root.attributes("-topmost", True)
        self.root.after(
            150,
            lambda: self._remove_temporary_topmost(),
        )

    def _remove_temporary_topmost(self) -> None:
        if self.closing:
            return

        try:
            self.root.attributes("-topmost", False)
        except tk.TclError:
            pass

    def schedule_update(self) -> None:
        self.after_id = self.root.after(
            CHECK_INTERVAL_MS,
            self.update_status,
        )

    def update_status(self) -> None:
        if self.closing:
            return

        try:
            idle_seconds = get_idle_seconds()
            current_time = time.monotonic()

            self.update_stopwatch_display(idle_seconds)

            # 火焰測試期間顯示目前輪次、方向與 20 秒等待倒數。
            if self.flame_test_mode:
                self.canvas.itemconfigure(
                    self.message_text,
                    text=self.flame_overlay.round_status_text(),
                )

                if self.flame_overlay.sequence_finished:
                    self.canvas.itemconfigure(
                        self.message_text,
                        text="火焰 5 次位移輪全部完成",
                    )

                if current_time >= self.flame_test_until:
                    self.stop_flames("桌面火焰測試完成")

            else:
                # 若火焰已因閒置啟動，偵測閒置秒數突然下降，
                # 且不是本程式剛送出的滑鼠訊號，就視為使用者回來操作。
                if self.flame_active:
                    idle_drop = (
                        self.previous_idle_seconds
                        - idle_seconds
                    )

                    if (
                        idle_drop > 0.8
                        and current_time - self.last_injected_at > 1.2
                    ):
                        self.stop_flames(
                            "偵測到操作，桌面火焰已清除"
                        )

                # 真正閒置滿 3 分鐘時先啟動火焰，再送滑鼠訊號。
                if (
                    self.enabled
                    and idle_seconds >= IDLE_SECONDS
                ):
                    if not self.flame_active:
                        self.start_idle_flames()

                    if (
                        current_time - self.last_signal_time
                        >= SIGNAL_COOLDOWN_SECONDS
                    ):
                        send_tiny_mouse_move()
                        self.last_signal_time = current_time
                        self.last_injected_at = current_time

                        now_text = time.strftime("%H:%M:%S")
                        self.canvas.itemconfigure(
                            self.message_text,
                            text=(
                                f"{now_text} 已送出訊號／"
                                "火焰持續顯示"
                            ),
                        )

            self.previous_idle_seconds = idle_seconds

        except Exception as exc:
            self.canvas.itemconfigure(
                self.status_text,
                text="偵測失敗",
                fill=COLOR_DANGER_HOVER,
            )
            self.canvas.itemconfigure(
                self.message_text,
                text=str(exc)[:34],
            )

        self.schedule_update()

    # ------------------------------------------------------------------
    # 系統匣要求轉回 Tkinter 主執行緒
    # ------------------------------------------------------------------

    def _tray_restore_request(self) -> None:
        if not self.closing:
            self.root.after(0, self.restore_from_tray)

    def _tray_toggle_request(self) -> None:
        if not self.closing:
            self.root.after(0, self.toggle_enabled)

    def _tray_test_request(self) -> None:
        if not self.closing:
            self.root.after(0, self.test_signal)

    def _tray_exit_request(self) -> None:
        if not self.closing:
            self.root.after(0, self.close_app)

    def close_app(self) -> None:
        if self.closing:
            return

        self.closing = True

        if self.after_id is not None:
            try:
                self.root.after_cancel(self.after_id)
            except tk.TclError:
                pass
            self.after_id = None

        self.flame_overlay.destroy()
        self.tray_icon.stop()

        try:
            self.root.destroy()
        except tk.TclError:
            pass


def show_startup_error(error: Exception) -> None:
    try:
        error_root = tk.Tk()
        error_root.withdraw()

        messagebox.showerror(
            f"{APP_NAME} 啟動失敗",
            str(error),
            parent=error_root,
        )

        error_root.destroy()
    except Exception:
        pass


def main() -> None:
    root = tk.Tk()
    MouseAwakeApp(root)
    root.mainloop()


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        show_startup_error(exc)
        sys.exit(1)
