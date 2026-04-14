"""向导页面 3：下载模式选择页（预设 + 组件勾选）"""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from downloader.config import CUSTOM_CATEGORIES, OS_DISABLED_CATEGORIES, PRESETS


class ModeSelectionPage(QWidget):
    """下载模式选择页：预设按钮 + 组件勾选"""

    next_clicked = pyqtSignal(dict)  # {"categories": [...], "category_labels": {...}}
    back_clicked = pyqtSignal()

    def __init__(self):
        super().__init__()
        self._arch = ""
        self._version = ""
        self._os = ""
        self._username = ""
        self._password = ""
        self._preset_btns: dict[str, QPushButton] = {}
        self._category_cbs: dict[str, QCheckBox] = {}
        self._sdk_linked: set[str] = {"cuda11"}  # 跟随 SDK 自动选中/取消的类别
        self._auto_updating = False
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(60, 30, 60, 30)

        # 标题
        title = QLabel("选择下载内容")
        title.setFont(QFont("Microsoft YaHei", 14, QFont.Weight.Bold))
        layout.addWidget(title)

        # 当前选择信息
        self.info_label = QLabel("")
        self.info_label.setFont(QFont("Microsoft YaHei", 10))
        self.info_label.setStyleSheet("color: #888888;")
        layout.addWidget(self.info_label)

        # 预设按钮区域
        self.preset_title = QLabel("快速选择")
        self.preset_title.setFont(QFont("Microsoft YaHei", 12, QFont.Weight.Bold))
        layout.addWidget(self.preset_title)

        self.preset_layout = QHBoxLayout()
        self.preset_layout.setSpacing(16)

        self._preset_group = QButtonGroup(self)
        for key, preset in PRESETS.items():
            btn = QPushButton(preset["label"])
            btn.setFixedSize(160, 50)
            btn.setFont(QFont("Microsoft YaHei", 12))
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #F8F8F8;
                    border: 2px solid #DDDDDD;
                    border-radius: 8px;
                    color: #333333;
                }
                QPushButton:hover {
                    border-color: #AAAAAA;
                }
                QPushButton:checked {
                    background-color: #E8F0FE;
                    border: 2px solid #4A90D9;
                    color: #4A90D9;
                }
            """)
            btn.clicked.connect(lambda checked, k=key: self._on_preset_clicked(k))
            self._preset_group.addButton(btn)
            self._preset_btns[key] = btn
            self.preset_layout.addWidget(btn)

        self.preset_layout.addStretch(1)
        layout.addLayout(self.preset_layout)

        layout.addSpacing(8)

        # 组件勾选区域
        cat_title = QLabel("下载组件")
        cat_title.setFont(QFont("Microsoft YaHei", 12, QFont.Weight.Bold))
        layout.addWidget(cat_title)

        # 使用两列布局放置 checkbox
        cat_container = QWidget()
        cat_layout = QHBoxLayout(cat_container)
        cat_layout.setSpacing(20)
        cat_layout.setContentsMargins(0, 0, 0, 0)

        col_left = QVBoxLayout()
        col_left.setSpacing(8)
        col_right = QVBoxLayout()
        col_right.setSpacing(8)

        cat_keys = list(CUSTOM_CATEGORIES.keys())
        mid = (len(cat_keys) + 1) // 2
        for i, cat_key in enumerate(cat_keys):
            cat_config = CUSTOM_CATEGORIES[cat_key]
            cb = QCheckBox(cat_config["label"])
            cb.setFont(QFont("Microsoft YaHei", 11))
            cb.setCursor(Qt.CursorShape.PointingHandCursor)
            cb.setStyleSheet("QCheckBox { spacing: 6px; }")
            self._category_cbs[cat_key] = cb
            # SDK 勾选联动 cuda11
            if cat_key == "sdk":
                cb.toggled.connect(self._on_sdk_toggled)
            if i < mid:
                col_left.addWidget(cb)
            else:
                col_right.addWidget(cb)

        col_left.addStretch(1)
        col_right.addStretch(1)
        cat_layout.addLayout(col_left)
        cat_layout.addLayout(col_right)
        layout.addWidget(cat_container)

        layout.addStretch(1)

        # 底部按钮
        btn_layout = QHBoxLayout()

        self.back_btn = QPushButton("上一步")
        self.back_btn.setFixedSize(120, 40)
        self.back_btn.setFont(QFont("Microsoft YaHei", 11))
        self.back_btn.setStyleSheet("""
            QPushButton {
                background-color: #F0F0F0;
                border: 1px solid #CCCCCC;
                border-radius: 6px;
            }
            QPushButton:hover { background-color: #E0E0E0; }
        """)
        self.back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.back_btn.clicked.connect(self.back_clicked.emit)

        self.next_btn = QPushButton("下一步")
        self.next_btn.setFixedSize(120, 40)
        self.next_btn.setFont(QFont("Microsoft YaHei", 11))
        self.next_btn.setStyleSheet("""
            QPushButton {
                background-color: #4A90D9;
                color: white;
                border: none;
                border-radius: 6px;
            }
            QPushButton:hover { background-color: #3A7BC8; }
            QPushButton:pressed { background-color: #2E6AB5; }
            QPushButton:disabled { background-color: #AAAAAA; }
        """)
        self.next_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.next_btn.clicked.connect(self._on_next)

        btn_layout.addStretch(1)
        btn_layout.addWidget(self.back_btn)
        btn_layout.addSpacing(12)
        btn_layout.addWidget(self.next_btn)
        layout.addLayout(btn_layout)

    def on_enter(self, arch: str, version: str, os_name: str, username: str, password: str):
        """进入页面时设置上下文信息"""
        self._arch = arch
        self._version = version
        self._os = os_name
        self._username = username
        self._password = password

        arch_display = "x86_64" if arch == "x86" else "ARM64"
        os_display = os_name.capitalize()
        self.info_label.setText(f"当前: {arch_display} | {os_display} | {version}")

        # 根据操作系统禁用/启用组件
        is_restricted = os_name in ("windows", "centos")

        # "测试 vLLM" 预设包含 container 和 vllm_image，Windows/CentOS 下不可用
        vllm_btn = self._preset_btns.get("vllm")
        if vllm_btn:
            vllm_btn.setVisible(not is_restricted)

        # 禁用/启用相关 checkbox
        for cat_key, cb in self._category_cbs.items():
            if cat_key in OS_DISABLED_CATEGORIES:
                cb.setEnabled(not is_restricted)
                if is_restricted:
                    cb.setChecked(False)
            else:
                cb.setEnabled(True)

        # 清除预设选中状态
        self._preset_group.setExclusive(False)
        for btn in self._preset_btns.values():
            btn.setChecked(False)
        self._preset_group.setExclusive(True)

    def _on_preset_clicked(self, preset_key: str):
        """预设按钮被点击，自动勾选对应组件"""
        categories = PRESETS[preset_key]["categories"]
        self._auto_updating = True
        for cat_key, cb in self._category_cbs.items():
            cb.setChecked(cat_key in categories and cb.isEnabled())
        self._auto_updating = False

    def _on_sdk_toggled(self, checked: bool):
        """SDK 被勾选/取消时，自动勾选/取消 cuda11"""
        if self._auto_updating:
            return
        self._auto_updating = True
        for linked_key in self._sdk_linked:
            cb = self._category_cbs.get(linked_key)
            if cb and cb.isEnabled():
                cb.setChecked(checked)
        self._auto_updating = False

    def _on_next(self):
        """点击下一步：收集选中的类别，发射信号"""
        selected = [key for key, cb in self._category_cbs.items() if cb.isChecked()]
        if not selected:
            QMessageBox.warning(self, "请选择组件", "请至少勾选一个下载组件")
            return

        category_labels = {
            key: CUSTOM_CATEGORIES[key]["label"] for key in selected
        }
        self.next_clicked.emit({
            "categories": selected,
            "category_labels": category_labels,
        })
