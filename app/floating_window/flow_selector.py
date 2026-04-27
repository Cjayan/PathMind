"""
flow_selector.py - Dialog for selecting a product and flow to record steps into.
"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QPushButton, QMessageBox, QLineEdit,
)
from PyQt6.QtCore import Qt


class FlowSelectorDialog(QDialog):
    """Modal dialog that lets the user pick a product → flow."""

    def __init__(self, api_client, parent=None):
        super().__init__(parent)
        self.api = api_client
        self.selected_flow = None
        self.selected_product = None

        self.setWindowTitle('选择录制流程')
        self.setFixedWidth(360)
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # Product selector
        layout.addWidget(QLabel('产品:'))
        self.product_combo = QComboBox()
        self.product_combo.currentIndexChanged.connect(self._on_product_changed)
        layout.addWidget(self.product_combo)

        # Flow selector
        layout.addWidget(QLabel('流程:'))
        self.flow_combo = QComboBox()
        layout.addWidget(self.flow_combo)

        # New flow creation row
        new_flow_row = QHBoxLayout()
        self.new_flow_input = QLineEdit()
        self.new_flow_input.setPlaceholderText('输入新流程名称...')
        self.new_flow_input.returnPressed.connect(self._on_create_flow)
        new_flow_row.addWidget(self.new_flow_input)
        self.create_flow_btn = QPushButton('新建')
        self.create_flow_btn.clicked.connect(self._on_create_flow)
        new_flow_row.addWidget(self.create_flow_btn)
        layout.addLayout(new_flow_row)

        # Buttons
        btn_layout = QHBoxLayout()
        self.ok_btn = QPushButton('确定')
        self.ok_btn.clicked.connect(self._on_ok)
        cancel_btn = QPushButton('取消')
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addStretch()
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(self.ok_btn)
        layout.addLayout(btn_layout)

        self._load_products()

    def _load_products(self):
        try:
            products = self.api.list_products()
            self.product_combo.clear()
            if not products:
                self.product_combo.addItem('(无产品)', None)
                return
            for p in products:
                self.product_combo.addItem(p['name'], p['id'])
        except Exception as e:
            QMessageBox.warning(self, '加载失败', f'无法加载产品列表:\n{e}')

    def _on_product_changed(self, index):
        product_id = self.product_combo.currentData()
        self.flow_combo.clear()
        self.create_flow_btn.setEnabled(product_id is not None)
        if product_id is None:
            return
        try:
            flows = self.api.list_flows(product_id)
            if not flows:
                self.flow_combo.addItem('(无流程)', None)
                return
            for f in flows:
                status = '录制中' if f.get('status') == 'recording' else '已完成'
                label = f'{f["name"]} [{status}]'
                self.flow_combo.addItem(label, f['id'])
        except Exception as e:
            QMessageBox.warning(self, '加载失败', f'无法加载流程列表:\n{e}')

    def _on_create_flow(self):
        product_id = self.product_combo.currentData()
        if product_id is None:
            QMessageBox.information(self, '提示', '请先选择一个产品')
            return
        name = self.new_flow_input.text().strip()
        if not name:
            QMessageBox.information(self, '提示', '请输入流程名称')
            return
        # Check for duplicate name in current flow list
        for i in range(self.flow_combo.count()):
            existing_text = self.flow_combo.itemText(i)
            # Flow items are formatted as "name [status]"
            existing_name = existing_text.rsplit(' [', 1)[0] if ' [' in existing_text else existing_text
            if existing_name == name:
                QMessageBox.warning(self, '重复', f'该产品下已存在名为「{name}」的流程')
                return
        try:
            flow = self.api.create_flow(product_id, name)
            self.new_flow_input.clear()
            # Refresh flow list and select the new one
            self._on_product_changed(self.product_combo.currentIndex())
            new_flow_id = flow.get('id')
            for i in range(self.flow_combo.count()):
                if self.flow_combo.itemData(i) == new_flow_id:
                    self.flow_combo.setCurrentIndex(i)
                    break
            # Auto-confirm selection
            self.selected_flow = {
                'id': new_flow_id,
                'name': flow.get('name', name),
                'product_id': product_id,
                'product_name': self.product_combo.currentText(),
            }
            self.accept()
        except Exception as e:
            QMessageBox.warning(self, '创建失败', f'无法创建流程:\n{e}')

    def _on_ok(self):
        flow_id = self.flow_combo.currentData()
        product_id = self.product_combo.currentData()
        if flow_id is None or product_id is None:
            QMessageBox.information(self, '提示', '请先选择一个有效的流程')
            return
        self.selected_flow = {
            'id': flow_id,
            'name': self.flow_combo.currentText(),
            'product_id': product_id,
            'product_name': self.product_combo.currentText(),
        }
        self.accept()

    def get_selected_flow(self):
        return self.selected_flow
