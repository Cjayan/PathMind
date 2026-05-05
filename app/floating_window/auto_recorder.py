"""
auto_recorder.py - Central coordinator for auto-recording mode.

Orchestrates hotkey listener, mouse monitor, screen capture, and
title input dialog into a cohesive auto-recording workflow.
"""
import os
import sys
import time
import logging
import threading
from PyQt6.QtCore import QObject, QTimer, pyqtSignal
from PyQt6.QtGui import QPixmap, QImage

from app.platform import get_platform

from app.floating_window.hotkey_listener import GlobalHotkeyListener
from app.floating_window.mouse_monitor import MouseClickMonitor
from app.floating_window.screen_capture import ScreenCaptureService
from app.floating_window.title_input_dialog import TitleInputDialog
from app.floating_window.toast_notification import ToastWidget

logger = logging.getLogger(__name__)

CLICK_COOLDOWN_MS = 800  # Minimum interval between captures
SETTLE_DELAY_MS = 300    # Wait after click for UI to settle
HIDE_DELAY_MS = 100      # Wait after hiding window before capture


class AutoRecordController(QObject):
    """Central controller for auto-recording workflow."""

    recording_started = pyqtSignal()
    recording_stopped = pyqtSignal()
    step_saved = pyqtSignal(int, str)    # (step_count, description)
    error_occurred = pyqtSignal(str)     # error message

    def __init__(self, api_client, floating_window, parent=None):
        super().__init__(parent)
        self.api = api_client
        self._window = floating_window  # reference to FloatingWindow
        self._ai_worker = None  # set via set_ai_worker()

        self._is_recording = False
        self._is_processing = False  # True while capture-prompt-save cycle running
        self._flow = None
        self._step_count = 0
        self._last_click_time = 0.0

        # Sub-components
        self.hotkey_listener = GlobalHotkeyListener(self)
        self.mouse_monitor = MouseClickMonitor(self)
        self.capture_service = ScreenCaptureService()

        # Connect signals
        self.hotkey_listener.start_hotkey_pressed.connect(self._on_start_hotkey)
        self.hotkey_listener.stop_hotkey_pressed.connect(self._on_stop_hotkey)
        self.mouse_monitor.left_click_detected.connect(self._on_mouse_click)

    # ── Configuration ──

    def configure(self, hotkey_start='', hotkey_stop='', snipaste_path=''):
        """Configure hotkeys and screenshot tool from settings."""
        self.hotkey_listener.configure(hotkey_start, hotkey_stop)
        self.capture_service.configure(snipaste_path)

    @property
    def is_configured(self):
        return self.hotkey_listener.is_configured

    def set_ai_worker(self, worker):
        """Set the shared AI comment worker for retry-capable AI generation."""
        self._ai_worker = worker

    @property
    def is_recording(self):
        return self._is_recording

    # ── Start / Stop ──

    def start_recording(self, flow):
        """Start auto-recording for the given flow."""
        if self._is_recording:
            return
        if not flow:
            self.error_occurred.emit('请先选择一个流程')
            return

        self._flow = flow
        self._is_recording = True
        self._is_processing = False
        self._step_count = 0
        self._last_click_time = 0.0

        # Register floating window for click exclusion
        if sys.platform == 'darwin':
            # macOS: exclude all windows from our own process
            self.mouse_monitor.add_excluded_pid(os.getpid())
        else:
            # Windows: exclude by window handle
            try:
                hwnd = get_platform().get_native_window_id(self._window)
                self.mouse_monitor.add_excluded_hwnd(hwnd)
            except Exception:
                pass

        self.mouse_monitor.start()
        self.recording_started.emit()
        logger.info('Auto-recording started for flow: %s', flow.get('name', ''))

    def stop_recording(self):
        """Stop auto-recording."""
        if not self._is_recording:
            return

        self._is_recording = False
        self._is_processing = False
        self.mouse_monitor.stop()
        self.recording_stopped.emit()
        logger.info('Auto-recording stopped, %d steps captured', self._step_count)

    def start_hotkey_listener(self):
        """Start listening for global hotkeys (called on app init)."""
        self.hotkey_listener.start_listening()

    def stop_hotkey_listener(self):
        """Stop listening for global hotkeys (called on app close)."""
        self.hotkey_listener.stop_listening()

    # ── Hotkey Handlers ──

    def _on_start_hotkey(self):
        """Handle start hotkey press."""
        if self._is_recording:
            return
        # Always use the flow currently selected in floating window
        flow = self._window.current_flow
        if not flow:
            self.error_occurred.emit('请先选择录制流程后再按开始热键')
            return
        self.start_recording(flow)

    def _on_stop_hotkey(self):
        """Handle stop hotkey press."""
        self.stop_recording()

    # ── Mouse Click Handler ──

    def _on_mouse_click(self, x, y):
        """Handle detected left-click (main thread, via signal)."""
        if not self._is_recording:
            return
        if self._is_processing:
            return

        # Debounce
        now = time.time() * 1000
        if now - self._last_click_time < CLICK_COOLDOWN_MS:
            return
        self._last_click_time = now

        self._is_processing = True
        self.mouse_monitor.pause()

        # Wait for UI to settle after click, then capture
        QTimer.singleShot(SETTLE_DELAY_MS, self._do_hide_and_capture)

    def _do_hide_and_capture(self):
        """Hide floating window, wait briefly, then capture."""
        if not self._is_recording:
            self._finish_processing()
            return

        # Hide floating window so it doesn't appear in screenshot
        self._window.hide()

        # Wait for the window to actually disappear from screen
        QTimer.singleShot(HIDE_DELAY_MS, self._do_capture_and_prompt)

    def _do_capture_and_prompt(self):
        """Capture screenshot, show floating window, open title dialog."""
        try:
            if not self._is_recording:
                return

            # Capture the foreground window
            png_bytes, error_msg, window_title = self.capture_service.capture_foreground_window()

            # Show floating window again immediately
            self._window.show()

            if not png_bytes:
                self.error_occurred.emit(f'截图失败: {error_msg}')
                return

            # Create pixmap for dialog preview
            qimg = QImage.fromData(png_bytes)
            pixmap = QPixmap.fromImage(qimg) if not qimg.isNull() else None

            # Show title input dialog (modal, blocks until user responds)
            dialog = TitleInputDialog(pixmap, window_title, self._window)

            # Add dialog HWND to exclusion
            dialog_hwnd = dialog.get_hwnd()
            if dialog_hwnd:
                self.mouse_monitor.add_excluded_hwnd(dialog_hwnd)

            try:
                dialog.exec()
                description, trigger_ai = dialog.get_result()
            finally:
                if dialog_hwnd:
                    self.mouse_monitor.remove_excluded_hwnd(dialog_hwnd)

            # Save step in background thread
            self._save_step_async(png_bytes, description, trigger_ai)

        except Exception as e:
            logger.exception('Error in capture-and-prompt flow')
            self.error_occurred.emit(str(e))
            self._window.show()  # Ensure window is visible on error
        finally:
            self._finish_processing()

    def _finish_processing(self):
        """Re-enable click monitoring after processing."""
        self._is_processing = False
        if self._is_recording:
            self.mouse_monitor.resume()

    # ── Step Save (Background Thread) ──

    def _save_step_async(self, image_bytes, description, trigger_ai):
        """Save step via API in a background thread."""
        flow_id = self._flow.get('id') if self._flow else None
        if not flow_id:
            return

        def _worker():
            try:
                result = self.api.create_step(
                    flow_id=flow_id,
                    description=description,
                    image_bytes=image_bytes,
                )
                step_id = result.get('id')
                self._step_count += 1
                self.step_saved.emit(self._step_count, description or '')

                # Trigger AI via shared worker (with retry) or direct call (fallback)
                if trigger_ai and step_id:
                    if self._ai_worker:
                        self._ai_worker.submit(step_id)
                    else:
                        try:
                            self.api.trigger_ai_comment(step_id)
                        except Exception as e:
                            logger.warning('AI comment failed for step %s: %s', step_id, e)

            except Exception as e:
                logger.exception('Failed to save step')
                self.error_occurred.emit(f'保存步骤失败: {e}')

        thread = threading.Thread(target=_worker, daemon=True)
        thread.start()
