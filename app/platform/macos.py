"""
macos.py - macOS platform implementation using Quartz (CoreGraphics).

Uses CGWindowListCopyWindowInfo for window queries and the built-in
screencapture CLI for screenshots. Requires pyobjc-framework-Quartz.

NOTE: No Mac test environment is currently available. This implementation
uses conservative error handling and detailed logging to aid remote debugging.
"""
import logging
import os
import subprocess

from app.platform.base import PlatformHelper, WindowInfo

logger = logging.getLogger(__name__)

# Lazy-loaded Quartz bindings — imported on first use
_quartz = None
_appkit = None


def _ensure_quartz():
    """Lazy-import Quartz framework. Logs detailed error on failure."""
    global _quartz
    if _quartz is not None:
        return True
    try:
        import Quartz
        _quartz = Quartz
        logger.info('Quartz framework imported successfully')
        return True
    except ImportError:
        logger.error(
            'pyobjc-framework-Quartz is not installed. '
            'Install it with: pip install pyobjc-framework-Quartz'
        )
        return False


def _ensure_appkit():
    """Lazy-import AppKit framework."""
    global _appkit
    if _appkit is not None:
        return True
    try:
        import AppKit
        _appkit = AppKit
        logger.info('AppKit framework imported successfully')
        return True
    except ImportError:
        logger.warning('AppKit not available, some features may be limited')
        return False


class MacOSPlatform(PlatformHelper):
    """macOS implementation using Quartz/CoreGraphics APIs."""

    def get_foreground_window(self):
        if not _ensure_quartz():
            return None
        if not _ensure_appkit():
            return None

        try:
            # Get the frontmost application's PID
            workspace = _appkit.NSWorkspace.sharedWorkspace()
            front_app = workspace.frontmostApplication()
            if front_app is None:
                logger.warning('No frontmost application found')
                return None

            front_pid = front_app.processIdentifier()
            logger.debug('Frontmost app PID: %d, name: %s',
                         front_pid, front_app.localizedName())

            # List on-screen windows for that PID
            window_list = _quartz.CGWindowListCopyWindowInfo(
                _quartz.kCGWindowListOptionOnScreenOnly
                | _quartz.kCGWindowListExcludeDesktopElements,
                _quartz.kCGNullWindowID,
            )

            if not window_list:
                logger.warning('CGWindowListCopyWindowInfo returned empty')
                return None

            # Find the first window owned by the frontmost app
            for win in window_list:
                owner_pid = win.get(_quartz.kCGWindowOwnerPID, 0)
                if owner_pid != front_pid:
                    continue

                # Skip windows on non-normal layers (menu bar, dock, etc.)
                layer = win.get(_quartz.kCGWindowLayer, 0)
                if layer != 0:
                    continue

                wid = win.get(_quartz.kCGWindowNumber, 0)
                title = win.get(_quartz.kCGWindowName, '') or ''
                bounds = win.get(_quartz.kCGWindowBounds, {})

                x = int(bounds.get('X', 0))
                y = int(bounds.get('Y', 0))
                w = int(bounds.get('Width', 0))
                h = int(bounds.get('Height', 0))

                rect = (x, y, x + w, y + h)

                logger.debug(
                    'Foreground window: id=%d, title=%r, rect=%s, pid=%d',
                    wid, title, rect, owner_pid,
                )
                return WindowInfo(
                    id=wid, title=title, rect=rect, owner_pid=owner_pid,
                )

            logger.warning('No suitable window found for PID %d', front_pid)
            return None

        except Exception:
            logger.exception('Failed to get foreground window on macOS')
            return None

    def get_window_at_point(self, x, y):
        if not _ensure_quartz():
            return None

        try:
            window_list = _quartz.CGWindowListCopyWindowInfo(
                _quartz.kCGWindowListOptionOnScreenOnly
                | _quartz.kCGWindowListExcludeDesktopElements,
                _quartz.kCGNullWindowID,
            )

            if not window_list:
                return None

            # Windows are in z-order (front to back), find the first containing (x, y)
            for win in window_list:
                layer = win.get(_quartz.kCGWindowLayer, 0)
                if layer != 0:
                    continue

                bounds = win.get(_quartz.kCGWindowBounds, {})
                bx = float(bounds.get('X', 0))
                by = float(bounds.get('Y', 0))
                bw = float(bounds.get('Width', 0))
                bh = float(bounds.get('Height', 0))

                if bx <= x < bx + bw and by <= y < by + bh:
                    wid = win.get(_quartz.kCGWindowNumber, 0)
                    title = win.get(_quartz.kCGWindowName, '') or ''
                    owner_pid = win.get(_quartz.kCGWindowOwnerPID, 0)

                    logger.debug(
                        'Window at (%d, %d): id=%d, title=%r, pid=%d',
                        x, y, wid, title, owner_pid,
                    )
                    return WindowInfo(
                        id=wid,
                        title=title,
                        rect=(int(bx), int(by), int(bx + bw), int(by + bh)),
                        owner_pid=owner_pid,
                    )

            return None

        except Exception:
            logger.exception('Failed to get window at point (%d, %d)', x, y)
            return None

    def get_root_window_id(self, window_id):
        # macOS CGWindowListCopyWindowInfo already returns top-level windows
        return window_id

    def get_native_window_id(self, qt_widget):
        # macOS uses process-level exclusion, so we don't need the native ID
        return 0

    def create_subprocess_kwargs(self):
        return {}

    def validate_screenshot_tool(self, path):
        # macOS uses the built-in screencapture command
        screencapture = '/usr/sbin/screencapture'
        if os.path.isfile(screencapture):
            return True, '使用系统内置截图工具 (screencapture)'
        # Fallback check
        try:
            result = subprocess.run(
                ['which', 'screencapture'],
                capture_output=True, timeout=5,
            )
            if result.returncode == 0:
                return True, '使用系统内置截图工具 (screencapture)'
        except Exception:
            pass
        return False, 'screencapture 未找到，将使用 PIL 内置截图'

    def get_data_directory(self, app_name):
        return os.path.join(
            os.path.expanduser('~/Library/Application Support'), app_name,
        )

    def show_fatal_error(self, title, message):
        try:
            # Escape double quotes for osascript
            esc_msg = message.replace('"', '\\"').replace('\n', '\\n')
            esc_title = title.replace('"', '\\"')
            subprocess.run(
                [
                    'osascript', '-e',
                    f'display dialog "{esc_msg}" with title "{esc_title}" '
                    f'buttons {{"OK"}} with icon stop',
                ],
                timeout=30,
            )
        except Exception:
            logger.exception('Failed to show fatal error dialog')

    def is_same_process_window(self, window_info):
        if window_info is None:
            return False
        return window_info.owner_pid == os.getpid()
