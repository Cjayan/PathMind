"""
hotkey_listener.py - Global hotkey listener using pynput.

Monitors keyboard globally (daemon thread) and emits Qt signals
when configured start/stop hotkeys are pressed.
"""
import logging
from PyQt6.QtCore import QObject, pyqtSignal

logger = logging.getLogger(__name__)


def _parse_hotkey(hotkey_str):
    """Parse a hotkey string like 'ctrl+shift+f9' into a frozenset of pynput keys.

    Returns:
        frozenset or None if parsing fails or string is empty.
    """
    if not hotkey_str or not hotkey_str.strip():
        return None

    try:
        from pynput.keyboard import Key, KeyCode
    except ImportError:
        logger.warning('pynput not installed, hotkeys disabled')
        return None

    parts = [p.strip().lower() for p in hotkey_str.strip().split('+')]
    keys = set()

    modifier_map = {
        'ctrl': Key.ctrl_l,
        'control': Key.ctrl_l,
        'shift': Key.shift_l,
        'alt': Key.alt_l,
        'cmd': Key.cmd,
        'win': Key.cmd,
    }

    function_key_map = {f'f{i}': getattr(Key, f'f{i}') for i in range(1, 21)}

    special_map = {
        'esc': Key.esc, 'escape': Key.esc,
        'tab': Key.tab,
        'space': Key.space,
        'enter': Key.enter, 'return': Key.enter,
        'backspace': Key.backspace,
        'delete': Key.delete,
        'home': Key.home, 'end': Key.end,
        'pageup': Key.page_up, 'pagedown': Key.page_down,
        'up': Key.up, 'down': Key.down, 'left': Key.left, 'right': Key.right,
        'insert': Key.insert,
        'printscreen': Key.print_screen,
        'pause': Key.pause,
        'capslock': Key.caps_lock,
        'numlock': Key.num_lock,
        'scrolllock': Key.scroll_lock,
    }

    for part in parts:
        if part in modifier_map:
            keys.add(modifier_map[part])
        elif part in function_key_map:
            keys.add(function_key_map[part])
        elif part in special_map:
            keys.add(special_map[part])
        elif len(part) == 1:
            keys.add(KeyCode.from_char(part))
        else:
            logger.warning('Unknown key in hotkey string: %s', part)
            return None

    return frozenset(keys) if keys else None


class GlobalHotkeyListener(QObject):
    """Listens for global hotkeys via pynput and emits Qt signals."""

    start_hotkey_pressed = pyqtSignal()
    stop_hotkey_pressed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._listener = None
        self._start_keys = None   # frozenset of pynput keys
        self._stop_keys = None
        self._pressed = set()     # currently pressed keys
        self._configured = False

    def configure(self, start_str, stop_str):
        """Parse and store hotkey configurations.

        Args:
            start_str: Hotkey string for starting recording (e.g., 'f9')
            stop_str: Hotkey string for stopping recording (e.g., 'f10')
        """
        self._start_keys = _parse_hotkey(start_str)
        self._stop_keys = _parse_hotkey(stop_str)
        self._configured = bool(self._start_keys and self._stop_keys)

        if self._configured:
            logger.info('Hotkeys configured: start=%s, stop=%s', start_str, stop_str)
        else:
            logger.info('Hotkeys not fully configured (start=%s, stop=%s)',
                        start_str, stop_str)

    @property
    def is_configured(self):
        return self._configured

    def start_listening(self):
        """Start the global keyboard listener (daemon thread)."""
        if not self._configured:
            logger.warning('Cannot start hotkey listener: not configured')
            return

        self.stop_listening()

        try:
            from pynput.keyboard import Listener
            self._pressed.clear()
            self._listener = Listener(
                on_press=self._on_press,
                on_release=self._on_release,
                daemon=True,
            )
            self._listener.start()
            logger.info('Hotkey listener started')
        except ImportError:
            logger.error('pynput not installed')
        except Exception:
            logger.exception('Failed to start hotkey listener')

    def stop_listening(self):
        """Stop the global keyboard listener."""
        if self._listener is not None:
            try:
                self._listener.stop()
            except Exception:
                pass
            self._listener = None
            self._pressed.clear()
            logger.info('Hotkey listener stopped')

    def _on_press(self, key):
        """pynput callback — runs on pynput daemon thread."""
        self._pressed.add(key)
        if self._start_keys and self._start_keys.issubset(self._pressed):
            self.start_hotkey_pressed.emit()
        elif self._stop_keys and self._stop_keys.issubset(self._pressed):
            self.stop_hotkey_pressed.emit()

    def _on_release(self, key):
        """pynput callback — runs on pynput daemon thread."""
        self._pressed.discard(key)
