"""
screen_capture.py - Screenshot capture service with platform-native tools.

Captures the foreground window using platform-specific methods:
- Windows: Snipaste CLI (if configured) → PIL.ImageGrab (fallback)
- macOS: screencapture CLI (built-in) → PIL.ImageGrab (fallback)
"""
import io
import os
import subprocess
import sys
import tempfile
import logging

from app.platform import get_platform

logger = logging.getLogger(__name__)


class ScreenCaptureService:
    """Captures screenshots of the foreground window."""

    def __init__(self):
        self._snipaste_path = ''
        self._snipaste_available = False
        self._pil_fallback_warned = False

    def configure(self, snipaste_path=''):
        """Set and validate screenshot tool path.

        On Windows, validates the Snipaste executable path.
        On macOS, uses built-in screencapture (snipaste_path is ignored).
        """
        self._snipaste_path = snipaste_path.strip()

        if sys.platform == 'win32':
            is_valid, _ = get_platform().validate_screenshot_tool(self._snipaste_path)
            self._snipaste_available = is_valid
            if self._snipaste_path and not self._snipaste_available:
                logger.warning('Snipaste path invalid: %s', self._snipaste_path)
        else:
            # macOS: Snipaste not applicable
            self._snipaste_available = False

        self._pil_fallback_warned = False

    def capture_foreground_window(self):
        """Capture the foreground window screenshot.

        Returns:
            tuple: (png_bytes, error_msg, window_title)
                - png_bytes: bytes or None on failure
                - error_msg: str, empty on success
                - window_title: str, title of the captured window
        """
        try:
            window_info = get_platform().get_foreground_window()
            if not window_info:
                return None, '无法获取前台窗口', ''

            title = window_info.title
            rect = window_info.rect
            if not rect:
                return None, '无法获取窗口位置', title

            left, top, right, bottom = rect
            width = right - left
            height = bottom - top
            if width <= 0 or height <= 0:
                return None, '窗口尺寸无效', title

            # Platform-specific capture strategy
            if sys.platform == 'win32':
                # Windows: try Snipaste first
                if self._snipaste_available:
                    png_bytes, err = self._capture_with_snipaste(left, top, width, height)
                    if png_bytes:
                        return png_bytes, '', title
                    logger.warning('Snipaste capture failed: %s, falling back to PIL', err)
                    if not self._pil_fallback_warned:
                        self._pil_fallback_warned = True
            elif sys.platform == 'darwin':
                # macOS: try screencapture first
                png_bytes, err = self._capture_with_screencapture(left, top, width, height)
                if png_bytes:
                    return png_bytes, '', title
                logger.warning('screencapture failed: %s, falling back to PIL', err)

            # Fallback to PIL (cross-platform)
            png_bytes, err = self._capture_with_pil(left, top, right, bottom)
            if png_bytes:
                return png_bytes, '', title
            return None, err, title

        except Exception as e:
            logger.exception('Screenshot capture error')
            return None, str(e), ''

    # ── Snipaste Capture (Windows) ──

    def _capture_with_snipaste(self, x, y, w, h):
        """Capture using Snipaste CLI to a temp file.

        Returns:
            tuple: (bytes or None, error_msg)
        """
        tmp_path = None
        try:
            fd, tmp_path = tempfile.mkstemp(suffix='.png', prefix='autorecord_')
            os.close(fd)

            cmd = [
                self._snipaste_path, 'snip',
                '-a', f'{x},{y},{w},{h}',
                '-o', tmp_path,
            ]
            proc = subprocess.run(
                cmd, capture_output=True, timeout=10,
                **get_platform().create_subprocess_kwargs(),
            )
            if proc.returncode != 0:
                stderr = proc.stderr.decode('utf-8', errors='replace')[:200]
                return None, f'Snipaste exit code {proc.returncode}: {stderr}'

            if not os.path.exists(tmp_path) or os.path.getsize(tmp_path) == 0:
                return None, 'Snipaste output file empty'

            with open(tmp_path, 'rb') as f:
                return f.read(), ''

        except subprocess.TimeoutExpired:
            return None, 'Snipaste timeout'
        except Exception as e:
            return None, str(e)
        finally:
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass

    # ── screencapture (macOS) ──

    @staticmethod
    def _capture_with_screencapture(x, y, w, h):
        """Capture using macOS built-in screencapture CLI.

        Returns:
            tuple: (bytes or None, error_msg)
        """
        tmp_path = None
        try:
            fd, tmp_path = tempfile.mkstemp(suffix='.png', prefix='autorecord_')
            os.close(fd)

            cmd = [
                'screencapture', '-R',
                f'{x},{y},{w},{h}',
                '-t', 'png',
                tmp_path,
            ]
            logger.debug('screencapture command: %s', cmd)
            proc = subprocess.run(cmd, capture_output=True, timeout=10)

            if proc.returncode != 0:
                stderr = proc.stderr.decode('utf-8', errors='replace')[:200]
                return None, f'screencapture exit code {proc.returncode}: {stderr}'

            if not os.path.exists(tmp_path) or os.path.getsize(tmp_path) == 0:
                return None, 'screencapture output file empty'

            with open(tmp_path, 'rb') as f:
                return f.read(), ''

        except subprocess.TimeoutExpired:
            return None, 'screencapture timeout'
        except Exception as e:
            return None, str(e)
        finally:
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass

    # ── PIL Capture (cross-platform fallback) ──

    @staticmethod
    def _capture_with_pil(left, top, right, bottom):
        """Capture using PIL.ImageGrab.

        Returns:
            tuple: (bytes or None, error_msg)
        """
        try:
            from PIL import ImageGrab
            # all_screens=True is required for multi-monitor setups;
            # without it PIL only captures from the primary monitor,
            # producing a black image when the target window is on
            # a secondary display.
            img = ImageGrab.grab(bbox=(left, top, right, bottom), all_screens=True)
            buf = io.BytesIO()
            img.save(buf, format='PNG')
            return buf.getvalue(), ''
        except ImportError:
            return None, 'PIL not available'
        except Exception as e:
            return None, str(e)
