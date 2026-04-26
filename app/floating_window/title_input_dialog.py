"""
title_input_dialog.py - Compact title input popup for auto-recording.

Appears after each auto-capture, allowing the user to enter a step title
or skip. Matches the floating window's dark theme.
"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap, QShortcut, QKeySequence


class TitleInputDialog(QDialog):
    """Compact dialog for entering step title after auto-capture."""

    def __init__(self, screenshot_pixmap=None, window_title='', parent=None):
        super().__init__(parent)
        self._description = None
        self._trigger_ai = False

        self.setWindowTitle('步骤标题')
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Dialog
        )
        self.setFixedWidth(360)
        self.setStyleSheet(self._stylesheet())

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # Header
        header = QLabel('自动截图完成 — 输入步骤标题')
        header.setObjectName('dialogHeader')
        layout.addWidget(header)

        # Thumbnail preview
        if screenshot_pixmap and not screenshot_pixmap.isNull():
            thumb = QLabel()
            thumb.setAlignment(Qt.AlignmentFlag.AlignCenter)
            preview = screenshot_pixmap.scaled(
                336, 80,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            thumb.setPixmap(preview)
            thumb.setObjectName('thumbArea')
            layout.addWidget(thumb)

        # Title input
        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText(window_title or '输入步骤描述...')
        self.title_input.setObjectName('titleInput')
        layout.addWidget(self.title_input)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        self.skip_btn = QPushButton('跳过 (Esc)')
        self.skip_btn.setObjectName('skipBtn')
        self.skip_btn.setFixedHeight(32)
        self.skip_btn.clicked.connect(self._on_skip)
        btn_row.addWidget(self.skip_btn)

        self.confirm_btn = QPushButton('确认并AI评分 (Enter)')
        self.confirm_btn.setObjectName('confirmBtn')
        self.confirm_btn.setFixedHeight(32)
        self.confirm_btn.clicked.connect(self._on_confirm)
        btn_row.addWidget(self.confirm_btn)

        layout.addLayout(btn_row)

        # Shortcuts
        QShortcut(QKeySequence(Qt.Key.Key_Return), self).activated.connect(self._on_confirm)
        QShortcut(QKeySequence(Qt.Key.Key_Escape), self).activated.connect(self._on_skip)

        self.title_input.setFocus()

    def _on_skip(self):
        # Save with whatever is typed but don't trigger AI
        text = self.title_input.text().strip()
        self._description = text if text else None
        self._trigger_ai = False
        self.accept()

    def _on_confirm(self):
        text = self.title_input.text().strip()
        self._description = text if text else None
        self._trigger_ai = True
        self.accept()

    def get_result(self):
        """Get dialog result.

        Returns:
            tuple: (description: str|None, trigger_ai: bool)
        """
        return self._description, self._trigger_ai

    def get_hwnd(self):
        """Get the native window handle for exclusion."""
        try:
            return int(self.winId())
        except Exception:
            return 0

    @staticmethod
    def _stylesheet():
        return """
        TitleInputDialog {
            background: #1e1e2e;
            border: 2px solid #89b4fa;
            border-radius: 10px;
        }
        #dialogHeader {
            color: #89b4fa;
            font-size: 13px;
            font-weight: bold;
        }
        #thumbArea {
            background: #313244;
            border: 1px solid #45475a;
            border-radius: 6px;
            padding: 4px;
        }
        #titleInput {
            background: #313244;
            border: 1px solid #45475a;
            border-radius: 6px;
            color: #cdd6f4;
            padding: 8px 10px;
            font-size: 14px;
        }
        #titleInput:focus { border-color: #89b4fa; }
        #skipBtn {
            background: #45475a;
            color: #a6adc8;
            border: none;
            border-radius: 6px;
            font-size: 12px;
        }
        #skipBtn:hover { background: #585b70; }
        #confirmBtn {
            background: #89b4fa;
            color: #1e1e2e;
            border: none;
            border-radius: 6px;
            font-size: 12px;
            font-weight: bold;
        }
        #confirmBtn:hover { background: #74c7ec; }
        QLabel { color: #bac2de; font-size: 12px; }
        """
