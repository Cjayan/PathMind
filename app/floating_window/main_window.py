"""
main_window.py - Compact always-on-top floating window for quick step recording.

Features:
  - Always on top, draggable via title bar
  - Ctrl+V to paste screenshot from clipboard
  - Quick title input + save
  - Step counter showing progress
  - Minimize to small bar / restore
"""
import io
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTextEdit, QMessageBox, QApplication, QSizePolicy, QSlider,
)
from PyQt6.QtCore import Qt, QPoint, QByteArray, QBuffer, QIODevice, pyqtSignal, QRect, QEvent, QTimer
from PyQt6.QtGui import QPixmap, QImage, QShortcut, QKeySequence, QIcon, QCursor

from app.floating_window.api_client import ApiClient
from app.floating_window.flow_selector import FlowSelectorDialog
from app.floating_window.auto_recorder import AutoRecordController
from app.floating_window.ai_comment_worker import AiCommentWorker
from app.floating_window.toast_notification import ToastWidget


class FloatingWindow(QWidget):
    """Compact floating widget for recording flow steps."""

    closed = pyqtSignal()  # Emitted when window is closed

    COLLAPSED_HEIGHT = 40
    EXPANDED_WIDTH = 340
    EXPANDED_MIN_HEIGHT = 480
    RESIZE_MARGIN = 6  # pixels from edge to trigger resize

    def __init__(self, port=5000, parent=None):
        super().__init__(parent)
        self.api = ApiClient(f'http://127.0.0.1:{port}')
        self.current_flow = None
        self.step_count = 0
        self.current_image_bytes = None
        self.current_pixmap = None
        self._drag_pos = None
        self._resizing = False
        self._resize_edge = None
        self._is_pinned = True  # starts as always-on-top

        self._setup_ui()
        self._setup_shortcuts()
        self._setup_auto_recorder()
        self._setup_ai_worker()

    # ── UI Setup ──

    def _setup_ui(self):
        self.setWindowTitle('快速录制')
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.setMouseTracking(True)  # for resize cursor near edges
        self.setMinimumWidth(280)
        self.setMaximumWidth(500)
        self.setMinimumHeight(self.EXPANDED_MIN_HEIGHT)

        self.setStyleSheet(self._stylesheet())

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Title bar (draggable) ──
        self.title_bar = QWidget()
        self.title_bar.setObjectName('titleBar')
        self.title_bar.setFixedHeight(self.COLLAPSED_HEIGHT)
        tb_layout = QHBoxLayout(self.title_bar)
        tb_layout.setContentsMargins(10, 0, 4, 0)
        tb_layout.setSpacing(3)

        self.title_label = QLabel('快速录制')
        self.title_label.setObjectName('titleLabel')
        tb_layout.addWidget(self.title_label, 1)

        self.flow_btn = QPushButton('选择流程')
        self.flow_btn.setObjectName('flowBtn')
        self.flow_btn.setFixedHeight(24)
        self.flow_btn.clicked.connect(self._select_flow)
        tb_layout.addWidget(self.flow_btn)

        self.rec_btn = QPushButton('REC')
        self.rec_btn.setObjectName('recBtn')
        self.rec_btn.setFixedSize(36, 24)
        self.rec_btn.setToolTip('自动录制（需在设置中配置快捷键）')
        self.rec_btn.clicked.connect(self._toggle_auto_record)
        tb_layout.addWidget(self.rec_btn)

        self.pin_btn = QPushButton('\u2191')  # ↑ for pinned
        self.pin_btn.setObjectName('pinBtn')
        self.pin_btn.setFixedSize(24, 24)
        self.pin_btn.setToolTip('取消置顶')
        self.pin_btn.clicked.connect(self._toggle_pin)
        tb_layout.addWidget(self.pin_btn)

        self.min_btn = QPushButton('\u2014')
        self.min_btn.setObjectName('ctrlBtn')
        self.min_btn.setFixedSize(24, 24)
        self.min_btn.clicked.connect(self._toggle_collapse)
        tb_layout.addWidget(self.min_btn)

        self.close_btn = QPushButton('\u2715')
        self.close_btn.setObjectName('closeBtn')
        self.close_btn.setFixedSize(24, 24)
        self.close_btn.clicked.connect(self.close)
        tb_layout.addWidget(self.close_btn)

        root.addWidget(self.title_bar)

        # ── Body ──
        self.body = QWidget()
        self.body.setObjectName('body')
        body_layout = QVBoxLayout(self.body)
        body_layout.setContentsMargins(12, 12, 12, 12)
        body_layout.setSpacing(10)

        # Status label
        self.status_label = QLabel('请先选择录制流程')
        self.status_label.setObjectName('statusLabel')
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        body_layout.addWidget(self.status_label)

        # Image preview / paste area
        self.image_area = QLabel('Ctrl+V 粘贴截图')
        self.image_area.setObjectName('imageArea')
        self.image_area.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_area.setFixedHeight(160)
        self.image_area.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        body_layout.addWidget(self.image_area)

        # Clear image button
        img_actions = QHBoxLayout()
        img_actions.addStretch()
        self.clear_img_btn = QPushButton('清除图片')
        self.clear_img_btn.setObjectName('secondaryBtn')
        self.clear_img_btn.setFixedHeight(24)
        self.clear_img_btn.clicked.connect(self._clear_image)
        self.clear_img_btn.setVisible(False)
        img_actions.addWidget(self.clear_img_btn)
        body_layout.addLayout(img_actions)

        # Title input
        body_layout.addWidget(QLabel('步骤描述:'))
        self.desc_input = QLineEdit()
        self.desc_input.setPlaceholderText('输入步骤描述...')
        self.desc_input.setObjectName('descInput')
        body_layout.addWidget(self.desc_input)

        # Notes input (optional, collapsed by default)
        self.notes_toggle = QPushButton('+ 添加备注')
        self.notes_toggle.setObjectName('linkBtn')
        self.notes_toggle.setFixedHeight(24)
        self.notes_toggle.clicked.connect(self._toggle_notes)
        body_layout.addWidget(self.notes_toggle)

        self.notes_input = QTextEdit()
        self.notes_input.setPlaceholderText('可选备注...')
        self.notes_input.setFixedHeight(60)
        self.notes_input.setVisible(False)
        body_layout.addWidget(self.notes_input)

        # Save button
        self.save_btn = QPushButton('保存步骤')
        self.save_btn.setObjectName('saveBtn')
        self.save_btn.setFixedHeight(36)
        self.save_btn.clicked.connect(self._save_step)
        self.save_btn.setEnabled(False)
        body_layout.addWidget(self.save_btn)

        # Step counter
        self.counter_label = QLabel('')
        self.counter_label.setObjectName('counterLabel')
        self.counter_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        body_layout.addWidget(self.counter_label)

        # Opacity slider
        opacity_row = QHBoxLayout()
        opacity_row.setSpacing(6)
        opacity_lbl = QLabel('透明度')
        opacity_lbl.setObjectName('counterLabel')
        opacity_lbl.setFixedWidth(36)
        opacity_row.addWidget(opacity_lbl)
        self.opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self.opacity_slider.setObjectName('opacitySlider')
        self.opacity_slider.setRange(30, 100)
        self.opacity_slider.setValue(100)
        self.opacity_slider.setFixedHeight(18)
        self.opacity_slider.valueChanged.connect(self._on_opacity_changed)
        opacity_row.addWidget(self.opacity_slider)
        self.opacity_val = QLabel('100%')
        self.opacity_val.setObjectName('counterLabel')
        self.opacity_val.setFixedWidth(32)
        opacity_row.addWidget(self.opacity_val)
        body_layout.addLayout(opacity_row)

        root.addWidget(self.body)

        self._is_collapsed = False
        self._last_screen = None

        # Let Qt calculate the natural height based on content
        self.adjustSize()

    def _setup_shortcuts(self):
        paste_sc = QShortcut(QKeySequence('Ctrl+V'), self)
        paste_sc.activated.connect(self._paste_image)

        save_sc = QShortcut(QKeySequence('Ctrl+Return'), self)
        save_sc.activated.connect(self._save_step)

    # ── Auto-Recording ──

    def _setup_auto_recorder(self):
        """Initialize auto-recorder and load config."""
        self._auto_recorder = AutoRecordController(self.api, self, parent=self)

        # Connect signals
        self._auto_recorder.recording_started.connect(self._on_recording_started)
        self._auto_recorder.recording_stopped.connect(self._on_recording_stopped)
        self._auto_recorder.step_saved.connect(self._on_auto_step_saved)
        self._auto_recorder.error_occurred.connect(self._on_auto_error)

        # Load recording config from server
        self._load_recording_config()

    def _setup_ai_worker(self):
        """Initialize shared AI comment worker and wire it to auto_recorder."""
        self._ai_worker = AiCommentWorker(self.api, parent=self)
        self._ai_worker.ai_started.connect(self._on_ai_started)
        self._ai_worker.ai_succeeded.connect(self._on_ai_succeeded)
        self._ai_worker.ai_failed.connect(self._on_ai_failed)
        self._ai_worker.ai_retrying.connect(self._on_ai_retrying)
        # Share worker with auto_recorder so it also gets retry capability
        self._auto_recorder.set_ai_worker(self._ai_worker)

    def _load_recording_config(self):
        """Load recording config and configure auto-recorder."""
        try:
            config = self.api.get_config()
            rec = config.get('recording', {})
            self._auto_recorder.configure(
                hotkey_start=rec.get('hotkey_start', ''),
                hotkey_stop=rec.get('hotkey_stop', ''),
                snipaste_path=rec.get('snipaste_path', ''),
            )
            if self._auto_recorder.is_configured:
                self._auto_recorder.start_hotkey_listener()
                self.rec_btn.setToolTip('点击开始/停止自动录制')
            else:
                self.rec_btn.setToolTip('自动录制未配置（请在设置中配置快捷键）')
        except Exception:
            self.rec_btn.setToolTip('无法加载录制配置')

    def _toggle_auto_record(self):
        """Toggle auto-recording on/off."""
        if self._auto_recorder.is_recording:
            self._auto_recorder.stop_recording()
            return

        if not self._auto_recorder.is_configured:
            QMessageBox.information(
                self, '提示',
                '自动录制未配置。\n请在 Web 设置页面中配置"开始录制热键"和"停止录制热键"后重启悬浮窗。'
            )
            return

        if not self.current_flow:
            QMessageBox.information(self, '提示', '请先选择一个录制流程')
            return

        self._auto_recorder.start_recording(self.current_flow)

    def _on_recording_started(self):
        self.rec_btn.setStyleSheet(
            '#recBtn { background: #f38ba8; color: #1e1e2e; border: none; '
            'border-radius: 4px; font-size: 11px; font-weight: bold; }'
            '#recBtn:hover { background: #eba0ac; }'
        )
        self.rec_btn.setText('STOP')
        self.status_label.setText('自动录制中... 点击任意窗口自动截图')
        ToastWidget.show_toast('自动录制已开始', 'success', self._toast_pos())

    def _on_recording_stopped(self):
        self.rec_btn.setStyleSheet('')  # Reset to default from parent stylesheet
        self.rec_btn.setText('REC')
        count = self._auto_recorder._step_count
        self.status_label.setText(f'自动录制已停止，共录制 {count} 步')
        self._refresh_step_count()
        ToastWidget.show_toast(f'录制结束，共 {count} 步', 'info', self._toast_pos())

    def _on_auto_step_saved(self, count, desc):
        self.step_count += 1
        self.counter_label.setText(f'已录制 {self.step_count} 步')
        ToastWidget.show_toast(f'步骤已保存: {desc[:20] if desc else "(无标题)"}', 'success', self._toast_pos())

    def _on_auto_error(self, msg):
        ToastWidget.show_toast(msg, 'error', self._toast_pos())

    # ── AI Comment Worker Slots ──

    def _on_ai_started(self, step_id):
        self.status_label.setText('AI 评论生成中...')

    def _on_ai_succeeded(self, step_id):
        ToastWidget.show_toast('AI 评论已生成', 'success', self._toast_pos())
        self.status_label.setText('AI 评论已生成')

    def _on_ai_failed(self, step_id, error):
        short = error[:40] if len(error) > 40 else error
        ToastWidget.show_toast(f'AI 评论失败: {short}', 'error', self._toast_pos())
        self.status_label.setText('AI 评论生成失败')

    def _on_ai_retrying(self, step_id, attempt, max_retries):
        self.status_label.setText(f'AI 重试中 ({attempt}/{max_retries})...')

    def _toast_pos(self):
        """Get position for toast notifications near this window."""
        from PyQt6.QtCore import QPoint
        return self.mapToGlobal(QPoint(0, -40))

    # ── Dragging & Resizing ──

    def _edge_at(self, pos):
        """Return resize edge(s) if mouse is near an edge, else None."""
        rect = self.rect()
        m = self.RESIZE_MARGIN
        edges = []
        if pos.y() <= m:
            edges.append('top')
        if pos.y() >= rect.height() - m:
            edges.append('bottom')
        if pos.x() >= rect.width() - m:
            edges.append('right')
        if pos.x() <= m:
            edges.append('left')
        return tuple(edges) if edges else None

    def _update_cursor(self, pos):
        edges = self._edge_at(pos)
        if not edges:
            self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))
        elif set(edges) == {'top', 'left'} or set(edges) == {'bottom', 'right'}:
            self.setCursor(QCursor(Qt.CursorShape.SizeFDiagCursor))
        elif set(edges) == {'top', 'right'} or set(edges) == {'bottom', 'left'}:
            self.setCursor(QCursor(Qt.CursorShape.SizeBDiagCursor))
        elif 'top' in edges or 'bottom' in edges:
            self.setCursor(QCursor(Qt.CursorShape.SizeVerCursor))
        elif 'right' in edges or 'left' in edges:
            self.setCursor(QCursor(Qt.CursorShape.SizeHorCursor))

    def mousePressEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton:
            return
        edges = self._edge_at(event.pos())
        if edges and not self._is_collapsed:
            self._resizing = True
            self._resize_edge = edges
            self._resize_origin = event.globalPosition().toPoint()
            self._resize_geo = self.geometry()
            event.accept()
        elif self._in_title_bar(event.pos()):
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if self._resizing and event.buttons() & Qt.MouseButton.LeftButton:
            delta = event.globalPosition().toPoint() - self._resize_origin
            geo = QRect(self._resize_geo)
            if 'top' in self._resize_edge:
                geo.setTop(geo.top() + delta.y())
            if 'bottom' in self._resize_edge:
                geo.setBottom(geo.bottom() + delta.y())
            if 'right' in self._resize_edge:
                geo.setRight(geo.right() + delta.x())
            if 'left' in self._resize_edge:
                geo.setLeft(geo.left() + delta.x())
            # Enforce min/max
            if geo.width() < self.minimumWidth():
                if 'left' in self._resize_edge:
                    geo.setLeft(geo.right() - self.minimumWidth())
                else:
                    geo.setRight(geo.left() + self.minimumWidth())
            if geo.width() > self.maximumWidth():
                if 'left' in self._resize_edge:
                    geo.setLeft(geo.right() - self.maximumWidth())
                else:
                    geo.setRight(geo.left() + self.maximumWidth())
            if geo.height() < self.minimumHeight():
                if 'top' in self._resize_edge:
                    geo.setTop(geo.bottom() - self.minimumHeight())
                else:
                    geo.setBottom(geo.top() + self.minimumHeight())
            self.setGeometry(geo)
            event.accept()
        elif self._drag_pos is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()
        else:
            self._update_cursor(event.pos())

    def mouseReleaseEvent(self, event):
        self._drag_pos = None
        self._resizing = False
        self._resize_edge = None

    def _in_title_bar(self, pos):
        return pos.y() <= self.COLLAPSED_HEIGHT

    # ── Collapse / Expand ──

    def _toggle_collapse(self):
        self._is_collapsed = not self._is_collapsed
        self.body.setVisible(not self._is_collapsed)
        if self._is_collapsed:
            self.setFixedHeight(self.COLLAPSED_HEIGHT)
            self.min_btn.setText('\u25a1')
        else:
            self.setMinimumHeight(self.EXPANDED_MIN_HEIGHT)
            self.setMaximumHeight(16777215)
            self.adjustSize()
            self.min_btn.setText('\u2014')

    # ── Pin / Opacity ──

    def _toggle_pin(self):
        self._is_pinned = not self._is_pinned
        flags = self.windowFlags()
        if self._is_pinned:
            flags |= Qt.WindowType.WindowStaysOnTopHint
            self.pin_btn.setText('\u2191')  # ↑
            self.pin_btn.setToolTip('取消置顶')
            self.pin_btn.setStyleSheet('')
        else:
            flags &= ~Qt.WindowType.WindowStaysOnTopHint
            self.pin_btn.setText('\u2193')  # ↓
            self.pin_btn.setToolTip('置顶窗口')
            self.pin_btn.setStyleSheet('#pinBtn { color: #45475a; }')
        # Save geometry before setWindowFlags (which hides the window)
        geo = self.geometry()
        self.setWindowFlags(flags)
        self.setGeometry(geo)
        self.show()

    def _on_opacity_changed(self, value):
        self.setWindowOpacity(value / 100.0)
        self.opacity_val.setText(f'{value}%')

    # ── Flow Selection ──

    def _select_flow(self):
        dialog = FlowSelectorDialog(self.api, self)
        if dialog.exec() == FlowSelectorDialog.DialogCode.Accepted:
            flow = dialog.get_selected_flow()
            if flow:
                self.current_flow = flow
                self.flow_btn.setText(flow['name'].split(' [')[0][:12])
                self.title_label.setText(flow['product_name'][:15])
                self.save_btn.setEnabled(True)
                self._refresh_step_count()
                self.status_label.setText(f'录制到: {flow["name"].split(" [")[0]}')

    def _refresh_step_count(self):
        if not self.current_flow:
            return
        try:
            steps = self.api.list_steps(self.current_flow['id'])
            self.step_count = len(steps)
            self.counter_label.setText(f'已录制 {self.step_count} 步')
        except Exception:
            pass

    # ── Image Paste ──

    def _paste_image(self):
        clipboard = QApplication.clipboard()
        mime = clipboard.mimeData()

        pixmap = None
        if mime.hasImage():
            image = clipboard.image()
            if not image.isNull():
                pixmap = QPixmap.fromImage(image)
        elif mime.hasUrls():
            for url in mime.urls():
                if url.isLocalFile():
                    path = url.toLocalFile()
                    pm = QPixmap(path)
                    if not pm.isNull():
                        pixmap = pm
                        break

        if pixmap is None or pixmap.isNull():
            self.status_label.setText('剪贴板中没有图片')
            return

        self.current_pixmap = pixmap
        self.current_image_bytes = self._pixmap_to_png_bytes(pixmap)

        # Show preview
        preview = pixmap.scaled(
            self.image_area.width() - 4,
            self.image_area.height() - 4,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.image_area.setPixmap(preview)
        self.clear_img_btn.setVisible(True)
        self.status_label.setText('截图已粘贴')

    def _clear_image(self):
        self.current_image_bytes = None
        self.current_pixmap = None
        self.image_area.setText('Ctrl+V 粘贴截图')
        self.clear_img_btn.setVisible(False)

    @staticmethod
    def _pixmap_to_png_bytes(pixmap):
        ba = QByteArray()
        buf = QBuffer(ba)
        buf.open(QIODevice.OpenModeFlag.WriteOnly)
        pixmap.save(buf, 'PNG')
        buf.close()
        return bytes(ba)

    # ── Notes Toggle ──

    def _toggle_notes(self):
        visible = not self.notes_input.isVisible()
        self.notes_input.setVisible(visible)
        self.notes_toggle.setText('- 收起备注' if visible else '+ 添加备注')
        self.adjustSize()

    # ── Save Step ──

    def _save_step(self):
        if not self.current_flow:
            QMessageBox.information(self, '提示', '请先选择一个录制流程')
            return

        desc = self.desc_input.text().strip()
        if not desc:
            self.status_label.setText('请输入步骤描述')
            return
        if not self.current_image_bytes:
            self.status_label.setText('请先粘贴截图 (Ctrl+V)')
            return

        self.save_btn.setEnabled(False)
        self.save_btn.setText('保存中...')
        self.status_label.setText('正在保存...')

        try:
            notes = self.notes_input.toPlainText().strip() or None
            result = self.api.create_step(
                flow_id=self.current_flow['id'],
                description=desc,
                image_bytes=self.current_image_bytes,
                notes=notes,
            )
            self.step_count += 1
            self.counter_label.setText(f'已录制 {self.step_count} 步')

            # Trigger AI comment generation in background
            step_id = result.get('id')
            if step_id:
                self._ai_worker.submit(step_id)
                self.status_label.setText(f'步骤 {self.step_count} 已保存，AI评论生成中...')
            else:
                self.status_label.setText(f'步骤 {self.step_count} 已保存')

            # Clear form for next step
            self.desc_input.clear()
            self.notes_input.clear()
            self._clear_image()
            self.desc_input.setFocus()

        except Exception as e:
            self.status_label.setText(f'保存失败')
            QMessageBox.warning(self, '保存失败', str(e))
        finally:
            self.save_btn.setEnabled(True)
            self.save_btn.setText('保存步骤')

    # ── DPI / Screen change handling ──

    def showEvent(self, event):
        super().showEvent(event)
        self._last_screen = self.screen()

    def moveEvent(self, event):
        """Detect screen change and reset layout to prevent DPI-induced stretching."""
        super().moveEvent(event)
        current_screen = self.screen()
        if not current_screen or current_screen == self._last_screen:
            return
        self._last_screen = current_screen

        if self._is_collapsed:
            return

        # Defer correction to after Qt finishes internal DPI processing
        QTimer.singleShot(100, self._correct_after_screen_change)

    def _correct_after_screen_change(self):
        """Reset window size after moving to a different DPI screen."""
        if self._is_collapsed:
            return

        # Re-apply constraints (they may have been distorted by DPI scaling)
        self.setMinimumWidth(280)
        self.setMaximumWidth(500)
        self.setMinimumHeight(self.EXPANDED_MIN_HEIGHT)
        self.setMaximumHeight(16777215)

        # Let Qt recalculate natural size from content
        self.adjustSize()

        # Clamp position so window stays fully on the current screen
        screen = self.screen()
        if screen:
            geo = screen.availableGeometry()
            x = max(geo.left(), min(self.x(), geo.right() - self.width()))
            y = max(geo.top(), min(self.y(), geo.bottom() - self.height()))
            self.move(x, y)

    # ── Close ──

    def closeEvent(self, event):
        # Stop auto-recording if active
        if hasattr(self, '_auto_recorder'):
            self._auto_recorder.stop_recording()
            self._auto_recorder.stop_hotkey_listener()
        # Stop AI comment worker
        if hasattr(self, '_ai_worker'):
            self._ai_worker.stop()
        self.closed.emit()
        super().closeEvent(event)

    # ── Stylesheet ──

    @staticmethod
    def _stylesheet():
        return """
        FloatingWindow {
            background: #1e1e2e;
            border: 1px solid #444;
            border-radius: 10px;
        }
        #titleBar {
            background: #2d2d3f;
            border-top-left-radius: 10px;
            border-top-right-radius: 10px;
        }
        #titleLabel {
            color: #cdd6f4;
            font-size: 13px;
            font-weight: bold;
        }
        #flowBtn {
            background: #45475a;
            color: #cdd6f4;
            border: none;
            border-radius: 4px;
            padding: 2px 10px;
            font-size: 12px;
        }
        #flowBtn:hover { background: #585b70; }
        #recBtn {
            background: #45475a;
            color: #a6adc8;
            border: none;
            border-radius: 4px;
            font-size: 11px;
            font-weight: bold;
        }
        #recBtn:hover { background: #585b70; }
        #ctrlBtn, #closeBtn {
            background: transparent;
            color: #a6adc8;
            border: none;
            border-radius: 4px;
            font-size: 13px;
            font-weight: bold;
        }
        #pinBtn {
            background: transparent;
            color: #89b4fa;
            border: none;
            border-radius: 4px;
            font-size: 13px;
            font-weight: bold;
        }
        #pinBtn:hover { background: #45475a; }
        #ctrlBtn:hover { background: #45475a; }
        #closeBtn:hover { background: #f38ba8; color: #1e1e2e; }
        #body {
            background: #1e1e2e;
            border-bottom-left-radius: 10px;
            border-bottom-right-radius: 10px;
        }
        #statusLabel {
            color: #a6adc8;
            font-size: 12px;
        }
        #imageArea {
            background: #313244;
            border: 2px dashed #585b70;
            border-radius: 8px;
            color: #6c7086;
            font-size: 13px;
        }
        #descInput {
            background: #313244;
            border: 1px solid #45475a;
            border-radius: 6px;
            color: #cdd6f4;
            padding: 6px 10px;
            font-size: 13px;
        }
        #descInput:focus { border-color: #89b4fa; }
        QTextEdit {
            background: #313244;
            border: 1px solid #45475a;
            border-radius: 6px;
            color: #cdd6f4;
            padding: 4px 8px;
            font-size: 12px;
        }
        QLabel {
            color: #bac2de;
            font-size: 12px;
        }
        #saveBtn {
            background: #89b4fa;
            color: #1e1e2e;
            border: none;
            border-radius: 8px;
            font-size: 14px;
            font-weight: bold;
        }
        #saveBtn:hover { background: #74c7ec; }
        #saveBtn:disabled { background: #45475a; color: #6c7086; }
        #secondaryBtn {
            background: transparent;
            color: #a6adc8;
            border: 1px solid #45475a;
            border-radius: 4px;
            font-size: 11px;
            padding: 2px 8px;
        }
        #secondaryBtn:hover { border-color: #f38ba8; color: #f38ba8; }
        #linkBtn {
            background: transparent;
            color: #89b4fa;
            border: none;
            font-size: 12px;
            text-align: left;
        }
        #linkBtn:hover { color: #74c7ec; }
        #counterLabel {
            color: #6c7086;
            font-size: 11px;
        }
        QComboBox {
            background: #313244;
            color: #cdd6f4;
            border: 1px solid #45475a;
            border-radius: 4px;
            padding: 4px 8px;
        }
        QComboBox:hover { border-color: #89b4fa; }
        QComboBox QAbstractItemView {
            background: #313244;
            color: #cdd6f4;
            selection-background-color: #45475a;
        }
        #opacitySlider::groove:horizontal {
            background: #313244;
            height: 4px;
            border-radius: 2px;
        }
        #opacitySlider::handle:horizontal {
            background: #89b4fa;
            width: 12px;
            height: 12px;
            margin: -4px 0;
            border-radius: 6px;
        }
        #opacitySlider::handle:horizontal:hover {
            background: #74c7ec;
        }
        """
