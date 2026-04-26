"""
toast_notification.py - Non-blocking toast popup for status notifications.

Shows brief messages near the floating window without blocking the workflow.
"""
from PyQt6.QtWidgets import QWidget, QLabel, QHBoxLayout
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QFont


class ToastWidget(QWidget):
    """Small translucent popup that auto-fades after a delay."""

    # Class-level reference to prevent GC
    _active_toasts = []

    TYPE_STYLES = {
        'success': ('#a6e3a1', '#1e1e2e'),
        'error':   ('#f38ba8', '#1e1e2e'),
        'info':    ('#89b4fa', '#1e1e2e'),
        'warning': ('#fab387', '#1e1e2e'),
    }

    def __init__(self, message, toast_type='info', parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)

        bg_color, text_color = self.TYPE_STYLES.get(toast_type, self.TYPE_STYLES['info'])

        self.setStyleSheet(f"""
            ToastWidget {{
                background: {bg_color};
                border-radius: 8px;
                border: 1px solid {bg_color};
            }}
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 8, 14, 8)

        label = QLabel(message)
        label.setStyleSheet(f'color: {text_color}; font-size: 12px; font-weight: bold;')
        label.setFont(QFont('', 10))
        layout.addWidget(label)

        self.adjustSize()
        self.setFixedSize(self.sizeHint())

    @classmethod
    def show_toast(cls, message, toast_type='info', position=None, duration_ms=2500):
        """Show a toast notification.

        Args:
            message: Text to display
            toast_type: 'success', 'error', 'info', or 'warning'
            position: QPoint for top-left corner, or None for screen center
            duration_ms: Auto-dismiss delay in milliseconds
        """
        toast = cls(message, toast_type)
        cls._active_toasts.append(toast)

        if position:
            toast.move(position)
        else:
            from PyQt6.QtWidgets import QApplication
            screen = QApplication.primaryScreen()
            if screen:
                geo = screen.availableGeometry()
                x = geo.center().x() - toast.width() // 2
                y = geo.top() + 80
                toast.move(x, y)

        toast.show()

        def _dismiss():
            toast.close()
            if toast in cls._active_toasts:
                cls._active_toasts.remove(toast)

        QTimer.singleShot(duration_ms, _dismiss)

        return toast
