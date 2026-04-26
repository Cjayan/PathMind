"""
windows.py - Windows platform implementation using Win32 API (ctypes).

Extracted from the original screen_capture.py and mouse_monitor.py.
All ctypes.windll calls are isolated here — no other file in the project
should import ctypes.windll directly.
"""
import ctypes
import ctypes.wintypes
import logging
import os
import subprocess

from app.platform.base import PlatformHelper, WindowInfo

logger = logging.getLogger(__name__)


class WindowsPlatform(PlatformHelper):
    """Windows implementation using Win32 user32 API."""

    def get_foreground_window(self):
        try:
            hwnd = ctypes.windll.user32.GetForegroundWindow()
            if not hwnd:
                return None

            title = self._get_window_title(hwnd)
            rect = self._get_window_rect(hwnd)
            if rect is None:
                return None

            # Get owner PID
            pid = ctypes.wintypes.DWORD()
            ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))

            return WindowInfo(
                id=hwnd,
                title=title,
                rect=rect,
                owner_pid=pid.value,
            )
        except Exception:
            logger.exception('Failed to get foreground window')
            return None

    def get_window_at_point(self, x, y):
        try:
            point = ctypes.wintypes.POINT(int(x), int(y))
            hwnd = ctypes.windll.user32.WindowFromPoint(point)
            if not hwnd:
                return None

            title = self._get_window_title(hwnd)

            pid = ctypes.wintypes.DWORD()
            ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))

            return WindowInfo(
                id=hwnd,
                title=title,
                rect=(0, 0, 0, 0),  # rect not needed for click filtering
                owner_pid=pid.value,
            )
        except Exception:
            logger.exception('Failed to get window at point (%d, %d)', x, y)
            return None

    def get_root_window_id(self, window_id):
        try:
            # GA_ROOT = 2
            root = ctypes.windll.user32.GetAncestor(int(window_id), 2)
            return root if root else window_id
        except Exception:
            return window_id

    def get_native_window_id(self, qt_widget):
        try:
            return int(qt_widget.winId())
        except Exception:
            return 0

    def create_subprocess_kwargs(self):
        return {'creationflags': subprocess.CREATE_NO_WINDOW}

    def validate_screenshot_tool(self, path):
        if not path:
            return False, '路径不能为空'
        if not os.path.isfile(path):
            return False, '文件不存在'
        if not path.lower().endswith('.exe'):
            return False, '请选择 Snipaste.exe 文件'
        return True, 'Snipaste 路径有效'

    def get_data_directory(self, app_name):
        base = os.environ.get('APPDATA', os.path.expanduser('~'))
        return os.path.join(base, app_name)

    def show_fatal_error(self, title, message):
        try:
            ctypes.windll.user32.MessageBoxW(0, message, title, 0x10)
        except Exception:
            pass

    def is_same_process_window(self, window_info):
        # Windows uses HWND-level exclusion, not process-level
        return False

    # ── Internal helpers ──

    @staticmethod
    def _get_window_title(hwnd):
        """Get window title text via GetWindowTextW."""
        length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
        if length == 0:
            return ''
        buf = ctypes.create_unicode_buffer(length + 1)
        ctypes.windll.user32.GetWindowTextW(hwnd, buf, length + 1)
        return buf.value

    @staticmethod
    def _get_window_rect(hwnd):
        """Get window rectangle (left, top, right, bottom)."""
        rect = ctypes.wintypes.RECT()
        result = ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(rect))
        if not result:
            return None
        return (rect.left, rect.top, rect.right, rect.bottom)
