"""
mouse_monitor.py - Global mouse click monitor using pynput.

Monitors left-click events globally (daemon thread) and emits Qt signals
with screen coordinates. Filters out clicks on excluded windows using
platform-specific methods:
- Windows: HWND-based exclusion
- macOS: Process-level exclusion (PID)
"""
import logging
from PyQt6.QtCore import QObject, pyqtSignal

from app.platform import get_platform

logger = logging.getLogger(__name__)


class MouseClickMonitor(QObject):
    """Monitors global mouse clicks and emits signals for left-clicks."""

    left_click_detected = pyqtSignal(int, int)  # (screen_x, screen_y)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._listener = None
        self._is_active = False
        self._excluded_hwnds = set()  # Window handles to ignore (Windows)
        self._excluded_pids = set()   # Process IDs to ignore (macOS)

    def start(self):
        """Start global mouse monitoring."""
        self.stop()
        try:
            from pynput.mouse import Listener, Button
            self._Button = Button
            self._is_active = True
            self._listener = Listener(
                on_click=self._on_click,
                daemon=True,
            )
            self._listener.start()
            logger.info('Mouse monitor started')
        except ImportError:
            logger.error('pynput not installed')
        except Exception:
            logger.exception('Failed to start mouse monitor')

    def stop(self):
        """Stop global mouse monitoring."""
        self._is_active = False
        if self._listener is not None:
            try:
                self._listener.stop()
            except Exception:
                pass
            self._listener = None
            logger.info('Mouse monitor stopped')

    def pause(self):
        """Temporarily pause click detection."""
        self._is_active = False

    def resume(self):
        """Resume click detection after pause."""
        if self._listener is not None:
            self._is_active = True

    def add_excluded_hwnd(self, hwnd):
        """Add a window handle to the exclusion set (Windows)."""
        self._excluded_hwnds.add(int(hwnd))

    def remove_excluded_hwnd(self, hwnd):
        """Remove a window handle from the exclusion set (Windows)."""
        self._excluded_hwnds.discard(int(hwnd))

    def add_excluded_pid(self, pid):
        """Add a process ID to the exclusion set (macOS)."""
        self._excluded_pids.add(int(pid))

    def remove_excluded_pid(self, pid):
        """Remove a process ID from the exclusion set (macOS)."""
        self._excluded_pids.discard(int(pid))

    def _on_click(self, x, y, button, pressed):
        """pynput callback — runs on pynput daemon thread.

        Only processes left-button press events when active.
        Filters out clicks on excluded windows.
        """
        if not pressed:
            return
        if not self._is_active:
            return
        if not hasattr(self, '_Button') or button != self._Button.left:
            return

        # Check if click is on an excluded window
        try:
            platform = get_platform()
            clicked_win = platform.get_window_at_point(int(x), int(y))

            if clicked_win:
                # Process-level exclusion (macOS)
                if clicked_win.owner_pid in self._excluded_pids:
                    return

                # Window-level exclusion (Windows)
                if clicked_win.id in self._excluded_hwnds:
                    return

                # Also check parent/root windows for child controls (Windows)
                root_id = platform.get_root_window_id(clicked_win.id)
                if root_id in self._excluded_hwnds:
                    return
        except Exception:
            pass

        self.left_click_detected.emit(int(x), int(y))
